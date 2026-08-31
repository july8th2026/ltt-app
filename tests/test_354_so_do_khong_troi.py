"""Số đo đã ghi phải KHỚP với con số đang dùng trong mã — và với nhau.

## Vì sao

`docs/LTT_VOICE/do_v1.json` là bản đo thật trên RTX 5060 Ti (30/08/2026). Nhiều
hằng số trong mã **lấy từ nó**: sàn VRAM để xếp chỗ, tỉ lệ ký tự/giây để báo giá,
trần thời gian chạy. Nhưng chúng là hai bản chép, và hai bản chép không có phép
kiểm là hai bản chép **sẽ lệch**.

Cái lệch đó không kêu: job vẫn chạy, tiền vẫn trừ, chỉ là con số ai đó dựa vào
để quyết định đã cũ. Đó là toàn bộ lý do tệp này tồn tại.

⛔ NÓ KHÔNG PHẢI PHÉP ĐO. Nó không nạp model, không chạm GPU, không cần
   `vieneu-venv`. Nó chỉ đối chiếu **giấy tờ với mã**. Muốn đo lại thì chạy
   `voice_sidecar/do_v1.py` trên máy có card, rồi cập nhật `do_v1.json` — và
   khi đó tệp này sẽ nói ngay nếu số mới phá một giả định nào trong mã.

## Hợp đồng `job.result`

Phần cuối tệp chốt **hình dạng** `result` mà handler trả về. Giao diện đọc thẳng
`audio_key`, `duration_s`, `credit_cost` để hiện lịch sử; đổi tên một khoá là
làm trắng một cột mà không ai được báo.
"""
from __future__ import annotations

import json
import pathlib

GOC = pathlib.Path(__file__).resolve().parents[1]
DO_V1 = GOC / "docs" / "LTT_VOICE" / "do_v1.json"


def _do() -> dict:
    return json.loads(DO_V1.read_text(encoding="utf-8"))["phep"]


# ═══════════════════════════════════════════════ VRAM ════════════════════════

def test_san_vram_khai_trong_manifest_cao_hon_dinh_da_do():
    """Sàn xếp chỗ phải nằm TRÊN đỉnh đã đo, nếu không job bị xếp vào card chật.

    ⚠️ `gpu_vram_mb` là sàn ĐỂ XẾP CHỖ, không phải hạn mức cứng. Khai thấp hơn
       thực tế thì nền tảng vẫn cho job chạy — chỉ là nó có thể xếp job vào một
       card gần đầy, rồi hỏng vì hết bộ nhớ ở giữa chừng. Một lỗi chỉ xuất hiện
       khi máy bận, tức đúng lúc tệ nhất.
    """
    from platform_core.registry import discover

    d = _do()["ranh.pytorch.vram_dinh"]
    dinh = float(d["dinh_mb"])
    dat_truoc = float(d["dat_truoc_mb"])

    mf = next(i.manifest for i in discover() if i.manifest.slug == "ltt_voice")
    for jt in ("ltt_voice.synthesize", "ltt_voice.enroll"):
        khai = mf.vram_for(jt)
        assert khai >= dat_truoc, (
            f"{jt} khai {khai} MB, thap hon VRAM torch DA DAT TRUOC "
            f"({dat_truoc} MB, dinh cap phat {dinh} MB) trong `do_v1.json`.\n"
            f"Sàn xep cho phai tren so da do — neu khong, job bi xep vao card "
            f"gan day roi hong giua chung, va chi hong khi may ban.")


def test_san_vram_khong_khai_thua_qua_dang():
    """Khai thừa cũng có giá: job phải chờ một card trống hơn mức nó cần.

    Không có ngưỡng chuẩn nào cho "thừa bao nhiêu là quá", nên chốt một bội số
    rộng rãi — nó bắt lỗi gõ nhầm một số 0, không bắt sự dè dặt hợp lý.
    """
    from platform_core.registry import discover

    dat_truoc = float(_do()["ranh.pytorch.vram_dinh"]["dat_truoc_mb"])
    mf = next(i.manifest for i in discover() if i.manifest.slug == "ltt_voice")
    khai = mf.vram_for("ltt_voice.synthesize")
    assert khai <= dat_truoc * 5, (
        f"khai {khai} MB, gap hon nam lan muc da do ({dat_truoc} MB). Khai thua "
        f"lam job phai cho mot card trong hon muc no can.")


# ═══════════════════════════════════════════════ tốc độ ══════════════════════

