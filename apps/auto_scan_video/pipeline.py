"""Chuoi giai doan CO DINH cua Auto Scan Video, va bang phan cong thi hanh.

## Vi sao chuoi nay nam trong MA NGUON chu khong nam trong CSDL

Khach **khong** dung duoc do thi. Khong keo tha, khong them bot, khong doi thu
tu (`MVP_CONTRACT.md` muc 5, bat bien I17, O18). Neu thu tu nam trong CSDL thi
no la du lieu, ma du lieu thi sua duoc — va cai cho sua duoc do chinh la Canvas
di vao bang cua sau. Nam trong ma nguon thi doi thu tu la mot lan commit co
review, khong phai mot lan UPDATE.

## Bang phan cong: vi sao ba app chu khong phai mot

`platform_core/jobs.py:158-164` loc quyen nhat job theo **APP**, khong theo
`job_type`:

    eligible = [app for app in discover()
                if set(app.manifest.requires).issubset(capabilities)]

Nen mot app khai `requires=("api","ffmpeg","gpu")` chi duoc nhat boi mot lan co
**du ca ba**. Tren doi hinh chia lan (`LTT_WORKER_POOLS`), job cua no vo hinh
voi moi worker va nam `queued` **mai mai, khong loi nao bao** — dung kieu hong
ma `apps/ltt_voice/manifest.py:112` da ghi lai.

`tests/test_400_asv_bat_bien_thi_hanh.py::test_app_gop_ca_hai_nang_luc_bi_ca_HAI_lan_le_tu_choi`
tai hien dung canh do.

⇒ Ba app: mot cho khach nhin thay, hai executor an. Xem ADR-001 D5.
"""
from __future__ import annotations

from dataclasses import dataclass

# ── Ten giai doan ────────────────────────────────────────────────────────────
MEDIA_PREPARE = "media_prepare"
AUDIO_PREPARE = "audio_prepare"
TRANSCRIBE = "transcribe"
CONTENT_PROCESS = "content_process"
VOICE_SYNTHESIS = "voice_synthesis"
TIMING_ALIGN = "timing_align"
COMPOSE = "compose"
RENDER = "render"
QC = "qc"


@dataclass(frozen=True)
class GiaiDoan:
    """Bang khai cua mot giai doan. Bat bien o cap doi tuong."""

    ten: str
    #: App SO HUU job con cua giai doan nay. Quyet dinh worker nao nhat duoc no.
    app_slug: str
    #: `job_type` nop vao hang doi nen tang.
    job_type: str
    #: Giai doan phai `succeeded` truoc khi giai doan nay duoc nop.
    sau: tuple[str, ...] = ()
    #: Tai nguyen dung chung ma giai doan phai gianh truoc khi chay. Rong = khong
    #: gianh gi. Duoc chup luc nop job (`jobs._nop_giai_doan_san_sang`).
    #:
    #: ⭐ `llm_remote` la ten `apps/ltt_llm` dung cho model nha: job, sync va
    #:    stream cua no deu tranh **dung mot suat**. Khai cung ten de nen tang
    #:    xep hang chung, thay vi de hai app dam nhau tren cung mot may.
    tai_nguyen: str = ""
    tai_nguyen_suat: int = 0

    @property
    def la_giai_doan_dau(self) -> bool:
        return not self.sau


