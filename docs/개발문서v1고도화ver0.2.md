# FinFlow 개발문서 v1 고도화 ver0.2

이 문서는 `개발문서v1고도화..md`의 투자 설계 의도를 기준으로, **현재 시스템이 어디까지 구현되어 있는지 평가**하고, **구현되지 않은 항목은 어떻게 구현할지**를 정리한 투자 관점의 갭 분석 및 실행 문서입니다.

핵심 목표는 다음 두 가지입니다.

1. 지금 투자 기능이 “문서상 목표” 대비 실제로 어느 수준까지 구현되었는지 객관적으로 평가한다.
2. 미구현/부분구현 항목에 대해 한국투자증권 OpenAPI(KIS) 중심으로 구현 방향을 정의한다.

---

## 1. 평가 기준

본 문서는 기존 `개발문서v1고도화..md`의 다음 항목을 평가 기준으로 사용합니다.

- `4.2 주식 계좌 요구사항`
- `4.3 자동매매 요구사항`
- `6. 주식계좌 설계`
- `9. 데이터 모델 설계` 중 `stock_account_detail`, `stock_holding`, `stock_price_snapshot`, `auto_trade_rule`, `stock_order_log`
- `10. API 설계 초안` 중 주식 계좌/자동매매 API
- `11. 스케줄러 설계`
- `12. 한국투자증권 연동 설계`

---

## 2. 현재 구현 요약

현재 레포의 투자 기능은 다음 수준까지 구현되어 있습니다.

- 투자 거래(`InvestmentTrade`)를 직접 기록할 수 있다.
- 매수/매도 기록을 합산하여 보유 종목(`holdings`)을 계산할 수 있다.
- 최근 가격(`investment_price_latest`)과 일별 가격(`investment_price_daily`)을 저장할 수 있다.
- 주기적 가격 갱신 루프가 존재한다.
- 매수/매도 기록 생성 시 일반 계좌(`accounts.balance`)와 거래원장(`transactions`)에 현금 정산을 반영한다.

하지만 아래는 아직 구현되지 않았습니다.

- 한국투자증권 OpenAPI 인증/토큰 관리
- 한국투자증권 보유 종목/예수금/주문 가능 금액 동기화
- 한국투자증권 주문 실행/체결 조회
- 체결 기반 정산
- 자동매매 규칙/실행/주문 로그
- 투자계좌 전용 상세 모델(브로커 구분, 실전/모의, API 가능 여부 등)

즉, **현재 시스템은 “수동 투자 기록 + 가격 캐시 + 현금원장 연동” 수준**이며, **“증권사 연동 투자관리”는 아직 완성되지 않았다**고 평가할 수 있습니다.

---

## 3. 투자 관점 구현 평가

### 3.1 요구사항별 평가표

| 항목 | 기존 문서 목표 | 현재 상태 | 평가 |
|---|---|---|---|
| 주식 계좌 등록 | 주식 계좌 등록 가능 | `accounts.type = investment`로 등록 가능하나, 브로커 전용 상세 정보 없음 | 부분 구현 |
| 증권사 구분 | KIS / MANUAL / OTHER 구분 | `Account`에 `broker_type` 없음 | 미구현 |
| 연동 가능 여부 표시 | API 연동 여부 저장/표시 | `api_enabled`, `order_enabled`, `auto_trade_enabled` 없음 | 미구현 |
| 보유 종목 조회 | 계좌별 holdings 조회 | `InvestmentTrade` 집계로 보유 수량 계산 가능 | 부분 구현 |
| 평균단가/평가손익 조회 | 종목별 조회 가능 | `get_holdings()`에서 계산 가능 | 구현 |
| 현재가 조회 | 실시간/주기적 현재가 조회 | 가능하나 현재는 KIS가 아니라 외부 price provider 기반 | 부분 구현 |
| 1분 주기 가격 갱신 | 1분 주기 시세 갱신 | 현재 기본 10분 주기, KIS 아님 | 부분 구현 |
| 자동매매 옵션 | 계좌별 활성/비활성 | 관련 모델/필드/API 없음 | 미구현 |
| 목표가/손절가/분할매도 | 규칙 저장 및 실행 | 관련 모델/API/스케줄러 없음 | 미구현 |
| 주문 실행 결과/실패 로그 | 주문/체결 로그 기록 | 관련 모델 없음 | 미구현 |
| 주문 전 보유 수량 검증 | 브로커 주문 전 검증 | 브로커 연동 자체 없음 | 미구현 |
| 주문 후 체결 상태 확인 | 체결 조회 및 반영 | 체결 조회 없음 | 미구현 |
| 실패 시 로그/알림 | 오류 추적 및 알림 | 일부 서버 로그만 존재, 주문 알림 체계 없음 | 미구현 |
| KIS OAuth 토큰 | 토큰 발급/갱신 관리 | 설정/모델/서비스 없음 | 미구현 |
| KIS 보유/잔고 동기화 | 브로커 데이터 기준 holdings/balance | 현재는 로컬 trade 기준 | 미구현 |
| 체결 기반 현금 정산 | 주문 체결 후 cash ledger 반영 | 현재는 trade 생성 즉시 반영 | 부분 구현 |

