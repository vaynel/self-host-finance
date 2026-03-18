# FinFlow 백엔드 API 및 서비스 문서

> 최종 수정일: 2026-01-XX

이 문서는 FinFlow 백엔드의 모든 API 엔드포인트와 서비스 로직을 상세히 정리한 문서입니다.

---

## 목차

1. [개요](#개요)
2. [API 엔드포인트](#api-엔드포인트)
3. [서비스 레이어](#서비스-레이어)
4. [공통 사항](#공통-사항)

---

## 개요

### 기술 스택
- **프레임워크**: FastAPI
- **ORM**: SQLAlchemy
- **데이터베이스**: PostgreSQL
- **인증**: JWT (Access Token + Refresh Token)
- **문서화**: Swagger UI (`/docs`), ReDoc (`/redoc`)

### 프로젝트 구조
```
backend/app/
├── main.py                 # FastAPI 앱 진입점
├── routers/                # API 라우터
│   ├── auth.py
│   ├── transactions.py
│   ├── accounts.py
│   ├── investments.py
│   ├── reports.py
│   ├── upload.py
│   ├── settings.py
│   ├── category_keywords.py
│   └── parsing_strategies.py
├── services/               # 비즈니스 로직
│   ├── auth_service.py
│   ├── transaction_service.py
│   ├── account_service.py
│   ├── investment_service.py
│   ├── report_service.py
│   ├── upload_service.py
│   ├── settings_service.py
│   ├── category_registry.py
│   ├── category_classifier.py
│   ├── duplicate_detector.py
│   ├── llm_category_enricher.py
│   ├── parsing_strategy_service.py
│   └── ...
└── models/                # 데이터베이스 모델
```

### Base URL
- **개발**: `http://localhost:3000/v1`
- **운영**: `https://api.finflow.app/v1`

---

## API 엔드포인트

### 1. 인증 (Auth)

**라우터**: `app/routers/auth.py`  
**서비스**: `app/services/auth_service.py`

#### POST `/v1/auth/login`
사용자 로그인 및 토큰 발급

**요청 본문**:
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**응답**:
```json
{
  "success": true,
  "data": {
    "accessToken": "eyJ...",
    "refreshToken": "eyJ...",
    "expiresIn": 3600,
    "user": {
      "id": "usr_abc123",
      "email": "user@example.com",
      "name": "홍길동"
    }
  },
  "error": null,
  "meta": null
}
```

**서비스 함수**:
- `authenticate_user(db, email, password)`: 이메일/비밀번호 검증
- `create_access_token(user_id)`: Access Token 생성 (1시간 유효)
- `create_refresh_token(user_id)`: Refresh Token 생성 (7일 유효)
- `store_refresh_token(db, user_id, token)`: Refresh Token 저장

---

#### POST `/v1/auth/register`
신규 사용자 회원가입

**요청 본문**:
```json
{
  "email": "user@example.com",
  "password": "password123",
  "name": "홍길동"
}
```

**응답**: 로그인과 동일한 형식

**서비스 함수**:
- `register_user(db, email, password, name)`: 사용자 등록
  - 이메일 중복 체크
  - 비밀번호 해시화 (bcrypt)
  - 사용자 ID 생성 (`usr_` 접두어)

---

#### POST `/v1/auth/refresh`
Access Token 갱신

**요청 본문**:
```json
{
  "refreshToken": "eyJ..."
}
```

**응답**: 새로운 Access Token 포함

**서비스 함수**:
- `verify_refresh_token(db, token)`: Refresh Token 검증 및 사용자 반환
- `create_access_token(user_id)`: 새 Access Token 생성

---

#### POST `/v1/auth/logout`
로그아웃 (클라이언트에서 토큰 삭제)

**인증**: 필요

**응답**:
```json
{
  "success": true,
  "data": {
    "message": "로그아웃되었습니다."
  }
}
```

---

### 2. 거래 (Transactions)

**라우터**: `app/routers/transactions.py`  
**서비스**: `app/services/transaction_service.py`

#### GET `/v1/transactions`
거래 목록 조회 (필터링 및 페이지네이션)

**쿼리 파라미터**:
- `page` (int, 기본값: 1): 페이지 번호
- `limit` (int, 기본값: 20, 최대: 100): 페이지당 항목 수
- `type` (string, 선택): `income`, `expense`, `transfer`
- `category` (string, 선택): 카테고리명
- `account` (string, 선택): 계좌명
- `startDate` (string, 선택): 시작일 (YYYY-MM-DD)
- `endDate` (string, 선택): 종료일 (YYYY-MM-DD)
- `search` (string, 선택): 설명 검색

**응답**:
```json
{
  "success": true,
  "data": [
    {
      "id": "txn_abc123",
      "date": "2024-01-15",
      "description": "카페 결제",
      "amount": 5000,
      "type": "expense",
      "category": "카페",
      "account": "신한카드",
      "memo": ""
    }
  ],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 150
  }
}
```

**서비스 함수**:
- `list_transactions(db, user_id, page, limit, ...)`: 필터링된 거래 목록 반환
- `_txn_to_dict(t)`: Transaction 모델을 딕셔너리로 변환

---

#### GET `/v1/transactions/{txn_id}`
단일 거래 조회

**경로 파라미터**:
- `txn_id` (string): 거래 ID

**응답**: 단일 거래 객체

**서비스 함수**:
- `get_transaction(db, user_id, txn_id)`: 거래 조회

---

#### POST `/v1/transactions`
새 거래 생성

**요청 본문**:
```json
{
  "date": "2024-01-15",
  "description": "카페 결제",
  "amount": 5000,
  "type": "expense",
  "category": "카페",
  "account": "신한카드",
  "memo": "아메리카노"
}
```

**응답**: 생성된 거래 객체

**서비스 함수**:
- `create_transaction(db, user_id, data)`: 거래 생성
  - 거래 ID 생성 (`txn_` 접두어)
  - 금액을 Decimal로 변환

---

#### PUT `/v1/transactions/{txn_id}`
거래 수정

**요청 본문**: 부분 수정 가능 (모든 필드 선택)

**응답**: 수정된 거래 객체

**서비스 함수**:
- `update_transaction(db, user_id, txn_id, data)`: 거래 업데이트

---

#### DELETE `/v1/transactions/{txn_id}`
거래 삭제

**응답**:
```json
{
  "success": true,
  "data": {
    "message": "삭제되었습니다."
  }
}
```

**서비스 함수**:
- `delete_transaction(db, user_id, txn_id)`: 거래 삭제

---

### 3. 계좌 (Accounts)

**라우터**: `app/routers/accounts.py`  
**서비스**: `app/services/account_service.py`

#### GET `/v1/accounts`
계좌 목록 조회

**응답**:
```json
{
  "success": true,
  "data": [
    {
      "id": "acc_abc123",
      "name": "신한카드",
      "type": "bank",
      "balance": 1000000,
      "institution": "신한은행",
      "account_number": "1234-5678",
      "lastSync": "2024-01-15T10:00:00"
    }
  ]
}
```

**서비스 함수**:
- `list_accounts(db, user_id)`: 사용자 계좌 목록 반환
- `_acc_to_dict(a)`: Account 모델을 딕셔너리로 변환

---

#### GET `/v1/accounts/{account_id}`
단일 계좌 조회

**서비스 함수**:
- `get_account(db, user_id, account_id)`: 계좌 조회

---

#### GET `/v1/accounts/{account_id}/flow`
계좌 잔액 흐름 조회

**쿼리 파라미터**:
- `period` (string, 기본값: "30d"): 기간 (`7d`, `30d`, `90d`, `1y`)

**응답**:
```json
{
  "success": true,
  "data": {
    "accountId": "acc_abc123",
    "chartData": [
      {"date": "2024-01-01", "balance": 1000000},
      {"date": "2024-01-15", "balance": 950000}
    ]
  }
}
```

**서비스 함수**:
- `get_account_flow(db, user_id, account_id, period)`: 기간별 잔액 흐름 계산
  - 거래 내역을 날짜별로 그룹화
  - 역순으로 잔액 계산

---

#### POST `/v1/accounts`
새 계좌 생성

**요청 본문**:
```json
{
  "name": "신한카드",
  "type": "bank",
  "balance": 1000000,
  "institution": "신한은행",
  "account_number": "1234-5678"
}
```

**서비스 함수**:
- `create_account(db, user_id, data)`: 계좌 생성
  - 계좌 ID 생성 (`acc_` 접두어)

---

#### PUT `/v1/accounts/{account_id}`
계좌 수정

**서비스 함수**:
- `update_account(db, user_id, account_id, data)`: 계좌 업데이트

---

#### DELETE `/v1/accounts/{account_id}`
계좌 삭제

**서비스 함수**:
- `delete_account(db, user_id, account_id)`: 계좌 삭제

---

### 4. 투자 (Investments)

**라우터**: `app/routers/investments.py`  
**서비스**: `app/services/investment_service.py`

#### GET `/v1/investments/holdings`
보유 종목 집계

**응답**:
```json
{
  "success": true,
  "data": [
    {
      "ticker": "AAPL",
      "name": "Apple Inc.",
      "type": "stock",
      "shares": 10,
      "avgPrice": 150.00,
      "currentPrice": 150.00,
      "totalValue": 1500.00,
      "profitLoss": 0.00,
      "profitLossRate": 0.00
    }
  ]
}
```

**서비스 함수**:
- `get_holdings(db, user_id)`: 보유 종목 집계
  - 매수/매도 거래를 집계하여 보유 수량 계산
  - 평균 매수가 계산
  - 현재가 (현재는 평균가로 대체, 외부 API 연동 필요)

---

#### GET `/v1/investments/trades`
투자 거래 목록 조회

**쿼리 파라미터**:
- `ticker` (string, 선택): 종목 코드
- `action` (string, 선택): `buy`, `sell`
- `startDate` (string, 선택): 시작일
- `endDate` (string, 선택): 종료일

**서비스 함수**:
- `list_trades(db, user_id, ticker, action, start_date, end_date)`: 거래 목록 반환
- `_trade_to_dict(t)`: InvestmentTrade 모델을 딕셔너리로 변환

---

#### GET `/v1/investments/prices/{ticker}`
시세 조회 (현재는 빈 배열 반환)

**경로 파라미터**:
- `ticker` (string): 종목 코드

**쿼리 파라미터**:
- `period` (string, 선택): 기간

**응답**:
```json
{
  "success": true,
  "data": {
    "ticker": "AAPL",
    "prices": []
  }
}
```

**참고**: 외부 주식 시세 API 연동 필요

---

#### POST `/v1/investments/trades`
투자 거래 생성

**요청 본문**:
```json
{
  "ticker": "AAPL",
  "name": "Apple Inc.",
  "type": "stock",
  "action": "buy",
  "date": "2024-01-15",
  "shares": 10,
  "price": 150.00,
  "fee": 5.00
}
```

**서비스 함수**:
- `create_trade(db, user_id, data)`: 투자 거래 생성
  - 거래 ID 생성 (`trd_` 접두어)

---

### 5. 리포트 (Reports)

**라우터**: `app/routers/reports.py`  
**서비스**: `app/services/report_service.py`

#### GET `/v1/reports/monthly-summary`
월별 수입/지출/저축 요약

**쿼리 파라미터**:
- `year` (int, 선택): 연도 (기본값: 현재 연도)

**응답**:
```json
{
  "success": true,
  "data": [
    {
      "month": "2024-01",
      "income": 3000000,
      "expense": 2000000,
      "savings": 1000000,
      "savingsRate": 33.3
    }
  ]
}
```

**서비스 함수**:
- `monthly_summary(db, user_id, year)`: 월별 집계
  - 수입/지출을 월별로 그룹화
  - 저축률 계산

---

#### GET `/v1/reports/category-spending`
카테고리별 지출 분석

**쿼리 파라미터**:
- `month` (string, 선택): 월 (YYYY-MM, 기본값: 현재 월)

**응답**:
```json
{
  "success": true,
  "data": [
    {
      "category": "식료품",
      "amount": 500000
    },
    {
      "category": "카페",
      "amount": 100000
    }
  ]
}
```

**서비스 함수**:
- `category_spending(db, user_id, month)`: 카테고리별 지출 집계

---

### 6. 업로드 (Upload)

**라우터**: `app/routers/upload.py`  
**서비스**: `app/services/upload_service.py`, `app/services/smart_upload_parser.py`

#### POST `/v1/upload/preview`
거래 내역 파일 미리보기 (임포트 전)

**요청**: `multipart/form-data`
- `file` (file, 필수): CSV/XLSX 파일
- `format` (string, 선택): `csv`, `xlsx`, `xls` (자동 감지)
- `accountId` (string, 선택): 계좌 ID

**응답**:
```json
{
  "success": true,
  "data": {
    "rows": [
      {
        "row": 1,
        "date": "2024-01-15",
        "description": "카페 결제",
        "amount": 5000,
        "type": "expense",
        "category": "카페",
        "account": "신한카드",
        "memo": ""
      }
    ],
    "column_mapping": {
      "date": 0,
      "description": 1,
      "amount": 2
    },
    "total": 10
  }
}
```

**주요 기능**:
- 스마트 파싱 (LLM 기반 컬럼 매핑 추론)
- 자동 타입/카테고리 분류
- LLM을 통한 카테고리 자동 등록

**서비스 함수**:
- `parse_csv_smart(content, index_mapping_override)`: CSV 스마트 파싱
- `parse_xlsx_smart(content, index_mapping_override)`: XLSX 스마트 파싱
- `parse_xls_smart(content, index_mapping_override)`: XLS 스마트 파싱
- `get_or_create_strategy(db, user_id, headers, samples)`: 파싱 전략 생성/조회
- `enrich_categories_for_rows(db, user_id, rows)`: LLM 기반 카테고리 보강

---

#### POST `/v1/upload/transactions`
거래 내역 파일 임포트

**요청**: `multipart/form-data`
- `file` (file, 필수): CSV/XLSX 파일
- `accountId` (string, 필수): 계좌 ID
- `format` (string, 선택): 파일 형식
- `skipDuplicates` (bool, 기본값: true): 중복 건너뛰기
- `toleranceDays` (int, 기본값: 0): 중복 검사 날짜 허용 범위

**응답**:
```json
{
  "success": true,
  "data": {
    "imported": 50,
    "skipped": 5,
    "duplicates": 3,
    "errors": [],
    "column_mapping": {...}
  }
}
```

**서비스 함수**:
- `import_transactions(db, user_id, rows, account_name, ...)`: 거래 임포트
  - 자동 분류 (타입/카테고리)
  - 중복 검사 (`is_duplicate_transaction`)
  - 에러 처리

---

### 7. 설정 (Settings)

**라우터**: `app/routers/settings.py`  
**서비스**: `app/services/settings_service.py`

#### GET `/v1/settings`
사용자 설정 조회

**응답**:
```json
{
  "success": true,
  "data": {
    "currency": "KRW",
    "language": "ko",
    "notifications": true
  }
}
```

**서비스 함수**:
- `get_settings(db, user_id)`: 설정 조회 (없으면 기본값 생성)

---

#### PUT `/v1/settings`
사용자 설정 업데이트

**요청 본문**:
```json
{
  "currency": "USD",
  "language": "en",
  "notifications": false
}
```

**서비스 함수**:
- `update_settings(db, user_id, data)`: 설정 업데이트

---

### 8. 카테고리 키워드 (Category Keywords)

**라우터**: `app/routers/category_keywords.py`

#### GET `/v1/category-keywords`
카테고리 키워드 목록 조회

**쿼리 파라미터**:
- `category` (string, 선택): 카테고리 필터

**응답**:
```json
{
  "success": true,
  "data": {
    "식료품": [
      {
        "id": "kw_abc123",
        "keyword": "마트",
        "priority": "high",
        "created_at": "2024-01-15T10:00:00"
      }
    ]
  }
}
```

---

#### POST `/v1/category-keywords`
카테고리 키워드 생성

**요청 본문**:
```json
{
  "category": "식료품",
  "keyword": "마트",
  "priority": "high"
}
```

**우선순위**: `high`, `normal`, `low`

---

#### PUT `/v1/category-keywords/{keyword_id}`
카테고리 키워드 수정

---

#### DELETE `/v1/category-keywords/{keyword_id}`
카테고리 키워드 삭제

---

#### GET `/v1/category-keywords/categories`
키워드가 있는 카테고리 목록

---

### 9. 파싱 전략 (Parsing Strategies)

**라우터**: `app/routers/parsing_strategies.py`  
**서비스**: `app/services/parsing_strategy_service.py`

#### GET `/v1/parsing-strategies`
파싱 전략 목록 조회

**응답**:
```json
{
  "success": true,
  "data": [
    {
      "id": "str_abc123",
      "fingerprint": "sha256...",
      "provider": "groq",
      "model": "llama-3.1-70b-versatile",
      "prompt_version": "v1",
      "created_at": "2024-01-15T10:00:00",
      "updated_at": "2024-01-15T10:00:00"
    }
  ]
}
```

**서비스 함수**:
- `compute_fingerprint(headers, sample_rows)`: 파일 형식 핑거프린트 계산
- `get_or_create_strategy(db, user_id, headers, samples)`: 전략 조회/생성
- `infer_strategy_with_llm(headers, sample_rows)`: LLM을 통한 전략 추론

---

#### GET `/v1/parsing-strategies/{strategy_id}`
파싱 전략 상세 조회

**응답**:
```json
{
  "success": true,
  "data": {
    "id": "str_abc123",
    "fingerprint": "...",
    "mapping": {
      "date": "거래일자",
      "description": "적요",
      "amount": "거래금액"
    },
    "rules": {
      "amount": {"mode": "amount"},
      "date": {"formats": ["%Y-%m-%d"]}
    },
    "header": ["거래일자", "적요", "거래금액"],
    "examples": [...]
  }
}
```

---

#### DELETE `/v1/parsing-strategies/{strategy_id}`
파싱 전략 삭제

---

### 10. 헬스 체크

#### GET `/health`
서버 상태 확인

**응답**:
```json
{
  "status": "ok"
}
```

---

## 서비스 레이어

### 1. 인증 서비스 (`auth_service.py`)

#### 주요 함수

**`register_user(db, email, password, name)`**
- 신규 사용자 등록
- 이메일 중복 체크
- 비밀번호 해시화 (bcrypt)
- 사용자 ID 생성 (`usr_` 접두어)

**`authenticate_user(db, email, password)`**
- 이메일/비밀번호 검증
- 사용자 반환 또는 None

**`store_refresh_token(db, user_id, token)`**
- Refresh Token을 DB에 저장
- 만료 시간: 7일

**`verify_refresh_token(db, token)`**
- Refresh Token 검증
- DB에 저장된 토큰과 일치 여부 확인
- 사용자 반환 또는 None

**`invalidate_refresh_token(db, token)`**
- Refresh Token 무효화 (로그아웃)

---

### 2. 거래 서비스 (`transaction_service.py`)

#### 주요 함수

**`list_transactions(db, user_id, page, limit, ...)`**
- 필터링된 거래 목록 반환
- 페이지네이션 지원
- 필터: 타입, 카테고리, 계좌, 날짜 범위, 검색어

**`get_transaction(db, user_id, txn_id)`**
- 단일 거래 조회

**`create_transaction(db, user_id, data)`**
- 거래 생성
- 금액을 Decimal로 변환
- 날짜를 date 객체로 변환

**`update_transaction(db, user_id, txn_id, data)`**
- 거래 업데이트 (부분 수정 지원)

**`delete_transaction(db, user_id, txn_id)`**
- 거래 삭제

---

### 3. 계좌 서비스 (`account_service.py`)

#### 주요 함수

**`list_accounts(db, user_id)`**
- 사용자 계좌 목록 반환

**`get_account(db, user_id, account_id)`**
- 단일 계좌 조회

**`create_account(db, user_id, data)`**
- 계좌 생성
- 계좌 ID 생성 (`acc_` 접두어)

**`update_account(db, user_id, account_id, data)`**
- 계좌 업데이트

**`delete_account(db, user_id, account_id)`**
- 계좌 삭제

**`get_account_flow(db, user_id, account_id, period)`**
- 계좌 잔액 흐름 계산
- 기간별 거래 내역 집계
- 역순으로 잔액 계산

---

### 4. 투자 서비스 (`investment_service.py`)

#### 주요 함수

**`get_holdings(db, user_id)`**
- 보유 종목 집계
- 매수/매도 거래를 집계하여 보유 수량 계산
- 평균 매수가 계산
- 손익 계산 (현재가는 평균가로 대체)

**`list_trades(db, user_id, ticker, action, start_date, end_date)`**
- 투자 거래 목록 조회
- 필터: 종목, 거래 유형, 날짜 범위

**`create_trade(db, user_id, data)`**
- 투자 거래 생성
- 거래 ID 생성 (`trd_` 접두어)

---

### 5. 리포트 서비스 (`report_service.py`)

#### 주요 함수

**`monthly_summary(db, user_id, year)`**
- 월별 수입/지출/저축 요약
- SQL 집계 함수 사용
- 저축률 계산

**`category_spending(db, user_id, month)`**
- 카테고리별 지출 분석
- 특정 월의 지출을 카테고리별로 집계

---

### 6. 업로드 서비스 (`upload_service.py`)

#### 주요 함수

**`import_transactions(db, user_id, rows, account_name, ...)`**
- 거래 내역 임포트
- 자동 분류 (타입/카테고리)
- 중복 검사
- 에러 처리

**파라미터**:
- `auto_classify` (bool): 자동 분류 여부
- `skip_duplicates` (bool): 중복 건너뛰기
- `tolerance_days` (int): 중복 검사 날짜 허용 범위

**반환값**:
```python
{
  "imported": int,      # 임포트된 건수
  "skipped": int,       # 건너뛴 건수
  "duplicates": int,    # 중복 건수
  "errors": list        # 에러 목록
}
```

---

### 7. 설정 서비스 (`settings_service.py`)

#### 주요 함수

**`get_settings(db, user_id)`**
- 사용자 설정 조회
- 없으면 기본값으로 생성

**`update_settings(db, user_id, data)`**
- 사용자 설정 업데이트
- 부분 수정 지원

---

### 8. 카테고리 레지스트리 (`category_registry.py`)

#### 주요 함수

**`list_registered_categories(db, user_id)`**
- 사용자 등록 카테고리 목록 반환
- DB 카테고리 + 키워드 카테고리 + 기본 카테고리 병합
- 중복 제거 (대소문자 무시)

**기본 카테고리**:
```python
["식료품", "카페", "교통", "쇼핑", "구독", "주거", "의료", "교육", "운동", "배달", "편의점", "기타"]
```

**`ensure_category(db, user_id, name)`**
- 카테고리가 존재하는지 확인하고 없으면 생성
- 반환값: True (생성됨), False (이미 존재)

---

### 9. 카테고리 분류기 (`category_classifier.py`)

#### 주요 함수

**`auto_classify_category(db, user_id, description, amount)`**
- 설명과 금액을 기반으로 카테고리 자동 분류
- 키워드 기반 매칭 (우선순위 고려)
- 금액 기반 폴백 (50만원 이상 → "주거")

**`auto_detect_type(amount, description)`**
- 거래 타입 자동 감지 (`income`, `expense`)
- 금액 부호 기반
- 설명 키워드 기반

**`get_category_keywords(db, user_id)`**
- 사용자의 카테고리 키워드 조회
- 카테고리별로 그룹화
- 우선순위 정렬

---

### 10. 중복 검사 (`duplicate_detector.py`)

#### 주요 함수

**`is_duplicate_transaction(db, user_id, txn_date, amount, description, account, tolerance_days)`**
- 거래 중복 여부 확인
- 매칭 조건:
  - 금액 일치
  - 계좌 일치
  - 날짜 일치 (또는 허용 범위 내)
  - 설명 유사 (포함 관계)

**`find_duplicate_transactions(db, user_id, rows, account_name, tolerance_days)`**
- 임포트할 거래 목록에서 중복 찾기
- 중복된 행의 인덱스와 정보 반환

---

### 11. LLM 카테고리 보강 (`llm_category_enricher.py`)

#### 주요 함수

**`enrich_categories_for_rows(db, user_id, rows, groq=None)`**
- LLM을 사용하여 카테고리 자동 보강
- 처리 순서:
  1. 이미 등록된 카테고리가 있으면 유지
  2. 키워드 기반 분류 시도
  3. LLM으로 분류 요청
  4. 새로운 카테고리 자동 등록

**반환값**: `(llm_calls, new_categories_created)`

**특징**:
- 요청 내 캐싱으로 중복 LLM 호출 방지
- 등록된 카테고리 우선 사용
- 새로운 카테고리 자동 등록

---

### 12. 파싱 전략 서비스 (`parsing_strategy_service.py`)

#### 주요 함수

**`compute_fingerprint(headers, sample_rows)`**
- 파일 형식 핑거프린트 계산 (SHA256)
- 헤더 + 샘플 행 기반

**`get_or_create_strategy(db, user_id, headers, samples)`**
- 파싱 전략 조회 또는 생성
- 핑거프린트로 기존 전략 매칭
- 없으면 LLM으로 전략 추론

**`infer_strategy_with_llm(headers, sample_rows)`**
- LLM을 사용하여 파싱 전략 추론
- 컬럼 매핑 및 파싱 규칙 생성

**`mapping_to_index_map(headers, mapping)`**
- 컬럼명 기반 매핑을 인덱스 매핑으로 변환

---

## 공통 사항

### 응답 형식

모든 API는 다음 형식을 따릅니다:

```json
{
  "success": boolean,
  "data": any,
  "error": {
    "code": number,
    "message": string,
    "details": array
  } | null,
  "meta": object | null
}
```

**성공 응답**:
```json
{
  "success": true,
  "data": {...},
  "error": null,
  "meta": {...}
}
```

**에러 응답**:
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": 400,
    "message": "유효성 검증 실패",
    "details": ["field: error message"]
  },
  "meta": null
}
```

---

### 인증

대부분의 API는 JWT 인증이 필요합니다.

**헤더**:
```
Authorization: Bearer <accessToken>
```

**의존성**:
- `get_current_user`: 현재 사용자 조회
- 인증 실패 시 401 에러 반환

---

### 에러 코드

| HTTP 코드 | 의미 |
|-----------|------|
| 400 | 유효성 검증 실패 |
| 401 | 인증 실패 (토큰 없음/만료/위조) |
| 403 | 권한 없음 |
| 404 | 리소스 없음 |
| 500 | 서버 내부 오류 |

---

### ID 형식

- **사용자**: `usr_` + 12자리 hex
- **거래**: `txn_` + 12자리 hex
- **계좌**: `acc_` + 12자리 hex
- **투자 거래**: `trd_` + 12자리 hex
- **카테고리 키워드**: `kw_` + 12자리 hex
- **파싱 전략**: `str_` + 12자리 hex

---

### 데이터베이스 모델

주요 모델:
- `User`: 사용자
- `RefreshToken`: 리프레시 토큰
- `Transaction`: 거래
- `Account`: 계좌
- `InvestmentTrade`: 투자 거래
- `UserSettings`: 사용자 설정
- `Category`: 카테고리
- `CategoryKeyword`: 카테고리 키워드
- `ParsingStrategy`: 파싱 전략

---

### CORS 설정

- **개발 환경**: 모든 Origin 허용 (`allow_origin_regex=".*"`)
- **운영 환경**: 설정된 Origin만 허용

---

### 미들웨어

- **CORS Middleware**: CORS 처리
- **Debug Middleware**: 요청/응답 로깅 (개발 환경)

---

## 참고 문서

- [API 정의서](../frontend/docs/API정의서.md)
- [API 구현 참조](./API_구현_참조.md)
- [백엔드 개발 문서](./백엔드_개발문서.md)
