"""KIS (Korea Investment & Securities) broker adapter."""

from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
import requests

from app.brokers.base import BrokerAdapter
from app.models.broker_account import BrokerAccount
from app.services.kis_auth_service import KISAuthService
from app.config import get_settings
from sqlalchemy.orm import Session

settings = get_settings()


def normalize_kis_account_input(raw: str) -> Tuple[str, Optional[str]]:
    """
    사용자 입력에서 CANO(앞 8자리)와 선택적 상품코드 힌트(10자리 이상일 때 뒤 2자리)를 뽑습니다.
    하이픈·공백은 무시합니다.
    """
    digits = "".join(c for c in (raw or "") if c.isdigit())
    if len(digits) < 8:
        raise ValueError("계좌번호는 숫자 8자리(연속계좌 앞자리) 이상 입력해 주세요.")
    cano = digits[:8]
    hint = digits[8:10] if len(digits) >= 10 else None
    return cano, hint


def _acnt_prdt_candidate_order(hint: Optional[str]) -> List[str]:
    """자주 쓰이는 상품코드 우선, 이후 01~99 전체(중복 제거)."""
    priority = (
        "01",
        "45",
        "22",
        "81",
        "03",
        "21",
        "43",
        "44",
        "46",
        "47",
        "48",
        "49",
        "91",
        "92",
        "93",
        "02",
        "04",
        "05",
        "06",
        "07",
        "08",
        "09",
        "10",
    )
    seen: set[str] = set()
    out: List[str] = []
    if hint and len(hint) == 2 and hint.isdigit():
        if hint not in seen:
            seen.add(hint)
            out.append(hint)
    for p in priority:
        if p not in seen:
            seen.add(p)
            out.append(p)
    for i in range(1, 100):
        code = f"{i:02d}"
        if code not in seen:
            seen.add(code)
            out.append(code)
    return out


