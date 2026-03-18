# FinFlow 개발문서 v1 고도화 ver0.1

이 문서는 **현재 레포에 실제로 구현되어 있는 v1 시스템**을 기준으로, 문서/설계가 더 이상 “이전 가정(예: 특정 브로커 API 연동)”에 묶이지 않도록 재정리한 개발 문서입니다.

기존 `개발문서v1고도화..md`는 당시의 가정 기반 설계가 일부 남아 있어, 본 문서에서는 **구현된 기능을 다시 기술**하고, **API 경로/형식은 현재 `/v1` 프리픽스 라우팅**을 따릅니다.

---

## 1. 목표

1. 업로드(CSV/XLS/XLSX)에서 **파싱 전략을 생성/재사용**하고, **LLM 카테고리 보강**이 안정적으로 동작하는 흐름을 문서화
2. 투자 기능에서 **trade 생성 시 현금(계좌) 정산**이 자동으로 반영되고, **5~10분 단위 주가 갱신**이 DB에 적재되는 흐름을 문서화
3. API/서비스 문서(엔드포인트/응답 포맷)는 구현 코드와 맞도록 `/v1` 경로를 기준으로 정리

---

## 2. 현재 v1 기준(전제/범위)

### 2.1 라우팅 규칙

- 모든 비헬스 체크 API는 `backend/app/main.py`에서 `/v1` 프리픽스를 붙여 등록합니다.
- 헬스 체크는 `/health` 입니다.

### 2.2 공통 응답 형식

`backend/app/main.py` 기준으로 모든 API는 아래 형태로 응답합니다.

- `success`: boolean
- `data`: 성공 시 데이터
- `error`: 실패 시 `{ code, message, details }`
- `meta`: 리스트/페이지네이션 등 메타 데이터

### 2.3 인증

- `Authorization: Bearer <accessToken>` 헤더 기반 JWT 인증을 사용합니다.
- `/v1/auth/login`, `/v1/auth/register`, `/v1/auth/refresh` 로 토큰을 발급/갱신합니다.

---

## 3. v1 API 엔드포인트(현재 구현 기준)

아래 경로는 모두 `/v1` 프리픽스를 포함한 “클라이언트 호출 기준”입니다.

### 3.1 Auth

- `POST /v1/auth/login`: 로그인 후 access/refresh 토큰 발급
- `POST /v1/auth/register`: 회원가입 후 토큰 발급
- `POST /v1/auth/refresh`: refreshToken으로 accessToken 갱신
- `POST /v1/auth/logout`: 서버는 토큰 무효화를 “클라이언트 로컬 폐기” 중심으로 처리(로그아웃 응답만 반환)

### 3.2 Transactions

- `GET /v1/transactions`
  - 필터: `type`, `category`, `account`, `startDate`, `endDate`, `search`, 페이지네이션(`page`, `limit`)
- `GET /v1/transactions/{txn_id}`: 단일 거래 조회
- `POST /v1/transactions`: 거래 생성
- `PUT /v1/transactions/{txn_id}`: 거래 수정
- `DELETE /v1/transactions/{txn_id}`: 거래 삭제

### 3.3 Accounts

- `GET /v1/accounts`: 계좌 목록
- `GET /v1/accounts/{account_id}`: 단일 계좌
- `GET /v1/accounts/{account_id}/flow?period=30d`: 계좌 잔액 흐름
- `POST /v1/accounts`: 계좌 생성
- `PUT /v1/accounts/{account_id}`: 계좌 수정
- `DELETE /v1/accounts/{account_id}`: 계좌 삭제

### 3.4 Upload (CSV/XLS/XLSX)

업로드는 “미리보기 + 임포트” 두 단계로 구성됩니다.

#### 3.4.1 미리보기

- `POST /v1/upload/preview`
  - `multipart/form-data`
  - `file`: CSV/XLS/XLSX 파일
  - `format`: 선택(`csv`, `xlsx`, `xls`), 미지정 시 확장자로 판단
  - `accountId`: 선택(거래의 account 이름 보정에 사용)

