"""
gate.py — MỘT lệnh chạy cổng chất lượng theo hồ sơ tường minh.

    python tools/gate.py --doi       # VONG LAP L1 — pham vi tu diff
    python tools/gate.py             # PHAN QUYET L3 — day du, ~11,4 phut
    python tools/gate.py --quick     # bo hai buoc nang, ~40 giay
    python tools/gate.py --vong-lap  # CHAN DOAN   — tinh + `--lf`, ~15 giay

## Ba che do, va chon nham thi hong theo hai kieu khac nhau

| | Chay gi | Do 27/08 | Dung khi |
|---|---|---|---|
| `--doi` | thanh phan cham toi diff | tuy diff | vong lap mac dinh |
| day du | tat ca cac buoc | **~11,4 phut** | checkpoint / truoc khi bao xong |
| `--quick` | bo `bo test` + da tien trinh | ~40 giay | sua nhieu tep lien tiep |
| `--vong-lap` | tinh + `test_nhanh --lf` | **~15 giay** | chan doan last-failed |

🔑 Gate la cong cu ra **phan quyet**, khong phai cong cu **chan doan**.

   Ngay 27/08 gate day du duoc chay **sau lan** de do loi, moi lan ~5 phut. Bon
   trong sau luot do do vi mot thu ma mot buoc con le tra loi trong nua giay:
   baseline cua phien khac · mot emoji trong stdout cua mot cong cu · ho so he
   thong stale · mot phep kiem lech thu tu. Do la 20 phut tra cho bon cau tra
   loi da co san.

⛔ Va chieu nguoc lai nguy hon: `--quick` va `--vong-lap` **khong phai bang
   chung**. Dong RESULT cua chung noi thang dieu do, vi ngay 25/08 ca hai phien
   Claude deu doc dong PASS cua `--quick` thanh "moi thu xanh" — trong khi moi
   loi that hom do deu nam o dung buoc `pytest` ma no bo qua.

## Lich chay (tu 27/08 khong con noi tiep)

Do tren may chu, 20 nhan: 16 chot tinh mat **28,3 giay** noi duoi nhau, **7,1
giay** o 8 luong. Moi buoc deu la mot tien trinh con CHI DOC (`--check`/`--kiem`)
nen song song hoa khong doi ket qua — dieu nay da duoc kiem, khong phai gia dinh.
Xem `_chay_theo_lich`.

Vì sao cần: `python -m pytest` **không** chạy test frontend. Trước file này,
"full regression xanh" không bao gồm 77 test vitest ở ba thư mục `frontend/*`,
và người chạy gate phải nhớ gõ thêm ba lệnh nữa. Một bước thủ công dễ quên là
một bước sớm muộn sẽ bị quên — audit control-plane 2026-08-06 xếp đây là việc
đáng làm nhất vì rẻ nhất.

Nguyên tắc: **chạy hết rồi mới báo**, không dừng ở lỗi đầu tiên. Dừng sớm khiến
người sửa phải chạy lại toàn bộ để thấy lỗi thứ hai — với bộ test 20 phút thì đó
là nửa giờ mất trắng mỗi vòng.
"""
from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cua_so_yen import MAC_DINH, CuaSoYen  # noqa: E402  (can sys.path o tren)

ROOT = Path(__file__).resolve().parent.parent
FRONTENDS = ("agent-canvas", "autosub-studio", "prompt-ai-ommi", "chatltt")

# ═══════════════════════════════════════════════════════════════════════════
# NGAN SACH LOI — mot chu so huu duy nhat cho ca luot gate
# ═══════════════════════════════════════════════════════════════════════════
#
# 🔴 VI SAO PHAI CO. Do 2026-09-02, sau HAI lan may treo phai reset cung.
#
#    Lich chay cu dem TIEN TRINH CON, nhung thu bi tranh la LOI. Va moi tien
#    trinh con lai la mot BE tien trinh tu no:
#
#      `bo test`      -> pytest `-n auto`                          = 20 worker
#      `frontend` x3  -> vitest 4 tu dat `min(12, numCpus - 1)`    = 36 worker
#      nhom `tinh`    -> phan con lai cua `j`                      ~ 5
#                                                          DINH  ~= 61
#
#    Tren mot may **20 loi**. Ba buoc frontend nam trong nhom `nhe`, duoc nop
#    vao CUNG mot `ThreadPoolExecutor` voi `bo test`, nen chung chay **dong
#    thoi** voi 20 worker pytest.
#
# ⛔ Cai gia khong phai "gate cham". May nay LA production: bon dich vu
#    `LTTStudioWeb`, `LTTStudioWorker`, `LTTStudioVoice`, `LTTStudioCodex` dang
#    phuc vu khach that tren dung 20 loi do.
#
# ⭐ Goc khong phai "song song hoa la sai". Goc la **khong ai so huu ngan sach
#    CPU**: moi cong cu con tu do minh theo CA MAY, va ba cong cu cung lam the
#    thi tong la ba lan ca may. Nen thu them o day khong phai mot gioi han moi —
#    la mot CHU SO HUU cho mot tai nguyen truoc gio vo chu.

#: Loi chua lai cho phan con lai cua may.
#:
#: ⚠️ Khong phai con so cho dep. Do 2026-09-02 luc may RANH: CPU nen da 27%
#:    (~5 loi) cho bon dich vu production + cac phien Claude. De danh it hon
#:    the la gate an thang vao phan dang phuc vu khach.
#:
#: ⭐ Dat 6 chu khong 5: mot phep do o luc ranh la san cua truong hop tot nhat,
#:    va thu ta dang bao ve la truong hop XAU nhat — luc khach dong.
LOI_DE_DANH_CHO_MAY = 6

#: Tran cung cho MOT cong cu con. Vitest tu dat `min(12, n-1)`; con so 12 do la
#: kinh nghiem cua ho ve diem bao hoa, khong co ly do de ta di xa hon.
LOI_TOI_DA_MOI_CONG_CU = 12


def ngan_sach_loi(*, phien: str = "", tru_phien_khac: bool = False) -> int:
    """So loi ma CA luot gate duoc dung cung luc.

    Toi thieu 2: mot may hai loi van phai chay duoc gate, chi la cham hon.

    `tru_phien_khac=True` bien ngan sach tu **per-RUN** thanh **per-MAY**: tru di
    so loi cac luot gate KHAC dang giu khoa.

    🔴 Vi sao can: truoc 03/09 ham nay chi doc `os.cpu_count()`, nen moi luot tu
       tin no co 14 loi — va **ca hai deu dung theo cach tinh cua rieng minh**.
       Do duoc: 1 luot + nen production = 19/20 loi; **2 luot = 33/20**.

    ⚠️ `BELOW_NORMAL_PRIORITY_CLASS` khong che duoc canh do, va day la tran cua
       lop bao ve ay: no cuu `LTTStudioWeb` (uu tien binh thuong) khoi gate,
       nhung hai gate deu uu tien THAP BANG NHAU nen tranh nhau song phang.

    ⛔ Mac dinh `False` de moi nguoi goi cu giu nguyen hanh vi. Chi duong chay
       that (sau khi da giu khoa) moi bat len — xem `_ap_ngan_sach_thuc`.
    """
    # 🔑 **DON VI VAT LY**, thong nhat voi `loi_cho_bo_test`.
    #
    # 🔴 Truoc 03/09 dong nay la `(os.cpu_count() or 4) - LOI_DE_DANH_CHO_MAY`
    #    = 20 - 6 = 14, tren loi LOGIC. Hau qua khong nam o `bo test` (da sua o
    #    `loi_cho_bo_test`) ma o **bo dem lich**: no cho tong <= 14, `bo test`
    #    khai 6, con **8 suat** cho buoc tinh chay cung. Tam buoc tinh ~4 loi
    #    vat ly + 6 cua bo test = 10/10 — cham tran tro lai, va lan nay khong
    #    qua duong nao co ai soi.
    #
    # ⇒ Mot don vi cho CA LUOT chay, khong phai mot don vi cho moi tang.
    con = loi_cong_cu_tu_do() - LOI_DE_DANH_VAT_LY
    if tru_phien_khac:
        try:
            from cua_so_yen import loi_phien_khac_dang_giu
            con -= loi_phien_khac_dang_giu(phien)
        except (ImportError, OSError, ValueError) as exc:
            # ⛔ Khong do duoc thi giu nguyen ngan sach cu, KHONG doan. Mot cong
            #    cu do hong khong duoc bien thanh mot cai chan.
            #
            # ⚠️ Nhung NOI RA. Ban dau day la `except Exception: pass` va banh
            #    coc `nuot loi lang le` bat dung no — dung: mot ngan sach khong
            #    tru duoc phan cua phien khac trong y het mot may dang ranh, va
            #    im lang la cach chac chan nhat de khong ai biet.
            print(f"  [ngan sach] khong doc duoc khoa phien khac "
                  f"({type(exc).__name__}: {exc}) - giu ngan sach per-RUN")
    return max(2, con)


def loi_cong_cu_tu_do() -> int:
    """So worker ma `pytest -n auto` se TU CHON. Cung nguon voi xdist.

    🔴 **HAM NAY SUA MOT LOI DANG SONG, do duoc 03/09:**

            os.cpu_count()            = 20   loi LOGIC
            psutil.cpu_count(False)   = 10   loi VAT LY   <- xdist `auto` dung
            gate truyen  -n           = 11

       `ngan_sach_loi()` tinh tren loi **logic**, xdist `auto` tinh tren loi
       **vat ly**, va ca hai bi tru cung mot hang so `LOI_DE_DANH_CHO_MAY`. Nen
       "ngan sach" 11 lai LON HON 10 — mot co che sinh ra de GIAM tai dang TANG.

    ⭐ Tren may khong sieu phan luong hai so trung nhau va loi nay **khong ton
       tai**. No chi lo ra o may co SMT — tuc dung loai may nay.

    ⛔ Bai hoc the loai, `lttchat-...-49` tra gia de co o mot ban va bi bo:
       **mot ngan sach la GIOI HAN TREN, khong phai mot phep gan.** Gan thang
       thi khi cong cu tu do ra so nho hon, cai "tran" lai thanh SAN.

    ⇒ Doc cung nguon voi `xdist/plugin.py:32` de hai ben khong bao gio lech.

    ⚠️ Khong psutil thi xdist cung roi ve `os.cpu_count()` (`plugin.py:46`), nen
       nhanh du phong tra dung thu xdist se tra — khong doan, khong tu che.
    """
    try:
        import psutil
    except ImportError:
        return os.cpu_count() or 1
    return psutil.cpu_count(logical=False) or psutil.cpu_count() or 1


def loi_dang_ban(mau_s: float = 1.0) -> float:
    """So loi VAT LY dang bi ai do chiem — **do that**, khong doan.

    ⭐ Ham nay den tu phien `lttchat` (`4420b56`), va no tra loi mot cau hoi ma
       khoa `cua_so_yen` khong the tra loi. Doc nguyen van ly do cua ho:

         `LOI_DE_DANH_VAT_LY` la mot HANG SO, dat tu mot phep do luc may RANH.
         No dung cho cai no mo ta: nen tai cua bon dich vu production. Nhung
         hai lan may treo phai reset KHONG do nen tai gay ra — chung do hai thu
         ma mot hang so khong the biet:

           · mot `pytest -n auto` go tay NGOAI gate: 20 worker, khong ngan
             sach, khong khoa
           · mot luot gate THU HAI da het `--cho` va chay de: `cua_so_yen` chi
             canh bao roi `return self`, no khong tu choi

         Ca hai deu **vo hinh voi khoa** — khoa chi thay ai XIN khoa. Ca hai
         deu **hien ra o CPU**.

    🔴 Va ngay 03/09 con mot thu thu ba, do duoc trong hop den: **muoi hai tien
       trinh `demucs`, moi cai 460-984% CPU**, chay ngoai moi khoa. Mot tien
       trinh chau khong xin khoa va khong nam trong `-n`; no chi hien ra o day.

    ⛔ **Don vi VAT LY.** Ban goc nhan voi `os.cpu_count()` = 20 (LOGIC), con
       moi phep tinh khac o day dung `loi_cong_cu_tu_do()` = 10 (vat ly). Tron
       hai don vi la **dung cai loi da khoi dau ca chuyen nay** (`-n 11` lon hon
       `auto` = 10). Doi don vi khi nhap, khong phai khi dung.

    ⚠️ Tra 0.0 khi khong do duoc: fail-open co chu y. Mot cong chat luong tu
       choi chay vi khong doc noi CPU la mot cong khong ai dung.
    """
    try:
        import psutil
    except ImportError:
        return 0.0
    try:
        phan_tram = psutil.cpu_percent(interval=mau_s)
    except (OSError, RuntimeError) as loi:
        print(f"  [ngan sach] khong do duoc CPU ({loi}) - coi nhu may ranh")
        return 0.0
    return loi_cong_cu_tu_do() * float(phan_tram) / 100.0


# ══════════════════════════════════════════════════════════════════════════════
#  MOT cau hoi, MOT cau tra loi: bo test duoc bao nhieu worker
# ══════════════════════════════════════════════════════════════════════════════

#: Loi VAT LY de danh cho may: Windows + 4 dich vu production + phien khac.
#:
#: 🔴 **Don vi VAT LY, khong phai logic.** Day la cho ca co che tung hong:
#:    `LOI_DE_DANH_CHO_MAY = 6` tru tren `os.cpu_count()` = 20 (logic), con
#:    `pytest -n auto` doc `psutil.cpu_count(logical=False)` = 10 (vat ly). Hai
#:    don vi, mot hang so ⇒ "ngan sach" 11 lai LON HON `auto` = 10. Mot co che
#:    sinh ra de GIAM tai da TANG no, suot tu `03845cb` toi 03/09.
#:
#: ⭐ Do that: nen may 3%-37% tuy gio (0,6-3,7 loi vat ly). De danh 3 phu duoc
#:    nen thuong; luc nen cao thi `loi_phien_khac_dang_giu` va tran cung o duoi
#:    keo tiep xuong.
LOI_DE_DANH_VAT_LY = 3

