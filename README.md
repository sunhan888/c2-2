# 국내 여행 추천 프로그램

Gemini API와 Kakao Local API를 연동하여 사용자가 입력한 여행 날짜를 기준으로 국내 여행지를 추천하고, 해당 지역의 맛집을 검색한 뒤 최종 여행 리포트를 생성하는 CLI 기반 Python 프로그램입니다.

## 1. 프로그램 개요

프로그램은 다음 순서로 동작합니다.

1. 사용자가 CLI에서 여행 날짜를 입력합니다.
2. Gemini API가 여행 날짜를 바탕으로 추천 지역, 날씨, 행사/축제, 추천 이유를 JSON 형식으로 생성합니다.
3. Gemini가 추천한 지역명을 Kakao Local API의 입력값으로 사용합니다.
4. Kakao Local API에서 해당 지역의 맛집을 최대 5곳 검색합니다.
5. 여행 추천 정보와 맛집 검색 결과를 다시 Gemini API에 전달합니다.
6. 최종 여행 리포트를 Markdown 형식으로 생성합니다.
7. 원본 데이터는 JSON, 최종 리포트는 Markdown 파일로 `results/` 폴더에 저장합니다.

## 2. 개발 환경

- Python 3.10 이상
- Google Gemini API
- Kakao Local API

사용 라이브러리:

- google-genai
- requests
- python-dotenv

## 3. 설치 방법

필요한 라이브러리를 설치합니다.

```bash
pip install -r requirements.txt
```

## 4. API 키 설정

프로젝트 최상위 폴더에 `.env` 파일을 생성합니다.

```text
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
KAKAO_REST_API_KEY=YOUR_KAKAO_REST_API_KEY
```

실제 API 키 값은 GitHub, README, 실행 로그, 결과 파일 등에 공개하지 않습니다.

`.gitignore`에 `.env`를 등록하여 Git 저장소에 API 키가 업로드되지 않도록 관리합니다.

## 5. 실행 방법

터미널에서 다음과 같이 실행합니다.

```bash
python travel_planner.py --date "2026-10-15"
```

또는 다음 형식도 사용할 수 있습니다.

```bash
python travel_planner.py -date "2026-10-15"
```

날짜는 반드시 `YYYY-MM-DD` 형식으로 입력해야 합니다.

잘못된 날짜 형식을 입력하면 사용법과 오류 메시지를 출력하고 프로그램을 종료합니다.

## 6. 실행 과정

정상 실행 시 다음과 같은 진행 로그가 표시됩니다.

```text
[1/3] 1차 추천 생성 중(Gemini)...
  - recommended_city: 경주

[2/3] 맛집 검색 중(Kakao Local)...
  - 맛집 5곳 검색 완료

[3/3] 최종 리포트 생성 중(Gemini)...
  - 리포트 생성 완료

완료!
원본 데이터: results/2026-10-15_raw.json
최종 리포트: results/2026-10-15_travel_plan.md
```

## 7. 결과물 확인

프로그램을 실행하면 `results/` 폴더가 자동으로 생성됩니다.

예시:

```text
results/
├── 2026-10-15_raw.json
└── 2026-10-15_travel_plan.md
```

### 원본 JSON

원본 JSON에는 다음 데이터가 저장됩니다.

- 입력한 여행 날짜
- Gemini의 1차 여행 추천 결과
- Kakao Local의 맛집 검색 결과
- 프로그램 실행 중 발생한 오류 목록

주요 구조:

```json
{
  "date": "2026-10-15",
  "recommendation": {
    "recommended_city": "경주",
    "weather": "날씨 정보",
    "events": [
      "행사1",
      "행사2"
    ],
    "reason": "추천 이유"
  },
  "restaurants": [],
  "errors": []
}
```

### 최종 Markdown 리포트

최종 여행 리포트에는 다음 내용이 포함됩니다.

- 추천 지역
- 추천 이유
- 날씨 요약
- 행사/축제
- 맛집 추천
- 1일 일정 제안
- 오류 요약

## 8. 오류 처리

프로그램에서는 `try-except`를 사용하여 외부 API 호출과 데이터 처리 중 발생할 수 있는 오류를 처리합니다.

- API 키가 설정되지 않은 경우 프로그램을 즉시 종료합니다.
- Gemini의 JSON 파싱에 실패하면 최대 1회 재시도합니다.
- Kakao Local API 호출이 실패하더라도 전체 프로그램을 중단하지 않습니다.
- 맛집 검색 결과가 0건이면 `데이터 없음`으로 처리합니다.
- 인증, 네트워크, 검색 결과 없음 등의 오류는 `errors` 배열에 기록합니다.
- 최종 리포트 생성 API가 실패해도 최소한의 Markdown 리포트를 생성합니다.

## 9. API 키 보안

API 키를 Python 코드에 직접 작성하지 않고 `.env` 파일과 환경변수를 사용하는 이유는 다음과 같습니다.

1. GitHub 또는 협업 과정에서 API 키가 실수로 공개되는 것을 방지할 수 있습니다.
2. API 키가 변경되어도 프로그램 코드를 수정할 필요가 없습니다.
3. API 사용량 및 과금과 관련된 보안 사고를 예방할 수 있습니다.

따라서 `.env` 파일은 외부에 공유하거나 Git 저장소에 업로드하지 않습니다.

## 10. API 데이터 연결 구조

이 프로그램의 핵심은 서로 다른 API의 결과를 다음 API의 입력으로 사용하는 것입니다.

```text
사용자 날짜 입력
        ↓
Gemini API
        ↓
추천 지역 JSON
        ↓
recommended_city 추출
        ↓
Kakao Local API
        ↓
맛집 검색 JSON
        ↓
여행 추천 JSON + 맛집 JSON
        ↓
Gemini API
        ↓
최종 Markdown 여행 리포트
```

단일 API를 호출하는 것에서 끝나는 것이 아니라, LLM의 구조화된 출력 결과를 다른 외부 API의 입력으로 활용하고 여러 데이터를 결합하여 최종 결과물을 생성합니다.