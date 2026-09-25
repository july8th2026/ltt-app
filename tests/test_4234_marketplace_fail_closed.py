"""Cổng duyệt FAIL-CLOSED ở CẢ BA cửa: cài / nạp / publish (ràng buộc b).

🔴 Trục chính của tệp này: một piece **CHƯA duyệt** không được đi qua bất kỳ
cửa nào trong ba cửa — và ở cửa CÀI, phải dừng lại TRƯỚC khi chạm mạng/đĩa
(hai điểm nối `giai_quyet_integrity`/`thuc_thi_install` không được gọi).
Không có bằng chứng "chưa gọi" thì một phép `pytest.raises` có thể xanh vì
lý do khác hẳn (vd lỗi kiểu dữ liệu) chứ không phải vì cổng duyệt chặn.

`giai_quyet_integrity`/`thuc_thi_install` mô phỏng — phép kiểm ranh giới
AppContainer THẬT nằm ở `test_4239` (bỏ qua có khai lý do khi máy không dựng
được vỏ).
"""
from __future__ import annotations

import json
import pathlib

import pytest

from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401

INTEGRITY_DUNG = "sha512-DUNG=="


def _admin(id_="admin1"):
    from platform_core.models import User
    return User(id=id_, email=f"{id_}@x.test", role="admin",
               password_hash="x", display_name="Admin")


def _user(id_="u1"):
    from platform_core.models import User
    return User(id=id_, email=f"{id_}@x.test", role="user",
               password_hash="x", display_name="User")


def _khong_duoc_goi(*a, **k):
    raise AssertionError("seam KHONG duoc goi khi chua qua cong duyet")


def _fake_integrity_ok(ten, phien_ban):
    return INTEGRITY_DUNG


def _fake_install_ok(argv, *, mien):
    prefix = pathlib.Path(argv[argv.index("--prefix") + 1])
    spec = argv[-1]
    ten, phien_ban = spec.rsplit("@", 1)
    goi_dir = prefix / "node_modules" / ten
    goi_dir.mkdir(parents=True, exist_ok=True)
    (goi_dir / "package.json").write_text(
        json.dumps({"name": ten, "version": phien_ban}), encoding="utf-8")
    (prefix / "package-lock.json").write_text(json.dumps({
        "packages": {f"node_modules/{ten}": {"version": phien_ban,
                                              "integrity": INTEGRITY_DUNG}},
    }), encoding="utf-8")
    return {"ok": True, "log": ""}


@pytest.fixture()
def mkt_dir(monkeypatch, tmp_path):
    from platform_core.workflow import connector
    d = tmp_path / "mkt"
    monkeypatch.setattr(connector, "THU_MUC_MARKETPLACE", d)
    return d


def test_cai_dat_hang_cho_duyet_bi_chan_TRUOC_khi_cham_mang(db, mkt_dir):  # noqa: F811
    from platform_core.workflow import marketplace as mp
    hang = mp.yeu_cau(db, nguoi=_user(), ten="@foo/piece-bar", phien_ban="1.2.3")
    with pytest.raises(mp.LoiChuaDuyet):
        mp.cai_dat(db, yeu_cau_id=hang.id, nguoi=_admin(),
                  giai_quyet_integrity=_khong_duoc_goi,
                  thuc_thi_install=_khong_duoc_goi)
    assert not mkt_dir.exists() or not (mkt_dir / "allowlist.json").exists()


def test_cai_dat_hang_tu_choi_bi_chan(db, mkt_dir):  # noqa: F811
    from platform_core.workflow import marketplace as mp
    hang = mp.yeu_cau(db, nguoi=_user(), ten="@foo/piece-bar", phien_ban="1.2.3")
    mp.tu_choi(db, yeu_cau_id=hang.id, nguoi=_admin())
    with pytest.raises(mp.LoiChuaDuyet):
        mp.cai_dat(db, yeu_cau_id=hang.id, nguoi=_admin(),
                  giai_quyet_integrity=_khong_duoc_goi,
                  thuc_thi_install=_khong_duoc_goi)


