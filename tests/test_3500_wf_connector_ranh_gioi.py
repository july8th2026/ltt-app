"""🔴 RANH GIỚI EGRESS của runner connector — phép NGHIỆM THU của cả phase P6.

## Câu hỏi tệp này trả lời

*Một piece **cố ý** thoát ra Internet có thoát được không?* ⛔ Không phải câu
*"một piece viết ẩu có bị chặn không"* — câu đó đã có `chan_trong_tien_trinh.js`
trả lời, và nó **không phải** một ranh giới an ninh.

## Vì sao phép quyết định là `spawn` một tiến trình con

Đo hai lần ở hai spike (`docs/superpowers/reports/p6-egress/`, `p6b-ranh-gioi-os/`):

    node -r preload-socket-only.js piece-https.js          -> EGRESS_BLOCKED
    node -r preload-socket-only.js piece-child-process.js  -> CHILD_REACHED 200

`-r <preload>` là cờ của **tiến trình đó**; nó không đi theo `spawn`. Mọi lớp
vá trong tiến trình đều bị đi vòng bằng đúng bốn dòng JavaScript. Đội
Activepieces nói cùng điều trong `activepieces#11547`, dẫn CVE-2025-68668
(n8n, Pyodide sandbox escape, CVSS 9.9).

⇒ Phép kiểm chạy **bản sao logic ấy bên trong runner thật** (piece giả
`thoat_bang_tien_trinh_con`), và nó **phải bị chặn**.

## ⛔ Không có phép nào ở đây được xanh nhờ VẮNG MẶT

Mọi phép chạm vỏ đều đi kèm **đối chứng**:

- `thoat_bang_tien_trinh_con` chạy **ngoài** vỏ phải `CHILD_REACHED 200`. Thiếu
  đối chứng này thì một lần mất mạng, một tường lửa công ty, hay một tệp piece
  gõ sai tên cũng cho ra "BLOCKED" — và ta sẽ ăn mừng một phép đo rỗng.
- Cùng vỏ, **thêm** capability `internetClient` phải `REACHED 200`. Đây là đối
  chứng mạnh nhất: cùng container, cùng ACL, cùng tiến trình, **khác đúng một
  capability**.

⚠️ **IPv6: CHƯA BIẾT, ⛔ không phải "đã chặn".** Máy A không có địa chỉ IPv6
   toàn cục và không có route `::/0`, nên **đối chứng cũng hỏng** — kênh đó
   chưa nói được gì về bất cứ hướng nào. Muốn phủ phải đo trên máy có IPv6.
   ⛔ Không có phép kiểm IPv6 ở đây, và sự vắng mặt ấy là **cố ý**: một phép
   `assert BLOCKED` trên một kênh chết là một phép luôn xanh.
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

import pytest

CAN_WINDOWS = pytest.mark.skipif(
    sys.platform != "win32", reason="AppContainer chi co tren Windows")

GOC = pathlib.Path(__file__).resolve().parents[1]
TEN_VO = "ltt-conn-test-3500"


# ── Lớp thuần: so khớp miền ────────────────────────────────────────────────
#
# ⭐ Không cần vỏ, không cần mạng — và vì thế nó luôn chạy, kể cả trên máy
#    không phải Windows. Nó giữ đúng MỘT luật, và luật đó là chỗ một proxy lọc
#    miền hay bị thủng.

def test_khop_mien_theo_NHAN_chu_khong_phai_chuoi_con():
    """`slack.com.ke-tan-cong.vn` ⛔ KHÔNG được khớp `slack.com`.

    🔴 Đây là toàn bộ giá trị của `_khop_mien`. Một `"slack.com" in host` hay
       `host.endswith("slack.com")` trả **True** cho chuỗi trên — tức mở proxy
       cho một miền do kẻ tấn công đăng ký.
    """
    from platform_core.workflow.proxy_egress import _khop_mien
    cho_phep = ("slack.com", "api.github.com")

    assert _khop_mien("slack.com", cho_phep)
    assert _khop_mien("files.slack.com", cho_phep)
    assert _khop_mien("SLACK.COM.", cho_phep)          # hoa + dấu chấm cuối
    # ⛔ Ba dạng tấn công, cả ba phải False.
    assert not _khop_mien("slack.com.ke-tan-cong.vn", cho_phep)
    assert not _khop_mien("xxslack.com", cho_phep)
    assert not _khop_mien("api.github.com.evil.net", cho_phep)


def test_doi_chung_phep_kiem_tren_PHAN_BIET_DUOC():
    """Tiêm lại lỗi cũ: `endswith` trần **phải** cho kết quả khác.

    Không có phép này, `test_khop_mien_...` có thể xanh vì mọi thứ đều False.
    """
    tan_cong = "slack.com.ke-tan-cong.vn"
    assert tan_cong.endswith("slack.com") is False
    assert "slack.com" in tan_cong        # <- `in` trần THỦNG, và đó là điểm


def test_mien_cua_piece_KHONG_khai_thi_RONG_khong_phai_tu_do():
    """Fail **closed**: piece không có mục `mien` ⇒ không được nối đi đâu."""
    from platform_core.workflow import connector
    assert connector.mien_cua_piece("@activepieces/piece-khong-ton-tai") == ()
    assert "slack.com" in connector.mien_cua_piece("@activepieces/piece-slack")


# ── Vỏ thật ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def vo():
    """Vỏ + ACL + miễn trừ loopback. Gỡ sạch ở cuối module.

    Bỏ qua (⛔ không FAIL) khi không dựng được vỏ — ví dụ phiên không có quyền
    quản trị. ⚠️ Và **khai ra**: một lượt bỏ qua **không** chứng minh ranh giới
    còn đúng; nó chỉ nói là chưa đo. Đó là lý do `--reason` nói rõ nguyên nhân
    thay vì im lặng skip.
    """
    from platform_core.workflow import connector, vo_boc
    try:
        connector.chuan_bi_vo(TEN_VO)
    except Exception as loi:  # noqa: BLE001
        pytest.skip(f"khong dung duoc vo AppContainer: {loi}")
    yield TEN_VO
    try:
        connector.go_vo(TEN_VO)
    except Exception:  # noqa: BLE001
        pass
    vo_boc.xoa_vo(TEN_VO)


def _chay_trong_vo(ten_action, props=None, caps=()):
    from platform_core.workflow import connector
    return connector.chay(
        "run_action", piece="@ltt/piece-gia", version="0.0.0",
        name=ten_action, props=props or {}, auth=None, han_ms=40_000,
        ten_vo=TEN_VO, moi_truong_them={"LTT_TEST": "1"}, giu_tmp=True)


def _log_cuoi():
    """stdout/stderr THẬT của tiến trình trong vỏ (nơi tiến trình CON in ra).

    ⭐ Phải đọc từ đây chứ không từ `KetQua.output`: tiến trình con ghi thẳng
       vào đầu ra đã kế thừa (`stdio: 'inherit'`), nên dòng
       `CHILD_REACHED`/`CHILD_BLOCKED` **không** đi qua giao thức JSON.
    """
    from platform_core.workflow import connector
    thu_muc = sorted(connector.THU_MUC_LAM_VIEC.glob("j-*"),
                     key=lambda p: p.stat().st_mtime)
    if not thu_muc:
        return ""
    return (thu_muc[-1] / "log.txt").read_text(encoding="utf-8",
                                               errors="replace")


def _don_tmp():
    from platform_core.workflow import connector
    for d in connector.THU_MUC_LAM_VIEC.glob("j-*"):
        shutil.rmtree(d, ignore_errors=True)


@CAN_WINDOWS
def test_DOI_CHUNG_ngoai_vo_tien_trinh_con_RA_DUOC_Internet():
    """⛔ Phép này phải chạy TRƯỚC khi tin bất cứ "BLOCKED" nào.

    Nó chạy **cùng một runner, cùng một piece**, chỉ khác là không có vỏ. Nếu
    nó không `CHILD_REACHED` thì máy đang không có Internet, và mọi phép
    "BLOCKED" phía dưới là phép đo rỗng.
    """
    d = pathlib.Path(tempfile.mkdtemp(prefix="p6c-doi-chung-"))
    try:
        (d / "vao.json").write_text(json.dumps({
            "op": "run_action", "piece": "@ltt/piece-gia", "version": "0.0.0",
            "name": "thoat_bang_tien_trinh_con",
            "props": {"url": "https://example.com/"}, "auth": None,
            "store": {}, "tmp_dir": str(d), "han_ms": 40_000}),
            encoding="utf-8")
        moi = dict(os.environ)
        moi["LTT_TEST"] = "1"
        r = subprocess.run(
            ["node", str(GOC / "connector_runner" / "src" / "runner.js"),
             str(d / "vao.json"), str(d / "ra.json")],
            capture_output=True, text=True, timeout=120, env=moi, cwd=str(GOC))
        if r.returncode != 0 and not (d / "ra.json").exists():
            pytest.skip(f"khong chay duoc runner ngoai vo: {r.stderr[:200]}")
        assert "CHILD_REACHED" in r.stdout, (
            "doi chung HONG: tien trinh con NGOAI vo cung khong ra duoc "
            f"Internet => moi phep BLOCKED phia duoi la phep do rong. "
            f"stdout={r.stdout[:300]!r}")
    finally:
        shutil.rmtree(d, ignore_errors=True)


@CAN_WINDOWS
def test_TRONG_vo_tien_trinh_con_BI_CHAN(vo):
    """🔴 Phép nghiệm thu. Đây là dòng `CHILD_REACHED 200` đã làm sập spike P6.

    Piece đã **gỡ sạch** biến proxy trước khi `spawn` — tức nó cố ý đi vòng qua
    cả proxy lọc miền của ta. Cái còn chặn được nó chỉ có thể là AppContainer.
    """
    _don_tmp()
    kq = _chay_trong_vo("thoat_bang_tien_trinh_con",
                        {"url": "https://example.com/"})
    log = _log_cuoi()
    _don_tmp()
    assert "CHILD_REACHED" not in log, f"⛔ PIECE THOAT RA DUOC: {log[:400]!r}"
    assert "CHILD_BLOCKED" in log, (
        "khong thay dong nao cua tien trinh con — phep kiem khong do duoc gi. "
        f"ok={kq.ok} log={log[:400]!r}")


@CAN_WINDOWS
def test_TRONG_vo_tien_trinh_con_bi_chan_ca_khi_dung_IP_TRAN(vo):
    """Tên miền bị chặn ⇒ có thể chỉ là DNS. Đo thêm bằng **IP trần**.

    ⚠️ Đối chứng của phép này KHÔNG hoàn hảo và điều đó được khai ra: ngoài vỏ,
       một `https://<ip>/` tới Cloudflare trả `EPROTO` (bắt tay TLS không khớp
       SNI) chứ không phải 200. Nên phép so là theo **hạng lỗi**: trong vỏ phải
       là lỗi ở tầng **socket** (`EACCES`/`ETIMEDOUT`/`ENETUNREACH`), ⛔ không
       phải một lỗi TLS — lỗi TLS nghĩa là đã nối được.
    """
    import socket
    try:
        ip = socket.gethostbyname("example.com")
    except OSError:
        pytest.skip("khong phan giai duoc example.com (may khong co mang)")
    _don_tmp()
    _chay_trong_vo("thoat_bang_tien_trinh_con", {"url": f"https://{ip}/"})
    log = _log_cuoi()
    _don_tmp()
    assert "CHILD_REACHED" not in log, f"⛔ THOAT BANG IP TRAN: {log[:300]!r}"
    assert any(m in log for m in ("EACCES", "ETIMEDOUT", "ENETUNREACH")), (
        f"loi khong nam o tang socket => co the da noi duoc: {log[:300]!r}")


@CAN_WINDOWS
def test_DOI_CHUNG_cung_vo_THEM_internetClient_thi_RA_DUOC(vo):
    """Đối chứng mạnh nhất: cùng container, khác **đúng một** capability.

    Không có phép này, ba phép BLOCKED ở trên không phân biệt được *"vỏ chặn
    mạng"* với *"vỏ hỏng, tiến trình chẳng chạy gì"*.
    """
    from platform_core.workflow import vo_boc
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="p6c-cap-"))
    js = tmp / "probe.js"
    js.write_text(
        "require('https').get('https://example.com/',r=>{"
        "process.stdout.write('REACHED '+r.statusCode);process.exit(0);})"
        ".on('error',e=>{process.stdout.write('BLOCKED '+(e.code||e.message));"
        "process.exit(0);});", encoding="utf-8")
    from platform_core.workflow import connector
    node = connector.THU_MUC_LAM_VIEC / "node.exe"
    sid = vo_boc.sid_cua_vo(vo)
    vo_boc.cap_acl(str(tmp), sid, "(OI)(CI)(RX)")
    try:
        ra = tmp / "log.txt"
        vo_boc.chay([str(node), "--preserve-symlinks", "--preserve-symlinks-main", str(js)],
                    ra_log=str(ra), ten_vo=vo, caps=("internetClient",),
                    moi_truong=vo_boc.moi_truong_toi_thieu(),
                    han_ms=30_000, thu_muc=str(tmp))
        co_cap = ra.read_text(encoding="utf-8", errors="replace")
        vo_boc.chay([str(node), "--preserve-symlinks", "--preserve-symlinks-main", str(js)],
                    ra_log=str(ra), ten_vo=vo, caps=(),
                    moi_truong=vo_boc.moi_truong_toi_thieu(),
                    han_ms=30_000, thu_muc=str(tmp))
        khong_cap = ra.read_text(encoding="utf-8", errors="replace")
    finally:
        vo_boc.go_acl(str(tmp), sid)
        shutil.rmtree(tmp, ignore_errors=True)
    if "REACHED" not in co_cap:
        pytest.skip(f"doi chung khong ra duoc Internet: {co_cap[:200]!r}")
    assert "REACHED" not in khong_cap, (
        f"⛔ vo KHONG capability van ra duoc Internet: {khong_cap[:200]!r}")


@CAN_WINDOWS
def test_capability_ngoai_danh_sach_DONG_thi_NEM(vo):
    """⛔ Một capability lạ không được lặng lẽ bỏ qua — nó phải ném."""
    from platform_core.workflow import vo_boc
    with pytest.raises(vo_boc.LoiVoBoc):
        vo_boc.chay(["cmd.exe"], ra_log="x", ten_vo=vo,
                    caps=("internetClientServer",))


@CAN_WINDOWS
def test_moi_truong_toi_thieu_KHONG_mang_bi_mat_cua_worker():
    """⛔ Runner **không** kế thừa môi trường worker (97 biến từ `app.env`).

    Mã piece là mã của bên thứ ba; cho nó môi trường của nền tảng là cho nó
    mọi bí mật của nền tảng.
    """
    from platform_core.workflow import vo_boc
    moi = vo_boc.moi_truong_toi_thieu(proxy="http://127.0.0.1:1")
    assert "LOCALAPPDATA" in moi, (
        "thieu LOCALAPPDATA => CreateProcessW cua tien trinh AppContainer tra "
        "win32=203 ERROR_ENVVAR_NOT_FOUND (do 24/09)")
    # Tập biến phải NHỎ và không chứa thứ gì trông như bí mật.
    assert len(moi) <= 12, f"moi truong qua rong: {sorted(moi)}"
    for k in moi:
        assert not any(x in k.upper() for x in
                       ("SECRET", "TOKEN", "PASSWORD", "KEY", "DSN", "DATABASE"))
