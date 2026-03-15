#!/usr/bin/env python3
"""FinFlow API 및 페이지별 점검 스크립트 (회원가입 → 로그인 → 전체 API)"""
import os
import sys
import json
import urllib.request
import urllib.error

BASE = os.environ.get("API_BASE", "http://localhost:8001/v1")
results: list[dict] = []


def req(method: str, path: str, body=None, token: str | None = None) -> tuple[int, dict]:
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body else None
    req_obj = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req_obj, timeout=10) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode())
        except Exception:
            body = {}
        return e.code, body
    except Exception as e:
        return 0, {"error": str(e)}


def ok(name: str, status: int, data: dict | None = None):
    success = 200 <= status < 300
    results.append({"name": name, "ok": success, "status": status, "data": data})
    sym = "✓" if success else "✗"
    print(f"  {sym} {name} (HTTP {status})")


def main():
    print("=" * 50)
    print("FinFlow 점검: 회원가입 → 로그인 → 전체 페이지 API")
    print("=" * 50)

    # 1. 회원가입
    email = f"test_{hash(os.urandom(8).hex()) % 100000}@test.com"
    status, resp = req("POST", "/auth/register", {"email": email, "password": "Test1234!", "name": "테스트"})
    ok("회원가입 POST /auth/register", status, resp.get("data"))

    if status not in (200, 201):
        # 이미 존재할 수 있음 → 로그인 시도
        status2, resp2 = req("POST", "/auth/login", {"email": email, "password": "Test1234!"})
        if status2 in (200, 201):
            token = (resp2.get("data") or {}).get("accessToken")
        else:
            print("  로그인 시도도 실패. 점검 중단.")
            sys.exit(1)
    else:
        token = (resp.get("data") or {}).get("accessToken")

    if not token:
        print("  토큰 획득 실패. 점검 중단.")
        sys.exit(1)

    ok("로그인 (토큰 획득)", 200)

    # 2. 인증 API
    status, _ = req("POST", "/auth/logout", token=token)
    ok("로그아웃 POST /auth/logout", status)
    # 다시 로그인
    _, resp = req("POST", "/auth/login", {"email": email, "password": "Test1234!"})
    token = (resp.get("data") or {}).get("accessToken")
    if not token:
        ok("재로그인", 0)
        sys.exit(1)
    ok("재로그인", 200)

    # 3. 거래 내역
    status, _ = req("GET", "/transactions", token=token)
    ok("거래 목록 GET /transactions", status)
    status, _ = req("POST", "/transactions", {
        "date": "2026-03-13", "description": "점검용", "amount": 1000,
        "type": "expense", "category": "식비", "account": "테스트계좌"
    }, token=token)
    ok("거래 추가 POST /transactions", status)

    # 4. 계좌
    status, acc = req("GET", "/accounts", token=token)
    ok("계좌 목록 GET /accounts", status)
    if status in (200, 201) and (acc.get("data") or []):
        aid = acc["data"][0].get("id")
        if aid:
            status, _ = req("GET", f"/accounts/{aid}", token=token)
            ok("계좌 상세 GET /accounts/{id}", status)
            status, _ = req("GET", f"/accounts/{aid}/flow", token=token)
            ok("계좌 잔액 흐름 GET /accounts/{id}/flow", status)

    status, _ = req("POST", "/accounts", {
        "name": "점검용계좌", "type": "bank", "institution": "테스트은행", "balance": 0
    }, token=token)
    ok("계좌 추가 POST /accounts", status)

    # 5. 투자
    status, _ = req("GET", "/investments/holdings", token=token)
    ok("투자 보유 GET /investments/holdings", status)
    status, _ = req("GET", "/investments/trades", token=token)
    ok("투자 거래 GET /investments/trades", status)

    # 6. 리포트
    status, _ = req("GET", "/reports/monthly-summary", token=token)
    ok("월간 요약 GET /reports/monthly-summary", status)
    status, _ = req("GET", "/reports/category-spending", token=token)
    ok("카테고리 지출 GET /reports/category-spending", status)

    # 7. 설정
    status, _ = req("GET", "/settings", token=token)
    ok("설정 조회 GET /settings", status)
    status, _ = req("PUT", "/settings", {"currency": "KRW", "monthStart": 1}, token=token)
    ok("설정 수정 PUT /settings", status)

    # 8. 업로드 (multipart 필수 - JSON POST 시 400 정상, 엔드포인트 존재 확인)
    status, _ = req("POST", "/upload/transactions", token=token)
    upload_ok = status in (200, 400, 422)  # 400=file/accountId 필수
    results.append({"name": "업로드 POST /upload/transactions (엔드포인트 존재)", "ok": upload_ok, "status": status, "data": None})
    print(f"  {'✓' if upload_ok else '✗'} 업로드 POST /upload/transactions (HTTP {status})")

    # 요약
    passed = sum(1 for r in results if r["ok"])
    total = len(results)
    print("=" * 50)
    print(f"결과: {passed}/{total} 통과")
    print("=" * 50)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