#: ⛔ TRAN CUNG. Chu du an chon 03/09: **uu tien an toan, chap nhan cham hon**.
#:
#:    Do that hom do: `-n 11` mat 327s; `-n 6` mat hon 15 phut (~2,8x cham hon).
#:    Cai gia do duoc chap nhan co y — mot luot gate cham khong lam ai mat gi,
#:    mot lan treo may lam khach mat dich vu.
#:
#: ⚠️ Va no la TRAN chu khong phai gia tri: khi may ban, phep tinh o duoi cho ra
#:    so nho hon va so do thang.
TRAN_WORKER_BO_TEST = 6


def loi_cho_bo_test(*, phien: str = "", do_tai: bool = True) -> int:
    """So worker cho `bo test`. **Ham DUY NHAT tra loi cau hoi nay.**

    Truoc 03/09 co sau cho cung tra loi no — `ngan_sach_loi`, `_chia_loi`,
    `LOI_TOI_DA_MOI_CONG_CU`, `loi_cong_cu_tu_do`, `loi_dang_ban`,
    `_ap_ngan_sach_thuc` — tren HAI don vi khac nhau. Chong cheo nhieu tang thi
    khong ai doc noi ca duong, va cho lech nam giua hai tang la cho khong ai soi.

    Mot phep tinh, mot don vi (**loi vat ly**), bon ve:

        vat_ly - de_danh - chiem           may con bao nhieu cho ta
        chiem = max(KHAI BAO, DO DUOC)     ai dang giu cho — hai nguon, mot so
        TRAN_WORKER_BO_TEST                tran an toan cung
        max(1, ...)                        khong bao gio tu choi chay

    ## 🔑 `max`, KHONG phai `+` — va day la ca thiet ke

    Hai nguon tin ve "ai dang chiem may", va chung **chong len nhau**:

        KHAI BAO  `cua_so_yen`: phien khac da XIN khoa va khai bao so loi
        DO DUOC   `loi_dang_ban()`: CPU that dang bi dot, bat ke ai dot

    Mot phien vua khai 6 loi vua dang dung 6 loi **xuat hien o ca hai**. Cong
    lai la tru 12 cho mot viec dang chiem 6, va ngan sach tut ve 1 — mot co che
    giam tai tu lam minh vo dung.

    ⇒ `max()` lay **cai lon hon**, tuc dem moi ke chiem cho dung mot lan:

        chi KHAI BAO   phien khac vua giu khoa, chua kip chay  -> khai bao thang
        chi DO DUOC    `pytest` go tay, bot, tien trinh chau   -> do duoc thang
        ca hai         cung mot phien                          -> dem MOT lan

    🔴 Ve DO DUOC la thu duy nhat nhin thay muoi hai tien trinh `demucs` cua
       ngay 03/09 (moi cai 460-984% CPU, khong cai nao xin khoa, khong cai nao
       nam trong `-n`). Khoa khong thay chung. Hang so khong thay chung.

    ⛔ `max(1, ...)`: mot cong chat luong tu choi chay vi ban la mot cong khong
       ai dung, va no se bi go bang mot co `--bo-qua`. Cham thi duoc, dung han
       thi khong.
    """
    vat_ly = loi_cong_cu_tu_do()

    khai_bao = 0
    if phien is not None:
        try:
            from cua_so_yen import loi_phien_khac_dang_giu
            khai_bao = loi_phien_khac_dang_giu(phien)
        except (ImportError, OSError, ValueError) as exc:
            print(f"  [ngan sach] khong doc duoc khoa phien khac "
                  f"({type(exc).__name__}) - bo qua phan tru do")

    do_duoc = 0
    if do_tai:
        # Phan VUOT nen: nen da duoc tru rieng bang `LOI_DE_DANH_VAT_LY`, nen
        # tru them ca nen mot lan nua la tru hai lan cung mot thu.
        thua = loi_dang_ban() - LOI_DE_DANH_VAT_LY
        do_duoc = max(0, int(thua + 0.5))

    chiem = max(khai_bao, do_duoc)
    if chiem:
        print(f"  [ngan sach] {chiem} loi dang bi chiem "
              f"(khai bao {khai_bao}, do duoc {do_duoc}) - lay so lon hon")
    return max(1, min(TRAN_WORKER_BO_TEST, vat_ly - LOI_DE_DANH_VAT_LY - chiem))


