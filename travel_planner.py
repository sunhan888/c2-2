import argparse
import json
import os
from datetime import datetime

import requests
from dotenv import load_dotenv
from google import genai


# ==================================================
# 1. 환경변수 및 API 키 설정
# ==================================================

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")

if not GEMINI_API_KEY:
    print("오류: GEMINI_API_KEY가 설정되지 않았습니다.")
    print(".env 파일에 GEMINI_API_KEY를 설정해주세요.")
    raise SystemExit(1)

if not KAKAO_REST_API_KEY:
    print("오류: KAKAO_REST_API_KEY가 설정되지 않았습니다.")
    print(".env 파일에 KAKAO_REST_API_KEY를 설정해주세요.")
    raise SystemExit(1)

client = genai.Client(api_key=GEMINI_API_KEY)


# ==================================================
# 2. 날짜 형식 검증
# ==================================================

def valid_date(date_string):
    try:
        datetime.strptime(date_string, "%Y-%m-%d")
        return date_string
    except ValueError:
        raise argparse.ArgumentTypeError(
            "날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식으로 입력하세요."
        )


# ==================================================
# 3. CLI 설정
# ==================================================

parser = argparse.ArgumentParser(
    description="Gemini와 Kakao Local API를 활용한 국내 여행 추천 프로그램"
)

parser.add_argument(
    "--date",
    "-date",
    required=True,
    type=valid_date,
    help='여행 날짜 (예: 2026-10-15)'
)

args = parser.parse_args()


# 프로그램 전체 오류 기록
errors = []


# ==================================================
# 4. Gemini - 1차 여행지 추천
# ==================================================

def get_travel_recommendation(travel_date):

    prompt = f"""
여행 날짜는 {travel_date}입니다.

이 날짜에 대한민국에서 여행하기 좋은 지역 1곳을 추천해주세요.

반드시 아래 구조의 JSON 객체만 출력하세요.
마크다운 코드블록이나 JSON 이외의 설명은 출력하지 마세요.

{{
    "recommended_city": "지역명",
    "weather": "해당 시기의 일반적인 날씨 요약",
    "events": ["행사 또는 축제 후보1", "행사 또는 축제 후보2"],
    "reason": "추천 이유를 2~4문장으로 설명"
}}
"""

    # 최초 요청 + JSON 파싱 실패 시 1회 재시도
    for attempt in range(2):

        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt
            )

            text = response.text.strip()

            data = json.loads(text)

            # 필수 키 확인
            required_keys = [
                "recommended_city",
                "weather",
                "events",
                "reason"
            ]

            for key in required_keys:
                if key not in data:
                    raise ValueError(f"필수 키 누락: {key}")

            return data

        except (json.JSONDecodeError, ValueError) as e:

            if attempt == 0:
                print("  - JSON 파싱 실패. 1회 재시도합니다.")

                prompt += """
이전 응답을 JSON으로 파싱할 수 없었습니다.
다른 설명 없이 필수 키만 포함한 올바른 JSON 객체를 출력하세요.
"""
            else:
                errors.append({
                    "step": "llm_recommendation",
                    "type": "JSON_PARSE_ERROR",
                    "message": str(e)
                })

                raise

        except Exception as e:

            errors.append({
                "step": "llm_recommendation",
                "type": "API_ERROR",
                "message": str(e)
            })

            raise


# ==================================================
# 5. Kakao Local - 맛집 검색
# ==================================================

def search_restaurants(city):

    url = "https://dapi.kakao.com/v2/local/search/keyword.json"

    headers = {
        "Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"
    }

    params = {
        "query": f"{city} 맛집",
        "size": 5
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=10
        )

        # 인증 오류
        if response.status_code in (401, 403):

            errors.append({
                "step": "place_search",
                "type": "AUTH_ERROR",
                "message": f"HTTP {response.status_code}"
            })

            print(
                f"  - 인증 오류({response.status_code}). "
                "맛집은 데이터 없음으로 처리합니다."
            )

            return []

        response.raise_for_status()

        data = response.json()

        documents = data.get("documents", [])

        # 검색 결과 0건
        if not documents:

            errors.append({
                "step": "place_search",
                "type": "EMPTY_RESULT",
                "message": f"0 results for query={city} 맛집"
            })

            print(
                "  - 검색 결과 0건. "
                "맛집은 데이터 없음으로 처리합니다."
            )

            return []

        restaurants = []

        for place in documents:

            restaurants.append({
                "name": place.get("place_name", ""),
                "address": place.get("address_name", ""),
                "category": place.get("category_name", ""),
                "url": place.get("place_url", ""),
                "x": float(place["x"]) if place.get("x") else None,
                "y": float(place["y"]) if place.get("y") else None
            })

        return restaurants

    except requests.RequestException as e:

        errors.append({
            "step": "place_search",
            "type": "REQUEST_ERROR",
            "message": str(e)
        })

        print(
            "  - 장소 API 호출 실패. "
            "맛집은 데이터 없음으로 처리합니다."
        )

        return []

    except Exception as e:

        errors.append({
            "step": "place_search",
            "type": "UNKNOWN_ERROR",
            "message": str(e)
        })

        print(
            "  - 장소 검색 처리 중 오류가 발생했습니다. "
            "맛집은 데이터 없음으로 처리합니다."
        )

        return []


