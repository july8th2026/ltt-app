"""`connector_store` — bộ nhớ bền của piece (spec §11.4).

## Vì sao bảng này đáng một tệp test riêng

Nó giữ **con trỏ poll**. Một lỗi ở đây không trông như một lỗi: nó trông như
một trigger đột nhiên bắn lại **toàn bộ lịch sử** — tức tạo lại mọi run cũ,
tức **tiêu credit thật** của khách. Cùng hạng với bốn lỗ TIỀN của phase 4.

Ba bất biến được đo ở đây, mỗi cái vì một ca hỏng cụ thể:

1. **Cách ly theo `owner_id`.** Hai khách dùng cùng một piece phải không bao
   giờ đọc được store của nhau.
2. **`pham_vi` là một ĐƯỜNG.** `trigger:<id>` và `run:<id>` cùng id ⇒ hai hàng
   khác nhau. Khoá theo id trần là đúng lỗi đã lặp ba lần ở phase 4.
3. **Trần chạm ⇒ NÉM.** Một `put` bị bỏ im lặng là một con trỏ poll không bao
   giờ tiến, tức poll lần sau tạo lại run cho cùng bản ghi.
"""
from __future__ import annotations

import pytest

from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401


def test_doc_pham_vi_rong_tra_dict_rong(db):  # noqa: F811
    from platform_core.workflow import connector_store as cs
    assert cs.doc(db, owner_id="u1", pham_vi=cs.pham_vi_run("r1")) == {}


def test_put_roi_doc_lai_dung_gia_tri(db):  # noqa: F811
    from platform_core.workflow import connector_store as cs
    pv = cs.pham_vi_trigger("t1")
    cs.ap(db, owner_id="u1", pham_vi=pv,
          ops=[{"op": "put", "key": "da_thay", "value": ["a", "b"]}])
    assert cs.doc(db, owner_id="u1", pham_vi=pv) == {"da_thay": ["a", "b"]}


def test_put_lan_hai_GHI_DE_khong_tao_hang_thu_hai(db):  # noqa: F811
    from platform_core.models import ConnectorStore
    from platform_core.workflow import connector_store as cs
    pv = cs.pham_vi_trigger("t1")
    cs.ap(db, owner_id="u1", pham_vi=pv,
          ops=[{"op": "put", "key": "k", "value": 1}])
    cs.ap(db, owner_id="u1", pham_vi=pv,
          ops=[{"op": "put", "key": "k", "value": 2}])
    assert cs.doc(db, owner_id="u1", pham_vi=pv) == {"k": 2}
    assert db.query(ConnectorStore).count() == 1


def test_delete_xoa_dung_mot_khoa(db):  # noqa: F811
    from platform_core.workflow import connector_store as cs
    pv = cs.pham_vi_run("r1")
    cs.ap(db, owner_id="u1", pham_vi=pv,
          ops=[{"op": "put", "key": "a", "value": 1},
               {"op": "put", "key": "b", "value": 2}])
    cs.ap(db, owner_id="u1", pham_vi=pv, ops=[{"op": "delete", "key": "a"}])
    assert cs.doc(db, owner_id="u1", pham_vi=pv) == {"b": 2}


def test_HAI_KHACH_cung_pham_vi_KHONG_doc_duoc_cua_nhau(db):  # noqa: F811
    """🔴 Cách ly credential/dữ liệu giữa hai người dùng (spec §18.3).

    `pham_vi` do hệ thống sinh, nhưng hai khách **có thể** có cùng chuỗi phạm
    vi nếu ai đó đổi cách sinh id. `owner_id` nằm trong khoá duy nhất chính là
    để ngày ấy không thành một lần rò.
    """
    from platform_core.workflow import connector_store as cs
    pv = cs.pham_vi_trigger("CUNG-MOT-ID")
    cs.ap(db, owner_id="u1", pham_vi=pv,
          ops=[{"op": "put", "key": "k", "value": "cua-u1"}])
    cs.ap(db, owner_id="u2", pham_vi=pv,
          ops=[{"op": "put", "key": "k", "value": "cua-u2"}])
    assert cs.doc(db, owner_id="u1", pham_vi=pv) == {"k": "cua-u1"}
    assert cs.doc(db, owner_id="u2", pham_vi=pv) == {"k": "cua-u2"}


def test_pham_vi_la_DUONG_trigger_va_run_cung_id_KHONG_dung_nhau(db):  # noqa: F811
    """⛔ `trigger:x` ≠ `run:x`. Khoá theo id trần thì hai chủ thể đụng nhau —
    đúng lỗi đã lặp ba lần ở phase 4 (`wakeup`, `node_run`, `dedupe_key`)."""
    from platform_core.workflow import connector_store as cs
    cs.ap(db, owner_id="u1", pham_vi=cs.pham_vi_trigger("x"),
          ops=[{"op": "put", "key": "k", "value": "T"}])
    cs.ap(db, owner_id="u1", pham_vi=cs.pham_vi_run("x"),
          ops=[{"op": "put", "key": "k", "value": "R"}])
    assert cs.doc(db, owner_id="u1", pham_vi=cs.pham_vi_trigger("x")) == {"k": "T"}
    assert cs.doc(db, owner_id="u1", pham_vi=cs.pham_vi_run("x")) == {"k": "R"}


def test_vuot_TRAN_KHOA_thi_NEM_khong_bo_im_lang(db):  # noqa: F811
    from platform_core.workflow import connector_store as cs
    pv = cs.pham_vi_trigger("t-tran")
    cs.ap(db, owner_id="u1", pham_vi=pv,
          ops=[{"op": "put", "key": f"k{i}", "value": i}
               for i in range(cs.TRAN_KHOA)])
    with pytest.raises(cs.LoiStore):
        cs.ap(db, owner_id="u1", pham_vi=pv,
              ops=[{"op": "put", "key": "mot-khoa-nua", "value": 1}])


def test_gia_tri_qua_lon_thi_NEM(db):  # noqa: F811
    from platform_core.workflow import connector_store as cs
    with pytest.raises(cs.LoiStore):
        cs.ap(db, owner_id="u1", pham_vi=cs.pham_vi_run("r"),
              ops=[{"op": "put", "key": "k",
                    "value": "x" * (cs.TRAN_GIA_TRI_BYTE + 10)}])


def test_op_la_thi_NEM_khong_nuot(db):  # noqa: F811
    """⛔ Một `op` không biết bị bỏ qua nghĩa là runner và Python đã lệch giao
    thức mà không ai biết — và store sẽ sai lặng lẽ."""
    from platform_core.workflow import connector_store as cs
    with pytest.raises(cs.LoiStore):
        cs.ap(db, owner_id="u1", pham_vi=cs.pham_vi_run("r"),
              ops=[{"op": "increment", "key": "k", "value": 1}])


def test_xoa_pham_vi_chi_xoa_pham_vi_do(db):  # noqa: F811
    from platform_core.workflow import connector_store as cs
    cs.ap(db, owner_id="u1", pham_vi=cs.pham_vi_trigger("a"),
          ops=[{"op": "put", "key": "k", "value": 1}])
    cs.ap(db, owner_id="u1", pham_vi=cs.pham_vi_trigger("b"),
          ops=[{"op": "put", "key": "k", "value": 2}])
    assert cs.xoa_pham_vi(db, owner_id="u1",
                          pham_vi=cs.pham_vi_trigger("a")) == 1
    assert cs.doc(db, owner_id="u1", pham_vi=cs.pham_vi_trigger("b")) == {"k": 2}
