"""`core.set` · `core.transform` · `core.filter` · `core.aggregate` · `core.output`.

⛔ **KHÔNG THÊM HÀM NÀO NGOÀI BẢNG ĐÓNG §6.3.** P2 chốt 49 hàm trong
`ham_bieu_thuc.BANG_HAM`; bốn node dưới đây chỉ **gọi** bảng ấy. Một `aggregate`
tự viết phép `sum` là phép `sum` thứ hai trong kho, và hai phép cùng tên sẽ khác
nhau ở đúng ca biên mà không ai thử (rỗng, `null`, chuỗi lẫn số).
`test_banh_coc_aggregate_khong_tu_viet_phep` cưỡng chế điều đó.

## `core.set` và `vars` (§6.5)

`bien_vars` đã có đủ luật và đã được test ở P2: `gop_vars` (người đi sau ghi đè
người đi trước, chỉ tính **tổ tiên**, người ghi chưa `SUCCEEDED` không đóng góp)
và `kiem_ghi_xung_dot` (hai `core.set` ghi cùng khoá mà không ai là tổ tiên của
ai ⇒ **từ chối publish**). Task 6 chỉ nối dây: khai node, và gọi
`kiem_ghi_xung_dot` **ở cổng publish** — trước đó nó là một hàm không ai gọi.

## Phép này KHÔNG phủ cái gì

Không phủ `graph.outputs` khai ở cấp workflow (spec §4.1 `outputs[].from`) —
`core.output` ở đây ghi ra `run.output`, việc ánh xạ vào lược đồ `outputs` của
version thuộc về tầng API. Không chạy trên PostgreSQL thật (Task 8).
"""
from __future__ import annotations
# ruff: noqa: F811 -- imported pytest fixtures are intentionally requested below.

import ast
import pathlib

import pytest

from platform_core.workflow.cong_cu import CongCu
from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401

CC = {"text.chat": CongCu(ten="text.chat", app_slug="ltt_llm",
                          job_type="ltt_llm.chat", type_version=1,
                          params_schema={}, side_effect="external",
                          idempotency_fields=(), tinh_gia=lambda p: 3,
                          returns={"text": "text"})}


def _core(nid: str, loai: str, **params) -> dict:
    return {"id": nid, "type": f"core.{loai}", "position": {"x": 0, "y": 0},
            "params": params}


def _canh(a: str, b: str, *, kind: str = "DATA", condition: str = "") -> dict:
    return {"id": f"{a}-{b}-{condition}", "source_node": a, "target_node": b,
            "source_port": "out", "target_port": "in", "kind": kind,
            "condition": condition}


@pytest.fixture()
def lam(db, monkeypatch):
    from platform_core import credit
    from platform_core.workflow import cong_cu, dinh_nghia, tao_run
    monkeypatch.setattr(cong_cu, "tat_ca", lambda: CC)
    credit.nap(db, "u1", 10000, note="test")
    dem = {"n": 0}

    def _lam(nodes, edges):
        dem["n"] += 1
        w = dinh_nghia.tao_workflow(db, owner_id="u1", name=f"t{dem['n']}")
        dinh_nghia.luu_draft(db, w.id, revision=0, document={
            "version": 3, "pages": [{"id": "p1", "nodes": nodes,
                                     "edges": edges}]})
        v = dinh_nghia.xuat_ban_draft(db, w.id, created_by="u1", cong_cu=CC)
        w.published_version_id = v.id
        db.flush()
        run, _ = tao_run.tao_run(db, workflow=w, owner_id="u1",
                                 trigger_kind="manual",
                                 idempotency_key=f"k{dem['n']}")
        return run
    return _lam


def _chay(db, run):
    from platform_core.workflow import dong_co
    return dong_co.xu_ly_run(db, run.id, cong_cu=CC)


def _ra(db, run, nid):
    from platform_core.workflow import thi_hanh
    return thi_hanh.anh_chup_hien_tai(db, run.id, nid).output_ref


# ── core.set + vars ─────────────────────────────────────────────────────────

def test_set_ghi_bien_va_node_sau_doc_duoc(db, lam):
    run = lam([_core("s", "set", bien={"ten": '"Lan"', "tuoi": "3 + 4"}),
               _core("t", "transform", gia_tri='vars.ten + ":" + to_string(vars.tuoi)')],
              [_canh("s", "t")])
    assert _chay(db, run) == "SUCCEEDED"
    assert _ra(db, run, "s") == {"ten": "Lan", "tuoi": 7}
    assert _ra(db, run, "t")["gia_tri"] == "Lan:7"


def test_doi_chung_node_KHONG_phai_hau_due_khong_thay_bien(db, lam):
    """`gop_vars` chỉ gộp `core.set` là **tổ tiên**. Đối chứng của phép trên."""
    from platform_core.workflow import may_trang_thai as mtt, thi_hanh
    run = lam([_core("s", "set", bien={"ten": '"Lan"'}),
               _core("t", "transform", gia_tri="vars.ten")],
              [])                                   # KHONG co canh s -> t
    _chay(db, run)
    assert mtt.trang_thai_node(db, run.id, "t") == "FAILED"
    assert "vars" in thi_hanh.anh_chup_hien_tai(db, run.id, "t").error


