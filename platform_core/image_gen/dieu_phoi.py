"""
dieu_phoi.py — chạy MỘT job sinh ảnh bằng model nội bộ, từ đầu đến cuối. (H37/A7)

⭐ Đây là chỗ nối ba mảnh đã dựng riêng:

    prompt khách
      ① prompt_dich   → dịch phần mô tả, giữ nguyên chữ-cần-vẽ
      ② storage       → cấp presigned PUT (và presigned GET cho ảnh tham chiếu)
      ③ cong_render   → gửi máy B, chờ, nhận khoá ảnh
      → trả về khoá R2 để app hiển thị / cho tải

⛔ MÁY B KHÔNG GIỮ BÍ MẬT NÀO CỦA NỀN TẢNG (Q102). Nó không có khoá R2, không có
   mật khẩu CSDL. Ảnh **vào** bằng presigned GET, **ra** bằng presigned PUT — cả
   hai đều do máy A cấp, có hạn, và ràng buộc đúng một khoá.

⛔ BẬN KHÔNG PHẢI HỎNG. `cong_render.BanError` đi thẳng ra ngoài, **không** bọc
   thành lỗi chung. App phải phân biệt được để nói với khách "máy nhà đang bận,
   còn khoảng N phút" thay vì "sinh ảnh thất bại". Và tầng gọi **không được** tự
   chuyển sang đám mây — đổi model sau lưng khách là đánh tráo sản phẩm (D-010).

⛔ PROMPT PHẢI DỊCH TRƯỚC. Model chỉ hiểu Anh/Trung (D-027). Bỏ bước này là ảnh ra
   không liên quan gì tới yêu cầu, mà **không có lỗi nào báo**.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from platform_core.i18n import _ as _t

from . import cong_render as CR
from . import prompt_dich as PD

log = logging.getLogger(__name__)

#: Trần chờ một job. Ảnh tham chiếu mất ~190 giây, ảnh thường ~58 giây ở 30 bước;
#: ở 50 bước và lúc máy bận thì lâu hơn. 15 phút là rộng rãi mà vẫn không treo mãi.
TRAN_CHO_S = 900.0

#: Nhịp hỏi trạng thái. Thưa hơn nữa thì khách chờ oan; dày hơn thì phí lượt gọi.
NHIP_HOI_S = 3.0

#: Hạn của vé PUT. Phải > trần chờ, không thì vé hết hạn giữa lúc máy B đang vẽ.
TTL_PUT_S = 3600

#: Hạn của vé GET cho ảnh tham chiếu. Máy B tải chúng ngay đầu job.
TTL_GET_S = 1800


class DieuPhoiError(Exception):
    """Hỏng thật ở tầng điều phối. `BanError` KHÔNG thuộc loại này."""


@dataclass(frozen=True)
class KetQuaAnh:
    job_id: str
    image_keys: tuple
    prompt_da_gui: str
    da_dich: bool
    canh_bao: tuple = ()

    def as_dict(self) -> dict:
        return {"job_id": self.job_id, "image_keys": list(self.image_keys),
                "prompt_da_gui": self.prompt_da_gui, "da_dich": self.da_dich,
                "canh_bao": list(self.canh_bao)}


@dataclass
class DieuPhoi:
    cong: CR.CongRender
    storage: Any
    #: `goi_llm(text, he_thong) -> str`. Thường là `dich_gemini.tao_ham_dich(db)`.
    goi_llm: Optional[Callable] = None
    tran_cho_s: float = TRAN_CHO_S
    nhip_hoi_s: float = NHIP_HOI_S
    #: Tiêm được để test không phải ngủ thật.
    sleep: Callable[[float], None] = time.sleep
    now: Callable[[], float] = time.monotonic
    giu_nguoi_viet: bool = True

    def chay(self, *, job_id: str, prompt: str, model: str = "hidream-o1",
             mode: str = "t2i", ref_keys=(), so_anh: int = 1,
             negative_prompt: str = "", params: Optional[dict] = None,
             tien_to_khoa: str = "anh") -> KetQuaAnh:
        """Chạy trọn một job. Ném `CR.BanError` khi máy bận, `DieuPhoiError` khi hỏng."""
        if not job_id:
            raise DieuPhoiError("thieu job_id")
        so_anh = max(1, int(so_anh or 1))

        # ① Dịch. Hỏng ở đây thì hỏng job — gửi bản gốc là giao ảnh sai (D-027).
        try:
            chuan_bi = PD.dich_prompt_anh(prompt, goi_llm=self.goi_llm,
                                          giu_nguoi_viet=self.giu_nguoi_viet)
        except PD.DichThatBai as e:
            raise DieuPhoiError(str(e)) from e

        # ② Vé vào và vé ra. Máy B không tự đọc/ghi R2 được (Q102).
        refs = self._ve_vao(ref_keys)
        khoa, put_urls = self._ve_ra(job_id, so_anh, tien_to_khoa)

        # ③ Gửi. `BanError` cố ý KHÔNG bị bọc lại.
        self.cong.gui(job_id=job_id, model=model, mode=mode,
                      prompt=chuan_bi.prompt_model, negative_prompt=negative_prompt,
                      put_urls=put_urls, image_keys=khoa, refs=refs,
                      params=dict(params or {}))

        t = self._cho(job_id)
        if not t.thanh_cong:
            raise DieuPhoiError(_t("Máy tạo ảnh báo lỗi: {ma} {loi}").format(
                ma=t.error_code or "?", loi=t.error_message or ""))

        # 🔴 KHÔNG ĐƯỢC LẤY `khoa` LÀM PHƯƠNG ÁN DỰ PHÒNG Ở ĐÂY.
        #
        #    `khoa` là danh sách khoá lưu trữ **cấp phát trước** khi vẽ — nó tồn
        #    tại kể cả khi không ảnh nào được tải lên. Trước đây dòng này là
        #    `t.image_keys or khoa`, nghĩa là cổng trả về rỗng thì ta vẫn khai đủ
        #    `so_anh` ảnh, tính tiền đủ `so_anh` ảnh, và khách bấm vào thì
        #    404 từng cái một.
        #
        #    Cổng đã hứa điều ngược lại: `runner.py` trả **đúng số ảnh tải lên
        #    được** (`image_keys[:so]`) và tự `fail` khi không có ảnh nào. Nên
        #    "thành công mà rỗng" là một mâu thuẫn của cổng, không phải một
        #    trường hợp cần chữa cháy im lặng.
        keys = tuple(t.image_keys or ())
        if not keys:
            raise DieuPhoiError(_t(
                "Máy tạo ảnh báo thành công nhưng không trả về ảnh nào."))
        return KetQuaAnh(job_id, keys,
                         chuan_bi.prompt_model, chuan_bi.da_dich, chuan_bi.canh_bao)

    # ── các bước ─────────────────────────────────────────────────────────────
    def _ve_vao(self, ref_keys) -> list:
        """Presigned GET cho từng ảnh tham chiếu."""
        ra = []
        for k in (ref_keys or ()):
            url = self.storage.try_url_for(k, ttl_s=TTL_GET_S)
            if not url:
                # ⛔ Backend cục bộ trả None. Máy B KHÔNG có đường nào khác để lấy
                #    ảnh — nói thẳng thay vì gửi một job chắc chắn hỏng giữa chừng.
                raise DieuPhoiError(_t(
                    "Không cấp được đường tải ảnh tham chiếu ({khoa}). Chế độ dùng "
                    "ảnh tham chiếu cần lưu trữ R2.").format(khoa=k))
            ra.append({"url": url, "role": "edit"})
        return ra

    def _ve_ra(self, job_id: str, so_anh: int, tien_to: str) -> tuple:
        khoa, urls = [], []
        for i in range(so_anh):
            k = f"{tien_to.strip('/')}/{job_id}/{i}.png"
            ve = self.storage.try_put_url(k, ttl_s=TTL_PUT_S, content_type="image/png")
            if not ve:
                raise DieuPhoiError(_t(
                    "Không cấp được vé tải ảnh lên. Model nội bộ cần lưu trữ R2 — "
                    "máy tạo ảnh không giữ khoá lưu trữ nào."))
            khoa.append(ve.key)
            urls.append(ve.url)
        return khoa, urls

    def _cho(self, job_id: str) -> CR.TrangThaiJob:
        het = self.now() + self.tran_cho_s
        loi_lien_tiep = 0
        while self.now() < het:
            self.sleep(self.nhip_hoi_s)
            try:
                t = self.cong.trang_thai(job_id)
                loi_lien_tiep = 0
            except CR.CongRenderError as e:
                # Một cú vấp mạng LAN không phải là máy B chết. Ba cú liên tiếp thì là.
                loi_lien_tiep += 1
                if loi_lien_tiep >= 3:
                    raise DieuPhoiError(_t(
                        "Mất liên lạc với máy tạo ảnh: {loi}").format(loi=e)) from e
                continue
            if t.xong:
                return t
        # Hết giờ: huỷ để máy B không vẽ tiếp một thứ không ai còn chờ.
        self.cong.huy(job_id)
        raise DieuPhoiError(_t("Quá {phut:.0f} phút mà chưa xong — đã huỷ.").format(
            phut=self.tran_cho_s / 60))
