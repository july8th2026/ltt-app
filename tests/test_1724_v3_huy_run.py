"""Huỷ một lượt chạy v3 — `POST /agent/api/v3/runs/{id}/cancel`.

## Mệnh đề đắt nhất ở đây: huỷ phải LŨY ĐẲNG THEO NGHĨA ĐÚNG

Bấm "Huỷ" hai lần là chuyện thường ngày (mạng chậm, người dùng sốt ruột). Hai
cách sai đối xứng nhau:

    tra 200 lan hai   giao dien tuong lan hai cung "huy duoc" mot run da ket
                      thuc — va se tuong the ca voi mot run da SUCCEEDED
    tra 500 lan hai   nguoi dung thay "loi he thong" cho mot thao tac vo hai

⇒ Lần hai trả **409 có mã**: thao tác không xảy ra, và lý do đọc được bằng máy.

Và một vế đối chứng bắt buộc: huỷ một run **đã SUCCEEDED** cũng phải 409 — nếu
không, `huy_run` đang ghi `CANCELLED` đè lên một run đã kết sổ.
"""
from __future__ import annotations
# ruff: noqa: F811 -- imported pytest fixture is intentionally requested below.

from tests.test_1723_v3_tao_va_doc_run import (  # noqa: F401
    CC, _publish, _uid, api)


def _tao(a, token, wf_id) -> str:
    r = a.post(f"/agent/api/v3/workflows/{wf_id}/runs",
               headers={"X-CSRF-Token": token}, json={})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_huy_lan_dau_tra_CANCELLED_va_ghi_su_kien(api):
    a, token_a, _, _ = api
    run_id = _tao(a, token_a, _publish(_uid("v3run-a@example.com")))
    r = a.post(f"/agent/api/v3/runs/{run_id}/cancel",
               headers={"X-CSRF-Token": token_a}, json={})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "CANCELLED"
    assert "WorkflowCancelled" in [e["loai"] for e in body["su_kien"]]
    assert all(n["status"] == "CANCELLED" for n in body["nodes"])


def test_huy_lan_hai_tra_409_co_ma_chu_khong_200_cung_khong_500(api):
    a, token_a, _, _ = api
    run_id = _tao(a, token_a, _publish(_uid("v3run-a@example.com")))
    a.post(f"/agent/api/v3/runs/{run_id}/cancel",
           headers={"X-CSRF-Token": token_a}, json={})
    r = a.post(f"/agent/api/v3/runs/{run_id}/cancel",
               headers={"X-CSRF-Token": token_a}, json={})
    assert r.status_code == 409
    assert r.json()["detail"]["ma"] == "da_ket_thuc"


def test_huy_run_cua_nguoi_khac_tra_404(api):
    a, token_a, b, token_b = api
    run_id = _tao(a, token_a, _publish(_uid("v3run-a@example.com")))
    r = b.post(f"/agent/api/v3/runs/{run_id}/cancel",
               headers={"X-CSRF-Token": token_b}, json={})
    assert r.status_code == 404


def test_su_kien_moi_sinh_ra_SAU_khi_huy_doc_duoc_bang_sau(api):
    """Vòng poll của Canvas gửi `sau=<seq_cuoi>` mỗi nhịp. Nếu `seq_cuoi`
    không tiến sau khi có sự kiện mới, nhịp kế lại lấy đúng bộ cũ và giao
    diện đứng im dù run đã đổi."""
    a, token_a, _, _ = api
    run_id = _tao(a, token_a, _publish(_uid("v3run-a@example.com")))
    truoc = a.get(f"/agent/api/v3/runs/{run_id}").json()["seq_cuoi"]
    a.post(f"/agent/api/v3/runs/{run_id}/cancel",
           headers={"X-CSRF-Token": token_a}, json={})
    tiep = a.get(f"/agent/api/v3/runs/{run_id}", params={"sau": truoc}).json()
    assert tiep["seq_cuoi"] > truoc
    assert [e["loai"] for e in tiep["su_kien"]] == ["WorkflowCancelled"]
