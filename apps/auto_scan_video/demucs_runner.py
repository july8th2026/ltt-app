"""Tien trinh con tach nguon tieng. Chay bang `python -m apps.auto_scan_video.demucs_runner`.

    python -m apps.auto_scan_video.demucs_runner <vao.wav> <thu_muc_ra> [--buoc-gpu]

## Vi sao la TIEN TRINH CON chu khong phai mot lan goi ham

Hai ly do, ca hai deu la kinh nghiem cua chinh kho nay:

1. **Card do nen tang cap.** `platform_core.gpu_lease` giu cho mot card roi
   `JobContext.gpu_env()` truyen no xuong qua bien moi truong. Mot tien trinh
   con thua huong moi truong do; mot lan goi ham trong worker thi khong — no
   se thay bat cu card nao torch tu chon, va do la mot cuoc dua voi chinh cai
   lease vua giu.

2. **Torch/CUDA sap la sap ca tien trinh.** `job_worker.py` da ghi ly do do khi
   giai thich vi sao worker la tien trinh rieng chu khong phai luong: "job nang
   goi thu vien C/CUDA giu GIL va co the sap ca tien trinh; mot job hong khong
   duoc keo theo job cua khach hang khac". Cung lap luan ay ap dung o day.

## Vi sao KHONG dung `torchaudio.save` — va vi sao khong va no nhu ban di san

Ban di san (`Cut_only ver2/nerf_engine/stages/audio.py:8`) tiem mot ban va vao
`torchaudio.save` de doi sang `soundfile`, vi `torchaudio >= 2.10` doi
`torchcodec` ma DLL cua no hong tren Windows. Ban va do dung — nhung no phu
thuoc `soundfile`, va **`soundfile` khong co trong moi truong nay**:

    torchaudio 2.11.0+cpu
    torchaudio.save -> ImportError: TorchCodec is required for save_with_torchcodec
    soundfile      -> KHONG CAI

⭐ Nen thay vi tiem mot ban va vao ruot mot thu vien khac de goi mot thu vien
   thu ba, tep nay **khong goi `torchaudio.save`**. No doc va ghi WAV bang
   module `wave` cua thu vien chuan. Bo di mot phu thuoc, mot ban va toan cuc,
   va ca mot lop hong chi xuat hien tren Windows.

⛔ Khong in gi ra stdout ngoai dong JSON ket qua o cuoi: tien trinh cha doc
   stdout de lay ket qua.
"""
from __future__ import annotations

import json
import sys
import wave
from pathlib import Path

#: Ten cac nguon ma htdemucs tach ra. Thu tu do model quyet dinh, khong phai ta.
NGUON_MONG_DOI = ("drums", "bass", "other", "vocals")


def doc_wav(duong: str):
    """WAV PCM 16-bit -> (mang float32 [kenh, mau], tan_so). Khong dung torchaudio.

    ⚠️ Ham nay nap CA TEP vao RAM. No con lai cho phep kiem va cho cac tep ngan;
       duong chay that di qua `doc_khoi_wav` (xem `KHOI_GIAY`).
    """
    import numpy as np

    with wave.open(duong, "rb") as f:
        if f.getsampwidth() != 2:
            raise ValueError("chi ho tro WAV PCM 16-bit")
        kenh = f.getnchannels()
        tan_so = f.getframerate()
        khung = f.readframes(f.getnframes())
    mau = np.frombuffer(khung, dtype="<i2").astype("float32") / 32768.0
    return mau.reshape(-1, kenh).T, tan_so


def ghi_wav(duong: str, mang, tan_so: int) -> None:
    """(kenh, mau) float32 -> WAV PCM 16-bit.

    Kep bien do TRUOC khi doi kieu: mot mau vuot [-1, 1] ma doi thang sang int16
    se **cuon vong** — mot dinh am to bien thanh mot tieng no. Kep thi no chi bi
    cat ngon, nghe duoc.
    """
    import numpy as np

    x = np.clip(np.asarray(mang, dtype="float32"), -1.0, 1.0)
    i16 = (x * 32767.0).astype("<i2")
    with wave.open(duong, "wb") as f:
        f.setnchannels(int(i16.shape[0]))
        f.setsampwidth(2)
        f.setframerate(int(tan_so))
        f.writeframes(i16.T.tobytes())


