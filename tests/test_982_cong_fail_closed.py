"""test_982 — cổng VLM phải TỪ CHỐI KHỞI ĐỘNG khi nghe ra LAN mà không có token.

Dải **980–989** của chương trình MASTER UPGRADE (`docs/LLM_UPGRADE_MASTER_PLAN.md`).

═══════════════════════════════════════════════════════════════════════════
 KHUYẾT TẬT
═══════════════════════════════════════════════════════════════════════════

`llm_gateway/api.py::auth` trả về ngay khi token rỗng:

    def auth(authorization: str = Header(default="")) -> None:
        if not cfg.token:
            return          # dev: chua dat token -> khong chan

Đó là đường dev, và nó **đúng** chừng nào cổng còn nghe `127.0.0.1`. Nhưng máy A
phải gọi được, nên có người **phải** đổi `LTT_LLM_HOST` thành `0.0.0.0` bằng tay
trong `gateway.env`. Trước bản vá này, không có gì nối hai biến ấy lại: một dòng
`LTT_LLM_TOKEN=` rỗng cùng với `0.0.0.0` mở model nhà cho cả LAN, và triệu chứng
duy nhất là **một dòng `log.warning`**.

⭐ ĐO THẬT TRƯỚC KHI SỬA (09/09, từ máy A, chỉ đọc):

      GET http://192.168.2.66:8299/live    -> 200
      GET http://192.168.2.66:8299/health  -> 401 {"detail":"token khong dung"}

  ⇒ **Production đang có token.** Tệp này KHÔNG vá một lỗ hổng đang mở — nó biến
    một thứ đang đúng nhờ **giao ước** ("nhớ đặt token khi mở host") thành một
    thứ đúng nhờ **cơ chế**. Nói quá lên là nói sai; nhưng bỏ qua cũng sai, vì
    giao ước không sống sót qua một lần sửa `gateway.env` lúc 2 giờ sáng.

⛔ `SystemExit` chứ không phải 401-cho-mọi-yêu-cầu. Phương án kia để dịch vụ vẫn
   "chạy" với `/live` xanh — một cổng khoẻ mạnh không phục vụ được ai. Kho này
   đã trả giá cho đúng lớp triệu chứng đó ngày 01/09 (health xanh giả, xem
   `to_tien.py`), và bài học là: **hỏng phải nói ra tên thủ phạm**.
"""
from __future__ import annotations

import logging

import pytest

from llm_gateway.config import DEM_UOC_MAC_DINH, Config
from llm_gateway.vat_ly import VatLy
from llm_gateway.main import LOOPBACK


def _cfg(host: str, token: str) -> Config:
    """Một `Config` tối thiểu. Chỉ `host`/`token` có ý nghĩa ở đây."""
    return Config(
        upstream_url="http://127.0.0.1:8280", host=host, port=8299, token=token,
        models_mo=("qwen38-api",), max_output_tokens=100,
        max_images=1, max_image_bytes=1024, upstream_timeout_s=1.0,
        stream_timeout_s=1.0, ram_trong_toi_thieu_gb=1.0, trong_tai_bat=False,
        vram_sach_mb=1,
        nhip_tim_giay=0.0, nguon_vat_ly="test",
        # Rao vat ly: tran vao = ctx - max_out(100) - DEM_UOC = 1000.
        vat_ly={"qwen38-api": VatLy(ctx=1000 + 100 + DEM_UOC_MAC_DINH, np=1, kvu=True)})


def _chay_chot(monkeypatch, host: str, token: str):
    """Chạy `main()` tới đúng chỗ chốt, không dựng uvicorn.

    ⭐ Ta chặn ở `_ai_dang_nghe`: chốt bảo mật đứng **trước** nó, nên nếu chốt
       cho qua thì `_ai_dang_nghe` sẽ được gọi và ta ném một dấu hiệu riêng để
       phân biệt *"đã qua chốt"* với *"chốt chặn lại"*.

    ⛔ KHÔNG dùng `SystemExit` làm dấu hiệu "đã qua" — nó trùng đúng thứ ta đang
       đo, và một phép kiểm không phân biệt được hai đường thì nó xanh vì lý do
       gì cũng được.
    """
    from llm_gateway import main as M

    class DaQuaChot(Exception):
        pass

    monkeypatch.setattr(M, "nap_env", lambda *a, **k: 0)
    monkeypatch.setattr(M.Config, "from_env", staticmethod(lambda: _cfg(host, token)))

    def _khong_nen_toi_day(*a, **k):
        raise DaQuaChot()

    monkeypatch.setattr(M, "_ai_dang_nghe", _khong_nen_toi_day)
    return M, DaQuaChot


