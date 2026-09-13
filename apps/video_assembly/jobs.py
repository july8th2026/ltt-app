"""Handler chạy trong worker cho `video_assembly.run`.

Mỏng có chủ ý: giải các clip về một thư mục tạm, gọi
`services/dung_video.chay()`, đẩy video lên kho. Nghiệp vụ ở service — cùng hàm
mà GUI và Macro Node gọi.

⚠️ Job này tiêu **bốn model** và hàng phút GPU. Mọi thứ có thể từ chối được thì
   từ chối **trước** khi chạm giai đoạn 1.
"""
from __future__ import annotations

import io
import logging
import tempfile
import uuid
from pathlib import Path

from platform_core import storage

from .services import dung_video

log = logging.getLogger("apps.video_assembly.jobs")


class LoiVideoAssembly(RuntimeError):
    """Lỗi nghiệp vụ — worker biến thành job `error`, có hoàn phần giữ chỗ."""


def _tai_ve_nhieu(khoa: list[str], thu_muc: Path) -> Path:
    """Giải danh sách khoá về một thư mục. Trả về chính thư mục đó.

    ⚠️ Giữ **thứ tự và tên** như khoá gốc: chế độ khớp `sequential` đọc tiền tố
       tên tệp (`^\\d{3,4}-scene`). Đổi tên khi tải về là làm hỏng đúng chế độ
       mà production đang dùng — và hỏng im lặng, vì `semantic` vẫn chạy.
    """
    kho = storage.get_storage()
    thu_muc.mkdir(parents=True, exist_ok=True)
    for k in khoa:
        ten = Path(str(k)).name or f"{uuid.uuid4().hex}.mp4"
        with kho.open(str(k)) as nguon, open(thu_muc / ten, "wb") as f:
            for khoi in iter(lambda: nguon.read(4 * 1024 * 1024), b""):
                f.write(khoi)
    return thu_muc


def handle(params: dict, ctx=None) -> dict:
    yc = dung_video.chuan_hoa(params)
    owner = str((params or {}).get("owner_id") or "chung")
    khoa_clip = (params or {}).get("clips") or []
    if isinstance(khoa_clip, str):
        khoa_clip = [khoa_clip]
    if not khoa_clip:
        raise LoiVideoAssembly("khong co clip nao")

    def tien_do(pt: int, mo_ta: str) -> None:
        if ctx is not None and hasattr(ctx, "progress"):
            ctx.progress(pt, mo_ta)

    with tempfile.TemporaryDirectory(prefix="video_assembly_") as tam:
        goc = Path(tam)
        try:
            thu_muc_clip = _tai_ve_nhieu(list(khoa_clip), goc / "clip")
            thu_muc_nhac = ""
            if yc.thu_muc_nhac:
                _tai_ve_nhieu([yc.thu_muc_nhac], goc / "nhac")
                thu_muc_nhac = str(goc / "nhac")
        except (OSError, KeyError, ValueError) as e:
            raise LoiVideoAssembly(f"khong doc duoc dau vao: {e}") from e

        lam_viec = goc / "lam_viec"
        lam_viec.mkdir(exist_ok=True)
        ra = goc / "ra.mp4"
        try:
            ket = dung_video.chay(
                dung_video.YeuCau(
                    thu_muc_clip=str(thu_muc_clip), thu_muc_nhac=thu_muc_nhac,
                    che_do_khop=yc.che_do_khop, bat_demucs=yc.bat_demucs,
                    bat_phu_de=yc.bat_phu_de, bat_cham_diem=yc.bat_cham_diem,
                    cau_hinh=yc.cau_hinh),
                lam_viec, str(ra), tien_do=tien_do)
        except dung_video.LoiDungVideo as e:
            raise LoiVideoAssembly(str(e)) from e

        # ⛔ Đẩy lên kho TRONG `with`: ra khỏi khối là thư mục tạm bị xoá.
        khoa_ra = f"video_assembly/{owner}/{uuid.uuid4().hex}.mp4"
        with open(ket.duong_video, "rb") as f:
            storage.get_storage().put(khoa_ra, io.BytesIO(f.read()))

    log.info("video_assembly xong job=%s doan=%d clip=%d che_do=%s",
             getattr(ctx, "job_id", "?"), ket.so_doan, ket.so_clip_dung,
             ket.che_do_khop)
    kq = ket.as_result()
    kq["video"] = khoa_ra
    return kq