def them_khung(f: wave.Wave_write, mang) -> None:
    """Noi them mot khoi (kenh, mau) float32 vao mot WAV dang mo de ghi.

    Cung phep kep bien do nhu `ghi_wav`, cung ly do. Tach ra thay vi goi lai
    `ghi_wav`: `ghi_wav` **mo va dong** tep, nen goi no nhieu lan la ghi de,
    khong phai ghi noi.
    """
    import numpy as np

    x = np.clip(np.asarray(mang, dtype="float32"), -1.0, 1.0)
    f.writeframes((x * 32767.0).astype("<i2").T.tobytes())


def doc_khoi_wav(f: wave.Wave_read, tu: int, so_mau: int):
    """Doc `so_mau` mau bat dau tu vi tri `tu` -> (kenh, mau) float32.

    Doc theo khoi thay vi nap ca tep la ca ly do ton tai cua duong chay khoi:
    xem ghi chu o `KHOI_GIAY`.
    """
    import numpy as np

    kenh = f.getnchannels()
    f.setpos(int(tu))
    khung = f.readframes(int(so_mau))
    mau = np.frombuffer(khung, dtype="<i2").astype("float32") / 32768.0
    return mau.reshape(-1, kenh).T


# ══════════════════════════════════════════════════════════════════════════════
#  Tran BO NHO — thu that su tang theo do dai
# ══════════════════════════════════════════════════════════════════════════════
#
#: 🔴 **Do that 03/09 tren venv san pham (torch 2.11.0+cu128, RTX 5060 Ti), bon
#:    do dai, va ket qua lat nguoc dieu toi tuong truoc khi do.**
#:
#:    | tieng vao | thoi gian | VRAM dinh | RSS dinh |
#:    |---|---|---|---|
#:    |   60 s |  5,5 s | 1089 MiB | 1557 MB |
#:    |  180 s |  9,2 s | 1089 MiB | 1829 MB |
#:    |  600 s | 21,6 s | 1089 MiB | 3152 MB |
#:    | 1800 s | 71,9 s | 1089 MiB | 7323 MB |
#:
#: ⭐ **VRAM PHANG tuyet doi tren dai 30 lan.** `apply_model` tu chia doan ben
#:    trong va giu ket qua o phia CPU. Nen thu ta phai chan khong phai VRAM —
#:    ma la RAM:
#:
#:        RSS ~ 1253 MB + 3,35 MB moi giay tieng      (khop tuyen tinh, 4 diem)
#:
#: 🔴 Va do la mot MAU THUAN voi mot thu KHAC da khai, khong phai mot cho de
#:    toi uu: `nhap_media.THOI_LUONG_TOI_DA_S = 7200` — san pham **nhan** video
#:    120 phut. Theo cong thuc tren, mot lan tach nguon cho dung mot tep hop le
#:    do can **~24,8 GiB**. May nay co **31,9 GiB tong** va ~17,8 GiB trong khi
#:    dang phuc vu khach.
#:
#:    ⇒ Mot job HOP LE, chay MOT MINH, du giet may. `tai_nguyen_suat=1` khong
#:      cuu duoc: no chi bao dam co dung mot cai.
#:
#: ⭐ Va cho nay khong hien ra o bat cu phep khai bao nao cua nen tang:
#:    `asv_gpu/manifest.py` khai `gpu_vram_mb`, tuc khai dung cai KHONG tang.
#:
#: 🔑 Nen ta khong ha tran san pham (do la lay mot loi ky thuat ra bat khach
#:    tra) — ta **chan muc tieu thu**: tach theo KHOI, doc vao theo khoi va ghi
#:    ra theo khoi, nen RSS thanh O(khoi) chu khong con O(do dai).
#:
#: 300 giay: du lon de phan phi ton meo dau moi khoi thanh nho (~3% tinh lai o
#: phan phu), du nho de dinh RSS dung quanh 2,3 GiB o MOI do dai dau vao.
KHOI_GIAY = 300