def test_hai_set_ghi_cung_khoa_khong_ho_hang_bi_TU_CHOI_luc_publish(db, lam):
    """§6.5 `ghi_bien_xung_dot` — `bien_vars.kiem_ghi_xung_dot` nay CÓ người gọi.

    ⭐ Đây là một hàm đã được P2 viết và test **nhưng chưa ai gọi**. Một cổng
       không có người gọi là một cổng mở.
    """
    from platform_core.workflow.bien_dich import LoiBienDich
    with pytest.raises(LoiBienDich) as e:
        lam([_core("i", "if", dieu_kien="true"),
             _core("a", "set", bien={"x": "1"}),
             _core("b", "set", bien={"x": "2"})],
            [_canh("i", "a", kind="CONTROL", condition="true"),
             _canh("i", "b", kind="CONTROL", condition="false")])
    assert e.value.ma == "ghi_bien_xung_dot"


def test_hai_set_CO_quan_he_to_tien_thi_nguoi_di_sau_thang(db, lam):
    """Đối chứng: cùng hai khoá, nhưng nối tiếp nhau ⇒ hợp lệ."""
    run = lam([_core("a", "set", bien={"x": "1"}),
               _core("b", "set", bien={"x": "2"}),
               _core("t", "transform", gia_tri="vars.x")],
              [_canh("a", "b"), _canh("b", "t")])
    assert _chay(db, run) == "SUCCEEDED"
    assert _ra(db, run, "t")["gia_tri"] == 2


def test_set_khoa_bat_dau_bang_gach_duoi_bi_tu_choi(db, lam):
    """`bien_vars._thay_duoc`: khoá `_` là VÔ HÌNH với ngôn ngữ §6.

    ⛔ Nhận nó rồi lặng lẽ không thấy nó là cách tệ nhất: người khai nghĩ đã
       ghi một biến, và `keys(vars)` không kể tên nó.
    """
    from platform_core.workflow.bien_dich import LoiBienDich
    with pytest.raises(LoiBienDich):
        lam([_core("s", "set", bien={"_an": "1"})], [])


# ── core.filter ─────────────────────────────────────────────────────────────

def test_filter_giu_phan_tu_thoa_dieu_kien(db, lam):
    run = lam([_core("f", "filter", items="[1, 2, 3, 4]",
                     dieu_kien="loop.item > 2")], [])
    assert _chay(db, run) == "SUCCEEDED"
    assert _ra(db, run, "f") == {"results": [3, 4], "so_bo": 2}


def test_filter_thay_duoc_loop_index(db, lam):
    run = lam([_core("f", "filter", items='["a", "b", "c"]',
                     dieu_kien="loop.index != 1")], [])
    _chay(db, run)
    assert _ra(db, run, "f")["results"] == ["a", "c"]


def test_filter_items_khong_phai_mang_thi_FAILED(db, lam):
    from platform_core.workflow import may_trang_thai as mtt, thi_hanh
    run = lam([_core("f", "filter", items='"khong phai mang"',
                     dieu_kien="true")], [])
    _chay(db, run)
    assert mtt.trang_thai_node(db, run.id, "f") == "FAILED"
    assert "dau_vao_sai" in thi_hanh.anh_chup_hien_tai(db, run.id, "f").error


# ── core.aggregate ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("phep,items,mong", [
    ("count", "[1, 2, 3]", 3),
    ("sum", "[1, 2, 3]", 6),
    ("min", "[3, 1, 2]", 1),
    ("max", "[3, 1, 2]", 3),
    ("first", "[3, 1, 2]", 3),
    ("last", "[3, 1, 2]", 2),
    ("unique", "[1, 1, 2]", [1, 2]),
    ("flatten", "[[1], [2, 3]]", [1, 2, 3]),
])
def test_aggregate_moi_phep_la_MOT_HAM_cua_bang_dong(db, lam, phep, items, mong):
    run = lam([_core("g", "aggregate", items=items, phep=phep)], [])
    assert _chay(db, run) == "SUCCEEDED"
    assert _ra(db, run, "g")["gia_tri"] == mong


def test_aggregate_phep_ngoai_bang_bi_tu_choi_luc_publish(db, lam):
    from platform_core.workflow.bien_dich import LoiBienDich
    with pytest.raises(LoiBienDich):
        lam([_core("g", "aggregate", items="[1]", phep="tu_nghi_ra")], [])


