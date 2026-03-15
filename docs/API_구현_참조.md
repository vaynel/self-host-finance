# FinFlow 백엔드 API 구현 참조

> API 상세 스펙은 [frontend/docs/API정의서.md](../frontend/docs/API정의서.md)를 따릅니다.  
> 이 문서는 엔드포인트별 **라우트·인증·검증** 요약입니다.

---

## Base URL 및 공통 사항

- **Base URL**: `https://api.finflow.app/v1` (운영) / `http://localhost:3000/v1` (개발)
- **Content-Type**: `application/json`
- **인증**: `Authorization: Bearer <accessToken>` (인증 필요 API)
- **공통 응답**: `{ success, data, error, meta }` — 형식은 API정의서 §1 참조

---

## 라우트·인증·검증 요약

| 메서드 | 경로 | 인증 | 요청 검증 | 비고 |
|--------|------|------|-----------|------|
| POST | `/auth/login` | ❌ | email, password (필수, password 최소 8자) | JWT 발급 |
| POST | `/auth/register` | ❌ | email, password, name (필수, 비밀번호 정책) | 이메일 중복 체크 |
| POST | `/auth/refresh` | ❌ | refreshToken (필수) | 새 accessToken 발급 |
| POST | `/auth/logout` | ✅ | - | refreshToken 무효화 |
| GET | `/transactions` | ✅ | page, limit, type, category, account, startDate, endDate, search (모두 선택) | user_id 필터 필수 |
| GET | `/transactions/:id` | ✅ | id (path) | 본인 거래만 |
| POST | `/transactions` | ✅ | date, description, amount, type, category, account (필수), memo (선택) | type: income/expense/transfer |
| PUT | `/transactions/:id` | ✅ | body 동일 (일부 필드만 수정 가능) | 본인 거래만 |
| DELETE | `/transactions/:id` | ✅ | id (path) | 본인 거래만 |
| GET | `/accounts` | ✅ | - | 해당 user만 |
| POST | `/accounts` | ✅ | name, type, balance, institution (필수) | type: bank/investment |
| PUT | `/accounts/:id` | ✅ | name, type, balance, institution (선택) | 본인 계좌만 |
| DELETE | `/accounts/:id` | ✅ | id (path) | 본인 계좌만 |
| GET | `/accounts/:id/flow` | ✅ | period (선택, 7d/30d/90d/1y) | 해당 계좌 잔액 흐름 |
| GET | `/investments/holdings` | ✅ | - | 보유 종목 집계 |
| GET | `/investments/trades` | ✅ | ticker, action, startDate, endDate (선택) | action: buy/sell |
| GET | `/investments/prices/:ticker` | ✅ | period (선택) | 시세 조회 |
| POST | `/investments/trades` | ✅ | ticker, action, date, shares, price (필수), fee (선택) | action: buy/sell |
| GET | `/reports/monthly-summary` | ✅ | year (선택) | 월별 수입/지출/저축 |
| GET | `/reports/category-spending` | ✅ | month (선택, YYYY-MM) | 카테고리별 지출 |
| POST | `/upload/transactions` | ✅ | file (필수), accountId (필수), format (선택) | multipart/form-data |
| GET | `/settings` | ✅ | - | user_settings 조회 |
| PUT | `/settings` | ✅ | currency, language, notifications (선택) | 부분 수정 |

---

## ID 형식

- 사용자·거래·계좌·설정 등 식별자는 **문자열 ID** 사용 (예: `usr_abc123`, `txn_001`, `acc_001`).
- DB에서는 UUID 저장 후 접두어를 붙여 노출하거나, 그대로 UUID 문자열로 노출해도 됩니다 (API정의서 예시와 일치시키면 됨).

---

## 에러 코드

| HTTP | 의미 |
|------|------|
| 400 | 유효성 검증 실패 (body/query) |
| 401 | 토큰 없음/만료/위조 |
| 403 | 리소스에 대한 권한 없음 |
| 404 | 리소스 없음 |
| 500 | 서버 오류 |

응답 body의 `error.code`는 HTTP 상태 코드와 맞추고, `error.details`에 검증 오류 목록을 넣으면 됩니다.