#: Phan chong nhau giua hai khoi lien tiep, de tron mem cho noi.
#:
#: ⛔ Cat khan tai ranh khoi thi nghe ra: hai khoi duoc tach doc lap nen pha va
#:    muc nen hai ben mep khong khop tuyet doi, va tai nguoi rat gioi bat cac
#:    bat thuong DOT NGOT. 10 giay tron tuyen tinh lam cho no khong con dot ngot.
PHU_GIAY = 10

#: Cho chu may go de: `set LTT_DEMUCS_KHOI=120`.
BIEN_KHOI = "LTT_DEMUCS_KHOI"


#: So lan dich ngau nhien khi goi `apply_model`. **0 = tat.**
#:
#: 🔴 Mac dinh cua demucs 4.1.0 la `shifts=1`, va doc ma no ra thi day la mot
#:    mac dinh chi co mat xau:
#:
#:        if shifts:
#:            for shift_idx in range(shifts):
#:                offset = random.randint(0, max_shift)   # khong gieo hat
#:            out /= shifts                               # chia cho 1
#:
#:    Mot lan chay o MOT diem dich NGAU NHIEN, roi chia cho 1. Tuc no lay tron
#:    ven tinh ngau nhien cua phep tang cuong ma **khong lay duoc chut loi ich
#:    trung binh nao** — trung binh tren mot mau thi khong phai trung binh. No
#:    con dem them 0,5 giay moi dau de tra tien cho viec do.
#:
#: 🔴 Va hau qua khong dung o "ket qua hoi khac": `van_tay_tach` HUA ban nen la
#:    ham tat dinh cua (nguon, model, chinh sach stem, phien ban cong cu). Voi
#:    `shifts=1` loi hua do **sai**. Do that 03/09: chay hai lan cung mot tep
#:    qua cung mot duong ma cho ra hai ket qua khac nhau (bass lech RMS 0,0072,
#:    tuong quan **-0,99** — doi dau). Mot cache tra ve thu ma tinh lai khong ra
#:    duoc thi khong con la cache, va ca cau chuyen artifact/lineage cua app dua
#:    tren dieu do.
#:
#: ⭐ Nen o day dat THANG `shifts=0` thay vi dua vao mac dinh. Mot hanh vi quan
#:    trong khong duoc phep phu thuoc vao mot mac dinh cua thu vien ben thu ba.
DICH_NGAU_NHIEN = 0

#: Cho phep dung lai hanh vi CU de do doi chieu: `set LTT_DEMUCS_DICH=1`.
#:
#: ⭐ Co mat vi mot ly do cu the: cau hoi "tach theo khoi co lam giam chat luong
#:    khong" chi tra loi duoc khi co MOT MOC de so. Moc dung nhat khong phai mot
#:    nguong bia ra, ma la **dao dong ma san pham VON DA CO** — tuc chenh lech
#:    giua hai lan chay cua chinh ban `shifts=1` cu.
BIEN_DICH = "LTT_DEMUCS_DICH"

#: Phan chong lap giua cac DOAN NOI BO cua `apply_model`. Mac dinh cua demucs
#: cung la 0,25 — dat thang o day vi `buoc_phan_doan` phai tinh ra **dung** con
#: so ma `apply_model` dung; hai cho doc hai nguon thi som muon se lech nhau.
CHONG_LAP = 0.25


def _model_goc(model):
    """Model con thuc su giu tham so. `BagOfModels` khong giu `segment` cua rieng no."""
    con = list(getattr(model, "models", []) or [])
    return con[0] if (getattr(model, "segment", None) is None and con) else model


def tan_so_model(model) -> int:
    """Tan so lay mau ma model duoc huan luyen tren. 0 = khong biet."""
    try:
        return int(getattr(_model_goc(model), "samplerate", 0) or 0)
    except (AttributeError, TypeError, ValueError):
        return 0


