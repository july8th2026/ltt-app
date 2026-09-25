"""Marketplace piece + CỔNG DUYỆT — cài piece BÊN THỨ BA lúc chạy (plan wfm).

🔴 **Bề mặt tấn công lớn nhất của cả vòng.** Đây là chỗ mã bên thứ ba được
   tải về và chạy trên máy **production**. Bốn ràng buộc an toàn, mỗi cái có
   phép kiểm riêng (`tests/test_4233..4249`):

   a. **Không chạy script vòng đời npm** (`--ignore-scripts`) — chặn đường RCE
      chuỗi cung ứng kinh điển (`postinstall` của một gói bất kỳ chạy với
      quyền tiến trình cài).
   b. **Cổng duyệt FAIL-CLOSED** — mặc định TỪ CHỐI. Một piece chưa duyệt thì
      không cài được, không nạp được, không publish được, ở BẤT KỲ cửa nào.
   c. **Ai được cài đi qua hệ quyền ĐÃ CÓ của kho** (`User.role == "admin"`,
      `platform_core/app_access.py`) — không tự chế vai trò mới.
   d. **Nhật ký kiểm toán** — cái gì, phiên bản nào, ai duyệt, lúc nào
      (`MarketplacePieceNhatKy`, cùng hình dạng `CredentialNhatKy`).

## Vì sao KHÔNG ghi allowlist/catalog vào `connector_runner/`

`connector.THU_MUC_RUNNER` bị **thay TOÀN BỘ** mỗi lần deploy (xem docstring
`connector.py`/`code_sandbox.py`) — ghi runtime state ở đó là một piece vừa
duyệt biến mất sau bản cập nhật kế tiếp mà không ai báo. Mọi trạng thái
marketplace sống dưới `connector.THU_MUC_MARKETPLACE` (`data/marketplace/`,
mặc định — ghi đè bằng `LTT_MARKETPLACE_DIR`), thư mục sống sót qua deploy,
cùng vai trò với `data/conn` của `connector.THU_MUC_LAM_VIEC`.

## Vì sao cài chạy trong CÙNG vỏ với piece tĩnh, không phải vỏ riêng

`connector.chuan_bi_vo()` / `connector.THU_MUC_LAM_VIEC` đã có ACL + miễn trừ
loopback cho `ltt-connector-runner`. Egress mỗi lượt đã được lọc THEO LƯỢT
(`proxy_egress.mo(mien=...)`, spec `connector.py::chay`) — cài đặt chỉ là một
lượt khác với `mien=("registry.npmjs.org",)` thay vì miền của một piece. Dựng
thêm một hồ sơ AppContainer thứ hai không mua thêm ranh giới nào; nó chỉ nhân
đôi bề mặt cần ACL đúng.

## Toàn vẹn — nói rõ giới hạn, không giấu

`integrity` ghi nhận lúc GHI YÊU CẦU (`npm view <ten>@<ban_ghim> dist.integrity`,
qua chính vỏ + proxy lọc miền) được đối chiếu với `dist.integrity` mà
`package-lock.json` do CHÍNH LƯỢT CÀI đó ghi lại — bắt đúng lớp tấn công
"đăng ký metadata rồi tráo tarball giữa lúc duyệt và lúc cài" (TOCTOU đăng ký
gói). Nó KHÔNG bảo vệ khỏi một registry bị chiếm hoàn toàn và trả về NHẤT
QUÁN cùng một mã độc cho mọi truy vấn — không công cụ nào (npm, pip, cargo)
tự bảo vệ khỏi lớp đó nếu không có provenance ngoài băng tần, và tài liệu này
không giả vờ có.
"""
from __future__ import annotations

import json
import pathlib
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select

from platform_core.models import (MARKETPLACE_CHO_DUYET, MARKETPLACE_DA_CAI,
                                  MARKETPLACE_DA_DUYET, MARKETPLACE_TU_CHOI,
                                  MarketplacePiece, MarketplacePieceNhatKy,
                                  User)
from platform_core.workflow import connector, job_object, proxy_egress, vo_boc

#: Tên npm hợp lệ: scoped `@scope/name` hoặc unscoped `name`. ⛔ Cố tình HẸP
#: hơn `validate-npm-package-name` thật (Node-RED dùng bản đầy đủ) — bề mặt
#: này không cần chấp nhận mọi tên npm hợp lệ trên đời, chỉ cần chặn chắc.
_RE_TEN_UNSCOPED = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_RE_TEN_SCOPED = re.compile(r"^@[a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._-]*$")

