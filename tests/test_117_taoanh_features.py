"""H15.S9.2 Image Studio: edit/ref privacy, provider IDs and settlement."""
from __future__ import annotations

import io
import re

import pytest

from PIL import Image


def _png(size=(96, 64), color=(220, 20, 30)) -> bytes:
    out = io.BytesIO(); Image.new("RGB", size, color).save(out, "PNG")
    return out.getvalue()


def test_reference_validation_and_semantic_directives():
    from apps.taoanh.features import edit_directive, validate_reference
    assert validate_reference(_png(), "image/png") == ("image/png", (96, 64))
    with pytest.raises(ValueError, match="MIME"):
        validate_reference(_png(), "image/jpeg")
    text = edit_directive("semantic_inpaint", "đổi chiếc áo", [{"role": "source"}])
    assert "only the area described" in text and "preserve the rest" in text
    assert "SOURCE" in edit_directive("outpaint", "mở rộng", [{"role": "source"}])
    assert "STYLE" in edit_directive("style_transfer", "sơn dầu", [
        {"role": "source"}, {"role": "style"}])


# ⏭️ `test_gemini_request_resolves_legacy_model_and_embeds_reference` ĐÃ GỠ ở
#    pha 06.2. Nó chốt **một cơ chế đã bị xoá**: `_goi_gemini` dựng thân yêu cầu
#    Gemini và nhét ảnh tham chiếu **inline** (base64). Đường LTT_IMAGE không
#    nhét ảnh vào thân — máy B tự tải qua **presigned GET** (`DieuPhoi._ve_vao`).
#
# ⛔ Viết lại nó cho đường mới sẽ là một phép kiểm KHÁC đội tên cũ. Bất biến nó
#    canh (ảnh tham chiếu tới được model) nay do `test_1002` + phép kiểm quyền
#    sở hữu ngay dưới đây canh, mỗi cái một mệnh đề.


def test_worker_edit_reads_only_owner_refs_and_settles_by_model(tmp_path, monkeypatch):
    """Ảnh tham chiếu của người khác **không** dùng được — bất biến BẢO MẬT.

    🔴 Viết lại ở pha 06.2 cho đường LTT_IMAGE. **Kỳ vọng đổi, bất biến thì
       không**: bản cũ tiêm `_goi_gemini` (đã xoá); bản này tiêm `_dieu_phoi`.
       Thứ nó canh — *một người không đọc được ảnh của người khác* — y nguyên.

    ⭐ Và bản mới chốt **mạnh hơn**: nó đòi bộ điều phối **không được gọi một
       lần nào** khi chủ sở hữu sai, tức việc từ chối xảy ra **trước** khi chạm
       máy B, không phải sau.
    """
    from apps.taoanh import jobs
    from platform_core.storage import LocalStorage, set_storage

    storage = LocalStorage(str(tmp_path / "store")); set_storage(storage)
    nguon = "taoanh/u1/refs/source"
    storage.put(nguon, io.BytesIO(_png()), "image/png")

    da_goi = {"n": 0}

    class _KetQua:
        image_keys = ("taoanh/u1/j1/0.png", "taoanh/u1/j1/1.png")
        prompt_da_gui = "a cat"
        da_dich = True

    class _DP:
        def chay(self, **kw):
            da_goi["n"] += 1
            da_goi.update(kw)
            return _KetQua()

    monkeypatch.setattr(jobs, "_dieu_phoi", lambda: _DP())
    try:
        out = jobs.handle({"owner_id": "u1", "prompt": "đổi nền", "count": 2,
                           "edit_mode": "edit",
                           "references": [{"key": nguon, "mime": "image/png",
                                           "role": "source"}]})
        assert len(out["image_keys"]) == 2
        assert da_goi["mode"] == "edit"
        assert nguon in da_goi["ref_keys"]

        truoc = da_goi["n"]
        with pytest.raises(ValueError, match="không thuộc"):
            jobs.handle({"owner_id": "u2", "prompt": "x", "edit_mode": "edit",
                         "references": [{"key": nguon, "mime": "image/png",
                                         "role": "source"}]})
        assert da_goi["n"] == truoc, (
            "tu choi PHAI xay ra truoc khi cham may B — neu bo dieu phoi da duoc "
            "goi thi anh cua nguoi khac da di ra khoi nen tang")
    finally:
        set_storage(None)