def buoc_phan_doan(model) -> int:
    """Buoc luoi phan doan noi bo cua model, tinh bang mau. 0 = khong biet.

    🔴 **Day la cho quyet dinh viec tach theo khoi co lam doi ban ra hay khong,
       va do that 03/09 chi thang vao no.**

       Khoi DAU trung khit tung mau voi ban tach ca tep (lech dung 0,000). Cac
       khoi sau lech deu ~-42,7 dBFS. Ly do khong phai cho noi — khong co gai
       nao o ranh khoi — ma la: `apply_model` chia ben trong theo
       `offsets = range(0, length, stride)`. Khoi dau bat dau o 0 nen luoi cua
       no trung luoi cua ban ca tep; khoi thu hai bat dau o mot cho **khong**
       chia het cho `stride` nen MOI doan trong no lech pha, tu dau den cuoi.

    ⭐ Nen ranh khoi duoc lam tron XUONG boi cua buoc nay. Khi do offset tuyet
       doi cua moi doan la `(m + j) * stride` — dung bang offset ma ban ca tep
       dung — va phan ruot cua khoi tro lai trung khit. Chi con hai mep khoi
       lech, vi o do it doan phu len nhau hon nen `sum_weight` khac; do la dung
       phan ma `PHU_GIAY` tron len.
    """
    try:
        m = _model_goc(model)
        doan = int(int(m.samplerate) * float(m.segment))
        return max(0, int((1.0 - CHONG_LAP) * doan))
    except (AttributeError, TypeError, ValueError):
        # ⛔ Tra 0 nghia la "khong biet luoi". Nguoi goi PHAI nem chu khong duoc
        #    lang le bo qua phep ghim — xem `tach_theo_khoi`.
        return 0


#: So luong torch duoc dung. ⛔ KHONG phai so loi cua may.
#:
#: 🔴 **Do duoc 03/09, va no la nguyen nhan gan nhat cua mot lan may chet.**
#:    Hop den ghi lai **muoi hai tien trinh nay chay trong 4 phut 12 giay, moi
#:    cai dinh 462-984% CPU** — tuc moi tien trinh mot minh doi 5 den 10 loi
#:    logic. Luc 16:51:09 CPU cham 100%, RAM trong tut tu 17,7 xuong 14,1 GB,
#:    va may khong ghi them dong nao nua.
#:
#: ⚠️ Truoc ban nay tep nay **khong dat gioi han nao**. Torch tren CPU mac dinh
#:    lay het loi vat ly, va `apply_model` cua demucs song song rat sau.
#:
#: 🔑 Va day la cho ma ngan sach cua gate **khong voi toi duoc**: `-n 6` dem
#:    WORKER PYTEST, khong dem thu moi worker sinh ra. Sau worker, moi worker
#:    mot demucs, moi demucs muoi luong = 60 luong tren 10 loi. Mot tien trinh
#:    chau khong xin khoa, khong khai bao, va khong nam trong bat cu phep tinh
#:    nao — no chi hien ra o phep DO tai (`gate.loi_dang_ban`).
#:
#: ⭐ **4, khong phai 2 va khong phai 10** — va con so nay dua tren MOT dU KIEN
#:    do duoc, khong phai mot cam giac an toan:
#:
#:    Trong PRODUCTION chi co **MOT** demucs chay tai mot thoi diem.
#:    `pipeline.CHUOI` khai `AUDIO_PREPARE` va `TRANSCRIBE` dung **chung mot ten
#:    tai nguyen** `tach_nguon_cuc_bo` voi `tai_nguyen_suat=1`, va nen tang
#:    cuong che that bang lease (`job_runner._cho_tai_nguyen` + `leases`).
#:
#:    ⇒ Chan xuong 2 se lam mot job cua khach that cham gap ~5 lan de doi lay
#:      mot thu khong xay ra. Mot tran an toan phai bao ve truoc mot moi nguy CO
#:      THAT, khong phai truoc mot moi nguy tuong tuong.
#:
#: ⚠️ Truong hop NHIEU demucs cung luc chi ton tai trong BO TEST (sau `-n 6`),
#:    va no da nam sau rao chan `LTT_TEST_NANG`. O do 6 x 4 la vuot suat, nhung
#:    moi tien trinh van co tran — khac han voi truoc, khi moi cai lay het may.
#:
#: 🔑 Va 4 khong phai mot nua cua 10 lam tron: demucs het gan het loi ich song
#:    song quanh 4 luong, nen phan tu 4 len 10 mua duoc rat it toc do ma tra ca
#:    kha nang dap ung cua may.
#:
#: ⚠️ Tran nay con an CA KHI chay tren CUDA: phep do 03/09 thay tien trinh dinh
#:    **413% CPU** o ca bon do dai du toan bo phep tinh nam tren card. Tuc no
#:    khong phai mot tran "chi cho duong CPU" — go no ra la mo lai dung cai lo
#:    da lam may chet, ke ca khi co GPU.
LUONG_TORCH = 4