@pytest.mark.parametrize("host", ["0.0.0.0", "::", "192.168.2.66"])
def test_ngoai_loopback_khong_token_thi_TU_CHOI_KHOI_DONG(monkeypatch, host):
    """Ca nguy hiểm. Phải `SystemExit`, không phải cảnh báo."""
    M, DaQuaChot = _chay_chot(monkeypatch, host, "")
    with pytest.raises(SystemExit) as e:
        M.main()
    assert e.value.code == 3, "ma thoat phai phan biet duoc voi chot cong-bi-giu (2)"


@pytest.mark.parametrize("host", sorted(LOOPBACK))
def test_loopback_khong_token_van_chay(monkeypatch, host):
    """Đường dev **không được** vỡ.

    ⛔ Đây là nửa quan trọng ngang nửa trên. Một chốt bảo mật bắt token **luôn
       luôn** sẽ chặn việc chạy cổng trên một máy không GPU để thử — và bản vá
       nào phá mất đường thử thì sẽ bị tắt đi, rồi cả chốt biến mất cùng nó.
    """
    M, DaQuaChot = _chay_chot(monkeypatch, host, "")
    with pytest.raises(DaQuaChot):
        M.main()


@pytest.mark.parametrize("host", ["0.0.0.0", "127.0.0.1", "192.168.2.66"])
def test_co_token_thi_luon_chay(monkeypatch, host):
    """Có token thì mọi host đều qua — kể cả LAN. Đây là hình dạng production."""
    M, DaQuaChot = _chay_chot(monkeypatch, host, "bi-mat-nao-do")
    with pytest.raises(DaQuaChot):
        M.main()


def test_0_0_0_0_KHONG_duoc_coi_la_loopback():
    """⛔ Cách dễ nhất để vô hiệu hoá chốt trên là "sửa" tập `LOOPBACK`.

    `0.0.0.0` và `::` **bao gồm** loopback, nên một người đọc vội rất dễ thêm
    chúng vào cho "đầy đủ". Chúng bind **mọi** giao diện — đó là dạng phơi ra
    rộng nhất, không phải một biến thể của loopback.
    """
    for xau in ("0.0.0.0", "::", ""):
        assert xau not in LOOPBACK, (
            xau + " bi coi la loopback -> chot fail-closed thanh vo dung")
    assert "127.0.0.1" in LOOPBACK and "::1" in LOOPBACK


def test_thong_diep_loi_noi_ro_phai_lam_gi(monkeypatch, caplog):
    """Một chốt chặn khởi động mà không nói cách gỡ thì nó bị gỡ bằng `git revert`.

    Đòi ba thứ: tên biến phải đặt, tệp phải sửa, và **`nap_lai_env.ps1`** —
    vì `nssm` nướng ENV lúc CÀI, nên "sửa tệp rồi Restart-Service" là **không
    đủ** và kho này đã dính đúng chuyện đó ba lần.
    """
    M, _ = _chay_chot(monkeypatch, "0.0.0.0", "")
    with caplog.at_level(logging.ERROR, logger="llm_gateway"):
        with pytest.raises(SystemExit):
            M.main()
    van = "\n".join(r.getMessage() for r in caplog.records)
    for phai_co in ("LTT_LLM_TOKEN", "nap_lai_env.ps1", "LTT_LLM_HOST=127.0.0.1"):
        assert phai_co in van, "thong diep loi thieu `" + phai_co + "`"


def test_chot_dung_TRUOC_do_cong_bi_giu(monkeypatch):
    """Thứ tự có ý nghĩa vận hành, nên nó được chốt chứ không để trôi.

    Chốt cổng-bị-giữ gọi `connect()` (1,5 s) rồi `netstat` (tới 20 s). Bắt người
    vận hành chờ hết một lượt dò chỉ để nghe "bạn quên đặt token" là lãng phí
    đúng lúc họ đang vội nhất.

    Phép kiểm: `_ai_dang_nghe` được thay bằng hàm ném — nếu nó **không** bị gọi
    trong ca thiếu token thì chốt bảo mật đã chạy trước.
    """
    M, DaQuaChot = _chay_chot(monkeypatch, "0.0.0.0", "")
    with pytest.raises(SystemExit):
        M.main()          # DaQuaChot khong duoc nem ra <=> chua goi _ai_dang_nghe
