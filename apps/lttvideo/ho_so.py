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
        ten=N_("Chuẩn 720p"),
        tep="ltt.video.chuan.v1.json",
        wangp_sha=WANGP_SHA,
        ghi_chu=(
            "Extracted from get_default_settings('t2v_2_2') on C-CLOUD "
            "2026-09-06. Set to 1280x720 / 20 steps to stay comparable with "
            "the V3 measurement."
        ),
    ),
)

_THEO_ID = {h.profile_id: h for h in _SO}


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
