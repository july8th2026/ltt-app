"""Màn API của Voice: nó nói đúng sự thật về cửa, ở CẢ HAI trạng thái.

## Vì sao màn này cần test riêng, khi nó chỉ là một trang chữ

Vì nội dung của nó **đổi theo cấu hình đang chạy**, và một trong hai nhánh
không dựng được trên máy phát triển: cửa `speech.ltt` hôm nay đóng, nên mọi lần
mở trình duyệt đều chỉ thấy đúng một nửa. Nửa còn lại — nửa có lệnh gọi chép
được — chỉ tồn tại trên production, tức chỗ sai thì đắt nhất.

## 🔴 Hai chiều sai, và cả hai đều đã có tiền lệ trong kho này

**Nói ĐÓNG khi đang MỞ.** `CLAUDE.md` đã dính hai lần, cùng một hàng, cùng một
hướng: tài liệu ghi *"tool chưa mở"* trong khi máy chủ đang thu tiền. Hệ quả
được ghi thẳng ở đó: *"một phiên sau sẽ sửa nó như sửa mã chết."*

**Nói MỞ khi đang ĐÓNG.** Chiều này chưa xảy ra nhưng đắt hơn, vì nạn nhân là
khách chứ không phải một phiên Claude: một lệnh `curl` nằm sẵn trên trang sẽ
được chép bất kể câu chữ quanh nó, và 404 trả về đến từ Cloudflare hoặc từ cổng
— **không** `request_id`, **không** dòng nào trong `public_api_requests`, không
tra được bằng `/admin/api-trace`. Khách đọc nó thành "khoá của tôi sai", đi tạo
khoá mới, vẫn 404. Và phía ta không thấy gì cả.

⇒ Nên chốt không phải là "có một câu cảnh báo", mà là **không có lệnh chép
   được** khi cửa đóng.

## Điều KHÔNG chốt ở đây, có chủ ý

Nội dung chữ (cách diễn đạt, thứ tự khối) không bị đóng băng — nó sẽ đổi, và một
test so từng câu chỉ tạo ra việc bảo trì. Thứ bị chốt là **quan hệ giữa trạng
thái thật và thứ trang mời khách làm**.
"""
from __future__ import annotations

import re

import pytest


