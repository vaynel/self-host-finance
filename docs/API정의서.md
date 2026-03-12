# FinFlow API 정의서

> 버전: 1.0.0  
> 최종 수정일: 2026-03-12  
> 작성자: FinFlow 개발팀

---

## 1. 개요

FinFlow는 개인 재무 관리 플랫폼으로, 아래 API를 통해 거래 내역, 계좌, 투자, 리포트 데이터를 관리합니다.

### 기본 정보
| 항목 | 값 |
|------|-----|
| Base URL | `https://api.finflow.app/v1` |
| 인증 방식 | Bearer Token (JWT) |
| 응답 형식 | JSON |
| 문자 인코딩 | UTF-8 |

### 공통 응답 형식
```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 100
  }
}
```

### 공통 에러 코드
| 코드 | 설명 |
|------|------|
| 400 | 잘못된 요청 (유효성 검증 실패) |
| 401 | 인증 실패 (토큰 만료/미제공) |
| 403 | 권한 없음 |
| 404 | 리소스를 찾을 수 없음 |
| 500 | 서버 내부 오류 |

---

## 2. 인증 API

### 2.1 로그인
```
POST /auth/login
```

**요청 본문:**
| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| email | string | ✅ | 사용자 이메일 |
| password | string | ✅ | 비밀번호 (최소 8자) |

**응답 (200):**
```json
{
  "success": true,
  "data": {
    "accessToken": "eyJhbGci...",
    "refreshToken": "dGhpcyBp...",
    "expiresIn": 3600,
    "user": {
      "id": "usr_abc123",
      "email": "user@example.com",
      "name": "홍길동"
    }
  }
}
```

### 2.2 회원가입
```
POST /auth/register
```

**요청 본문:**
| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| email | string | ✅ | 사용자 이메일 |
| password | string | ✅ | 비밀번호 (최소 8자, 영문+숫자+특수문자) |
| name | string | ✅ | 사용자 이름 |

### 2.3 토큰 갱신
```
POST /auth/refresh
```

**요청 본문:**
| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| refreshToken | string | ✅ | 리프레시 토큰 |

### 2.4 로그아웃
```
POST /auth/logout
```
> Authorization 헤더에 Bearer Token 필요

---

## 3. 거래 내역 API

### 3.1 거래 목록 조회
```
GET /transactions
```

**쿼리 파라미터:**
| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| page | number | - | 페이지 번호 (기본: 1) |
| limit | number | - | 페이지당 항목 수 (기본: 20, 최대: 100) |
| type | string | - | 거래 유형 필터 (`income`, `expense`, `transfer`) |
| category | string | - | 카테고리 필터 |
| account | string | - | 계좌명 필터 |
| startDate | string | - | 시작 날짜 (YYYY-MM-DD) |
| endDate | string | - | 종료 날짜 (YYYY-MM-DD) |
| search | string | - | 거래 내용 검색어 |

**응답 (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": "txn_001",
      "date": "2026-03-11",
      "description": "월급",
      "amount": 4500000,
      "type": "income",
      "category": "급여",
      "account": "국민은행",
      "memo": ""
    }
  ]
}
```

### 3.2 거래 상세 조회
```
GET /transactions/:id
```

### 3.3 거래 등록
```
POST /transactions
```

**요청 본문:**
| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| date | string | ✅ | 거래 날짜 (YYYY-MM-DD) |
| description | string | ✅ | 거래 내용 |
| amount | number | ✅ | 거래 금액 (지출은 음수) |
| type | string | ✅ | `income` / `expense` / `transfer` |
| category | string | ✅ | 카테고리 |
| account | string | ✅ | 계좌명 |
| memo | string | - | 메모 |

### 3.4 거래 수정
```
PUT /transactions/:id
```

### 3.5 거래 삭제
```
DELETE /transactions/:id
```

---

## 4. 계좌 API

### 4.1 계좌 목록 조회
```
GET /accounts
```

**응답 (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": "acc_001",
      "name": "국민은행 주거래",
      "type": "bank",
      "balance": 8500000,
      "institution": "KB국민은행",
      "lastSync": "2026-03-11T09:30:00Z"
    }
  ]
}
```

### 4.2 계좌 등록
```
POST /accounts
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| name | string | ✅ | 계좌 별칭 |
| type | string | ✅ | `bank` / `investment` |
| balance | number | ✅ | 현재 잔액 |
| institution | string | ✅ | 금융기관명 |

### 4.3 계좌 수정
```
PUT /accounts/:id
```

### 4.4 계좌 삭제
```
DELETE /accounts/:id
```

### 4.5 계좌별 거래 흐름 조회
```
GET /accounts/:id/flow
```

**쿼리 파라미터:**
| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| period | string | - | `7d`, `30d`, `90d`, `1y` (기본: 30d) |

**응답 (200):**
```json
{
  "success": true,
  "data": {
    "accountId": "acc_001",
    "chartData": [
      { "date": "2026-03-01", "balance": 5200000 },
      { "date": "2026-03-05", "balance": 4700000 }
    ]
  }
}
```

---

## 5. 투자 API

### 5.1 보유 종목 조회
```
GET /investments/holdings
```

**응답 (200):**
```json
{
  "success": true,
  "data": [
    {
      "ticker": "005930",
      "name": "삼성전자",
      "type": "stock",
      "shares": 50,
      "avgPrice": 58000,
      "currentPrice": 59200,
      "totalValue": 2960000,
      "profitLoss": 60000,
      "profitLossRate": 2.07
    }
  ]
}
```

### 5.2 거래 내역 조회
```
GET /investments/trades
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| ticker | string | - | 종목 코드 필터 |
| action | string | - | `buy` / `sell` |
| startDate | string | - | 시작 날짜 |
| endDate | string | - | 종료 날짜 |

### 5.3 종목 시세 조회
```
GET /investments/prices/:ticker
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| period | string | - | `7d`, `30d`, `90d`, `1y` |

### 5.4 매매 등록
```
POST /investments/trades
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| ticker | string | ✅ | 종목 코드 |
| action | string | ✅ | `buy` / `sell` |
| date | string | ✅ | 거래 날짜 |
| shares | number | ✅ | 수량 |
| price | number | ✅ | 단가 |
| fee | number | - | 수수료 |

---

## 6. 리포트 API

### 6.1 월별 수입/지출 요약
```
GET /reports/monthly-summary
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| year | number | - | 연도 (기본: 현재 연도) |

**응답 (200):**
```json
{
  "success": true,
  "data": [
    {
      "month": "2026-03",
      "income": 4535000,
      "expense": 1470700,
      "savings": 3064300,
      "savingsRate": 67.6
    }
  ]
}
```

### 6.2 카테고리별 지출
```
GET /reports/category-spending
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| month | string | - | 대상 월 (YYYY-MM) |

---

## 7. 데이터 업로드 API

### 7.1 CSV/Excel 파일 업로드
```
POST /upload/transactions
Content-Type: multipart/form-data
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| file | File | ✅ | CSV 또는 XLSX 파일 |
| accountId | string | ✅ | 대상 계좌 ID |
| format | string | - | 파일 형식 (`csv`, `xlsx`) |

**응답 (200):**
```json
{
  "success": true,
  "data": {
    "imported": 45,
    "skipped": 2,
    "errors": []
  }
}
```

---

## 8. 설정 API

### 8.1 사용자 설정 조회
```
GET /settings
```

### 8.2 사용자 설정 수정
```
PUT /settings
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| currency | string | - | 기본 통화 (`KRW`, `USD`) |
| language | string | - | 언어 설정 (`ko`, `en`) |
| notifications | object | - | 알림 설정 |