### 3.2 현재 구현에서 긍정적으로 볼 부분

현재 구조가 완전히 버려야 하는 상태는 아닙니다. 다음 요소는 KIS 연동형 투자관리로 확장할 때 재사용할 수 있습니다.

- `investment_trades` 테이블: 사용자 거래 이력을 유지하는 기본 원장으로 활용 가능
- `investment_price_latest`, `investment_price_daily`: 현재가/차트 이력 저장 구조는 유지 가능
- `/v1/investments/holdings`, `/v1/investments/trades`, `/v1/investments/prices/{ticker}`: API 골격은 유지 가능
- `create_trade()`의 현금 원장 연동 구조: “체결 이벤트 기반 정산”으로 시점만 바꾸면 재사용 가능

즉, **API 뼈대와 일부 테이블은 살리고**, **브로커 연동 계층과 투자계좌 상세 모델을 추가하는 방식이 적절**합니다.

---

## 4. 현재 코드 기준 상세 평가

### 4.1 투자계좌 모델 관점

현재 `Account` 모델은 아래 필드만 가집니다.

- `id`
- `user_id`
- `name`
- `type` (`bank`, `investment`)
- `balance`
- `institution`
- `account_number`
- `last_sync`

문제는 다음과 같습니다.

- 투자계좌와 일반계좌가 동일 모델에 단순히 `type`만 다르게 저장된다.
- 한국투자증권 연동에 필요한 `broker_type`, `api_enabled`, `mock/live`, `broker_account_no`, `can_place_order`, `can_sync_balance` 같은 정보가 없다.
- 따라서 “투자계좌를 등록했다”는 의미가 현재는 단순 문자열 구분에 가깝다.

평가:

- 일반적인 계좌 CRUD는 구현
- 브로커 연동형 투자계좌 설계는 미구현

### 4.2 보유 종목 계산 관점

현재 `get_holdings()`는 `InvestmentTrade`를 날짜순으로 읽어 직접 합산합니다.

장점:

- 평균단가 계산 가능
- 매도 시 원가 감소 로직이 포함되어 있음
- 최신 가격 캐시가 있으면 손익 계산 가능

한계:

- 한국투자증권 실제 잔고와 다를 수 있다.
- 타 시스템에서 체결된 주문, 배당입고, 액면분할, 권리락, 수수료 상세 등 브로커 데이터를 반영하지 못한다.
- “계좌별 holdings”가 아니라 “사용자 전체 ticker별 합산”에 가깝다.

평가:

- 수동 투자장부 기준 포트폴리오 계산은 구현
- 브로커 기준 holdings 동기화는 미구현

### 4.3 가격 갱신 관점

현재는 `investment_price_updater.py`가 별도 루프로 동작하며, `stock_price_provider.py`의 provider를 통해 가격을 가져옵니다.

현재 상태:

- 주기 실행: 구현
- DB 저장: 구현
- 수동 refresh API: 구현
- 공급원: `stooq`
- KIS quote 연동: 미구현

한계:

- 한국시장 종목코드 체계(`005930`, `A005930`, 시장구분 등)를 정식으로 처리하지 않음
- 종목 메타데이터/시장구분/호가 단위 등 브로커 정보가 없음
- 프론트 표기 ticker와 브로커 API 입력값 변환 규칙이 없음

평가:

- 가격 캐시 파이프라인은 구현
- KIS 기반 가격 동기화는 미구현