미리보기 흐름은 다음의 핵심을 포함합니다.

1) 파일 헤더/샘플 추출 → 2) `ParsingStrategy` 매칭/생성 → 3) smart parser로 row 파싱/정규화 → 4) 타입/카테고리 자동 보강(등록 카테고리 유지 → 키워드 분류 → 필요 시 Groq LLM) → 5) preview rows 반환

#### 3.4.2 임포트

- `POST /v1/upload/transactions`
  - `multipart/form-data`
  - `file`: CSV/XLS/XLSX
  - `accountId`: 필수(거래가 연결될 계좌)
  - `format`: 선택
  - `skipDuplicates`: bool(기본 `true`)
  - `toleranceDays`: int(기본 `0`)

임포트 흐름에서 `upload router`는 미리보기와 동일하게 파싱/보강을 수행하고, 최종 저장 시에는 `import_transactions(... auto_classify=False)`로 “중복 LLM/규칙 덮어쓰기”를 방지합니다.

### 3.5 Category Keywords

- `GET /v1/category-keywords?category=...`: 키워드 목록(카테고리 필터 가능)
- `POST /v1/category-keywords`: 키워드 생성
- `PUT /v1/category-keywords/{keyword_id}`: 키워드 수정
- `DELETE /v1/category-keywords/{keyword_id}`: 키워드 삭제
- `GET /v1/category-keywords/categories`: 키워드가 존재하는 카테고리 목록

### 3.6 Parsing Strategies

- `GET /v1/parsing-strategies`: 최근 업데이트 순 전략 목록(최대 100)
- `GET /v1/parsing-strategies/{strategy_id}`: 전략 상세(매핑/규칙/헤더/예시 포함)
- `DELETE /v1/parsing-strategies/{strategy_id}`: 전략 삭제

> 전략 생성/추론은 업로드 라우터의 내부 로직에서 자동으로 동작하며, 외부에서 직접 생성할 필요가 없습니다.

### 3.7 Investments

v1 투자 기능은 **trade 기록**을 기준으로 포트폴리오를 구성하고, **현금(계좌) 정산은 주식 주문의 체결 결과를 기반으로** 반영하도록 설계합니다.

또한 시세/보유 동기화는 **한국투자증권 OpenAPI(KIS)** 를 사용하는 방향으로 고도화합니다. (즉, 이전의 외부 시세 provider 개념은 “KIS quote/잔고 데이터”로 교체)

- `GET /v1/investments/holdings`
  - 브로커(KIS) 보유 데이터 동기화 결과를 기준으로 보유 종목/수량을 구성
  - 평균단가/평가손익 계산 후, 현재가는 `investment_price_latest`(또는 KIS에서 즉시 조회한 값)를 사용
- `GET /v1/investments/trades?ticker=&action=&startDate=&endDate=`
  - 투자 거래 목록
- `GET /v1/investments/prices/{ticker}?period=30d|...`
  - KIS로 수집한 일별 close 기반 가격 히스토리(프론트 차트 호환 필드: `date/open/high/low/close/volume`)
- `POST /v1/investments/trades`
  - buy/sell trade 생성
  - `accountId`를 지정하면 “주문 체결 시” 정산할 현금 계좌로 사용
- `POST /v1/investments/prices/refresh`
  - `ticker`가 있으면 해당 종목만 KIS quote로 즉시 갱신
  - 없으면 “사용자가 트래킹 중인 모든 tickers” 대상으로 갱신

---

## 4. 서비스(구현) 상세: 현재 “v1 고도화” 핵심 포인트

### 4.1 업로드 파싱 전략 재사용(LLM 호출 최소화)

업로드 라우터는 아래 방식으로 전략 재사용을 우선합니다.

1) 파일에서 `headers`, `samples` 추출
2) `parsing_strategy_service.get_or_create_strategy(db, user_id, headers, samples)` 호출
3) `ParsingStrategy`는 `compute_fingerprint(headers, samples)`의 SHA256 기반 fingerprint으로 재사용
4) 전략이 없으면 `Groq`로 `mapping`/`rules`를 생성하고 DB에 저장
5) 스마트 파서가 `mapping_to_index_map(...)` 결과를 이용해 컬럼 인덱스 기반으로 파싱

