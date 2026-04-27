# 자동매매(룰 기반 매도) 구조 및 KIS 적용 점검

> 이 문서는 FinFlow의 **자동매매(특히 자동매도)** 가 어떤 경로로 동작하는지(룰 추가 → 스냅샷 동기화 → 평가 → 주문 → 체결/정산)와, **한국투자증권(KIS) OpenAPI 연동이 현재 코드에서 올바르게 적용되어 있는지**를 코드 기준으로 정리합니다.

---

## 1) 자동매매 전체 흐름(요약)

자동매매는 크게 2개의 루프로 동작합니다.

- **(A) 스냅샷 동기화 루프**: 보유종목/예수금 스냅샷을 KIS에서 주기적으로 가져옵니다.
- **(B) 룰 평가/매매 루프**: 최신 스냅샷을 기반으로 룰을 평가하고, 조건 충족 시 주문(매도)을 생성합니다.

현재 구현은 기본적으로 **Celery(beat + worker)** 를 통해 (A)→(B) 순서로 실행되도록 구성되어 있습니다.

---

## 2) 핵심 컴포넌트(코드 기준)

### 2.1 API Router (룰/주문/동기화 엔드포인트)

- 파일: `backend/app/routers/investments.py`

주요 엔드포인트:

- **룰 CRUD (개별 종목 룰)**  
  - `GET /v1/investments/rules`  
  - `POST /v1/investments/rules`  
  - `PUT /v1/investments/rules/{rule_id}`  
  - `DELETE /v1/investments/rules/{rule_id}`

- **글로벌 룰 CRUD (계좌 내 전 종목)**  
  - (schema import 존재) `AutoTradeGlobalRuleCreate/Update` 기반으로 `create_global_rule/update_global_rule/delete_global_rule` 호출
  - 글로벌 실행 로그: `GET /v1/investments/global-rules/logs` 계열(라우터 하단 구현부 참고)

- **계좌 단위 자동매매 on/off**  
  - `POST /v1/investments/accounts/{account_id}/auto-trade/enable`  
  - `POST /v1/investments/accounts/{account_id}/auto-trade/disable`

- **스냅샷 수동 동기화**  
  - `POST /v1/investments/accounts/{account_id}/sync`

- **주문/체결(수동/자동 공통)**  
  - `POST /v1/investments/orders` (주문 생성)
  - `GET /v1/investments/orders` (주문 목록)
  - `GET /v1/investments/orders/{order_id}` (주문 상태 조회)
  - `POST /v1/investments/orders/{order_id}/refresh` (브로커 상태 갱신 + executions 수집)

---

### 2.2 Celery 스케줄/태스크(운영 기본 경로)

- 파일: `backend/app/celery_app.py`
  - `CELERY_ENABLED=true`일 때 beat schedule 활성
  - 주기 실행 task: `app.tasks.auto_trade_tasks.sync_all_investment_holdings`

- 파일: `backend/app/tasks/auto_trade_tasks.py`
  - `sync_all_investment_holdings`:
    1) 자동매매 활성 계좌 대상 선별  
       (`Account.type=investment` + `BrokerAccount.broker_type=KIS` + `api_enabled=true` + `auto_trade_enabled=true`)
    2) 계좌별 `sync_holdings_snapshot(...)` 실행
    3) 동기화 후 `evaluate_once()` 호출(룰 평가/주문)

**정상 동작 시 기대 로그**

- `logs/celery-worker.log`
  - `[tasks] ... sync_all_investment_holdings` 등록 표시
  - `Task ... sync_all_investment_holdings[...] received`
  - `... succeeded ... {'synced': N, 'targets': N}`

---

### 2.3 룰 평가(자동매도 엔진)

- 파일: `backend/app/services/auto_trade_evaluator.py`
  - `evaluate_once()`가 평가 메인 루틴
  - 최신 스냅샷: `investment_holding_snapshot`을 `synced_at desc`로 가져와 평가

룰 종류:

- **개별 종목 룰**: `auto_trade_rules` (`AutoTradeRule`)
- **글로벌 룰**: `auto_trade_global_rules` (`AutoTradeGlobalRule`)

평가 결과 기록:

- 개별 룰 로그: `auto_trade_run_logs`
- 글로벌 룰 로그: `auto_trade_global_run_logs`

중요한 가드(스킵 사유):

- `duplicate_pending_order`: 동일 티커/계좌에 `investment_orders.status in (pending, partially_filled)`가 이미 있으면 중복 주문 방지
- `cooldown`: 쿨다운 시간 내 재발동 방지
- `auto_trade_disabled`: 계좌 단위 자동매매 OFF 시 평가/주문 스킵
- (시장시간) `alert_only`는 장중 외에는 평가/주문 스킵(매도 모드는 시도 가능하도록 되어 있음)

---

### 2.4 주문 생성(공통 서비스)

- 파일: `backend/app/services/order_service.py`
  - `create_order(...)`가 브로커 API 호출 + `investment_orders` 저장을 담당
  - **브로커가 반환한 주문번호(`order_id`)가 없으면 로컬 pending 주문을 생성하지 않도록 방어** (고아 pending 방지)

정상 흐름(정상 응답/정상 상태):

