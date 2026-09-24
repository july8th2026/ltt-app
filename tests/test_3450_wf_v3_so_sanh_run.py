"""P9b task 2 — `GET /agent/api/v3/runs/{id}/so-sanh?voi={id2}` (spec §14
*"So sánh run: API trả hai danh sách node với tham số/output/chi phí; UI diff"*).

## Ba mệnh đề tệp này canh

1. **Dẫn xuất, không thêm cột.** Mọi thứ cửa này trả ra đọc được từ thứ đã có:
   `workflow_version.graph` (tham số KHAI), `node_run_snapshot` (trạng thái,
   attempt, `cost_credit`, `output_ref`, `error`), `workflow_event`
   (`WorkflowStarted.du_lieu["inputs"]`). ⛔ Không cột mới, không bảng mới —
   ranh giới làn (`platform_core/models.py` + migration thuộc làn `p6`).
2. **`khac` phải TRỪ ĐƯỢC.** Một danh sách "node lệch" mà liệt kê cả node
   giống hệt thì không giúp ai. Đối chứng ở đây là **so một run VỚI CHÍNH NÓ**:
   `khac` phải RỖNG. Không có phép đối chứng ấy, một cài đặt trả "mọi node"
   vẫn xanh ở phép so hai run khác nhau.
3. **Ranh giới chủ sở hữu là 404 cho CẢ HAI phía.** Cửa này nhận id run thứ
   hai từ query — đúng hình dạng một cửa dò id của người khác nếu chỉ lọc chủ
   sở hữu ở phía `path`.

⚠️ Tham số trả ra là tham số **KHAI trong đồ thị**, không phải `Job.params` đã
   giải. `cau_noi.nop_job` tiêm `owner_id`, `_idem` **và giá trị credential đã
   giải** vào `Job.params` (§9.4); trả nó cho trình duyệt là một đường rò bí
   mật mới. Phép kiểm cuối tệp chốt điều đó.
"""
from __future__ import annotations

from tests.test_1723_v3_tao_va_doc_run import (_chay, _publish,  # noqa: F401
                                               _uid, api)


def _so_sanh(client, a_id: str, b_id: str):
    return client.get(f"/agent/api/v3/runs/{a_id}/so-sanh", params={"voi": b_id})


def _ghi_anh(run_id: str, node_id: str, *, sang: str, **kw):
    """Một lần chuyển node THẬT (qua máy trạng thái), không `db.add()` tay."""
    import platform_core.db as dbmod
    from platform_core.workflow import may_trang_thai
    db = next(dbmod.get_session())
    try:
        ok = may_trang_thai.chuyen_node(db, run_id, node_id, sang=sang,
                                        mo_ta="test 3450", **kw)
        db.commit()
        return ok
    finally:
        db.close()


def test_so_sanh_mot_run_voi_CHINH_NO_thi_khac_RONG(api):  # noqa: F811
    """⭐ ĐỐI CHỨNG. Thiếu phép này, một cài đặt trả "mọi node" vẫn xanh."""
    a, token_a, _, _ = api
    wf_id = _publish(_uid("v3run-a@example.com"))
    run_id = _chay(a, token_a, wf_id).json()["id"]

    r = _so_sanh(a, run_id, run_id)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["khac"] == []
    assert body["khac_version"] is False
    assert body["a"]["id"] == body["b"]["id"] == run_id
    # Danh sách node vẫn phải ĐẦY ĐỦ — "không lệch" khác "không có gì".
    assert [n["node_id"] for n in body["a"]["nodes"]] == ["a"]


def test_node_lech_trang_thai_thi_nam_trong_khac(api):  # noqa: F811
    a, token_a, _, _ = api
    wf_id = _publish(_uid("v3run-a@example.com"))
    run1 = _chay(a, token_a, wf_id).json()["id"]
    run2 = _chay(a, token_a, wf_id).json()["id"]

    # run1: node `a` đi tới SUCCEEDED với chi phí thật 3 credit.
    assert _ghi_anh(run1, "a", sang="READY")
    assert _ghi_anh(run1, "a", sang="SUCCEEDED", cost_credit=3)
    # run2: cùng node, cùng version — nhưng HỎNG.
    assert _ghi_anh(run2, "a", sang="READY")
    assert _ghi_anh(run2, "a", sang="FAILED", error="loi_provider: 500")

    body = _so_sanh(a, run1, run2).json()
    assert body["khac"] == ["a"]
    assert body["khac_version"] is False
    na = {n["node_id"]: n for n in body["a"]["nodes"]}["a"]
    nb = {n["node_id"]: n for n in body["b"]["nodes"]}["a"]
    assert (na["status"], na["cost_credit"]) == ("SUCCEEDED", 3)
    assert (nb["status"], nb["error"]) == ("FAILED", "loi_provider: 500")