### 4.4 주문/정산 관점

현재 `create_trade()`는 사용자가 `buy`/`sell` trade를 생성하면 즉시 다음을 수행합니다.

1. `investment_trades`에 거래 저장
2. `transactions`에 투자 카테고리 원장 생성
3. `accounts.balance` 증감 반영

문제:

- 현재는 “주문 생성”과 “체결 확정”이 구분되지 않는다.
- 실제 브로커 환경에서는 접수/부분체결/정정/취소/거부가 존재한다.
- 따라서 지금 방식은 KIS 주문 연동 시 그대로 사용하면 실제 계좌 잔액과 어긋날 수 있다.

평가:

- 현금 정산 로직 자체는 구현
- 체결 기반 정산으로의 분리는 미구현

### 4.5 자동매매 관점

기존 문서의 핵심 목표였던 자동매매 관련 구성은 현재 코드에 존재하지 않습니다.

없는 것:

- 규칙 모델
- 규칙 CRUD API
- 계좌별 자동매매 활성화 필드
- 장중 체크
- 중복 주문 방지 락
- 주문/체결 상태 추적
- 실패 알림

평가:

- 자동매매는 미구현

---

## 5. 결론: 지금 투자 기능은 어디까지인가

현재 시스템의 투자 기능을 한 문장으로 정리하면 다음과 같습니다.

**“사용자가 직접 입력한 투자 거래를 기준으로 포트폴리오와 현금 흐름을 계산하고, 외부 가격 소스를 캐시해 화면에 보여주는 수준”**

따라서 투자 관점에서 요구하는 “한국투자증권 계좌를 실제로 연결하고, 보유 종목/예수금/주문/체결/정산을 브로커 기준으로 관리하는 시스템”은 아직 완성되지 않았습니다.

현재 구현 상태를 투자 서비스 maturity로 분류하면:

- Level 1: 수동 투자장부 + 평가손익 계산 -> 구현
- Level 2: 외부 가격 캐시/차트 -> 구현
- Level 3: 브로커 잔고/예수금 동기화 -> 미구현
- Level 4: 브로커 주문/체결 연동 -> 미구현
- Level 5: 자동매매/리스크 제어 -> 미구현

---

## 6. 미구현 항목은 어떻게 구현할 것인가

### 6.1 구현 원칙

1. 기존 `/v1/investments` API 골격은 최대한 유지한다.
2. 내부 구현은 “수동 기록 중심”에서 “브로커 연동 중심”으로 이동한다.
3. 주문과 체결을 분리한다.
4. 현금 정산은 반드시 체결 이벤트 기준으로 반영한다.
5. holdings는 장기적으로 `InvestmentTrade` 합산이 아니라 “KIS 동기화 결과 + 내부 보정” 구조로 이동한다.

### 6.2 1단계: 투자계좌 모델 확장

추가 대상:

- `investment_account_detail` 또는 `broker_account` 테이블 신설
- 필수 컬럼 예시
  - `account_id`
  - `broker_type` (`KIS`, `MANUAL`, `OTHER`)
  - `broker_account_no_masked`
  - `product_code`
  - `is_mock`
  - `api_enabled`
  - `order_enabled`
  - `auto_trade_enabled`
  - `last_balance_sync_at`
  - `last_price_sync_at`

이 단계 목표:

- “투자 계좌”를 단순 `Account.type == investment`가 아니라, **브로커 연결 가능한 투자계좌**로 승격

### 6.3 2단계: KIS 인증/어댑터 계층 추가

신규 구성 제안:

- `backend/app/brokers/base.py`
- `backend/app/brokers/kis.py`
- `backend/app/services/kis_auth_service.py`
- `backend/app/models/broker_token.py` 또는 암호화 저장 구조

필요 기능:

- KIS access token 발급/갱신
- 실전/모의투자 분기
- 공통 어댑터 인터페이스
  - `get_balance()`
  - `get_holdings()`
  - `get_quote()`
  - `place_order()`
  - `get_order_status()`

이 단계 목표:

- price provider 수준이 아니라 **브로커 어댑터 계층**을 확보

### 6.4 3단계: holdings/예수금 동기화

현재 로컬 trade 집계를 유지하되, 다음으로 전환합니다.

