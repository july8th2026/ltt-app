"""
quality_gate.py — cổng KỸ THUẬT cho đầu ra Upscale Video.

⭐ Cổng này chỉ trả lời MỘT câu: *"tệp ta vừa tạo có đúng là video ta đã hứa
không?"* — tồn tại, mở được, đúng khung, đúng thời lượng, đúng codec, có tiếng
khi khách đòi tiếng. Nó **không** chấm chất lượng mô hình.

## Vì sao chia hai lớp (chốt 2026-09-26)

Bản trước của tệp này tự nhận là cổng **PSNR/SSIM/VMAF** nhưng:

- gọi `ffprobe` để lấy PSNR/SSIM/VMAF — `ffprobe` **không có filter graph**, ba
  đại lượng đó là filter của `ffmpeg` (`-lavfi psnr|ssim|libvmaf`);
- không hề có video **tham chiếu**: nó đo full-reference với **chính đầu ra**;
- truyền **khoá R2** vào `subprocess` như đường dẫn local;
- đọc **toàn bộ MP4** vào RAM rồi đưa `bytes` cho `PIL.Image.open` (PIL không
  giải mã được MP4 dù có sửa).

⇒ Nó **luôn** thất bại, và vì `jobs.py` chỉ log cảnh báo, **mọi job của khách**
đều mang một chuỗi "kiểm chất lượng thất bại" phản ánh lỗi mã, không phản ánh
đầu ra — đồng thời trả tiền cho một lượt đọc R2 vô ích. Toàn văn:
`docs/UPSCALE_V2_CORRECTION/00_CURRENT_TRUTH.md` ISSUE H.

**Chất lượng MÔ HÌNH (PSNR/SSIM/VMAF) không thuộc đường job khách.** Nó cần
video tham chiếu và một bộ dữ liệu chuẩn ⇒ chạy **ngoại tuyến** ở
`apps/qualitylab` (nơi đã có phép đo PSNR/VMAF thật + test:
`tests/test_164_quality_lab_upscale.py`, `tests/test_166_quality_lab_upscale_video.py`).
⛔ Đừng dựng lại phép đo đó ở đây.

## Cổng này chạy TRÊN TỆP LOCAL, TRƯỚC khi upload

Đó là chỗ duy nhất đường dẫn thật tồn tại — nên không còn cửa nào để lẫn khoá
R2 với đường dẫn tệp.
"""
from __future__ import annotations

from platform_core.i18n import _ as _t
import logging
import os

logger = logging.getLogger(__name__)

# Tệp nhỏ hơn mức này thì chắc chắn không phải video dùng được (header + vài KB).
MIN_BYTES = 10 * 1024

# Thời lượng lệch quá tỉ lệ này so với kỳ vọng ⇒ cảnh báo (không đánh đỏ job):
# ffmpeg làm tròn theo GOP/keyframe nên lệch nhỏ là bình thường.
DUNG_SAI_THOI_LUONG = 0.05      # 5 %
DUNG_SAI_THOI_LUONG_TOI_THIEU_S = 1.0

# Dung sai chiều RỘNG, tính bằng pixel. Chuỗi encode dùng `scale=-2:H`: ffmpeg tự
# tính chiều rộng theo tỉ lệ nguồn rồi **làm tròn về số CHẴN** (yêu cầu của
# yuv420p). Vậy `round(src_w * H / src_h)` có thể lệch tối đa 1 px vì làm tròn tỉ
# lệ và thêm 1 px vì ép chẵn ⇒ 2 px. Đòi khớp CHÍNH XÁC ở đây là đánh đỏ những
# job hoàn toàn đúng.
DUNG_SAI_KHUNG_PX = 2

# Encoder → họ codec mà luồng đầu ra PHẢI có. Dùng để bắt ca "xin HEVC, nhận
# H.264" (ISSUE J) ngay tại runtime, thay vì để nó lặng lẽ đi ra API.
# ⚠️ CHỈ liệt kê những tên `jobs._resolve_encoder` có thể THẬT SỰ trả về. QSV/AMF
#    đã bị bỏ khỏi đây cùng lúc bị bỏ khỏi `schemas.py`: `ffmpeg -encoders` liệt
#    kê chúng nhưng cả bốn chết lúc chạy trên máy này (đo 2026-09-26).
HO_CODEC = {
    "h264_nvenc": "h264",
    "libx264": "h264",
    "hevc_nvenc": "hevc",
    "libx265": "hevc",
}


