"""Bộ điều phối ảnh GIẢ — dùng chung cho mọi test cần một job ảnh chạy trọn.

## Vì sao là một module dùng chung

Ba tệp test (`test_187`, `test_207`, và các tệp fixture) đều cần đúng một thứ:
*một job `taoanh`/`thumbnail` chạy hết mà không chạm mạng, không chạm GPU*.
Trước pha 06 chúng làm việc đó bằng cách vá `jobs._goi_gemini` — mỗi tệp một
bản. Khi `_goi_gemini` biến mất, cả ba **cùng đỏ vì một lý do**, và đó là dấu
hiệu chúng đáng lẽ phải dùng chung một khuôn.

⛔ Đây KHÔNG phải một lớp che như `rao_provider_retire` (đã hết hạn và bị gỡ ở
   pha 06.3). Nó không làm một provider đã ngừng trông như còn sống; nó chỉ
   thay **máy vẽ** bằng một cái giả — đúng ranh giới mà `_dieu_phoi()` được
   tách ra để phục vụ.

⭐ Bản giả **ghi ảnh thật vào kho lưu trữ**, đúng như máy B làm qua vé
   presigned. Thiếu bước đó thì mọi phép kiểm về chấm điểm, về tải ảnh về, về
   quyết toán theo ảnh thật sẽ xanh-rỗng.
"""
from __future__ import annotations

import io


def png(size=(64, 36), color=(180, 30, 25)) -> bytes:
    from PIL import Image
    out = io.BytesIO()
    Image.new("RGB", size, color).save(out, format="PNG")
    return out.getvalue()


class DieuPhoiGia:
    """Đứng chỗ `platform_core.image_gen.dieu_phoi.DieuPhoi`.

    `so_anh_tra_ve` nhỏ hơn `so_anh` mô phỏng cảnh máy B chỉ tải lên được một
    phần — cảnh có thật (`runner.py` trả `image_keys[:so]`) và là cảnh mà mọi
    phép kiểm quyết toán phải sống sót qua.
    """

    def __init__(self, *, so_anh_tra_ve=None, no=None, khi_goi=None):
        self.so_anh_tra_ve = so_anh_tra_ve
        self.no = no
        #: Gọi một lượt mỗi khi `chay` được gọi. Vài phép kiểm đếm **lượt gọi
        #: nhà cung cấp** để chứng minh sandbox/idempotency không gọi thật.
        self.khi_goi = khi_goi
        self.da_goi: list[dict] = []

    def chay(self, *, job_id, prompt, model="hidream-o1", mode="t2i", ref_keys=(),
             so_anh=1, negative_prompt="", params=None, ti_le="",
             tien_to_khoa="anh"):
        from platform_core.image_gen.dieu_phoi import KetQuaAnh
        from platform_core.storage import get_storage

        self.da_goi.append({"job_id": job_id, "prompt": prompt, "model": model,
                            "mode": mode, "ref_keys": list(ref_keys),
                            "so_anh": so_anh, "ti_le": ti_le,
                            "tien_to_khoa": tien_to_khoa})
        if self.khi_goi is not None:
            self.khi_goi()
        if self.no is not None:
            raise self.no

        so = so_anh if self.so_anh_tra_ve is None else self.so_anh_tra_ve
        storage = get_storage()
        keys = []
        for i in range(so):
            k = f"{str(tien_to_khoa).strip('/')}/{job_id}/{i}.png"
            storage.put(k, io.BytesIO(png()), content_type="image/png")
            keys.append(k)
        return KetQuaAnh(job_id, tuple(keys), prompt, True, ())


def tiem(monkeypatch, *modules, **kw) -> DieuPhoiGia:
    """Vá `_dieu_phoi` của từng module `jobs` truyền vào. Trả về bản giả."""
    gia = DieuPhoiGia(**kw)
    for mod in modules:
        monkeypatch.setattr(mod, "_dieu_phoi", lambda: gia)
    return gia
