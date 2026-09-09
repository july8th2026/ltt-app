"""ForEach `ghi_ket_qua` giành phần tử NGUYÊN TỬ — điều kiện nằm trong SQL.

## Mệnh đề

`R1` của chương trình migration 4-bot hỏi: *"ForEach hoàn tất một phần tử có
nguyên tử không?"* Câu trả lời trước 2026-09-09 là **không**, và cách nó sai thì
tinh vi hơn một lỗi thường:

    row = db.get(...)        # doc
    if row.xong: return False  # xet
    row.xong = True          # ghi

Ba câu, ba thời điểm. Hai worker cùng đọc `xong=False` thì **cả hai** đi qua cửa
và **cả hai trả `True`**. Docstring của hàm hứa *"bản ghi đầu tiên thắng"*; thứ
thực sự xảy ra là **bản ghi cuối cùng thắng**.

⚠️ Và hậu quả không dừng ở một giá trị bị đè. `so_luot_chay()` đếm hàng
   `xong=True`, nên một phần tử chạy **hai** lần vẫn hiện là **một** lượt —
   ngưỡng `M7` ("100 kết quả, 0 lượt lặp") sẽ báo **đạt** trong khi tiền đã tiêu
   hai lần. Một phép đo che đúng thứ nó sinh ra để đo.

## ⛔ Vì sao KHÔNG kiểm bằng hai luồng thật

Phép kiểm đa luồng cho câu trả lời **không tất định**: nó xanh khi hai luồng
tình cờ không chồng nhau, và nó cần PostgreSQL để có hai transaction thật —
tức một `pytest.skip` trên mọi máy không có Postgres, và một chỗ bỏ qua là một
chỗ **không canh gì cả** (`tools/check_bo_qua.py`).

⭐ Thứ làm cuộc đua **không thể xảy ra** không phải là "hai luồng không chồng
   nhau", mà là **điều kiện `xong = false` nằm trong câu `UPDATE`**. Mệnh đề ấy
   kiểm được tất định, một luồng: chạy đúng câu lệnh ấy hai lần và đọc
   `rowcount`. Đó là kiểm **cơ chế**, không phải kiểm **triệu chứng**.

## Đối chứng

`test_ban_cu_TRUOT_phep_kiem_nay` dựng lại đúng ba câu của bản cũ và chứng minh
nó **không** đạt bất biến. Thiếu nó, cả tệp này xanh với cả bản hỏng — và một
phép kiểm xanh với bản hỏng thì không đo gì (memory *không đối chứng thì số 0
không phải phát hiện*).
"""
from __future__ import annotations

import pytest
from sqlalchemy import update

from platform_core.models import ForeachMuc
from platform_core.workflow import foreach


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'fe1101.db').as_posix()}")
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
def vong(db):
    from platform_core.workflow import dinh_nghia, thi_hanh

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="FE")
    db.commit()
    v = dinh_nghia.xuat_ban(db, wf.id, {"schema_version": 1, "nodes": [],
                                        "edges": []}, created_by="u1")
    db.commit()
    r = thi_hanh.tao_run(db, workflow_id=wf.id, version_id=v.id,
                         owner_id="u1", trigger_kind="manual")
    db.commit()
    vg = foreach.mo_vong(db, run_id=r.id, node_id="n1", muc=["a", "b", "c"],
                         max_items=10)
    db.commit()
    return vg


def _giành_thô(db, vong, chi_so: int, gia_tri) -> int:
    """Đúng câu `UPDATE` mà `ghi_ket_qua` chạy — trả `rowcount`."""
    kq = db.execute(
        update(ForeachMuc)
        .where(ForeachMuc.vong_id == vong.id,
               ForeachMuc.chi_so == chi_so,
               ForeachMuc.xong.is_(False))
        .values(ket_qua={"v": gia_tri}, xong=True)
        .execution_options(synchronize_session=False))
    db.flush()
    return int(kq.rowcount)