def test_tra_tham_so_khai_va_output_ref_va_inputs(api):  # noqa: F811
    """Ba trường spec §14 đòi — tất cả dẫn xuất, không cột mới."""
    a, token_a, _, _ = api
    wf_id = _publish(_uid("v3run-a@example.com"))
    run1 = _chay(a, token_a, wf_id, {"inputs": {"chu_de": "mot"}}).json()["id"]
    run2 = _chay(a, token_a, wf_id, {"inputs": {"chu_de": "hai"}}).json()["id"]
    assert _ghi_anh(run1, "a", sang="READY")
    assert _ghi_anh(run1, "a", sang="SUCCEEDED", cost_credit=3,
                    output_ref={"artifact_id": "art-1"})

    body = _so_sanh(a, run1, run2).json()
    assert body["a"]["inputs"] == {"chu_de": "mot"}
    assert body["b"]["inputs"] == {"chu_de": "hai"}
    na = {n["node_id"]: n for n in body["a"]["nodes"]}["a"]
    assert na["output_ref"] == {"artifact_id": "art-1"}
    assert "params" in na            # tham số KHAI của node trong đồ thị
    # Node chưa chạy: `output_ref` rỗng, KHÔNG vắng mặt khỏi danh sách.
    nb = {n["node_id"]: n for n in body["b"]["nodes"]}["a"]
    assert nb["output_ref"] == {} and nb["status"] == "PENDING"


def test_khong_ro_bi_mat_cua_Job_params(api):  # noqa: F811
    """⛔ Tham số trả ra là tham số KHAI, không phải `Job.params` đã giải.

    Đối chứng: nhét một bí mật vào `Job.params` của job gắn với ảnh chụp rồi
    đòi cửa so sánh **không** nhắc tới nó. Không có phép này, một cài đặt
    "tiện tay đọc `Job.params` cho đủ chữ *tham số đã tính*" đi qua review.
    """
    import json as _json

    import platform_core.db as dbmod
    from platform_core import jobs
    a, token_a, _, _ = api
    uid = _uid("v3run-a@example.com")
    wf_id = _publish(uid)
    run1 = _chay(a, token_a, wf_id).json()["id"]

    db = next(dbmod.get_session())
    try:
        job = jobs.submit(db, user_id=uid, app_slug="ltt_llm",
                          job_type="ltt_llm.chat",
                          # ⭐ `fake` trong gia tri la CO Y: no la mot
                          #    nhan ma `scan_source_secrets` hieu
                          #    (`PLACEHOLDER_MARKERS`). Khong co nhan,
                          #    may quet bi mat DO gate chung cua MOI
                          #    phien vi mot bi mat GIA — va mot bao dong
                          #    gia la thu day nguoi ta tat canh bao.
                          #    ⛔ Van giu hinh dang `sk-...` de phep kiem
                          #    con do dung thu no dinh do: mot chuoi TRONG
                          #    NHU khoa that khong duoc lot ra dau ra.
                          params={"api_key": "sk-fake-BI-MAT-KHONG-DUOC-RO"})
        db.commit(); job_id = job.id
    finally:
        db.close()
    assert _ghi_anh(run1, "a", sang="READY")
    assert _ghi_anh(run1, "a", sang="QUEUED", job_id=job_id)

    r = _so_sanh(a, run1, run1)
    assert r.status_code == 200
    assert "sk-fake-BI-MAT-KHONG-DUOC-RO" not in _json.dumps(r.json())


def test_run_cua_nguoi_khac_tra_404_ca_hai_phia(api):  # noqa: F811
    a, token_a, b, token_b = api
    run_a = _chay(a, token_a, _publish(_uid("v3run-a@example.com"))).json()["id"]
    run_b = _chay(b, token_b, _publish(_uid("v3run-b@example.com"))).json()["id"]

    # B hỏi run của A ở vị trí `path`.
    assert _so_sanh(b, run_a, run_b).status_code == 404
    # ⭐ Và ở vị trí `voi` — đây là chỗ một cài đặt chỉ lọc `path` sẽ thủng.
    assert _so_sanh(b, run_b, run_a).status_code == 404
    # Đối chứng: chính chủ so hai run của mình thì 200.
    assert _so_sanh(a, run_a, run_a).status_code == 200


def test_thieu_tham_so_voi_tra_422(api):  # noqa: F811
    a, token_a, _, _ = api
    run_id = _chay(a, token_a, _publish(_uid("v3run-a@example.com"))).json()["id"]
    assert a.get(f"/agent/api/v3/runs/{run_id}/so-sanh").status_code == 422