def test_banh_coc_aggregate_khong_tu_viet_phep():
    """⛔ Mỗi phép của `core.aggregate` phải LÀ một khoá của `BANG_HAM` §6.3.

    ⭐ Bánh cóc **cắn thật**: thêm một phép không có trong bảng (vd `"trung_binh"`)
       vào `PHEP_GOP` là đủ để nó đỏ — đã tiêm thử (xem báo cáo Task 6).

    Đối chứng: nếu `PHEP_GOP` rỗng hoặc đường dẫn sai thì vòng lặp không chạy
    lần nào và phép này xanh mà không đo gì — nên khẳng định số lượng trước.
    """
    from platform_core.workflow.ham_bieu_thuc import BANG_HAM
    from platform_core.workflow.nut_loi.du_lieu import PHEP_GOP

    assert len(PHEP_GOP) >= 8, PHEP_GOP
    thieu = sorted(set(PHEP_GOP) - set(BANG_HAM))
    assert not thieu, f"phep khong co trong BANG_HAM Sec6.3: {thieu}"


# ── core.output ─────────────────────────────────────────────────────────────

def test_output_ghi_ket_qua_cua_ca_RUN(db, lam):
    run = lam([_core("t", "transform", gia_tri='"xin chao"'),
               _core("o", "output", ten="loi_chao",
                     gia_tri="nodes.t.output.gia_tri")],
              [_canh("t", "o")])
    assert _chay(db, run) == "SUCCEEDED"
    assert _ra(db, run, "o") == {"ten": "loi_chao", "gia_tri": "xin chao"}
    from platform_core.workflow import ket_qua_run
    assert ket_qua_run.doc(db, run.id) == {"loi_chao": "xin chao"}


def test_hai_output_cung_ten_bi_tu_choi_luc_publish(db, lam):
    """Hai node cùng ghi một tên đầu ra ⇒ kết quả run phụ thuộc thứ tự chạy."""
    from platform_core.workflow.bien_dich import LoiBienDich
    with pytest.raises(LoiBienDich) as e:
        lam([_core("a", "output", ten="x", gia_tri="1"),
             _core("b", "output", ten="x", gia_tri="2")], [])
    assert e.value.ma == "trung_ten_output"


# ── Bánh cóc chung: node lõi KHÔNG ĐƯỢC tốn tiền ────────────────────────────

def test_banh_coc_gia_node_loi_khop_BO_THI_HANH():
    """⛔ Một node lõi tốn tiền là một bút toán mà `cau_noi` không quản.

    Và một node `inline` không có bộ thi hành là một node đứng READY tới khi
    hết TTL 20 giờ — `dang_ky` đã chặn lúc dựng, đây là phép kiểm của chính
    cái chặn ấy (đối chứng: đếm số node trước, để một sổ rỗng không xanh giả).
    ⚠️ Bản đầu (Task 6) khẳng định **mọi** node lõi miễn phí. Nó đúng khi sổ
       chỉ có `core.*`, và sai ngay khi `ai.*` vào sổ (việc A) — vì `ai.llm`
       **phải** `theo_registry`. Đó là một phép kiểm đo nhầm đối tượng: thứ
       quyết định giá là **bộ thi hành**, không phải "node lõi".

    ⛔ Nay đo HAI CHIỀU, và cả hai đều là tiền: inline/run_con **tốn tiền**
       là một bút toán `cau_noi` không quản; job **miễn phí** là node chạy
       tài nguyên thật mà không ai trả — lỗ đi ngược chiều, và dễ lọt hơn
       vì nó không làm ai kêu.
    """
    from platform_core.workflow import nut_loi
    so = nut_loi.tat_ca()
    assert len(so) >= 12, sorted(so)
    for ten, nd in so.items():
        if nd.thi_hanh == "job":
            assert nd.gia.kieu != "mien_phi", (ten, nd.gia)
            continue
        assert nd.gia.kieu == "mien_phi", (ten, nd.gia)
        if nd.thi_hanh == "inline" and nd.kind != "trigger":
            assert nut_loi.bo_thi_hanh(ten) is not None, ten


def test_banh_coc_tham_so_bieu_thuc_deu_di_qua_cong_to_tien():
    """Mọi tham số kiểu `bieu_thuc` phải được `bien_dich` trích tham chiếu.

    ⭐ Cổng tổ tiên §6.2 là *"một cổng an ninh về tiền"*, và Task 5 đã đo rằng
       tham số biểu thức TRẦN của node lõi từng đi lọt qua nó. Bánh cóc này
       chặn ca ấy tái phát bằng cách hỏi thẳng mã: `_tham_chieu_node_loi` là
       hàm DUY NHẤT đọc `KIEU_BIEU_THUC`, và nó phải gọi `trich_tham_chieu`.
    """
    nguon = pathlib.Path("platform_core/workflow/bien_dich.py").read_text(
        encoding="utf-8")
    cay = ast.parse(nguon)
    ham = next((n for n in ast.walk(cay) if isinstance(n, ast.FunctionDef)
                and n.name == "_tham_chieu_node_loi"), None)
    assert ham is not None, "doi ten ham? banh coc nay dang do mot thu khong con"
    goi = {ast.unparse(c.func) for c in ast.walk(ham)
           if isinstance(c, ast.Call)}
    assert "trich_tham_chieu" in goi, goi