#### mapping_to_index_map의 보정 로직(중요)

LLM이 자주 하는 실수를 방어하기 위해 아래 보정이 포함됩니다.

- `"거래점/지점"`(지점/브랜치)은 account 이름이 아니므로, memo로 이동 후 account는 비움
- LLM이 `description`과 `memo`를 뒤집는 케이스 대응
  - 예: description이 `"적요"`로, memo가 `"내용"`/`"거래내용"`으로 들어온 경우 스왑

### 4.2 CSV/XLS/XLSX 전처리(금액/설명 우선순위)

`smart_upload_parser.py` 기준 정규화 핵심:

- description 우선순위: `"내용"`, `"거래내용"`, `"사용처"` 등이 `"적요"`보다 우선
- deposit/withdraw 분리 컬럼이 있으면 canonical `amount`를 `deposit - withdraw`로 계산
  - withdraw는 expense로 취급되도록 절댓값 처리 후 차감
- 타입(`income`/`expense`)은 deposit/withdraw가 있으면 분리 컬럼 기반으로 추정

이 전처리가 제대로 되어야, 이후 `auto_detect_type` / `enrich_categories_for_rows` / 중복 검사까지 일관되게 동작합니다.

### 4.3 카테고리 보강(키워드 → LLM) 및 Groq 안정성

`llm_category_enricher.py`의 단계:

1) 이미 등록된 카테고리가 있으면 유지
2) 키워드 분류(우선, 등록된 경우 즉시 확정)
3) 키워드 결과가 `"기타"`이거나 등록되지 않은 경우 LLM 호출
4) LLM이 새 카테고리를 제안하면 짧은 이름(1~12자) 등의 가드레일로 등록 가능

또한 `GroqClient`는 아래 안정성 처리를 포함합니다.

- decommission된 모델이면 자동 fallback
- Groq 응답이 JSON만 오지 않는 경우를 대비한 “loose JSON 파싱” (`{...}` 첫 JSON 오브젝트 추출)

### 4.4 투자: 시세 갱신(5~10분), DB 적재, 차트용 데이터 제공

`backend/app/main.py` startup에서 `start_investment_price_updater_if_needed()`가 호출됩니다.

동작:

- `investment_price_updater_loop()`가 `Settings.stock_price_update_interval_seconds` 주기로 실행
- tickers는 `InvestmentTrade`에서 distinct `(user_id, ticker)`를 기반으로 갱신(기본 동작)
- 가격 소스는 **한국투자증권 OpenAPI(KIS) quote API** 를 통해 가져오도록 교체
- 갱신 결과는 다음 두 테이블에 저장
  - `investment_price_latest`: 가장 최근 가격(현재가 계산용)
  - `investment_price_daily`: 일별 close(차트용 히스토리)
- 오래된 일별 데이터는 `Settings.stock_price_prune_days` 기준으로 prune(삭제)합니다.

KIS 사용 시 핵심 포인트:

- tickers(프론트 표기 예: `005930.KS`)를 KIS 입력값(종목코드, 시장구분 등)으로 변환하는 로직이 필요합니다.
- KIS quote 호출 실패/누락 시에는 기존 캐시(`InvestmentPriceLatest`) 값을 유지하도록 “fail-safe” 처리가 필요합니다.

### 4.5 투자: trade 생성 시 현금 계정 정산(기존 거래/계좌와 연결)

`InvestmentService.create_trade(...)`는 buy/sell trade를 생성하고, 이후 **KIS 주문 체결 결과**에 따라 현금 정산을 반영하도록 설계합니다.

- 입력: `TradeCreate`에 `accountId`(선택) 포함
- 정산 대상 계좌 우선순위:
  1) 지정된 `accountId`가 있으면 해당 계좌
  2) 없으면 `Account.type == "investment"` 중 1개
  3) 없으면 `Account.type == "bank"` 중 1개
  4) 둘 다 없으면 404