#: 🔑 CHUOI CO DINH. Thu tu o day la thu tu duy nhat ton tai.
#:
#: ⚠️ `app_slug` cua giai doan **khong** phai chi tiet trien khai — no la phep
#:    dinh tuyen. Doi mot dong o cot do la doi lan worker nao chay viec do, va
#:    `tests/test_402` chot rang moi giai doan roi vao app co dung nang luc.
CHUOI: tuple[GiaiDoan, ...] = (
    GiaiDoan(MEDIA_PREPARE, "asv_media", "asv_media.media_prepare"),
    # 🔴 `tai_nguyen` o day KHONG phai mot chi tiet toi uu — no la mot chot tai.
    #
    #    Ngay 02/09 chu du an phai **reset cung may hai lan** vi qua tai CPU, va
    #    mot phan nguyen nhan la demucs. Phien `lttstudiosapp-a1` truy ra: gate
    #    chay `pytest -n auto` (20 worker tren may nay), va `test_406` goi demucs
    #    THAT ben trong mot worker — nen tai khong CONG ma NHAN.
    #
    #    O production con ro hon: nen tang mo so worker bang so GPU, nen nhieu
    #    lan `audio_prepare` chay song song la hanh vi binh thuong. Demucs an het
    #    loi con lai cua may, va may nay LA production (`LTTStudioWeb`,
    #    `Worker`, `Voice`, `Codex` deu dang phuc vu khach tren cung 20 loi).
    #
    # ⇒ Khai tai nguyen de NEN TANG dieu tiet. Khong tu dem loi trong app: chi
    #   nen tang moi biet co bao nhieu job dang chay, va them mot bo dem thu hai
    #   la tao chu so huu thu hai cho cung mot tai nguyen.
    GiaiDoan(AUDIO_PREPARE, "asv_gpu", "asv_gpu.audio_prepare",
             sau=(MEDIA_PREPARE,),
             tai_nguyen="tach_nguon_cuc_bo", tai_nguyen_suat=1),
    # ⚠️ TRANSCRIBE dung chung MOT ten tai nguyen voi AUDIO_PREPARE, co y: ca hai
    #    deu la model nang chay cuc bo tren cung may. Khai hai ten khac nhau se
    #    cho phep chung chay dong thoi — dung dieu vua lam treo may.
    GiaiDoan(TRANSCRIBE, "asv_gpu", "asv_gpu.transcribe", sau=(AUDIO_PREPARE,),
             tai_nguyen="tach_nguon_cuc_bo", tai_nguyen_suat=1),
    # 🔑 CONTENT chay o lan `api`, nen no thuoc app KHACH — app duy nhat khai
    #    `requires=("api",)`. Khong phai `asv_media` (ffmpeg): mot lan goi model
    #    khong can ffmpeg, va xep no vao lan ffmpeg la giu mot suat co ffmpeg de
    #    ngoi cho mang.
    #
    # ⚠️ ADR-001 D5 du dinh **uy quyen** mot job `ltt_llm.chat`. Sau khi trace
    #    hop dong that o pha 11, uy quyen khong lam duoc viec: giai doan nay
    #    phai chia lo, goi N lan, gop va phat hien phan hoi thieu — con
    #    `ltt_llm.chat` la MOT luot goi, va `asv_stage` chi giu mot `job_id` cho
    #    moi giai doan. Phan quan trong cua D5 van giu: khong dung duong HTTP
    #    thu hai, khong tu chon khoa, an toan dispatch van la cua nen tang.
    #    Xem bao cao pha 11, muc "Sua doi ADR-001 D5".
    GiaiDoan(CONTENT_PROCESS, "auto_scan_video",
             "auto_scan_video.content_process", sau=(TRANSCRIBE,),
             tai_nguyen="llm_remote", tai_nguyen_suat=1),
    # 🔑 Lan `voice`, khong phai ffmpeg: may sinh tieng la mot DICH VU rieng
    #    (`LTTStudioVoice`, loopback :8120), nen "co ffmpeg" khong keo theo "co
    #    may sinh tieng". Xem `apps/asv_voice/manifest.py`.
    GiaiDoan(VOICE_SYNTHESIS, "asv_voice", "asv_voice.voice_synthesis",
             sau=(CONTENT_PROCESS,)),
    GiaiDoan(TIMING_ALIGN, "asv_media", "asv_media.timing_align",
             sau=(VOICE_SYNTHESIS, AUDIO_PREPARE)),
    GiaiDoan(COMPOSE, "asv_media", "asv_media.compose", sau=(TIMING_ALIGN,)),
    GiaiDoan(RENDER, "asv_media", "asv_media.render", sau=(COMPOSE,)),
    GiaiDoan(QC, "asv_media", "asv_media.qc", sau=(RENDER,)),
)