# ── Bất biến ────────────────────────────────────────────────────────────────

def test_chi_MOT_luot_gianh_duoc_mot_chi_so(db, vong):
    """Hai lượt cùng nhắm một chỉ số: một thắng, một thua. CSDL phân xử."""
    assert _giành_thô(db, vong, 0, "worker-A") == 1
    assert _giành_thô(db, vong, 0, "worker-B") == 0


def test_ke_thua_KHONG_de_len_ket_qua_cua_ke_thang(db, vong):
    """Đè kết quả là làm mất một lượt ĐÃ TÍNH TIỀN — và không ai phát hiện,
    vì hàng vẫn ở đó với một giá trị trông hợp lý."""
    foreach.ghi_ket_qua(db, vong, chi_so=0, ket_qua="worker-A")
    assert foreach.ghi_ket_qua(db, vong, chi_so=0, ket_qua="worker-B") is False
    db.commit()
    assert foreach.gom_ket_qua(db, vong) == [{"v": "worker-A"}]


def test_ke_thua_KHONG_lam_phong_so_luot_chay(db, vong):
    """`M7` đếm bằng `so_luot_chay()`; một lượt thua không được thành một lượt."""
    foreach.ghi_ket_qua(db, vong, chi_so=0, ket_qua="A")
    foreach.ghi_ket_qua(db, vong, chi_so=0, ket_qua="B")
    db.commit()
    assert foreach.so_luot_chay(db, vong) == 1


def test_chi_so_chua_xong_dung_NGAY_SAU_khi_ghi(db, vong):
    """Bản sao trong bộ nhớ của phiên không được nói khác CSDL.

    ⚠️ Đây là cạm bẫy của chính bản vá: `UPDATE` đi thẳng xuống CSDL, nên đối
       tượng đã nạp trong phiên vẫn mang `xong=False`. Không đuổi cache thì
       `chi_so_chua_xong()` trả về một chỉ số **vừa mới ghi xong** — và bộ khôi
       phục sẽ chạy lại nó.
    """
    foreach.ghi_ket_qua(db, vong, chi_so=1, ket_qua="xong roi")
    assert foreach.chi_so_chua_xong(db, vong) == [0, 2]


def test_chi_so_khong_ton_tai_tra_False(db, vong):
    assert foreach.ghi_ket_qua(db, vong, chi_so=99, ket_qua="x") is False


# ── Đối chứng: bản cũ phải TRƯỢT ────────────────────────────────────────────

def _ban_cu(phien, vong_id: str, chi_so: int, gia_tri, *,
            xong_luc_doc: bool) -> bool:
    """Bản `ghi_ket_qua` trước 2026-09-09: **xét trên một bản đọc**, rồi ghi.

    `xong_luc_doc` là giá trị worker này đọc được **lúc nó đọc** — đó chính là
    hình dạng của khiếm khuyết, và là thứ duy nhất cần dựng lại. Truyền vào chứ
    không đọc lại ở đây, vì đọc lại là hỏi CSDL ở một thời điểm khác và như thế
    thì đã không còn là bản cũ nữa.
    """
    if xong_luc_doc:
        return False
    row = phien.get(ForeachMuc, (vong_id, chi_so))
    if row is None:
        return False
    row.ket_qua = {"v": gia_tri}
    row.xong = True
    phien.flush()
    return True


