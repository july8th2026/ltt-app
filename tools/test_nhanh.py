"""test_nhanh.py — chạy toàn bộ pytest song song, KẾT QUẢ Y HỆT lượt nối tiếp.

    python tools/test_nhanh.py            # toan bo, song song
    python tools/test_nhanh.py --lf       # chi nhung test vua do
    python tools/test_nhanh.py -k credit  # loc theo ten
    python tools/test_nhanh.py -n 8       # chon so worker

## Mot dieu bat ngo ve `--lf`, de biet truoc thay vi doan giua chung

Cache `lastfailed` cua pytest **tich luy**: chay mot tap con thi cac muc cua tep
khong duoc thu thap van nam nguyen. Sau mot ngay chay nhieu luot le, no phinh ra
— do 27/08: **123 muc tu 36 tep**, phan lon da xanh tro lai tu lau.

=> Lan `--lf` DAU TIEN sau mot ngay nhu vay khong nhanh: no rut can cai cache do
   (do that: 3 phut 30). Cac lan sau moi la ~12 giay. Day la hanh vi DUNG, khong
   phai loi — nhung neu khong biet thi no trong y het "che do nhanh khong nhanh".

## ⭐ VÌ SAO CÓ TỆP NÀY

Bộ test đầy đủ mất **2 giờ**, và điều đó đổi cách người ta làm việc theo hướng
xấu: nó biến `pytest` từ một vòng lặp thành một sự kiện. Hệ quả đo được ngày
26/08 — hạng mục H40 đóng mà **chưa lượt `pytest` đầy đủ nào chạy xong**, và
lượt đầy đủ đầu tiên chạy sau đó tìm ra **36 lỗi**, trong đó một phép kiểm
**chưa bao giờ xanh** trên máy này.

Một bộ test quá chậm để chạy là một bộ test không ai chạy.

## Hai việc, và việc thứ nhất quan trọng hơn

**① Bỏ `fsync` cho SQLite tạm** *(nằm ở `platform_core/db.py`, không ở đây)*.
Đo được: `create_all` 44 bảng mất **2,16s** trên tệp thường và **0,05s** với
`synchronous=OFF` + `journal_mode=MEMORY` — **43 lần**. Vì gần như mọi test dựng
một CSDL mới, đó là hơn ba giờ trong tổng số hai giờ… nghe vô lý cho tới khi
nhớ rằng phần còn lại chạy song song được.

Đo thật trên một lát cắt 109 test: **193s → 42s**, chỉ nhờ hai dòng pragma.

**② Chạy song song** — việc của tệp này.

## ⛔ VÀ ĐÂY LÀ PHẦN KHÓ: SONG SONG KHÔNG ĐƯỢC ĐỔI KẾT QUẢ

Đã khảo sát tĩnh trước khi bật, không bật rồi chờ hỏng:

| Rủi ro | Thực tế đo được |
|---|---|
| Test ghi vào cây kho | **3 tệp** — xem `TEP_NOI_TIEP` |
| Cổng mạng cố định | **0** — mọi chỗ `bind` đều dùng cổng `0` (OS cấp) |
| Trạng thái toàn cục | `monkeypatch` là của từng tiến trình ⇒ xdist an toàn |
| CSDL dùng chung | mỗi test một SQLite trong `tmp_path` |

`--dist loadfile` gửi **trọn một tệp cho một worker**, nên thứ tự trong tệp giữ
nguyên — nhiều tệp ở đây dựa vào điều đó.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import pathlib
import socket
import subprocess
import sys
import time
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent

#: ⛔ BA TỆP PHẢI CHẠY NỐI TIẾP, MỘT TIẾN TRÌNH.
#:
#: Chúng ghi đè tệp **thật** trong kho rồi khôi phục trong `finally`:
#:
#:   test_209  `tools/*_baseline.json`
#:   test_210  `sdk/*` (TS + Python)
#:   test_306  `locale/en/LC_MESSAGES/messages.po` + `check_dich_thieu.moc`,
#:             và nó còn tạo một tệp test giả trong `tests/` rồi xoá
#:
#: Chạy song song với phần còn lại thì một worker có thể đọc trúng lúc tệp đang
#: bị sửa. Đó không phải giả thuyết: ngày 26/08 chính `test_306` đã làm hỏng
#: **hai** lượt gate (≈4 giờ) chỉ vì khôi phục không đúng từng byte và đúng cả
#: dấu thời gian.
#:
#: ⭐ Thêm một tệp cùng loại thì phải khai vào đây. `test_309` chốt danh sách
#:    này, nên quên khai sẽ làm gate đỏ chứ không lặng lẽ chạy song song.
TEP_NOI_TIEP = (
    "tests/test_209_versioning_status.py",
    "tests/test_210_sdk_ecosystem.py",
    "tests/test_306_banh_coc_bo_qua_va_dich.py",
)

BO_QUA = ("--ignore=tmp", "--ignore=test-results")


def _ep_utf8() -> None:
    """Cho phep tieng Viet trong nhan buoc ngay ca khi stdout bi HUNG.

    ⛔ Rieng viec nay KHONG thay duoc ASCII o `_chay`: `reconfigure` chi co tren
       `io.TextIOWrapper`, va stdout co the la thu khac duoi mot trinh hung khac.
       Hai lop, vi lop nay co the vang mat ma khong bao gi.
    """
    for luong in (sys.stdout, sys.stderr):
        try:
            luong.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass


def _con_id_song(cac_id: set[str]) -> tuple[int, int]:
    """`(so id con phan giai duoc, tong)`. Doc AST, khong nap module.

    🔴 **Trang thai thu BA cua `--lf`, va no la trang thai KHONG duoc canh bao.**

       `_da_do` ben duoi ke ba trang thai cua tep cache: vang mat, doc duoc,
       doc hong. Nhung con mot truc khac han: cache doc duoc, DAY id, va **khong
       id nao con phan giai duoc**. Luc do pytest thay "co failure da biet" nen
       `--lfnf=none` khong ap; roi khong id nao khop nen no khong deselect gi;
       ket qua la mot luot **day du** duoi cai ten `--vong-lap`.

    ⭐ Va id chet theo mot cach hoan toan lanh manh: kho nay **khuyen khich** go
       nhung chot da het ly do ton tai (mot `xfail(strict)` tu thong bao khi
       khiem khuyet cua no chet). Nen `--lf` tu xuong cap nhu **he qua cua viec
       lam dung**.

       Do 05/09 tren `phien/asv-v4`: 20 id trong cache, **ca 20 deu chet** — 5
       mat tep, 15 mat ham, phan lon do pha 27 go cac chot da xong viec.

    ⚠️ Mot id chet KHONG dau doc nhung id con song: chi can **mot** id phan giai
       duoc thi `--lf` van thu hep binh thuong (do bang thuc nghiem). Nen dieu
       kien canh bao la "khong con id nao", khong phai "co id chet".

    ⛔ Ham nay CHI de canh bao, khong de doi hanh vi. Bo chay rong o day se lam
       dung cai tep nay canh bao o cho khac: *"chay rong va chay het roi xanh in
       ra gan giong nhau"*. Mot id khong phan giai duoc con co the la loi thu
       gom tam thoi, va khi do chay rong la mot mau xanh doi tra.
    """
    song = 0
    for k in cac_id:
        tep, _, ham = k.partition("::")
        f = GOC / tep
        if not f.is_file():
            continue
        if not ham:
            song += 1
            continue
        ten = ham.split("::")[-1].split("[")[0]
        try:
            cay = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            # Khong doc duoc thi KHONG ket toi la chet — dem no la song de
            # canh bao nay khong tu bao dong tren mot tep dang sua do.
            song += 1
            continue
        if ten in {n.name for n in ast.walk(cay)
                   if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef,
                                     ast.ClassDef))}:
            song += 1
    return song, len(cac_id)


def _canh_bao_lf(cac_id: set[str]) -> list[str]:
    """Cac dong can in vi `--lf` sap chay TOAN BO. Rong = khong co gi de noi.

    🔑 **Tach ra khoi cho no duoc in, de chot duoc dieu no QUYET DINH.**

       `_con_id_song` do mot dai luong; ham nay ra mot phan quyet. Neu chi chot
       phep do thi mot ban sua doi `song == 0` thanh `song < tong` van xanh —
       va luc do canh bao se bat o moi luot co bat ky id chet nao, tuc bat gan
       nhu luon, tuc bi tat trong dau nguoi doc.

    ⛔ Va dieu kien la "khong con id nao SONG", khong phai "co id CHET". Do bang
       thuc nghiem: mot id chet nam canh mot id song thi `--lf` van thu hep binh
       thuong.
    """
    if not cac_id:
        return []
    song, tong = _con_id_song(cac_id)
    if song:
        return []
    return [
        f"",
        f"[--lf] {tong} id trong cache va KHONG id nao con phan giai duoc",
        "       (tep hoac ham da doi ten / da bi go). pytest coi day la",
        "       'co failure da biet' nen `--lfnf=none` khong ap, roi khong",
        "       id nao khop nen no khong deselect gi.",
        "  ==>  Luot nay se chay TOAN BO, khong phai mot vong hep.",
        "       Ket qua van dung; chi co thoi gian la khong nhu ten goi.",
    ]


def _da_do() -> tuple[set[str], set[str]] | None:
    """(test id, duong dan tep) da do o luot truoc. `None` = KHONG BIET.

    ## Ba trang thai, khong phai hai

    | Tren dia | Nghia | Tra ve |
    |---|---|---|
    | tep vang mat | luot truoc XANH HET (pytest tu xoa) | `(set(), set())` |
    | tep co, doc duoc | dung nhung muc do | tap thuc |
    | tep co, doc hong | khong biet | `None` |

    ⛔ Gop "vang mat" vao "khong biet" la sai, va no da lam hong che do vong lap
       theo mot cach rat kho thay: sau MOI luot gate xanh, `--vong-lap` chay lai
       **toan bo 4143 test** (do 27/08: 3 phut 35) thay vi 15 giay.

       Va no khong phai loi cua ham nay mot minh — `--lfnf=none` cua pytest cung
       chi ap khi cache CO ma RONG. Cache **vang mat** thi pytest coi la "khong
       co thong tin luot truoc" va chay het. Hai tang cung nham lan mot cho.

    ⭐ Nen tu day dung ket luan o day, dung nho vao `--lfnf`: khong co gi do thi
       khong co gi de chay lai, va noi thang ra nhu vay.
    """
    tep = GOC / ".pytest_cache" / "v" / "cache" / "lastfailed"
    if not tep.parent.exists():
        return None                      # chua bao gio chay pytest o cay nay
    try:
        muc = json.loads(tep.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return set(), set()              # luot truoc xanh het
    except (OSError, ValueError):
        return None                      # doc hong => khong biet => chay het
    return (set(muc),
            {k.split("::", 1)[0].replace("\\", "/") for k in muc})


def _chay(argv: list[str], nhan: str) -> tuple[int, float]:
    # ASCII, khong phai ky tu ke khung. Da dinh that 26/08: `gate.py` HUNG dau
    # ra nen stdout khong con la console, Python roi ve `cp1252`, va mot dau
    # gach ke khung lam vo CA BUOC — trong khi bo test chua chay lay mot phep
    # kiem nao.
    #
    # ⛔ Cai bay nam o cho no CHAY DUNG khi goi tay (console UTF-8) va chi vo
    #    khi bi hung — tuc vo o cho it nguoi nhin nhat, va vo som nhat trong CI.
    print(f"\n{'-' * 70}\n  {nhan}\n{'-' * 70}", flush=True)
    t0 = time.monotonic()
    ma = subprocess.run(argv, cwd=GOC).returncode
    global _SO_LAN_CHAY
    _SO_LAN_CHAY += 1
    return ma, time.monotonic() - t0


#: So lan `_chay` **that su** phong mot tien trinh pytest trong luot nay.
#:
#: 🔴 Day la mot khang dinh **nam SAU viec thi hanh**, va do la ca diem cua no.
#:    Ngay 06/09 mot phep tach ham lam hai pha roi vao ma chet sau mot `return`:
#:    tep nay thoat sau **0,114 giay**, ma **0**, **khong chay mot test nao** —
#:    va gate in `[PASS] bo test (song song) 0.1s`. **Ca nam banh coc AST van
#:    xanh**, vi chung hoi *hinh dang ma*, ma hinh dang van dung khi cong cu da
#:    chet. Dau hieu duy nhat la con so giay, thu khong ai doc.
#:
#: ⭐ Mot bien chi tang **khi tien trinh con da chay** thi khong the dung neu
#:    cong cu bat dong. Moi thu doc duoc **truoc** khi chay — co `with` khong,
#:    co nhap khong, khai dung tai nguyen khong — deu mu voi lop loi ay.
_SO_LAN_CHAY = 0

#: Luot nay CO Y khong chay gi (vd `--lf` ma khong co test nao do lan truoc).
#:
#: 🔴 Phai tach khoi `_SO_LAN_CHAY == 0`, vi hai trang thai ay NHIN GIONG NHAU
#:    tu ben ngoai — ca hai deu la "khong tien trinh pytest nao chay" — nhung
#:    mot cai la QUYET DINH con cai kia la TAI NAN. Gop chung lam mot thi hoac
#:    ta bao dong gia moi lan `--vong-lap` chay sau mot luot xanh, hoac ta phai
#:    noi long cong den muc no bo lot ca tai nan 06/09.
_CO_Y_KHONG_CHAY = False


#: Tài nguyên khai với `cua_so_yen`. Cùng tên gate dùng cho bước `bo test`
#: (`gate.py` khai `tai_nguyen=("cpu_nhieu",)` ở ba chỗ) — hai bên phải khai
#: **cùng một chuỗi**, nếu không thì hai lượt cùng ăn CPU mà không thấy nhau.
TAI_NGUYEN = ("cpu_nhieu", "postgres_test")


def _to_tien_la_gate(to_tien: list[tuple] | None = None) -> bool:
    """Lượt này có đang chạy DƯỚI một `gate.py` không?

    🔴 **Vì sao phải hỏi, thay vì cứ xin khoá.** `gate.py` gọi tệp này như một
       tiến trình con ở **bốn** chỗ (dòng 763, 769, 786, 978) và nó **đang giữ**
       `cpu_nhieu` lúc gọi. Khoá của `cua_so_yen` là **một tệp `O_EXCL`**, không
       tái nhập — nên nếu ta cũng xin thì ta chờ chính tổ tiên của mình, hết
       `cho_toi_da_s` rồi **chèn**. Tức bản vá sẽ làm mọi lượt gate chậm thêm
       đúng bằng thời gian chờ, rồi quay về đúng trạng thái cũ.

    ⭐ Hỏi **quan hệ** (`ppid`), đừng hỏi **nhãn**. Đó là luật đã trả giá ba lần
       trong đêm 05–06/09: `timeout.exe` tự fork làm phép lọc cmdline đếm
       **thừa**, `execnet` làm nó đếm **thiếu**. Cây tiến trình là thứ thật.

    ⛔ Và ta hỏi *"tổ tiên có phải gate không"*, **không** hỏi *"ai đang giữ khoá
       có phải tổ tiên không"*. Khác biệt quan trọng: gate có đường
       `cua_so_yen.chay_khong_khoa` — hết `--cho` thì nó **chèn** và chạy mà
       **không giữ gì**. Hỏi theo khoá thì trong đúng ca ấy ta lại đi xin khoá
       của phiên kia và làm chậm một lượt gate đang chạy. Chính sách khoá là
       việc của gate; việc của ta là **đừng xen vào**.

    ⭐ `to_tien` (danh sách `(ten, argv)`) là **cửa tiêm cho phép kiểm**, và nó có mặt vì một lỗi
       thật: bản đầu của hàm này không có nó, nên phép kiểm phải khẳng định
       `_to_tien_la_gate() is False` — tức chốt một **sự thật môi trường** thay
       vì một **tính chất của mã**. Nó xanh khi chạy `pytest` tay và **đỏ khi
       gate chạy bộ test**, vì lúc ấy pytest *thật sự* đang ở dưới `gate.py`.
       Đúng bẫy "chạy riêng xanh mà gate đỏ".

    ⚠️ Không có `psutil` thì trả `True` — tức **không khoá**, hành vi y như
       trước bản vá này. Chọn chiều đó có chủ ý: đoán nhầm sang "có khoá" làm
       **hỏng** một lượt gate, đoán nhầm sang "không khoá" chỉ **không sửa được
       gì**. `psutil` là thứ `gate.py` cũng import, nên khi có gate thì có nó.
    """
    if to_tien is None:
        try:
            import psutil
        except ImportError:
            return True
        try:
            to_tien = [(t.name(), t.cmdline() or [])
                       for t in psutil.Process().parents()]
        except (psutil.Error, OSError):
            return True                 # khong doc duoc cay -> khong khoa
    return any(_la_gate(ten, argv) for ten, argv in to_tien)


def _la_gate(ten: str, argv, kich_ban: str = "gate.py") -> bool:
    """Tien trinh nay CO PHAI mot luot `gate.py` dang chay khong.

    🔴 **Dung khop CHUOI CON tren ca dong lenh.** Ban truoc hoi
       `any("gate.py" in c for c in cmdline_to_tien)` voi `c` la ca dong lenh da
       noi lai. To tien cua pytest la `bash.exe -c "<CA cau lenh>"`, nen **bat
       ky** cau lenh nao nhac ten cong cu — mot `grep`, mot ghi chu, mot
       docstring trong heredoc — cung lam ham nay tra `True`, va `test_nhanh`
       **lang le bo khoa**.

       Do 06/09, hai lenh giong het nhau tru mot dong `echo` vo hai:

           lenh KHONG chua chu `gate.py`  ->  1 passed
           lenh CO   chua chu do          ->  1 failed

    ⛔ Va no hong theo huong de chiu, dung cho dau nhat: nhung phien hay nhac
       `gate.py` nhat la nhung phien **dang phoi hop voi nhau**.

    ⭐ Nen hoi TEN TEP DUOC THI HANH, dung hoi van ban cua cau lenh. Doi so cua
       mot tien trinh python la mot **duong dan**; doi so cua mot vo `-c` la
       **mot chuoi dai chua ca cau lenh** — `basename` phan biet duoc hai thu do,
       `in` thi khong. Loc them theo ten tien trinh vi mot chuoi ket thuc dung
       bang `tools/gate.py` van co `basename` la `gate.py`.
    """
    if not (ten or "").lower().startswith("python"):
        return False
    return any(os.path.basename(str(d).replace(chr(92), "/")) == kich_ban
               for d in list(argv or [])[1:])


def to_tien_da_giu_khoa(kich_ban: tuple[str, ...] = ("gate.py", "test_nhanh.py"),
                        to_tien: list[tuple] | None = None) -> bool:
    """Mot to tien CO PHAI mot cong cu da xin khoa ho ta khong.

    ⭐ Tong quat hoa `_to_tien_la_gate` de `tests/conftest.py` dung lai duoc.
       `pytest` go tay la lo CUOI CUNG con lai: `gate.py` xin khoa,
       `test_nhanh.py` xin khoa, nhung `python -m pytest tests/ -n 6` thi
       khong — va do la lenh nang nhat ma bon phien deu go trong dem 05-06/09.

    ⛔ Dung MOT ham cho ca hai cho, dung chep. Hai ban sao cua cung mot phep
       hoi la hai cho de chung lech nhau — va lech o day nghia la hoac khoa
       chet (ca hai cung xin) hoac lo hong (ca hai cung bo qua).
    """
    if to_tien is None:
        try:
            import psutil
        except ImportError:
            return True
        try:
            to_tien = [(t.name(), t.cmdline() or [])
                       for t in psutil.Process().parents()]
        except (psutil.Error, OSError):
            return True
    return any(_la_gate(ten, argv, kb)
               for ten, argv in to_tien for kb in kich_ban)


def _so_loi_se_dung(n: str) -> int:
    """Số lõi lượt này sẽ chiếm — khai cho `cua_so_yen` để lượt KHÁC trừ đúng.

    ⛔ Khai 0 làm cả cơ chế vô dụng một cách im lặng: lượt khác đọc bản ghi, thấy
       "giữ 0 lõi", và kết luận máy còn trống. `cua_so_yen.SO_LOI_KHI_KHONG_KHAI`
       tồn tại cho đúng lỗi đó, nhưng khai đúng vẫn hơn để nó đoán.
    """
    if n.isdigit():
        return max(1, int(n))
    # `-n auto`: xdist doc so nhan VAT LY.
    try:
        import psutil
        return max(1, psutil.cpu_count(logical=False) or os.cpu_count() or 1)
    except ImportError:
        return max(1, os.cpu_count() or 1)


#: Ma tra ve khi luot chay KHONG phong mot tien trinh pytest nao.
#: Khac 1 (co test do) va khac 5 (pytest thu thap 0 test) de doc duoc ngay.
MA_KHONG_CHAY_GI = 3
NL_IN = chr(10)


def _chot(ma: int) -> int:
    """Cong cuoi: mot luot "xanh" ma khong chay gi thi KHONG xanh.

    ⛔ Doi xung voi `_SO_LAN_CHAY`: bo dem chi tang khi mot tien trinh pytest da
       that su duoc phong. Nen `ma == 0` **va** bo dem `== 0` la trang thai khong
       the co that — no chi xay ra khi than ham bi cat mat, bi `return` som, hoac
       bi refactor hong. Do dung la chuyen da xay ra 06/09.

    ⭐ Cho no mot ma tra ve RIENG, khong dung 1: nguoi doc phai phan biet duoc
       *"co test do"* voi *"khong test nao chay"*. Hai chuyen do doi hoi hai hanh
       dong khac han nhau, va gop chung vao mot ma la bat nguoi sau di doan.
    """
    if ma == 0 and _SO_LAN_CHAY == 0 and not _CO_Y_KHONG_CHAY:
        print(NL_IN + "=" * 70)
        print("  KHONG MOT TIEN TRINH pytest NAO DUOC PHONG.")
        print("  Day KHONG phai mot luot xanh - day la mot luot RONG.")
        print("  `_SO_LAN_CHAY` chi tang SAU khi mot tien trinh da chay.")
        print("=" * 70)
        return MA_KHONG_CHAY_GI
    return ma


def main() -> int:
    """Vo mong: doc doi so, quyet dinh CO XIN KHOA hay khong, roi goi `_than`.

    🔴 **Vi sao tep nay phai xin khoa — do duoc dem 05-06/09/2026.**

       `cua_so_yen.py trang-thai` bao `RANH` trong khi may dang chay **ba** luot
       gate. No khong sai: no tra loi cau *"co ai XIN khoa khong"*, khong tra
       loi cau *"co gi dang CHAY khong"*. Va truoc ban va nay, tep nay **khong
       co mot dong nao** xin khoa (`grep cua_so_yen tools/test_nhanh.py` -> rong)
       — nen `python tools/test_nhanh.py` va `pytest` go tay chay hoan toan
       **vo hinh** voi moi phien khac.

    ⭐ **Nhan tin KHONG phai co che loai tru lan nhau.** Do duoc dem ay: hai
       phien bam gate cach nhau **25 giay**, ca hai deu do truoc khi bam, ca hai
       deu thay may trong, ca hai deu dung luc do. Khe giua *do* va *bam*
       **khong co day** — 25 giay chi la con so gap phai, no co the la 2. Thu
       dong duoc khe do la mot cai khoa, khong phai mot giao uoc.

    ⚠️ Bon phien da tra tien cho lo hong nay trong mot dem: mot luot gate bi
       `timeout` cat o buoc 22/27 (mat trang 21 buoc), va mot luot khac chay
       cham 25% (613,6s so voi 490s).
    """
    _ep_utf8()
    p = argparse.ArgumentParser(description="Chay pytest song song, ket qua y het.")
    p.add_argument("-n", default="auto",
                   help="so worker (mac dinh: auto = so nhan CPU)")
    p.add_argument("--lf", action="store_true",
                   help="chi chay nhung test vua do (--last-failed)")
    p.add_argument("--lf-rong-thi-khong-chay", action="store_true",
                   help="di kem --lf: khong co test nao do lan truoc thi chay "
                        "RONG, thay vi chay tat ca")
    p.add_argument("-k", default="", help="loc theo ten test")
    p.add_argument("--noi-tiep", action="store_true",
                   help="chay mot tien trinh — de doi chieu ket qua")
    p.add_argument("--cho", type=float, default=15.0,
                   help="phut cho khoa truoc khi CHEN (mac dinh 15, y het gate)")
    p.add_argument("--khong-khoa", action="store_true",
                   help="chay ma khong xin khoa — chi dung khi biet ro vi sao")
    args, con_lai = p.parse_known_args()

    # Cung ly do nhu trong `gate.py`: NOI RA ai khac dang ban, roi van chay.
    # Khoa `cua_so_yen` xep hang; dong nay chi lam cho thay thu khoa khong thay.
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from may_ban import dong_canh_bao
        _canh = dong_canh_bao()
        if _canh:
            print(_canh)
    except Exception as _e:  # noqa: BLE001
        print(f"  [may ban] khong dem duoc: {type(_e).__name__}")

    # ⛔ Duoi gate thi KHONG xin: gate da giu `cpu_nhieu` va khoa khong tai nhap.
    if args.khong_khoa or _to_tien_la_gate():
        return _chot(_than(args, con_lai))

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from cua_so_yen import CuaSoYen

    phien = (os.environ.get("LTT_PHIEN")
             or f"{socket.gethostname()}:{os.getpid()}")
    with CuaSoYen(phien, "test_nhanh",
                  cho_toi_da_s=args.cho * 60,
                  tai_nguyen=TAI_NGUYEN,
                  so_loi=_so_loi_se_dung(args.n)) as khoa:
        # ⭐ CHEN thi VAN CHAY, chi phai NOI RA — day la chinh sach da co cua
        #    `CuaSoYen`, khong phai lua chon moi cua tep nay: *"mot cong chat
        #    luong tu choi chay vi ban la mot cong khong ai dung"*.
        if getattr(khoa, "chay_khong_khoa", False):
            print("  [cua so yen] dang CHEN - mot luot khac van giu khoa. "
                  "Ket qua lan nay co the bi nhieu (may dang chia CPU).")
        elif khoa.da_cho_s > 1:
            print(f"  [cua so yen] da cho {khoa.da_cho_s:.0f} giay de den luot.")
        return _chot(_than(args, con_lai))


def _than(args, con_lai: list[str]) -> int:
    """Than that su cua luot chay. Tach ra de `main` boc duoc khoi `with`."""
    chung = [sys.executable, "-m", "pytest", "-q", *BO_QUA, *con_lai]
    if args.lf:
        chung.append("--lf")
        # 🔴 `--lf` MOT MINH KHONG LAM DIEU NGUOI TA TUONG.
        #
        #    Tai lieu pytest noi ro: no chay lai nhung test da do lan truoc,
        #    **hoac TAT CA neu khong cai nao do**. Nen sau mot luot xanh, `--lf`
        #    la mot lenh chay day du — mat 4,4 phut thay vi vai giay.
        #
        #    Do 27/08: `gate.py --vong-lap` (dat ra de xong trong ~20 giay) mat
        #    4 phut 26, vi lan truoc moi thu deu xanh.
        #
        # ⚠️ `--lfnf none` doi hanh vi do: khong co gi do thi chay RONG. Dung cho
        #    vong lap sua-roi-thu; KHONG dung cho mot luot lay bang chung, vi
        #    "chay rong" va "chay het roi xanh" in ra gan giong nhau.
        if args.lf_rong_thi_khong_chay:
            chung.append("--lfnf=none")
    if args.k:
        chung += ["-k", args.k]

    t_dau = time.monotonic()

    # ── Khong co gi do lan truoc thi khong co gi de chay lai ─────────────────
    #
    # 🔴 Ket luan o DAY, khong nho vao `--lfnf=none`. Pytest chi ap co do khi
    #    cache CO ma RONG; cache **vang mat** (no tu xoa sau mot luot xanh het)
    #    thi no coi la "khong biet gi ve luot truoc" va chay toan bo.
    #
    #    Hau qua do that 27/08: sau moi luot gate xanh, `--vong-lap` chay lai
    #    4143 test trong 3 phut 35 — dung cai no sinh ra de tranh.
    #
    # ⭐ Va noi THANG ra rang khong co gi chay, dung in mot dong "PASS" trong
    #    nhu mot luot day du. Do la khac biet giua mot che do nhanh va mot che
    #    do noi doi.
    if args.lf and args.lf_rong_thi_khong_chay:
        biet = _da_do()
        if biet is not None and not biet[0]:
            print("\n[--lf] KHONG test nao do o luot truoc => khong chay lai gi.")
            print("       Day KHONG phai mot luot test xanh. Do la mot luot")
            print("       test RONG. Muon chay that: bo `--lf`.")
            # Khai voi `gate.py` bang dau BO QUA o DAU DONG: mot buoc co y
            # khong lam gi phai hien ra o dong RESULT, khong duoc lan vao
            # mot chu PASS tran.
            print("BO QUA: --lf khong co test nao do o luot truoc")
            global _CO_Y_KHONG_CHAY
            _CO_Y_KHONG_CHAY = True
            return 0
        # ⭐ Trang thai thu BA — xem `_canh_bao_lf`. Khong doi hanh vi, chi GO
        #    SU IM LANG: mot luot day du chay duoi ten `--vong-lap` van xanh
        #    dung, nhung nguoi doc tuong minh vua ton 15 giay.
        if biet is not None:
            for dong in _canh_bao_lf(biet[0]):
                print(dong)

    if args.noi_tiep:
        ma, _ = _chay(chung, "MOT TIEN TRINH (doi chieu)")
        print(f"\nTONG: {time.monotonic() - t_dau:.0f} giay")
        return ma

    # ── Pha 1: song song, TRU cac tep lam ban cay ────────────────────────────
    loai = [f"--deselect={t}" for t in TEP_NOI_TIEP]
    ma1, t1 = _chay(chung + ["-n", args.n, "--dist", "loadfile", *loai],
                    f"PHA 1 - song song ({args.n} worker), tru {len(TEP_NOI_TIEP)} tep")

    # ── Pha 2: cac tep ghi vao cay kho, noi tiep ─────────────────────────────
    # ⛔ Chay ca khi pha 1 do: bo qua chung se lam bao cao cuoi noi doi ve do phu.
    co = [t for t in TEP_NOI_TIEP if (GOC / t).is_file()]
    if args.lf and args.lf_rong_thi_khong_chay:
        # 🔴 `--lf` KHONG loc duoc pha nay, va ly do rat de doc nham.
        #
        #    pytest chi ap `--lfnf` khi cache lastfailed RONG HOAN TOAN. O day
        #    cache thuong co hang tram muc tu cac tep KHAC, nen voi ba tep nay
        #    pytest ket luan "co failure da biet" roi... khong deselect gi ca va
        #    chay tron ca ba tep.
        #
        #    Do 27/08: pha 1 con 13 giay nho `--lfnf=none`, pha 2 van 54 giay —
        #    tuc 80% thoi gian cua che do "vong lap" nam o ba tep ma nguoi dang
        #    sua gan nhu chac chan khong dung toi.
        #
        # ⭐ Nen loc bang TAY, theo duong dan, tu chinh cache do. Va IN RA cai
        #    bi bo — mot pha bien mat khong tieng dong la thu da lam hong bao
        #    cao do phu truoc day.
        biet = _da_do()
        do = None if biet is None else biet[1]
        if do is None:
            print("\n[--lf] khong doc duoc cache lastfailed -> chay CA pha 2.")
            do = set(co)
        bo = [t for t in co if t not in do]
        co = [t for t in co if t in do]
        if bo:
            ten = ", ".join(pathlib.PurePath(t).name for t in bo)
            print(f"\n[--lf] bo qua {len(bo)} tep pha 2 (khong tep nao do lan "
                  f"truoc): {ten}")
    ma2, t2 = (0, 0.0)
    if co:
        ma2, t2 = _chay(chung + co, f"PHA 2 - noi tiep ({len(co)} tep ghi vao cay kho)")

    tong = time.monotonic() - t_dau
    print(f"\n{'=' * 70}")
    print(f"  pha 1 song song : {t1:6.0f} giay")
    print(f"  pha 2 noi tiep  : {t2:6.0f} giay")
    print(f"  TONG            : {tong:6.0f} giay ({tong / 60:.1f} phut)")
    print(f"{'=' * 70}")

    ma = ma1 or ma2
    print("RESULT: PASS" if ma == 0 else "RESULT: FAIL")
    if ma == 0:
        print("\n!!  Day KHONG thay the `tools/gate.py`. Gate con chay 21 phep kiem")
        print("    tinh + ba bo test frontend + bat bien da tien trinh.")
    return ma


if __name__ == "__main__":
    raise SystemExit(main())