1. KIS에서 계좌 잔고/보유 종목/예수금을 조회
2. 이를 내부 snapshot 테이블에 저장
3. `/v1/investments/holdings`는 우선 KIS snapshot을 기준으로 응답
4. 수동 입력 계좌 또는 연동 실패 시에만 `InvestmentTrade` 합산 fallback 사용

추가 테이블 제안:

- `investment_holding_snapshot`
- `investment_cash_snapshot`

이 단계 목표:

- holdings가 실제 브로커 기준 데이터가 되도록 개선

### 6.5 4단계: 주문/체결 모델 분리

현재 `InvestmentTrade`는 “체결된 거래 기록”에 가까운 성격으로 유지하는 것이 적절합니다.

따라서 별도 테이블이 필요합니다.

- `investment_order`
  - 주문 요청 단위
  - side, qty, price, order_type, requested_at, broker_order_id, status
- `investment_execution`
  - 체결 단위
  - executed_qty, executed_price, fee, executed_at

처리 흐름:

1. 프론트에서 주문 요청
2. 백엔드가 KIS 주문 API 호출
3. `investment_order` 저장
4. 체결 조회/폴링으로 `investment_execution` 저장
5. 체결이 확정되면 `InvestmentTrade` 기록 생성
6. 동시에 `transactions` 및 `accounts.balance` 정산 반영

이 단계 목표:

- 주문과 체결을 분리하여 실제 브로커 상태를 반영

### 6.6 5단계: 현금 정산 로직 전환

현재는 `create_trade()` 즉시 정산합니다. 이를 아래처럼 바꿉니다.

- `create_trade()`는 수동 거래 입력에서만 사용
- 브로커 주문 경로에서는 `create_order()` 또는 `place_order()` 사용
- 정산은 `execution confirmed` 시점에만 수행

정산 규칙:

- buy 체결:
  - `cash_delta = -(executed_qty * executed_price + fee)`
- sell 체결:
  - `cash_delta = executed_qty * executed_price - fee`

안전장치:

- 동일 체결번호 기준 idempotency 보장
- 중복 정산 방지 키 저장
- 부분체결 누적 반영 가능 구조

### 6.7 6단계: 자동매매

자동매매는 KIS 주문/체결 연동이 안정화된 이후 붙여야 합니다.

추가 대상:

- `auto_trade_rule`
- `auto_trade_run_log`
- 계좌별 활성화 옵션
- 장중 체크
- 쿨다운/중복 주문 방지
- 테스트 모드

자동매매 엔진 기본 순서:

1. 활성 규칙 조회
2. 현재가/보유 수량 확인
3. 시장시간 검증
4. 일일 한도/쿨다운 확인
5. 주문 요청
6. 주문 상태 추적
7. 실패/성공 로그 저장

---

## 7. API 고도화 제안

현재 `/v1/investments`를 유지하되 아래 API를 추가하는 것이 적절합니다.

### 7.1 계좌 연동

- `POST /v1/investments/accounts`
  - 투자계좌 등록
- `POST /v1/investments/accounts/{accountId}/kis/connect`
  - KIS 인증 연결
- `POST /v1/investments/accounts/{accountId}/sync`
  - 잔고/보유종목/예수금 즉시 동기화

### 7.2 주문/체결

- `POST /v1/investments/orders`
  - 주문 요청
- `GET /v1/investments/orders`
  - 주문 목록
- `GET /v1/investments/orders/{orderId}`
  - 주문 상세
- `POST /v1/investments/orders/{orderId}/refresh`
  - 체결 상태 갱신

### 7.3 자동매매

- `GET /v1/investments/rules`
- `POST /v1/investments/rules`
- `PUT /v1/investments/rules/{ruleId}`
- `DELETE /v1/investments/rules/{ruleId}`
- `POST /v1/investments/accounts/{accountId}/auto-trade/enable`
- `POST /v1/investments/accounts/{accountId}/auto-trade/disable`

---

## 8. 스케줄러 고도화 제안

### 8.1 가격 스케줄러

현재:

- `InvestmentTrade`의 ticker를 기준으로 가격을 갱신

개선:

- 투자계좌별 실제 보유 종목 snapshot을 기준으로 가격 갱신
- KIS quote 호출
- 장중 1~5분, 장마감 후 일별 저장

