"""
autotune.py — chọn tile size + số luồng NCNN theo VRAM trống (di trú từ BOT GEMINI).

Benchmark thực đo trên RTX 5060 Ti 16GB:
  fast (general-x4v3, nhẹ): alloc ~600-900MiB, gần như luôn vừa, luồng cao.
  quality (x4plus, nặng): CHỈ nhanh ở tile 512 (~10GB alloc); thiếu VRAM → rất chậm.

Bản nền tảng dùng ĐỒNG BỘ (worker 1 tiến trình 1 job) — bỏ các wrapper async.
"""
from __future__ import annotations

import logging
import subprocess

from apps.upscalevideo.schemas import Preset, PRESET_MODEL, TuneResult

logger = logging.getLogger(__name__)

_TOTAL_MB_FALLBACK = 16311     # RTX 5060 Ti 16GB


def query_vram(gpu_uuid: str = "") -> tuple:
    """Trả (total_mb, free_mb) của ĐÚNG card đang dùng.

    `gpu_uuid` là card nền tảng đã cấp cho job (`ctx.gpu_uuid`). Bỏ trống thì
    lấy card còn trống nhiều nhất — chỉ đúng cho việc dò thử, không dùng để
    quyết định lúc chạy job.

    Bản trước đọc `nvidia-smi ... .splitlines()[0]`, tức LUÔN đọc GPU 0. Đúng
    khi máy có một card; từ 2026-08-06 máy có hai, và nó sẽ báo dung lượng của
    card 0 trong khi job chạy trên card 1 — rồi chọn tile size sai và OOM.
    """
    from platform_core import gpu as gpu_mod
    gpus = gpu_mod.list_gpus()
    if not gpus:
        logger.warning("[autotune] không đọc được GPU nào → fallback thận trọng")
        return _TOTAL_MB_FALLBACK, 4000
    if gpu_uuid:
        cho = next((g for g in gpus if g.uuid == gpu_uuid), None)
        if cho is None:
            logger.warning("[autotune] không thấy GPU %s → fallback thận trọng",
                           gpu_uuid[:20])
            return _TOTAL_MB_FALLBACK, 4000
    else:
        cho = max(gpus, key=lambda g: g.free_mb)
    return cho.total_mb, cho.free_mb


def gpu_temp(gpu_uuid: str = "") -> int:
    """Nhiệt của ĐÚNG card đang dùng (°C). 0 nếu không đọc được.

    Bản trước đọc dòng đầu nvidia-smi, tức luôn báo nhiệt GPU 0 kể cả khi job
    chạy trên GPU 1 — dùng con số đó để giảm tải là giảm nhầm card.
    """
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=uuid,temperature.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=6).stdout.strip()
        for line in out.splitlines():
            uuid, temp = [p.strip() for p in line.split(",")]
            if not gpu_uuid or uuid == gpu_uuid:
                return int(temp)
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return 0


def has_nvidia_smi() -> bool:
    try:
        subprocess.run(["nvidia-smi", "-L"], capture_output=True, timeout=6)
        return True
    except Exception:  # noqa: BLE001
        return False


