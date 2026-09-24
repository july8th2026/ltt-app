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
#: 🔑 **Chen o pha 12, TRUOC `content_process` — va do la ca diem.**
#:
#: 🔴 `V4-R07` (P0): trong V2, `content_process` (dich ca ban chep loi bang model
#:    TRA TIEN) chay o vi tri thu **4**, khi chua co ban bien tap nao. Tuc ta
#:    dich — va tra tien cho — nhung cau thoai thuoc nhung canh se bi **cat bo**.
#:
#: ⇒ Ban bien tap la quyet dinh hinh anh CO THAM QUYEN. Moi thu tra tien phia
#:   sau chi duoc chay tren phan da duoc GIU.
EDIT_PLAN = "edit_plan"
CONTENT_PROCESS = "content_process"
VOICE_SYNTHESIS = "voice_synthesis"
TIMING_ALIGN = "timing_align"
COMPOSE = "compose"
RENDER = "render"
QC = "qc"
#: 🔑 Do ban long tieng bang MODEL tren card (ASR+WER/CER, SQUIM, MetricX) —
#:    lan `gpu`, giua QC tat dinh va QC bang LLM/VLM. Xem
#:    `giai_doan_qc_do_luong.py`. Khong nem khi doan khong dat: vong sua doc.
QC_DO_LUONG = "qc_do_luong"
#: 🔑 **Sau `qc`, khong thay `qc`.** QC ky thuat la mot cong PHAT HANH tat
#:    dinh — do duoc, chay lai cho cung ket qua. QC bang AI thi hoi mot ben
#:    **chu quan** va **tra tien**. Gop hai thu do vao mot giai doan la lam
#:    mot lan chay hong vi mot phan quyet chu quan truoc khi ai kip xem phep
#:    do tat dinh noi gi.
#:
#: ⛔ Va no MAC DINH TAT (`LTT_ASV_QC_AI`). Khi tat, giai doan van chay va van
#:    `succeeded` — bo qua han mot giai doan se lam `len(da_xong)` khong bao
#:    gio bang `len(CHUOI)` va lan chay khong ve `done`.
QC_AI = "qc_ai"


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
    # ⚠️ TRANSCRIBE dung chung MOT ten tai nguyen voi AUDIO_PREPARE. Ly do CU la
    #    "khai hai ten khac nhau se cho phep chung chay dong thoi — dung dieu vua
    #    lam treo may".
    #
    # 🔴 **Ly do do da het dung, va pha 13 do ra dieu do.** No dua tren tien de
    #    "demucs an het loi con lai cua may" — dung o thoi diem viet, khi
    #    `demucs_runner` chua dat gioi han luong nao. Nay no co
    #    `LUONG_TORCH = 4`, va do that 03/09 tren chinh may nay:
    #
    #        1 lan tach nguon dong thoi: CPU toan may dinh 40%, RAM trong >= 16,4 GiB
    #        2 lan tach nguon dong thoi: CPU toan may dinh 57%, RAM trong >= 14,4 GiB
    #                                    (thong luong 1,33 lan so voi chay lan luot)
    #
    #    Tuc may **thua suc** hai viec nang cung luc. Giu chung mot suat KHONG con
    #    duoc bien minh bang "may khong chiu noi".
    #
    # ⛔ Nhung van giu — vi mot ly do KHAC, va noi thang ra thay vi de nguyen ly do
    #    cu cho co ve van dung: phep do tren la demucs + **demucs**. Chua ai do
    #    demucs + **whisper** chay cung luc, va whisper co ho so khac han (khai
    #    6.000 MB VRAM, va whisperx con nang CPU o phan gong hang/phan vai).
    #
    # 🔑 Dung MOT phep do de tach suat: chay `asv_gpu.audio_prepare` va
    #    `asv_gpu.transcribe` dong thoi tren mot may dang phuc vu khach, do CPU
    #    toan may + RAM trong + VRAM moi card. Neu dinh CPU < 70% va RAM trong
    #    > 8 GiB thi tach ten tai nguyen ra, va thong luong tang ~1,3 lan.
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
    # ── Ban bien tap: quyet dinh HINH ANH, chot truoc khi tieu tien tieng ──
    #
    # ⭐ `llm_remote` cung ten voi `content_process`: doc canh bang VLM va dich
    #    bang LLM deu la model nha, va chung phai tranh **dung mot suat** thay vi
    #    dam nhau tren cung mot may.
    #
    # ⚠️ `sau=(TRANSCRIBE,)` chu khong `sau=(AUDIO_PREPARE,)`: chinh sach cat can
    #    biet canh nao CO LOI THOAI (nguong bo cao hon han), va dieu do doi ban
    #    chep loi da co.
    GiaiDoan(EDIT_PLAN, "auto_scan_video", "auto_scan_video.edit_plan",
             sau=(TRANSCRIBE,), tai_nguyen="llm_remote", tai_nguyen_suat=1),
    GiaiDoan(CONTENT_PROCESS, "auto_scan_video",
             "auto_scan_video.content_process", sau=(EDIT_PLAN,),
             tai_nguyen="llm_remote", tai_nguyen_suat=1),
    # 🔑 Lan `voice`, khong phai ffmpeg: may sinh tieng la mot DICH VU rieng
    #    (`LTTStudioVoice`, loopback :8120), nen "co ffmpeg" khong keo theo "co
    #    may sinh tieng". Xem `apps/asv_voice/manifest.py`.
    # 🔴 **Giai doan nay CO goi may B, va co y KHONG khai `llm_remote`.**
    #
    #    Tao tieng thi 100% o may A (`LTTStudioVoice`, loopback :8120). Nhung
    #    bac thang nan (pha 15) goi model de VIET LAI CAU NGAN HON khi tieng doc
    #    ra dai qua khe — `ai.RUT_NGAN_CHO_VUA`, mot thao tac van ban thuan
    #    (`can_thi_giac=False` -> `qwen38-api`, khong phai ban thi giac).
    #
    # ⚠️ Khai `llm_remote` o day se giu mot suat cua may B (ngay viet: suat
    #    DUY NHAT; nay so suat theo model o `ltt_llm.ngan_sach.HO_SO`) suot ca giai doan DAI NHAT
    #    cua chuoi — chan `edit_plan`/`content_process`/`qc_ai` cua moi lan chay
    #    khac, de tra gia cho mot loi goi THINH THOANG moi xay ra.
    #
    # ⭐ Nen cach xu ly la o TAY BAT chu khong o BAN KHAI: may ban thi bo nac
    #    rut ngan va xuong nac co gian, va `nan_cho_vua.ket_luan` ghi lai thanh
    #    `CO_GIAN` hoac `CAN_SUA` — suy giam CO GHI SO, va `CAN_SUA` chay thang
    #    vao vong sua. Xem `giai_doan_giong._viet_lai`.
    GiaiDoan(VOICE_SYNTHESIS, "asv_voice", "asv_voice.voice_synthesis",
             sau=(CONTENT_PROCESS,)),
    GiaiDoan(TIMING_ALIGN, "asv_media", "asv_media.timing_align",
             sau=(VOICE_SYNTHESIS, AUDIO_PREPARE)),
    GiaiDoan(COMPOSE, "asv_media", "asv_media.compose", sau=(TIMING_ALIGN,)),
    GiaiDoan(RENDER, "asv_media", "asv_media.render", sau=(COMPOSE,)),
    GiaiDoan(QC, "asv_media", "asv_media.qc", sau=(RENDER,)),
    # 🔑 `asv_gpu`: nap model len card (whisper, SQUIM, MetricX), tung bo do mot
    #    tien trinh con, lan luot — dinh VRAM = bo do nang nhat, va card duoc tra
    #    khi tien trinh thoat. Dung CUNG suat `tach_nguon_cuc_bo` voi hai giai
    #    doan GPU kia: ba viec nap model len mot card dung chung khong chay chong.
    GiaiDoan(QC_DO_LUONG, "asv_gpu", "asv_gpu.qc_do_luong", sau=(QC,),
             tai_nguyen="tach_nguon_cuc_bo", tai_nguyen_suat=1),
    # 🔑 `auto_scan_video` chu khong `asv_media`: duong nay goi model, tuc
    #    cung nang luc voi `edit_plan`/`content_process`. Nhet mot loi goi
    #    model vao giai doan cua app khac la pha phep dinh tuyen `test_402`
    #    chot — va phep dinh tuyen do la thu quyet dinh worker nao nhat viec.
    GiaiDoan(QC_AI, "auto_scan_video", "auto_scan_video.qc_ai", sau=(QC_DO_LUONG,),
             tai_nguyen="llm_remote", tai_nguyen_suat=1),
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