def test_cai_dat_hang_da_duyet_thanh_cong_ghi_allowlist(db, mkt_dir):  # noqa: F811
    from platform_core.models import MARKETPLACE_DA_CAI
    from platform_core.workflow import marketplace as mp
    hang = mp.yeu_cau(db, nguoi=_user(), ten="@foo/piece-bar", phien_ban="1.2.3",
                      mien=["bar.example.com"])
    mp.duyet(db, yeu_cau_id=hang.id, nguoi=_admin())
    ra = mp.cai_dat(db, yeu_cau_id=hang.id, nguoi=_admin(),
                    giai_quyet_integrity=_fake_integrity_ok,
                    thuc_thi_install=_fake_install_ok)
    assert ra.ok
    db.refresh(hang)
    assert hang.trang_thai == MARKETPLACE_DA_CAI
    assert hang.integrity == INTEGRITY_DUNG
    al = mp.doc_allowlist_marketplace()
    assert al["pieces"]["@foo/piece-bar"] == "1.2.3"
    assert al["mien"]["@foo/piece-bar"] == ["bar.example.com"]
    # Cửa NẠP: piece cài xong nằm ở node_modules DÙNG CHUNG mà `piece_nap.js`
    # đọc qua `LTT_MARKETPLACE_DIR`.
    goi = mkt_dir / "node_modules" / "@foo" / "piece-bar" / "package.json"
    assert goi.exists()
    assert json.loads(goi.read_text(encoding="utf-8"))["version"] == "1.2.3"


def test_publish_door_dam_bao_da_duyet_tu_choi_khi_chua_co_hang(db, mkt_dir):  # noqa: F811
    from platform_core.workflow import marketplace as mp
    with pytest.raises(mp.LoiChuaDuyet):
        mp.dam_bao_da_duyet(db, ten="@khong/ton-tai", phien_ban="1.0.0")


def test_publish_door_tu_choi_khi_con_cho_duyet(db, mkt_dir):  # noqa: F811
    from platform_core.workflow import marketplace as mp
    mp.yeu_cau(db, nguoi=_user(), ten="@foo/piece-bar", phien_ban="1.2.3")
    with pytest.raises(mp.LoiChuaDuyet):
        mp.dam_bao_da_duyet(db, ten="@foo/piece-bar", phien_ban="1.2.3")


def test_publish_door_qua_duoc_sau_khi_da_cai(db, mkt_dir):  # noqa: F811
    from platform_core.workflow import marketplace as mp
    hang = mp.yeu_cau(db, nguoi=_user(), ten="@foo/piece-bar", phien_ban="1.2.3")
    mp.duyet(db, yeu_cau_id=hang.id, nguoi=_admin())
    mp.cai_dat(db, yeu_cau_id=hang.id, nguoi=_admin(),
              giai_quyet_integrity=_fake_integrity_ok,
              thuc_thi_install=_fake_install_ok)
    ra = mp.dam_bao_da_duyet(db, ten="@foo/piece-bar", phien_ban="1.2.3")
    assert ra.id == hang.id


def test_cai_that_bai_KHONG_ghi_allowlist(db, mkt_dir):  # noqa: F811
    """Lệnh cài thất bại giữa chừng (npm trả lỗi) ⇒ allowlist marketplace
    KHÔNG được đụng tới — nếu không, một lần cài hỏng có thể để lại một mục
    allowlist trỏ tới một piece không thật sự có trên đĩa."""
    from platform_core.models import MARKETPLACE_DA_DUYET
    from platform_core.workflow import marketplace as mp

    def fake_that_bai(argv, *, mien):
        return {"ok": False, "log": "npm ERR! 404 Not Found"}

    hang = mp.yeu_cau(db, nguoi=_user(), ten="@foo/piece-bar", phien_ban="1.2.3")
    mp.duyet(db, yeu_cau_id=hang.id, nguoi=_admin())
    with pytest.raises(mp.LoiCaiThatBai):
        mp.cai_dat(db, yeu_cau_id=hang.id, nguoi=_admin(),
                  giai_quyet_integrity=_fake_integrity_ok,
                  thuc_thi_install=fake_that_bai)
    db.refresh(hang)
    assert hang.trang_thai == MARKETPLACE_DA_DUYET  # KHONG chuyen sang da_cai
    assert not (mkt_dir / "allowlist.json").exists()
