# 구현 계획: 주식 변동성 분석 봇 (제도권주식분석 전략 반영)

## 목표 설명

3배 레버리지 ETF(SOXL, TQQQ 등)의 일일 데이터를 가져와 **1년 단위 표준편차**를 분석하고, 주가가 통계적 저점(제도권주식분석 채널 전략 기반)에 도달했을 때 매수 신호를 포착하여 구글 스프레드시트에 기록하는 자동화 봇입니다.

## 사용자 검토 필요 (User Review Required)

> [!IMPORTANT] > **Google Cloud 설정**: 사용자는 관리자 역할을 수행합니다. GCP 프로젝트를 생성하고, **Google Sheets API** 및 **Google Drive API**를 활성화한 후, **서비스 계정(Service Account) JSON 키**를 생성해야 합니다.
>
> **GitHub Secrets 설정**: 자동화를 위해 `service_account.json` 파일의 내용을 GitHub 레포지토리의 Secrets(`GCP_SERVICE_ACCOUNT`)에 등록해야 합니다.

## 변경 제안 (Proposed Changes)

### 디렉토리 구조

```
stock-bot/
├── .github/
│   └── workflows/
│       └── daily_analysis.yml # 매일 한국시간 오전 6시 실행
├── config/
│   ├── settings.py         # 설정 (티커, 기간=252일, 임계값)
│   └── secrets_loader.py   # 시크릿 로드
├── src/
│   ├── __init__.py
│   ├── data_fetcher.py     # Yfinance 래퍼
│   ├── analyzer.py         # Pandas 통계 로직 (Z-Score)
│   └── sheets_manager.py   # Gspread 래퍼
├── main.py                 # 실행 스크립트
├── requirements.txt        # 의존성
└── service_account.json    # (로컬용 - .gitignore)
```

### 1. 환경 및 의존성

-   `yfinance`, `pandas`, `gspread`, `oauth2client`

### 2. 핵심 로직 및 설정 업데이트 (`config/settings.py`)

#### [전략] 제도권주식분석 스타일 설정

-   **LOOKBACK_PERIOD (분석 기간)**: `252` (1년 영업일 기준).
    -   영상에서 언급된 "1년 단위 변동성"을 반영하기 위함입니다.
-   **THRESHOLDS (매수 구간)**:
    -   **1차 매수 (관심)**: Z-Score `-1.0` (약 상위 16% 하락 구간)
    -   **2차 매수 (강력)**: Z-Score `-2.0` (약 상위 2.3% 하락 구간, 통계적 과매도)
    -   **3차 매수 (패닉)**: Z-Score `-3.0` (블랙스완급)

### 3. 모듈 상세

#### `src/analyzer.py`

-   `calculate_statistics(df)`:
    -   252일 이동평균(SMA_252) 계산.
    -   252일 표준편차(STD_252) 계산.
    -   현재 주가의 Z-Score 산출: `(현재가 - SMA_252) / STD_252`.
    -   데이터가 1년 미만인 경우 분석에서 제외하거나 경고 메시지 처리.

#### `src/sheets_manager.py`

-   대시보드 탭에 다음 컬럼 표시:
    `종목 | 현재가 | 1년평균 | Z-Score | 상태(매수/대기) | 매수단계(0/1/2/3)`

## 검증 계획

### 로컬 테스트

-   `python main.py` 실행 시 SOXL, TQQQ의 Z-Score가 정상적으로 계산되는지 로그 확인.
-   구글 시트에 업데이트된 값과 야후 파이낸스 차트를 대조하여 검증.