#: Cho phep chu may go de: `set LTT_DEMUCS_LUONG=6`.
BIEN_LUONG = "LTT_DEMUCS_LUONG"


def _so_tu_moi_truong(ten: str, mac_dinh: int) -> int:
    import os

    try:
        n = int(os.environ.get(ten, "") or mac_dinh)
    except ValueError:
        n = mac_dinh
    return max(1, n)


def _dich_ngau_nhien() -> int:
    """So lan dich ngau nhien. 0 tru khi chu may co y bat lai de do doi chieu."""
    import os

    try:
        return max(0, int(os.environ.get(BIEN_DICH, "") or DICH_NGAU_NHIEN))
    except ValueError:
        return DICH_NGAU_NHIEN


def _dat_tran_luong(torch) -> int:
    """Chan so luong torch. Tra ve so da dat, de ghi vao ket qua.

    ⛔ Dat TRUOC `apply_model`. `torch.set_num_threads` sau khi mot phep tinh
       da bat dau thi khong con tac dung len phep tinh do.
    """
    n = _so_tu_moi_truong(BIEN_LUONG, LUONG_TORCH)
    try:
        torch.set_num_threads(n)
        # Luong lien-phep-tinh: mac dinh cua torch cung la so loi. Mot phep
        # `set_num_threads` khong cham toi no.
        if hasattr(torch, "set_num_interop_threads"):
            try:
                torch.set_num_interop_threads(1)
            except RuntimeError:
                # Chi dat duoc TRUOC phep tinh dau tien cua tien trinh. Neu da
                # muon thi bo qua — `set_num_threads` da lo phan lon.
                pass
    except (AttributeError, RuntimeError):
        return 0
    return n


class ThieuCard(RuntimeError):
    """Nen tang da cap card nhung torch khong thay CUDA.

    ⛔ Day KHONG duoc phep thanh mot lan chay CPU im lang. Xem `chon_thiet_bi`.
    """


def chon_thiet_bi(torch, *, buoc_gpu: bool) -> str:
    """Thiet bi de chay, va mot cho tu choi ro rang thay vi mot cho tut xuong.

    🔴 Ban truoc viet `"cuda" if torch.cuda.is_available() else "cpu"` — mot
       **cho tut xuong CPU im lang**, dung thu `V4_RESOURCE_CPU_GPU_POLICY` cam
       ("no silent CPU fallback in production if GPU is required").

    ⭐ Va cai gia cua no khong phai "cham hon mot chut". Do that 03/09: cung mot
       tep, CUDA 21,6 giay / CPU thi lau hon **hang chuc lan** — trong suot thoi
       gian do no van giu suat `tach_nguon_cuc_bo`, tuc **moi phien chay cua moi
       khach khac deu dung lai sau no**. Mot lan hong dieu phoi GPU khong duoc
       phep bien thanh mot lan tac ca hang doi ma khong ai biet vi sao.

    🔑 Hai truong hop khac han nhau, va phan biet chung la ca y nghia cua tham so:

      * `buoc_gpu=False` — nen tang **khong** cap card (may khong co GPU, hoac
        lan nay khong xin). CPU la duong da khai, khong phai mot cho tut xuong.
      * `buoc_gpu=True` — nen tang **da giu cho** mot card qua `gpu_lease` va da
        ghim no bang `CUDA_VISIBLE_DEVICES`. Torch khong thay CUDA o day nghia
        la viec cap card da hong. Do la mot **loi**, va no phai keu.
    """
    co = bool(torch.cuda.is_available())
    if co:
        return "cuda"
    if buoc_gpu:
        raise ThieuCard(
            "nen tang da cap card nhung torch khong thay CUDA — "
            "khong tu tut xuong CPU (xem chon_thiet_bi)")
    return "cpu"