#: Bản ghim TUYỆT ĐỐI — semver ba số, tiền tố `-prerelease` tuỳ chọn. ⛔ Không
#: `^`, `~`, `>=`, `*`, `x`, `latest`, `next` — mọi thứ KHÔNG phải một điểm cố
#: định trên trục thời gian của gói đều bị từ chối ở `_kiem_phien_ban_ghim`.
_RE_BAN_GHIM = re.compile(
    r"^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$")

#: Miền npm registry — chỉ mở đúng lúc CÀI, ⛔ không mở cho piece lúc CHẠY
#: (đó là `connector.mien_cua_piece`, một danh sách khác hẳn).
MIEN_NPM_REGISTRY = ("registry.npmjs.org",)

HAN_CAI_MS = 90_000


class LoiMarketplace(Exception):
    """Gốc lỗi marketplace. Có mã (`ma_loi`) để phân biệt phép tiêm lỗi."""

    ma_loi = "loi"


class LoiKhongDuQuyen(LoiMarketplace):
    ma_loi = "khong_du_quyen"


class LoiPhienBanKhongGhim(LoiMarketplace):
    ma_loi = "phien_ban_khong_ghim"


class LoiTenKhongHopLe(LoiMarketplace):
    ma_loi = "ten_khong_hop_le"


class LoiChuaDuyet(LoiMarketplace):
    ma_loi = "chua_duyet"


class LoiToanVenSai(LoiMarketplace):
    ma_loi = "toan_ven_sai"


class LoiCaiThatBai(LoiMarketplace):
    ma_loi = "cai_that_bai"


# ── Phép kiểm THUẦN — không I/O, dùng ở cả `yeu_cau()` lẫn `cai_dat()` ──────
#
# ⭐ Kiểm HAI LẦN cố ý: một lần lúc ghi yêu cầu (chặn sớm, đỡ tốn một vòng
#   duyệt cho một tên/bản rõ ràng sai), một lần NGAY TRƯỚC KHI CÀI (phòng một
#   hàng cũ trong CSDL từ một phiên bản code trước khi có kiểm tra này).

def _kiem_ten_hop_le(ten: str) -> None:
    ten = str(ten or "")
    if ".." in ten or not (_RE_TEN_SCOPED.match(ten) or _RE_TEN_UNSCOPED.match(ten)):
        raise LoiTenKhongHopLe(f"ten goi khong hop le: {ten!r}")


def _kiem_phien_ban_ghim(phien_ban: str) -> None:
    v = str(phien_ban or "")
    if not _RE_BAN_GHIM.match(v):
        raise LoiPhienBanKhongGhim(
            f"phien ban phai la mot ban ghim TUYET DOI (vd '1.2.3'), "
            f"khong duoc la dai/latest/rong: {v!r}")


def _can_admin(nguoi: User) -> None:
    if nguoi is None or getattr(nguoi, "role", "") != "admin":
        raise LoiKhongDuQuyen(
            "chi admin duoc duyet/tu choi/cai dat piece marketplace")


def argv_npm_install(npm_cli_js: str, ten: str, phien_ban: str, *,
                     prefix: str, cache: str) -> list:
    """Argv NPM install — hàm THUẦN, không chạy gì. Điểm duy nhất quyết định
    cờ dòng lệnh, để phép tiêm lỗi (`test_42xx`) so được "có cờ" so với
    "thiếu cờ" mà không cần chạy npm thật.
    """
    _kiem_ten_hop_le(ten)
    _kiem_phien_ban_ghim(phien_ban)
    return [
        npm_cli_js, "install",
        "--ignore-scripts",       # 🔴 RÀNG BUỘC (a) — xem docstring module.
        "--no-audit", "--no-fund", "--no-update-notifier",
        "--omit=dev", "--engine-strict",
        "--prefix", prefix, "--cache", cache,
        "--", f"{ten}@{phien_ban}",
    ]


