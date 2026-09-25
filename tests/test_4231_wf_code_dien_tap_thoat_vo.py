"""🔴 DIỄN TẬP THOÁT SANDBOX cho `core.code` — điều kiện RA của P-D mục 4.

Đây là **phép nghiệm thu ranh giới**, khác hẳn `test_4230` (đo *lớp siết
thêm* isolated-vm). Giả định ở đây: **lớp isolated-vm đã bị vượt qua** — coi
như code đang chạy như Node THUẦN, không có `require` bị chặn, không có
isolate nào cả (JS sandbox trong-tiến-trình có lịch sử CVE dài: `vm2`
CVSS 10.0; `isolated-vm`/`vm` của n8n sau khi bỏ `vm2` vẫn dính
CVE-2026-25049). Câu hỏi DUY NHẤT tệp này trả lời: **AppContainer một mình
có còn chặn được không?**

## Bảy đường thoát (brief P-D mục 4), mỗi đường HAI phép

```
đường thoát           phép "PHẢI THẤT BẠI"              phép TIÊM LỖI (chứng minh CẦN)
─────────────────────  ────────────────────────────────  ──────────────────────────────
đọc tệp ngoài vỏ        test_D1_doc_tep_ngoai_vo_BI_CHAN   cấp ACL đúng SID -> đọc được
ghi tệp ngoài vỏ        test_D2_ghi_tep_ngoai_vo_BI_CHAN   cấp ACL đúng SID -> ghi được
kết nối mạng trực tiếp  test_D3_ket_noi_truc_tiep_BI_CHAN  thêm cap internetClient -> REACHED
miền ngoài allowlist    test_D4_mien_ngoai_allowlist...    domain nằm TRONG allowlist -> qua
                                                            được (200), rỗng thì domain
                                                            "hợp lệ" cũng bị chặn (fail-closed)
sinh tiến trình con     test_D5_spawn_con_BI_CHAN          thêm cap internetClient -> REACHED
đọc env bí mật          test_D6_doc_env_bi_mat_RONG        tiêm biến giả có chữ SECRET -> hiện
ăn bộ nhớ/CPU vô hạn    test_D7_an_bo_nho...                đo SỐ (đỉnh RAM, thời lượng) —
                        test_D7_vong_lap_cpu...             chính con số đó LÀ phép tiêm lỗi:
                                                            không trần thì các số này không giới
                                                            hạn được
```

## Vì sao không dùng `connector.chay()` cho các phép này

`connector.chay()` luôn mở `proxy_egress` (spec §9.4 cho node `piece.*`) và
bật lớp vá trong-tiến-trình `chan_trong_tien_trinh.js`. **`core.code` thì
không** (`code_sandbox.chay()` không mở proxy — không có domain nào được
phép cho code tuỳ ý). Chạy các drill này qua `connector.chay()` sẽ đo NHẦM
thứ: kết quả "bị chặn" có thể là lớp vá trong-tiến-trình, không phải
AppContainer. `_chay_tho_vo_code()` dưới đây dựng `vao.json`/gọi `vo_boc.chay`
trực tiếp, đúng tư thế mạng thật của một job `core.code`.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sys
import tempfile
import uuid

import pytest

CAN_WINDOWS = pytest.mark.skipif(
    sys.platform != "win32", reason="AppContainer chi co tren Windows")


def _chay_tho_vo_code(ten_vo, ten_action, props, *, caps=(),
                       moi_truong_them=None, han_ms=15_000):
    """Chạy MỘT action của `@ltt/piece-gia` trong vỏ code — KHÔNG proxy.

    Trả `(KetQuaVo, ra: dict|None, log: str)`. `ra` là nội dung `ra.json`
    (giao thức §11.1); `log` là stdout+stderr THẬT của tiến trình trong vỏ
    (nơi hành động `spawn` con ghi, `stdio:'inherit'`).
    """
    from platform_core.workflow import connector, vo_boc
    tmp = connector.THU_MUC_LAM_VIEC / f"drill-{uuid.uuid4().hex[:12]}"
    tmp.mkdir(parents=True)
    try:
        yc = {"op": "run_action", "piece": "@ltt/piece-gia", "version": "0.0.0",
              "name": ten_action, "props": props or {}, "auth": None,
              "store": {}, "tmp_dir": str(tmp), "han_ms": han_ms}
        (tmp / "vao.json").write_text(json.dumps(yc), encoding="utf-8")
        moi = vo_boc.moi_truong_toi_thieu(
            them=dict(moi_truong_them or {}, LTT_TEST="1"))
        kq = vo_boc.chay(
            [str(connector.THU_MUC_LAM_VIEC / "node.exe"), "--preserve-symlinks",
             "--preserve-symlinks-main",
             str(connector.THU_MUC_RUNNER / "src" / "runner.js"),
             str(tmp / "vao.json"), str(tmp / "ra.json")],
            ra_log=str(tmp / "log.txt"), ten_vo=ten_vo, caps=caps,
            moi_truong=moi, han_ms=han_ms, thu_muc=str(connector.THU_MUC_RUNNER))
        ra = None
        raj = tmp / "ra.json"
        if raj.exists():
            try:
                ra = json.loads(raj.read_text(encoding="utf-8"))
            except ValueError:
                ra = None
        log = ""
        try:
            log = (tmp / "log.txt").read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
        return kq, ra, log
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture(scope="module")
def vo():
    """Vỏ code riêng (`ltt-code-runner`) — KHÔNG dùng chung với
    `ltt-connector-runner` của test_3500/test_4230. Bỏ qua (không FAIL) khi
    không dựng được — và khai rõ: một lượt bỏ qua KHÔNG chứng minh ranh giới
    còn đúng, nó chỉ nói là chưa đo được."""
    from platform_core.workflow import code_sandbox, vo_boc
    try:
        code_sandbox.chuan_bi_vo_code()
    except Exception as loi:  # noqa: BLE001
        pytest.skip(f"khong dung duoc vo code: {loi}")
    yield code_sandbox.TEN_VO_CODE
    try:
        code_sandbox.go_vo_code()
    except Exception:  # noqa: BLE001
        pass
    vo_boc.xoa_vo(code_sandbox.TEN_VO_CODE)


# ── D1: đọc tệp ngoài vỏ ────────────────────────────────────────────────────

@CAN_WINDOWS
def test_D1_doc_tep_ngoai_vo_BI_CHAN(vo):
    d = pathlib.Path(tempfile.mkdtemp(prefix="p-d-fs-"))
    bi_mat = d / "bi_mat.txt"
    # ⛔ Tệp GIẢ, KHÔNG phải `C:\LTTPlatform\secrets\...` thật — máy này LÀ
    #    production (`Test-Path C:\LTTPlatform` = True) và CLAUDE.md cấm đọc
    #    bí mật thật, kể cả để CHỨNG MINH nó bị chặn.
    bi_mat.write_text("KHONG_PHAI_BI_MAT_THAT_day_la_moi_gia_cho_test",
                      encoding="utf-8")
    try:
        _, ra, _ = _chay_tho_vo_code(vo, "doc_tep_ngoai_vo", {"duong": str(bi_mat)})
        assert ra is not None and ra.get("ok"), ra
        out = ra["output"]
        assert out["doc_duoc"] is False, f"⛔ VO CODE DOC DUOC TEP NGOAI VO: {out}"
        assert out["loi"] in ("EPERM", "EACCES"), out
    finally:
        shutil.rmtree(d, ignore_errors=True)


@CAN_WINDOWS
def test_D1_TIEM_LOI_cap_ACL_thi_doc_duoc(vo):
    """Đối chứng mạnh nhất: CÙNG vỏ, CÙNG tệp, chỉ khác ACL. Không có phép
    này, `test_D1_...BI_CHAN` không phân biệt được "vỏ chặn đúng" với "vỏ
    hỏng, không chạy được gì" — hoặc tệ hơn, "đường dẫn gõ sai"."""
    from platform_core.workflow import vo_boc
    d = pathlib.Path(tempfile.mkdtemp(prefix="p-d-fs-acl-"))
    bi_mat = d / "bi_mat.txt"
    bi_mat.write_text("noi_dung_doi_chung", encoding="utf-8")
    sid = vo_boc.sid_cua_vo(vo)
    vo_boc.cap_acl(str(d), sid, "(OI)(CI)(RX)")
    try:
        _, ra, _ = _chay_tho_vo_code(vo, "doc_tep_ngoai_vo", {"duong": str(bi_mat)})
        assert ra is not None and ra.get("ok"), ra
        out = ra["output"]
        assert out["doc_duoc"] is True, (
            f"cap ACL roi van khong doc duoc -> phep D1 co the dang do NHAM "
            f"thu, khong phai ranh gioi: {out}")
        assert out["noi_dung"] == "noi_dung_doi_chung"
    finally:
        vo_boc.go_acl(str(d), sid)
        shutil.rmtree(d, ignore_errors=True)


