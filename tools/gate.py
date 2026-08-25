"""
gate.py — MỘT lệnh chạy toàn bộ cổng chất lượng.

    python tools/gate.py            # đầy đủ
    python tools/gate.py --quick    # bỏ full pytest, dùng khi vòng lặp ngắn

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
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTENDS = ("agent-canvas", "autosub-studio", "prompt-ai-ommi")


class Step:
    def __init__(self, name: str, argv: list[str], cwd: Path):
        self.name = name
        self.argv = argv
        self.cwd = cwd
        self.ok: bool | None = None
        self.seconds = 0.0
        self.tail = ""


def _npm() -> str | None:
    """npm trên Windows là `npm.cmd`; `shutil.which` xử lý đúng cả hai."""
    return shutil.which("npm")


def _steps(quick: bool) -> list[Step]:
    steps: list[Step] = [
        # 🔴 DAT DAU TIEN co chu y: mot tep khong bien dich duoc thi moi
        #    phep do phia sau deu vo nghia. Da tung commit mot tep vo cu
        #    phap ma gate bao PASS 14/14 - cac chot khac deu BO QUA tep
        #    khong parse duoc (chung dem xu huong), va `--quick` bo pytest.
        Step("bien dich duoc", [sys.executable, "tools/check_bien_dich.py"],
             ROOT),
        Step("secret scan", [sys.executable, "tools/scan_source_secrets.py"], ROOT),
        Step("app contract lint", [sys.executable, "tools/lint_app_contract.py"], ROOT),
        # Re nhung bat duoc thu test khong bat: mot route khong co test ma thieu
        # import thi chi vo khi nguoi dung bam. Xem tools/check_undefined_names.py.
        Step("ten chua dinh nghia", [sys.executable, "tools/check_undefined_names.py"], ROOT),
        # Banh coc: khong cho THEM cho nuot loi lang le. Xem
        # tools/check_silent_except.py vi sao khong doi ve 0 ngay.
        Step("nuot loi lang le", [sys.executable, "tools/check_silent_except.py"], ROOT),
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
             [sys.executable, "tools/check_dich_thieu.py"], ROOT),
        # Hồ sơ là bản đồ để AI/người mới hiểu code. Nếu không khóa freshness,
        # nó sẽ âm thầm mô tả hệ thống cũ ngay sau lần sửa đầu tiên.
        Step("system profile", [sys.executable, "tools/build_system_profile.py",
                                 "--check"], ROOT),
        # EXT-17: hợp đồng công khai của /api/v1 so với bản chuẩn đã đóng băng.
        # Không có bước này thì một thay đổi phá vỡ tương thích lên tàu được vì
        # không ai diff một thứ mà không ai gom lại. Cố ý phá thì chạy
        # `--accept`, và lần ghi lại đó hiện trong diff cho người review thấy.
        Step("hop dong API", [sys.executable, "tools/check_api_compat.py"],
             ROOT),
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
             [sys.executable, "tools/check_sdk_contract.py"], ROOT),
        # …và collection Postman phải được SINH lại, không sửa tay: một bản sao
        # thứ hai của hợp đồng luôn là bản trôi dạt.
        # Ban sao `ltt.css` canh GUI khong duoc troi khoi ban goc: mot ban
        # sao tinh khong co gi nhac no cap nhat thi no se khong cap nhat,
        # va cong cu se trong GAN GIONG nen tang - kieu sai kho chiu nhat.
        Step("tai san GUI", [sys.executable, "tools/dong_goi_gui.py", "--kiem"],
             ROOT),
        Step("postman", [sys.executable, "tools/build_postman.py", "--check"],
             ROOT),
    ]
    if not quick:
        # H36.9: bo bat bien DA TIEN TRINH. Ba loi P0 cua ban audit 2026-08-15
        # lot qua hon ba nghin test vi chua tung co gi chay hai tien trinh
        # worker cung luc — va phep do bit lo hong do lai chi chay khi co
        # PostgreSQL, nen `pytest` chi in mot chu `s`. Mot chu `s` giua ba
        # nghin dau cham la vo hinh. Buoc rieng nay khong lam gate do khi may
        # khong co PostgreSQL, nhung viec bo qua thi khong bao gio con lang le.
        steps.append(Step("bat bien da tien trinh",
                          [sys.executable, "tools/check_multiproc.py"], ROOT))
    npm = _npm()
    for name in FRONTENDS:
        folder = ROOT / "frontend" / name
        if not (folder / "package.json").exists():
            continue
        if npm is None:
            steps.append(Step(f"frontend {name}", ["npm-khong-tim-thay"], folder))
            continue
        steps.append(Step(f"frontend {name}", [npm, "test", "--", "--run"], folder))
    if not quick:
        # Browser/audit artifacts live under tmp/ and test-results/ by contract;
        # they may contain copied ``tests`` folders and must never be collected
        # as a second copy of the repository test suite.
        steps.append(Step("pytest", [sys.executable, "-m", "pytest", "-q",
                                      "--ignore=tmp", "--ignore=test-results"], ROOT))
    return steps


def _run(step: Step) -> None:
    started = time.monotonic()
    try:
        done = subprocess.run(step.argv, cwd=step.cwd, capture_output=True,
                              text=True, encoding="utf-8", errors="replace")
        step.ok = done.returncode == 0
        output = (done.stdout or "") + (done.stderr or "")
    except OSError as exc:
        step.ok = False
        output = f"khong chay duoc: {exc}"
    step.seconds = time.monotonic() - started
    lines = [line for line in output.splitlines() if line.strip()]
    step.tail = "\n".join(lines[-4:])


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
BO_QUA_KHI_QUICK = ("bat bien da tien trinh", "pytest")


def _dau_van_tay_cay() -> str:
    """Dấu vân tay của cây nguồn: đường dẫn + kích thước + thời điểm sửa.

    Không băm nội dung — chỉ cần biết cây **có đổi hay không** trong lúc chạy,
    và băm nội dung toàn cây tốn thêm hàng chục giây cho đúng một câu trả lời
    có/không.
    """
    import hashlib

    h = hashlib.sha256()
    for thu_muc in ("apps", "platform_core", "server", "tools", "tests",
                    "alembic", "locale"):
        goc = ROOT / thu_muc
        if not goc.exists():
            continue
        for f in sorted(goc.rglob("*")):
            if not f.is_file() or "__pycache__" in f.parts:
                continue
            try:
                st = f.stat()
            except OSError:
                continue
            h.update(f"{f.relative_to(ROOT).as_posix()}:{st.st_size}:"
                     f"{int(st.st_mtime)}\n".encode())
    return h.hexdigest()[:16]


def main() -> int:
    parser = argparse.ArgumentParser(description="Chay toan bo cong chat luong.")
    parser.add_argument("--quick", action="store_true",
                        help="bo full pytest (dung cho vong lap ngan)")
    args = parser.parse_args()

    steps = _steps(args.quick)
    van_tay_dau = _dau_van_tay_cay()
    print(f"Gate: {len(steps)} buoc\n")
    for step in steps:
        print(f"  ... {step.name}", flush=True)
        _run(step)

    print("\n" + "=" * 62)
    failed = [s for s in steps if not s.ok]
    for step in steps:
        mark = "PASS" if step.ok else "FAIL"
        print(f"  [{mark}] {step.name:<28} {step.seconds:6.1f}s")
    if failed:
        print("\nChi tiet buoc that bai:")
        for step in failed:
            print(_console_text(f"\n--- {step.name} ---\n{step.tail}"))
    print("=" * 62)

    # 🔴 Một lượt gate đầy đủ mất 2,9–4,4 giờ. Trên kho này — hai phiên làm
    #    việc song song — cây đổi vài phút một lần. Ngày 25/08 có ba lượt đầy
    #    đủ, và lượt 4,4 giờ báo lỗi ở **một tệp đã đổi tên từ nhiều giờ
    #    trước**.
    #
    #    Kết quả ấy không sai lúc nó đo. Nó **trả lời về quá khứ** — và đọc nó
    #    như bằng chứng cho hiện tại là cách sinh ra ba vòng sửa những thứ
    #    không còn hỏng.
    van_tay_cuoi = _dau_van_tay_cay()
    if van_tay_cuoi != van_tay_dau:
        print(f"CAY DA DOI TRONG LUC CHAY ({van_tay_dau} -> {van_tay_cuoi}).")
        print("Ket qua duoi day noi ve cay luc BAT DAU, khong phai cay hien tai.")
        print("Chay lai tren mot cay dung yen neu can no lam BANG CHUNG.")
        print("=" * 62)

    ket = "PASS" if not failed else f"FAIL ({len(failed)}/{len(steps)})"
    if args.quick:
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
    else:
        print("RESULT:", ket)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
