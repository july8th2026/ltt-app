"""
test_841 — giá và job của vòng nghiên cứu. (H44 B6 bước 3)

## Mệnh đề quyết định: KHÔNG THU HAI LẦN

`13_KE_HOACH_B6_NGHIEN_CUU.md` §2 D3 viết *"quyết toán theo số lượt thật sự
chạy"*, và làm đúng chữ ấy ở tầng job là **thu hai lần**: mỗi lượt model đã được
`runtime_noi_bo.luong` giữ rồi hoàn theo token thật (`billing.updated`). Vòng
nghiên cứu không làm gì tốn tiền ngoài những lượt ấy — nó đọc `chatltt_doan` của
chính người hỏi rồi ghép chữ.

⇒ `gia_nghien_cuu.credit_cost` là **0**, và `jobs._chay_nghien_cuu` **không** trả
  khoá `credit_cost`. Hai chốt dưới đây giữ cả hai đầu, vì một số 0 trông y hệt
  một chỗ quên — và ngày ai đó "sửa" nó, chỉ có một phép kiểm nói được vì sao nó
  cố ý.

⭐ Bài học `san-lam-tron-la-mot-tang-khac-voi-bang-gia`: bảng giá đúng mà tiền
   thu ra sai 6,4 lần. Câu phải hỏi là *"một lượt điển hình bị trừ bao nhiêu,
   cộng HẾT mọi tầng?"*

## Mệnh đề thứ hai: phân nhánh theo KHOÁ KHAI

`registry.credit_for()` gọi **một** `credit_cost(params)` cho cả app và chữ ký
không mang `job_type`. Cách dễ là suy từ hình dạng tham số — đúng cái §2 D1 cấm.
Ở đây khoá `viec` được khai trong `params_schema` của **mọi** tool, nên
`validate_tool_params` điền sẵn và không ai phải nhớ truyền.
"""
from __future__ import annotations

import pytest

from apps.chatltt import gia as GIA, gia_nghien_cuu as GNC, jobs as J
from apps.chatltt.manifest import MANIFEST


# ── 1. Không thu hai lần ───────────────────────────────────────────────────

def test_gia_job_nghien_cuu_la_KHONG():
    """🔴 Một số dương ở đây là thu hai lần cho cùng một lượt model."""
    assert GNC.credit_cost({"viec": "nghien_cuu", "tran_vong": 3}) == 0


class _DbGia:
    """CSDL giả: chỉ trả về một hội thoại thuộc `chu`."""

    def __init__(self, chu: str = "u1", alias: str = "ltt_llm"):
        self._hoi = type("H", (), {"user_id": chu, "model_alias": alias})()

    def get(self, _lop, _id):
        return self._hoi

    def commit(self):
        pass


def _chay_gia(monkeypatch, bc):
    """Chạy `_chay_nghien_cuu` với vòng nghiên cứu ĐƯỢC THAY, để phép kiểm này
    đo đúng thứ nó nói: **hình dạng kết quả job**, không phải vòng lặp."""
    from apps.chatltt.services import nghien_cuu as NC

    monkeypatch.setattr(NC, "chay", lambda **k: bc)
    monkeypatch.setattr(J, "_voi_db", lambda ham: ham(_DbGia()))
    return J.handle({"viec": GIA.VIEC_NGHIEN_CUU, "owner_id": "u1",
                     "conversation_id": "c1", "cau_hoi": "dieu khoan"})


def test_ket_qua_job_KHONG_mang_credit_cost(monkeypatch):
    """`job_runner._quyet_toan_credit` thu theo đúng khoá này.

    ⛔ Đây là nửa còn lại của cùng một mệnh đề: giá 0 lúc **nộp** mà job lại báo
       một `credit_cost` lúc **xong** thì khách vẫn bị trừ hai lần.
    """
    from apps.chatltt.services.nghien_cuu import BaoCao

    ra = _chay_gia(monkeypatch, BaoCao(cau_hoi="dieu khoan"))
    assert "credit_cost" not in ra, "job bao mot gia — day la tang thu THU HAI"
    assert ra["phien_ban_gia"] == GNC.PHIEN_BAN_GIA


def test_ket_qua_job_KHONG_lo_doan_id_cua_nguon_ra_ngoai_trich_dan(monkeypatch):
    """Trích dẫn đi ra nguyên vẹn; `chu` của nguồn thì KHÔNG.

    ⭐ Nội dung đoạn đã nằm trong `khang_dinh[].chu`. Đổ thêm toàn văn nguồn
       vào kết quả job là nhân đôi dữ liệu khách trong một bản ghi job.
    """
    from apps.chatltt.services.nghien_cuu import BaoCao
    from apps.chatltt.services.nguon import Nguon

    n = Nguon(loai="doan_tai_lieu", chu="TOAN VAN DOAN TAI LIEU",
              trich_dan={"doan_id": "d1", "tep_id": "t1", "trang": 3})
    ra = _chay_gia(monkeypatch, BaoCao(cau_hoi="x", nguon=[n]))
    assert ra["nguon"] == [{"loai": "doan_tai_lieu",
                            "trich_dan": {"doan_id": "d1", "tep_id": "t1",
                                          "trang": 3}}]