def bang_chung_thiet_bi(torch, thiet_bi: str) -> dict:
    """Card NAO da chay — de so ke tai nguyen kiem duoc, khong chi tin duoc.

    ⛔ Chuoi `"cuda"` khong phai bang chung: no khong noi card nao.

    🔑 Nhung tien trinh nay **khong duoc phep** doc bien moi truong ghim card de
       lay ten do — ke ca chi de ghi lai. Guard I11 (`test_401._CAM_GPU`) cam
       moi tep cua `auto_scan_video` cham vao co che cap card, va lan dau viet
       ham nay toi da vi pham no roi bien ho rang "doc de lam bang chung thi
       khac voi tu chon". Khong khac du: mot tep BIET ten bien do la mot tep chi
       con thieu mot dong nua la tu ghim duoc card.

    ⭐ Va cho dung han hoa ra gon hon: **cha da biet card nao** — no giu
       `ctx.gpu_uuid` va chinh no goi `gpu_env()`. Nen con chi bao cai no THAY
       (`torch.cuda.get_device_name(0)`, luon la thiet bi 0 vi card da bi ghim
       tu ngoai), con cha ghep cai no CAP vao. Doi chieu hai dau do la phep kiem
       that; mot dau tu bao cao ca hai thi khong kiem duoc gi.
    """
    bc = {"thiet_bi": thiet_bi}
    if thiet_bi == "cuda":
        try:
            bc["ten_card"] = torch.cuda.get_device_name(0)
        except (AttributeError, RuntimeError):    # driver tra loi -> khong co ten
            bc["ten_card"] = ""
    return bc