- 주문 체결 기반 정산 로직(핵심):
  - buy:
    - (체결 시점) cash_delta = `-(체결금액 + 수수료)`
    - `transactions`에 type=`expense`, category=`투자` 기록
  - sell:
    - (체결 시점) cash_delta = `체결금액 - 수수료`
    - `transactions`에 type=`income`, category=`투자` 기록
- 정산 타이밍은 “주문 생성 시”가 아니라 “KIS 주문 체결/확정 시”로 이동하는 것이 목표입니다.
  - 이유: 부분체결/정정/취소 등 브로커 특성을 반영해야 실제 계정 잔액과 어긋나지 않습니다.

추가로 문서상 필수 데이터(향후 DB 스키마/모델에 반영 예정):
- broker order id (KIS 주문번호)
- 주문 상태(접수/체결/취소/실패)
- 체결 수량/체결 단가/수수료/체결 시각

---

## 5. DB 마이그레이션 현황(문서화)

본 문서에서 v1 고도화로 추가된 투자 가격 테이블은 다음과 같습니다.

- Alembic: `backend/alembic/versions/c7d9c2f1e3ab_add_investment_price_tables.py`
- 테이블:
  - `investment_price_latest`
  - `investment_price_daily`

---

## 6. 구현 관점 체크리스트(“이 문서가 맞는지”)

아래 항목 중 하나라도 실제 코드와 다르면 문서/구현이 어긋난 상태입니다.

1) 모든 엔드포인트가 `/v1` 프리픽스를 통해 호출되는가
2) 업로드 preview/transactions가 모두 `get_or_create_strategy` + `parse_*_smart` 경로를 사용하는가
3) 카테고리 보강이 `키워드 → 필요시 LLM` 순서로 동작하는가(LLM이 무조건 호출되지 않게 방어되는가)
4) 투자 holdings/currentPrice가 `InvestmentPriceLatest`를 참조하고, fallback이 있는가
5) price history가 `InvestmentPriceDaily.close`를 차트 필드로 변환해주는가
6) trade 생성 시 transactions ledger와 accounts.balance가 동기화되는가(캐시 정산)
7) 가격 갱신이 startup background loop에서 자동 실행되고, 수동 refresh 엔드포인트로도 트리거 가능한가

---

## 7. (중요) 현재 v1에서 “아직 없음”으로 문서에 명시할 것

아래 항목들은 “v1 고도화 목표(한국투자증권 OpenAPI 기반)”에 포함되지만, 현재 레포 코드 기준으로는 완전 구현이 아닙니다.

- KIS 기반 보유/잔고 동기화(holdings 구성에 KIS 데이터를 사용하는 단계)
- KIS 주문 생성 및 주문 상태/체결 이벤트 폴링(또는 웹훅) 기반 정산 트리거
- KIS 토큰/인증 정보 저장 및 갱신(브로커 OAuth 흐름)
- 프론트 ticker 표기(`005930.KS` 등) <-> KIS 입력값 변환(종목코드/시장구분 매핑)

참고: 현재 코드에는 가격 갱신 루프와 차트용 가격 테이블 구조가 존재하지만, 가격 공급원은 문서 목표(“KIS quote”)로 교체해야 합니다.

현재 v1의 투자 기능은 “trade 기록 + 현금 ledger 반영(정산 흐름 포함) + 가격 히스토리 제공”까지 형태가 갖춰져 있으며,
이 정산 흐름을 KIS 체결 기반으로 정확히 이동하는 것이 이번 v1 고도화의 핵심입니다.

---

## 8. (프론트엔드 연동 관점 요약)

v1 구현 중 사용자 화면에 반영된 핵심 UX/접근성 변경:

- `Upload.tsx`: 업로드/미리보기 작업 동안 전체 화면 overlay loading UI 표시(포인터 이벤트 비활성화 포함)
- `Reports.tsx`, `Dashboard.tsx`, `index.css`: WCAG 2.1을 고려한 차트 색상 팔레트(HSL 변수 사용)와 파이 구분선(stroke) 강화

