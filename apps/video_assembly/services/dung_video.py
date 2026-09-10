"""Nghiệp vụ của App `video_assembly`: clip thô + nhạc → một video hoàn chỉnh.

**GUI, Macro Node và (sau này) API đều gọi hàm ở đây** — bất biến #2.

## Mười ba giai đoạn, giữ nguyên từ `bot_dungvideo/engine/runner.py`

```
 0 kiểm đầu vào      5 nhúng CLIP          10 trộn tiếng
 1 làm sạch video    6 khớp dòng thời gian 11 phụ đề
 2 phiên âm          7 ghép video          12 tự chấm điểm
 3 lấy mẫu clip      8 tách nhạc (Demucs)
 4 lọc               9 nhạc nền
```

## 🔴 `timeline.mode` MẶC ĐỊNH LÀ `sequential` Ở ĐÂY, không phải `semantic`

Mã legacy để `semantic` (khớp CLIP) làm mặc định. **Production thì đặt
`sequential`** — khớp theo tiền tố tên tệp (`^(\\d{3,4})-scene`). Đo ngày
2026-09-09 trong `configs/pipeline.yaml` đang chạy; xem
`docs/migration/workflow_apps/08_CAU_HINH_THAT_TREN_PRODUCTION.md` §1.

⇒ App này lấy **giá trị đang chạy** làm mặc định, không lấy giá trị trong mã.
Cả hai chế độ đều giữ; chỉ thứ tự ưu tiên đảo lại.

⚠️ Và khớp `semantic` là **tham lam, phụ thuộc thứ tự**: mỗi đoạn tiêu một clip
rồi tăng `used`, nên kết quả đổi theo thứ tự đoạn. Một bản "tốt hơn" dùng khớp
tối ưu toàn cục sẽ cho tập clip **khác** — và khác theo hướng trông đúng hơn.
Phép đo parity phải là **dãy `(đoạn → clip)` đúng thứ tự**, không phải tập hợp.

## Bốn model thật trong một job

`whisper` · `YOLO` · `CLIP` · `Demucs`. Bot legacy tự quản bằng `gpu_arbiter.py`
(1.520 dòng); ở đây việc ấy thuộc `ToolSpec.admission_resource` + `slots`.

⚠️ Món nợ đi kèm phải nhận: ngân sách `-n` **không đếm tiến trình cháu**. Ngày
03/09 đo được **12 tiến trình `demucs`, mỗi cái 460–984% CPU**, vì
`demucs_runner` không đặt `torch.set_num_threads`. Mọi phép kiểm nạp model thật
phải nằm sau rào `LTT_TEST_NANG` (`tests/rao_chan_nang.py`).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger("apps.video_assembly")

#: Hồ sơ STT của App này — tên NĂNG LỰC (`platform_core/stt/ho_so.py`).
HO_SO_STT = "khong_moc_tu_vad_trong"

#: Chế độ khớp dòng thời gian. **`sequential` là giá trị ĐANG CHẠY**, không phải
#: mặc định trong mã legacy — xem docstring đầu tệp.
CHE_DO_KHOP = ("sequential", "semantic")
CHE_DO_MAC_DINH = "sequential"


class LoiDungVideo(ValueError):
    """Đầu vào hoặc kết quả không dùng được."""


@dataclass(frozen=True)
class YeuCau:
    thu_muc_clip: str
    thu_muc_nhac: str = ""
    che_do_khop: str = CHE_DO_MAC_DINH
    bat_demucs: bool = True
    bat_phu_de: bool = True
    bat_cham_diem: bool = False
    cau_hinh: dict = field(default_factory=dict)


@dataclass(frozen=True)
class KetQua:
    duong_video: str
    so_doan: int
    so_clip_dung: int
    che_do_khop: str
    canh_bao: tuple[str, ...] = field(default_factory=tuple)

    def as_result(self) -> dict:
        return {
            "video": self.duong_video,
            "segments": self.so_doan,
            "clips_used": self.so_clip_dung,
            "timeline_mode": self.che_do_khop,
            "warnings": list(self.canh_bao),
        }


def chuan_hoa(params: dict) -> YeuCau:
    """Tham số thô → `YeuCau`. Từ chối **trước khi chạy**.

    ⚠️ Một job này tiêu bốn model và hàng phút GPU. Từ chối sớm rẻ hơn nhiều so
       với dừng ở giai đoạn 7.
    """
    p = dict(params or {})
    clip = str(p.get("clips") or p.get("thu_muc_clip") or "").strip()
    if not clip:
        raise LoiDungVideo("thieu tham so `clips`")

    che_do = str(p.get("che_do_khop") or CHE_DO_MAC_DINH).strip().lower()
    if che_do not in CHE_DO_KHOP:
        raise LoiDungVideo(
            f"`che_do_khop` phai la mot trong {list(CHE_DO_KHOP)}, "
            f"nhan {che_do!r}")

    cau_hinh = p.get("cau_hinh") or {}
    if not isinstance(cau_hinh, dict):
        raise LoiDungVideo("`cau_hinh` phai la mot doi tuong")

    # 🔴 Cong tac khong co duong lay khoa thi TU CHOI o day, dung de job chay.
    #
    #    Bot legacy lay khoa Gemini tu `configs/pipeline.yaml` — mot truong VAN
    #    BAN THUAN trong tep cau hinh. Nen tang nay khong co truong ay, va cung
    #    khong duoc co: bi mat di qua `platform_core/api_pool`.
    #
    # ⛔ Nhung engine chuyen nguyen ven **khong nem loi** khi thieu khoa. Doc
    #    `engine/runner.py:677`: no ghi `api_key="missing (env GEMINI_API_KEY)"`
    #    roi VAN goi `evaluate_video(gemini_api_key="")`, du vao bien moi truong.
    #    Tren nen tang nay bien do khong duoc dat.
    #
    # ⇒ Neu khong chan, khach bat cong tac "tu cham diem", **tra credit cho ca
    #   luot**, va nhan lai mot giai doan khong the chay. Mot no-op im lang o
    #   tang tinh tien la thu dat nhat trong ba lua chon.
    #
    # ⚠️ Day KHONG phai ban sua cuoi cung. Ban sua that la noi `evaluation` vao
    #    `api_pool` (provider `gemini` da co san). Cho toi luc do, rang buoc nay
    #    NHIN THAY DUOC thay vi mot cong tac gia. Xem
    #    `docs/migration/workflow_apps/31_...`.
    if bool(p.get("bat_cham_diem", False)) and not str(
            (cau_hinh.get("evaluation") or {}).get("gemini_api_key") or "").strip():
        raise LoiDungVideo(
            "`bat_cham_diem` chua dung duoc: giai doan tu cham diem can mot khoa "
            "Gemini, ma nen tang chua noi no vao `api_pool`. Tat cong tac nay di.")

    return YeuCau(
        thu_muc_clip=clip,
        thu_muc_nhac=str(p.get("music") or p.get("thu_muc_nhac") or "").strip(),
        che_do_khop=che_do,
        bat_demucs=bool(p.get("bat_demucs", True)),
        bat_phu_de=bool(p.get("bat_phu_de", True)),
        bat_cham_diem=bool(p.get("bat_cham_diem", False)),
        cau_hinh=dict(cau_hinh),
    )


def dung_cau_hinh(yc: YeuCau) -> dict:
    """Ghép `cau_hinh` của người dùng lên trên các giá trị ĐANG CHẠY.

    ⛔ Thứ tự ghép là một quyết định: giá trị người dùng nằm **trên**, nhưng
       những khoá điều khiển tài nguyên (`timeline.mode`, ba cờ giai đoạn) thì
       lấy từ `YeuCau` — chúng đã qua `chuan_hoa`, còn `cau_hinh` thì chưa.
       Nếu để `cau_hinh` ghi đè chúng, một khoá gõ sai sẽ bật lại một giai đoạn
       mà người dùng vừa tắt.
    """
    cfg = dict(yc.cau_hinh)
    cfg.setdefault("whisper", {})
    cfg["timeline"] = {**cfg.get("timeline", {}), "mode": yc.che_do_khop}
    cfg["demucs"] = {**cfg.get("demucs", {}), "enable": yc.bat_demucs}
    cfg["subtitle"] = {**cfg.get("subtitle", {}), "enable": yc.bat_phu_de}
    cfg["evaluation"] = {**cfg.get("evaluation", {}),
                         "enable": yc.bat_cham_diem}
    return cfg


def chay(yc: YeuCau, thu_muc_lam_viec: Path, duong_ra: str, *,
         tien_do: Optional[Any] = None) -> KetQua:
    """Gọi engine đã chuyển. Không đụng Sheet, Drive, GPU arbiter hay hàng đợi.

    ⚠️ Import engine **trong hàm**, không ở đầu tệp: `runner` kéo theo torch,
       CLIP, YOLO và Demucs. Import ở tầng module nghĩa là mỗi lần `registry`
       quét `apps/` — kể cả trong một lượt `pytest` không chạm App này — đều nạp
       chúng. Đó là hàng trăm MB và vài giây, cho một việc không ai xin.
    """
    from .engine.runner import run_local_job

    def bao(pt: int, mo_ta: str) -> None:
        if tien_do is not None:
            tien_do(pt, mo_ta)

    clip = Path(yc.thu_muc_clip)
    if not clip.is_dir():
        raise LoiDungVideo(f"khong co thu muc clip: {clip}")

    bao(2, "bat dau")
    cfg = dung_cau_hinh(yc)

    # 🔴 MOC TIEN DO GIUA CHUNG — va no la chuyen HUY, khong phai chuyen hien thi.
    #
    #    `ctx.progress()` cua nen tang tu no kiem `JOB_CANCELLED` roi nem
    #    `JobCancelled` (`job_runner.py:112-116`). Nen mat do moc CHINH LA do tre
    #    huy. Truoc bản vá: 3 moc thang tren `est_duration_s=900` => mot lenh huy
    #    phai cho ~300 giay, va trong ca 300 giay do job van giu lease 8 GB VRAM.
    #
    #    `runner.py` co 14 loi goi `tracker.start_stage`. Moc vao do => ~64 giay.
    from .engine import error_context as _ec
    tong = 14                                    # so `start_stage` trong runner
    dem = {"n": 0}

    def _moc(stage: str, chi_tiet: str = "") -> None:
        dem["n"] += 1
        # 2..96: chua 2 cho "bat dau" va 100 cho "xong".
        bao(min(96, 2 + int(94 * dem["n"] / tong)), str(stage)[:60])

    _cu = _ec.MOC_NGOAI
    _ec.MOC_NGOAI = _moc
    try:
        run_local_job(cfg, str(clip), yc.thu_muc_nhac or "", duong_ra,
                      str(thu_muc_lam_viec))
    except LoiDungVideo:
        raise
    except BaseException as e:
        # ⛔ `JobCancelled` KHONG duoc goi lai thanh loi engine.
        #
        #    Ban dau o day la `except Exception` goi TAT CA thanh
        #    `LoiDungVideo("engine that bai: ...")`. Mot lenh huy di qua `bao()`
        #    -> `ctx.progress()` -> `JobCancelled`, roi bi cai `except` ay bat va
        #    doi ten thanh mot that bai — khach bam Huy va nhan ve mot job LOI.
        #
        # ⚠️ Nhan dien theo TEN LOP chu khong import `job_runner`: tang App khong
        #    duoc phu thuoc vao noi bo cua worker, va `ranh gioi import giua cac
        #    tang` cua gate soi dung dieu do.
        if type(e).__name__ == "JobCancelled" or isinstance(e, KeyboardInterrupt):
            raise
        raise LoiDungVideo(f"engine that bai: {type(e).__name__}: {e}") from e
    finally:
        _ec.MOC_NGOAI = _cu

    ra = Path(duong_ra)
    if not ra.is_file() or ra.stat().st_size == 0:
        # 🔴 Một tệp 0 byte là kết cục thật của một chuỗi ffmpeg hỏng giữa
        #    chừng, và ffmpeg vẫn trả 0 ở vài nhánh. Không bắt ở đây thì job
        #    báo THANH CONG và khách tải về một tệp rỗng.
        raise LoiDungVideo("engine chay xong nhung khong ra video")

    bao(100, "xong")
    dong = _doc_dong_thoi_gian(thu_muc_lam_viec)
    return KetQua(
        duong_video=str(ra),
        so_doan=len(dong),
        so_clip_dung=len({str(d.get("clip", {}).get("file", "")) for d in dong}),
        che_do_khop=yc.che_do_khop,
    )


def _doc_dong_thoi_gian(thu_muc: Path) -> list[dict]:
    """Dòng thời gian engine ghi ra. Thiếu thì trả rỗng — nó chỉ dùng để **đếm**,
    không dùng để quyết định gì, nên một tệp thiếu không được làm hỏng job."""
    import json

    for ten in ("timeline.json", "matched_timeline.json"):
        tep = thu_muc / ten
        if tep.is_file():
            try:
                du_lieu = json.loads(tep.read_text(encoding="utf-8"))
            except (OSError, ValueError) as e:
                log.warning("khong doc duoc %s: %s", ten, e)
                return []
            return du_lieu if isinstance(du_lieu, list) else []
    return []
