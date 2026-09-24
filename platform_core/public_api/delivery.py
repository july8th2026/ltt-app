"""The outbound HTTP call for one webhook delivery.

Isolated in its own module because this is the one place the platform makes a
request to an address an untrusted party chose. Everything here is a defence:

* the target is checked **before every attempt and after every redirect** —
  DNS can change between the moment a subscription was created and now;
* the address that passed the check is the address the socket connects to
  (**IP pinning**) — see the block below;
* redirects are capped, because a permissive client would happily follow a 302
  into ``127.0.0.1``;
* the response is read with a hard cap and a short timeout, so a receiver cannot
  hold a worker thread open or feed it a gigabyte;
* nothing of the platform's is attached: no cookies, no API key, no internal
  header. The only credential involved is the subscription's own signature.

⭐ **Ghim IP — vá TOCTOU, 24/09/2026 (plan wf-v2 P5b/T1).**

   Bản trước làm hai việc rời rạc: `webhooks.validate_target(url)` phân giải
   DNS để **kiểm**, rồi `urllib` phân giải **lần nữa** để **nối**. Giữa hai
   lần đó DNS đổi được: kẻ tấn công điều khiển bản ghi của chính tên mình trả
   địa chỉ công cộng cho lần một và ``127.0.0.1`` cho lần hai — bộ gác phê
   duyệt một địa chỉ, socket đi tới **một địa chỉ khác, chưa hề được kiểm**.
   Đúng khuôn TOCTOU (DNS rebinding).

   ⛔ Không viết bộ kiểm thứ hai ở đây. Mô-đun này **dùng lại**
   `platform_core.http_an_toan` (port lối ghim IP từ
   ``langchain_core/_security/_transport.py``, commit
   ``7622d3dce760ac4be6d9aef4c653277e06064aea``): phân giải **một** lần,
   kiểm **mọi** địa chỉ trả về, nối tới đúng địa chỉ đã kiểm, giữ nguyên
   ``Host``/SNI. Vị từ chặn vẫn là `platform_core.an_toan_mang`.

   ⚠️ `follow_redirects` đặt ở **client**, nên httpx gọi lại transport cho
   **từng hop** — mỗi hop tự đi qua bộ gác, không cần vòng lặp redirect viết
   tay nữa. Phép kiểm: `tests/test_2913_delivery_ghim_ip.py`.
"""
from __future__ import annotations

import time

import httpx

import platform_core.an_toan_mang as an_toan_mang
import platform_core.http_an_toan as http_an_toan
from platform_core.public_api import webhooks

USER_AGENT = "LTTStudios-Webhook/1.0"


def build_headers(subscription, delivery, *, body: bytes | None = None,
                  timestamp: int | None = None) -> dict:
    """The headers one delivery is sent with, including its signature(s).

    Separated from sending so the signature can be checked in a test without a
    receiver — the thing most worth checking is exactly the thing that needs a
    server to observe otherwise.
    """
    from platform_core import secretbox
    from platform_core.public_api import webhook_console

    payload_body = webhooks.canonical_body(delivery.payload or {}) \
        if body is None else body
    stamp = int(time.time()) if timestamp is None else int(timestamp)
    signatures = [webhooks.sign(secretbox.giai_ma(subscription.secret_enc),
                                timestamp=stamp, event_id=delivery.event_id,
                                body=payload_body)]

    # During a rotation grace window the event is signed with both secrets, so a
    # receiver that has switched and one that has not both verify. They travel
    # comma-separated and a verifier accepts if *any* entry matches.
    previous = webhook_console.grace_secret(subscription)
    if previous:
        signatures.append(webhooks.sign(previous, timestamp=stamp,
                                        event_id=delivery.event_id,
                                        body=payload_body))
    return {
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
        webhooks.SIGNATURE_HEADER: ",".join(signatures),
        webhooks.TIMESTAMP_HEADER: str(stamp),
        webhooks.EVENT_HEADER: delivery.event_id,
    }


def send_delivery(subscription, delivery, *, require_https: bool = True,
                  resolver=None, timeout: float = webhooks.DELIVERY_TIMEOUT_S) -> int:
    """POST one signed event. Returns the HTTP status code."""
    body = webhooks.canonical_body(delivery.payload or {})
    headers = build_headers(subscription, delivery, body=body)

    # ⚠️ `resolver or webhooks._system_resolver` — KHÔNG để `an_toan_mang` tự
    #    chọn bộ phân giải mặc định. `tests/test_202_webhook_console.py:42`
    #    thay chính tên đó để cả cụm test không đi ra DNS thật; truyền `None`
    #    xuống sẽ làm lần thay ấy **vô hiệu trong im lặng**.
    client = http_an_toan.tao_client(
        chinh_sach=webhooks.chinh_sach_cho(require_https),
        bo_phan_giai=resolver or webhooks._system_resolver,
        timeout=timeout, max_redirects=webhooks.MAX_REDIRECTS)
    try:
        with client.stream("POST", subscription.url, content=body,
                           headers=headers) as response:
            # Cap cứng: một người nhận không được nuôi worker một gigabyte.
            doc = 0
            for khoi in response.iter_bytes():
                doc += len(khoi)
                if doc >= webhooks.MAX_RESPONSE_BYTES:
                    break
            return int(response.status_code)
    except an_toan_mang.LoiChanSSRF as exc:
        # Giữ nguyên từng câu `/api/v1` vẫn trả trước khi đổi sang httpx.
        raise webhooks.loi_api(exc) from exc
    except httpx.TooManyRedirects as exc:
        raise webhooks.WebhookError("Too many redirects.") from exc
    finally:
        client.close()
