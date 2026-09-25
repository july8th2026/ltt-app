"""Executor AN cua Auto Scan Video — lan `ffmpeg`.

Khach khong bao gio nhin thay app nay: `surface="runtime"`, `public=False`,
`catalog_parent="auto_scan_video"`. No ton tai vi mot ly do ky thuat duy nhat.

## Vi sao phai tach app thay vi khai `requires=("ffmpeg","gpu")` o mot cho

`platform_core/jobs.py:158-164` loc quyen nhat job theo **APP**:

    eligible = [app for app in discover()
                if set(app.manifest.requires).issubset(capabilities)]

Khong co dinh tuyen theo `job_type`. Nen mot app khai ca hai nang luc chi duoc
nhat boi mot lan co **du ca hai**; tren doi hinh chia lan
(`LTT_WORKER_POOLS="api:8, ffmpeg:2, gpu:2"`) job cua no vo hinh voi moi worker
va nam `queued` **mai mai, khong loi nao bao**.

`tests/test_400_asv_bat_bien_thi_hanh.py::test_app_gop_ca_hai_nang_luc_bi_ca_HAI_lan_le_tu_choi`
tai hien dung canh do bang mot app that.

## Vi sao RENDER nam o day chu khong o lan GPU

`MVP_CONTRACT.md` D-ASV-03: MVP **sao chep** luong video chu khong ma hoa lai,
vi khong giai doan nao doi mot diem anh. Nen RENDER la mot phep mux
(`-c:v copy -c:a aac`), khong phai mot phep transcode — no can ffmpeg, khong can
card. Do la ly do giai doan **dai nhat** cua san pham thoi tranh GPU voi cac ho
khac tren may.

## 🔴 Doan tren dung khi co MOT preset, va no khong duoc doc lai khi co hai

Preset `smart_localize` **buoc phai ma hoa lai** — cat bang stream copy chi cat
duoc tai keyframe, va do that tren chinh chuoi nay cho GOP 8,333 giay. Tuc tien
de *"khong giai doan nao doi mot diem anh"* het dung tu ngay preset cat ra doi,
va khong ai quay lai sua ban khai.

Hau qua do duoc (kiem toan pha 26, B24-01): `_vram_can("asv_media.render")` tra
**0**, nen `_giu_gpu` khong xin lease nao, nen `ctx.gpu_uuid` rong, nen
`chon_bo_ma_hoa(cho_phep_gpu=False)` tra `libx264` — **tren mot may co
`h264_nvenc`**. Bo ma hoa phan cung da duoc viet, duoc test, va khong bao gio
voi toi duoc.

## Con so 500 la con so DA DO, khong phai con so cho dep

Do ngay 04/09 tren chinh may nay (hai RTX 5060 Ti), mot phien `h264_nvenc`
1080p, `-preset p5`, lay mau 0,2 giay/lan qua `nvidia-smi`:

    dinh muc dung VRAM cua card:  +228 MiB so voi duong co so
    encoder util dinh:            88%
    thong luong:                  244 fps (~8x realtime)

⇒ 500 MiB la 228 cong khoang du. **Co y de NHO**: nguyen tac o doan tren —
  "giai doan dai nhat khong duoc tranh GPU voi ho khac" — van duoc ton trong ve
  **ban chat**, vi 500 MiB tren mot card 16 GiB khong day duoc `asv_gpu` (xin
  2.200 va 6.000) ra khoi cho. Va `gpu_lease` la **best-effort**: khong con card
  thi job van chay, chi la chay bang CPU.

⚠️ Preset `preserve` cung se xin lease nay du no chi mux. Do la gia phai tra cho
   viec `gpu_vram_mb` khoa theo `job_type` chu khong theo tham so — chia doi
   `job_type` de tranh 500 MiB la mot thay doi hop dong duong ong de doi lay
   3% cua mot card. Ghi ra day thay vi giau di.

## ⛔ Cai `gpu_vram_mb` KHONG do duoc, va no moi la thu khan hiem

Phep do tren cho thay mot phien 1080p da lam **encoder util 88%**. Tuc tai
nguyen that su khan hiem la **engine NVENC**, khong phai VRAM — va `gpu_lease`
giu cho theo VRAM, nen no **khong** ngan hai lan ma hoa dong thoi tren cung mot
card. Voi 500 MiB moi lease, mot card 16 GiB cho lot hang chuc lease.

⇒ Ghi thanh rui ro `V4-R13`, khong tu them mot co che thu hai o day: mot bo dem
  suat rieng trong app la tao chu so huu thu hai cho cung mot tai nguyen, dung
  dieu `pipeline.CHUOI` da tu choi lam cho demucs.
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.registry import AppManifest

#: Giai doan gia cua pha 05 khong ton gi. Gia THAT thuoc pha 21.
#:
#: ⛔ Tra 0 la CO Y va no phai o lai ke ca khi co engine that: chi `asv_run` giu
#:    tien (ADR-001 D4). Mot job giai doan tu khai gia khac 0 se lam khach bi
#:    tinh tien hai lan cho cung mot viec — mot lan o run, mot lan o day.
def _gia(params: dict) -> int:
    return 0


MANIFEST = AppManifest(
    slug="asv_media",
    display_name=N_('Auto Scan Video — xử lý media'),
    route_prefix="/asv-media",
    summary=N_('Executor nội bộ của Auto Scan Video. Không phải sản phẩm riêng.'),
    icon="🎞️",

    catalog_parent="auto_scan_video",
    surface="runtime",
    public=False,
    enabled=False,
    lifecycle="internal",

    job_types=(
        "asv_media.media_prepare",
        "asv_media.content_process",
        "asv_media.voice_synthesis",
        "asv_media.timing_align",
        "asv_media.compose",
        "asv_media.render",
        "asv_media.image_finish",
        "asv_media.qc",
    ),
    requires=("ffmpeg",),
    credit_cost=_gia,

    #: 🔑 CHI `render`. Xem docstring dau tep: con so 500 da do (228 MiB dinh +
    #:    du), va no o day de `ctx.gpu_uuid` co gia tri khi RENDER phai ma hoa
    #:    lai. Khong giai doan nao khac cua app nay cham bo ma hoa.
    #:
    #: ⛔ Khai o day KHONG lam app can nang luc "gpu": `jobs.py:201` loc worker
    #:    theo `requires`, va `registry.needs_gpu()` — thu doc ca `gpu_vram_mb` —
    #:    khong co nguoi goi nao. Da doi chieu truoc khi khai, vi neu no CO duoc
    #:    dung de loc thi ban khai nay se lam moi job cua `asv_media` vo hinh
    #:    voi moi worker tren doi hinh chia lan, dung cai bay docstring dau tep
    #:    mo ta.
    #: ⭐ `image_finish` (GIAI DOAN 2, b4 25/09) xin CUNG con so: no cung ma hoa
    #:    lai ca luong hinh bang cung bo ma hoa. ⛔ Khong the `-c copy` — GOP do
    #:    duoc la 8,333 giay nen mot cho cat lech toi 8 giay.
    gpu_vram_mb={"asv_media.render": 500, "asv_media.image_finish": 500},

    #: Tran thoi gian theo tung giai doan. Nhat job mo coi chi bat worker
    #: **chet**; mot job **treo** ma van dap nhip se giu suat vo han.
    max_runtime_s={
        "asv_media.media_prepare": 900,
        "asv_media.content_process": 1800,
        "asv_media.voice_synthesis": 3600,
        "asv_media.timing_align": 1800,
        "asv_media.compose": 300,
        "asv_media.render": 3600,
        "asv_media.image_finish": 3600,
        "asv_media.qc": 600,
    },
    notes="Pha 05: handler GIA. Khong goi engine that.",
)
