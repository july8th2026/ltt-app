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
    return ma, time.monotonic() - t0


def main() -> int:
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
    args, con_lai = p.parse_known_args()

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
