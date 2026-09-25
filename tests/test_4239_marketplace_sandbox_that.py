"""🔴 Ranh giới THẬT của lượt CÀI marketplace: AppContainer + `--ignore-scripts`.

Khác `test_4234`/`test_4236` (điều phối, seam mô phỏng), tệp này chạy
`_thuc_thi_npm_install_that` THẬT — cùng vỏ (`ltt-connector-runner`), cùng
`vo_boc.chay`, cùng `proxy_egress` — với một piece GIẢ có script `postinstall`
CỐ Ý ghi một tệp đánh dấu (`connector_runner/test/piece-marketplace-gia`).

## Đối chứng bắt buộc (cùng luật `test_3500`, `test_4231`)

Một phép `assert not marker.exists()` sau khi cài **với** `--ignore-scripts`
không tự nó chứng minh gì — nó cũng xanh nếu toàn bộ lượt cài thất bại âm
thầm trước khi chạm tới script. Đối chứng ở đây chạy **NGOÀI vỏ** (trên máy
thật, không AppContainer) vì đo được: **BÊN TRONG** vỏ, thiếu cờ không dẫn
tới "thành công kèm mã độc chạy" mà dẫn tới TREO rồi bị giết ở hạn giờ — npm
tự `spawn` một tiến trình con để chạy script, và `spawn` đã bị chặn ở tầng
AppContainer từ trước (`vo_boc.py`, đo 24/09). Đối chứng ngoài vỏ chứng minh
kênh này **sống thật** (postinstall THẬT SỰ chạy khi thiếu cờ, ở một môi
trường không có ranh giới); phép trong vỏ (`test_THIEU_co_TRONG_vo...`) là
một quan sát phòng thủ-theo-chiều-sâu THÊM, ⛔ không phải bằng chứng
`--ignore-scripts` là thừa.

⛔ KHÔNG chạm mạng: gói được `npm pack` từ THƯ MỤC CỤC BỘ
(`connector_runner/test/piece-marketplace-gia`, mã của chính kho này, không
phải bên thứ ba) rồi cài từ đường dẫn `.tgz` cục bộ — `mien=()` cho
`proxy_egress`, đúng tư thế "không cần Internet" của một lượt cài từ tarball.

Bỏ qua (⛔ không FAIL) khi không dựng được vỏ — cùng mẫu `test_3500`: một
lượt bỏ qua KHÔNG chứng minh ranh giới còn đúng, nó chỉ nói chưa đo được.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

import pytest

CAN_WINDOWS = pytest.mark.skipif(
    sys.platform != "win32", reason="AppContainer chi co tren Windows")
CAN_NPM = pytest.mark.skipif(
    shutil.which("npm") is None, reason="npm khong co tren PATH")

GOC = pathlib.Path(__file__).resolve().parents[1]
FIXTURE = GOC / "connector_runner" / "test" / "piece-marketplace-gia"
TEN_GOI_MARKER = "POSTINSTALL_DA_CHAY.txt"


def _pack_fixture(dich_dir: pathlib.Path) -> pathlib.Path:
    """`npm pack` THUẦN CỤC BỘ (không mạng) — sinh `.tgz` từ fixture của
    chính kho này. `--ignore-scripts` phòng thủ thêm cho chính bước pack."""
    ra = subprocess.run(
        [shutil.which("npm"), "pack", "--ignore-scripts", "--silent",
         "--pack-destination", str(dich_dir)],
        cwd=str(FIXTURE), capture_output=True, text=True, timeout=30)
    assert ra.returncode == 0, f"npm pack that bai: {ra.stderr}"
    ten_tep = ra.stdout.strip().splitlines()[-1].strip()
    return dich_dir / ten_tep


@pytest.fixture(scope="module")
def vo():
    from platform_core.workflow import connector
    try:
        connector.chuan_bi_vo()
    except Exception as loi:  # noqa: BLE001
        pytest.skip(f"khong dung duoc vo AppContainer: {loi}")
    yield connector.vo_boc.TEN_VO_MAC_DINH
    try:
        connector.go_vo()
    except Exception:  # noqa: BLE001
        pass


@pytest.fixture()
def khu_lam_viec(vo):
    """Thư mục làm việc CHO lượt cài — ⛔ KHÔNG dùng `tmp_path` của pytest
    (nằm dưới `%TEMP%` của người dùng, vỏ KHÔNG có ACL ở đó). Phải nằm dưới
    `connector.THU_MUC_LAM_VIEC` — nơi `connector.chuan_bi_vo()` đã cấp
    `(OI)(CI)(M)` cho SID của vỏ, kế thừa cho MỌI thư mục con tạo sau đó.
    """
    import shutil as _sh
    import uuid as _uuid
    from platform_core.workflow import connector
    d = connector.THU_MUC_LAM_VIEC / f"t4239-{_uuid.uuid4().hex[:12]}"
    d.mkdir(parents=True)
    yield d
    _sh.rmtree(d, ignore_errors=True)


@CAN_WINDOWS
@CAN_NPM
def test_cai_that_voi_ignore_scripts_KHONG_chay_postinstall(khu_lam_viec, monkeypatch):
    from platform_core.workflow import connector, marketplace as mp
    monkeypatch.setattr(connector, "THU_MUC_MARKETPLACE", khu_lam_viec / "mkt_state")

    tgz = _pack_fixture(khu_lam_viec)
    npm_cli = mp._npm_cli_js()
    dich = khu_lam_viec / "cai-co-co"
    cache = khu_lam_viec / "npm-cache"
    argv = mp.argv_npm_install(npm_cli, "x", "0.0.1", prefix=str(dich),
                               cache=str(cache))
    # `argv_npm_install` sinh spec `x@0.0.1` (ten/ban ghim GIA cho ham thuan);
    # o day ta CAN cai tu file .tgz cuc bo, nen thay the phan tu cuoi (spec)
    # bang duong dan .tgz — moi phan con lai (gom `--ignore-scripts`) GIU
    # NGUYEN tu ham that, khong tu tay go lai danh sach co.
    argv[-1] = str(tgz)
    mp.kiem_tra_argv_an_toan(argv)

    ket = mp._thuc_thi_npm_install_that(argv, mien=())
    assert ket["ok"], ket["log"][-2000:]

    goi_dir = dich / "node_modules" / "@ltt" / "piece-marketplace-gia"
    assert (goi_dir / "package.json").exists(), (
        f"cai bao ok nhung khong thay package.json — log: {ket['log'][-500:]!r}")
    marker = goi_dir / TEN_GOI_MARKER
    assert not marker.exists(), (
        "🔴 --ignore-scripts KHONG chan duoc postinstall — day la mot RCE "
        "chuoi cung ung con mo, khong phai mot chi tiet nho")


@CAN_NPM
def test_DOI_CHUNG_NGOAI_vo_thieu_co_thi_postinstall_THAT_SU_chay(tmp_path):
    """🔴 Đối chứng BẮT BUỘC cho phép ở trên — cùng luật `test_3500`: một
    `assert not marker.exists()` không tự nó chứng minh gì; nó cũng xanh nếu
    cả lượt cài thất bại vì lý do khác (mạng, tên gói sai...). Đối chứng này
    chạy CÙNG gói, CÙNG argv (trừ `--ignore-scripts`) nhưng NGOÀI vỏ — trên
    máy thật, không qua AppContainer — để chứng minh postinstall THẬT SỰ
    chạy khi không có cờ: kênh này SỐNG, phép "bị chặn" ở trên đo đúng thứ.
    """
    tgz = _pack_fixture(tmp_path)
    npm_cli = shutil.which("npm-cli.js") or str(
        pathlib.Path(shutil.which("npm")).resolve().parent
        / "node_modules" / "npm" / "bin" / "npm-cli.js")
    dich = tmp_path / "cai-ngoai-vo"
    cache = tmp_path / "npm-cache"
    argv = [shutil.which("node"), npm_cli, "install", "--no-audit", "--no-fund",
           "--no-update-notifier", "--prefix", str(dich), "--cache", str(cache),
           "--", str(tgz)]  # ⛔ KHONG --ignore-scripts — chinh doi chung
    ra = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    assert ra.returncode == 0, f"npm install (ngoai vo) that bai: {ra.stderr}"
    marker = dich / "node_modules" / "@ltt" / "piece-marketplace-gia" / TEN_GOI_MARKER
    assert marker.exists(), (
        "doi chung hong: thieu --ignore-scripts NGOAI vo ma postinstall van "
        "khong chay -- kenh nay chet, phep 'bi chan' o tren khong noi len "
        "duoc gi")


@CAN_WINDOWS
@CAN_NPM
def test_THIEU_co_TRONG_vo_khong_hoan_thanh_duoc_du_khong_co_co(khu_lam_viec, monkeypatch):
    """Quan sát PHÒNG THỦ THEO CHIỀU SÂU, ⛔ không phải phép quyết định.

    Đo được: BÊN TRONG vỏ, thiếu `--ignore-scripts` không dẫn tới một lượt
    cài "thành công kèm mã độc chạy được" — nó dẫn tới TREO rồi bị giết ở hạn
    giờ, vì `npm` tự spawn một tiến trình con (`node postinstall.js`) để chạy
    script, và `vo_boc.py` đã tài liệu hoá: "piece không chạy được tiến trình
    con" + "ống treo cứng trong vỏ" (docstring module đó). Hai lớp — hàng rào
    argv (`kiem_tra_argv_an_toan`, nhanh, xác định) và ranh giới AppContainer
    (chậm, phá huỷ theo kiểu treo-rồi-giết) — không cùng MỘT điểm hỏng.
    ⛔ Không suy ra từ đây rằng thiếu cờ là AN TOÀN: một `postinstall` không
    cần spawn (chạy thuần bằng `require()` nội tuyến trong tiến trình npm)
    vẫn có thể chạy được mà không cần spawn — hàng rào argv vẫn là lớp BẮT
    BUỘC, lớp này chỉ là một lớp phụ may mắn có được từ ranh giới khác.
    """
    from platform_core.workflow import connector, marketplace as mp
    monkeypatch.setattr(connector, "THU_MUC_MARKETPLACE", khu_lam_viec / "mkt_state")

    tgz = _pack_fixture(khu_lam_viec)
    npm_cli = mp._npm_cli_js()
    dich = khu_lam_viec / "cai-thieu-co"
    cache = khu_lam_viec / "npm-cache"
    argv = mp.argv_npm_install(npm_cli, "x", "0.0.1", prefix=str(dich),
                               cache=str(cache))
    argv[-1] = str(tgz)
    argv = [a for a in argv if a != "--ignore-scripts"]  # TIEM LOI co y

    ket = mp._thuc_thi_npm_install_that(argv, mien=())
    marker = dich / "node_modules" / "@ltt" / "piece-marketplace-gia" / TEN_GOI_MARKER
    assert not ket["ok"], (
        "bat ngo: npm install THIEU --ignore-scripts lai bao thanh cong "
        "BEN TRONG vo — can dieu tra lai gia thuyet 'spawn con bi chan'")
    assert not marker.exists()