def tach_theo_khoi(model, torch, vao: str, thu_muc: Path, *, thiet_bi: str,
                   ap=None) -> dict:
    """Tach ca tep theo tung khoi, ghi noi tiep. RSS thanh O(khoi).

    Moi khoi tinh them `PHU_GIAY` giay o duoi de tron voi dau khoi sau. Vung
    tron duoc **tinh hai lan** — mot lan la duoi khoi truoc, mot lan la dau khoi
    sau — roi tron tuyen tinh. Do la ly do phan phi ton tinh lai ~3%.

    ⛔ Ghi theo dong chay, khong gom lai roi ghi mot the: gom lai la dung cai
       O(do dai) vua bo di quay tro lai bang cua sau.
    """
    import numpy as np

    # Ham nay ghi vao `thu_muc`, nen no bao dam thu muc do ton tai. ⛔ Dua vao
    # nguoi goi da tao san la mot phu thuoc khong ai thay cho toi khi co nguoi
    # goi thu hai — va o day nguoi goi thu hai chinh la bo test.
    Path(thu_muc).mkdir(parents=True, exist_ok=True)

    # ⭐ `ap` la duong de phep kiem thay `apply_model` bang mot ham gia. Do la
    #    ca ly do so hoc chia khoi (phu song, tron cho noi, ghim luoi, do dai ra)
    #    kiem duoc **ma khong nap mot model that** — dieu ma
    #    `V4_RESOURCE_CPU_GPU_POLICY` doi thang: "unit tests never launch real
    #    Demucs". Mot mac dinh `None` chu khong phai mot tham so bat buoc: duong
    #    chay that khong duoc phep phu thuoc vao viec ai do truyen dung thu vao.
    if ap is None:
        from demucs.apply import apply_model as ap

    with wave.open(vao, "rb") as f:
        if f.getsampwidth() != 2:
            raise ValueError("chi ho tro WAV PCM 16-bit")
        tan_so = f.getframerate()
        tong_mau = f.getnframes()
        kenh_vao = f.getnchannels()

        # ⛔ Ghim luoi (duoi day) tinh buoc bang tan so cua MODEL, con khoi tinh
        #    bang tan so cua TEP. Hai tan so lech nhau thi phep ghim tro thanh vo
        #    nghia mot cach **im lang** — ranh khoi van la boi cua mot con so,
        #    chi la khong phai con so ma `apply_model` dung. Duong chay that luon
        #    khop (`rut_ban_day_du` ep 44,1 kHz), nen lech o day la mot loi lap
        #    trinh va phai keu ngay chu khong hien ra o chat luong ban ra.
        sr_model = tan_so_model(model)
        if sr_model and sr_model != tan_so:
            raise ValueError(
                f"tan so tep {tan_so} khac tan so model {sr_model} — "
                "phep ghim luoi phan doan se sai")

        khoi_mau = max(1, _so_tu_moi_truong(BIEN_KHOI, KHOI_GIAY)) * tan_so
        phu_mau = min(PHU_GIAY * tan_so, max(0, khoi_mau // 2))

        # ⛔ Ghim ranh khoi vao luoi phan doan cua model. Bo doan nay di thi ruot
        #    cac khoi sau lech pha — xem `buoc_phan_doan`.
        buoc = buoc_phan_doan(model)
        if not buoc:
            # 🔴 Bo qua phep ghim mot cach im lang chinh la loai loi ca pha nay di
            #    sua: ban ra van "dung", chi la ty so tin/lech tut tu 54,4 dB
            #    xuong 27,1 dB va khong co dau hieu nao o dau ca.
            raise ValueError("khong doc duoc buoc phan doan cua model — "
                             "khong the ghim ranh khoi vao luoi")
        if khoi_mau >= buoc:
            khoi_mau = (khoi_mau // buoc) * buoc
            phu_mau = min(phu_mau, max(0, khoi_mau // 2))

        ten_nguon = list(model.sources)
        duong_ra = {t: str(thu_muc / f"{t}.wav") for t in ten_nguon}
        tep_ra = {}
        try:
            for t in ten_nguon:
                w = wave.open(duong_ra[t], "wb")
                w.setnchannels(2); w.setsampwidth(2); w.setframerate(int(tan_so))
                tep_ra[t] = w

            len_ra = np.linspace(0.0, 1.0, phu_mau, dtype="float32") if phu_mau else None
            len_vao = (1.0 - len_ra) if phu_mau else None

            duoi_truoc = None       # (nguon, kenh, phu_mau) — duoi cua khoi truoc
            bat_dau = 0
            so_khoi = 0
            while bat_dau < tong_mau:
                lay = min(khoi_mau + phu_mau, tong_mau - bat_dau)
                x = doc_khoi_wav(f, bat_dau, lay)
                if kenh_vao == 1:
                    # htdemucs mong doi stereo. Nhan doi kenh thay vi de model tu doan.
                    x = np.vstack([x, x])

                with torch.no_grad():
                    ra = ap(model, torch.from_numpy(x).unsqueeze(0),
                            device=thiet_bi, progress=False,
                            overlap=CHONG_LAP,
                            shifts=_dich_ngau_nhien())[0]
                ra = ra.cpu().numpy()
                so_khoi += 1

                if duoi_truoc is None:
                    het = min(khoi_mau, ra.shape[-1])
                    for i, t in enumerate(ten_nguon):
                        them_khung(tep_ra[t], ra[i][:, :het])
                else:
                    # 🔑 `len_vao`/`len_ra` chi la `None` khi `phu_mau == 0`,
                    #    va khi do `duoi_truoc` khong bao gio duoc dat — nen
                    #    nhanh nay khong the chay. Rang buoc do la NGAM: no dung
                    #    hai bien cach nhau ba muoi dong de suy ra. Khai ro de
                    #    mot lan sua sau khong pha no ma khong ai thay.
                    assert len_vao is not None and len_ra is not None, (
                        "khong the None o day: duoi_truoc chi duoc dat khi phu_mau > 0")
                    n = min(phu_mau, ra.shape[-1], duoi_truoc.shape[-1])
                    for i, t in enumerate(ten_nguon):
                        tron = duoi_truoc[i][:, :n] * len_vao[:n] + ra[i][:, :n] * len_ra[:n]
                        them_khung(tep_ra[t], tron)
                        them_khung(tep_ra[t], ra[i][:, n:min(khoi_mau, ra.shape[-1])])

                if phu_mau and ra.shape[-1] > khoi_mau:
                    duoi_truoc = ra[:, :, khoi_mau:khoi_mau + phu_mau].copy()
                else:
                    duoi_truoc = None
                del ra, x
                bat_dau += khoi_mau
        finally:
            for w in tep_ra.values():
                w.close()

    return {"nguon": ten_nguon, "duong": duong_ra, "tan_so": int(tan_so),
            "so_khoi": so_khoi, "khoi_mau": int(khoi_mau), "phu_mau": int(phu_mau),
            "khoi_giay": round(khoi_mau / tan_so, 2),
            "phu_giay": round(phu_mau / tan_so, 2)}


class ChayTrongBoTest(RuntimeError):
    """Mot phep kiem cham toi model that ma khong xin phep."""


def _chan_nap_model_trong_bo_test() -> None:
    """Chot an toan dat NGAY TRUOC cho nap model, khong o cho goi.

    🔴 **Vi sao chot nay ton tai — mot lo hong do that trong pha 13.**

       `tests/rao_chan_nang.py` sinh ra de khong phep kiem nao nap model that
       giua mot luot gate tren may **dang phuc vu khach**. No duoc dan len hai
       phep kiem GOI THANG demucs. Nhung
       `test_406::test_cong_thoat_ban_nen_la_artifact_chinh_tac_da_kiem` voi toi
       demucs **gian tiep** — qua hang doi job — nen no khong bi rao, va no da
       chay demucs THAT **16 giay moi luot gate**, khong ai biet.

    ⭐ Bai hoc, va ly do chot nam o DAY chu khong o cho khac: **mot rao dat len
       NGUOI GOI chi chan nhung nguoi goi da biet.** Duong moi toi cung mot cho
       nguy hiem thi di vong qua no ma khong cham vao. Chot phai nam o chinh cho
       nguy hiem — cho nap model — vi o do chi co MOT duong.

    🔑 `PYTEST_CURRENT_TEST` do chinh pytest dat trong moi truong tien trinh cha,
       va `tach_nguon` chuyen ca moi truong xuong tien trinh con, nen no toi day.
       Worker that khong bao gio co bien nay — chot vo hinh voi production.

    Muon chay that thi noi ra: `set LTT_TEST_NANG=1`.
    """
    import os

    if os.environ.get("PYTEST_CURRENT_TEST") and not os.environ.get("LTT_TEST_NANG"):
        raise ChayTrongBoTest(
            "mot phep kiem dang nap model demucs THAT. Neu co y thi dat "
            "LTT_TEST_NANG=1; neu khong thi thay bang gia lap "
            "(tests/rao_chan_nang.py:gia_lap_demucs)")


def main(argv: list[str]) -> int:
    co = [a for a in argv[1:] if a.startswith("--")]
    vi_tri = [a for a in argv[1:] if not a.startswith("--")]
    if len(vi_tri) != 2:
        print(json.dumps({"loi": "cach dung: <vao.wav> <thu_muc_ra> [--buoc-gpu]"}))
        return 2
    vao, thu_muc = vi_tri[0], Path(vi_tri[1])
    buoc_gpu = "--buoc-gpu" in co
    thu_muc.mkdir(parents=True, exist_ok=True)

    import torch
    from demucs.pretrained import get_model

    luong = _dat_tran_luong(torch)

    # Card da duoc nen tang cap qua bien moi truong (xem ghi chu dau tep). Ta
    # chi HOI xem torch thay gi — khong bao gio tu chon.
    try:
        thiet_bi = chon_thiet_bi(torch, buoc_gpu=buoc_gpu)
    except ThieuCard as exc:
        print(json.dumps({"loi": str(exc), "thieu_card": True}))
        return 3

    _chan_nap_model_trong_bo_test()
    model = get_model("htdemucs")
    model.eval()

    kq = tach_theo_khoi(model, torch, vao, thu_muc, thiet_bi=thiet_bi)
    kq.update(bang_chung_thiet_bi(torch, thiet_bi))
    kq["luong_torch"] = luong
    print(json.dumps(kq))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
