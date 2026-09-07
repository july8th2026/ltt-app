"""Sổ đăng ký model — **sinh ra** từ bản khai của WanGP, không gõ tay.

## Vì sao tệp này thay `ho_so.py`

`ho_so.py` giữ một bảng gõ tay: hai hồ sơ, hai model, một `MODEL_THEO_DAU_VAO`
chép bằng tay. Chi phí mở thêm một model là **tuyến tính** — một hồ sơ rút tay,
một lần chạy công cụ, một lần đo pod. Nên không ai mở tới model thứ ba, và độ
phủ đứng ở **2/225 = 0,9%**.

Ở đây chi phí là **hằng số**: một lần đọc bản ghi cho ra bảng năng lực của cả
225 model, và chỉ mục ngược được dựng từ chính `metadata.media_inputs` mà WanGP
khai — không từ một bảng của ta.

## 🔑 Bất biến: không một tên model nào được gõ trong tệp này

`test_740` đọc AST và làm đỏ nếu bắt gặp một hằng chuỗi khớp `^(t2v|i2v|vace|
ltx2|ti2v)_`. Một tên model gõ tay là một giá trị **sẽ trôi** khi WanGP đổi bản,
và nó trôi im lặng: model biến mất khỏi bản khai thì bảng vẫn trỏ tới nó.

## ⛔ Và không một cờ chữ cái nào được gán tay

`docs_API.md:330` nói rõ WanGP **tự điền**:

> *"start images add `S`, end images add `E` without removing `S`, source-video
> continuation adds `V`, reference images use the first declared reference mode
> containing `I`"*

Tầng dịch cờ ở phía ta vừa **thừa** vừa là chỗ suy diễn lọt vào — và chính nó
tạo ra chi phí mỗi-model đã giữ độ phủ ở 0,9%.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apps.lttvideo.cong.giao_uoc import LoiMay, May

#: Vai trò media, đặt tên `"<loại>.<vai trò>"`. Danh sách này **không** phải
#: một bảng ta nghĩ ra — nó là các khoá WanGP khai trong `metadata.media_inputs`.
#: Đọc động ở `_vai_tro()`, hằng số dưới đây chỉ để mô tả và để đối chứng.
LOAI_MEDIA = ("image", "video", "audio")


def _vai_tro(sieu: dict) -> frozenset[str]:
    """Mọi vai trò media một model **khai là nhận được**.

    ⭐ Đọc ĐỘNG: model nào khai thêm một vai trò mới (WanGP lên bản) thì nó tự
      xuất hiện ở đây. Chép một danh sách vai trò cố định vào mã là dựng lại
      đúng cơ chế đã hỏng — một bảng chép tay không tự biết mình đã cũ.
    """
    ra = set()
    for loai, khe in (sieu.get("media_inputs") or {}).items():
        if not isinstance(khe, dict):
            continue
        for ten, co in khe.items():
            if co:
                ra.add(f"{loai}.{ten}")
    return frozenset(ra)


@dataclass(frozen=True)
class SoDangKy:
    """Bảng năng lực của mọi model, cộng một chỉ mục ngược theo vai trò."""

    #: `{model_type: metadata}` — nguyên văn WanGP khai.
    theo_model: dict[str, dict]
    #: `{"image.reference": {model_type, ...}}`
    theo_vai_tro: dict[str, frozenset[str]]

    def __len__(self) -> int:
        return len(self.theo_model)

    def vai_tro_co_that(self) -> frozenset[str]:
        """Mọi vai trò **có ít nhất một model** khai.

        Dùng để đối chứng danh mục tác vụ: một vai trò gõ sai (`image.first`)
        khớp 0 model, và tác vụ ấy sẽ **im lặng biến mất** khỏi giao diện.
        """
        return frozenset(self.theo_vai_tro)

    def model_cho(self, dau_vao: tuple[str, ...] = (), *,
                  dau_ra: str = "video") -> list[str]:
        """Model nào nhận được **tất cả** vai trò trong `dau_vao`.

        Rỗng `dau_vao` nghĩa là chỉ-chữ: mọi model sinh `dau_ra` đều được.
        """
        ra = {mt for mt, sieu in self.theo_model.items()
              if dau_ra in (sieu.get("main_output") or [])}
        for vt in dau_vao:
            ra &= self.theo_vai_tro.get(vt, frozenset())
        return sorted(ra)

    def sieu(self, model_type: str) -> dict:
        try:
            return self.theo_model[model_type]
        except KeyError as e:
            raise LoiMay(
                f"model {model_type!r} khong co trong ban ghi "
                f"({len(self.theo_model)} model)") from e


def nap(may: May, *, dau_ra: str = "video") -> SoDangKy:
    """Đọc bản khai của **mọi** model một lần, rồi dựng chỉ mục ngược.

    ⚠️ Không lọc theo `dau_ra` ở đây: chỉ mục phải chứa cả model ảnh và model
       âm thanh, vì `tac_vu` sẽ hỏi tới chúng. Lọc là việc của `model_cho()`.
    """
    theo_model: dict[str, dict] = {}
    theo_vai_tro: dict[str, set[str]] = {}
    for m in may.liet_ke_model():
        mt = m.get("model_type")
        if not mt:
            continue
        sieu = m.get("metadata") or {}
        theo_model[mt] = sieu
        for vt in _vai_tro(sieu):
            theo_vai_tro.setdefault(vt, set()).add(mt)
    return SoDangKy(theo_model,
                    {k: frozenset(v) for k, v in theo_vai_tro.items()})


#: 🔑 Khoá người dùng được phép đổi. Mọi khoá khác lấy **nguyên văn** từ
#:   `get_default_settings()`.
#:
#: ⛔ Danh sách này KHÔNG phải trang trí. Nó là hàng rào giữa "người dùng chọn
#:   độ phân giải" và "người dùng đặt `num_inference_steps=200`" — cái sau đi
#:   thẳng vào hoá đơn GPU. Giữ nguyên từ `ho_so.KHOA_NGUOI_DUNG_DOI_DUOC` khi
#:   `ho_so.py` bị gỡ: mệnh đề không đổi, chỉ nơi chứa nó đổi.
KHOA_NGUOI_DUNG_DOI_DUOC = frozenset({
    "prompt",
    "negative_prompt",
    "seed",
    "resolution",
    "video_length",
    "prompt_enhancer",
})


class KhoaKhongDuocPhep(LoiMay):
    """Có khoá nằm ngoài `KHOA_NGUOI_DUNG_DOI_DUOC`.

    ⛔ Ném lỗi chứ **không** lặng lẽ bỏ qua: một tham số sai bị bỏ qua âm thầm
       vẫn đi tới GPU, chỉ là đi kèm một kết quả không ai giải thích được.
    """


#: Ánh xạ vai trò → **khoá settings** của WanGP. Đây là thứ duy nhất trong tệp
#: này gần với một bảng, và nó KHÔNG phải giá trị model — nó là tên trường của
#: chính WanGP (`image_start`, `video_guide`…), đọc từ `wgp.py`.
KHE_THEO_VAI_TRO = {
    "image.start": "image_start",
    "image.end": "image_end",
    "image.reference": "image_refs",
    "image.background": "image_refs",     # anh #1 khi co co "K"
    "image.mask": "image_mask",
    "image.control": "image_guide",
    "video.continue": "video_source",
    "video.control": "video_guide",
    "video.mask": "video_mask",
    "audio.prompt": "audio_guide",
}


def settings(may: May, model_type: str, media: dict[str, Any] | None = None,
             **tham_so: Any) -> dict:
    """Bộ tham số đầy đủ cho một lượt chạy.

    🔑 Chỉ làm **ba** việc, và không việc nào là suy diễn:

    1. lấy `get_default_settings(model_type)` — nguyên văn của WanGP
    2. gắn media vào đúng khe theo `KHE_THEO_VAI_TRO`
    3. chồng các tham số người dùng đặt (prompt, seed, negative_prompt…)

    ⛔ **Không** đặt `image_prompt_type` / `video_prompt_type`. WanGP tự điền
       khi chuẩn hoá tác vụ (`docs_API.md:330`). Đặt tay ở đây là dựng một tầng
       dịch thứ hai, và tầng ấy chính là chi phí mỗi-model.

    ⚠️ Một cái bẫy của WanGP đáng nhớ khi đọc đoạn này: `wgp.py:1458` **gỡ âm
       thầm** chữ `E` nếu không có `S`/`V`/`L`. Ta không chạm tới cờ, nên ta
       không dính bẫy — nhưng giao diện thì phải biết, vì "chỉ khung cuối"
       không tồn tại.
    """
    ra = dict(may.mac_dinh(model_type))
    ra["model_type"] = model_type
    for vai_tro, duong_dan in (media or {}).items():
        khe = KHE_THEO_VAI_TRO.get(vai_tro)
        if khe is None:
            raise LoiMay(f"vai tro {vai_tro!r} chua co khe settings tuong ung")
        # `image_refs` la mot DANH SACH co thu tu — thu tu chinh la dia chi
        # (anh #1 = boi canh khi model khai `image.background`).
        if khe == "image_refs":
            # ⚠️ WanGP dat mac dinh la `None`, KHONG phai `[]`. `setdefault`
            #    khong thay mot khoa DA TON TAI, nen `list(None)` no. Do la
            #    khac biet giua "khoa vang mat" va "khoa co gia tri rong" —
            #    hai thu ma `setdefault` gop lam mot.
            dang_co = ra.get(khe) or []
            them = (list(duong_dan) if isinstance(duong_dan, (list, tuple))
                    else [duong_dan])
            ra[khe] = list(dang_co) + them
        else:
            ra[khe] = duong_dan
    la = sorted(set(tham_so) - KHOA_NGUOI_DUNG_DOI_DUOC)
    if la:
        raise KhoaKhongDuocPhep(
            f"khoa khong duoc phep: {la}; chi cho "
            f"{sorted(KHOA_NGUOI_DUNG_DOI_DUOC)}")
    ra.update({k: v for k, v in tham_so.items() if v is not None})
    return ra