# ── D2: ghi tệp ngoài vỏ ────────────────────────────────────────────────────

@CAN_WINDOWS
def test_D2_ghi_tep_ngoai_vo_BI_CHAN(vo):
    d = pathlib.Path(tempfile.mkdtemp(prefix="p-d-fs-w-"))
    dich = d / "moi.txt"
    try:
        _, ra, _ = _chay_tho_vo_code(
            vo, "ghi_tep_ngoai_vo", {"duong": str(dich), "noi_dung": "tu code"})
        assert ra is not None and ra.get("ok"), ra
        out = ra["output"]
        assert out["ghi_duoc"] is False, f"⛔ VO CODE GHI DUOC RA NGOAI VO: {out}"
        assert out["loi"] in ("EPERM", "EACCES"), out
        assert not dich.exists(), "tep DA duoc tao du output bao ghi_duoc=False"
    finally:
        shutil.rmtree(d, ignore_errors=True)


@CAN_WINDOWS
def test_D2_TIEM_LOI_cap_ACL_Modify_thi_ghi_duoc(vo):
    from platform_core.workflow import vo_boc
    d = pathlib.Path(tempfile.mkdtemp(prefix="p-d-fs-w-acl-"))
    dich = d / "moi.txt"
    sid = vo_boc.sid_cua_vo(vo)
    vo_boc.cap_acl(str(d), sid, "(OI)(CI)(M)")
    try:
        _, ra, _ = _chay_tho_vo_code(
            vo, "ghi_tep_ngoai_vo", {"duong": str(dich), "noi_dung": "tu code"})
        assert ra is not None and ra.get("ok"), ra
        assert ra["output"]["ghi_duoc"] is True, ra["output"]
        assert dich.read_text(encoding="utf-8") == "tu code"
    finally:
        vo_boc.go_acl(str(d), sid)
        shutil.rmtree(d, ignore_errors=True)