def kiem_tra_argv_an_toan(argv: list) -> None:
    """Đối chứng cho ràng buộc (a): một argv THIẾU `--ignore-scripts` phải bị
    hàm này từ chối. `cai_dat()` gọi nó ngay trước khi thực thi — gỡ cờ khỏi
    `argv_npm_install` thì đúng phép kiểm này đỏ trước, không phải một lượt
    cài thật âm thầm chạy postinstall.
    """
    if "--ignore-scripts" not in argv:
        raise LoiCaiThatBai(
            "argv npm install THIEU --ignore-scripts — day la RCE chuoi cung "
            "ung, khong duoc chay du chi mot lan")
    if "install" not in argv:
        raise LoiCaiThatBai("argv khong phai mot lenh 'npm install'")


def _ghi_nhat_ky(db, yeu_cau_id: str, hanh_dong: str, *,
                 nguoi_id: str = "", chi_tiet=None) -> None:
    db.add(MarketplacePieceNhatKy(
        yeu_cau_id=yeu_cau_id, hanh_dong=hanh_dong, nguoi_id=nguoi_id or "",
        chi_tiet=dict(chi_tiet or {})))


# ── Vòng đời yêu cầu ─────────────────────────────────────────────────────

def yeu_cau(db, *, nguoi: User, ten: str, phien_ban: str,
           mien=()) -> MarketplacePiece:
    """Bất kỳ người dùng đã đăng nhập nào có thể YÊU CẦU một piece — mở CỔNG
    request, ⛔ không mở cổng cài (đó là `duyet()` + `cai_dat()`, admin-only).
    """
    if nguoi is None:
        raise LoiKhongDuQuyen("phai dang nhap de yeu cau piece marketplace")
    _kiem_ten_hop_le(ten)
    _kiem_phien_ban_ghim(phien_ban)
    hang = MarketplacePiece(
        ten=str(ten), phien_ban=str(phien_ban), nguoi_yeu_cau_id=nguoi.id,
        trang_thai=MARKETPLACE_CHO_DUYET, mien=list(mien or []))
    db.add(hang)
    db.flush()
    _ghi_nhat_ky(db, hang.id, "yeu_cau", nguoi_id=nguoi.id,
                chi_tiet={"ten": hang.ten, "phien_ban": hang.phien_ban})
    return hang


def _lay(db, yeu_cau_id: str) -> MarketplacePiece:
    hang = db.get(MarketplacePiece, yeu_cau_id)
    if hang is None:
        raise LoiMarketplace(f"khong tim thay yeu cau marketplace: {yeu_cau_id}")
    return hang


def duyet(db, *, yeu_cau_id: str, nguoi: User) -> MarketplacePiece:
    """🔴 RÀNG BUỘC (c): admin-only. Chỉ chuyển `cho_duyet -> da_duyet` — CHƯA
    cài gì (`cai_dat()` là một bước riêng, có thể chạy sau nhiều giờ)."""
    _can_admin(nguoi)
    hang = _lay(db, yeu_cau_id)
    if hang.trang_thai != MARKETPLACE_CHO_DUYET:
        raise LoiMarketplace(
            f"chi duyet duoc yeu cau dang cho_duyet, hang nay dang "
            f"{hang.trang_thai!r}")
    hang.trang_thai = MARKETPLACE_DA_DUYET
    hang.nguoi_duyet_id = nguoi.id
    hang.quyet_dinh_luc = datetime.now(timezone.utc)
    db.flush()
    _ghi_nhat_ky(db, hang.id, "duyet", nguoi_id=nguoi.id)
    return hang


def tu_choi(db, *, yeu_cau_id: str, nguoi: User, ly_do: str = "") -> MarketplacePiece:
    """Admin-only. `cho_duyet -> tu_choi`."""
    _can_admin(nguoi)
    hang = _lay(db, yeu_cau_id)
    if hang.trang_thai != MARKETPLACE_CHO_DUYET:
        raise LoiMarketplace(
            f"chi tu choi duoc yeu cau dang cho_duyet, hang nay dang "
            f"{hang.trang_thai!r}")
    hang.trang_thai = MARKETPLACE_TU_CHOI
    hang.nguoi_duyet_id = nguoi.id
    hang.ly_do_tu_choi = str(ly_do or "")
    hang.quyet_dinh_luc = datetime.now(timezone.utc)
    db.flush()
    _ghi_nhat_ky(db, hang.id, "tu_choi", nguoi_id=nguoi.id,
                chi_tiet={"ly_do": hang.ly_do_tu_choi})
    return hang