def test_ti_le_ky_tu_moi_giay_dung_de_bao_gia_KHONG_cao_hon_do_that():
    """🔴 Hướng lệch ở đây quyết định khách bị thu thừa hay thiếu.

    `gia.KY_TU_MOI_GIAY_UOC` chia số ký tự để ước ra số giây, rồi giữ chỗ theo
    đó. Khai tỉ lệ **cao hơn** thực tế ⇒ ước ra ÍT giây hơn ⇒ giữ thiếu ⇒ quyết
    toán vượt phần đã giữ.

    Đo 31/08 trên ba độ dài: 19,6 / 19,8 / 19,9 ký tự mỗi giây, và biên báo giá
    ổn định +11 %. Giữ tỉ lệ khai **dưới** mức đã đo là giữ nguyên hướng lệch an
    toàn đó.
    """
    from apps.ltt_voice import gia

    d = _do()
    do_that = [v["ky_tu_moi_giay"] for k, v in d.items()
               if k.startswith("ranh.pytorch.do_dai.") and v.get("ok")]
    assert do_that, "khong tim thay so do do_dai nao trong do_v1.json"

    assert gia.KY_TU_MOI_GIAY_UOC <= min(do_that), (
        f"bao gia dung {gia.KY_TU_MOI_GIAY_UOC} ky tu/giay, CAO HON muc cham "
        f"nhat da do ({min(do_that)}). Uoc ra it giay hon thuc te ⇒ giu thieu "
        f"⇒ quyet toan vuot phan da giu.")


def test_tran_thoi_gian_chay_rong_hon_luot_dai_nhat_da_do():
    """Trần tồn tại để bắt job TREO, không để bắt job chậm."""
    from platform_core.registry import discover

    d = _do()
    lau_nhat = max(v["gen_s"] for k, v in d.items()
                   if k.startswith("ranh.pytorch.do_dai.") and v.get("ok"))
    mf = next(i.manifest for i in discover() if i.manifest.slug == "ltt_voice")
    tran = mf.runtime_limit_for("ltt_voice.synthesize", default=0)
    assert tran >= lau_nhat * 10, (
        f"tran {tran}s chi gap {tran / lau_nhat:.1f} lan luot dai nhat da do "
        f"({lau_nhat}s). Tran nay de bat job TREO; dat sat qua thi no bat nham "
        f"job cham.")


# ═════════════════════════════════════ hợp đồng `job.result` ═════════════════

def test_result_giu_dung_bon_khoa_ma_giao_dien_doc():
    """🔴 Giao diện đọc thẳng `result`; đổi tên một khoá là làm trắng một cột.

    Trang Lịch sử hiện thời lượng, credit và nút nghe lại từ `job.result`. Không
    có hợp đồng thì một lần đổi tên trong `features.py` sẽ làm trắng cột đó, và
    **không phép kiểm nào của app kêu** — dữ liệu vẫn đúng, chỉ là không ai đọc
    được nó nữa.

    ⭐ Chốt là TẬP CON, không phải tập bằng: thêm khoá mới luôn an toàn, bỏ hay
       đổi tên thì không. Cùng luật với bánh cóc khác trong kho này.
    """
    from apps.ltt_voice import features

    yc = features.YeuCau(text="xin chao", owner_id="u1")
    kq = features.KetQua(yeu_cau=yc, audio_key="voice/out/u1/j1/tieng.wav",
                         giay=3.25, text_da_chuan_hoa="xin chao", so_doan=1)
    r = kq.as_result()

    #: Giao diện và Public API dựa vào đúng những khoá này.
    BAT_BUOC = {"audio_key", "duration_s", "credit_cost", "text",
                "so_doan", "phien_ban_gia"}
    thieu = BAT_BUOC - set(r)
    assert not thieu, (
        f"`as_result()` thieu {sorted(thieu)}. Giao dien doc thang cac khoa nay; "
        f"bo mot cai la lam trang mot cot ma khong phep kiem nao keu.")

    assert isinstance(r["duration_s"], (int, float))
    assert isinstance(r["credit_cost"], int)
    assert isinstance(r["audio_key"], str) and r["audio_key"]


def test_credit_cost_luon_co_mat_ke_ca_khi_khong_do_duoc_thoi_luong():
    """⛔ Thiếu `credit_cost` thì nền tảng thu TRỌN phần đã giữ, im lặng.

    Đúng lỗi H37 mắc và đã sửa 24/08: xin 4 ảnh, máy trả 2, khách vẫn bị thu 4.
    """
    from apps.ltt_voice import features

    yc = features.YeuCau(text="xin chao", owner_id="u1")
    kq = features.KetQua(yeu_cau=yc, audio_key="k", giay=0.0,
                         text_da_chuan_hoa="xin chao")
    r = kq.as_result()
    assert "credit_cost" in r
    assert r["credit_cost"] == 0, (
        "khong do duoc thoi luong ma van tinh tien — thu tien khong bang chung "
        "te hon mat mot it tien (khuon 3.5)")
