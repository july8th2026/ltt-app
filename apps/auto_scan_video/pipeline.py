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

# ⭐ So ma loi chung (I3). Huong phu thuoc: `ma_loi` -> `rang_giong`, va ⛔ KHONG
#    bao gio -> `quan_sat` (chinh `quan_sat` import tep nay).
from . import ma_loi, rang_giong

# ── Ten giai doan ────────────────────────────────────────────────────────────
MEDIA_PREPARE = "media_prepare"
AUDIO_PREPARE = "audio_prepare"
TRANSCRIBE = "transcribe"
CONTENT_PROCESS = "content_process"
VOICE_SYNTHESIS = "voice_synthesis"
TIMING_ALIGN = "timing_align"
COMPOSE = "compose"
RENDER = "render"
#: 🔑 **GIAI DOAN 2 tu 26/09/2026 — XUONG SAU `render` (B1 §9a).**
#:
#: 🔴 Truoc do no dung TRUOC `content_process`, va ly do cu la `V4-R07`: *"dung
#:    dich nhung cau thuoc canh se bi cat"*. Ly do do **da het dung** khi chu du
#:    an chot kien truc hai giai doan: GD1 giu nguyen hinh va xuat MP4 **full do
#:    dai**, nen ⛔ khong con canh nao bi cat trong GD1 de tiet kiem.
#:
#: 🔑 **Va viec chay SAU `render` xoa mot LOP LOI, ⛔ khong chi doi cho.** O vi
#:    tri cu, giai doan nay phan quyet tren truc thoi gian **NGUON**, con
#:    `ke_cat`/`image_finish` cat tren truc **BAN RA** — chinh
#:    `thoi_gian.ngan_sach_doan` da canh bao lop loi do: *"ham nay lang le TRON
#:    HAI DONG HO"*. Chay sau `render` thi chi con MOT dong ho.
#:
#: ⚠️ **Cai gia, noi thang:** cat sau khi da long tieng nghia la ta tra tien
#:    tieng cho phan se bi bo. Tran cat la **5 %** (`ke_cat.TRAN_CAT_TI_LE`) nen
#:    phan mat <= 5 % chi phi tieng. Do la cai gia DUNG cua kien truc hai giai
#:    doan, va no da duoc nhan (B1 §9a).
EDIT_PLAN = "edit_plan"
#: 🔑 **GIAI DOAN 2** — chu du an chot 25/09. Thao tac hinh anh tren MP4 DA XONG.
#:
#: ⭐ Chen SAU `render` va TRUOC `qc`, va ca hai ranh gioi deu co ly do:
#:    · sau `render`: giai doan 1 phai giao xong mot MP4 tieng Viet **toan bo do
#:      dai goc** truoc khi ai duoc cat mot khung nao;
#:    · truoc `qc`: cong chat luong phai do **tep khach nhan**. Dat `qc` o giua
#:      la chung nhan mot tep khong ai duoc giao — mot cong do dung thu khong
#:      phai ban giao thi ⛔ khong canh giu ban giao.
#:
#: 🔴 Va no la BAN GIAO: `thi_hanh.la_ban_giao` chuyen tu `RENDER` sang day, nen
#:    `.mp4`/`.srt` cua no ⛔ khong co han, con cua `render` thi co
#:    (`assets.HAN_TRUNG_GIAN`). Thieu buoc chuyen do thi video cua khach tu bien
#:    mat sau 30 ngay — chinh cai bay `thi_hanh` ghi lai o pha 27.
IMAGE_FINISH = "image_finish"
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
    #: Dieu kien phai dung de buoc nay CO NGHIA. ⛔ Khong duoc rong (I2).
    #:
    #: 🔴 `("",)` = khai tuong minh "khong co tien de". `()` = CHUA AI NGHI TOI,
    #:    va `thieu_khai()` do. Khac biet nay la ca muc dich cua truong: luot A
    #:    24/09 chet o `content_process` vi che do tu khop giong doi **nguon co
    #:    tieng noi** ma khong ai viet ra — nen no hien ra nhu mot khiem khuyet
    #:    trong khi no la mot dieu kien.
    #:
    #: ⛔ Khai theo thu CO THAT trong mo-dun cua buoc. Mot `tien_quyet` bia con
    #:    te hon mot o rong: no **trong nhu** da duoc kiem.
    tien_quyet: tuple[str, ...] = ()
    #: Ma loi ON DINH buoc nay duoc phep nem — khoa cua `ma_loi.SO_MA` (I3).
    #: ⛔ Khong nem chuoi tu do: G-04, cau giai thich dung o cot `error` va khach
    #: nhan mot cau chung chung kem mot nut "Thu lai buoc nay" chac chan hong.
    #:
    #: ⚠️ `("",)` = buoc nay **chua** co ma on dinh nao; that bai cua no roi vao
    #:    `error` duoi dang chu tu do. Hom nay do la 10/12 buoc — xem
    #:    `tests/test_3200::test_CHI_HAI_mat_xich_co_ma_on_dinh__ghi_lai_HIEN_TRANG`.
    ma_loi: tuple[str, ...] = ()
    #: Ten phep do quyet dinh DAT, theo bang cong cua
    #: `docs/superpowers/plans/2026-09-24-thang-cong-asv.md`. ⛔ Rong = buoc
    #: khong the "dat" ⇒ khong duoc vao thang cong (I4).
    do: tuple[str, ...] = ()

    @property
    def la_giai_doan_dau(self) -> bool:
        return not self.sau