def thu_hoi(db, *, yeu_cau_id: str, nguoi: User, ly_do: str = "") -> MarketplacePiece:
    """Admin-only. Thu hồi một piece ĐÃ DUYỆT/ĐÃ CÀI — quay về `tu_choi` VÀ
    xoá ngay khỏi allowlist marketplace (fail closed cho lượt NẠP kế tiếp:
    một piece bị thu hồi giữa chừng không được tiếp tục nạp được nữa, kể cả
    khi bản đã cài còn nằm nguyên trên đĩa).
    """
    _can_admin(nguoi)
    hang = _lay(db, yeu_cau_id)
    if hang.trang_thai not in (MARKETPLACE_DA_DUYET, MARKETPLACE_DA_CAI):
        raise LoiMarketplace(
            f"chi thu hoi duoc yeu cau da_duyet/da_cai, hang nay dang "
            f"{hang.trang_thai!r}")
    hang.trang_thai = MARKETPLACE_TU_CHOI
    hang.ly_do_tu_choi = str(ly_do or "thu hoi")
    hang.quyet_dinh_luc = datetime.now(timezone.utc)
    db.flush()
    al = doc_allowlist_marketplace()
    if al.get("pieces", {}).pop(hang.ten, None) is not None:
        al.get("mien", {}).pop(hang.ten, None)
        al.get("palette", {}).pop(hang.ten, None)
        ghi_allowlist_marketplace(al)
    _ghi_nhat_ky(db, hang.id, "thu_hoi", nguoi_id=nguoi.id,
                chi_tiet={"ly_do": hang.ly_do_tu_choi})
    return hang


def dam_bao_da_duyet(db, *, ten: str, phien_ban: str) -> MarketplacePiece:
    """Cửa PUBLISH/NẠP dùng chung: một piece marketplace chỉ hợp lệ để tham
    chiếu trong một workflow khi có đúng một hàng `(ten, phien_ban)` ở trạng
    thái `da_duyet`/`da_cai`. ⛔ Không tồn tại hàng ⇒ từ chối — im lặng coi
    "không thấy" là "chưa duyệt" là ĐÚNG hướng fail-closed, ⛔ không phải
    hướng ngược lại.
    """
    hang = db.execute(select(MarketplacePiece).where(
        MarketplacePiece.ten == ten, MarketplacePiece.phien_ban == phien_ban,
    )).scalar_one_or_none()
    if hang is None or hang.trang_thai not in (MARKETPLACE_DA_DUYET, MARKETPLACE_DA_CAI):
        raise LoiChuaDuyet(
            f"piece marketplace chua duoc duyet: {ten}@{phien_ban}")
    return hang


# ── Allowlist/catalog marketplace (đọc/ghi tệp, cửa NẠP) ────────────────────

def _mac_dinh_allowlist() -> dict:
    return {"pieces": {}, "mien": {}, "palette": {}}


def doc_allowlist_marketplace() -> dict:
    tep = connector.THU_MUC_MARKETPLACE / "allowlist.json"
    if not tep.exists():
        return _mac_dinh_allowlist()
    with open(tep, encoding="utf-8") as f:
        dl = json.load(f)
    dl.setdefault("pieces", {})
    dl.setdefault("mien", {})
    dl.setdefault("palette", {})
    return dl