def pick(preset: Preset, frame_w: int, frame_h: int, reserve_mb: int = 3000,
         gpu_uuid: str = "") -> TuneResult:
    """Chọn (tile, threads) tốt nhất vừa VRAM trống, chừa reserve_mb.

    Truyền `gpu_uuid` (từ `ctx.gpu_uuid`) để đo ĐÚNG card job đang chạy — đo
    nhầm card khác là chọn tile size theo dung lượng không có thật.

    H32.6 runtime evidence (RTX 5060 Ti):
    - Fast (general-x4v3): dinh 848 MB   -> nguong budget `est_alloc` = 1000 MB
    - Quality (x4plus):    dinh 11.176 MB -> bien budget than trong theo dai

    ⛔ Con so o day PHAI khop ma ben duoi. Ban cu ghi "750 MB" trong ca docstring
       nay va mot chu thich cach `est_alloc = 1000` dung HAI dong — chu thich noi
       doi chinh ham chua no (ISSUE C).

    ⭐ BAT BIEN CUA MOI DAI (ke ca dai DAY, 26/09): `est_alloc_mb` la luong VRAM
       cau hinh tra ve CAN. Neu budget khong dai tho noi luong do thi ket qua
       PHAI dat `budget_du_cho_est=False` — ⛔ khong duoc im lang khai mot con so
       budget khong cover. Ban truoc co dung mot san cho BON dai tren (5095/
       7025/9314/10524) nhung dai DAY (`tile=256, est=3513`) va duong du phong
       Fast (`est=500`) khong co san nao: budget = 0 van khai 3513/500.
    """
    total, free = query_vram(gpu_uuid)
    budget = max(0, free - reserve_mb)
    model = PRESET_MODEL[preset]

    if preset == Preset.fast:
        # Fast = general-x4v3: ton it VRAM, du cho luong day.
        # Tile: khung LON dung tile NHO hon (256) — tile nho giam dinh VRAM.
        # Khung nho/vua dung 384. (Ban cu chu thich "large frames need larger
        # tiles" — NGUOC voi ma ngay ben duoi no.)
        long_edge = max(frame_w, frame_h)
        tile = 256 if long_edge >= 1100 else 384
        threads = "4:4:4"
        # 848 MB dinh do duoc + 152 MB an toan = 1000. Khop khai bao
        # `"upscalevideo.render.fast"` trong `manifest.gpu_vram_mb` (tra theo TEN
        # khoa, khong theo so dong — so dong da ROT mot lan: chu thich cu ghi
        # `manifest.py:63`, cho that la ~:77).
        est_alloc = 1000

        if budget < est_alloc:
            tile, threads, est_alloc = 200, "2:2:2", 500
        return TuneResult(model=model, tile=tile, threads=threads,
                          est_alloc_mb=est_alloc, free_mb=free, budget_mb=budget,
                          fast_path=True, budget_du_cho_est=budget >= est_alloc)

    # Quality = x4plus: ton nhieu VRAM, luong than trong.
    # Tile chon theo BUDGET (khong theo kich thuoc khung): tile to = it lan ghep
    # bien hon, nhung ton VRAM hon. ⚠️ Anh huong cua tile len DO NET la CHUA DO
    # o day — dung khai "net hon". Moi dai khai dung `est` cua no.
    # ⭐ CHOT 2026-09-27 — tile 512 duoc GIU CO Y, khong phai vi chua ai do.
    #
    # Do duoc (v3 836x576, 60 khung, 3 luot, trung vi — §K cua
    # `docs/UPSCALE_V2_CORRECTION/08_BENCHMARK_RESULTS.md`):
    #     tile 256 -> 88,83 s,  4 761 MiB   <- NHANH HON 8,7 %, it VRAM hon 64 %
    #     tile 512 -> 96,53 s, 13 135 MiB
    # Bien do nay LON hon nhieu mot bac (ba luot tile 256 lech 0,3 %), nen no la
    # hieu ung THAT, khong phai nhieu.
    #
    # ⛔ NHUNG dau ra KHAC NHAU: so PNG vs PNG tren 12 khung cho PSNR 45,2-46,5 dB,
    #    SSIM 0,990-0,992, va 0/12 khung giong het tung bit. Nguon 836x576 => tile
    #    512 chia 2x2 manh, tile 256 chia 4x3 => tile nho NHIEU DUONG GHEP hon.
    #
    # Chu du an chot: UU TIEN CHAT LUONG. 8,7 % toc do doi lay mot khac biet chat
    # luong DO DUOC, trong chinh preset ten la Quality — preset khach chon VI ho
    # uu tien chat luong hon toc do. Danh doi do tu mau thuan voi ly do ton tai
    # cua preset.
    #
    # ⚠️ Muon lay 8,7 % ve sau thi phai lam TRUOC: (a) mot nguoi NHIN hai dau ra
    #    canh nhau tren noi dung that, (b) do tren clip co VUNG PHANG / CHUYEN MAU
    #    MUOT — noi vet ghep lo ro nhat, ma bo 4 video test hien tai KHONG co.
    #    `tests/test_4906_upscale_chot_tile_quality.py` khoa quyet dinh nay lai.
    FAST_TILE, FAST_ALLOC, SAFETY = 512, 10024, 500
    if budget >= FAST_ALLOC + SAFETY:
        return TuneResult(model=model, tile=FAST_TILE, threads="1:2:2",
                          est_alloc_mb=FAST_ALLOC, free_mb=free, budget_mb=budget,
                          fast_path=True, budget_du_cho_est=True)
    if budget >= 9314:
        tile, est = 448, 9314
    elif budget >= 7025:
        tile, est = 384, 7025
    elif budget >= 5095:
        # ⛔ San dai PHAI >= `est` cua chinh no. Ban cu ghi `budget >= 5000` roi
        #    khai `est = 5095`: job co budget 5000..5094 duoc nhan vao roi khai
        #    can nhieu hon minh duoc phep (vuot san cua chinh dai 95 MB).
        tile, est = 320, 5095
    else:
        # Dai DAY: cau hinh nho nhat ta co so do (`tile=256` -> dinh ~3513 MB).
        # Duoi 3513 MB budget thi KHONG con dai nao nho hon de tut ve, va tu
        # choi job o day la mot quyet dinh SAN PHAM (khach mat tinh nang khi GPU
        # dang bi job khac chiem) — nen ta VAN chay, nhung noi that ra rang
        # budget khong dai tho noi `est`. `budget_du_cho_est=False` + `warning`
        # la cho noi that do; ⛔ dung "sua" bang cach ha `est` xuong bang budget,
        # vi `est` la luong CAN, khong phai luong DUOC PHEP.
        tile, est = 256, 3513
    warn = (f"GPU đang bận (trống {free}MiB, budget {budget}MiB). Quality (x4plus) "
            f"sẽ RẤT chậm. Nên chuyển sang Fast hoặc chạy khi GPU rảnh.")
    logger.warning("[autotune] %s", warn)
    return TuneResult(model=model, tile=tile, threads="1:2:2",
                      est_alloc_mb=est, free_mb=free, budget_mb=budget,
                      fast_path=False, warning=warn,
                      budget_du_cho_est=budget >= est)