# ── D3: kết nối mạng trực tiếp (không qua proxy) ────────────────────────────

@CAN_WINDOWS
def test_D3_ket_noi_truc_tiep_khong_qua_proxy_BI_CHAN(vo):
    """`thoat_truc_tiep` gọi `require('https').get()` NGAY TRONG tiến trình
    — không spawn con, không proxy nào được cấu hình (đúng tư thế `core.code`
    thật). Nếu điều này REACHED thì AppContainer không chặn gì cả."""
    _, ra, _ = _chay_tho_vo_code(vo, "thoat_truc_tiep", {"url": "https://example.com/"})
    assert ra is not None and ra.get("ok"), ra
    kq = ra["output"]["ket_qua"]
    assert kq.startswith("BLOCKED"), f"⛔ THOAT DUOC RA INTERNET TRUC TIEP: {kq}"


@CAN_WINDOWS
def test_D3_TIEM_LOI_them_cap_internetClient_thi_REACHED(vo):
    """Đối chứng mạnh nhất: CÙNG container, CÙNG hành động, khác ĐÚNG MỘT
    capability."""
    _, ra, _ = _chay_tho_vo_code(
        vo, "thoat_truc_tiep", {"url": "https://example.com/"},
        caps=("internetClient",))
    assert ra is not None and ra.get("ok"), ra
    kq = ra["output"]["ket_qua"]
    if not kq.startswith("REACHED"):
        pytest.skip(f"doi chung khong ra duoc Internet (may khong co mang?): {kq}")
    assert kq.startswith("REACHED"), kq


# ── D4: gọi một miền NGOÀI danh sách cho phép qua proxy ─────────────────────
#
# ⭐ `core.code` không có proxy nào (D3 đã đo AppContainer chặn thẳng). Đường
#    này chỉ có Ý NGHĨA nếu một phase sau cho code một allowlist hạn chế (vd
#    gọi webhook nội bộ) — kiểm THÀNH PHẦN `proxy_egress` trực tiếp, không
#    cần vỏ: đây là phần "miền ngoài allowlist" brief yêu cầu, đo Ở MỨC sẽ
#    dùng nếu/khi tính năng đó mở, và đo luôn tư thế MẶC ĐỊNH của code hôm
#    nay (allowlist RỖNG — fail-closed, xem đối chứng thứ hai).

