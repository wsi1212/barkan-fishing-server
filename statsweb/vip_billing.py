"""VIP 결제 백엔드의 Oracle 내부 API 클라이언트."""
import os

import httpx

BASE_URL = os.environ.get("VIP_BILLING_API_URL", "http://127.0.0.1:3100").rstrip("/")
TOKEN = os.environ.get("VIP_BILLING_INTERNAL_TOKEN", "")


class VipBillingUnavailable(RuntimeError):
    pass


async def _request(method, path, payload=None):
    if not TOKEN:
        raise VipBillingUnavailable("VIP_BILLING_INTERNAL_TOKEN이 statsweb .env에 설정되지 않았습니다.")
    headers = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.request(method, BASE_URL + path, headers=headers, json=payload)
    except httpx.HTTPError as exc:
        raise VipBillingUnavailable(f"VIP 결제 서비스 연결 실패: {exc}") from exc
    if response.status_code >= 400:
        raise VipBillingUnavailable(f"VIP 결제 서비스 오류 (HTTP {response.status_code})")
    return response.json()


async def refunds():
    return await _request("GET", "/internal/refunds")


async def decide_refund(refund_id, action, admin_name):
    if action not in ("approve", "reject"):
        raise ValueError("잘못된 환불 처리 요청입니다.")
    return await _request("POST", f"/internal/refunds/{refund_id}", {
        "action": action,
        "decidedBy": admin_name,
    })


async def bank_transfer_orders():
    return await _request("GET", "/internal/bank-transfer/orders")


async def decide_bank_transfer_order(order_id, action, admin_name):
    if action not in ("confirm", "reject"):
        raise ValueError("잘못된 입금 확인 요청입니다.")
    return await _request("POST", f"/internal/bank-transfer/orders/{order_id}", {
        "action": action,
        "decidedBy": admin_name,
    })