1) `create_order()` 성공
2) `investment_orders` 신규 row 생성
   - `status = pending`
   - `broker_order_id != ''` (KIS 주문번호)
3) 이후 `collect_executions()` / `get_order_status()`로 체결/정산 반영

---

## 3) 데이터 모델(자동매매에서 중요한 테이블)

- `broker_accounts`
  - `api_enabled`, `order_enabled`, `auto_trade_enabled`, `is_mock`
  - `broker_account_no_masked`(CANO), `product_code`(ACNT_PRDT_CD)

- `investment_holding_snapshot` (보유 스냅샷)
  - `ticker`, `quantity`, `average_price`, `current_price`, `synced_at`

- `auto_trade_rules` / `auto_trade_global_rules`
  - `trigger_kind`(cost_drop/peak_drop), `trigger_percent`
  - `action_mode`(alert_only/auto_sell/alert_and_sell)
  - `order_type`(limit/market), `limit_price`, `sell_quantity_ratio`

- `investment_orders`
  - `side='sell'`
  - `status in (pending, partially_filled, filled, failed, cancelled...)`
  - `broker_order_id` (KIS의 ODNO)

- `investment_executions`
  - 체결/정산 반영 단위

---

## 4) “정상”이 무엇인지(확인 체크리스트)

### 4.1 자동매매가 실제로 “주문 접수”까지 됐는지

다음 조건이 동시에 만족해야 “브로커(KIS)에 실제 주문이 접수됨”으로 봅니다.

- `investment_orders.status = pending`
- **`investment_orders.broker_order_id`가 빈 값이 아님** (ODNO)

> `pending`인데 `broker_order_id=''`이면 “로컬에만 남은 상태”일 수 있어 체결/상태조회가 불가합니다.

### 4.2 체결/정산이 정상 반영됐는지

- `investment_executions` 생성
- `investment_trades` 생성
- `transactions` 생성
- `accounts.balance` 반영

---

## 5) KIS OpenAPI 적용 점검(현재 코드 기준)

### 5.1 주문 API(현금 주문: order-cash)

- 파일: `backend/app/brokers/kis.py`
- 호출 URL: `/uapi/domestic-stock/v1/trading/order-cash`
- 주문 구분:
  - `SLL_BUY_DVSN_CD`: `"01"(매수) / "02"(매도)`
  - `ORD_DVSN`: `"00"(지정가) / "01"(시장가)`
- TR ID:
  - 매수: `TTTC0802U` (모의: `VTTC0802U`)
  - 매도: `TTTC0801U` (모의: `VTTC0801U`)
- 정상 응답에서 주문번호:
  - 통상 `result.output.ODNO`에 주문번호가 포함됨
  - 코드도 `output.ODNO` 우선으로 파싱하도록 되어 있음

**판정**

- 주문 요청 payload 필드/`tr_id`/응답 `ODNO` 파싱은 **현재 코드상 정상 방향으로 적용됨**.

---

### 5.2 주문 상태/체결 조회 API(주의: 현재 구현은 단순/임시 성격)

- 파일: `backend/app/brokers/kis.py`
- `get_order_status()`가 호출하는 URL은 현재 `inquire-psbl-order`로 되어 있음.

이 엔드포인트는 “주문가능 조회” 성격이 강하며, **주문 체결/상태 조회 전용 API로는 부적합**할 수 있습니다.
실운영에서는 보통 “주문/체결 조회” 전용 API(일별 주문체결 조회 등)를 사용해:

- 주문 상태(`pending/filled/cancelled`)
- 체결 목록(executions)

을 안정적으로 가져와야 합니다.

**판정**

- “주문 상태/체결 조회”는 **현재 코드가 완전하다고 보기 어렵고 개선 필요** (정확한 KIS 체결 조회 API로 교체 권장)

---

## 6) 운영 중 자주 발생하는 이슈와 의미(원인 추적 포인트)

### 6.1 `duplicate_pending_order`

- 의미: 같은 티커에 대해 이미 `pending/partially_filled` 주문이 있어 새 주문을 막음(중복 방지)
- 확인: `investment_orders`에서 해당 티커/계좌 pending이 남아있는지 확인

### 6.2 `pending`인데 `broker_order_id=''`

- 의미: 브로커 주문번호를 못 받아 “실접수/조회 불가” 상태가 됨
- 현재 코드에서:
  - `order_service.create_order()`는 원칙적으로 `broker_order_id` 없으면 로컬 주문을 만들지 않도록 방어
  - 다만 과거 생성된 고아 pending이 남아있을 수 있으므로 정리 필요

### 6.3 KIS 오류 코드(`rt_cd != 0`)

- 의미: HTTP 200이어도 실패이며, `msg1`에 원인이 들어있음
- 코드에서 `_raise_if_kis_error()`로 실패를 예외로 처리

---

## 7) 추천 운영 구성(현재 코드가 의도한 형태)

- `CELERY_ENABLED=true`
- Redis 실행
- `celery beat` + `celery worker` 실행(주기적으로 동기화→평가→주문)
- 필요 시 `POST /v1/investments/orders/{orderId}/refresh`를 통해 체결/정산을 강제 동기화(단, 주문상태 조회 구현 보강 권장)