def _connect_qua_proxy(dang_chay, dich: str) -> tuple:
    """Gửi MỘT yêu cầu `CONNECT dich` qua `dang_chay` (proxy_egress.DangChay).
    Trả `(ma_trang_thai, dong_dau)`."""
    import base64
    import socket

    s = socket.create_connection(("127.0.0.1", dang_chay.cong), timeout=5)
    try:
        ve_b64 = base64.b64encode(f"ltt:{dang_chay.ve}".encode()).decode()
        yc = (f"CONNECT {dich} HTTP/1.1\r\nProxy-Authorization: Basic {ve_b64}\r\n"
              f"\r\n")
        s.sendall(yc.encode("latin-1"))
        s.settimeout(5)
        dau = s.recv(4096)
        dong_dau = dau.split(b"\r\n", 1)[0].decode("latin-1")
        ma = int(dong_dau.split(" ", 2)[1])
        return ma, dong_dau
    finally:
        s.close()


def test_D4_mien_NGOAI_allowlist_BI_CHAN_qua_proxy():
    from platform_core.workflow import proxy_egress
    dang_chay = proxy_egress.mo(("api.noi-bo-gia.test",))
    try:
        ma, dong = _connect_qua_proxy(dang_chay, "evil.ke-tan-cong.test:443")
        assert ma == 403, f"⛔ MIEN NGOAI ALLOWLIST DUOC CHO QUA: {dong}"
    finally:
        dang_chay.dung()


def test_D4_TIEM_LOI_mien_TRONG_allowlist_thi_duoc_CONNECT():
    """Không có phép này, `test_D4_...BI_CHAN` có thể xanh vì proxy chặn
    MỌI THỨ (kể cả miền hợp lệ) — một cách chặn vô dụng."""
    from platform_core.workflow import proxy_egress
    dang_chay = proxy_egress.mo(("example.com",))
    try:
        ma, dong = _connect_qua_proxy(dang_chay, "example.com:443")
        assert ma == 200, (
            f"mien HOP LE bi tu choi -> proxy co the dang chan vo dieu kien, "
            f"khong phai loc theo allowlist: {dong}")
    finally:
        dang_chay.dung()


def test_D4_TIEM_LOI_allowlist_RONG_chan_ca_mien_hop_le():
    """Tư thế THẬT của `core.code` hôm nay: allowlist rỗng (`code_sandbox.chay`
    không mở proxy — nhưng NẾU nó có mở một `proxy_egress` rỗng, đây là kết
    quả bắt buộc). Fail **closed**: rỗng ⇒ chặn hết, không phải tự do."""
    from platform_core.workflow import proxy_egress
    dang_chay = proxy_egress.mo(())
    try:
        ma, dong = _connect_qua_proxy(dang_chay, "example.com:443")
        assert ma == 403, f"⛔ ALLOWLIST RONG MA VAN CHO MOT MIEN DI QUA: {dong}"
    finally:
        dang_chay.dung()


# ── D5: sinh tiến trình con ──────────────────────────────────────────────────

@CAN_WINDOWS
def test_D5_spawn_con_BI_CHAN(vo):
    """Bản sao của phép nghiệm thu `test_3500` — chạy LẠI cho vỏ `ltt-code-
    runner` (hồ sơ AppContainer KHÁC `ltt-connector-runner`). ⛔ Không giả
    định hai hồ sơ hành xử giống nhau chỉ vì cùng code: đo lại, có đối chứng
    riêng."""
    _, _, log = _chay_tho_vo_code(
        vo, "thoat_bang_tien_trinh_con", {"url": "https://example.com/"})
    assert "CHILD_REACHED" not in log, f"⛔ CON THOAT RA DUOC: {log[:300]!r}"
    assert "CHILD_BLOCKED" in log, f"khong do duoc gi: {log[:300]!r}"


@CAN_WINDOWS
def test_D5_TIEM_LOI_them_cap_internetClient_thi_CHILD_REACHED(vo):
    _, _, log = _chay_tho_vo_code(
        vo, "thoat_bang_tien_trinh_con", {"url": "https://example.com/"},
        caps=("internetClient",))
    if "CHILD_REACHED" not in log:
        pytest.skip(f"doi chung khong ra duoc Internet: {log[:200]!r}")
    assert "CHILD_REACHED" in log


# ── D6: đọc biến môi trường mang bí mật ──────────────────────────────────────

_TU_KHOA_BI_MAT = ("SECRET", "TOKEN", "PASSWORD", "KEY", "DSN", "DATABASE")


def _co_ve_bi_mat(moi: dict) -> list:
    return [k for k in moi if any(x in k.upper() for x in _TU_KHOA_BI_MAT)]


