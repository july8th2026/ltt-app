"""test_1535 — `/api/v1/chat/completions`: máy B hết giờ đọc ⇒ 503 có thân lỗi, hoàn đủ. C0-34.

Cửa đồng bộ của cùng lỗi `test_1534` (cửa stream). `dieu_phoi._goi_openai` dịch
`httpx.ReadTimeout` thành `AmbiguousProviderError` (không phạt khoá — test_1534);
ở đây chốt rằng cửa HTTP trả lỗi có mã, không phải 500 chưa bắt, và không thu tiền.
"""
from __future__ import annotations

import importlib

_t1208 = importlib.import_module("tests.test_1208_cua_dong_bo_cho")

api = _t1208.api                     # noqa: F811 — dùng lại fixture đã có
DUONG = _t1208.DUONG
_account = _t1208._account
_so_du = _t1208._so_du
_than = _t1208._than
_h = _t1208._h


def test_chat_completions_het_gio_doc_tra_503_va_hoan_tien(api, monkeypatch):
    from apps.ltt_llm import features
    from platform_core.llm.cong_vlm import AmbiguousProviderError

    goi: list = []

    def gia(db, params, *, timeout_s=300.0, **_):
        # Đúng thứ `dieu_phoi._goi_openai` ném khi `httpx.ReadTimeout`.
        goi.append(1)
        raise AmbiguousProviderError("mat ket noi sau khi bat dau gui: ReadTimeout")

    monkeypatch.setattr(features, "chay", gia)
    user_id, token = _account()
    truoc = _so_du(user_id)

    r = api.post(DUONG, json=_than(), headers=_h(token))

    assert goi, "chua cham model — phep kiem khong do dung thu no noi"
    assert r.status_code == 503, r.text
    # Khuôn lỗi chung của `/api/v1` (problem+json), không phải 500 chưa bắt.
    than = r.json()
    assert than.get("code") == "service_unavailable", r.text
    assert than.get("retry") == "after_delay", r.text
    assert _so_du(user_id) == truoc, "het gio ma van thu tien"
