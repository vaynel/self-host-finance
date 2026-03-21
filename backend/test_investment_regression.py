#!/usr/bin/env python3
"""Investment regression smoke checks for v1.10 scenarios."""

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Optional

BASE = os.environ.get("API_BASE", "http://localhost:8001/v1")


def req(method: str, path: str, body=None, token: Optional[str] = None) -> tuple[int, dict]:
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    request_obj = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request_obj, timeout=15) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)}


def ensure_token() -> str:
    email = f"reg_{os.urandom(6).hex()}@test.com"
    password = "Test1234!"
    status, body = req("POST", "/auth/register", {"email": email, "password": password, "name": "reg"})
    if status not in (200, 201):
        raise RuntimeError("회원가입 실패")
    token = (body.get("data") or {}).get("accessToken")
    if not token:
        raise RuntimeError("토큰 획득 실패")
    return token


def main() -> int:
    token = ensure_token()
    checks: list[tuple[str, bool, str]] = []

    # 투자 계좌 생성
    status, body = req(
        "POST",
        "/accounts",
        {"name": "inv-reg", "type": "investment", "balance": 1000000, "institution": "KIS", "account_number": "000-00-0000"},
        token,
    )
    account_id = ((body.get("data") or {}) if status in (200, 201) else {}).get("id")
    checks.append(("create investment account", status in (200, 201), f"status={status}"))

    # holdings 응답 source 필드 계약 확인
    status, body = req("GET", "/investments/holdings", token=token)
    ok_holdings = status in (200, 201) and isinstance((body.get("data") or []), list)
    if ok_holdings and body.get("data"):
        ok_holdings = "source" in body["data"][0]
    checks.append(("holdings source field", ok_holdings, f"status={status}"))

    # rules CRUD 계약 점검
    rule_id = None
    if account_id:
        status, body = req(
            "POST",
            "/investments/rules",
            {
                "account_id": account_id,
                "ticker": "005930",
                "side": "buy",
                "order_type": "limit",
                "quantity": 1,
                "limit_price": 10000,
                "cooldown_seconds": 300,
            },
            token,
        )
        rule_id = ((body.get("data") or {}) if status in (200, 201) else {}).get("id")
        checks.append(("create rule", status in (200, 201), f"status={status}"))

        status, _ = req("GET", "/investments/rules", token=token)
        checks.append(("list rules", status in (200, 201), f"status={status}"))

        if rule_id:
            status, _ = req("PUT", f"/investments/rules/{rule_id}", {"enabled": False}, token)
            checks.append(("update rule", status in (200, 201), f"status={status}"))
            status, _ = req("DELETE", f"/investments/rules/{rule_id}", token=token)
            checks.append(("delete rule", status in (200, 201), f"status={status}"))

        # 계좌 auto-trade enable/disable
        status, _ = req("POST", f"/investments/accounts/{account_id}/auto-trade/enable", token=token)
        checks.append(("enable auto-trade", status in (200, 201), f"status={status}"))
        status, _ = req("POST", f"/investments/accounts/{account_id}/auto-trade/disable", token=token)
        checks.append(("disable auto-trade", status in (200, 201), f"status={status}"))

    passed = sum(1 for _, ok, _ in checks if ok)
    total = len(checks)
    print("=" * 50)
    print(f"Investment regression checks: {passed}/{total}")
    for name, ok, detail in checks:
        print(f"{'✓' if ok else '✗'} {name} ({detail})")
    print("=" * 50)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
