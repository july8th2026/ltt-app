"""
gate.py — MỘT lệnh chạy toàn bộ cổng chất lượng.

    python tools/gate.py             # PHAN QUYET  — day du, ~5 phut
    python tools/gate.py --quick     # bo hai buoc nang, ~40 giay
    python tools/gate.py --vong-lap  # CHAN DOAN   — tinh + `--lf`, ~15 giay

## Ba che do, va chon nham thi hong theo hai kieu khac nhau

| | Chay gi | Do 27/08 | Dung khi |
|---|---|---|---|
| day du | tat ca 23 buoc | **~5 phut** | truoc khi bao xong |
| `--quick` | bo `bo test` + da tien trinh | ~40 giay | sua nhieu tep lien tiep |
| `--vong-lap` | tinh + `test_nhanh --lf` | **~15 giay** | sau MOI lan sua |

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
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTENDS = ("agent-canvas", "autosub-studio", "prompt-ai-ommi")


#: Nhóm quyết định LỊCH CHẠY, không quyết định ý nghĩa của bước.
#:
#:   cong     — cổng gác. Chạy MỘT MÌNH và trước hết. Xem `bien dich duoc`.
#:   nang     — dài (phút). Khởi động TRƯỚC vì lịch "việc dài chạy trước" cho
#:              tổng thời gian ngắn nhất khi mọi thứ khác nấp được vào bóng nó.
#:   tinh     — mỗi bước vài giây, độc lập nhau hoàn toàn.
#:   frontend — `npm test` ở ba thư mục; độc lập với nhau và với mọi thứ khác.
NHOM = ("cong", "nang", "tinh", "frontend")


class Step:
    def __init__(self, name: str, argv: list[str], cwd: Path,
                 nhom: str = "tinh"):
        assert nhom in NHOM, nhom
        self.name = name
        self.argv = argv
        self.cwd = cwd
        self.nhom = nhom
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
             ROOT, nhom="cong"),
        Step("secret scan", [sys.executable, "tools/scan_source_secrets.py"], ROOT),
        Step("app contract lint", [sys.executable, "tools/lint_app_contract.py"], ROOT),
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
                          [sys.executable, "tools/check_multiproc.py"], ROOT,
                          nhom="nang"))
    npm = _npm()
    for name in FRONTENDS:
        folder = ROOT / "frontend" / name
        if not (folder / "package.json").exists():
            continue
        if npm is None:
            steps.append(Step(f"frontend {name}", ["npm-khong-tim-thay"], folder,
                              nhom="frontend"))
            continue
        steps.append(Step(f"frontend {name}", [npm, "test", "--", "--run"], folder,
                          nhom="frontend"))
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
        steps.append(Step("bo test (song song)",
                          [sys.executable, "tools/test_nhanh.py"], ROOT,
                          nhom="nang"))
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
    """Chế độ `--vong-lap`: đủ nhanh để chạy sau MỖI lần sửa.

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
    ra.append(Step("bo test --lf",
                   [sys.executable, "tools/test_nhanh.py", "--lf",
                    "--lf-rong-thi-khong-chay"], ROOT, nhom="nang"))
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

    # `len(nang) + j` luồng: mỗi việc nặng một luồng riêng, phần còn lại chia `j`.
    with ThreadPoolExecutor(max_workers=len(nang) + max(1, j)) as ex:
        cho = [ex.submit(chay_va_in, s) for s in nang]      # dài nhất, chạy trước
        cho += [ex.submit(chay_va_in, s) for s in nhe]
        for f in cho:
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


def _anh_chup_cay() -> dict[str, tuple[int, int]]:
    """Ảnh chụp cây nguồn: đường dẫn → (kích thước, thời điểm sửa).

    Không băm nội dung — chỉ cần biết cây **có đổi hay không** trong lúc chạy,
    và băm nội dung toàn cây tốn thêm hàng chục giây cho đúng một câu hỏi
    có/không.

    ⭐ Trả về cả **bản đồ** chứ không chỉ một chuỗi băm, vì hai chuỗi băm khác
       nhau không nói được gì ngoài "khác nhau". Xem `_ke_cho_da_doi`.
    """
    ra: dict[str, tuple[int, int]] = {}
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
            ra[f.relative_to(ROOT).as_posix()] = (st.st_size, int(st.st_mtime))
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Chay toan bo cong chat luong.")
    parser.add_argument("--quick", action="store_true",
                        help="bo full pytest (dung cho vong lap ngan)")
    parser.add_argument("--vong-lap", action="store_true",
                        help="che do VONG LAP: tinh + `test_nhanh --lf`, ~20s")
    parser.add_argument("-j", type=int, default=8,
                        help="so luong buoc tinh chay cung luc (mac dinh 8)")
    parser.add_argument("--tuan-tu", action="store_true",
                        help="ep chay noi tiep - de go loi chinh gate")
    args = parser.parse_args()

    steps = _steps(args.quick or args.vong_lap)
    if args.vong_lap:
        steps = _rut_gon_vong_lap(steps)
    cay_dau = _anh_chup_cay()
    print(f"Gate: {len(steps)} buoc"
          f"{'' if args.tuan_tu else f', {args.j} luong cho buoc tinh'}\n")
    _chay_theo_lich(steps, j=args.j, tuan_tu=args.tuan_tu)

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
    cay_cuoi = _anh_chup_cay()
    if cay_cuoi != cay_dau:
        print("CAY DA DOI TRONG LUC CHAY:")
        _ke_cho_da_doi(cay_dau, cay_cuoi)
        print("Ket qua duoi day noi ve cay luc BAT DAU, khong phai cay hien tai.")
        print("Chay lai tren mot cay dung yen neu can no lam BANG CHUNG.")
        print("=" * 62)

    ket = "PASS" if not failed else f"FAIL ({len(failed)}/{len(steps)})"
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
    else:
        print("RESULT:", ket)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
