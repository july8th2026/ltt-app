"""Endpoint `DELETE` phải CHẠY được — không chỉ tồn tại trong mã.

🔴 **VÌ SAO CHỐT (27/09/2026).** Tôi gom hai chỗ nuốt lỗi lặng lẽ về một helper
`body_khong_bat_buoc()` nhưng **quên thêm nó vào danh sách import** của hai tệp
dùng nó ⇒ `NameError` ở **mọi** lượt `DELETE` brief và `DELETE` nhân vật.

⚠️ **45 phép kiểm xanh ⛔ không bắt được.** Vì mọi phép của `test_5310` và
`test_5341` là **kiểm TĨNH** — chúng đọc `inspect.getsource(...)` rồi tra chuỗi,
nên chúng khẳng định *"mã có gọi `_csrf`"*, *"mã không gõ tay số"*... và tất cả
vẫn đúng khi hàm ⛔ **không chạy nổi**. `mypy` là lưới duy nhất bắt được
(`name-defined`).

⭐ Bài học: một phép kiểm đọc **văn bản mã** trả lời *"mã trông thế nào"*, ⛔ không
trả lời *"mã có chạy không"*. Hai câu khác nhau, và một cụm endpoint chỉ có phép
kiểm tĩnh là một cụm **chưa ai chạy thử**.

Bài này gọi HTTP **thật** qua `TestClient`, nên nó đo đúng câu còn thiếu.
"""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'del-api.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("LTT_STORAGE", raising=False)
    import platform_core.storage as storage_mod
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))

    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    db = next(dbmod.get_session())
    from platform_core.users import tao_nguoi_dung
    uid = tao_nguoi_dung(db, email="del-a@example.com",
                         password="Strong-pass-123", is_verified=True,
                         role="user").id
    from apps.prompt_ai_ommi.tables import OmmiBrief, OmmiCharacter
    brief = OmmiBrief(owner_id=uid, title="Brief de xoa",
                      story_vi="x" * 40, target_scenes=6, target_duration_sec=30)
    nhan_vat = OmmiCharacter(owner_id=uid, name="Nhan vat de xoa")
    db.add(brief); db.add(nhan_vat); db.commit()
    ids = (brief.id, nhan_vat.id)
    db.close(); dbmod.reset_engine()

    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "ommi-del-api-test",
                          "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": ""})
    client = TestClient(app, base_url="https://testserver", follow_redirects=True)
    page = client.get("/login")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    assert client.post("/login", data={
        "username": "del-a@example.com", "password": "Strong-pass-123",
        "csrf_token": token, "next": "/prompt-ai-ommi"}).status_code == 200
    studio = client.get("/prompt-ai-ommi")
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', studio.text).group(1)
    yield client, csrf, ids[0], ids[1]
    client.close(); dbmod.reset_engine(); storage_mod._storage = None


@pytest.mark.parametrize("duong, khoa", [
    ("/prompt-ai-ommi/api/briefs/{}", "brief"),
    ("/prompt-ai-ommi/api/characters/{}", "nhan_vat"),
])
def test_delete_KHONG_CO_BODY_chay_duoc(api, duong, khoa):
    """`DELETE` không body là ca THƯỜNG — `request.json()` nổ và helper phải đỡ.

    Đây chính là ca đã hỏng: thiếu import ⇒ `NameError` ⇒ 500. Gửi ⛔ không body
    và ⛔ không `Content-Type: application/json`, đúng như một client thật làm.
    """
    client, csrf, brief_id, nv_id = api
    row_id = brief_id if khoa == "brief" else nv_id
    resp = client.request("DELETE", duong.format(row_id),
                          headers={"X-CSRF-Token": csrf})
    assert resp.status_code < 500, f"{resp.status_code}: {resp.text[:400]}"
    assert resp.status_code in (200, 204), resp.text


@pytest.mark.parametrize("duong, khoa", [
    ("/prompt-ai-ommi/api/briefs/{}", "brief"),
    ("/prompt-ai-ommi/api/characters/{}", "nhan_vat"),
])
def test_delete_voi_body_RAC_khong_thanh_500(api, duong, khoa):
    """Body ⛔ không phải JSON ⇒ 4xx của người dùng, ⛔ KHÔNG 500.

    ⭐ Đây là ĐỐI CHỨNG cho lựa chọn `except ValueError` thay vì `except
    Exception`: cả hai đều làm bài trên xanh, nhưng chỉ cách hẹp mới để một lỗi
    THẬT nổi lên. Body rác là ca `ValueError` ⇒ phải được đỡ; nếu ai đổi helper
    thành `except Exception` thì bài này vẫn xanh — nên nó ⛔ không đo cái đó, và
    tôi ⛔ không tuyên bố thế. Nó đo: rác ⛔ không làm sập máy chủ.
    """
    client, csrf, brief_id, nv_id = api
    row_id = brief_id if khoa == "brief" else nv_id
    resp = client.request("DELETE", duong.format(row_id),
                          headers={"X-CSRF-Token": csrf,
                                   "Content-Type": "application/json"},
                          content=b"{khong-phai-json")
    assert resp.status_code < 500, f"{resp.status_code}: {resp.text[:400]}"


def test_delete_thieu_csrf_bi_tu_choi(api):
    """Đối chứng bảo mật: helper trả `{}` ⛔ KHÔNG làm yếu CSRF.

    Không có ca này thì hai bài trên có thể xanh nhờ một helper đã **tắt** CSRF.
    """
    client, _csrf, brief_id, _nv = api
    resp = client.request("DELETE", f"/prompt-ai-ommi/api/briefs/{brief_id}")
    assert resp.status_code == 400, resp.text
