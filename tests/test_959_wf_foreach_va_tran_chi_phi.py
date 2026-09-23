"""LTT WORKFLOW V2 · Đợt 4.3–4.6 — ForEach · Join · node điều khiển · trần chi phí.

Bốn hạng mục, bốn ngưỡng số:

  `M7`  ForEach 100 phan tu, crash giua chung -> 100 ket qua, 0 luot lap
  `M4`  nhanh song song toi da moi run: hom nay 4 CUNG -> khai duoc, mac dinh 8
  `M8`  bao gia phai kem HAI SO (toi da va uoc tinh), chenh lech do duoc
  `G15` node dieu khien KHONG sinh Job -> re nhanh khong tao dong so tien

⚠️ `4.6` là mục **không có đối chứng ngành** (`23_24 §7`): **không kho nào**
   trong bảy kho khảo sát có trần chi phí — bước của họ gần như miễn phí. Nên nó
   phải có bộ test riêng, và **không được coi là an toàn vì "ngành làm thế"**.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'wf9.db').as_posix()}")
    import platform_core.db as dbmod

    dbmod.reset_engine()
    import platform_core.models  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session()
    session = next(gen)
    try:
        yield session
    finally:
        session.close()
        dbmod.reset_engine()


@pytest.fixture()
def run(db):
    from platform_core.workflow import dinh_nghia, thi_hanh

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="FE")
    db.commit()
    v = dinh_nghia.xuat_ban(db, wf.id, {"schema_version": 1, "nodes": [],
                                        "edges": []}, created_by="u1")
    db.commit()
    r = thi_hanh.tao_run(db, workflow_id=wf.id, version_id=v.id,
                         owner_id="u1", trigger_kind="manual")
    db.commit()
    return r


# ── 4.3 ForEach ───────────────────────────────────────────────────────────────

def test_max_items_la_BAT_BUOC(db, run):
    """⛔ Không có `max_items` hữu hạn thì **trần chi phí không tính được**.

    Đây là ràng buộc do `WF-501` áp xuống, không phải một tuỳ chọn tiện nghi:
    một ForEach không chặn trên là một hoá đơn không chặn trên.
    """
    from platform_core.workflow import foreach

    with pytest.raises(ValueError, match="max_items"):
        foreach.mo_vong(db, run_id=run.id, node_id="fe", muc=list(range(3)),
                        max_items=0)


def test_vuot_max_items_bi_TU_CHOI_truoc_khi_chay(db, run):
    """Từ chối **trước khi chạy**, không phải dừng giữa chừng.

    Dừng giữa chừng nghĩa là đã tiêu một phần tiền cho một lượt chạy chắc chắn
    thất bại — tệ hơn cả không chạy.
    """
    from platform_core.workflow import foreach

    with pytest.raises(foreach.VuotTran):
        foreach.mo_vong(db, run_id=run.id, node_id="fe",
                        muc=list(range(101)), max_items=100)


def test_M7_100_phan_tu_crash_giua_chung_ra_100_ket_qua_0_lap(db, run):
    """🔴 `M7`: 100 phần tử, crash giữa chừng → **100 kết quả, 0 lượt lặp**.

    Hai nửa, và nửa thứ hai mới khó: "không lặp" nghĩa là một phần tử đã chạy
    **không được chạy lại** sau khi khôi phục — nếu nó gọi model thì lặp là tiền
    thật, và là kết quả khác.
    """
    from platform_core.workflow import foreach

    vong = foreach.mo_vong(db, run_id=run.id, node_id="fe",
                           muc=list(range(100)), max_items=100)
    db.commit()

    for i in range(57):
        foreach.ghi_ket_qua(db, vong, chi_so=i, ket_qua={"v": i})
    db.commit()

    # Ba phan tu DANG BAY: da ghi, chua commit. Tien trinh chet o day.
    for i in (57, 58, 59):
        foreach.ghi_ket_qua(db, vong, chi_so=i, ket_qua={"v": i})
    db.rollback()                     # <- tien trinh chet giua chung

    con_lai = foreach.chi_so_chua_xong(db, vong)
    assert con_lai == list(range(57, 100)), "phai biet CHINH XAC con lai gi"

    for i in con_lai:
        foreach.ghi_ket_qua(db, vong, chi_so=i, ket_qua={"v": i})
    db.commit()

    ra = foreach.gom_ket_qua(db, vong)
    assert len(ra) == 100
    assert [r["v"] for r in ra] == list(range(100)), "phai dung THU TU dau vao"
    assert foreach.so_luot_chay(db, vong) == 100, "0 luot lap"


def test_ghi_lai_mot_chi_so_DA_XONG_khong_tao_luot_thu_hai(db, run):
    """Luỹ đẳng theo **chỉ số**, vì worker phát lại sẽ thử ghi lại."""
    from platform_core.workflow import foreach

    vong = foreach.mo_vong(db, run_id=run.id, node_id="fe", muc=[10, 20],
                           max_items=10)
    foreach.ghi_ket_qua(db, vong, chi_so=0, ket_qua={"v": "a"})
    foreach.ghi_ket_qua(db, vong, chi_so=0, ket_qua={"v": "GHI DE"})
    db.commit()

    assert foreach.so_luot_chay(db, vong) == 1
    assert foreach.gom_ket_qua(db, vong)[0] == {"v": "a"}, "ban dau tien thang"


def test_M4_song_song_KHAI_DUOC_va_mac_dinh_8(db, run):
    """🔴 `M4`: hôm nay 4 **cứng**; V2 phải khai được, mặc định 8.

    ⚠️ Phải dùng danh sách **đủ dài**: `parallelism` bị kẹp xuống số phần tử
       (xin 8 luồng cho 1 phần tử là vô nghĩa). Bản đầu của bài này dùng
       `muc=[1]` nên nó **không thể** quan sát được mặc định — nó đo một tình
       huống mà giá trị cần đo không hiện ra.
    """
    from platform_core.workflow import foreach

    du_dai = list(range(20))
    mac_dinh = foreach.mo_vong(db, run_id=run.id, node_id="a", muc=du_dai,
                               max_items=50)
    khai = foreach.mo_vong(db, run_id=run.id, node_id="b", muc=du_dai,
                           max_items=50, parallelism=3)
    db.commit()
    assert mac_dinh.parallelism == 8, "mac dinh phai la 8, khong phai 4 cung"
    assert khai.parallelism == 3, "khai duoc thi phai theo lo khai"


def test_parallelism_khong_duoc_vuot_max_items(db, run):
    """Xin 50 luồng cho 3 phần tử là một con số vô nghĩa đi vào bộ xếp chỗ."""
    from platform_core.workflow import foreach

    vong = foreach.mo_vong(db, run_id=run.id, node_id="a", muc=[1, 2, 3],
                           max_items=10, parallelism=50)
    assert vong.parallelism == 3


# ── 4.4 Join ──────────────────────────────────────────────────────────────────

def test_join_ALL_ANY_N_of_M_dung_chung_MOT_co_che_voi_waitpoint(db, run):
    """⭐ Join không phải cơ chế thứ hai — nó là `waitpoint` với `policy` khác.

    Dựng một cơ chế chờ thứ hai là dựng một chỗ thứ hai để `sealed` bị quên.
    """
    from platform_core.workflow import cho_doi, join

    a = join.tao(db, run_id=run.id, owner_id="u1", che_do="ANY", so_nhanh=3)
    b = join.tao(db, run_id=run.id, owner_id="u1", che_do="ALL", so_nhanh=3)
    c = join.tao(db, run_id=run.id, owner_id="u1", che_do="N_OF_M",
                 so_nhanh=3, can=2)
    db.commit()

    assert a.required_successes == 1
    assert b.required_successes == 0 and b.so_nguon == 3 and b.sealed is False
    assert c.required_successes == 2
    assert cho_doi.da_mo(db, a.id) is False


def test_join_ANY_mo_ngay_khi_co_MOT_nhanh_xong(db, run):
    from platform_core.workflow import cho_doi, join

    j = join.tao(db, run_id=run.id, owner_id="u1", che_do="ANY", so_nhanh=3)
    cho_doi.ghi_tin_hieu(db, j.id, seq=0, status="SUCCEEDED")
    db.commit()
    assert cho_doi.da_mo(db, j.id) is True


def test_behavior_TRAN_khai_duoc(db, run):
    """`G10`: tràn thì làm gì — chặn, bỏ, hay lỗi. Phải KHAI, không mặc định ngầm."""
    from platform_core.workflow import join

    assert join.HANH_VI_TRAN >= {"CHAN", "BO_QUA", "LOI"}
    with pytest.raises(ValueError):
        join.tao(db, run_id=run.id, owner_id="u1", che_do="ANY", so_nhanh=2,
                 hanh_vi_tran="bay_ra_ngoai")


# ── 4.5 Node điều khiển KHÔNG sinh Job ───────────────────────────────────────

def test_G15_tam_node_dieu_khien_deu_KHONG_sinh_job(db):
    """🔴 Rẽ nhánh không được tạo một dòng trong sổ tiền.

    Hôm nay mỗi bước đều đi qua hàng đợi job, nên một node `IF` cũng sinh một
    job — và một job là một bút toán. Tám loại này chạy **trong** scheduler.
    """
    from platform_core.workflow.dieu_khien import LOAI_DIEU_KHIEN, sinh_job

    assert len(LOAI_DIEU_KHIEN) == 8
    assert LOAI_DIEU_KHIEN >= {"IF", "SWITCH", "MERGE", "FOREACH", "JOIN",
                               "DELAY", "SET_VAR", "NOOP"}
    for loai in LOAI_DIEU_KHIEN:
        assert sinh_job(loai) is False, f"{loai} khong duoc sinh job"


def test_node_thuong_thi_VAN_sinh_job(db):
    """Đối chứng: nếu `sinh_job` trả `False` cho mọi thứ thì bài trên vô nghĩa."""
    from platform_core.workflow.dieu_khien import sinh_job

    assert sinh_job("llm.chat") is True
    assert sinh_job("anhnoibo.generate") is True


# ── 4.6 Trần chi phí — 🔴 KHÔNG CÓ ĐỐI CHỨNG NGÀNH ───────────────────────────

def _cc_llm_chat(gia: int = 5):
    from platform_core.workflow.cong_cu import CongCu

    return {"llm.chat": CongCu(ten="llm.chat", app_slug="ltt_llm",
                               job_type="ltt_llm.chat", type_version=1,
                               params_schema={}, side_effect="external",
                               idempotency_fields=(), tinh_gia=lambda p: gia)}


def test_M8_bao_gia_kem_HAI_SO(db):
    """🔴 `M8`: báo giá phải kèm **hai** số — tối đa và ước tính.

    Một số duy nhất buộc phải chọn: nói số tối đa thì khách thấy đắt và bỏ đi;
    nói số ước tính thì khách bị bất ngờ khi bị trừ nhiều hơn. Hai số nói đúng
    thứ ta biết: *"thường khoảng X, không bao giờ quá Y"*.
    """
    from platform_core.workflow import bao_gia

    bg = bao_gia.bao_gia_do_thi({"schema": "ltt.workflow/3", "nodes": [
        {"id": "a", "type": "app.llm.chat", "params": {}, "thi_hanh": "job"},
        {"id": "b", "type": "app.llm.chat", "params": {}, "thi_hanh": "job"},
    ], "edges": []}, cong_cu=_cc_llm_chat())
    assert bg.toi_da > 0 and bg.uoc_tinh > 0
    assert bg.uoc_tinh <= bg.toi_da


# ⭐ Giá FOREACH (`max_items × thân`) VÀ giá nhánh IF lồng (`"nhanh": [...]`)
#    chuyển sang plan 04 cùng lúc node `core.foreach`/rẽ nhánh điều khiển được
#    viết lại — plan 01a không còn hình dạng đó trong `bao_gia` (đồ thị đã
#    biên dịch `ltt.workflow/3`, Task 5, biểu diễn rẽ nhánh bằng `edges` kiểu
#    `CONTROL`/`condition`, không phải `"nhanh"` lồng nhau). Ba bài đã xoá
#    khỏi tệp này (ghi vào ledger kế hoạch 01a — review round 1 22/09):
#      test_tran_ForEach_la_max_items_NHAN_than
#      test_ForEach_KHONG_khai_max_items_thi_bao_gia_TU_CHOI
#      test_nhanh_IF_tinh_theo_nhanh_DAT_NHAT


def test_node_dieu_khien_khong_cong_vao_tran(db):
    """Nhất quán với `G15`: không sinh job (`thi_hanh != "job"`) ⇒ không tốn tiền."""
    from platform_core.workflow import bao_gia

    chi_dieu_khien = bao_gia.bao_gia_do_thi({"schema": "ltt.workflow/3", "nodes": [
        {"id": "a", "type": "IF", "params": {}},
        {"id": "b", "type": "NOOP", "params": {}},
    ], "edges": []}, cong_cu={})
    assert chi_dieu_khien.toi_da == 0 and chi_dieu_khien.uoc_tinh == 0
