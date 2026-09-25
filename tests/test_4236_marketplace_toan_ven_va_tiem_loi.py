"""Toàn vẹn (bước 4+8 của `cai_dat`) + TIÊM LỖI cho từng ràng buộc.

⭐ "Tiêm lỗi" ở đây nghĩa là: với MỖI ràng buộc, có một phép kiểm trực tiếp
chứng minh việc GỠ ràng buộc đó khiến một phép kiểm khác đỏ — không chỉ
"có một dòng code trông như kiểm tra", mà "gỡ dòng đó thì có test báo động".

- Ràng buộc (a) `--ignore-scripts`: `kiem_tra_argv_an_toan` là nơi DUY NHẤT
  gác cổng cờ này trước khi thực thi. `test_go_co...` dựng một argv y hệt
  `argv_npm_install` sinh ra nhưng ĐÃ BỊ GỠ cờ (mô phỏng ai đó sửa
  `argv_npm_install` mà quên cờ) và chứng minh `kiem_tra_argv_an_toan` vẫn
  bắt được nó — tức nếu chính `argv_npm_install` bị sửa nhầm, hàng rào thứ
  hai này vẫn đỏ.
- Ràng buộc (b) cổng duyệt: `test_go_kiem_tra_trang_thai...` gọi thẳng
  `_lay()` + thao tác hàng để mô phỏng "nếu `cai_dat()` không kiểm
  `trang_thai`" và chứng minh `dam_bao_da_duyet` (cửa thứ hai, độc lập) vẫn
  chặn — hai cửa không cùng chung một điểm hỏng.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401


def _admin(id_="admin1"):
    from platform_core.models import User
    return User(id=id_, email=f"{id_}@x.test", role="admin",
               password_hash="x", display_name="Admin")


def _user(id_="u1"):
    from platform_core.models import User
    return User(id=id_, email=f"{id_}@x.test", role="user",
               password_hash="x", display_name="User")


@pytest.fixture()
def mkt_dir(monkeypatch, tmp_path):
    from platform_core.workflow import connector
    d = tmp_path / "mkt"
    monkeypatch.setattr(connector, "THU_MUC_MARKETPLACE", d)
    return d


# ── Toàn vẹn: registry-vs-lockfile phải khớp ────────────────────────────

def test_toan_ven_sai_khi_lockfile_khac_registry(db, mkt_dir):  # noqa: F811
    """Registry nói `sha512-A`, nhưng lockfile của CHÍNH lượt cài lại ghi
    `sha512-B` (mô phỏng tarball bị tráo giữa lúc hỏi metadata và lúc tải).
    ⇒ phải NÉM `LoiToanVenSai`, ⛔ không được âm thầm dùng bản nào."""
    from platform_core.models import MARKETPLACE_DA_DUYET
    from platform_core.workflow import marketplace as mp

    def fake_install_lech(argv, *, mien):
        prefix = pathlib.Path(argv[argv.index("--prefix") + 1])
        goi = prefix / "node_modules" / "@foo" / "piece-bar"
        goi.mkdir(parents=True, exist_ok=True)
        (goi / "package.json").write_text(
            json.dumps({"name": "@foo/piece-bar", "version": "1.2.3"}),
            encoding="utf-8")
        (prefix / "package-lock.json").write_text(json.dumps({
            "packages": {"node_modules/@foo/piece-bar": {
                "version": "1.2.3", "integrity": "sha512-KHAC-BAN=="}},
        }), encoding="utf-8")
        return {"ok": True, "log": ""}

    hang = mp.yeu_cau(db, nguoi=_user(), ten="@foo/piece-bar", phien_ban="1.2.3")
    mp.duyet(db, yeu_cau_id=hang.id, nguoi=_admin())
    with pytest.raises(mp.LoiToanVenSai):
        mp.cai_dat(db, yeu_cau_id=hang.id, nguoi=_admin(),
                  giai_quyet_integrity=lambda t, v: "sha512-GOC==",
                  thuc_thi_install=fake_install_lech)
    db.refresh(hang)
    assert hang.trang_thai == MARKETPLACE_DA_DUYET
    assert not (mkt_dir / "allowlist.json").exists()


def test_toan_ven_sai_khi_khong_co_lockfile(db, mkt_dir):  # noqa: F811
    """`npm install` báo `ok=True` nhưng không ghi `package-lock.json` (npm
    cấu hình `--no-package-lock` ở đâu đó) ⇒ không có gì để đối chứng, phải
    NÉM — ⛔ không được coi "không đo được" là "an toàn"."""
    from platform_core.workflow import marketplace as mp

    def fake_install_khong_lockfile(argv, *, mien):
        prefix = pathlib.Path(argv[argv.index("--prefix") + 1])
        goi = prefix / "node_modules" / "@foo" / "piece-bar"
        goi.mkdir(parents=True, exist_ok=True)
        (goi / "package.json").write_text(
            json.dumps({"name": "@foo/piece-bar", "version": "1.2.3"}),
            encoding="utf-8")
        return {"ok": True, "log": ""}

    hang = mp.yeu_cau(db, nguoi=_user(), ten="@foo/piece-bar", phien_ban="1.2.3")
    mp.duyet(db, yeu_cau_id=hang.id, nguoi=_admin())
    with pytest.raises(mp.LoiToanVenSai):
        mp.cai_dat(db, yeu_cau_id=hang.id, nguoi=_admin(),
                  giai_quyet_integrity=lambda t, v: "sha512-GOC==",
                  thuc_thi_install=fake_install_khong_lockfile)


def test_phien_ban_cai_duoc_lech_voi_ban_da_duyet_bi_chan(db, mkt_dir):  # noqa: F811
    """npm cài được nhưng `package.json` ghi phiên bản KHÁC bản đã duyệt (vd
    registry đổi `dist-tag` giữa lúc duyệt và lúc cài) — không "gần đúng"."""
    from platform_core.workflow import marketplace as mp

    def fake_install_ban_khac(argv, *, mien):
        prefix = pathlib.Path(argv[argv.index("--prefix") + 1])
        goi = prefix / "node_modules" / "@foo" / "piece-bar"
        goi.mkdir(parents=True, exist_ok=True)
        (goi / "package.json").write_text(
            json.dumps({"name": "@foo/piece-bar", "version": "1.2.4"}),
            encoding="utf-8")
        return {"ok": True, "log": ""}

    hang = mp.yeu_cau(db, nguoi=_user(), ten="@foo/piece-bar", phien_ban="1.2.3")
    mp.duyet(db, yeu_cau_id=hang.id, nguoi=_admin())
    with pytest.raises(mp.LoiCaiThatBai):
        mp.cai_dat(db, yeu_cau_id=hang.id, nguoi=_admin(),
                  giai_quyet_integrity=lambda t, v: "x",
                  thuc_thi_install=fake_install_ban_khac)


# ── Tiêm lỗi (a): --ignore-scripts ──────────────────────────────────────

def test_argv_that_luon_co_co_ignore_scripts(db):  # noqa: F811
    from platform_core.workflow import marketplace as mp
    argv = mp.argv_npm_install("npm-cli.js", "@foo/bar", "1.2.3",
                               prefix="p", cache="c")
    mp.kiem_tra_argv_an_toan(argv)  # khong nem


def test_TIEM_LOI_go_co_ignore_scripts_bi_hang_rao_thu_hai_bat(db):  # noqa: F811
    """Mô phỏng: một sửa đổi trong tương lai ở `argv_npm_install` VÔ Ý làm
    rơi mất `--ignore-scripts`. `kiem_tra_argv_an_toan` (hàng rào ĐỘC LẬP,
    gọi ngay trước khi thực thi trong `cai_dat()`) vẫn phải bắt được."""
    from platform_core.workflow import marketplace as mp
    argv = mp.argv_npm_install("npm-cli.js", "@foo/bar", "1.2.3",
                               prefix="p", cache="c")
    argv_thieu_co = [a for a in argv if a != "--ignore-scripts"]
    assert "--ignore-scripts" not in argv_thieu_co
    with pytest.raises(mp.LoiCaiThatBai):
        mp.kiem_tra_argv_an_toan(argv_thieu_co)


def test_TIEM_LOI_thieu_co_trong_cai_dat_thi_bi_chan_TRUOC_khi_thuc_thi(db, mkt_dir):  # noqa: F811
    """Ép `cai_dat()` dùng một argv KHÔNG có `--ignore-scripts` bằng cách
    tiêm một `thuc_thi_install` giả kiểm tra chính argv nó nhận được — nếu
    `kiem_tra_argv_an_toan` bị xoá khỏi `cai_dat()`, phép này sẽ thấy
    `thuc_thi_install` bị gọi VỚI argv thiếu cờ (tức "chạy được npm install
    không --ignore-scripts") thay vì thấy `cai_dat()` tự nổ trước."""
    from platform_core.workflow import marketplace as mp

    goi_voi_argv = {}

    def fake_bat_argv(argv, *, mien):
        goi_voi_argv["argv"] = argv
        return {"ok": False, "log": "khong chay that"}

    hang = mp.yeu_cau(db, nguoi=_user(), ten="@foo/piece-bar", phien_ban="1.2.3")
    mp.duyet(db, yeu_cau_id=hang.id, nguoi=_admin())
    import platform_core.workflow.marketplace as mp_mod
    orig = mp_mod.argv_npm_install

    # Patch `argv_npm_install` (khong phai `kiem_tra_argv_an_toan`) de mo
    # phong "ai do sua ham sinh argv lam mat co" ma KHONG dung ca hang rao.
    # ⚠️ Goi `orig(...)` (ham GOC da chup truoc), KHONG `mp.argv_npm_install`
    #    — sau khi patch, ten do tro LAI chinh ham nay, de quy vo han.
    def argv_thieu_co(*a, **k):
        return [x for x in orig(*a, **k) if x != "--ignore-scripts"]

    mp_mod.argv_npm_install = argv_thieu_co
    try:
        with pytest.raises(mp.LoiCaiThatBai) as ei:
            mp.cai_dat(db, yeu_cau_id=hang.id, nguoi=_admin(),
                      giai_quyet_integrity=lambda t, v: "x",
                      thuc_thi_install=fake_bat_argv)
        assert "ignore-scripts" in str(ei.value)
    finally:
        mp_mod.argv_npm_install = orig
    # Hàng rào chặn TRƯỚC khi gọi thực thi — `thuc_thi_install` khong chay.
    assert "argv" not in goi_voi_argv


# ── Tiêm lỗi (b): cổng duyệt là cửa ĐỘC LẬP, không chỉ một if trong cai_dat ──

def test_TIEM_LOI_publish_door_khong_dua_vao_cung_bien_voi_cai_dat(db, mkt_dir):  # noqa: F811
    """`dam_bao_da_duyet` (cửa publish) tự truy vấn CSDL lại từ đầu — nó
    không nhận tham số "đã kiểm chưa" từ nơi gọi. Chứng minh: một hàng bị
    thao túng thẳng qua ORM (bỏ qua toàn bộ `marketplace.py`) về `cho_duyet`
    SAU khi đã `da_cai` vẫn bị `dam_bao_da_duyet` chặn ngay lập tức — cửa
    publish đọc trạng thái LÚC ĐÓ, không cache một quyết định cũ."""
    from platform_core.models import MARKETPLACE_CHO_DUYET
    from platform_core.workflow import marketplace as mp

    hang = mp.yeu_cau(db, nguoi=_user(), ten="@foo/piece-bar", phien_ban="1.2.3")
    mp.duyet(db, yeu_cau_id=hang.id, nguoi=_admin())
    mp.cai_dat(db, yeu_cau_id=hang.id, nguoi=_admin(),
              giai_quyet_integrity=lambda t, v: "x",
              thuc_thi_install=lambda argv, mien: _cai_gia(argv))
    assert mp.dam_bao_da_duyet(db, ten="@foo/piece-bar", phien_ban="1.2.3")

    hang.trang_thai = MARKETPLACE_CHO_DUYET  # mo phong thu hoi/hong du lieu
    db.flush()
    with pytest.raises(mp.LoiChuaDuyet):
        mp.dam_bao_da_duyet(db, ten="@foo/piece-bar", phien_ban="1.2.3")


def _cai_gia(argv):
    prefix = pathlib.Path(argv[argv.index("--prefix") + 1])
    goi = prefix / "node_modules" / "@foo" / "piece-bar"
    goi.mkdir(parents=True, exist_ok=True)
    (goi / "package.json").write_text(
        json.dumps({"name": "@foo/piece-bar", "version": "1.2.3"}), encoding="utf-8")
    (prefix / "package-lock.json").write_text(json.dumps({
        "packages": {"node_modules/@foo/piece-bar": {
            "version": "1.2.3", "integrity": "x"}},
    }), encoding="utf-8")
    return {"ok": True, "log": ""}