def test_che_do_khong_map_duoc_thi_TU_CHOI_co_ten(monkeypatch):
    """⛔ `semantic_inpaint` · `outpaint` · `style_transfer` bị GỠ ở pha 06.2.

    `hidream-o1` **khai** ba chế độ (`t2i` · `edit` · `subject`); ba chế độ kia
    không map được. Nguỵ trang chúng thành `edit` sẽ trả về một tấm ảnh **trông
    hợp lý mà không phải thứ khách xin** — hỏng lặng lẽ, đắt hơn gỡ tử tế.
    """
    from apps.taoanh import jobs

    monkeypatch.setattr(jobs, "_dieu_phoi",
                        lambda: pytest.fail("khong duoc cham may B voi che do la"))
    for che_do in ("semantic_inpaint", "outpaint", "style_transfer"):
        with pytest.raises(ValueError, match="không còn được hỗ trợ"):
            jobs.handle({"owner_id": "u1", "prompt": "x", "edit_mode": che_do})


def test_edit_handoff_is_owner_scoped(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path/'edit.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-image-edit")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core.models import JOB_DONE, Job
    from platform_core.storage import LocalStorage, set_storage
    from platform_core.users import tao_nguoi_dung
    storage = LocalStorage(str(tmp_path / "store")); set_storage(storage)
    gen = dbmod.get_session(); db = next(gen)
    try:
        owner = tao_nguoi_dung(db, email="owner-edit@test.com",
                               password="matkhau-tot-12", is_verified=True)
        other = tao_nguoi_dung(db, email="other-edit@test.com",
                               password="matkhau-tot-12", is_verified=True)
        db.flush(); key = f"taoanh/{owner.id}/job-edit/0.png"
        job = Job(user_id=owner.id, app_slug="taoanh", job_type="taoanh.generate",
                  status=JOB_DONE, progress=100, params={"prompt": "gốc", "count": 1},
                  result={"image_keys": [key]})
        db.add(job); db.commit(); job_id = job.id
        storage.put(key, io.BytesIO(_png()), "image/png")
    finally:
        try: next(gen)
        except StopIteration: pass

    from fastapi.testclient import TestClient
    from server.app import create_app
    client = TestClient(create_app(), base_url="https://testserver", follow_redirects=False)
    def login(email):
        page = client.get("/login")
        token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        assert client.post("/login", data={"username": email,
            "password": "matkhau-tot-12", "csrf_token": token}).status_code == 303
    try:
        login("owner-edit@test.com")
        page = client.get(f"/taoanh/edit/{job_id}/0")
        assert page.status_code == 200 and 'name="saved_source_key"' in page.text
        assert "Đã nạp output làm ảnh nguồn" in page.text
        logout_token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        client.post("/logout", data={"csrf_token": logout_token})
        login("other-edit@test.com")
        assert client.get(f"/taoanh/edit/{job_id}/0").status_code == 404
    finally:
        client.close(); set_storage(None); dbmod.reset_engine()


def test_template_discloses_provider_privacy_and_precision_limit():
    from pathlib import Path
    src = (Path(__file__).parents[1] / "apps" / "taoanh" / "templates" / "image.html").read_text("utf-8")
    assert "enctype=\"multipart/form-data\"" in src
    # Bat bien: template phai KHAI anh tham chieu roi nen tang di dau. Dich den
    # doi o pha 08 (AI CLEAN REBUILD V2) — Gemini bi go, may tao anh noi bo thay
    # cho. Nen chot CA HAI chieu, de ban viet lai kho xanh hon ban cu:
    assert "Ảnh tham chiếu chỉ rời nền tảng để tới máy tạo ảnh nội bộ" in src
    assert "Gemini" not in src, "khai bao quyen rieng tu con ten nha cung cap da go"
    assert "chưa phải công cụ mask chính xác từng pixel" in src
    assert "saved_source_key" in src and "/edit/{{j.id}}/{{loop.index0}}" in src
