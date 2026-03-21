"""Base broker adapter interface."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from decimal import Decimal


class BrokerAdapter(ABC):
    """브로커 API 연동을 위한 공통 인터페이스."""

    @abstractmethod
    def get_balance(self) -> Dict[str, Any]:
        """
        계좌 예수금/주문가능금액 조회.
        
        Returns:
            {
                "cash_balance": Decimal,  # 예수금
                "orderable_cash": Decimal,  # 주문가능금액
                "currency": str,  # 통화
            }
        """
        pass

    @abstractmethod
    def get_holdings(self) -> List[Dict[str, Any]]:
        """
        보유 종목 조회.
        
        Returns:
            [
                {
                    "ticker": str,  # 종목코드
                    "name": str,  # 종목명
                    "quantity": Decimal,  # 보유수량
                    "average_price": Decimal,  # 평균단가
                    "current_price": Decimal,  # 현재가
                    "valuation": Decimal,  # 평가금액
                },
                ...
            ]
        """
        pass

    @abstractmethod
    def get_quote(self, ticker: str) -> Dict[str, Any]:
        """
        현재가 조회.
        
        Args:
            ticker: 종목코드
            
        Returns:
            {
                "ticker": str,
                "current_price": Decimal,
                "change": Decimal,  # 전일대비
                "change_rate": Decimal,  # 등락률
                "volume": int,  # 거래량
                "timestamp": datetime,
            }
        """
        pass

    @abstractmethod
    def place_order(
        self,
        ticker: str,
        side: str,  # "buy" or "sell"
        quantity: Decimal,
        price: Optional[Decimal] = None,
        order_type: str = "limit",  # "limit" or "market"
    ) -> Dict[str, Any]:
        """
        주문 실행.
        
        Args:
            ticker: 종목코드
            side: 매수/매도 ("buy" or "sell")
            quantity: 수량
            price: 가격 (지정가 주문 시 필수)
            order_type: 주문유형 ("limit" or "market")
            
        Returns:
            {
                "order_id": str,  # 브로커 주문번호
                "status": str,  # "pending", "filled", "rejected", etc.
                "requested_at": datetime,
            }
        """
        pass

    @abstractmethod
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        주문 상태 조회.
        
        Args:
            order_id: 브로커 주문번호
            
        Returns:
            {
                "order_id": str,
                "status": str,  # "pending", "partially_filled", "filled", "cancelled", "rejected"
                "requested_quantity": Decimal,
                "filled_quantity": Decimal,
                "average_price": Decimal,
                "executions": [  # 체결 내역
                    {
                        "execution_id": str,
                        "quantity": Decimal,
                        "price": Decimal,
                        "executed_at": datetime,
                    },
                    ...
                ],
            }
        """
        pass