class KISAdapter(BrokerAdapter):
    """한국투자증권 OpenAPI 어댑터."""

    @staticmethod
    def _raise_if_kis_error(data: Dict[str, Any], context: str) -> None:
        """KIS는 HTTP 200이어도 rt_cd != 0 인 경우가 많음."""
        rt = str(data.get("rt_cd", "0")).strip()
        if rt == "0":
            return
        msg = (data.get("msg1") or data.get("msg_cd") or data.get("message") or str(data))[:500]
        raise ValueError(f"[{context}] 한국투자 API: {msg} (코드 {rt})")

    def __init__(self, db: Session, broker_account: BrokerAccount):
        """
        Args:
            db: 데이터베이스 세션
            broker_account: 브로커 계좌 정보
        """
        self.db = db
        self.broker_account = broker_account
        self._base_url = KISAuthService._get_base_url(broker_account.is_mock)

    def _get_access_token(self) -> str:
        """Access token 조회 (자동 갱신 포함)."""
        return KISAuthService.get_access_token(self.db, self.broker_account)

    def _get_headers(self) -> Dict[str, str]:
        """API 요청 헤더 생성."""
        token = self._get_access_token()
        app_key = settings.kis_app_key

        return {
            "authorization": f"Bearer {token}",
            "appkey": app_key,
            "appsecret": settings.kis_app_secret,
            "tr_id": "",  # 거래 ID는 각 API별로 설정
            "content-type": "application/json; charset=utf-8",
        }

    def _tr_id_inquire_balance(self) -> str:
        return "VTTC8434R" if self.broker_account.is_mock else "TTTC8434R"

    def probe_inquire_balance_ok(self, cano: str, prdt_cd: str) -> bool:
        """해당 CANO+상품코드 조합이 잔고조회에 성공(rt_cd==0)하는지 확인 (연동 시 자동 매핑용)."""
        url = f"{self._base_url}/uapi/domestic-stock/v1/trading/inquire-balance"
        headers = self._get_headers()
        headers["tr_id"] = self._tr_id_inquire_balance()
        params = {
            "CANO": cano,
            "ACNT_PRDT_CD": prdt_cd,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "01",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
        except Exception:
            return False
        return str(data.get("rt_cd", "0")).strip() == "0"

    def get_balance(self) -> Dict[str, Any]:
        """계좌 예수금/주문가능금액 조회."""
        # KIS API: 계좌 잔고 조회
        # 실제 엔드포인트는 KIS 문서 참조 필요
        url = f"{self._base_url}/uapi/domestic-stock/v1/trading/inquire-balance"
        headers = self._get_headers()
        headers["tr_id"] = self._tr_id_inquire_balance()

        params = {
            "CANO": self.broker_account.broker_account_no_masked or "",
            "ACNT_PRDT_CD": self.broker_account.product_code or "01",
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "01",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }

        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        self._raise_if_kis_error(data, "예수금 조회")

        # 응답 파싱 (실제 구조는 KIS API 문서 참조)
        output = data.get("output2", [{}])[0] if data.get("output2") else {}
        
        return {
            "cash_balance": Decimal(str(output.get("dnca_tot_amt", "0"))),  # 예수금
            "orderable_cash": Decimal(str(output.get("ord_psbl_cash", "0"))),  # 주문가능금액
            "currency": "KRW",
        }

    def get_holdings(self) -> List[Dict[str, Any]]:
        """보유 종목 조회."""
        url = f"{self._base_url}/uapi/domestic-stock/v1/trading/inquire-balance"
        headers = self._get_headers()
        headers["tr_id"] = self._tr_id_inquire_balance()

        params = {
            "CANO": self.broker_account.broker_account_no_masked or "",
            "ACNT_PRDT_CD": self.broker_account.product_code or "01",
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "01",  # 보유종목 조회
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "01",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }

        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        self._raise_if_kis_error(data, "보유종목 조회")

        holdings = []
        output1 = data.get("output1", [])

        for item in output1:
            holdings.append({
                "ticker": item.get("pdno", ""),  # 종목코드
                "name": item.get("prdt_name", ""),  # 종목명
                "quantity": Decimal(str(item.get("hldg_qty", "0"))),  # 보유수량
                "average_price": Decimal(str(item.get("pchs_avg_pric", "0"))),  # 평균단가
                "current_price": Decimal(str(item.get("prpr", "0"))),  # 현재가
                "valuation": Decimal(str(item.get("evlu_amt", "0"))),  # 평가금액
            })

        return holdings

    def get_quote(self, ticker: str) -> Dict[str, Any]:
        """현재가 조회."""
        # KIS API: 현재가 조회
        url = f"{self._base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
        headers = self._get_headers()
        headers["tr_id"] = "FHKST01010100"

        params = {
            "fid_cond_mrkt_div_code": "J",  # 주식
            "fid_input_iscd": ticker,
        }

        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        output = data.get("output", {})
        
        return {
            "ticker": ticker,
            "current_price": Decimal(str(output.get("stck_prpr", "0"))),  # 현재가
            "change": Decimal(str(output.get("prdy_vrss", "0"))),  # 전일대비
            "change_rate": Decimal(str(output.get("prdy_ctrt", "0"))),  # 등락률
            "volume": int(output.get("acml_vol", "0")),  # 거래량
            "timestamp": datetime.utcnow(),
        }

    def place_order(
        self,
        ticker: str,
        side: str,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        order_type: str = "limit",
    ) -> Dict[str, Any]:
        """주문 실행."""
        # KIS API: 주문 실행
        url = f"{self._base_url}/uapi/domestic-stock/v1/trading/order-cash"
        headers = self._get_headers()
        headers["tr_id"] = "TTTC0802U" if self.broker_account.is_mock else "TTTC0802U"

        # 매수/매도 구분
        bns_dvsn_cd = "01" if side == "buy" else "02"
        # 지정가/시장가 구분
        ord_dvsn = "00" if order_type == "limit" else "01"

        data = {
            "CANO": self.broker_account.broker_account_no_masked or "",
            "ACNT_PRDT_CD": self.broker_account.product_code or "01",
            "PDNO": ticker,
            "ORD_DVSN": ord_dvsn,
            "ORD_QTY": str(int(quantity)),
            "ORD_UNPR": str(int(price)) if price else "0",
            "BNS_DVSN_CD": bns_dvsn_cd,
        }

        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        result = response.json()

        return {
            "order_id": result.get("ODNO", ""),  # 주문번호
            "status": "pending",
            "requested_at": datetime.utcnow(),
        }

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """주문 상태 조회."""
        # KIS API: 주문 체결 조회
        url = f"{self._base_url}/uapi/domestic-stock/v1/trading/inquire-psbl-order"
        headers = self._get_headers()
        headers["tr_id"] = "TTTC8001R" if self.broker_account.is_mock else "TTTC8001R"

        params = {
            "CANO": self.broker_account.broker_account_no_masked or "",
            "ACNT_PRDT_CD": self.broker_account.product_code or "01",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
            "INQR_DVSN_1": "0",
            "INQR_DVSN_2": "0",
        }

        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        # 주문번호로 필터링 (실제로는 체결 조회 API 사용 필요)
        # 여기서는 간단한 구조로 반환
        output = data.get("output", [])

        for item in output:
            if item.get("ODNO") == order_id:
                ord_stat = item.get("ORD_STAT_CD", "")
                status_map = {
                    "00": "pending",
                    "01": "partially_filled",
                    "02": "filled",
                    "03": "cancelled",
                    "04": "rejected",
                }
                
                return {
                    "order_id": order_id,
                    "status": status_map.get(ord_stat, "unknown"),
                    "requested_quantity": Decimal(str(item.get("ORD_QTY", "0"))),
                    "filled_quantity": Decimal(str(item.get("EXEC_QTY", "0"))),
                    "average_price": Decimal(str(item.get("EXEC_AVG_PRIC", "0"))),
                    "executions": [],  # 체결 내역은 별도 API로 조회 필요
                }

        return {
            "order_id": order_id,
            "status": "unknown",
            "requested_quantity": Decimal("0"),
            "filled_quantity": Decimal("0"),
            "average_price": Decimal("0"),
            "executions": [],
        }


def discover_kis_acnt_prdt_cd(
    db: Session,
    broker_account: BrokerAccount,
    cano: str,
    hint: Optional[str] = None,
) -> str:
    """
    토큰이 유효한 상태에서, inquire-balance(예수금) 호출이 rt_cd==0 이 되는 ACNT_PRDT_CD를 찾습니다.
    """
    adapter = KISAdapter(db, broker_account)
    for prdt in _acnt_prdt_candidate_order(hint):
        if adapter.probe_inquire_balance_ok(cano, prdt):
            return prdt
    raise ValueError(
        "입력한 계좌번호에 맞는 상품코드(ACNT_PRDT_CD)를 자동으로 찾지 못했습니다. "
        "연속계좌 앞 8자리가 맞는지, 모의투자 스위치가 계좌 종류와 일치하는지 확인해 주세요."
    )