def _chia_loi(so_viec_nang: int) -> int:
    """Moi viec nang duoc bao nhieu loi. Toi thieu 1."""
    return max(1, min(LOI_TOI_DA_MOI_CONG_CU,
                      ngan_sach_loi() // max(1, so_viec_nang)))


#: Nhóm quyết định LỊCH CHẠY, không quyết định ý nghĩa của bước.
#:
#:   cong     — cổng gác. Chạy MỘT MÌNH và trước hết. Xem `bien dich duoc`.
#:   nang     — dài (phút). Khởi động TRƯỚC vì lịch "việc dài chạy trước" cho
#:              tổng thời gian ngắn nhất khi mọi thứ khác nấp được vào bóng nó.
#:   tinh     — mỗi bước vài giây, độc lập nhau hoàn toàn.
#:   frontend — `npm test` ở ba thư mục; độc lập với nhau và với mọi thứ khác.
#:   sau_test — ĐỌC một tệp mà `bo test` GHI. Phải chạy SAU khi bộ test xong.
#:              Xem `TEP_KHONG_DUOC_DOC_SONG_SONG` bên dưới.
NHOM = ("cong", "nang", "tinh", "frontend", "sau_test")

#: 🔴 BA TỆP MÀ BỘ TEST GHI VÀO CÂY, và bước gate nào đọc chúng.
#:
#:    `tools/test_nhanh.py::TEP_NOI_TIEP` bắt ba tệp test này chạy **nối tiếp
#:    với nhau**, nên chúng không giẫm lên nhau. Nhưng hàng rào đó chắn **sai
#:    hướng**: nó không nói gì về nhóm kiểm TĨNH của chính lượt gate đó, mà
#:    nhóm ấy chạy **song song** với `bo test` và **đọc đúng ba tệp ấy**.
#:
#: ⛔ Hệ quả đo được ngày 2026-08-29: `test_209` / `test_210` / `test_306` đỏ
#:    với `OSError: [Errno 22] Invalid argument` ngay tại `read_text()` hoặc
#:    `write_text()`. Trên Windows, hai tiến trình chạm một tệp cùng lúc cho
#:    đúng mã lỗi đó.
#:
#:    Hai phiên đã mất **gần trọn một ngày** cho chuyện này và lần lượt đổ cho:
#:    `__pycache__` cũ · một tiến trình thứ hai · một tệp ghi thứ tư chưa tìm
#:    ra · rác fixture ngẫu nhiên. **Không cái nào đúng.** Công cụ đo tự nhiễu
#:    vào phép đo của nó.
#:
#: ⭐ Docstring của `_chay_theo_lich` từng khẳng định điều kiện an toàn là "mọi
#:    bước đều CHỈ ĐỌC, nên không bước nào chạm cây — và nó đã được kiểm chứ
#:    không giả định". Câu đó đúng **một nửa**: nhóm tĩnh đúng là chỉ đọc, còn
#:    `bo test` thì GHI. Nửa được kiểm là nửa không hỏng.
TEP_KHONG_DUOC_DOC_SONG_SONG = {
    "docs/PUBLIC_API/CONTRACT_BASELINE.json": "tests/test_209_versioning_status.py",
    "locale/en/LC_MESSAGES/messages.po": "tests/test_306_banh_coc_bo_qua_va_dich.py",
    "sdk/typescript/ltt-public-api.ts": "tests/test_210_sdk_ecosystem.py",
    "server/templates/vps_dieu_khoan.html": "tests/test_306_banh_coc_bo_qua_va_dich.py",
}


class Step:
    def __init__(self, name: str, argv: list[str], cwd: Path,
                 nhom: str = "tinh", tai_nguyen: tuple[str, ...] = (),
                 so_loi: int = 1, giay_toi_thieu: float = 0.0):
        assert nhom in NHOM, nhom
        self.name = name
        self.argv = argv
        self.cwd = cwd
        self.nhom = nhom
        #: So LOI buoc nay chiem khi chay — khong phai so tien trinh.
        #:
        #: 🔴 Day la khac biet da lam treo may hai lan. Lich cu dem tien trinh
        #:    con (`bo test` = 1, moi `frontend` = 1) va ket luan "10 la vua".
        #:    Nhung `bo test` la 20 worker va moi `frontend` la 12 — nen "10
        #:    tien trinh" that ra la ~61 luong tren 20 loi.
        #:
        #: ⚠️ Mac dinh 1: mot chot tinh doc tep roi in mot dong, no dung mot
        #:    loi. Chi thu nao TU SINH be tien trinh moi khai so lon hon.
        self.so_loi = max(1, int(so_loi))
        #: Tai nguyen DOC QUYEN CAP MAY ma buoc nay can (`thanh_phan.toml`).
        #:
        #: ⚠️ Khong phai "buoc nay dung CPU" — moi buoc deu dung CPU. Chi khai
        #:    thu ma HAI LUOT SONG SONG lam hong nhau: `-n auto` an het loi,
        #:    mot CSDL test dung chung, mot cong TCP, mot GPU.
        self.tai_nguyen = tuple(tai_nguyen)
        self.ok: bool | None = None
        #: Buoc chay xong, tra 0, NHUNG tu khai la no khong lam duoc viec.
        #:
        #: 🔴 VI SAO CAN TRANG THAI THU BA. `gate.py` chi doc MA THOAT, nen
        #:    mot buoc bo qua va mot buoc dat trong Y HET nhau tren dong RESULT.
        #:    Do 31/08: `bat bien da tien trinh` xanh trong 0,7 giay vi
        #:    `check_multiproc.py` khong tao duoc CSDL test, in mot doan giai
        #:    thich rat tu te, roi `return 0`.
        #:
        #: ⭐ Va `return 0` o do la DUNG, dung sua no: mot may khong co
        #:    PostgreSQL phai chay duoc gate. Cai sai nam o cho DOC, khong o do.
        #:
        #: ⛔ Hai phien doc cung mot dong RESULT theo hai cach trai nguoc trong
        #:    cung mot ngay, va ca hai deu tuong minh dung. Do la cai gia that:
        #:    mot buoc khong chay ma trong nhu da chay thi khong ai di tim no.
        #: San thoi gian: buoc nay KHONG THE xong nhanh hon ngan nay giay.
        #:
        #: 🔴 Vi sao can. Ngay 06/09 mot phep tach ham lam hai pha pytest roi
        #:    vao ma chet sau mot `return`. `tools/test_nhanh.py` thoat sau
        #:    **0,114 giay**, ma **0**, KHONG chay mot test nao — va dong nay
        #:    in ra: `[PASS] bo test (song song) 0.1s`.
        #:
        #:    Ca NAM banh coc AST luc ay van xanh, vi chung hoi *hinh dang ma*
        #:    con hinh dang thi van dung khi cong cu da chet. Dau hieu duy nhat
        #:    la CON SO GIAY — thu gate VAN IN RA nhung khong ai doc.
        #:
        #: ⭐ Nen bien no thanh mot PHAN QUYET. Day la lop bao ve TONG QUAT:
        #:    no khong can biet buoc lam gi, chi can biet buoc do khong the
        #:    xong trong tich tac. Mot banh coc rieng cho tung cong cu thi
        #:    phai viet lai moi lan them cong cu; cai nay thi khong.
        #:
        #: ⚠️ Buoc TU KHAI bo qua (`DAU_BO_QUA`) duoc mien: "khong lam duoc
        #:    viec va noi ra" la mot trang thai HOP LE, khac han "trong nhu da
        #:    lam ma khong lam".
        self.giay_toi_thieu = max(0.0, float(giay_toi_thieu))
        self.bo_qua = False
        self.seconds = 0.0
        self.tail = ""
        self.tep_loi = ""


def _npm() -> str | None:
    """npm trên Windows là `npm.cmd`; `shutil.which` xử lý đúng cả hai."""
    return shutil.which("npm")


def _ap_ngan_sach_thuc(steps: list, phien: str) -> None:
    """Sua lai `-n` cua buoc `bo test` theo ngan sach THUC, sau khi da giu khoa.

    ⭐ Sua **tai cho** thay vi dung lai ca danh sach: `steps` co the da di qua
       `_rut_gon_vong_lap` / `_thu_hep`, va dung lai se mat phan do.

    ⚠️ Chi cham dung mot buoc, va tim no bang chinh `argv` cua no (`-n` di ngay
       sau `test_nhanh.py`) chu khong bang TEN buoc — mot cai ten la mot chuoi
       hien thi, doi luc nao cung duoc, va no se doi im lang.
    """
    moi = loi_cho_bo_test(phien=phien)
    for st in steps:
        argv = list(getattr(st, "argv", []) or [])
        if "test_nhanh.py" not in " ".join(argv) or "-n" not in argv:
            continue
        i = argv.index("-n")
        if i + 1 >= len(argv):
            continue
        cu_so = argv[i + 1]
        if str(cu_so) == str(moi):
            continue
        argv[i + 1] = str(moi)
        st.argv = argv
        st.so_loi = moi
        print(f"  [ngan sach] -n {cu_so} -> {moi} "
              f"(luot khac dang giu {loi_bi_giu_boi_phien_khac(phien)} loi)")


def loi_bi_giu_boi_phien_khac(phien: str = "") -> int:
    """Chi de IN ra. Khong tham gia phep tinh — xem `ngan_sach_loi`."""
    try:
        from cua_so_yen import loi_phien_khac_dang_giu
        return loi_phien_khac_dang_giu(phien)
    except (ImportError, OSError, ValueError):
        # Chi de IN; that bai o day da duoc `ngan_sach_loi` noi ra roi.
        return 0


def _steps(quick: bool, noi_tiep: bool = False) -> list[Step]:
    # ── Chia ngan sach loi TRUOC khi dung danh sach buoc ────────────────────
    #
    # Bon viec co the chay dong thoi va MOI viec tu sinh mot be tien trinh:
    # `bo test` + ba `frontend`. Chia ngan sach cho chung, va moi con so duoc
    # TRUYEN XUONG cong cu con thay vi de no tu do minh theo ca may.
    #
    # ⛔ KHONG chia deu. `bo test` chiem ~85% thoi gian ca luot (~360 giay),
    #    con ba `frontend` moi cai 5-15 giay. Chia deu bon phan la lay loi cua
    #    thu quyet dinh tong thoi gian de dua cho thu se xong trong chop mat.
    #
    # ⭐ Nen: `bo test` lay phan lon, frontend lay du de khong cham, va **bo dem
    #    loi** o `_chay_theo_lich` lo phan con lai — neu tong vuot ngan sach thi
    #    mot frontend doi, chu khong phai ai cung bi cat nho tu dau.
    loi_moi_viec = min(2, LOI_TOI_DA_MOI_CONG_CU)          # frontend: ngan, 2 la du
    # ⛔ `loi_cong_cu_tu_do()` la ve thu BA cua phep `min`, va no la ve chiu luc:
    #    hai ve kia tinh tren loi LOGIC, ve nay tra ve dung thu xdist se tu chon.
    #    Thieu no thi "ngan sach" 11 lai lon hon `auto` = 10. Xem docstring cua no.
    # MOT nguon duy nhat. Xem `loi_cho_bo_test`.
    loi_bo_test = loi_cho_bo_test()

    # ── Che do NOI TIEP: mot loi cho moi cong cu con ────────────────────────
    #
    # ⭐ Doan nay den tu nhanh `admin-mvp-v3` (phien lttchat) va duoc giu nguyen
    #    khi hop nhat: no giai mot bai toan KHAC voi ngan sach o tren, va hai
    #    thu bo sung cho nhau.
    #
    # 🔴 `--tuan-tu` MOT MINH khong du, va day la cho de doc nham nhat trong ca
    #    tep nay. No xep hang cac BUOC — nhung buoc `bo test` van tu mo n worker
    #    pytest ben trong no, va moi buoc `frontend` van mo 2 worker vitest.
    #    "Tuan tu" o muc lich chay khong co nghia la mot tien trinh.
    #
    # ⇒ Ho so `noi-tiep` phai ha CA HAI muc: lich chay MOT buoc mot luc, va moi
    #   cong cu con MOT tien trinh.
    if noi_tiep:
        loi_moi_viec = 1
        loi_bo_test = 1

    # 🔴 THU HOI XAC TIEN TRINH TRUOC KHI DO BAT CU THU GI.
    #
    #    Do 30/08: 282 tien trinh con `multiprocessing.spawn` mo coi, cu nhat 55
    #    gio, giu 9,5 GB RAM va **khoa 85 GB temp** (154/158 thu muc pytest khong
    #    xoa duoc). O muc do do o C: con 9,4 GB / 930 GB — va Postgres cua
    #    production nam tren C:. Day thi Postgres tu choi ghi, va trieu chung se
    #    KHONG noi "het dia".
    #
    # ⭐ `test_214` don dung roi (`join` -> `terminate` -> `join`); ro ri chi xay
    #    ra khi tien trinh CHA bi giet giua chung — gate qua gio, Ctrl-C, hay
    #    `gate.py | head` gay SIGPIPE. Khong co cach nao ngan mot tien trinh bi
    #    SIGKILL don dep sau no.
    #
    # ⇒ Nen muc tieu khong phai NGAN ma la TU LANH: don xac cu truoc moi luot.
    #    Nguong 3 gio de khong bao gio dung vao luot dang chay cua phien khac.
    don_xac = [sys.executable, "tools/don_tien_trinh_mo_coi.py", "--giet"]
    subprocess.run(don_xac, cwd=ROOT, capture_output=True, text=True,
                   encoding="utf-8", errors="replace", timeout=120)

    steps: list[Step] = [
        # 🔴 DAT DAU TIEN co chu y: mot tep khong bien dich duoc thi moi
        #    phep do phia sau deu vo nghia. Da tung commit mot tep vo cu
        #    phap ma gate bao PASS 14/14 - cac chot khac deu BO QUA tep
        #    khong parse duoc (chung dem xu huong), va `--quick` bo pytest.
        Step("bien dich duoc", [sys.executable, "tools/check_bien_dich.py"],
             ROOT, nhom="cong"),
        Step("secret scan", [sys.executable, "tools/scan_source_secrets.py"], ROOT),
        Step("app contract lint", [sys.executable, "tools/lint_app_contract.py"], ROOT),
        # 🔴 Mot tep bi ghi lai TOAN BO thi `git diff` khong doc duoc nua.
        #    Do that: 26/08 mot tep .po lech 10.465 dong; 30/08 **25 tep**
        #    cung luc — 5.356 dong nhieu che 266 dong that.
        # ⛔ Va luat KHONG phai "moi tep dung LF": hai tep von LA CRLF
        #    trong git (DEVELOPER_GUIDE.md do cong cu sinh). Nen no hoi
        #    git tung tep, khong nho mot quy uoc.
        # ⭐ `sau_test` chu KHONG phai `tinh`, va do khong chi la de qua banh
        #    coc `test_332`: chay SAU bo test la chay dung luc — no bat duoc ca
        #    truong hop mot TEST lat kieu xuong dong cua mot tep. Do dung la
        #    thu da xay ra 26/08 voi `messages.po`.
        Step("kieu xuong dong", [sys.executable, "tools/check_xuong_dong.py"],
             ROOT, nhom="sau_test"),
        # 🔴 Banh coc kich thuoc cho `server/routes/`. Hop dong app thi hanh tran
        #    900 dong / 30 handler cho `apps/` — con `server/` KHONG co nguong
        #    nao, va ba tep lon nhat kho deu nam o do. `developer.py` vuot CA HAI
        #    nguong (1.521 dong / 32 handler) chi vi no nam o thu muc khac.
        #
        # ⭐ Banh coc chu khong phai tran cung: audit 26/08 do change locality va
        #    thay `admin_api.py` co churn thap + ban dong hanh thua => te lon ma
        #    it doi va doi co lap la CHI PHI THAP, chua dang che. Che no bay gio
        #    la tra tien hom nay cho mot van de chua xuat hien.
        Step("kich thuoc route server",
             [sys.executable, "tools/check_server_routes.py"], ROOT),
        # 🔴 CHUONG DA DUC MA CHUA AI TREO — banh coc goc re nhat cua audit 26/08.
        #
        #    Bon loi tuong nhu doc lap hoa ra mot hinh dang: mot ham quet/canh bao
        #    TON TAI, co docstring, co test, co trong `__all__` — va KHONG DUONG
        #    THUC THI NAO goi toi. No trong y het mot ham dang chay.
        #
        #    Ca dat nhat: canh bao "dang ban duoi gia von" nam trong ma suot thoi
        #    gian nen tang ban anh o 45-57% gia von trong 22 ngay. No khong im vi
        #    hong — im vi khong ai cam day.
        #
        # ⭐ Da chung minh phep kiem nay BAT DUNG ca goc: go dong cam
        #    `costing.scan_for_alerts` ra thi no bao ngay.
        Step("chuong chua treo",
             [sys.executable, "tools/check_chuong_chua_treo.py"], ROOT),
        # Re nhung bat duoc thu test khong bat: mot route khong co test ma thieu
        # import thi chi vo khi nguoi dung bam. Xem tools/check_undefined_names.py.
        Step("ten chua dinh nghia", [sys.executable, "tools/check_undefined_names.py"], ROOT),
        # Banh coc: khong cho THEM cho nuot loi lang le. Xem
        # tools/check_silent_except.py vi sao khong doi ve 0 ngay.
        Step("nuot loi lang le", [sys.executable, "tools/check_silent_except.py"], ROOT),
        # 🔴 Banh coc cho chinh LUAT VAN HANH. Truoc 08/09 cadence duoc chep lai
        #    trong 10 tep ke hoach, va 5 ban chep KHONG giong nhau — trong do hai
        #    ban bao chay `test_nhanh.py` ROI `gate.py`, tuc tra ~4 phut hai lan
        #    cho cung mot tap pass/fail (buoc `bo test` ngay trong tep nay CHINH
        #    LA `test_nhanh.py`).
        #
        # ⛔ Khong ai co y viet sai. Cai sai la khong co CHO NAO de tra loi, nen
        #    ai can mot cadence thi tu viet mot cai. Buoc nay giu cho do duy nhat.
        Step("luat van hanh", [sys.executable, "tools/check_luat_van_hanh.py"], ROOT),
        # 🔴 `ruff` đã nằm sẵn trong máy nhiều tháng mà **không có cấu hình** và
        #    không nằm trong gate. Đo 06/09 nó bắt một bộ phát hiện lớn với bộ luật
        #    `F,B` (đã bỏ `B008` vì nó là `Depends()` của FastAPI) — trong đó có
        #    những lớp lỗi THẬT mà các bước viết tay không soi:
        #
        #        F811  hai ham cung ten, cai sau che cai truoc
        #        B023  bay closure trong vong lap
        #        B017  phep kiem khang dinh QUA RONG
        #        B904  raise khong `from` -> mat traceback goc
        #
        # ⚠️ SO LUONG tung ma nam o `tools/check_ruff.moc`, KHONG chep vao day.
        #    Chep mot con so vao chu thich la tao ra mot con so se troi —
        #    dung luc viet ba cho nay no DA lech (B904: 22 o ruff.toml, 26 o moc).
        #
        # ⭐ `B017` đáng chú ý riêng: nó bắt đúng lớp lỗi đã cắn bốn lần trong
        #    một buổi ngày 06/09 — một phép kiểm trông như đang đo, mà khẳng
        #    định của nó rộng đến mức nó xanh với cả bản hỏng. Xem `AGENTS.md`
        #    mục 4d lớp C.
        #
        # ⛔ Là BÁNH CÓC, không phải cổng "phải sạch": 512 lỗi thì một cổng
        #    tuyệt đối sẽ bị tắt ngay lượt đầu. Và chốt theo **mã luật** chứ
        #    không theo **tổng** — một mốc tổng có cửa hoán đổi một-đổi-một đi
        #    lọt (xoá một `F401`, thêm một `F811` thì tổng không đổi).
        Step("ruff", [sys.executable, "tools/check_ruff.py"], ROOT),
        # `mypy` cung nam san trong may nhieu thang ma KHONG co cau hinh.
        # Do 06/09: 590 phat hien / 14 ma loi, ~45 giay.
        #
        #    attr-defined   cham thuoc tinh KHONG TON TAI  -> AttributeError
        #    union-attr     cham thuoc tinh tren thu co the None
        #    arg-type       truyen sai KIEU cho tham so
        #
        # Ba ma tren bat dung lop A trong AGENTS.md muc 4d: DOAN hinh dang
        # API thay vi DOC no. So luong tung ma o `tools/check_mypy.moc`,
        # khong chep vao day.
        #
        # Dong quan trong nhat cua `mypy.ini` la `plugins = pydantic.mypy`:
        # thieu no thi mypy coi moi truong Pydantic co `Field(mac_dinh)` la
        # BAT BUOC va de ra 58 `call-arg` SAI. Do 06/09 tren mot tep:
        # khong plugin 60 loi, co plugin 1 loi — va cai 1 do la loi that.
        Step("mypy", [sys.executable, "tools/check_mypy.py"], ROOT),
        # Ranh gioi IMPORT giua cac tang -- xem `.importlinter`. 0,3 giay.
        #
        # ⛔ KHONG thay `lint_app_contract.py`. Hai cong cu giai hai bai
        #    toan khac nhau: cai kia kiem CO HOC hop dong app (manifest,
        #    CSRF, co route), cai nay kiem AI DUOC IMPORT AI. Plan ban dau
        #    ghi "thay the" va do la sai -- da sua trong `.importlinter`.
        #
        # ⭐ Do 06/09: 3 hop dong, 0 gay. Hai mon no con lai nam duoi dang
        #    `ignore_imports` CO TEN va CO LY DO, khong phai mot con so.
        Step("ranh gioi import", [sys.executable, "tools/check_ranh_gioi.py"], ROOT),
        # PowerShell khong phan biet hoa thuong o ten bien, va tham so cua script
        # chi la mot bien thuong. Nen mot vong lap gan `$ten` ghi de tham so
        # `-Ten` — khong loi, khong canh bao. Da xay ra 31/08/2026: giong tao ra
        # mang ten "HF_HOME", bien cuoi cung trong app.env.
        Step("bien .ps1 trung tham so",
             [sys.executable, "tools/check_ps_bien_trung_tham_so.py"], ROOT),
        # Banh coc: khong cho THEM so tep test bi trung. Do 23/08/2026: 24 so dang
        # trung, co so mang BA tep. Nguyen nhan la nhieu phien lam viec song song,
        # moi phien chon so tiep theo theo thu no nhin thay luc bat dau. Buoc nay
        # KHONG don qua khu (doi ten tep test cua phien khac la dung vao viec dang
        # do cua ho) — no chan tuong lai.
        Step("trung so test", [sys.executable, "tools/check_so_test.py"], ROOT),
        # 🔴 Banh coc: khong cho THEM cho bo qua ma khong khai bao.
        #
        #    `pytest -q` in mot chu `s` cho moi test bi bo qua, va gate chi giu
        #    4 dong cuoi cua dau ra — nen mot phep kiem NGUNG chay la mot su
        #    kien khong co trieu chung nao.
        #
        #    Do 25/08: cum VPS "503 passed, 2 skipped". Hai cai `s` do la hai
        #    phep kiem DUY NHAT chot rang kich ban dung lai cong vao con khop bo
        #    luat nftables that — va chung khong bao gio chay o dau, vi
        #    `secrets/` khong duoc commit.
        #
        # ⭐ Buoc nay KHONG ep chung chay (may khong co PostgreSQL/ffmpeg/R2 thi
        #    bo qua la dung). No in HET danh sach moi luot va bao do khi co cho
        #    MOI — bo qua tro thanh mot thu duoc khai bao, khong phai mot thu
        #    xay ra.
        Step("bo qua im lang", [sys.executable, "tools/check_bo_qua.py"], ROOT),
        # Ky tu dieu khien vo hinh trong tai lieu. `test_61` da quet dai nay tu
        # lau va van quet — buoc nay KHONG thay no, no bit hai lo khac:
        #   - pham vi: `test_61` dung `glob("*.md")` KHONG de quy, nen no phu 43
        #     tep o `docs/` cap tren cung va bo qua moi thu muc con. Buoc nay
        #     quet 623 tep van ban git dang theo doi — va no tim ra ngay mot BEL
        #     song tu 2026-08-20 trong `docs/nexus/`, lam duong dan trong tai
        #     lieu chi sai suot chin ngay;
        #   - thoi diem: `test_61` chay o pha test; buoc nay chay trong
        #     `--vong-lap` (~15 giay), tuc bat truoc khi thiet hai kip lan ra.
        Step("ky tu dieu khien", [sys.executable,
                                  "tools/check_ky_tu_dieu_khien.py"], ROOT),
        # H24: banh coc chong THEM chuoi chua boc _(). Con ~2.310 chuoi chua dich;
        # cam tuyet doi thi chan moi viec khac, nen chi cam TANG. Khong co buoc
        # nay thi cong dich muc dan — dung nhu "Marketplace"/"My Apps" tieng Anh
        # lot vao giua trang tieng Viet ma khong ai biet tu luc nao.
        Step("chuoi chua dich", [sys.executable, "tools/check_i18n.py"], ROOT),
        # 🔴 …va banh coc thu HAI, cho buoc SAU do. `check_i18n.py` canh chuoi
        #    chua duoc boc `_()`. Buoc nay canh chuoi DA vao `messages.po` roi
        #    ma `msgstr` van rong — tuc trang tieng Anh in ra tieng Viet.
        #
        #    Do 25/08: 203 muc `msgstr` rong + 76 muc `#, fuzzy` tren 2.352.
        #    Fuzzy dem NHU RONG: `msgfmt` bo qua moi muc fuzzy, nen mot ban dich
        #    fuzzy khong bao gio toi mat nguoi dung — no chi TRONG NHU da xong
        #    khi doc tep `.po`.
        Step("dich thieu ban EN",
             [sys.executable, "tools/check_dich_thieu.py"], ROOT,
             nhom="sau_test"),
        # EXT-17: hợp đồng công khai của /api/v1 so với bản chuẩn đã đóng băng.
        # Không có bước này thì một thay đổi phá vỡ tương thích lên tàu được vì
        # không ai diff một thứ mà không ai gom lại. Cố ý phá thì chạy
        # `--accept`, và lần ghi lại đó hiện trong diff cho người review thấy.
        Step("hop dong API", [sys.executable, "tools/check_api_compat.py"],
             ROOT, nhom="sau_test"),
        # 🔴 ANH CHUP HOP DONG VANG — do 25/08, va no da do TREN NHANH mot ngay
        #    ma khong ai thay.
        #
        #    Tran `max_tokens` cua `text.chat` nang 16.384 -> 32.768 hom 24/08.
        #    Ma doi, CHANGELOG doi, con `tests/golden/public_api_catalog_v1.json`
        #    thi khong — nen `test_181` va `test_187` do suot tu do.
        #
        # ⛔ VI SAO KHONG AI THAY: hai test do chi chay trong pytest, ma
        #    `gate --quick` KHONG chay pytest. Ca hai phien deu chay `--quick`
        #    truoc khi deploy va deu thay PASS.
        #
        # ⭐ Phep kiem nay re (dung catalog roi so JSON), nen no chay ca o
        #    `--quick`. Mot thay doi hop dong co y thi chay
        #    `python tools\\sinh_golden_api.py --ghi` — va lan ghi do hien ra
        #    trong diff cho nguoi review thay, dung nhu buoc tren.
        Step("anh chup hop dong", [sys.executable, "tools/sinh_golden_api.py"],
             ROOT),
        # 🔴 TÀI LIỆU SINH RA CŨNG TRÔI ĐƯỢC — và nó đã trôi, ngay trong HEAD.
        #
        #    `DEVELOPER_GUIDE.md` là tài liệu ta **xuất bản cho khách**. Commit
        #    `c246858` nâng `MAX_TOKENS_TRAN` 16.384 → 32.768 nhưng không sinh
        #    lại tài liệu, nên từ đó **mã nói 32.768 còn tài liệu nói 16.384**.
        #
        # ⛔ VÀ NÓ SAI VỀ PHÍA KHÔNG AI BÁO LỖI: tài liệu báo trần THẤP hơn thực
        #    tế. Khách đọc, tự kẹp ở 16.384, và không bao giờ dùng hết thứ họ đã
        #    trả tiền để được dùng. Không có triệu chứng, không có ai khiếu nại.
        #
        # ⭐ `--check` đã tồn tại và đã trả mã 1 khi lệch — nhưng nó chỉ chạy
        #    trong pytest, thứ `gate --quick` bỏ qua. Cùng lỗ với ảnh chụp hợp
        #    đồng: phép kiểm CÓ, mà không ai gặp nó đúng lúc cần.
        Step("tai lieu sinh ra", [sys.executable, "tools/build_public_api_docs.py",
                                  "--check"], ROOT),
        # EXT-18: SDK thiếu một route không bao giờ báo lỗi — nó chỉ để người
        # dùng tự viết lấy, rồi họ viết sai retry hoặc quên Idempotency-Key.
        Step("SDK khop hop dong",
             [sys.executable, "tools/check_sdk_contract.py"], ROOT,
             nhom="sau_test"),
        # …và collection Postman phải được SINH lại, không sửa tay: một bản sao
        # thứ hai của hợp đồng luôn là bản trôi dạt.
        # Ban sao `ltt.css` canh GUI khong duoc troi khoi ban goc: mot ban
        # sao tinh khong co gi nhac no cap nhat thi no se khong cap nhat,
        # va cong cu se trong GAN GIONG nen tang - kieu sai kho chiu nhat.
        Step("tai san GUI", [sys.executable, "tools/dong_goi_gui.py", "--kiem"],
             ROOT),
        Step("postman", [sys.executable, "tools/build_postman.py", "--check"],
             ROOT, nhom="sau_test"),
    ]
    if not quick:
        # H36.9: bo bat bien DA TIEN TRINH. Ba loi P0 cua ban audit 2026-08-15
        # lot qua hon ba nghin test vi chua tung co gi chay hai tien trinh
        # worker cung luc — va phep do bit lo hong do lai chi chay khi co
        # PostgreSQL, nen `pytest` chi in mot chu `s`. Mot chu `s` giua ba
        # nghin dau cham la vo hinh. Buoc rieng nay khong lam gate do khi may
        # khong co PostgreSQL, nhung viec bo qua thi khong bao gio con lang le.
        # `test_214` dung HAI tien trinh worker — do la ca diem cua no. Khai 2,
        # khong khai 1: bo dem loi chi dung khi moi buoc noi that ve cai no lay.
        # 🔴 `postgres_test` THEM 06/09/2026. `check_multiproc.py` goi
        #    `drop_all()` (xem docstring dong 19 cua no) tren CSDL test DUNG
        #    CHUNG, va buoc nay truoc do KHONG khai tai nguyen nao. Hai luot gate
        #    o hai cay khac nhau => mot ben xoa schema giua luc ben kia dang ghi.
        #    Trieu chung do that dem 05-06/09, hai phien, hai kieu:
        #        relation "api_metric_samples" does not exist
        #        assert 0 == 9   (9 job bien mat khoi bang)
        steps.append(Step("bat bien da tien trinh",
                          [sys.executable, "tools/check_multiproc.py"], ROOT,
                          nhom="nang", tai_nguyen=("postgres_test",),
                          so_loi=2, giay_toi_thieu=3.0))
        # 🔴 THEM 08/09/2026. Do duoc hom do: KHONG phep kiem nao trong kho thi
        #    hanh `alembic upgrade` tren PostgreSQL.
        #
        #        moi tep goi `command.upgrade`: test_103 · test_451 · test_45
        #                                       · test_505 · test_616
        #        -> postgres = 0 o TAT CA (chung deu tro `sqlite:///`)
        #
        #    Va buoc `bat bien da tien trinh` ngay tren KHONG lap duoc lo do: no
        #    dung luoc do bang `drop_all()`/metadata — tuc di duong SQLAlchemy
        #    MODEL, khong di duong MIGRATION. Hai duong khac nhau, va chi duong
        #    thu hai la duong production di.
        #
        # ⇒ He qua that: `BOOLEAN DEFAULT 1` (PostgreSQL tu choi, SQLite nhan)
        #   song sot qua BA commit, moi commit deu kem cau "thi hanh that tu
        #   base toi head" — cau ay dung, va no dung TREN SQLITE.
        steps.append(Step("migration tren postgres",
                          [sys.executable, "tools/do_migration_tren_postgres.py"],
                          ROOT, nhom="nang", tai_nguyen=("postgres_test",),
                          giay_toi_thieu=2.0))
        # ⭐ TRUC THU HAI, va no khac buoc tren chu khong trung.
        #
        # Buoc tren hoi: *migration* co chay tren PostgreSQL khong (DDL).
        # Buoc nay hoi:  *ma chay luc runtime* co chay tren PostgreSQL khong
        #                (DML) — voi du lieu THAT cua production.
        #
        # ⇒ He qua that, do 08/09/2026: `M-1` danh dau ban da di tru bang
        #   `"m1:" + id` = 39 ky tu vao cot `String(36)`. SQLite khong cuong
        #   che do dai VARCHAR nen bo test xanh, va ca mot lan dien tap tren
        #   BAN SAO SQLITE CUA CHINH DU LIEU PRODUCTION cung xanh. PostgreSQL:
        #   `StringDataRightTruncation`. Buoc tren khong the thay — no khong
        #   chay mot dong ma san pham nao.
        # ⚠️ SAN 0.8s, KHONG phai 2.0s. Ban dau toi chep `2.0` tu buoc tren ma
        #    khong do — va gate do vi chinh cai san do: buoc chay THAT, in
        #    `RESULT: PASS`, roi bi danh truot vi xong trong 1.63s.
        #
        # Do ba luot tren may ranh: 1466 / 1400 / 1376 ms. Buoc nay nhanh hon
        # buoc migration vi no chi nap 10 hang, khong chay ca chuoi alembic.
        #
        # ⭐ San chi can phan biet CHAY THAT voi TRA 0 AM THAM — duong `BO QUA`
        #    da duoc `_tu_khai_bo_qua` mien roi (`step.ok and not step.bo_qua`).
        #    Duong tra 0 am tham la doc secrets roi thoat: ~0.2s. Nen 0.8s nam
        #    giua hai cum voi bien ca hai phia.
        steps.append(Step("M-1 tren postgres",
                          [sys.executable, "tools/dien_tap_m1_tren_postgres.py"],
                          ROOT, nhom="nang", tai_nguyen=("postgres_test",),
                          giay_toi_thieu=0.8))
    npm = _npm()
    for name in FRONTENDS:
        folder = ROOT / "frontend" / name
        if not (folder / "package.json").exists():
            continue
        # 🔴 CAY RIENG KHONG CO `node_modules`, va do khong phai mot loi.
        #
        #    `node_modules/` khong nam trong git, nen moi worktree moi tao ra
        #    deu thieu no. Do 2026-09-02: luot gate day du dau tien chay trong
        #    mot worktree do **ba** buoc frontend voi `'vitest' is not
        #    recognized` — trong khi khong co gi hong ca.
        #
        # ⛔ De no la FAIL thi mot cay rieng **khong bao gio** xanh duoc, va nhu
        #    the thi ca quy trinh "moi phien mot cay" tu no vo nghia: nguoi ta
        #    se hoc cach bo qua ba dong do, roi bo qua dong do thu tu.
        #
        # ⭐ Nhung cung KHONG duoc lang le cho qua. Day dung la truong hop
        #    `Step.bo_qua` sinh ra de xu ly: chay xong, tra 0, va TU KHAI rang
        #    no khong lam duoc viec — nen no hien o dong RESULT.
        if npm is not None and not (folder / "node_modules").is_dir():
            steps.append(Step(
                f"frontend {name}",
                [sys.executable, "-c",
                 f"print('{DAU_BO_QUA}: {name} chua cai node_modules "
                 f"(cay rieng?). Chay `npm ci` trong frontend/{name} "
                 f"neu can chung minh phan frontend.')"],
                folder, nhom="frontend"))
            continue
        if npm is None:
            steps.append(Step(f"frontend {name}", ["npm-khong-tim-thay"], folder,
                              nhom="frontend"))
            continue
        # ⛔ `--maxWorkers` la BAT BUOC, khong phai toi uu.
        #
        #    Vitest 4 tu dat `min(12, numCpus - 1)`. Tren may 20 loi la 12
        #    worker — cho MOI thu muc, va ba thu muc chay dong thoi voi 20
        #    worker pytest. Do la 56 luong tren 20 loi, tren mot may dang phuc
        #    vu khach that.
        steps.append(Step(f"frontend {name}",
                          [npm, "test", "--", "--run",
                           f"--maxWorkers={loi_moi_viec}"],
                          folder, nhom="frontend", so_loi=loi_moi_viec))
    if not quick:
        # Browser/audit artifacts live under tmp/ and test-results/ by contract;
        # they may contain copied ``tests`` folders and must never be collected
        # as a second copy of the repository test suite.
        # 🔴 DI QUA `test_nhanh.py`, KHONG goi `pytest` truc tiep nua.
        #
        #    Truoc 2026-08-26 buoc nay la mot lenh `pytest` MOT LUONG, mat
        #    **2 gio**. Do khong phai su bat tien — no doi cach nguoi ta lam
        #    viec: `pytest` thoi la mot vong lap va thanh mot su kien.
        #
        # ⛔ He qua da do duoc: hang muc H40 dong ma CHUA luot `pytest` day du
        #    nao chay xong, va luot day du dau tien sau do tim ra **36 loi** —
        #    gom mot phep kiem CHUA BAO GIO XANH tren may nay.
        #
        # ⭐ `test_nhanh.py` cho CUNG TAP pass/fail trong 4 phut, chung minh
        #    bang so chu khong bang tin tuong:
        #        noi tiep   4096 passed, 26 skipped, 1.534 giay
        #        song song  4096 passed, 26 skipped,   234 giay
        #
        #    Hai pha: song song `--dist loadfile` cho phan lon, roi noi tiep cho
        #    ba tep ghi vao cay kho (`TEP_NOI_TIEP`). Xem AGENTS.md muc 4b.
        # ⛔ `-n` tuong minh thay cho `auto`. `auto` = MOI loi cua may, va no
        #    khong biet gi ve ba vitest dang chay canh no, cung khong biet gi ve
        #    bon dich vu production tren cung may.
        #
        # ⛔ NOI TIEP KHONG PHAI `-n 1`. Hai thu khac nhau that su:
        #      `-n 1`      van qua xdist — mot worker, nhung la mot TIEN TRINH
        #                  CON, va no van chia tep theo `--dist loadfile`.
        #      `--noi-tiep` khong co xdist gi ca: dung tien trinh pytest do,
        #                  dung thu tu thu thap goc, khong co pha 2.
        #    Khac biet do la ca cai gia tri cua che do nay: no la phep do duy
        #    nhat KHONG di qua lop ma ta dang nghi ngo.
        if noi_tiep:
            steps.append(Step("bo test (noi tiep)",
                              [sys.executable, "tools/test_nhanh.py",
                               "--noi-tiep"], ROOT,
                              nhom="nang",
                              tai_nguyen=("cpu_nhieu", "postgres_test"),
                              so_loi=1, giay_toi_thieu=3.0))
        else:
            steps.append(Step("bo test (song song)",
                              [sys.executable, "tools/test_nhanh.py",
                               "-n", str(loi_bo_test)], ROOT,
                              nhom="nang",
                              tai_nguyen=("cpu_nhieu", "postgres_test"),
                              so_loi=loi_bo_test, giay_toi_thieu=3.0))
    return steps


def _steps_pham_vi(tep_test: list[str]) -> list[Step]:
    """Bo test THU HEP: chi nhung tep `thanh_phan.py` chi ra.

    ⛔ Tra ve RONG khi khong co tep nao — va nguoi goi phai coi do la mot loi,
       khong phai "khong co gi de chay nen PASS". Mot pham vi khong test nao la
       mot pham vi chua ai bao ve, va no phai NOI RA thay vi in mot dong xanh.
    """
    if not tep_test:
        return []
    return [Step("bo test (pham vi)",
                 [sys.executable, "tools/test_nhanh.py", *sorted(tep_test)],
                 ROOT, nhom="nang",
                 tai_nguyen=("cpu_nhieu", "postgres_test"), giay_toi_thieu=3.0)]


#: HO SO — moi ho so mot HOP DONG viet ra thanh chu.
#:
#: 🔴 Vi sao phai viet hop dong chu khong chi dat ten. Truoc do gate co hai che
#:    do (`--quick`, `--vong-lap`) va ca hai deu phai TU NHAC o dong RESULT rang
#:    chung khong phai bang chung — vi neu khong, hai phien se doc cung mot dong
#:    "PASS" theo hai nghia khac nhau. Do da xay ra that (xem `Step.bo_qua`).
#:
#: ⇒ Them ho so ma khong them hop dong la nhan doi dung cai loi do. Moi muc
#:   duoi day phai tra loi: no CHUNG MINH duoc gi, va no KHONG chung minh gi.
HO_SO: dict[str, dict] = {
    "nhanh": {
        "mo_ta": "bo hai buoc nang (~40s) — chinh la co `--quick`",
        "chung_minh": "moi phep kiem TINH deu xanh",
        "khong_chung_minh": "KHONG phai bang chung. Moi loi THAT ngay 25/08 "
                            "deu nam o dung buoc `pytest` ma che do nay bo qua.",
        "xep_hang": False,
    },
    "vong-lap": {
        "mo_ta": "chan doan last-failed (~20s; khong phai cadence mac dinh)",
        "chung_minh": "khong co loi tinh moi, va nhung test vua do da xanh lai",
        "khong_chung_minh": "KHONG phai bang chung. `--lf` chi chay lai test da "
                            "do; mot test dang xanh ma thay doi nay lam hong "
                            "thi no khong he chay.",
        "xep_hang": False,
    },
    "pham-vi": {
        "mo_ta": "mot thanh phan + nguoi tieu thu cua no",
        "chung_minh": "moi test CHAM TOI cac thanh phan da chon deu xanh",
        "khong_chung_minh": "KHONG noi gi ve phan con lai cua kho. Chi dung khi "
                            "thay doi nam gon trong pham vi — `--doi` tu kiem "
                            "dieu do, con `--pham-vi` thi TIN NGUOI GOI.",
        "xep_hang": True,
    },
    "doi": {
        "mo_ta": "suy pham vi TU cay hien tai",
        "chung_minh": "moi test cham toi phan da doi deu xanh",
        "khong_chung_minh": "KHONG phai bang chung phat hanh. Va no TU HA CAP "
                            "xuong day du khi khong chac (cham tep dung chung, "
                            "hoac mot duong dan khong thanh phan nao so huu).",
        "xep_hang": True,
    },
    "day-du": {
        "mo_ta": "toan kho — mac dinh, giu nguyen hanh vi cu",
        "chung_minh": "toan bo cong chat luong tren cay nay",
        "khong_chung_minh": "khong noi gi ve viec deploy hay ve production",
        "xep_hang": True,
    },
    "noi-tiep": {
        "mo_ta": "day du, MOT buoc mot luc, MOT tien trinh pytest (~25-30 phut)",
        "chung_minh": "toan bo cong chat luong, VA rang ket qua do khong phu "
                      "thuoc vao so worker hay vao tai cua may luc do",
        "khong_chung_minh": "khong noi gi ve deploy hay production. Va no KHONG "
                            "chung minh che do song song sai — mot lan noi tiep "
                            "xanh trong khi song song do la bang chung ve MOT "
                            "loi CACH LY (hoac mot may qua tai), chua chi ra "
                            "loi nam o dau.",
        "xep_hang": True,
    },
    "phat-hanh": {
        "mo_ta": "day du + cai/cap nhat/rollback + quet bi mat",
        "chung_minh": "day du, cong them duong cai dat va rollback",
        "khong_chung_minh": "van khong thay the mot lan nghiem thu that tren may chu",
        "xep_hang": True,
    },
}

#: Buoc nao KHONG lam duoc viec cua no thi mo dau mot dong bang chuoi nay.
#: Quy uoc, khong phai ma thoat — vi ma thoat 0 o cac buoc do la co chu y.
DAU_BO_QUA = "BO QUA"
NL_GATE = chr(10)


def _tu_khai_bo_qua(output: str) -> bool:
    """Buoc co tu khai rang no khong lam duoc viec khong.

    ⛔ Chi nhan o DAU DONG. Mot buoc in "khong BO QUA gi ca" giua cau khong
       phai mot buoc bo qua, va bat theo `in` se bien moi ban bao cao noi ve
       viec bo qua thanh mot lan bo qua.
    """
    return any(d.lstrip().startswith(DAU_BO_QUA) for d in output.splitlines())


#: Chay tien trinh con o uu tien THAP HON binh thuong.
#:
#: 🔴 Day la lop bao ve THU HAI, va no can vi lop thu nhat (ngan sach loi) la
#:    mot phep TINH — con phep tinh thi co the sai. Uu tien thi khong: du gate
#:    co tinh nham bao nhieu, he dieu hanh van cho `LTTStudioWeb` chay truoc.
#:
#: ⭐ Va no gan nhu mien phi: tren mot may RANH, tien trinh uu tien thap van
#:    duoc dung 100% CPU. No chi nhuong khi co ai do CAN — tuc dung luc ta muon
#:    no nhuong.
#:
#: ⚠️ Chi Windows. `BELOW_NORMAL_PRIORITY_CLASS = 0x00004000`.
UU_TIEN_THAP = 0x00004000 if os.name == "nt" else 0


def _run(step: Step) -> None:
    started = time.monotonic()
    them = {"creationflags": UU_TIEN_THAP} if UU_TIEN_THAP else {}
    try:
        done = subprocess.run(step.argv, cwd=step.cwd, capture_output=True,
                              text=True, encoding="utf-8", errors="replace",
                              **them)
        step.ok = done.returncode == 0
        output = (done.stdout or "") + (done.stderr or "")
    except OSError as exc:
        step.ok = False
        output = f"khong chay duoc: {exc}"
    step.seconds = time.monotonic() - started
    step.bo_qua = bool(step.ok) and _tu_khai_bo_qua(output)
    if (step.ok and not step.bo_qua and step.giay_toi_thieu > 0
            and step.seconds < step.giay_toi_thieu):
        step.ok = False
        output += (f"{NL_GATE}[san thoi gian] buoc `{step.name}` xong trong "
                   f"{step.seconds:.2f}s, duoi san {step.giay_toi_thieu:.1f}s.{NL_GATE}"
                   f"Mot buoc nang xong trong tich tac la mot buoc KHONG CHAY."
                   f" Neu no co y khong lam gi thi phai TU KHAI bang dong"
                   f" bat dau bang `{DAU_BO_QUA}`.")
    lines = [line for line in output.splitlines() if line.strip()]
    # 🔴 GIU 40 DONG, KHONG PHAI 4 — day la mot sua loi QUY TRINH, khong phai
    #    mot con so tuy chinh.
    #
    #    Ngay 26/08 toi dung gate lam CONG CU PHAT HIEN: chay 2 gio, doc 4 dong
    #    cuoi, thay 3 cai ten trong so 36 loi, sua 3 cai do, roi chay lai 2 gio.
    #    Nam luot nhu vay ≈ 10 gio — de lay mot thu ma MOT luot da cho het neu
    #    dau ra khong bi cat.
    #
    # ⭐ Bon dong du cho mot buoc tinh (chung in mot dong ket luan). Voi bo test,
    #    danh sach FAILED moi la thu can doc, va no dai hon 4 dong.
    step.tail = "\n".join(lines[-40:])

    # 🔴 VA 40 DONG VAN KHONG DU KHI BO TEST DO. Do 06/09/2026: mot phep kiem
    #    do trong 6.616 phep kiem; `short test summary` cho DUNG mot dong —
    #    TEN phep kiem — con traceback da troi qua tu lau. Toi biet CAI GI do
    #    ma khong biet VI SAO, va phai chay lai ca luot 11 phut de xem.
    #
    # ⛔ Do khong phai chuyen tang mot con so. Bat ky tran nao cung se bi vuot
    #    boi mot luot du dai. Thu dung la: DO thi giu TRON dau ra ra tep.
    #
    # ⭐ Chi ghi khi DO, nen luot xanh khong de lai gi. Va in duong dan ra ngay
    #    dong ket luan, vi mot tep khong ai biet la mot tep khong ai doc.
    if not step.ok:
        try:
            thu_muc = ROOT / "test-results" / "gates"
            thu_muc.mkdir(parents=True, exist_ok=True)
            ten = "".join(c if c.isalnum() else "-" for c in step.name).strip("-")
            tep = thu_muc / f"loi-{os.getpid()}-{ten}.log"
            tep.write_text(output, encoding="utf-8", errors="replace")
            step.tep_loi = str(tep.relative_to(ROOT)).replace("\\", "/")
        except OSError:
            # ⛔ HEP: mot loi ghi tep KHONG duoc bien mot buoc do thanh mot
            #    ngoai le khac lam mat luon phan quyet.
            step.tep_loi = ""


def _da_doi_so_voi_HEAD() -> set[str] | None:
    """Đường dẫn đã đổi so với HEAD, kể cả chưa commit. `None` = không biết.

    ⚠️ `None` là **fail-open**: không có git, hay git trả lỗi, thì người gọi phải
       chạy TẤT CẢ. Một danh sách rỗng vì đọc hỏng trông y hệt một danh sách
       rỗng vì không đổi gì — và một trong hai nghĩa đó dẫn tới bỏ qua nhầm.
    """
    try:
        ra = subprocess.run(["git", "status", "--porcelain", "-uall"],
                            cwd=ROOT, capture_output=True, text=True, timeout=30)
        if ra.returncode != 0:
            return None
        duong = {d[3:].strip().strip('"') for d in ra.stdout.splitlines() if d[3:].strip()}
        ra2 = subprocess.run(["git", "diff", "--name-only", "HEAD"],
                             cwd=ROOT, capture_output=True, text=True, timeout=30)
        if ra2.returncode == 0:
            duong |= {d.strip() for d in ra2.stdout.splitlines() if d.strip()}
        return duong
    except (OSError, subprocess.SubprocessError):
        return None


def _rut_gon_vong_lap(steps: list[Step]) -> list[Step]:
    """Chế độ `--vong-lap`: chẩn đoán bằng cache last-failed.

    ## Vì sao chế độ này phải tồn tại

    Ngày 27/08 tôi chạy gate đầy đủ **sáu lần** để chẩn đoán, mỗi lần ~5 phút,
    và mỗi lần đỏ vì một thứ khác nhau: baseline của phiên kia · một emoji trong
    stdout của một công cụ · hồ sơ hệ thống stale · một phép kiểm lệch thứ tự.
    Bốn trong sáu lượt đó đáng lẽ là một lệnh 0,5 giây.

    🔑 Gate là công cụ ra **phán quyết**, không phải công cụ **chẩn đoán**. Dùng
       nó để dò là trả giá 5 phút cho một câu trả lời mà một bước con đã có.

    ## Nó bỏ gì, và vì sao vẫn giữ được ý nghĩa

    Giữ **toàn bộ** nhóm tĩnh — chúng chỉ tốn 7 giây khi chạy song song, và
    chính chúng là thứ bắt được bốn trong sáu lỗi hôm đó.
    Bỏ `bo test` đầy đủ, thay bằng `test_nhanh --lf`.
    Bỏ frontend **trừ khi** có tệp trong `frontend/` đổi — kiểu "affected" của
    Nx/Turborepo, nhưng chỉ áp cho đúng chỗ mà quan hệ vào-ra là hiển nhiên.

    ⛔ CHẾ ĐỘ NÀY KHÔNG PHẢI BẰNG CHỨNG, và dòng kết quả nói thẳng điều đó —
       cùng lý do `--quick` phải nói. `--lf` chỉ chạy lại những test **đã đỏ lần
       trước**; một test đang xanh mà thay đổi này làm hỏng thì nó **không hề
       chạy**. Đó là giới hạn của `--lf`, không phải một chi tiết cài đặt.
    """
    doi = _da_doi_so_voi_HEAD()
    ra: list[Step] = []
    for s in steps:
        # Tự bỏ hai bước nặng, thay vì trông chờ người gọi đã truyền
        # `_steps(quick=True)`. Một hàm "rút gọn" mà kết quả phụ thuộc việc
        # đầu vào đã được rút gọn sẵn hay chưa là một hàm rất dễ gọi sai.
        if s.name in BO_QUA_KHI_QUICK:
            continue
        if s.nhom == "frontend":
            if doi is None or any(d.startswith("frontend/") for d in doi):
                ra.append(s)
            continue
        ra.append(s)
    # ⚠️ `--lf-rong-thi-khong-chay` la bat buoc o day. `--lf` mot minh chay TAT
    #    CA khi lan truoc khong co gi do — do 27/08: che do nay dat ra de xong
    #    trong ~20 giay va mat 4 phut 26 vi dung ly do do.
    # ⛔ Buoc nay truoc 06/09 khai **KHONG TAI NGUYEN NAO** — ke ca `cpu_nhieu`.
    #    Va no khong he nhe: `--lf` chay TOAN BO bo test khi cache lastfailed
    #    rong hoac toan id chet (do that 06/09: 393 giay). Tuc `--vong-lap` la
    #    mot buoc nang **doi lot mot buoc nhanh**, va no vo hinh voi khoa.
    ra.append(Step("bo test --lf",
                   [sys.executable, "tools/test_nhanh.py", "--lf",
                    "--lf-rong-thi-khong-chay"], ROOT, nhom="nang",
                   tai_nguyen=("cpu_nhieu", "postgres_test"), giay_toi_thieu=3.0))
    return ra


def _chay_theo_lich(steps: list[Step], *, j: int, tuan_tu: bool) -> None:
    """Chạy các bước theo lịch, in mỗi bước khi nó **xong**.

    ## Vì sao không chạy tuần tự nữa

    Đo 2026-08-27 trên máy chủ (20 nhân): 16 bước tĩnh mất **28,3 giây** khi nối
    đuôi nhau, **7,1 giây** khi chạy 8 luồng. Mọi bước đều là một tiến trình con
    ở chế độ **chỉ đọc** (`--check` / `--kiem`), nên không bước nào chạm cây —
    đó là điều kiện làm việc này an toàn, và nó đã được kiểm chứ không giả định.

    ## Lịch: việc DÀI chạy trước

    `bo test` chiếm ~85% tổng thời gian (255s / ~300s). Khởi động nó trước rồi
    thả mọi thứ khác chạy trong bóng của nó thì tổng thời gian bằng đúng thời
    gian của nó. Nhóm `tinh` (7s) và `frontend` (~20s) biến mất khỏi đồng hồ.

    ⚠️ Riêng `bo test` pha 1 đã lấy `-n auto` = mọi nhân. Nên nhóm `tinh` bị
       giới hạn `j` luồng: giành CPU với bộ test là làm chậm chính thứ đang
       quyết định tổng thời gian. Và pha 2 của nó chạy **nối tiếp trên 3 tệp**
       (~53s) — đó là cửa sổ mà 19 nhân rảnh, chỗ nhóm tĩnh nấp vào.

    ## Vì sao `cong` chạy một mình, trước

    `bien dich duoc` là cổng gác: một tệp không biên dịch được thì mọi phép đo
    phía sau đều vô nghĩa (các chốt khác **bỏ qua** tệp không parse được — chúng
    đếm xu hướng). Chạy nó song song với phần còn lại nghĩa là 20 bước kia vẫn
    tốn công cho một cây mà ta sắp biết là hỏng.
    """
    from concurrent.futures import ThreadPoolExecutor

    xong: list[Step] = []

    def chay_va_in(step: Step) -> None:
        _run(step)
        xong.append(step)
        dau = "ok  " if step.ok else "LOI "
        print(f"  [{dau}] {step.name:<28} {step.seconds:6.1f}s "
              f"({len(xong)}/{len(steps)})", flush=True)

    if tuan_tu:
        for step in steps:
            chay_va_in(step)
        return

    for step in [s for s in steps if s.nhom == "cong"]:
        chay_va_in(step)
    if any(s.nhom == "cong" and not s.ok for s in steps):
        # ⛔ KHONG bo qua phan con lai: nguyen tac "chay het roi moi bao" van
        #    giu. Chi la khong con ly do de song song hoa mot cay da hong.
        for step in [s for s in steps if s.nhom != "cong"]:
            chay_va_in(step)
        return

    nang = [s for s in steps if s.nhom == "nang"]
    nhe = [s for s in steps if s.nhom in ("tinh", "frontend")]
    sau = [s for s in steps if s.nhom == "sau_test"]

    # 🔴 NHAN VIEC THEO LOI, KHONG THEO TIEN TRINH — sua 2026-09-02 sau HAI lan
    #    may treo phai reset cung.
    #
    #    Ban cu: `max_workers = len(nang) + j` = 2 + 8 = 10 luong, va tac gia
    #    suy "10 tien trinh con la vua tren 20 loi". Phep suy do dung cho nhom
    #    `tinh` — moi buoc do that su la MOT tien trinh. No sai cho hai loai
    #    khac, va sai rat lon:
    #
    #      `bo test`     -> pytest `-n auto`                = 20 worker
    #      `frontend` x3 -> vitest `min(12, numCpus - 1)`   = 36 worker
    #
    #    ⇒ "10 tien trinh" thuc te la ~61 luong tren 20 loi, canh bon dich vu
    #      production. Ba lan qua tai.
    #
    # ⭐ Nen bo dem khong phai `max_workers` ma la NGAN SACH LOI: moi buoc khai
    #    `so_loi`, va lich chi nhan them viec khi con cho.
    #
    # ⚠️ Mot buoc lon hon ca ngan sach van duoc chay — MOT MINH. Tu choi chay
    #    thi cong chat luong thanh vo dung tren may nho, va do la mot cach hong
    #    te hon han cham.
    import threading

    ngan_sach = ngan_sach_loi()
    con_lai = ngan_sach
    khoa = threading.Condition()

    def chay_co_ngan_sach(step: Step) -> None:
        nonlocal con_lai
        can = min(step.so_loi, ngan_sach)
        with khoa:
            khoa.wait_for(lambda: con_lai >= can)
            con_lai -= can
        try:
            chay_va_in(step)
        finally:
            with khoa:
                con_lai += can
                khoa.notify_all()

    # Viec DAI nop truoc de moi thu khac nap vao bong cua no — giu nguyen y do
    # cua lich cu; chi doi bo dem.
    thu_tu = sorted(nang, key=lambda s: -s.so_loi) + nhe
    # ⚠️ HAI tran cung luc, va ca hai deu can:
    #      `j`         — bao nhieu BUOC duoc chay cung luc
    #      `ngan_sach` — bao nhieu LOI duoc dung cung luc
    #    Bo `j` di thi mot may co 40 buoc tinh se mo 40 luong chi de xep hang;
    #    bo `ngan_sach` di thi ta quay lai dung cho da lam treo may hai lan.
    with ThreadPoolExecutor(max_workers=min(len(thu_tu), max(1, j))) as ex:
        for f in [ex.submit(chay_co_ngan_sach, s) for s in thu_tu]:
            f.result()

    # ⛔ SAU khi `bo test` xong hẳn, KHÔNG song song với nó.
    #
    #    Bốn bước này đọc tệp mà bộ test ghi rồi khôi phục
    #    (`TEP_KHONG_DUOC_DOC_SONG_SONG`). Đọc chúng giữa lúc bị ghi cho
    #    `OSError: [Errno 22]` trên Windows, hoặc — tệ hơn vì im lặng — đọc
    #    trúng **bản đã bị tiêm** và báo một vi phạm hợp đồng không có thật.
    #
    # ⭐ Cái giá là thật và đã đo: bốn bước này (~11 giây cộng lại) trước đây
    #    nấp trong bóng của `bo test` nên **miễn phí**; nay chúng cộng thẳng vào
    #    tổng. Đổi ~11 giây lấy việc mọi lượt gate nói về **cùng một cây** là
    #    một đổi chác dễ — một dòng RESULT không tin được thì nhanh cũng vô ích.
    if sau:
        with ThreadPoolExecutor(max_workers=max(1, j)) as ex:
            for f in [ex.submit(chay_va_in, s) for s in sau]:
                f.result()


def _console_text(value: str, encoding: str | None = None) -> str:
    """Make captured UTF-8 diagnostics printable on legacy Windows consoles.

    PowerShell 5.1 commonly exposes CP1252. A failed test may contain Vietnamese
    or symbols; reporting that failure must not itself crash and hide the cause.
    """
    target = encoding or getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        return value.encode(target, errors="backslashreplace").decode(target)
    except LookupError:
        return value.encode("ascii", errors="backslashreplace").decode("ascii")


#: Tên các bước `--quick` KHÔNG chạy. In ra ở dòng kết quả — xem `main`.
BO_QUA_KHI_QUICK = ("bat bien da tien trinh", "bo test (song song)")


#: Thư mục nằm trong ảnh chụp "cây đứng yên".
#:
#: 🔴 TRƯỚC 03/09 DANH SÁCH NÀY THIẾU BA THỨ QUAN TRỌNG NHẤT VỚI HAI PHIÊN
#:    LÀM VIỆC SONG SONG: `llm_gateway/` (mã cổng máy B), `sdk/` (bộ cài chạy
#:    trên máy khách) và `frontend/`.
#:
#:    Một chương trình sửa 10 thư mục — đo thật 03/09 — có **năm** thư mục nằm
#:    ngoài ảnh chụp. Nghĩa là sửa mã cổng máy B ngay giữa một lượt gate thì
#:    `CAY DA DOI TRONG LUC CHAY` **không kêu**, và dòng `RESULT: PASS` nói về
#:    một cây đã không còn tồn tại.
#:
#: ⭐ Cùng họ với `banh-coc-chi-bao-ve-thu-no-nhin-thay`: chốt có, và nó chỉ
#:    canh phần nó được kể tên.
THU_MUC_CHUP = (
    "apps", "platform_core", "server", "tools", "tests", "alembic", "locale",
    # Mã chạy trên máy B và bộ cài chạy trên máy khách. Cả hai deploy đi xa
    # khỏi kho này, nên một lần sửa giữa lượt gate là một lần sai không ai thấy.
    "llm_gateway", "render_gateway", "sdk", "nexus_agent",
    # (`codex_sidecar` gỡ 09/09/2026 — AI CLEAN REBUILD V2 pha 07.)
    # Nguồn frontend. `node_modules` bị cắt ở `_BO_QUA_THU_MUC`.
    "frontend",
)

#: Thư mục **cắt ngay lúc duyệt**, không phải lọc sau.
#:
#: ⭐ VÀ ĐÓ LÀ TOÀN BỘ LÝ DO ẢNH CHỤP RỘNG HƠN MÀ LẠI NHANH HƠN. Bản `rglob`
#:    trước vẫn **đi xuống** `node_modules` (12.255 tệp) rồi mới bỏ; `os.walk`
#:    cắt `dirnames` tại chỗ nên nó không xuống. Đo 03/09 trên cây này:
#:
#:        rglob,   7 thu muc, loc sau   1.321 tep   0,143 s
#:        os.walk, 13 thu muc, cat nhanh 1.491 tep   0,047 s
#:
#: ⛔ VÀ KHÔNG CẮT `.vite`. Bốn tệp `server/static/*/.vite/manifest.json` là
#:    bundle production **đã commit** — chúng chính là thứ máy chủ phục vụ, nên
#:    mất chúng khỏi ảnh chụp là mất đúng thứ cần canh. Cắt `dist`/`coverage`
#:    cũng cùng rủi ro; chỉ cắt hai thứ chắc chắn vô nghĩa.
_BO_QUA_THU_MUC = frozenset({"__pycache__", "node_modules"})


def _anh_chup_cay() -> dict[str, tuple[int, int]]:
    """Ảnh chụp cây nguồn: đường dẫn → (kích thước, thời điểm sửa).

    Không băm nội dung — chỉ cần biết cây **có đổi hay không** trong lúc chạy,
    và băm nội dung toàn cây tốn thêm hàng chục giây cho đúng một câu hỏi
    có/không.

    ⭐ Trả về cả **bản đồ** chứ không chỉ một chuỗi băm, vì hai chuỗi băm khác
       nhau không nói được gì ngoài "khác nhau". Xem `_ke_cho_da_doi`.
    """
    ra: dict[str, tuple[int, int]] = {}
    for thu_muc in THU_MUC_CHUP:
        goc = ROOT / thu_muc
        if not goc.is_dir():
            continue
        for thu, con, tep in os.walk(goc):
            # Cắt tại chỗ: `os.walk` đọc lại `con` sau mỗi vòng, nên gán vào
            # `con[:]` là bảo nó **không đi xuống** những nhánh đó.
            con[:] = [d for d in con if d not in _BO_QUA_THU_MUC]
            for ten in tep:
                p = Path(thu) / ten
                try:
                    st = p.stat()
                except OSError:
                    continue
                ra[p.relative_to(ROOT).as_posix()] = (st.st_size, int(st.st_mtime))
    return ra


def _ke_cho_da_doi(truoc: dict[str, tuple[int, int]],
                   sau: dict[str, tuple[int, int]], *, toi_da: int = 12) -> None:
    """In ra CÁI GÌ đổi, không chỉ RẰNG có đổi.

    🔴 Vì sao đáng viết thêm hàm này: bản trước chỉ in hai chuỗi băm, và ngày
       27/08 nó bắn ở **mọi** lượt gate đầy đủ. Nguyên nhân hoá ra rất nhỏ — ba
       chỗ khôi phục trong `test_306` trả lại đúng từng byte nhưng quên
       `os.utime`, nên **kích thước y hệt, mtime khác**.

    ⛔ Một cảnh báo luôn bắn là một cảnh báo bị bỏ qua, và dòng này lại đúng là
       dòng quyết định lượt chạy có tính làm **bằng chứng** hay không. Nêu tên
       tệp biến 20 phút mò thành một cái liếc.

    ⭐ Phân biệt "chỉ mtime" với "nội dung đổi": cái đầu gần như luôn là một test
       khôi phục thiếu, cái sau là ai đó thật sự đang gõ vào cây.
    """
    doi = sorted(k for k in set(truoc) | set(sau) if truoc.get(k) != sau.get(k))
    chi_mtime = [k for k in doi
                 if k in truoc and k in sau and truoc[k][0] == sau[k][0]]
    for k in doi[:toi_da]:
        if k not in truoc:
            print(f"    + {k}")
        elif k not in sau:
            print(f"    - {k}")
        elif k in chi_mtime:
            print(f"    ~ {k}  (chi mtime, kich thuoc y het)")
        else:
            print(f"    M {k}  ({truoc[k][0]} -> {sau[k][0]} byte)")
    if len(doi) > toi_da:
        print(f"    ... va {len(doi) - toi_da} tep nua")
    if chi_mtime and len(chi_mtime) == len(doi):
        print("    => TAT CA chi doi mtime: gan nhu chac chan mot test ghi vao")
        print("       cay roi khoi phuc noi dung ma quen `os.utime`. Cay khong")
        # !! THUAN ASCII. Dau ra cua gate bi HUNG (`> gate.log`) thi stdout
        #    khong con la console, Python roi ve cp1252, va mot dau tieng Viet
        #    nem `UnicodeEncodeError` — lam vo dung cai dong dang giai thich
        #    rang khong co gi hong. Da dinh that o day ngay 27/08.
        print("       thuc su doi, nhung canh bao nay se keu mai toi khi sua.")


def _thu_hep(steps: list[Step], args, ho_so: str
             ) -> tuple[list[Step] | None, str]:
    """Thay `bo test` day du bang tap test cua pham vi. `None` = KHONG thu hep duoc.

    ⛔ Moi duong tra ve `None` o day la mot lan **tu ha cap xuong day du**, va
       do la thiet ke chu khong phai bo cuoc. Mot cong chat luong doan bua khi
       khong chac thi te hon han mot cong chay lau.
    """
    sys.path.insert(0, str(ROOT / "tools"))
    try:
        import thanh_phan as tp_mod
    except ImportError as e:
        return None, f"  [pham vi] khong nap duoc thanh_phan.py ({e})"

    tat_ca = tp_mod.cac_thanh_phan(ROOT)
    if ho_so == "pham-vi":
        chon = {t.strip() for t in args.pham_vi.split(",") if t.strip()}
        la = sorted(chon - set(tat_ca))
        if la:
            return None, f"  [pham vi] khong co thanh phan: {', '.join(la)}"
        _, tieu_thu = tp_mod.do_thi_phu_thuoc(ROOT, tat_ca)
        phan = set(chon)
        for t in chon:
            phan |= tieu_thu.get(t, set())
        nguon = f"chon tay: {', '.join(sorted(chon))}"
    else:
        try:
            duong = tp_mod.duong_da_doi(ROOT)
        except tp_mod.KhongBiet as e:
            return None, f"  [doi] khong doc duoc cay ({e}) -> chay DAY DU"
        if not duong:
            return None, "  [doi] cay khong doi gi -> chay DAY DU"
        phan = tp_mod.bi_anh_huong(duong, ROOT)
        if phan is None:
            return None, ("  [doi] cham tep DUNG CHUNG hoac duong khong ai"
                          " so huu -> chay DAY DU")
        nguon = f"{len(duong)} duong dan doi"

    tep_test = tp_mod.test_can_chay(phan, ROOT)
    # ⭐ Tep test DA DOI di thang vao danh sach, khong qua do thi thanh phan.
    #    `bi_anh_huong` co y khong nhan chu cho chung (khong ai import mot
    #    module test, nen khong co canh tieu thu de mo rong). Thieu dong nay
    #    thi mot thay doi CHI cham tep test se chay 0 test — te hon han so voi
    #    ha cap xuong day du.
    if ho_so == "doi":
        tep_test |= {t for t in tp_mod.tep_test_da_doi(duong)
                     if (ROOT / t).is_file()}
    if not tep_test:
        return None, (f"  [pham vi] {len(phan)} thanh phan nhung KHONG test nao"
                      " cham toi chung -> chay DAY DU")

    # Frontend chi chay khi `frontend` THAT SU nam trong pham vi. Cung phep loc
    # "affected" ma `_rut_gon_vong_lap` da dung — chi o day co so lieu tot hon:
    # do thi thanh phan, chu khong phai mot tien to duong dan.
    ra = [s for s in steps
          if s.name != "bo test (song song)"
          and (s.nhom != "frontend" or "frontend" in phan)]
    ra += _steps_pham_vi(sorted(tep_test))
    ghi_chu = (f"  [pham vi] {nguon}\n"
               f"  [pham vi] {len(phan)} thanh phan: "
               f"{', '.join(sorted(phan)[:6])}"
               f"{' ...' if len(phan) > 6 else ''}\n"
               f"  [pham vi] {len(tep_test)} tep test (thay cho bo day du)\n")
    return ra, ghi_chu


def main() -> int:
    parser = argparse.ArgumentParser(description="Chay toan bo cong chat luong.")
    parser.add_argument("--quick", action="store_true",
                        help="bo full pytest (dung cho vong lap ngan)")
    parser.add_argument("--vong-lap", action="store_true",
                        help="che do VONG LAP: tinh + `test_nhanh --lf`, ~20s")
    parser.add_argument("-j", type=int, default=8,
                        help="so luong buoc tinh chay cung luc (mac dinh 8)")
    parser.add_argument("--tuan-tu", action="store_true",
                        help="ep cac BUOC chay lan luot - de go loi chinh gate "
                             "(cong cu con van tu song song ben trong)")
    parser.add_argument("--noi-tiep", action="store_true",
                        help="ho so NOI TIEP: mot buoc mot luc VA mot tien "
                             "trinh pytest. Cham (~25-30 phut) nhung khong the "
                             "bi nhieu boi tai may hay boi cach ly worker")
    parser.add_argument("--phien", default="",
                        help="ten phien, hien cho phien khac dang doi")
    parser.add_argument("--khong-khoa", action="store_true",
                        help="chay ngay, khong xep hang cua so yen")
    parser.add_argument("--cho", type=float, default=15.0,
                        help="so phut chiu xep hang truoc khi chay khong khoa")
    parser.add_argument("--ho-so", default="", choices=["", *HO_SO],
                        help="ho so chay; xem HO_SO trong tep nay")
    parser.add_argument("--pham-vi", default="",
                        help="chi kiem mot thanh phan (vd core:tien, app:vps)")
    parser.add_argument("--doi", action="store_true",
                        help="suy pham vi tu cay hien tai")
    args = parser.parse_args()

    # ⛔ NOI RA thay vi im lang uu tien. `--noi-tiep` la mot HO_SO, va ho so thi
    #    loai tru nhau. Nhan ca hai roi lang le bo mot cai la dung cai bay ma
    #    `--pham-vi` sinh ra de tranh: mot phep do HEP ma nguoi doc tuong la
    #    day du — chi dao chieu.
    if args.noi_tiep and (args.pham_vi or args.doi or args.quick or args.vong_lap):
        parser.error("`--noi-tiep` la mot ho so DAY DU; no khong ket hop voi "
                     "--pham-vi/--doi/--quick/--vong-lap. Chon mot.")

    # 🔴 MOT BANG CHE DO DUY NHAT — `HO_SO`. Khong co "gate cu" va "gate moi".
    #
    #    Hai co cu (`--quick`, `--vong-lap`) la **ten goi tat** cua hai muc
    #    trong bang do, khong phai mot co che thu hai. Chung phai song vi
    #    `AGENTS.md` muc 4b va `CLAUDE.md` muc 4 day chung, va vi moi phien deu
    #    da quen tay — bo di la pha hop dong voi nguoi dung, doi lai khong duoc
    #    gi ngoai mot cai ten ngan hon.
    #
    # ⛔ Nhung moi che do PHAI co mot muc trong `HO_SO`. Truoc 02/09 `--quick`
    #    khong co, nen cau "no chung minh gi" nam rai trong ba chu thich o cuoi
    #    `main()` thay vi o mot cho tra cuu duoc. Do dung la mam cua chong cheo:
    #    khong phai hai tep, ma hai NOI dinh nghia cung mot thu.
    ho_so = (args.ho_so or ("vong-lap" if args.vong_lap else
                            "nhanh" if args.quick else
                            "noi-tiep" if args.noi_tiep else
                            "pham-vi" if args.pham_vi else
                            "doi" if args.doi else "day-du"))

    # Ho so `noi-tiep` KEO THEO `--tuan-tu`. Neu khong, `_chay_theo_lich` van
    # nop ba buoc frontend song song voi bo test — moi cai mot loi, nhung ba
    # tien trinh node canh mot tien trinh pytest van la bon thu tranh nhau, va
    # ca diem cua che do nay la khong con thu gi tranh nhau ca.
    noi_tiep = ho_so == "noi-tiep"
    tuan_tu = args.tuan_tu or noi_tiep

    steps = _steps(ho_so in ("nhanh", "vong-lap"), noi_tiep=noi_tiep)
    if ho_so == "vong-lap":
        steps = _rut_gon_vong_lap(steps)
    elif ho_so in ("pham-vi", "doi"):
        steps, ghi_chu_pham_vi = _thu_hep(steps, args, ho_so)
        if steps is None:
            # `_thu_hep` da giai thich vi sao khong thu hep duoc. Ha cap xuong
            # day du thay vi chay mot phep do hep ma khong biet no hep sai cho.
            ho_so = "day-du"
            steps = _steps(False)
        else:
            print(ghi_chu_pham_vi)
    # 🔴 XEP HANG, DUNG CHAY TRANH. Pha `bo test` lay `-n auto` = MOI loi,
    #    nen hai luot cung luc chi chia doi cung mot chiec banh: tong thoi gian
    #    gan y het chay lan luot, nhung tra them gap doi bo nho, gap doi thu muc
    #    tam, va gap doi kha nang do sai. Xem `tools/cua_so_yen.py`.
    #
    # ⛔ CHI luot DAY DU xep hang. `--quick` va `--vong-lap` thi khong, va
    #    khong phai vi tiec thoi gian: ca hai deu TU KHAI rang chung khong phai
    #    bang chung (xem dong RESULT cua chung), nen tranh chap lam nhieu phep do
    #    cua chung it quan trong hon han. Nguoc lai, chan mot vong lap ngan sau
    #    mot luot day du 6 phut la giet dung cai lam no huu dung.
    #
    # ⭐ DOI 2026-09-02: xep hang theo TAI NGUYEN, khong theo mot khoa duy nhat.
    #
    #    Cai cu xep hang "mot luot gate day du mot luc". Dung, nhung tho: hai
    #    luot `--pham-vi` cham hai app khac nhau van phai doi nhau du chung chi
    #    dung chung CPU chu khong dung chung gi khac. Nay moi buoc khai tai
    #    nguyen no can (`Step.tai_nguyen`) va gate xin dung nhung cai do.
    lenh = f"gate --ho-so {ho_so}"
    phien = (args.phien or os.environ.get("LTT_PHIEN")
             or f"{socket.gethostname()}:{os.getpid()}")

    # ⚠️ In ra ai KHAC dang ban, roi VAN CHAY. Khong chan.
    #
    # 🔴 Dem theo `cwd`, khong theo ten lenh — xem `tools/may_ban.py`. Ba cach
    #    dem theo van ban deu sai trong dem 05-06/09, va cai hong nguy nhat la
    #    no hong IM LANG THEO HUONG DE CHIU: mot bo dem bo sot hang xom se luon
    #    bao "toi chay mot minh" — tuc luon tra ve dung ket luan nguoi bam muon.
    #
    # ⛔ KHONG chan: mot cong chan nguoi ta la mot cong nguoi ta se tat, va luc
    #    do mat ca phan canh bao. `cua_so_yen` moi la thu xep hang; day chi la
    #    thu NOI RA dieu ma khoa khong thay (pytest go tay, worker execnet).
    try:
        from may_ban import dong_canh_bao
        _canh = dong_canh_bao()
        if _canh:
            print(_canh)
    except Exception as _e:  # noqa: BLE001
        print(f"  [may ban] khong dem duoc: {type(_e).__name__}")

    can: set[str] = set()
    for s in steps:
        can |= set(s.tai_nguyen)
    xep_hang = HO_SO[ho_so]["xep_hang"] and not args.khong_khoa and bool(can)
    with CuaSoYen(phien, lenh, bat=xep_hang,
                  cho_toi_da_s=args.cho * 60,
                  tai_nguyen=tuple(sorted(can)) or (MAC_DINH,)) as khoa:
        # 🔴 TINH LAI NGAN SACH O DAY, khong o `_steps()`.
        #
        #    `_steps()` chay o dong ~1036, TRUOC `CuaSoYen.__enter__`. Luc do ta
        #    chua biet co luot nao khac dang giu khoa, va `argv` cua buoc
        #    `bo test` da co dinh `-n <so>`.
        #
        # ⛔ Tinh lai CON SO thoi thi vo nghia: no tru dung va van chay dung so
        #    worker cu. Phai sua ca `argv`.
        if getattr(khoa, "chay_khong_khoa", False):
            print("  [cua so yen] dang CHEN - ngan sach se tu tut xuong theo "
                  "phan luot kia dang giu (B3, xem cua_so_yen.chay_khong_khoa)")
        _ap_ngan_sach_thuc(steps, phien)

        cay_dau = _anh_chup_cay()
        dong = f"Gate [{ho_so}]: {len(steps)} buoc"
        if tuan_tu:
            dong += ", MOT buoc mot luc" + (", MOT tien trinh" if noi_tiep else "")
        else:
            dong += (f", toi da {args.j} buoc cung luc"
                     f", ngan sach {ngan_sach_loi()}/{os.cpu_count()} loi")
        if can:
            dong += f", tai nguyen: {', '.join(sorted(can))}"
        print(dong)
        # 🔴 IN TAI MAY TRUOC KHI CHAY, o MOI ho so. Khoa cua so yen chi thay ai
        #    XIN khoa; no khong thay `pytest` go tay, khong thay deploy, khong
        #    thay bon dich vu production dang ban. Do 03/09: `cua_so_yen
        #    trang-thai` bao RANH trong khi CPU 65%.
        ban = loi_dang_ban()
        muc = ("RANH" if ban <= LOI_DE_DANH_CHO_MAY else
               "BAN" if ban <= ngan_sach_loi() else "QUA TAI")
        print(f"  [tai may] {ban:.1f}/{os.cpu_count()} loi dang ban -> {muc}")
        if muc == "QUA TAI":
            print("  [tai may] CANH BAO: co thu gi do NGOAI luot nay dang chiem "
                  "may. Ket qua co the bi nhieu; xem `--noi-tiep`.")
        print()
        t0_chay = time.time()
        _chay_theo_lich(steps, j=args.j, tuan_tu=tuan_tu)
        tong_s = time.time() - t0_chay

    print("\n" + "=" * 62)
    failed = [s for s in steps if not s.ok]
    for step in steps:
        mark = "BOQUA" if step.bo_qua else ("PASS" if step.ok else "FAIL")
        print(f"  [{mark}] {step.name:<28} {step.seconds:6.1f}s")
    if failed:
        print("\nChi tiet buoc that bai:")
        for step in failed:
            print(_console_text(f"\n--- {step.name} ---\n{step.tail}"))
            if getattr(step, "tep_loi", ""):
                print(_console_text(
                    f"    [dau ra DAY DU] {step.tep_loi}"))
    print("=" * 62)

    # 🔴 Một lượt gate đầy đủ mất 2,9–4,4 giờ. Trên kho này — hai phiên làm
    #    việc song song — cây đổi vài phút một lần. Ngày 25/08 có ba lượt đầy
    #    đủ, và lượt 4,4 giờ báo lỗi ở **một tệp đã đổi tên từ nhiều giờ
    #    trước**.
    #
    #    Kết quả ấy không sai lúc nó đo. Nó **trả lời về quá khứ** — và đọc nó
    #    như bằng chứng cho hiện tại là cách sinh ra ba vòng sửa những thứ
    #    không còn hỏng.
    cay_cuoi = _anh_chup_cay()
    cay_da_doi = cay_cuoi != cay_dau
    if cay_da_doi:
        print("CAY DA DOI TRONG LUC CHAY:")
        _ke_cho_da_doi(cay_dau, cay_cuoi)
        print("Ket qua duoi day noi ve cay luc BAT DAU, khong phai cay hien tai.")
        print("Chay lai tren mot cay dung yen neu can no lam BANG CHUNG.")
        print("=" * 62)

    ket = "PASS" if not failed else f"FAIL ({len(failed)}/{len(steps)})"
    # 🔴 BUOC BO QUA PHAI HIEN RA O DONG RESULT, khong chi trong bang tren.
    #
    #    Cung luat da ap cho `--quick`, `--vong-lap` va cay-doi: mot luot chay
    #    it hon thi dong ket qua cua no phai TRONG KHAC. Ngay 31/08 hai phien
    #    doc cung mot dong `PASS 25/25` theo hai cach trai nguoc, vi mot buoc
    #    da tu bo qua ma dong RESULT khong he noi.
    #
    # ⛔ Va no phai keu KE CA KHI TAT CA CON LAI DEU DAT — do dung la luc
    #    nguy hiem nhat: mot dong `PASS` tron ven che mot bat bien chua bao gio
    #    duoc chung minh.
    bo_qua = [s for s in steps if s.bo_qua]
    if bo_qua:
        ket += (f"  [{len(bo_qua)} BUOC TU BO QUA, KHONG PHAI BANG CHUNG: "
                f"{', '.join(s.name for s in bo_qua)}]")
    # 🔴 CUNG LUAT VOI `--quick` VA `--vong-lap`: mot luot chay it tin cay
    #    hon thi DONG KET QUA cua no phai trong khac. Truoc day cay-doi chi duoc
    #    noi trong mot doan van phia tren, con dong RESULT in y het mot luot
    #    sach - va dong RESULT la thu duy nhat duoc doc khi nguoi ta voi.
    if cay_da_doi:
        ket += "  [CAY DA DOI GIUA CHUNG - KHONG DUNG LAM BANG CHUNG]"
    if args.vong_lap:
        # 🔴 Cùng luật với `--quick`: một chế độ chạy ít hơn thì dòng kết quả
        #    của nó **phải trông khác**. Đọc "PASS" ở đây rồi báo xong là lặp
        #    lại đúng chuyện ngày 25/08, chỉ khác tên cờ.
        print(f"RESULT: {ket}  [--vong-lap: `--lf` thay cho bo test day du]")
        if not failed:
            print("        KHONG phai bang chung. `--lf` chi chay lai nhung test")
            print("        DA DO lan truoc; mot test dang xanh ma thay doi nay")
            print("        lam hong thi no khong he chay.")
            print("        Chay `python tools/gate.py` truoc khi bao xong.")
    elif args.quick:
        # 🔴 `--quick` ĐÚNG khi bỏ pytest — đó là mục đích nó khai. Lỗi nằm ở
        #    chỗ dòng kết quả in **y hệt** gate đầy đủ, nên người đọc hiểu nó
        #    là "mọi thứ xanh".
        #
        #    Cả hai phiên Claude làm việc trong kho này ngày 25/08 đều đọc như
        #    vậy — và **mọi lỗi thật hôm đó đều nằm ở đúng bước `pytest`** mà
        #    chế độ này bỏ: migration vỡ trên SQLite, liên kết điều khoản 404,
        #    trùng số tệp test.
        print(f"RESULT: {ket}  [--quick: KHONG chay {', '.join(BO_QUA_KHI_QUICK)}]")
        if not failed:
            print("        Chua phai bang chung day du - moi loi THAT ngay")
            print("        25/08 deu nam o buoc `pytest` ma che do nay bo qua.")
    elif ho_so in ("pham-vi", "doi"):
        # 🔴 CUNG LUAT LAN THU BA. Mot luot thu hep KHONG duoc in mot dong
        #    RESULT trong y het luot day du — do la ca ly do `--quick` va
        #    `--vong-lap` phai tu khai. Them ho so ma khong them cau tu khai la
        #    lam song lai chuyen ngay 25/08 duoi mot cai ten moi.
        print(f"RESULT: {ket}  [--ho-so {ho_so}: bo test THU HEP theo pham vi]")
        if not failed:
            print(f"        {HO_SO[ho_so]['khong_chung_minh']}")
            print("        Chay `python tools/gate.py` truoc khi bao xong.")
    else:
        print("RESULT:", ket)

    _ghi_ket_qua(ho_so, steps, ket, tong_s, khoa, cay_da_doi)
    return 0 if not failed else 1


def _ghi_ket_qua(ho_so: str, steps: list[Step], ket: str, tong_s: float,
                 khoa, cay_da_doi: bool) -> None:
    """Ghi danh tinh cua luot chay nay vao `test-results/gates/<id>.json`.

    ## Vi sao can

    Ba phien cung mot may, moi phien mot cay. Cau hoi "gate nao da chay tren
    ma nao" hien khong tra loi duoc bang gi ngoai cuon len doc lai dau ra —
    va dau ra thi mat khi dong cua so. Ngay 25/08 mot luot 4,4 gio bao loi o
    mot tep DA DOI TEN tu nhieu gio truoc, va khong ai truy nguoc duoc no do
    tren cay nao.

    ⛔ KHONG commit tep nay: `test-results/` da nam trong `.gitignore` (dong
       148). Day la du lieu cua mot lan chay, khong phai cua kho.

    ⚠️ KHONG ghi bien moi truong, dau ra buoc, hay bat cu gi co the chua bi
       mat. Chi ghi danh tinh va ket qua.
    """
    try:
        import json
        from datetime import datetime, timezone

        thu_muc = ROOT / "test-results" / "gates"
        thu_muc.mkdir(parents=True, exist_ok=True)
        luc = datetime.now(timezone.utc)
        sha = _git_gon(["git", "rev-parse", "HEAD"])
        ban_ghi = {
            "id": f"{luc.strftime('%Y%m%dT%H%M%SZ')}-{os.getpid()}",
            "luc": luc.isoformat(timespec="seconds"),
            "ho_so": ho_so,
            "ket_qua": ket,
            "tong_giay": round(tong_s, 1),
            "cho_khoa_giay": round(getattr(khoa, "da_cho_s", 0.0), 1),
            "tai_nguyen_da_giu": list(getattr(khoa, "da_giu_xong", None)
                                      or getattr(khoa, "da_giu", [])),
            "cay": str(ROOT),
            "la_cay_chinh": (ROOT / ".git").is_dir(),
            "sha": sha,
            "nhanh": _git_gon(["git", "rev-parse", "--abbrev-ref", "HEAD"]),
            "cay_da_doi_giua_chung": cay_da_doi,
            "buoc": [{"ten": s.name, "ket": ("BOQUA" if s.bo_qua else
                                             "PASS" if s.ok else "FAIL"),
                      "giay": round(s.seconds, 1)} for s in steps],
        }
        tep = thu_muc / f"{ban_ghi['id']}.json"
        tep.write_text(json.dumps(ban_ghi, ensure_ascii=False, indent=2),
                       encoding="utf-8", newline="\n")
        print(f"        [ket qua] {tep.relative_to(ROOT).as_posix()}")
    except OSError as e:
        # ⚠️ Khong ghi duoc thi NOI RA roi di tiep. Mot kho ket qua hong khong
        #    duoc phep lam do mot luot gate da chay xong — nhung im lang o day
        #    thi phien sau se tuong no da duoc ghi.
        print(f"        [ket qua] KHONG ghi duoc: {e}")


def _git_gon(argv: list[str]) -> str:
    try:
        r = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True,
                           timeout=15, encoding="utf-8", errors="replace")
        return r.stdout.strip() if r.returncode == 0 else "?"
    except (OSError, subprocess.SubprocessError):
        return "?"


if __name__ == "__main__":
    raise SystemExit(main())