TEN_GIAI_DOAN: tuple[str, ...] = tuple(g.ten for g in CHUOI)
THEO_TEN: dict[str, GiaiDoan] = {g.ten: g for g in CHUOI}
THEO_JOB_TYPE: dict[str, GiaiDoan] = {g.job_type: g for g in CHUOI}


def ke_tiep(da_xong: set[str]) -> list[GiaiDoan]:
    """Cac giai doan da du phu thuoc va san sang nop.

    Tra ve DANH SACH chu khong phai mot phan tu: `timing_align` cho ca
    `voice_synthesis` lan `audio_prepare`, nen chuoi nay khong phai mot duong
    thang — hai nhanh chay song song duoc va viec do la co that, khong phai
    tinh nang thua.
    """
    return [g for g in CHUOI
            if g.ten not in da_xong and set(g.sau).issubset(da_xong)]


def ha_nguon_cua(ten: str) -> list[str]:
    """Moi giai doan phu thuoc `ten`, TRUC TIEP hay GIAN TIEP, theo thu tu chuoi.

    Day la quan he **nguoc** cua `GiaiDoan.sau`, va no la thu Prompt 16 muc 4
    doi: khi mot giai doan chay lai, chi nhung giai doan that su an theo no moi
    duoc vo hieu.

    ⚠️ **Hom nay ket qua nay TRUNG voi "moi giai doan dung sau trong `CHUOI`"**,
       va noi khac di la noi sai. Do that:

           media_prepare   -> 8 giai doan con lai
           audio_prepare   -> 7 giai doan con lai
           ...
           render          -> ['qc']

       Do thi hien tai gan nhu mot duong thang. Cho re duy nhat la
       `timing_align`, phu thuoc CA `voice_synthesis` lan `audio_prepare` — nhung
       cho re do khong tao ra giai doan nao "dung sau ma khong an theo".

    ⇒ Vay tai sao khong viet `CHUOI[i+1:]` cho gon? Vi hai thu do **bang nhau do
      hoan canh, khong do dinh nghia**. Them mot nhanh doc lap (vd mot giai doan
      chi an theo `media_prepare`) la chung tach ra ngay, va phien ban `[i+1:]`
      se lang le vo hieu — tuc bat khach tra tien lai cho mot viec khong dau vao
      nao doi. `tests/test_417` chot ca hai chieu, ke ca su trung nhau hom nay,
      nen luc chung tach ra thi co mot phep kiem noi ra thay vi im lang.

    ⛔ Chieu nguoc lai dat hon: vo hieu **thieu** mot giai doan ha nguon nghia la
       giao mot ban long tieng tron lan ket qua cua hai lan chay khac nhau —
       hong theo kieu khong loi nao bao.
    """
    ra: list[str] = []
    bien: set[str] = {ten}
    for g in CHUOI:                     # `CHUOI` da theo thu tu topo (co chot)
        if g.ten == ten:
            continue
        if set(g.sau) & bien:
            bien.add(g.ten)
            ra.append(g.ten)
    return ra


def _kiem_tra_chuoi() -> None:
    """Chot luc import: khong co phu thuoc nao tro toi mot giai doan chua ton tai.

    Chay o cap module co chu y. Mot chuoi hong la loi cau hinh, va no phai no
    luc **nap app** — chu khong phai luc mot khach hang dang cho job chay.
    """
    da_thay: set[str] = set()
    for g in CHUOI:
        thieu = set(g.sau) - da_thay
        if thieu:
            raise ValueError(
                f"giai doan {g.ten!r} phu thuoc {sorted(thieu)} — chua duoc "
                f"khai truoc do trong CHUOI")
        da_thay.add(g.ten)
    if len(da_thay) != len(CHUOI):
        raise ValueError("CHUOI co ten giai doan trung nhau")


_kiem_tra_chuoi()
