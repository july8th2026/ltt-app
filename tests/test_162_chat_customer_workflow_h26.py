"""H26.10B — customer workflow, money safety and operation trace for Chat AI."""
from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).parents[1]


def test_chat_ui_hides_engine_ids_and_exposes_customer_controls():
    src = (ROOT / "apps" / "chataistudio" / "templates" /
           "chataistudio.html").read_text("utf-8")
    assert "model_label" in src
    assert "{{active.model}}" not in src
    assert 'class="chat-suggestions"' in src
    assert 'id="stopbtn"' in src
    assert "AbortController" in src
    assert 'class="chat-turn-meta"' in src
    assert "tokens_total" in src
    assert "data-credit-balance" in src


def test_public_model_labels_do_not_leak_provider_ids():
    from apps.chataistudio.features import public_model_label

    assert public_model_label("gpt-5.6-sol") == "Chất lượng cao"
    assert public_model_label("gpt-5.6-terra") == "Nhanh"
    assert "gpt" not in public_model_label("gpt-unknown").lower()


# ⏭️ `test_incremental_image_hold_never_makes_balance_negative` ĐÃ GỠ ở pha 05.7
#    (AI CLEAN REBUILD V2), ghi lại ở 06.3 khi lượt gate đầy đủ phát hiện.
#
#    Nó chốt cơ chế **giữ credit tăng dần cho ảnh** của `chataistudio`:
#    `_hold_more` · `_refund` · `_settle`. Cả ba biến mất cùng lúc, vì hai lý do
#    độc lập và cả hai đều dứt điểm:
#
#      · vòng đời credit chuyển hẳn về `runtime_noi_bo.luong.mo_luong` (giành
#        suất → ước → giữ → commit → quyết toán trong `finally`). Giữ thêm một
#        vòng đời ở tầng app là **thu tiền hai lần** hoặc **hoàn nhầm**;
#      · tính năng **ảnh** trong app này bị gỡ — LTT_LLM là model văn bản.
#
# ⭐ Bất biến *"số dư không bao giờ âm"* thì KHÔNG mất, nó chỉ đổi chủ:
#    `tests/test_600_runtime_noi_bo_luong.py::test_thieu_credit_la_ThieuCredit_chua_cham_GPU`
#    canh nó ở cửa mới, và canh sớm hơn — trước khi chạm GPU.


def test_partial_reply_is_saved_and_charged_instead_of_lost(tmp_path, monkeypatch):
    """Lượt đứt giữa chừng: phần chữ đã nhận phải được LƯU, không bị vứt.

    🔴 VIẾT LẠI 09/09/2026 (AI CLEAN REBUILD V2). Bản cũ tiêm `routes.sc.turn_stream`
       — sidecar Codex, đã thay bằng `runtime_noi_bo.luong.mo_luong` ở pha 05.7.
       Tiêm vào đó nay **không có tác dụng gì**: luồng thật không đi qua sidecar
       nữa, nên phép kiểm rơi vào một nhánh khác và đỏ vì một lý do khác.

    ⭐ Mệnh đề thì y nguyên, và nó là một mệnh đề về TIỀN: `mo_luong` quyết toán
       trong `finally` của chính nó theo token THẬT, nên một lượt hỏng nửa chừng
       **vẫn bị thu tiền phần đã sinh ra**. Nếu phần chữ ấy không được lưu thì
       khách trả tiền cho một thứ họ không thấy đâu.

    ⛔ Và đó đúng là thứ pha 05.7 làm hỏng: bản ấy chỉ lưu ở nhánh `done`, mà
       `done` KHÔNG xảy ra khi luồng hỏng. Phép kiểm này canh chỗ đã gãy.
    """
    db_url = f"sqlite:///{(tmp_path / 'chat-partial.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", db_url)
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "chat-partial-test")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    dbmod.reset_engine(); dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session(); db = next(gen)
    try:
        user = tao_nguoi_dung(db, email="chat-partial@test.com",
                              password="Strong-pass-123", is_verified=True)
        credit.cap_tay(db, user.id, 10, by="test")
        db.commit(); user_id = user.id
    finally:
        try: next(gen)
        except StopIteration: pass

    from apps.chataistudio import routes
    monkeypatch.setattr(routes, "_models_cached", lambda: [])

    # Cửa runtime: hai đoạn chữ, một bản kê token, rồi HỎNG. Đúng hình dạng của
    # một lượt bị ngắt giữa chừng trên đường thật.
    from platform_core.runtime_noi_bo import luong as L

    def mo_luong_dut(db, **_kw):
        yield {"type": "response.started"}
        yield {"type": "response.delta", "text": "Phần đã "}
        yield {"type": "response.delta", "text": "nhận"}
        yield {"type": "usage.updated", "token_vao": 3, "token_ra": 4}
        yield {"type": "response.failed", "code": "khong_mo_duoc",
               "ly_do": "/models/qwen3.gguf khong nap duoc tren 10.0.0.7"}

    monkeypatch.setattr(L, "mo_luong", mo_luong_dut)

    from fastapi.testclient import TestClient
    from server.app import create_app
    client = TestClient(create_app(), base_url="https://testserver",
                        follow_redirects=False)
    try:
        login = client.get("/login")
        token = re.search(r'name="csrf_token" value="([^"]+)"', login.text).group(1)
        assert client.post("/login", data={"username": "chat-partial@test.com",
            "password": "Strong-pass-123", "csrf_token": token}).status_code == 303
        page = client.get("/chataistudio")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        made = client.post("/chataistudio/new", data={"csrf_token": csrf})
        conv_id = re.search(r"[?&]c=([^&]+)", made.headers["location"]).group(1)
        sent = client.post("/chataistudio/send", data={
            "csrf_token": csrf, "conv_id": conv_id, "message": "Kiểm tra partial"})
        assert sent.status_code == 200
        # Khách thấy phần chữ đã nhận, rồi thấy một lỗi.
        assert "Phần đã " in sent.text and '"type": "error"' in sent.text
        # ⛔ Và KHÔNG thấy một chữ nào của thượng nguồn: đường dẫn `.gguf` và IP
        #    nội bộ từng ra tới trình duyệt qua `str(e)` (đo 07/09).
        assert ".gguf" not in sent.text and "10.0.0.7" not in sent.text

        from platform_core.models import ChatMessage
        gen = dbmod.get_session(); db = next(gen)
        try:
            messages = db.query(ChatMessage).filter_by(
                conversation_id=conv_id, role="assistant").all()
            assert [m.content for m in messages] == ["Phần đã nhận"], (
                "phan chu da nhan bi vut — khach tra tien cho thu khong thay dau")
            assert messages[0].tokens_total == 7
            # Tin của người dùng được ghi ĐÚNG MỘT lần: pha 05.7 từng `db.add`
            # hai bản ghi cùng `id` và mọi lượt gửi vỡ ở `commit()`.
            assert db.query(ChatMessage).filter_by(
                conversation_id=conv_id, role="user").count() == 1
            # ⚠️ PHẠM VI: phép kiểm này đo việc **lưu chữ**, không đo việc **thu
            #    tiền** — cửa runtime đã bị thay nên không có bút toán nào chạy,
            #    và số dư vì thế không đổi. Việc quyết toán theo token thật do
            #    `tests/test_600_runtime_noi_bo_luong.py` canh, ở đúng tầng của nó.
            assert credit.so_du(db, user_id) == 10
        finally:
            try: next(gen)
            except StopIteration: pass
    finally:
        client.close(); dbmod.reset_engine()
