"""Sổ đăng ký hồ sơ (profile) — **nguồn gốc**, không phải engine tham số.

⛔ ĐÂY KHÔNG PHẢI `VideoTemplateManager`. WanGP đã có định dạng settings và đã có
   `get_default_settings()` / `get_model_settings()`. Thứ duy nhất LTT thêm là
   câu hỏi mà WanGP **không có khái niệm** để trả lời:

       "Bản tham số nào ĐƯỢC DUYỆT, và nó thuộc phiên bản engine nào?"

   Xem `docs/VIDEO_AI_V2/REUSE_DELETE_BUILD_MATRIX.md` §B4.

🔴 **Bất biến trung tâm: hồ sơ neo vào SHA WanGP.** Tham số chỉ có nghĩa với đúng
   phiên bản engine sinh ra chúng. Một `profile_id` không neo SHA là một
   `profile_id` sẽ sai **thầm lặng** vào ngày ai đó nâng WanGP — không có gì đỏ
   lên, chỉ là video xấu đi.

⭐ Tệp trong `ho_so_data/` là **settings thật của WanGP**, rút bằng
   `session.get_default_settings("t2v_2_2")` trên C-CLOUD ngày 06/09 (bằng chứng:
   `docs/VIDEO_AI_V2/do_luong_P01/settings_t2v_2_2.json`). Không gõ tay con số
   nào — kể cả `flow_shift = 12`, con số mà V3 phải đào ra bằng tay còn WanGP đã
   khai sẵn.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from platform_core.i18n import N_

#: SHA thượng nguồn mà mọi hồ sơ dưới đây được rút ra từ đó.
#: ⛔ Đổi SHA WanGP ⇒ phải rút lại hồ sơ và đổi hằng số này. Không sửa một vế.
WANGP_SHA = "1e1dd2757f24923f008593d9d4ec09062234be20"

_THU_MUC = Path(__file__).with_name("ho_so_data")

#: Khoá người dùng đổi được mỗi lượt. Mọi khoá khác thuộc hồ sơ đã duyệt.
#: ⭐ Danh sách hẹp **có chủ đích**: bản settings đầy đủ có 113 khoá, và mở hết
#:    ra giao diện là bỏ đúng ranh giới mà kiến trúc V2.1 §2.D dựng lên.
KHOA_NGUOI_DUNG_DOI_DUOC = frozenset({
    "prompt",
    "negative_prompt",
    "seed",
    "resolution",
    "video_length",
    "prompt_enhancer",
})


class LoiHoSo(RuntimeError):
    """Gốc cho mọi lỗi của sổ đăng ký."""


class KhongCoHoSo(LoiHoSo):
    """Không có `profile_id` đó."""


class KhoaKhongDuocPhep(LoiHoSo):
    """Có khoá nằm ngoài `KHOA_NGUOI_DUNG_DOI_DUOC`.

    ⛔ Ném lỗi chứ **không** lặng lẽ bỏ qua: một tham số sai bị bỏ qua âm thầm
       vẫn đi tới GPU, chỉ là đi kèm một kết quả không ai giải thích được.
    """


@dataclass(frozen=True)
class HoSo:
    profile_id: str
    ten: str
    tep: str
    wangp_sha: str
    ghi_chu: str = ""

    def duong_dan(self) -> Path:
        return _THU_MUC / self.tep

    def doc_tham_so(self) -> dict:
        """Đọc bản settings thật của WanGP. Trả bản sao — người gọi sửa thoải mái."""
        return json.loads(self.duong_dan().read_text(encoding="utf-8"))

    def ap_dung(self, doi: dict) -> dict:
        """Ghép lựa chọn của người dùng lên hồ sơ đã duyệt.

        ⛔ Khoá ngoài danh sách cho phép ⇒ `KhoaKhongDuocPhep`.
        """
        thua = set(doi) - KHOA_NGUOI_DUNG_DOI_DUOC
        if thua:
            raise KhoaKhongDuocPhep(
                "settings keys not allowed here: " + ", ".join(sorted(thua))
            )
        tham_so = self.doc_tham_so()
        tham_so.update(doi)
        return tham_so


#: ⭐ Một hồ sơ cho baseline. Thêm hồ sơ = thêm một dòng + một tệp settings đã
#:   rút từ WanGP, **không** phải thêm mã.
_SO: tuple[HoSo, ...] = (
    HoSo(
        profile_id="ltt.video.chuan.v1",
        ten=N_("Chuẩn WanGP"),
        tep="ltt.video.chuan.v1.json",
        wangp_sha=WANGP_SHA,
        ghi_chu=(
            "Extracted from get_default_settings('t2v_2_2') on C-CLOUD "
            "2026-09-06, kept byte-for-byte at WanGP's own factory values "
            "(832x480, 30 steps).\n"
            "An earlier revision forced 1280x720 / 20 steps to stay comparable "
            "with the V3 measurement. That was a local convenience, never a "
            "WanGP recommendation: wgp.py:3219 picks 720p only when the model "
            "type name contains '720', and t2v_2_2 does not. WanGP's own route "
            "to a high-resolution result is README.md:234 -- generate at 480p, "
            "then upsample -- via the spatial_upsampling key already present in "
            "these settings."
        ),
    ),
    HoSo(
        profile_id="ltt.video.anh.v1",
        ten=N_("Chuẩn WanGP — có ảnh"),
        tep="ltt.video.anh.v1.json",
        wangp_sha=WANGP_SHA,
        ghi_chu=(
            "Extracted from get_default_settings('i2v_2_2') on C-CLOUD "
            "2026-09-06, kept at WanGP's factory values (832x480, 30 steps, "
            "flow_shift 5, guidance 3.5). "
            "image_prompt_type is 'S' -- WanGP's own default for this family "
            "(wan_handler.update_default_settings sets it when the model "
            "allows a start image). We do not compose that flag by hand; "
            "SETTINGS.md says to take it from the model's exposed choices."
        ),
    ),
)

_THEO_ID = {h.profile_id: h for h in _SO}

#: 🔑 **BẢNG CHỌN MODEL — một QUYẾT ĐỊNH của người, không phải một suy luận.**
#:
#: Đo trên ảnh chụp `metadata` thật (225 model, SHA ghim): đầu vào chỉ-chữ có
#: **150** model hợp, có ảnh **83**, có video **122**. Ngay trong hai model ta
#: dùng, cả hai đều khai `text_to_video: true`. ⇒ Dữ liệu **không** xác định
#: duy nhất câu trả lời, nên mọi cách gỡ hoà đều là bảng xếp hạng tự chế.
#:
#: ⇒ Người chọn ở đây; `chon_model.kiem_model()` **kiểm lại** lựa chọn ấy trên
#:   `metadata` để một dòng gõ sai không lặng lẽ gửi ảnh tới model không nhận
#:   ảnh.
#:
#: ⚠️ `"video"` chưa mở: cần tải thêm model điều khiển, và `A1` mới mở tới ảnh.
MODEL_THEO_DAU_VAO: dict[str, str] = {
    "chu": "t2v_2_2",     # docs/MODELS.md de cu cho general text-to-video
    "anh": "i2v_2_2",     # cung ho, nhan anh lam khung mo dau
}

#: Hồ sơ tham số đi kèm mỗi hình dạng đầu vào. **Một model — một hồ sơ**: tham
#: số của `i2v_2_2` khác `t2v_2_2` ở `flow_shift`, `guidance_scale`, và
#: `image_prompt_type`, nên dùng chung một hồ sơ là gửi tham số của model này
#: cho model kia.
HO_SO_THEO_DAU_VAO: dict[str, str] = {
    "chu": "ltt.video.chuan.v1",
    "anh": "ltt.video.anh.v1",
}

#: `A5` — giá trị khoá `prompt_enhancer` gửi mỗi lượt khi người dùng bật mở rộng.
#:
#: 🔑 **Đọc thẳng từ mã WanGP, không suy.** Khoá này có sẵn trong
#:    `models/_settings.json` (mặc định `""`), và `wgp.py:6561` đọc nó đúng một
#:    cách: `if image_start is None or not "I" in prompt_enhancer` — tức `"I"`
#:    nghĩa là **đưa cả ảnh mở đầu vào bộ mở rộng**, `"T"` là đưa chữ.
#:
#: ⭐ Vì sao `"anh"` là `"TI"` chứ không phải `"I"`: `wgp.py:3118-3121` tự nâng
#:    `"I"` thành `"TI"` khi nạp settings. Gửi `"TI"` sẵn là gửi đúng thứ WanGP
#:    sẽ dùng, nên bản ghi `params` của job khớp với thứ thật sự chạy.
MO_RONG_THEO_DAU_VAO: dict[str, str] = {
    "chu": "T",
    "anh": "TI",
}

#: Giá trị khoá khi **tắt** mở rộng — chính là giá trị xuất xưởng của WanGP.
MO_RONG_TAT = ""


def khoa_mo_rong(hinh_dang: str, *, bat: bool) -> str:
    """Giá trị `prompt_enhancer` cho một lượt.

    ⛔ Tắt ⇒ trả `""`, y hệt hồ sơ xuất xưởng. Nghĩa là đường mở rộng **không**
       đổi hành vi của lượt không bật, kể cả khi C-CLOUD đã bật bộ mở rộng.
    """
    if not bat:
        return MO_RONG_TAT
    return MO_RONG_THEO_DAU_VAO.get(hinh_dang, MO_RONG_TAT)


def liet_ke() -> tuple[HoSo, ...]:
    return _SO


def lay(profile_id: str) -> HoSo:
    try:
        return _THEO_ID[profile_id]
    except KeyError:
        raise KhongCoHoSo(
            f"no such profile {profile_id!r}; "
            f"available: {', '.join(sorted(_THEO_ID))}"
        ) from None