# ==================================================
# 6. Gemini - 최종 Markdown 리포트
# ==================================================

def create_final_report(
    travel_date,
    recommendation,
    restaurants
):

    recommendation_text = json.dumps(
        recommendation,
        ensure_ascii=False,
        indent=2
    )

    restaurant_text = json.dumps(
        restaurants,
        ensure_ascii=False,
        indent=2
    )

    error_text = json.dumps(
        errors,
        ensure_ascii=False,
        indent=2
    )

    prompt = f"""
다음 데이터를 이용하여 국내 여행 추천 리포트를 작성해주세요.

여행 날짜:
{travel_date}

1차 여행 추천 데이터:
{recommendation_text}

맛집 검색 결과:
{restaurant_text}

오류 목록:
{error_text}

반드시 Markdown 형식으로 작성해주세요.

다음 항목을 모두 포함해야 합니다.

# {travel_date} 국내 여행 추천 리포트

## 추천 지역
## 추천 이유
## 날씨 요약
## 행사/축제
## 맛집 추천
## 1일 일정 제안
## 오류 요약(errors)

1일 일정은 오전, 오후, 저녁으로 나누어 제안해주세요.

맛집 목록이 비어 있다면
"데이터 없음"이라고 명시해주세요.

오류 목록이 비어 있다면
"오류 없음"이라고 작성해주세요.
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt
        )

        return response.text.strip()

    except Exception as e:

        errors.append({
            "step": "final_report",
            "type": "API_ERROR",
            "message": str(e)
        })

        # LLM이 실패해도 최소 리포트 생성
        restaurant_section = "데이터 없음"

        if restaurants:
            restaurant_section = "\n".join(
                [
                    f"- {r['name']} / {r['address']}"
                    for r in restaurants
                ]
            )

        return f"""# {travel_date} 국내 여행 추천 리포트

## 추천 지역
{recommendation.get("recommended_city", "데이터 없음")}

## 추천 이유
{recommendation.get("reason", "데이터 없음")}

## 날씨 요약
{recommendation.get("weather", "데이터 없음")}

## 행사/축제
{chr(10).join("- " + event for event in recommendation.get("events", []))}

## 맛집 추천
{restaurant_section}

## 1일 일정 제안
최종 리포트 생성 API 오류로 자동 일정을 생성하지 못했습니다.

## 오류 요약(errors)
{json.dumps(errors, ensure_ascii=False, indent=2)}
"""


# ==================================================
# 7. 메인 프로그램 실행
# ==================================================

print("[1/3] 1차 추천 생성 중(Gemini)...")

try:
    recommendation = get_travel_recommendation(args.date)

    city = recommendation["recommended_city"]

    print(f"  - recommended_city: {city}")

except Exception as e:

    print("  - 여행지 추천 생성 실패:", e)
    print("프로그램을 종료합니다.")

    raise SystemExit(1)


print("[2/3] 맛집 검색 중(Kakao Local)...")

restaurants = search_restaurants(city)

if restaurants:

    print(f"  - 맛집 {len(restaurants)}곳 검색 완료")

    for restaurant in restaurants:
        print(
            f"  - {restaurant['name']} / "
            f"{restaurant['address']}"
        )

else:
    print("  - 맛집 데이터 없음")


print("[3/3] 최종 리포트 생성 중(Gemini)...")

final_report = create_final_report(
    args.date,
    recommendation,
    restaurants
)

print("  - 리포트 생성 완료")


# ==================================================
# 8. 결과 저장
# ==================================================

os.makedirs("results", exist_ok=True)

raw_data = {
    "date": args.date,
    "recommendation": recommendation,
    "restaurants": restaurants,
    "errors": errors
}

json_path = f"results/{args.date}_raw.json"
report_path = f"results/{args.date}_travel_plan.md"


with open(
    json_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        raw_data,
        f,
        ensure_ascii=False,
        indent=2
    )


with open(
    report_path,
    "w",
    encoding="utf-8"
) as f:

    f.write(final_report)


print()
print("완료!")
print(f"원본 데이터: {json_path}")
print(f"최종 리포트: {report_path}")