def ghi_allowlist_marketplace(allowlist: dict) -> None:
    connector.THU_MUC_MARKETPLACE.mkdir(parents=True, exist_ok=True)
    tep = connector.THU_MUC_MARKETPLACE / "allowlist.json"
    tmp = tep.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(allowlist, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    tmp.replace(tep)


def mien_cua_piece_marketplace(ten: str) -> tuple:
    """Cùng luật `connector.mien_cua_piece`: không có mục ⇒ RỖNG — fail closed."""
    return tuple((doc_allowlist_marketplace().get("mien") or {}).get(ten) or ())


# ── Kết quả cài + hai điểm nối THỰC THI (seam) cho phép tiêm lỗi/mô phỏng ──
#
# ⭐ `cai_dat()` KHÔNG tự gọi `subprocess`/`vo_boc.chay` trực tiếp — nó gọi
#   qua hai hàm module-level dưới đây. Đây không phải một lối tắt bỏ qua vỏ:
#   `_thuc_thi_npm_install_that` VẪN đi qua `vo_boc.chay` + `proxy_egress`
#   (cùng ranh giới đã đo ở `test_3500_wf_connector_ranh_gioi.py`) — tách hàm
#   chỉ để lớp ĐIỀU PHỐI (thứ tự kiểm tra, dừng ở đâu khi sai) kiểm được bằng
#   phép kiểm thường, không đòi quyền quản trị dựng AppContainer cho MỌI CI.
#   Phép kiểm ranh giới sandbox thật nằm ở `test_4239` (bỏ qua có khai lý do
#   khi máy không dựng được vỏ — cùng mẫu `test_3500`).

@dataclass
class KetQuaCai:
    ok: bool
    ten: str = ""
    phien_ban: str = ""
    ma_loi: str = ""
    thong_diep: str = ""
    do: dict = field(default_factory=dict)


def _giai_quyet_integrity_that(ten: str, phien_ban: str) -> str:
    """`npm view <ten>@<ban> dist.integrity` — qua vỏ + proxy chỉ mở
    `registry.npmjs.org`. Ném nếu registry không trả về (mạng, tên/bản sai)."""
    connector.chuan_bi_vo()
    npm_cli = _npm_cli_js()
    pr = proxy_egress.mo(MIEN_NPM_REGISTRY)
    tmp = connector.THU_MUC_LAM_VIEC / f"mkt-view-{uuid.uuid4().hex[:16]}"
    tmp.mkdir(parents=True)
    # Cùng lý do `_thuc_thi_npm_install_that`: npm dò gốc dự án bằng cách
    # `lstat` ngược lên cây cha — cho nó một `package.json` NGAY tại thư mục
    # làm việc để nó dừng ở đây, không đụng tới cây cha (không ACL).
    (tmp / "package.json").write_text(
        json.dumps({"name": "ltt-marketplace-view", "version": "0.0.0",
                   "private": True}), encoding="utf-8")
    try:
        moi = vo_boc.moi_truong_toi_thieu(proxy=pr.url)
        argv = [str(connector.THU_MUC_LAM_VIEC / "node.exe"),
               "--preserve-symlinks", "--preserve-symlinks-main",
               npm_cli, "view", "--json", "--", f"{ten}@{phien_ban}",
               "dist.integrity"]
        kq = vo_boc.chay(argv, ra_log=str(tmp / "log.txt"),
                         moi_truong=moi, han_ms=30_000,
                         bo_nho_mb=job_object.BO_NHO_MAC_DINH_MB,
                         thu_muc=str(tmp))
        log = (tmp / "log.txt").read_text(encoding="utf-8", errors="replace")
        if kq.het_gio or kq.ma_thoat != 0:
            raise LoiCaiThatBai(f"npm view that bai: {log[-800:]!r}")
        try:
            gia = json.loads(log)
        except ValueError as loi:
            raise LoiCaiThatBai(
                f"npm view tra ve khong phai JSON: {log[-500:]!r}") from loi
        integrity = gia if isinstance(gia, str) else ""
        if not integrity:
            raise LoiCaiThatBai(
                f"npm registry khong tra dist.integrity cho {ten}@{phien_ban}")
        return integrity
    finally:
        pr.dung()
        import shutil as _sh
        _sh.rmtree(tmp, ignore_errors=True)


def _npm_cli_js() -> str:
    """Bản chép `npm-cli.js` + `node_modules/npm` TRONG `THU_MUC_LAM_VIEC` —
    thư mục đó đã có ACL `(OI)(CI)(M)` cho vỏ (`connector.chuan_bi_vo`), nên
    một bản chép MỚI ở đây kế thừa đúng quyền mà không cần một lượt `icacls`
    riêng (⛔ cấp ACL trong `Program Files`, nơi npm hệ thống sống, là sửa
    quyền một thư mục hệ thống — CLAUDE.md luật 6).
    """
    import shutil as _sh
    nguon = _sh.which("npm")
    if not nguon:
        raise LoiCaiThatBai("khong tim thay npm tren May (dat PATH)")
    import pathlib as _pl
    goc_npm = _pl.Path(nguon).resolve().parent / "node_modules" / "npm"
    if not goc_npm.exists():
        # `npm` co the la mot shim (.cmd) tro toi noi khac -- do lai tu node.
        node = _sh.which("node")
        if node:
            goc_npm = _pl.Path(node).resolve().parent / "node_modules" / "npm"
    if not goc_npm.exists():
        raise LoiCaiThatBai(f"khong tim thay npm CLI canh node: {goc_npm}")
    dich = connector.THU_MUC_LAM_VIEC / "npm_cli"
    dich_cli = dich / "bin" / "npm-cli.js"
    if not dich_cli.exists():
        connector.THU_MUC_LAM_VIEC.mkdir(parents=True, exist_ok=True)
        _sh.copytree(goc_npm, dich, dirs_exist_ok=True)
    return str(dich_cli)


def _thuc_thi_npm_install_that(argv: list, *, mien) -> dict:
    """Chạy `argv` (đã qua `kiem_tra_argv_an_toan`) TRONG vỏ, egress giới hạn
    `mien`. Trả `{"ok", "log"}` — KHÔNG diễn giải; `cai_dat()` diễn giải.
    """
    connector.chuan_bi_vo()
    connector.THU_MUC_MARKETPLACE.mkdir(parents=True, exist_ok=True)
    vo_boc.cap_acl(str(connector.THU_MUC_MARKETPLACE),
                   vo_boc.sid_cua_vo(), "(OI)(CI)(M)")
    pr = proxy_egress.mo(tuple(mien))
    tmp = connector.THU_MUC_LAM_VIEC / f"mkt-cai-{uuid.uuid4().hex[:16]}"
    tmp.mkdir(parents=True)
    try:
        # npm CLI dò "gốc dự án" (workspace/`.npmrc`) bằng cách `lstat` NGƯỢC
        # LÊN từ thư mục làm việc tới tận gốc ổ đĩa (đo 24/09: `EPERM: lstat
        # 'D:\LTTSTUDIOSAPP-wfm'` dù `THU_MUC_LAM_VIEC` đã có ACL — cây cha
        # của nó thì KHÔNG, và ⛔ cấp ACL ngược lên cây cha là mở rộng bề mặt
        # một cách không cần thiết, đúng thứ CLAUDE.md cấm cho `Program
        # Files`). Thuốc: cho npm một `package.json` NGAY tại thư mục làm
        # việc — dò thấy gốc ở đó, dừng, không đi tiếp lên cây cha (cùng cách
        # Activepieces `piece-installer.ts::createPiecePackageJson` làm:
        # luôn viết `package.json` TRƯỚC khi gọi install).
        prefix = pathlib.Path(argv[argv.index("--prefix") + 1])
        prefix.mkdir(parents=True, exist_ok=True)
        (prefix / "package.json").write_text(
            json.dumps({"name": "ltt-marketplace-scratch", "version": "0.0.0",
                       "private": True}),
            encoding="utf-8")
        moi = vo_boc.moi_truong_toi_thieu(proxy=pr.url)
        # 🔴 CẢ HAI cờ symlink (cùng lý do `connector.py::chay`, đo 24/09): npm
        #    CLI `require`-chain đi qua realpath lên tận gốc ổ đĩa, và vỏ
        #    không đọc được gốc ổ đĩa — thiếu cờ này chết `EPERM: lstat 'D:\'`
        #    trước khi npm kịp làm gì.
        full_argv = [str(connector.THU_MUC_LAM_VIEC / "node.exe"),
                    "--preserve-symlinks", "--preserve-symlinks-main"] + argv
        kq = vo_boc.chay(full_argv, ra_log=str(tmp / "log.txt"),
                         moi_truong=moi, han_ms=HAN_CAI_MS,
                         bo_nho_mb=job_object.BO_NHO_MAC_DINH_MB,
                         thu_muc=str(prefix))
        log = ""
        try:
            log = (tmp / "log.txt").read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
        return {"ok": (not kq.het_gio) and kq.ma_thoat == 0, "log": log,
               "het_gio": kq.het_gio, "ma_thoat": kq.ma_thoat}
    finally:
        pr.dung()
        # ⛔ KHÔNG xoá `prefix` ở đây — đó là ĐÍCH cài (`--prefix`), gọi hàm
        #    (`cai_dat()`) còn phải đọc `node_modules/<ten>` từ đó SAU khi hàm
        #    này trả về. Chỉ `tmp` (thư mục log/scratch riêng của lượt gọi
        #    này) là rác cần dọn.
        import shutil as _sh
        _sh.rmtree(tmp, ignore_errors=True)


def cai_dat(db, *, yeu_cau_id: str, nguoi: User,
           giai_quyet_integrity=None, thuc_thi_install=None) -> KetQuaCai:
    """FAIL CLOSED, từng bước ném ngay khi sai — ⛔ không "cố hết sức rồi
    cảnh báo". `giai_quyet_integrity`/`thuc_thi_install` là điểm tiêm cho
    test (mặc định gọi thật qua vỏ, xem docstring hai hàm `_that` ở trên).
    """
    giai_quyet_integrity = giai_quyet_integrity or _giai_quyet_integrity_that
    thuc_thi_install = thuc_thi_install or _thuc_thi_npm_install_that

    # (1) RÀNG BUỘC (c) — ai được cài.
    _can_admin(nguoi)

    # (2) RÀNG BUỘC (b) — cổng duyệt FAIL CLOSED. Chưa duyệt ⇒ dừng ở đây,
    #     TRƯỚC bất kỳ I/O mạng/đĩa nào.
    hang = _lay(db, yeu_cau_id)
    if hang.trang_thai not in (MARKETPLACE_DA_DUYET,):
        _ghi_nhat_ky(db, hang.id, "cai_that_bai", nguoi_id=nguoi.id,
                    chi_tiet={"ly_do": "chua_duyet",
                             "trang_thai": hang.trang_thai})
        raise LoiChuaDuyet(
            f"piece chua duoc duyet (dang {hang.trang_thai!r}) — khong the cai")

    # (3) Ghim phiên bản — phòng thủ theo chiều sâu, `yeu_cau()` đã kiểm rồi.
    try:
        _kiem_ten_hop_le(hang.ten)
        _kiem_phien_ban_ghim(hang.phien_ban)
    except LoiMarketplace as loi:
        _ghi_nhat_ky(db, hang.id, "cai_that_bai", nguoi_id=nguoi.id,
                    chi_tiet={"ly_do": loi.ma_loi, "thong_diep": str(loi)})
        raise

    bat_dau = time.monotonic()
    try:
        # (4) Toàn vẹn — nghị quyết TRƯỚC khi cài (pin sớm nhất có thể).
        integrity_ky_vong = giai_quyet_integrity(hang.ten, hang.phien_ban)

        # (5) Argv + RÀNG BUỘC (a) — --ignore-scripts bắt buộc, kiểm TRƯỚC
        #     khi thực thi, không phải sau khi đọc log.
        npm_cli = _npm_cli_js() if thuc_thi_install is _thuc_thi_npm_install_that \
            else "npm-cli.js"
        dich = connector.THU_MUC_MARKETPLACE / "installs" / f"{_slug(hang.ten)}-{hang.phien_ban}-{uuid.uuid4().hex[:8]}"
        cache = connector.THU_MUC_MARKETPLACE / "npm-cache"
        argv = argv_npm_install(npm_cli, hang.ten, hang.phien_ban,
                                prefix=str(dich), cache=str(cache))
        kiem_tra_argv_an_toan(argv)

        # (6) Thực thi TRONG vỏ, egress giới hạn npm registry.
        ket = thuc_thi_install(argv, mien=MIEN_NPM_REGISTRY)
        if not ket.get("ok"):
            raise LoiCaiThatBai(
                f"npm install that bai: {ket.get('log', '')[-800:]!r}")

        # (7) Không "gần đúng": phiên bản CÀI ĐƯỢC phải khớp TUYỆT ĐỐI với
        #     phiên bản đã DUYỆT — cùng luật `piece_nap.js::napPiece`.
        goi_dir = dich / "node_modules" / hang.ten
        pkg_json = goi_dir / "package.json"
        if not pkg_json.exists():
            raise LoiCaiThatBai(
                f"cai xong nhung khong thay {pkg_json} — cai that bai im lang")
        pkg = json.loads(pkg_json.read_text(encoding="utf-8"))
        if str(pkg.get("version")) != str(hang.phien_ban):
            raise LoiCaiThatBai(
                f"phien ban lech: cai {pkg.get('version')} != duyet {hang.phien_ban}")

        # (8) Toàn vẹn — đối chiếu integrity NGHỊ QUYẾT (bước 4) với integrity
        #     GHI LẠI TRONG LOCKFILE của chính lượt cài này.
        integrity_that = _doc_integrity_lockfile(dich, hang.ten)
        if not integrity_that or integrity_that != integrity_ky_vong:
            raise LoiToanVenSai(
                f"toan ven sai: nghi quyet {integrity_ky_vong!r} != "
                f"lockfile {integrity_that!r}")

        # (9) MỌI kiểm tra qua — CHỈ BÂY GIỜ mới ghi allowlist (cửa NẠP).
        al = doc_allowlist_marketplace()
        al["pieces"][hang.ten] = hang.phien_ban
        al["mien"][hang.ten] = list(hang.mien or [])
        ghi_allowlist_marketplace(al)
        _dua_vao_node_modules_chung(dich, hang.ten)
        # Dọn thư mục SCRATCH (`installs/...`) sau khi đã sao xong vào
        # node_modules DÙNG CHUNG — giữ nó lại chỉ tổ tích rác trên đĩa qua
        # mỗi lượt duyệt (⛔ khác đường LỖI: ở đó ta CỐ Ý giữ nguyên để còn
        # điều tra được — xem `except LoiMarketplace` cuối hàm).
        import shutil as _sh
        _sh.rmtree(dich, ignore_errors=True)

        hang.trang_thai = MARKETPLACE_DA_CAI
        hang.integrity = integrity_that
        hang.cai_luc = datetime.now(timezone.utc)
        db.flush()
        do = {"do_tre_ms": int((time.monotonic() - bat_dau) * 1000)}
        _ghi_nhat_ky(db, hang.id, "cai", nguoi_id=nguoi.id,
                    chi_tiet={"ten": hang.ten, "phien_ban": hang.phien_ban,
                             "integrity": integrity_that, "do": do})
        return KetQuaCai(ok=True, ten=hang.ten, phien_ban=hang.phien_ban, do=do)
    except LoiMarketplace as loi:
        _ghi_nhat_ky(db, hang.id, "cai_that_bai", nguoi_id=nguoi.id,
                    chi_tiet={"ly_do": loi.ma_loi, "thong_diep": str(loi)})
        raise


def _slug(ten: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", ten.lower()).strip("_")


def _doc_integrity_lockfile(thu_muc, ten: str) -> str:
    """`dist.integrity` mà CHÍNH lượt `npm install` này ghi vào
    `package-lock.json` — nguồn đối chứng cho bước (8), tách khỏi bước (4)
    (registry) để bắt lệch giữa hai lần hỏi registry.
    """
    tep = thu_muc / "package-lock.json"
    if not tep.exists():
        return ""
    try:
        dl = json.loads(tep.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    for khoa, muc in (dl.get("packages") or {}).items():
        if khoa == f"node_modules/{ten}":
            return str((muc or {}).get("integrity") or "")
    # Lockfile npm v1 (`dependencies` phang) — dự phòng cho npm cũ.
    dep = (dl.get("dependencies") or {}).get(ten) or {}
    return str(dep.get("integrity") or "")


def _dua_vao_node_modules_chung(nguon_prefix, ten: str) -> None:
    """Sao `node_modules/<ten>` của lượt cài SCRATCH vào
    `THU_MUC_MARKETPLACE/node_modules/<ten>` DÙNG CHUNG — nơi
    `LTT_MARKETPLACE_DIR` trỏ tới cho `piece_nap.js` (spec module đó).
    Ghi đè nguyên tử theo thư mục đích (xoá rồi chép, không có cửa sổ tệp
    thiếu — có thể một lệnh `nap` khác đang đọc giữa lúc thay; chấp nhận vì
    lượt nạp lỗi giữa chừng chỉ làm MỘT job thất bại, thử lại được, ⛔ không
    làm hỏng ranh giới an toàn).
    """
    import shutil as _sh
    nguon = nguon_prefix / "node_modules" / ten
    dich = connector.THU_MUC_MARKETPLACE / "node_modules" / ten
    dich.parent.mkdir(parents=True, exist_ok=True)
    if dich.exists():
        _sh.rmtree(dich, ignore_errors=True)
    _sh.copytree(nguon, dich)


__all__ = [
    "KetQuaCai", "LoiCaiThatBai", "LoiChuaDuyet", "LoiKhongDuQuyen",
    "LoiMarketplace", "LoiPhienBanKhongGhim", "LoiTenKhongHopLe",
    "LoiToanVenSai", "MIEN_NPM_REGISTRY", "argv_npm_install", "cai_dat",
    "dam_bao_da_duyet", "doc_allowlist_marketplace", "duyet",
    "ghi_allowlist_marketplace", "kiem_tra_argv_an_toan",
    "mien_cua_piece_marketplace", "thu_hoi", "tu_choi", "yeu_cau",
]