@pytest.fixture()
def khach(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'voice-api.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-voice-api")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    import apps.ltt_voice.tables  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from platform_core.storage import LocalStorage, set_storage
    from platform_core.users import tao_nguoi_dung
    set_storage(LocalStorage(str(tmp_path / "store")))

    gen = dbmod.get_session()
    db = next(gen)
    try:
        tao_nguoi_dung(db, email="voice-api@test.com",
                       password="matkhau-tot-12", is_verified=True)
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    from fastapi.testclient import TestClient

    from server.app import create_app
    client = TestClient(create_app(), base_url="https://testserver",
                        follow_redirects=False)
    m = re.search(r'name="csrf_token" value="([^"]+)"', client.get("/login").text)
    assert m
    client.post("/login", data={"username": "voice-api@test.com",
                                "password": "matkhau-tot-12",
                                "csrf_token": m.group(1)})
    try:
        yield client
    finally:
        client.close()
        set_storage(None)
        dbmod.reset_engine()


def _than(text: str) -> str:
    m = re.search(r'<section class="lv-man[^"]*".*?</section>', text, re.S)
    assert m, "khong tim thay than man `.lv-man`"
    return m.group(0)


# ── Cửa đóng ─────────────────────────────────────────────────────────────────

def test_cua_dong_thi_khong_co_lenh_goi_chep_duoc(khach):
    r = khach.get("/ltt-voice/api")
    assert r.status_code == 200
    than = _than(r.text)
    assert "alert-warn" in than
    assert "curl" not in than.lower()
    assert "lv-ma-chep" not in than or "data-chep-tu" not in than


def test_cua_dong_van_giu_thu_dung_duoc_ngay(khach):
    """Đóng cửa API không làm mất giá trị còn lại của màn.

    Tên giọng dựng sẵn và đường sang khu Lập trình viên đúng dù cửa đóng — một
    trang chỉ có mỗi câu "chưa mở" là một trang không ai quay lại.
    """
    than = _than(khach.get("/ltt-voice/api").text)
    from apps.ltt_voice import giong_mau
    assert giong_mau.MAC_DINH in than
    assert "/developers/keys" in than


# ── Cửa mở ───────────────────────────────────────────────────────────────────

@pytest.fixture()
def cua_mo(monkeypatch):
    monkeypatch.setenv("LTT_PUBLIC_API", "1")
    monkeypatch.setenv("LTT_PUBLIC_API_TOOLS", "speech.ltt")
    yield


def test_cua_mo_thi_hien_lenh_goi_dung_ten_tool(khach, cua_mo):
    than = _than(khach.get("/ltt-voice/api").text)
    assert "alert-ok" in than, "cua mo ma van bao dong"
    assert "curl" in than.lower()
    from apps.ltt_voice import doc_man_api
    assert doc_man_api.TEN_TOOL in than, "lenh mau khong nhac dung ten cong cu"
    assert "/api/v1/jobs" in than


def test_cua_mo_chi_doc_thi_noi_ra(khach, monkeypatch):
    """`read_only` bật thì cửa "mở" vẫn từ chối tạo việc — phải nói trước."""
    monkeypatch.setenv("LTT_PUBLIC_API", "1")
    monkeypatch.setenv("LTT_PUBLIC_API_TOOLS", "speech.ltt")
    monkeypatch.setenv("LTT_PUBLIC_API_READ_ONLY", "1")
    than = _than(khach.get("/ltt-voice/api").text)
    assert "alert-ok" in than
    assert "read-only" in than.lower() or "chỉ đọc" in than


def test_mot_cong_cu_KHAC_duoc_mo_khong_lam_man_nay_bao_mo(khach, monkeypatch):
    """Chốt hẹp nhất, và là chốt dễ hỏng nhất nếu ai đọc `enabled` thay cho tool.

    Production hôm nay có bốn công cụ mở — nếu màn này chỉ hỏi "khu API có bật
    không" thì nó đã báo MỞ suốt, sai theo đúng chiều nguy hiểm.
    """
    monkeypatch.setenv("LTT_PUBLIC_API", "1")
    monkeypatch.setenv("LTT_PUBLIC_API_TOOLS", "text.chat,image.ltt")
    than = _than(khach.get("/ltt-voice/api").text)
    assert "alert-warn" in than, "cong cu khac mo, khong phai cong cu nay"
    assert "curl" not in than.lower()


# ── Không đẻ ra bản sao thứ hai của một sự thật ──────────────────────────────

def test_man_api_khong_in_gia(khach, cua_mo):
    """Giá tính theo GIÂY tiếng ra, không theo ký tự vào.

    Mọi cách viết giá ở một trang hướng dẫn gọi API đều là một phép ước, và một
    phép ước in cạnh một lệnh `curl` sẽ được đọc là một lời hứa.
    `/developers/pricing` có bộ mô phỏng thật.
    """
    than = _than(khach.get("/ltt-voice/api").text)
    assert "credit" not in than.lower(), (
        "man API dang in gia — do la ban thu hai cua mot su that, va ban sai se "
        "la ban khong ai nho phai sua")


# ── Nút chép chỉ hoạt động khi trang có nạp `voice.js` ───────────────────────

def test_moi_khuon_co_nut_chep_deu_nap_voice_js():
    """Bản đầu của màn API quên `{% block scripts %}` — và không gì báo.

    🔴 VÌ SAO NÓ LÀ MỘT LỖI THẬT chứ không phải một thiếu sót nhỏ: nút chép vẫn
       **hiện đầy đủ, vẫn bấm được, vẫn có con trỏ tay**. Nó chỉ không làm gì.
       Khách bấm, tưởng đã chép, dán vào và nhận nội dung cũ trong bộ nhớ tạm —
       tệ hơn một nút không có, vì một nút không có thì người ta đi bôi đen.

    ⛔ Và nó không được phát hiện bởi bất kỳ phép kiểm HTTP nào, vì mọi phép
       kiểm đó soi HTML — mà HTML thì **đúng**. Chỉ hành vi là sai. Nên chốt
       phải bắc cầu giữa hai tệp: khuôn nào dùng nút thì khuôn ấy phải nạp mã.

    ⚠️ Tính cả nút đến GIÁN TIẾP qua `_voice_ma.html`: một khuôn `include` mảnh
       đó vẫn có nút, dù chính nó không viết chữ `lv-ma-chep` nào.
    """
    import pathlib

    goc = pathlib.Path(__file__).resolve().parents[1] / "apps/ltt_voice/templates"
    thieu = []
    for tep in sorted(goc.glob("ltt_voice_*.html")):   # chỉ khuôn TRANG
        noi_dung = tep.read_text(encoding="utf-8")
        co_nut = "lv-ma-chep" in noi_dung or "_voice_ma.html" in noi_dung
        if co_nut and "voice.js" not in noi_dung:
            thieu.append(tep.name)
    assert thieu == [], (
        f"{thieu} co nut chep nhung khong nap voice.js — nut se hien va bam "
        f"duoc ma khong lam gi ca")


def test_vi_du_lay_tu_ban_khai_chu_khong_go_lai(khach, cua_mo):
    """Câu ví dụ trên trang phải là CHÍNH câu trong `api_contract`.

    ⭐ Không phải để tiết kiệm một dòng: hai bản của cùng một ví dụ sẽ lệch, và
       bản lệch là bản không ai nhớ phải sửa. `/developers/tools` in ví dụ từ
       bản khai; nếu màn này gõ lại thì một ngày khách thấy hai câu khác nhau
       cho cùng một tham số và không biết tin câu nào.
    """
    from apps.ltt_voice import doc_man_api
    from apps.ltt_voice.manifest import MANIFEST

    tool = next(t for t in MANIFEST.tools if t.name == doc_man_api.TEN_TOOL)
    vi_du = tool.api_contract["params"]["text"]["example"]
    assert vi_du, "ban khai khong con vi du cho tham so `text`"
    assert vi_du in _than(khach.get("/ltt-voice/api").text)