def test_uoc_tran_chi_de_HIEN_va_tang_theo_vong():
    """Ước trần là số hiện ra trước khi bấm, không phải số bị giữ."""
    assert GNC.uoc_tran(1) > 0
    assert GNC.uoc_tran(3) > GNC.uoc_tran(1)


def test_uoc_tran_CAO_hon_gia_that_cua_tang_job():
    """Ước phải cao hơn, không được thấp — cùng luật `gia_trich.uoc_tran`."""
    assert GNC.uoc_tran(3) > GNC.credit_cost({"viec": "nghien_cuu"})


# ── 2. Phân nhánh theo khoá KHAI, không theo hình dạng ─────────────────────

def test_MOI_tool_cua_app_deu_khai_khoa_viec():
    """⛔ Thiếu một cái thì `credit_cost` của nó phải ĐOÁN — và đoán là thứ §2
    D1 cấm sau khi `gpt-researcher` #1846 suy trạng thái từ `len(...)`."""
    thieu = [t.name for t in MANIFEST.tools
             if GIA.KHOA_VIEC not in (t.params_schema or {})]
    assert thieu == [], f"tool chua khai `{GIA.KHOA_VIEC}`: {thieu}"


def test_moi_viec_khai_ra_deu_co_trong_BANG_GIA():
    """Bánh cóc hai chiều: thêm một tool mà quên bảng giá ⇒ đỏ ở đây."""
    khai = set()
    for t in MANIFEST.tools:
        o = (t.params_schema or {}).get(GIA.KHOA_VIEC) or {}
        khai |= set(o.get("values") or ())
    assert khai == set(GIA.BANG_GIA), (
        f"lech: khai={sorted(khai)} bang_gia={sorted(GIA.BANG_GIA)}")


def test_so_viec_bang_so_job_type():
    """Mỗi việc một job_type. Lệch số ⇒ có một job không ai tính giá được."""
    assert len(GIA.BANG_GIA) == len(MANIFEST.job_types)


@pytest.mark.parametrize("params", [{}, {"viec": ""}, {"viec": "viec_la"},
                                    {"tep_id": "t1", "so_byte": 10}])
def test_viec_khong_khai_thi_NEM_chu_khong_doan(params):
    """🔴 Ca cuối là ca nguy hiểm: tham số **đúng hình dạng** của trích, nhưng
    không khai việc. Một bộ suy-theo-hình-dạng sẽ vui vẻ tính giá trích."""
    with pytest.raises(GIA.ViecLa):
        GIA.credit_cost(params)


# ── 3. Worker phân nhánh CÙNG một khoá ─────────────────────────────────────

def test_handle_viec_LA_thi_nem():
    with pytest.raises(J.LoiTrich):
        J.handle({"viec": "viec_khong_ton_tai", "owner_id": "u1"})


def test_handle_KHONG_CHU_thi_nem_truoc_moi_thu():
    """⛔ Một job không chủ đọc `chatltt_doan` của "người dùng rỗng" và trả về
    rỗng một cách trông rất bình thường — nên phải chặn sớm và ồn ào."""
    with pytest.raises(J.LoiTrich):
        J.handle({"viec": GIA.VIEC_NGHIEN_CUU, "conversation_id": "c1",
                  "cau_hoi": "x"})


@pytest.mark.parametrize("thieu", ["conversation_id", "cau_hoi"])
def test_nghien_cuu_thieu_pham_vi_hoac_cau_hoi_thi_nem(thieu):
    p = {"viec": GIA.VIEC_NGHIEN_CUU, "owner_id": "u1",
         "conversation_id": "c1", "cau_hoi": "dieu khoan"}
    p[thieu] = ""
    with pytest.raises(J.LoiNghienCuu):
        J.handle(p)


# ── 4. Bản khai của tool nghiên cứu ────────────────────────────────────────

def _tool_nc():
    return next(t for t in MANIFEST.tools if t.name == "chatltt.nghien_cuu")


def test_pham_vi_la_BAT_BUOC_trong_ban_khai():
    """🔴 `tim_doan.tim` lọc theo CẢ `user_id` và `conversation_id`. Một lệnh
    nghiên cứu không phạm vi là một lệnh không ai kiểm được nó đọc gì."""
    o = (_tool_nc().params_schema or {}).get("conversation_id") or {}
    assert o.get("required") is True


def test_tran_vong_khong_vuot_duoc_tran_cua_chinh_no():
    """⭐ Người dùng đề nghị ĐỘ BỀN, không đề nghị ĐỊA CHỈ — cùng luật
    `thi_hanh(boi_canh=…)`. Một tham số nâng được trần của chính nó thì trần
    ấy không phải một trần."""
    from apps.chatltt.services import nghien_cuu as NC

    o = (_tool_nc().params_schema or {}).get("tran_vong") or {}
    assert int(o["max"]) == NC.TRAN_VONG


def test_tool_nghien_cuu_CHUA_mo_cho_khach_hay_cho_model():
    """Bốn cổng vẫn đóng: bước 4 mới mở, và mở sau một cờ riêng."""
    from apps.chatltt.services import chieu_tool, chinh_sach

    t = _tool_nc()
    assert t.customer_visible is False
    assert t.api_exposed is False
    assert "chatltt.nghien_cuu" not in chieu_tool.CHO_MODEL_GOI
    assert "chatltt.nghien_cuu" not in chinh_sach.CONG_CU_CHO_PHEP
