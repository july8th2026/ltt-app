"""Danh mục tác vụ — biến 225 model thành một danh sách việc người dùng hiểu.

## 🔑 Ranh giới giữa QUYẾT ĐỊNH và SUY LUẬN

Đo được trên bản ghi thật: **150/225 model đều khai `text_to_video`**. Dữ liệu
của WanGP **không xác định duy nhất** model nào nên dùng cho "tạo video từ mô
tả" — nó chỉ nói model nào *làm được*.

⇒ Mỗi tác vụ gồm hai phần, và chúng khác hẳn nhau về bản chất:

| Phần | Là gì | Ai quyết |
|---|---|---|
| `dau_vao` | vai trò media tác vụ cần | **suy từ dữ liệu** — `so_dang_ky` lọc |
| `model` | dùng model nào | **quyết định của người**, ghi rõ lý do |

⛔ Đừng xoá cột thứ hai để "cho tự động hoàn toàn". Tự động ở đây nghĩa là chọn
   bừa một trong 150 model, và người dùng trả tiền cho lựa chọn ấy.

⭐ Nhưng quyết định của người vẫn **bị máy kiểm lại**: `test_741` đòi mọi
  `model` phải có thật trong bản ghi **và** khai đủ `dau_vao`. Một quyết định
  không kiểm được là một quyết định sẽ trôi.

## Thêm tác vụ = thêm một dòng

Không sửa `routes.py`, không sửa `jobs.py`, không sửa giao diện. Model mới xuất
hiện trong WanGP thì `so_dang_ky` tự thấy; tác vụ mới chỉ cần một dòng ở đây và
một bản ghi `mac_dinh__<model>.json`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from platform_core.i18n import N_


@dataclass(frozen=True)
class TacVu:
    """Một việc người dùng chọn được trên giao diện."""

    ma: str
    nhan: object                      # chuoi dich lazy
    #: Vai trò media **bắt buộc** — dùng để lọc model, và để giao diện biết
    #: phải mời người dùng đính kèm gì.
    dau_vao: tuple[str, ...] = ()
    #: 🔑 QUYẾT ĐỊNH của người. Rỗng nghĩa là tác vụ chưa mở.
    model: str = ""
    #: Vì sao chọn model ấy. Bắt buộc khi `model` khác rỗng — một quyết định
    #: không kèm căn cứ là một quyết định không ai dám đổi.
    can_cu: str = ""
    #: Đính kèm tối đa. `1` cho khung mở đầu; VACE nhận nhiều.
    so_tep_toi_da: int = 0
    mo: bool = False


#: ⚠️ `mo=False` nghĩa là tác vụ **đã biết đường đi** nhưng chưa có bản ghi
#:   `mac_dinh__<model>.json`, nên chưa chạy được. Giữ nó ở đây thay vì xoá:
#:   danh sách này là bản đồ, và một bản đồ chỉ vẽ chỗ đã tới thì vô dụng.
TAC_VU: dict[str, TacVu] = {
    "chu_thanh_video": TacVu(
        ma="chu_thanh_video",
        nhan=N_("Tạo video từ mô tả"),
        dau_vao=(),
        model="t2v_2_2",
        can_cu=("Wan 2.2 T2V — 150/225 model deu khai text_to_video, nen day la "
                "mot LUA CHON: ho Wan la ho da do gia von va da chay that o V2.1."),
        so_tep_toi_da=0,
        mo=True,
    ),
    "anh_thanh_video": TacVu(
        ma="anh_thanh_video",
        nhan=N_("Tạo video từ một ảnh"),
        dau_vao=("image.start",),
        model="i2v_2_2",
        can_cu=("Wan 2.2 I2V — cung ho voi t2v_2_2 nen cung mot muc gia von, va "
                "no khai `image.start`. `t2v_2_2` KHONG khai khe anh nao."),
        so_tep_toi_da=1,
        mo=True,
    ),
    "nhieu_anh_tham_chieu": TacVu(
        ma="nhieu_anh_tham_chieu",
        nhan=N_("Video theo nhiều ảnh tham chiếu"),
        dau_vao=("image.reference",),
        model="vace_14B",
        can_cu=("VACE khai `image.reference` + `image.background` + "
                "`image.injected_frames`, tuc mo mot lan tam hang muc cua bang "
                "cham diem. Chua co ban ghi `mac_dinh__vace_14B`."),
        so_tep_toi_da=5,
    ),
    "boi_canh_va_nhan_vat": TacVu(
        ma="boi_canh_va_nhan_vat",
        nhan=N_("Bối cảnh riêng, nhân vật riêng"),
        dau_vao=("image.background", "image.reference"),
        model="vace_14B",
        can_cu=("Anh #1 giu nen, anh #2..N bi CAT nen tu dong. Day la nang luc "
                "Seedance 2.0 KHONG co."),
        so_tep_toi_da=5,
    ),
    "theo_video_dieu_khien": TacVu(
        ma="theo_video_dieu_khien",
        nhan=N_("Video theo chuyển động của video mẫu"),
        dau_vao=("video.control",),
        model="vace_14B",
        can_cu="VACE khai 16 che do dieu khien (pose/depth/canny/flow/...).",
        so_tep_toi_da=1,
    ),
    "noi_dai_video": TacVu(
        ma="noi_dai_video",
        nhan=N_("Nối dài một video có sẵn"),
        dau_vao=("video.continue",),
        model="",
        can_cu="",
        so_tep_toi_da=1,
    ),
}


def co_trong_so(model_type: str) -> bool:
    """Trọng số của model đã nằm trên đĩa của máy dựng chưa.

    🔴 Đo 08/09 trên máy thật: **1/225 model** có trọng số (`t2v_2_2`), 4 phần,
       **220 thiếu** — trong đó có `i2v_2_2`, model của một tác vụ đang mở.

    ⭐ Đây là **cửa thứ ba**, và nó khác hai cửa kia. Trước đó ta canh:
         1. ô chọn tệp mời gì   ↔  tác vụ nhận gì
         2. tác vụ cần vai trò  ↔  model khai vai trò
       Cả hai đều xanh cho `anh_thanh_video`. Nhưng có **bản khai** không có
       nghĩa là có **trọng số**: WanGP sẽ đi tải ~30 GB giữa lượt chạy, hoặc
       hỏng — sau khi nền tảng đã giữ credit.
    """
    from apps.lttvideo.cong.may_gia_lap import GOC_BAN_GHI  # noqa: PLC0415

    tep = GOC_BAN_GHI / "kha_dung.json"
    if not tep.is_file():
        # Chua ghi thi KHONG doan la co. Doan "co" la mo mot cua khoa.
        return False
    d = json.loads(tep.read_text(encoding="utf-8")).get("du_lieu") or {}
    return bool((d.get(model_type) or {}).get("available"))


def dang_mo() -> list[TacVu]:
    """Tác vụ **chạy được ngay**. Giao diện chỉ mời những cái này.

    Ba điều kiện, và cả ba đều phải đúng:

      1. `mo=True`                  — ta đã quyết định mở nó
      2. có `mac_dinh__<model>`     — có bản khai tham số
      3. `co_trong_so(model)`       — trọng số đã trên đĩa

    ⛔ Thiếu vế 3 thì tác vụ hiện trên giao diện, người dùng bấm, nền tảng giữ
       credit — rồi máy dựng đi tải hàng chục GB hoặc hỏng.
    """
    return [t for t in TAC_VU.values()
            if t.mo and t.model and co_trong_so(t.model)]


def lay(ma: str) -> TacVu:
    try:
        return TAC_VU[ma]
    except KeyError as e:
        raise LoiTacVu(f"khong co tac vu {ma!r}") from e


class LoiTacVu(RuntimeError):
    """Tác vụ không tồn tại, chưa mở, hoặc đính kèm không khớp."""


def kiem_dinh_kem(tv: TacVu, so_tep: int) -> None:
    """⛔ Cửa trước phải khớp cửa sau.

    Bài học đã trả giá: ô chọn tệp mời `video/mp4` trong khi đường job không
    nhận, nên người dùng bị **giữ credit → job hỏng → hoàn credit**. Tiền trả
    lại, thời gian và niềm tin thì không.
    """
    if not tv.mo:
        raise LoiTacVu(f"tac vu {tv.ma!r} chua mo")
    if so_tep > tv.so_tep_toi_da:
        raise LoiTacVu(
            f"tac vu {tv.ma!r} nhan toi da {tv.so_tep_toi_da} tep, "
            f"nhan duoc {so_tep}")
    if so_tep < len(tv.dau_vao) and tv.dau_vao:
        raise LoiTacVu(
            f"tac vu {tv.ma!r} can {len(tv.dau_vao)} tep dinh kem")


def media_cho(tv: TacVu, duong_dan: list[str]) -> dict[str, object]:
    """Ánh xạ danh sách tệp **đã có thứ tự** sang `{vai_tro: đường dẫn}`.

    🔑 Thứ tự **là** địa chỉ. Với `("image.background", "image.reference")`,
    tệp #1 là bối cảnh và phần còn lại là nhân vật/đạo cụ — đúng cách WanGP đọc
    `image_refs` khi cờ chứa `K` (`wan_handler.py:825-832`).
    """
    if not tv.dau_vao:
        return {}
    ra: dict[str, object] = {}
    if len(tv.dau_vao) == 1:
        vt = tv.dau_vao[0]
        ra[vt] = duong_dan if tv.so_tep_toi_da > 1 else duong_dan[0]
        return ra
    # Nhieu vai tro: cai DAU lay mot tep, cai CUOI om phan con lai.
    for i, vt in enumerate(tv.dau_vao[:-1]):
        ra[vt] = duong_dan[i]
    ra[tv.dau_vao[-1]] = duong_dan[len(tv.dau_vao) - 1:]
    return ra


#: Giá trị `prompt_enhancer` khi **tắt** — chính là giá trị xuất xưởng của WanGP.
MO_RONG_TAT = ""


def khoa_mo_rong(tv: TacVu, *, bat: bool) -> str:
    """Giá trị `prompt_enhancer` cho một lượt.

    Ngữ nghĩa đọc từ `wgp.py`: `"T"` = đưa **chữ** vào bộ mở rộng, `"I"` = đưa
    thêm **ảnh mở đầu** (`wgp.py`: `if image_start is None or not "I" in
    prompt_enhancer`).

    ⭐ Suy từ chính `dau_vao` của tác vụ, **không** từ một bảng chép tay: tác vụ
      nào có đầu vào ảnh thì bộ mở rộng nên nhìn thấy ảnh ấy. Thêm tác vụ ảnh
      mới thì nó tự đúng.

    ⭐ Vì sao gửi `"TI"` chứ không `"I"`: `wgp.py:3118-3121` tự nâng `"I"` thành
      `"TI"` khi nạp settings. Gửi sẵn `"TI"` nghĩa là bản ghi `params` của job
      khớp với thứ **thật sự chạy** — không thì hai bên lệch nhau một chữ và
      không ai biết bên nào đúng.

    ⛔ Tắt ⇒ trả `""`, y hệt hồ sơ xuất xưởng. Đường mở rộng **không** đổi hành
       vi của lượt không bật, kể cả khi C-CLOUD đã bật sẵn bộ mở rộng.
    """
    if not bat:
        return MO_RONG_TAT
    return "TI" if any(v.startswith("image.") for v in tv.dau_vao) else "T"