def test_ban_cu_TRUOT_phep_kiem_nay(db, vong):
    """Dựng lại bản cũ và chứng minh nó KHÔNG đạt bất biến.

    Không có phép kiểm này thì cả tệp trên xanh với **cả bản hỏng**: mọi khẳng
    định ở trên đi qua `ghi_ket_qua`, và một hàm hỏng vẫn trả `True` rồi `False`
    khi chạy **tuần tự trong một phiên**.

    ## ⚠️ Cuộc đua dựng lại bằng BẢN ĐỌC, không bằng luồng

    Khiếm khuyết của bản cũ không nằm ở "hai luồng chạy cùng lúc" — nó nằm ở chỗ
    **cửa được xét trên một giá trị đọc lúc T, còn phép ghi xảy ra lúc T+Δ**.
    Dựng lại đúng hình dạng ấy thì không cần luồng nào, và kết quả tất định.

    ⛔ Tôi đã thử hai cách trước khi tới đây, và cả hai đều **không** dựng lại
       được — đáng ghi lại vì chúng cho một âm tính giả:

       1. hai `db.get()` trong **một** phiên: identity map của SQLAlchemy trả về
          **cùng một đối tượng**, nên bản đọc thứ hai *chính là* bản thứ nhất và
          đã mang `xong=True`;
       2. hai `Session` riêng: bản sao trong bộ nhớ của phiên B vẫn bị làm mới
          trước khi tới cửa, nên B cũng thấy `xong=True`.

    🔑 Cả hai lần, **một lớp cache đã che mất khiếm khuyết** — và đó cũng chính
       là lý do khiếm khuyết sống sót qua `test_959`: phép kiểm luỹ đẳng ở đó
       chạy trong một phiên, và trong một phiên thì bản cũ *thật sự* luỹ đẳng.
    """
    # Cả hai worker đọc khi hàng còn `xong=False` — cảnh bình thường của
    # `parallelism=8`, không phải một ca hiếm.
    doc_cua_A = db.get(ForeachMuc, (vong.id, 0)).xong
    doc_cua_B = db.get(ForeachMuc, (vong.id, 0)).xong
    assert doc_cua_A is False and doc_cua_B is False

    assert _ban_cu(db, vong.id, 0, "worker-A", xong_luc_doc=doc_cua_A) is True
    db.commit()

    # 🔴 Đây là khiếm khuyết: B đi qua cửa bằng bản đọc của chính nó — đã cũ —
    #    và trả `True`. Hai lượt cùng "thắng" một phần tử.
    assert _ban_cu(db, vong.id, 0, "worker-B",
                   xong_luc_doc=doc_cua_B) is True, (
        "ban cu dang KHONG con hong theo cach nay - doi chung nay het han, "
        "hay viet lai no cho khop cach hong that su")
    db.commit()

    # Hậu quả: kết quả của A biến mất, và `so_luot_chay` vẫn đếm MỘT.
    assert foreach.gom_ket_qua(db, vong) == [{"v": "worker-B"}]
    assert foreach.so_luot_chay(db, vong) == 1


def test_ban_moi_DUNG_trong_dung_canh_ay(db, vong):
    """Cùng cảnh — hai bản đọc cùng thấy "chưa xong" — nhưng qua bản hiện hành.

    ⭐ Đây mới là dạng mạnh nhất của bất biến: không phải *"gọi hai lần thì lần
       hai trả False"* (bản cũ cũng đạt), mà **"hai bản đọc cùng thấy chưa xong
       thì vẫn chỉ một lượt thắng"** — vì điều kiện nằm trong câu `UPDATE`, chứ
       không nằm trong bản đọc của ai cả.
    """
    doc_cua_A = db.get(ForeachMuc, (vong.id, 0)).xong
    doc_cua_B = db.get(ForeachMuc, (vong.id, 0)).xong
    assert doc_cua_A is False and doc_cua_B is False

    assert foreach.ghi_ket_qua(db, vong, chi_so=0, ket_qua="worker-A") is True
    db.commit()
    # B vẫn "tin" rằng phần tử chưa xong — và điều đó không còn quan trọng nữa.
    assert foreach.ghi_ket_qua(db, vong, chi_so=0, ket_qua="worker-B") is False
    db.commit()

    assert foreach.gom_ket_qua(db, vong) == [{"v": "worker-A"}]
    assert foreach.so_luot_chay(db, vong) == 1