@CAN_WINDOWS
def test_D6_doc_env_bi_mat_RONG(vo):
    """`doc_env_bi_mat` trả THẲNG `process.env` của tiến trình trong vỏ,
    không lọc gì — nếu môi trường sạch, không có gì để lọc."""
    _, ra, _ = _chay_tho_vo_code(vo, "doc_env_bi_mat", {})
    assert ra is not None and ra.get("ok"), ra
    moi = ra["output"]
    xau = _co_ve_bi_mat(moi)
    assert not xau, f"⛔ MOI TRUONG TRONG VO CO BIEN TRONG BI MAT: {xau}"
    assert len(moi) <= 12, f"moi truong qua rong so voi moi_truong_toi_thieu: {sorted(moi)}"


@CAN_WINDOWS
def test_D6_TIEM_LOI_bien_gia_co_chu_SECRET_thi_HIEN_RA(vo):
    """Chứng minh `test_D6_...RONG` KHÔNG vô dụng: nếu một chỗ ghép môi
    trường sau này lỡ đưa một biến "bí mật" vào (vd `moi_truong_them` của
    `code_sandbox.chay` mang nhầm một ref credential), phép trên phải BẮT
    được nó. Đây là mô phỏng chính xác tình huống đó."""
    _, ra, _ = _chay_tho_vo_code(
        vo, "doc_env_bi_mat", {},
        moi_truong_them={"LTT_SECRET_DECOY": "sk-gia-nhung-giong-that"})
    assert ra is not None and ra.get("ok"), ra
    moi = ra["output"]
    assert moi.get("LTT_SECRET_DECOY") == "sk-gia-nhung-giong-that", (
        "co che tiem bien khong hoat dong nhu ky vong -> phep D6 chinh co "
        "the dang khong do duoc gi")
    xau = _co_ve_bi_mat(moi)
    assert "LTT_SECRET_DECOY" in xau, (
        f"⛔ BO LOC KHONG BAT DUOC BIEN GIA — test_D6_RONG co the dang xanh "
        f"GIA: {xau}")


# ── D7: ăn hết bộ nhớ / treo CPU vô hạn ──────────────────────────────────────

@CAN_WINDOWS
def test_D7_an_bo_nho_BI_CHAN_boi_job_object(vo):
    """Ở tầng TIẾN TRÌNH NGOÀI (không qua isolate — coi như isolated-vm đã bị
    vượt qua). `job_object.py` (`ProcessMemoryLimit` 512 MB) phải chặn trước
    khi tiến trình chạm 2 GiB nó cố cấp phát."""
    from platform_core.workflow import job_object
    kq, ra, _ = _chay_tho_vo_code(vo, "an_het_bo_nho", {}, han_ms=20_000)
    dinh = kq.so_lieu.get("dinh_bo_nho_job_byte", 0)
    tran = job_object.BO_NHO_MAC_DINH_MB * 1024 * 1024
    # ⭐ Phep TIEM LOI la CHINH con SO nay: neu khong co JobObjectExtendedLimit
    #    (JOB_OBJECT_LIMIT_PROCESS_MEMORY), tien trinh se cap phat het 2 GiB
    #    ma khong bi chan — dinh se >> tran. So sanh voi tran la du, khong can
    #    tai hien ban khong-co-tran (thay doi tran san xuat qua rui ro tren
    #    may nay).
    assert 0 < dinh <= tran * 1.15, (
        f"⛔ DINH BO NHO ({dinh} byte) VUOT XA TRAN JOB ({tran} byte) — "
        f"ProcessMemoryLimit co the khong con hieu luc")
    assert ra is None or ra.get("ok") is False, (
        "action bao thanh cong du no co du dinh cap phat 2 GiB")


@CAN_WINDOWS
def test_D7_vong_lap_cpu_vo_han_bi_CAT_boi_han_gio_TROI(vo):
    """Job Object CỐ Ý không dùng `JOB_OBJECT_LIMIT_JOB_TIME` (đếm CPU-thời-
    gian-người-dùng, không bắt được một job đang CHỜ I/O) — hạn thật là hạn
    giờ TRÔI của `vo_boc.chay`. Đo con số: han 3 s thì phải bị giết TRONG một
    khoảng hợp lý quanh 3 s, không phải chạy tự do."""
    import time
    t0 = time.monotonic()
    kq, _, _ = _chay_tho_vo_code(vo, "vong_lap_cpu_vo_han", {}, han_ms=3_000)
    dt = time.monotonic() - t0
    assert kq.het_gio is True, "vong lap CPU vo han khong bi giet"
    assert dt < 15, (
        f"⛔ mat {dt}s de giet mot han 3s — han gio TROI co the khong con "
        f"hieu luc (dang cho JOB_OBJECT_LIMIT_JOB_TIME khong bat duoc no)")