def bat_cong() -> bool:
    """Cổng kỹ thuật có bật không. Mặc định BẬT — nó rẻ và là lưới duy nhất.

    Tắt bằng `LTT_UPSCALE_TECH_GATE=0` (dùng khi cần cứu một job đang gấp).
    """
    return os.environ.get("LTT_UPSCALE_TECH_GATE", "1").strip() not in ("0", "false", "no")


def kiem_tra_dau_ra(out_local: str, *, target_h: int, src_w: int, src_h: int,
                    expect_encoder: str, expect_audio: bool,
                    expect_duration_s: float,
                    cancel_check=None, env: dict | None = None) -> dict:
    """Soi tệp đầu ra local. Trả `{"ok", "loi", "canh_bao", "do"}`.

    `loi` (LIST) khác rỗng ⇒ đầu ra **hỏng**, job phải đỏ: khách không được trả
    tiền cho một tệp không mở được. `canh_bao` ⇒ ghi log + trả về, không đánh đỏ.

    ⚠️ Không bao giờ ném ra ngoài: mọi lỗi bất ngờ của chính cổng thành một
    `canh_bao`. Một cổng tự sập **không được** làm đỏ một job có đầu ra tốt.

    ## ⭐ Mọi kỳ vọng ở đây phải ĐỘC LẬP với đầu ra (chốt 26/09)

    Bản trước nhận `expect_w`/`expect_h`, nhưng `jobs.handle` lấy hai số đó từ
    `ff.encode_full`/`concat_and_mux`, mà hai hàm ấy lại `probe_video(out_path)`
    — tức **so tệp với chính nó**. Một phép kiểm không bao giờ đỏ được là một
    phép kiểm KHÔNG TỒN TẠI, trong khi chú thích lại khai "con số ta TỰ tính ra"
    và bản ghi sửa sai coi ISSUE M là đã đóng. Nay cổng nhận **lời hứa**:

    - `target_h`: chiều CAO khách xin (`params["target_height"]`).
    - `src_w`/`src_h`: khung **NGUỒN** đã áp xoay, tức đúng `info["w"]`/`info["h"]`
      của `ff.probe_video(<nguồn>)` (hàm đó đã đổi w↔h cho rotation 90/270). Từ
      hai số này ra tỉ lệ đã hứa. Đầu ra dựng từ PNG nên KHÔNG có metadata xoay
      ⇒ `probe_video(<đầu ra>)` không đổi chiều, hai bên cùng hệ quy chiếu.
    - `expect_duration_s`: thời lượng container mà chuỗi encode HỨA. ⚠️ Nó KHÔNG
      phải "độ dài phần video khách xem": `ff.encode_full` map audio nguồn
      **nguyên vẹn** và không có `-shortest`, nên khi có audio thì container dài
      bằng luồng DÀI NHẤT. `jobs._thoi_luong_hua` là nơi duy nhất tính nó; đừng
      truyền `eff_dur` vào đây (một preview 8 s có audio 265 s sẽ ăn cảnh báo
      giả trên MỌI job — ISSUE M/N).
    """
    do: dict = {}
    loi: list[str] = []
    canh_bao: list[str] = []

    # --- 1. Tệp có thật và không rỗng ------------------------------------
    if not os.path.isfile(out_local):
        return {"ok": False,
                "loi": [_t("không có tệp đầu ra: {0}").format(out_local)],
                "canh_bao": [], "do": do}
    size = os.path.getsize(out_local)
    do["bytes"] = size
    if size < MIN_BYTES:
        return {"ok": False,
                "loi": [_t("tệp đầu ra chỉ {0} B (< {1} B)").format(size, MIN_BYTES)],
                "canh_bao": [], "do": do}

    # --- 2. Mở được bằng ffprobe -----------------------------------------
    #     Dùng lại ff.probe_video: MỘT nơi biết cách đọc video (§'dùng lại').
    from apps.upscalevideo import ff
    try:
        info = ff.probe_video(out_local, cancel_check=cancel_check, env=env)
    except Exception as e:  # noqa: BLE001 — ffprobe đỏ = đầu ra hỏng thật
        return {"ok": False,
                "loi": [_t("ffprobe không đọc được đầu ra: {0}").format(e)],
                "canh_bao": [], "do": do}

    do.update({"w": info["w"], "h": info["h"], "duration_s": info["duration"],
               "vcodec": info["vcodec"], "has_audio": info["has_audio"],
               "fps": info["fps"]})

    if info["w"] == 0 or info["h"] == 0:
        loi.append(_t("đầu ra không có luồng video đọc được"))
    if info["duration"] <= 0:
        loi.append(_t("đầu ra có thời lượng 0"))

    # --- 3. Đúng khung hình ta đã HỨA ------------------------------------
    #     Lời hứa = "cao đúng `target_h`, giữ tỉ lệ nguồn". Cả hai vế đều lấy từ
    #     NGOÀI đầu ra (tham số khách + probe nguồn) nên phép kiểm này đỏ được
    #     thật. Cao: khớp CHÍNH XÁC (`scale=-2:H` đặt thẳng H). Rộng: ±
    #     `DUNG_SAI_KHUNG_PX` vì ffmpeg ép số chẵn.
    if info["w"] and info["h"] and target_h > 0 and src_w > 0 and src_h > 0:
        rong_hua = round(src_w * target_h / src_h)
        do["khung_hua"] = f"~{rong_hua}x{target_h}"
        if info["h"] != target_h:
            loi.append(_t("chiều cao sai: chờ {0}, nhận {1}")
                      .format(target_h, info['h']))
        elif abs(info["w"] - rong_hua) > DUNG_SAI_KHUNG_PX:
            loi.append(
                _t("tỉ lệ khung sai: nguồn {0}x{1} ở {2}p phải cho rộng "
                   "~{3}px (±{4}), nhận {5}px")
                .format(src_w, src_h, target_h, rong_hua, DUNG_SAI_KHUNG_PX,
                        info['w']))
    elif target_h > 0 and not (src_w > 0 and src_h > 0):
        canh_bao.append(_t("không có khung nguồn để đối chiếu tỉ lệ đầu ra"))

    # --- 4. Codec THẬT khớp encoder đã dùng ------------------------------
    ho_cho = HO_CODEC.get(expect_encoder)
    ho_that = (info["vcodec"] or "").lower()
    if ho_cho and ho_that and ho_cho != ho_that:
        loi.append(_t("codec sai: encoder {0} phải cho {1}, luồng lại là {2}")
                  .format(expect_encoder, ho_cho, ho_that))
    elif ho_cho is None:
        canh_bao.append(_t("không biết encoder {0!r} thuộc họ codec nào")
                        .format(expect_encoder))

    # --- 5. Thời lượng trong dung sai ------------------------------------
    #     `expect_duration_s` PHẢI là thời lượng CONTAINER đã hứa (luồng dài
    #     nhất), do `jobs._thoi_luong_hua` tính — không phải độ dài phần video.
    #     `<= 0` nghĩa là caller khai "không dự đoán được" ⇒ bỏ qua phép này chứ
    #     không đoán.
    if expect_duration_s > 0 and info["duration"] > 0:
        lech = abs(info["duration"] - expect_duration_s)
        nguong = max(expect_duration_s * DUNG_SAI_THOI_LUONG,
                     DUNG_SAI_THOI_LUONG_TOI_THIEU_S)
        do["lech_thoi_luong_s"] = round(lech, 3)
        if lech > nguong:
            canh_bao.append(
                _t("thời lượng lệch {0:.2f}s (chờ ~{1:.2f}s, dung sai {2:.2f}s)")
                .format(lech, expect_duration_s, nguong))

    # --- 6. Có tiếng khi khách đòi tiếng ---------------------------------
    if expect_audio and not info["has_audio"]:
        canh_bao.append(
            _t("khách yêu cầu giữ tiếng nhưng đầu ra không có luồng audio"))

    return {"ok": not loi, "loi": loi, "canh_bao": canh_bao, "do": do}