### 8.2 주문 상태 스케줄러

신규 필요:

- `status in (pending, partially_filled)` 주문 조회
- KIS 주문체결 조회 API 호출
- 신규 체결 발생 시 execution 저장 및 정산 반영

### 8.3 잔고 동기화 스케줄러

신규 필요:

- 계좌별 예수금/보유 종목 재동기화
- 내부 holdings snapshot 갱신
- 불일치 감지 시 경고 로그

---

## 9. 우선순위 제안

### 9.1 반드시 먼저 할 것

1. 투자계좌 상세 모델 추가
2. KIS 인증/어댑터 추가
3. holdings/예수금 동기화
4. 주문/체결 모델 분리
5. 체결 기반 정산 전환

### 9.2 그 다음 할 것

1. 수동 trade 입력과 브로커 주문 경로 분리
2. 가격 스케줄러를 KIS 기준으로 전환
3. 주문 상태 스케줄러 추가

### 9.3 마지막에 할 것

1. 자동매매 규칙
2. 주문 실패 알림
3. 고급 리스크 제어

---

## 10. 최종 판단

현재 시스템은 투자 기능의 “기초”는 구현되어 있습니다. 하지만 이것은 **브로커 연동 투자관리 시스템의 기초**이지, **한국투자증권 OpenAPI 기반 투자관리 완성본**은 아닙니다.

따라서 지금의 정확한 판단은 다음과 같습니다.

- 투자 거래 기록/손익 계산/가격 캐시: 구현됨
- 투자계좌 브로커 모델: 미구현
- KIS 연동: 미구현
- 체결 기반 정산: 미구현
- 자동매매: 미구현

즉, 투자 관점에서의 v1 고도화는 다음 한 문장으로 정리할 수 있습니다.

**“현재 구조를 폐기할 필요는 없지만, KIS 계좌/주문/체결/정산 계층을 추가하지 않으면 목표한 투자관리 시스템에 도달할 수 없다.”**

---

## TODO (KIS 투자 고도화 실행 목록)

- [completed] `v1.1-inv-model` 투자계좌 상세 모델 추가 (broker_account / investment_account_detail): broker_type, api_enabled, order_enabled, auto_trade_enabled, last_balance/price sync 등 DB 스키마/모델/마이그레이션 생성
- [completed] `v1.2-kis-auth-adapter` KIS OpenAPI 인증/어댑터 계층 추가: 토큰 발급/갱신(암호화 포함) + BrokerAdapter 구현(kis.py) 및 공통 인터페이스 함수 설계
- [completed] `v1.3-kis-holdings-sync` holdings/예수금 동기화 구현: KIS 조회 -> snapshot 테이블 저장 -> /v1/investments/holdings snapshot 기반 응답 (실패 시 fallback 정의)
- [completed] `v1.4-order-exec-separate` 주문/체결 모델 분리: investment_order, investment_execution 테이블 + 서비스/라우터 추가 (주문 생성, 주문 상태 조회, 체결 수집)
- [completed] `v1.5-settlement-on-exec` 체결 기반 정산 전환: execution 확정 시 transactions/accounts.balance에 idempotent 반영 (부분체결 누적 포함)
- [completed] `v1.6-price-scheduler-kis` 가격 갱신 파이프라인 전환: investment_price_updater를 KIS quote 기반으로 변경 (장중/장마감 정책, 실패 시 캐시 유지, daily close 저장)
- [completed] `v1.7-auto-trade-rules` 자동매매 구현: auto_trade_rule 및 규칙 CRUD API, 계좌별 enable/disable, 중복 주문 방지/쿨다운/장중 체크 로직 추가
- [completed] `v1.8-status-scheduler` 주문 상태 스케줄러/폴링 추가: pending/partially_filled 주문을 주기적으로 KIS에서 조회 -> execution 저장 -> 정산 트리거
- [completed] `v1.9-frontend-api-contract` 프론트 API 계약 정리: /v1/investments/accounts/*, orders/exec 조회, holdings source 변경에 따른 프론트 데이터 구조 업데이트 계획 수립 및 반영
- [completed] `v1.10-tests-checks` 회귀 테스트/점검: holdings 동기화, 부분체결 정산, 중복 정산 방지(idempotency) 시나리오 테스트 케이스 정의 및 최소 구현