#: Khai tuong minh "khong co" — phan biet voi `()` la "chua ai nghi toi".
RONG_TUONG_MINH: tuple[str, ...] = ("",)


def thieu_khai(chuoi: tuple[GiaiDoan, ...] | None = None) -> list[str]:
    """Giai doan nao thieu truong bat buoc (I2/I3/I4). Rong = du.

    🔑 Nhan chuoi lam **du lieu** chu khong doc thang `CHUOI`, va do la ca diem:
       `_kiem_tra_chuoi()` chay o cap module, nen mot phep tiem vao tep nay chet
       o luc **nap module** va khong bao gio toi duoc phan phan xu. Mot doi chung
       that bai vi ly do KHAC thi khong phai mot doi chung (N-08b).
    """
    ra: list[str] = []
    for g in (CHUOI if chuoi is None else chuoi):
        for ten_truong in ("tien_quyet", "ma_loi", "do"):
            if not getattr(g, ten_truong):
                ra.append(f"{g.ten}: thieu {ten_truong}")
    return ra


#: 🔑 CHUOI CO DINH. Thu tu o day la thu tu duy nhat ton tai.
#:
#: ⚠️ `app_slug` cua giai doan **khong** phai chi tiet trien khai — no la phep
#:    dinh tuyen. Doi mot dong o cot do la doi lan worker nao chay viec do, va
#:    `tests/test_402` chot rang moi giai doan roi vao app co dung nang luc.
CHUOI: tuple[GiaiDoan, ...] = (
    GiaiDoan(MEDIA_PREPARE, "asv_media", "asv_media.media_prepare",
             tien_quyet=(
                 "run.source_key tro toi mot tep con doc duoc trong kho "
                 "(giai_doan_media.py:66)",
                 "tep nguon qua nhap_media.kiem_chinh_sach — chay TRUOC khi ton "
                 "mot giay ffmpeg nao (giai_doan_media.py:83)",
                 "ffmpeg va ffprobe co tren may worker; phien ban cua chung vao "
                 "van tay (giai_doan_media.py:86)"),
             ma_loi=RONG_TUONG_MINH,
             do=("tep_ra_giai_ma_duoc", "thoi_luong_khop_nguon")),
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
             tai_nguyen="tach_nguon_cuc_bo", tai_nguyen_suat=1,
             tien_quyet=(
                 "run.source_key con doc duoc — buoc nay rut mot ban 44,1 kHz "
                 "stereo tu TEP GOC, khong dung ban 16 kHz cua media_prepare "
                 "(giai_doan_am_thanh.py:35)",
                 # 🔴 TIEN DE IM LANG, va la mat con lai cua cai da lam chet luot A.
                 "nguon CO TIENG NOI thi `f0_trung_vi` moi khac 0; `0.0` nghia la "
                 "KHONG DO DUOC, **khong** phai 'khong co giong' — va "
                 "content_process chet o dung con so nay "
                 "(giai_doan_am_thanh.py:129)",
                 "card do NEN TANG cap qua ctx.gpu_uuid; khong co thi demucs TU "
                 "CHOI chu khong tut xuong CPU im lang (giai_doan_am_thanh.py:51)",
                 "han demucs <= ngan sach con lai cua job (lat_cat); nguoc lai job "
                 "bi giet truoc va demucs mo coi giu GPU "
                 "(giai_doan_am_thanh.py:74)"),
             ma_loi=RONG_TUONG_MINH,
             do=("f0_trung_vi_khac_0_tren_phim_co_tieng",
                 "demucs_chay_tren_card")),
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
             tai_nguyen="tach_nguon_cuc_bo", tai_nguyen_suat=1,
             tien_quyet=(
                 "media_prepare cua CUNG lan chay da dang mot .wav 16 kHz "
                 "(giai_doan_chep_loi.py:61,74)",
                 # 🔴 TIEN DE IM LANG — va no la N-08 tren duong CHAY LAI.
                 "`_khoa_tieng_asr` lay .wav DAU TIEN trong outputs cua "
                 "media_prepare: chay lai media_prepare ma khong vo hieu buoc nay "
                 "thi no doc ban tieng cua luot TRUOC (features.py:263)",
                 # 🔴 TIEN DE IM LANG — Q7: san pham la voice->voice.
                 #    ⭐ 26/09 (Task 21): `embedded`/`ocr`/`auto` DA BO. Tien de cu
                 #    ("mac dinh `auto` nen duong asr KHONG chay") da HET, va thay
                 #    vao do la mot tien de MOI, nang hon: nay ⛔ khong con duong
                 #    nao doc chu tren hinh, nen mot phim ⛔ KHONG CO TIENG NOI cho
                 #    ra ban ghi RONG chu khong lui sang hardsub.
                 "duong `asr` doi nguon CO TIENG NOI; phim khong co tieng noi ⇒ "
                 "ban ghi rong, ⛔ KHONG con duong hardsub de lui sang "
                 "(nguon_loi.py: MOT duong duy nhat, 26/09)",
                 "cap ngon ngu hop le: nguon thuoc (zh,en,vi) hoac `auto`, dich "
                 "thuoc (vi,en) — chot NGAY SAU asr, truoc moi buoc tra tien "
                 "(ngon_ngu.py:37,38 · giai_doan_chep_loi.py:155)"),
             ma_loi=RONG_TUONG_MINH,
             do=("wer_vs_hardsub", "cer_vs_hardsub")),
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
             tai_nguyen="llm_remote", tai_nguyen_suat=1,
             tien_quyet=(
                 "ban ghi chinh tac cua transcribe da co va qua ban_ghi.kiem "
                 "(giai_doan_noi_dung.py:66,74)",
                 # ⭐ 26/09: `edit_plan` xuong GD2 nen tien de CU ("ban bien tap
                 #    phai co") da bien thanh nguoc lai — "khong co ban bien tap"
                 #    la trang thai DUNG, va `_doc_ban_bien_tap` tra `(None,
                 #    None)` = GIU TAT CA (B1 §4a buoc 1).
                 "⛔ KHONG doi ban bien tap: buoc nay chay TRUOC `edit_plan`, nen "
                 "`_doc_ban_bien_tap` tra `(None, None)` = giu tat ca va ⛔ khong "
                 "loc ban chep loi (giai_doan_noi_dung._doc_ban_bien_tap)",
                 "ban chep loi con it nhat MOT doan thoai "
                 "(giai_doan_noi_dung.py, sau khi giu tat ca)",
                 # 🔴🔴 DAY LA TIEN DE DA LAM CHET LUOT A 24/09 — truoc do
                 #      khong ai viet no ra o bat cu dau.
                 "che do tu khop giong (AUTO_MATCH) doi nguon CO TIENG NOI: "
                 "audio_prepare phai do duoc `f0_trung_vi` khac 0 de "
                 "cao_do.gioi_tu_f0 suy ra `gioi`; F0 = 0 hay ngoai dai "
                 "[F0_THAP,F0_CAO] ⇒ `gioi` rong ⇒ dac_diem.co_du_de_khop sai ⇒ "
                 "auto_match_thieu_can_cu (giai_doan_noi_dung.py:128 · "
                 "ho_so_noi_dung.py:180 · cao_do.py:96 · cao_do.py:96)",
                 "ngon ngu dich thuoc (vi,en) — da chot o transcribe, doc lai o "
                 "day qua cai_dat (ngon_ngu.py:38)",
                 "diem chot mang van tay: doi giong thi cac doan cu KHONG con "
                 "duoc tinh la da lam; van tay ban bien tap la hang TUONG MINH "
                 "`VAN_TAY_KHONG_CO_BAN` (giai_doan_noi_dung.py)"),
             ma_loi=(rang_giong.MA_KHONG_KHOP,
                     rang_giong.MA_KHO_CHUNG_THIEU_GIOI,
                     rang_giong.MA_THIEU_CAN_CU),
             do=("metricx_qe", "ti_le_bao_dong_gia_bo_cham")),
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
             sau=(CONTENT_PROCESS,),
             tien_quyet=(
                 "may tao tieng (LTTStudioVoice, loopback :8120) san sang — "
                 "giong_noi.san_sang() (giai_doan_giong.py:71)",
                 "ban long tieng cua content_process da co va qua van_ban.kiem "
                 "(giai_doan_giong.py:62,65)",
                 "ban long tieng DA GHI `ma_giong`; ⛔ khong rot ve "
                 "settings.giong_id (giai_doan_giong.py:104)",
                 "ngon ngu dich phai KHOP lan cua giong, neu khong "
                 "voice_language_mismatch (giai_doan_giong.py:127)",
                 # 🔴 TIEN DE IM LANG: hong bang KeyError, khong phai loi co cau.
                 "moi muc phai co `ma` va `chu`: thieu thi KeyError chu khong phai "
                 "mot loi co cau khach doc duoc (giai_doan_giong.py:184,196)",
                 "moi muc phai co khe thoi gian (nan_cho_vua.khe_cua) de bac thang "
                 "nan chay duoc (giai_doan_giong.py:178)",
                 "doan bi vong sua phai DOI van tay, neu khong 'doc lai' tra ve "
                 "dung tep da bi tu choi (giai_doan_giong.py:418)"),
             ma_loi=(ma_loi.MA_LOI_LECH_LAN, ma_loi.MA_LOI_LAN_KHONG_RO),
             do=("wer_luot_cuoi", "pesq")),
    GiaiDoan(TIMING_ALIGN, "asv_media", "asv_media.timing_align",
             sau=(VOICE_SYNTHESIS, AUDIO_PREPARE),
             tien_quyet=(
                 "co ban dich cua content_process va ban ke tieng cua "
                 "voice_synthesis (giai_doan_thoi_gian.py:56,62)",
                 "biet thoi luong video nguon (> 0) tu ho so soi cua media_prepare "
                 "(giai_doan_thoi_gian.py:93)",
                 # ⭐ 26/09: `ban_do`/`so_cho_noi` DA ROI KHOI buoc nay (b4 hai
                 #    giai doan) — GD1 ⛔ khong cat gi, luong hinh di nguyen ven,
                 #    nen ban do thoi gian luon DONG NHAT. Tien de cu ("preset
                 #    CAT doi ban bien tap") da sai tu luc do, va tu 26/09
                 #    `edit_plan` con dung SAU buoc nay.
                 "ban do thoi gian luon DONG NHAT o GD1: ⛔ khong doc ban bien "
                 "tap nao (giai_doan_thoi_gian.py, `tom_tat`)",
                 "co ban nen .wav cua audio_prepare de tron ban phoi "
                 "(giai_doan_thoi_gian.py:180)",
                 "moi doan trong ke hoach phai co tep tieng tuong ung trong ban ke "
                 "(giai_doan_thoi_gian.py:215)"),
             ma_loi=RONG_TUONG_MINH,
             do=("ti_le_cau_vua_khe", "troi_don_cuoi")),
    GiaiDoan(COMPOSE, "asv_media", "asv_media.compose", sau=(TIMING_ALIGN,),
             tien_quyet=(
                 "co ke hoach thoi gian, ban ke tieng, nhac nen .wav va "
                 "run.source_key (giai_doan_ban_dung.py:172,175,178,180)",
                 "co ban phoi master.wav do timing_align dung "
                 "(giai_doan_ban_dung.py:60)",
                 # 🔴 TIEN DE IM LANG: tra (0,0) roi tinh logo/crop tren khung 0.
                 "ho so soi cua media_prepare phai co rong/cao/xoay: thieu hay doc "
                 "khong duoc thi `_co_khung` tra `(0, 0)` LANG LE, va logo/vung che "
                 "duoc tinh tren mot khung 0x0 (giai_doan_ban_dung.py:76)",
                 "preset anh xa duoc ve che do render (che_do_render.che_do_cho) "
                 "(giai_doan_ban_dung.py:202)",
                 "khach xin phu de thi phai co ban dich "
                 "(giai_doan_ban_dung.py:157)"),
             ma_loi=RONG_TUONG_MINH,
             do=("lufs_tich_hop", "dinh_that_dbtp")),
    GiaiDoan(RENDER, "asv_media", "asv_media.render", sau=(COMPOSE,),
             tien_quyet=(
                 "co ban dung .json cua compose va no qua ban_dung.kiem "
                 "(giai_doan_ket_xuat.py:86,111)",
                 "moi khoa trong ban dung tro toi artifact CON SONG cua chu so huu "
                 "(giai_doan_ket_xuat.py:119)",
                 "ban dung khai ban phoi master (`tieng.master.khoa`) "
                 "(giai_doan_ket_xuat.py:145)",
                 # 🔴 TIEN DE IM LANG: khong loi nao bao.
                 "khung ra phai dung: sai khung thi phu de .ass bi dat sai cho ma "
                 "KHONG loi nao bao (giai_doan_ket_xuat.py:187)",
                 "nvenc chi duoc KHAI chu khong duoc kiem — thieu card thi ha ve "
                 "CPU, nen nhanh nvenc CHUA duoc do bao gio "
                 "(giai_doan_ket_xuat.py:191)"),
             ma_loi=RONG_TUONG_MINH,
             do=("vmaf",)),
    # ── GIAI DOAN 2 · Ban bien tap: phan quyet "canh nao kem" tren BAN RA ──────
    #
    # 🔑 **Xuong GD2 (26/09/2026, B1 §9a).** Ly do o cho khai ten `EDIT_PLAN` phia
    #    tren: mot dong ho thay vi hai.
    #
    # ⛔ **`tai_nguyen` RONG, va do la ca mot phep sua loi.** Truoc day no khai
    #    `llm_remote` **TINH** — nen voi preset giu hinh no ⛔ khong goi gi ma VAN
    #    giu suat LLM duy nhat cua ca may suot giai doan. Do 26/09: hai luot cung
    #    preset, `edit_plan` mat **2,8 s** va **205,7 s** — 203 giay chenh la XEP
    #    HANG, khong phai tinh toan. Tu nay no ⛔ khong goi model nao (B1 §9b:
    #    nam can cu), nen khong con gi de khai.
    GiaiDoan(EDIT_PLAN, "auto_scan_video", "auto_scan_video.edit_plan",
             sau=(RENDER,),
             tien_quyet=(
                 "preset doc duoc tu cai_dat — hai nhanh (giu hinh / cat) re o "
                 "day (giai_doan_ban_bien_tap.chay)",
                 "preset giu hinh doi thoi luong nguon duong: thieu thi "
                 "ThieuChiMuc (giai_doan_ban_bien_tap.chay)",
                 "co nguon soi duoc hoac run.source_key: media_prepare KHONG "
                 "dang luong hinh nao (giai_doan_ban_bien_tap._nguon_soi_duoc)",
                 # 🔴 TIEN DE IM LANG, va tu 26/09 no la BAT BIEN O BIEN chu
                 #    khong con la mot canh bao: `_co_thoai` tra `False` cho MOI
                 #    canh khi ban ghi rong, tuc ca video thanh "khong loi thoai"
                 #    va thanh ung vien cat khap noi.
                 "ban chep loi phai co: thieu thi `_do_cac_canh` khai THIEU BANG "
                 "CHUNG cho moi canh, ⛔ khong doc im lang thanh 'khong co thoai' "
                 "(giai_doan_ban_bien_tap._do_cac_canh)",
                 "ffmpeg chay duoc `blackdetect`+`freezedetect` trong MOT luot "
                 "giai ma; khong chay duoc thi moi canh la 'khong_do_duoc_hinh' "
                 "(qc.do_hinh · giai_doan_ban_bien_tap._do_cac_canh)",
                 "preset CAT (hop_dong_v4.PRESET_CAT_THONG_MINH) doi do phu bang "
                 "chung canh = 1,0 (PHU_BANG_CHUNG_TOI_THIEU, _chot_do_phu)",
                 "phien ban ffmpeg vao van tay ban bien tap: doi ffmpeg co the "
                 "doi ranh gioi khoang den/dung hinh, tuc doi QUYET DINH CAT "
                 "(giai_doan_ban_bien_tap.chay, ghi_chu['ffmpeg'])"),
             ma_loi=RONG_TUONG_MINH,
             do=("so_canh_vs_do_truc_tiep", "do_phu_bang_chung_canh")),
    # 🔑 **GIAI DOAN 2.** Dung `asv_media` (lan ffmpeg) va xin GPU y het `render`:
    #    no cung ma hoa lai ca luong hinh. ⛔ Khong the `-c copy` — GOP cua chuoi
    #    nay do duoc la 8,333 giay, nen mot cho cat lech toi 8 giay.
    #
    # 🔴 **`sau=(EDIT_PLAN,)` chu khong `(RENDER,)` (26/09).** `ke_tiep` tra ve
    #    DANH SACH moi giai doan du phu thuoc, nen neu buoc nay con khai `RENDER`
    #    thi no ⛔ nop duoc **cung luc** voi `edit_plan` — va mot luot
    #    `image_finish` chay truoc se doc `khoa_ep` rong, cat 0 khung, roi bao
    #    `succeeded`. Tuc phep dai giai doan xuong GD2 mat tac dung IM LANG.
    GiaiDoan(IMAGE_FINISH, "asv_media", "asv_media.image_finish",
             sau=(EDIT_PLAN,),
             tien_quyet=(
                 "co MP4 cua render, va ffprobe doc duoc thoi luong cua no — ke "
                 "cat dung tren truc cua TEP THAT, khong tren mot ban khai "
                 "thuong nguon (giai_doan_hinh_anh.py:_ke_cat)",
                 "ban bien tap cua edit_plan + chi muc canh: thieu MOT trong hai "
                 "thi ⛔ khong cat gi — mac dinh cua ca he la GIU, vi 'bo la hanh "
                 "dong phai co can cu' (ban_bien_tap._quyet_dinh_mot_canh)",
                 "ke hoach thoi gian cua timing_align: 'co thoai' doc tieng VIET "
                 "DA SINH o day, ⛔ khong doc ban chep loi NGUON "
                 "(ke_cat.khe_thoai_tu_ke_hoach)",
                 # 🔴 Bo sung 27/09. Dong tren khai DUNG *nguon nao*, nhung no im
                 #    ve *TRUC nao* — va tu khi `edit_plan` chay SAU `render`, truc
                 #    la cho lech. `khe_thoai_tu_ke_hoach` tra khe tren truc BAN RA
                 #    CUA timing_align (truoc `toc_do`), con tep ma giai doan nay
                 #    cat la MP4 cua GD1 (**sau** `toc_do`). Doi truc o
                 #    `giai_doan_hinh_anh._khe_thoai_truc_ban_giao`; thieu phep doi
                 #    ay thi voi `toc_do = 1,25` mot cau thoai o giay 90 bi doc
                 #    thanh "⛔ khong thoai" va bi cat vao giua loi.
                 "khe tieng phai DOI TRUC tu truc bien tap (truoc `toc_do`) sang "
                 "truc MP4 cua GD1 (sau `toc_do`) truoc khi dung — hai truc chi "
                 "trung nhau khi `toc_do = 1` "
                 "(giai_doan_hinh_anh._khe_thoai_truc_ban_giao)",
                 "tran 5 % la BAT BIEN O BIEN: `ke_cat.kiem` NEM khi vuot, nen "
                 "mot ke cat hong ⛔ khong bao gio ton tai (ke_cat.py)",
                 "cua so `cat_dau_cuoi` cua khach GIAO SAU ke cat, va CO Y nam "
                 "ngoai tran 5 % — no la yeu cau ro rang cua khach, ⛔ khong phai "
                 "mot phep phan doan (giai_doan_hinh_anh._cua_so_khach)"),
             ma_loi=RONG_TUONG_MINH,
             do=("ti_le_cat_vs_tran", "do_dai_ra_khop_ke_cat")),
    GiaiDoan(QC, "asv_media", "asv_media.qc", sau=(IMAGE_FINISH,),
             tien_quyet=(
                 "co ban giao mp4 cua image_finish + du tai lieu thuong nguon (ke "
                 "hoach, ban dung) (giai_doan_qc.py:74,79)",
                 "ban ra VA ban nguon phai giai ma duoc — mot tep hong nem tho o "
                 "day, khong suy giam (giai_doan_qc.py:98)",
                 # 🔴 TIEN DE IM LANG: khac han T3/T13/T17/T18 von suy giam.
                 #    ⚠️ T17 bo sung 27/09: `giai_doan_qc.py:273` dat
                 #    `ly_do_khong_do["T13"] = ly_do_khong_do["T17"]` — MOT luot giai ma
                 #    hong lam CA HAI khong do duoc, nen mot ban khai chi ke T13 noi
                 #    HEP hon thuc te va lam nguoi doc tin T17 luon co so.
                 "do duoc am luong bang loudnorm: khong do duoc thi CA giai doan "
                 "hong (khac T3/T13/T17/T18 von ha xuong khong_kha_dung) "
                 "(giai_doan_qc.py:103 · tach_tieng.py:282)",
                 "ban dung khai cach render; thieu thi MAC DINH ve SAO_CHEP "
                 "(giai_doan_qc.py:113)",
                 "do dai MONG DOI doc ke cat cua image_finish khi co, ⛔ khong "
                 "doan tu chinh tep dang do (giai_doan_qc._thoi_luong_mong_doi)",
                 "ffmpeg co bo loc libvmaf + mo hinh, neu khong T18 thanh "
                 "khong_kha_dung (giai_doan_qc.py:245)",
                 "giai doan nay KHONG tu lam hong lan chay, va tu 27/09 "
                 "nguoi goi CUNG khong: QC la BO DO va BAO CAO, ⛔ khong "
                 "phai cong cam phat hanh (chu du an chot). `thi_hanh` doc "
                 "`_qc_hong`, GHI mot dong warning, roi DI TIEP; phat hien "
                 "nam o `qc_muc_hong` + `qc_ky_thuat_dat` + qc_report.json "
                 "(thi_hanh.py:~650)"),
             ma_loi=RONG_TUONG_MINH,
             do=("t1_den_t18",)),
    # 🔑 `asv_gpu`: nap model len card (whisper, SQUIM, MetricX), tung bo do mot
    #    tien trinh con, lan luot — dinh VRAM = bo do nang nhat, va card duoc tra
    #    khi tien trinh thoat. Dung CUNG suat `tach_nguon_cuc_bo` voi hai giai
    #    doan GPU kia: ba viec nap model len mot card dung chung khong chay chong.
    GiaiDoan(QC_DO_LUONG, "asv_gpu", "asv_gpu.qc_do_luong", sau=(QC,),
             tai_nguyen="tach_nguon_cuc_bo", tai_nguyen_suat=1,
             tien_quyet=(
                 "co ban ke doan tieng .json cua voice_synthesis "
                 "(giai_doan_qc_do_luong.py:92)",
                 "moi doan phai co tep TTS con doc duoc, va duoc dua qua DUNG "
                 "`he_so_co_gian` ma ban phoi da ap "
                 "(giai_doan_qc_do_luong.py:9)",
                 "bo do co venv + model; thieu thi `khong_kha_dung` trong bao cao "
                 "va giai doan VAN xong, ⛔ khong nem "
                 "(giai_doan_qc_do_luong.py:31)",
                 "card do nen tang cap; ba viec GPU dung CUNG suat "
                 "`tach_nguon_cuc_bo` (pipeline.py, khai ngay tren)",
                 # ⚠️ Da do va KHONG dung — mot tien de bi tuong la da co.
                 "SQUIM KHONG thay khoang lang chen giua cau (SI-SDR 15,96 so voi "
                 "16,58 cua ban sach) ⇒ ⛔ dung doc bang chung nay thanh 'da co "
                 "cong gac cho dut quang' (giai_doan_qc_do_luong.py:71)"),
             ma_loi=RONG_TUONG_MINH,
             do=("wer_cer_giong", "pesq", "si_sdr")),
    # 🔑 `auto_scan_video` chu khong `asv_media`: duong nay goi model, tuc
    #    cung nang luc voi `edit_plan`/`content_process`. Nhet mot loi goi
    #    model vao giai doan cua app khac la pha phep dinh tuyen `test_402`
    #    chot — va phep dinh tuyen do la thu quyet dinh worker nao nhat viec.
    GiaiDoan(QC_AI, "auto_scan_video", "auto_scan_video.qc_ai", sau=(QC_DO_LUONG,),
             tai_nguyen="llm_remote", tai_nguyen_suat=1,
             tien_quyet=(
                 "cong `LTT_ASV_QC_AI` phai bang '1'; tat thi giai doan tra ve som "
                 "nhung VAN `succeeded` — bo qua han mot giai doan se lam "
                 "`len(da_xong)` khong bao gio bang `len(CHUOI)` "
                 "(giai_doan_qc_ai.py:12,72)",
                 "co ban dich cua content_process (giai_doan_qc_ai.py:149)",
                 # 🔴 TIEN DE IM LANG: bi bo, khong bi bao.
                 "moi muc phai co DU `ma` + goc + `chu`: thieu mot trong ba thi muc "
                 "do bi BO LANG LE khoi phep soat (giai_doan_qc_ai.py:97)",
                 # 🔴 TIEN DE IM LANG: phan quyet co ma khong thanh viec.
                 "ban bien tap cua edit_plan phai co de phan quyet SINH duoc viec "
                 "sua; thieu thi phan quyet van duoc ghi nhung KHONG thanh viec "
                 "(giai_doan_qc_ai.py:414)",
                 "rut du hai khung moi cho noi, it hon thi `hong` chu khong phai "
                 "mot phan quyet (giai_doan_qc_ai.py:200)",
                 "lop hinh chi TU VAN, khong sinh viec sua "
                 "(sua_chua.QC_HINH_LA_TU_VAN, giai_doan_qc_ai.py:305)"),
             ma_loi=RONG_TUONG_MINH,
             do=("ti_le_bao_dong_gia",)),
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
