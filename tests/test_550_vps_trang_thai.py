"""VPS V2 Pha 01 — mô hình trạng thái: vòng đời · điện · tác vụ · sức khoẻ.

Bộ này canh **mệnh đề**, không canh cách viết. Cụ thể là bốn mệnh đề mà bản một-cột
cũ không viết ra được, và mỗi cái đều là một lỗi thật đã xảy ra:

1. bốn khái niệm phải **cùng đúng một lúc** được;
2. `khong_ro` **không bao giờ** được biến thành `da_tat`;
3. `bi_treo` là chuyện **tiền**, nên nó phải sống sót qua mọi thứ xảy ra với điện;
4. hình chiếu `trang_thai` **không được** phép sai lệch khỏi mô hình.

Và một phép kiểm không nói về hành vi mà nói về **hai bản sao**: bảng ánh xạ trong
`trang_thai_may.TU_MA_CU` với bảng `_BACKFILL` trong migration. Hai bản sao lệch
nhau cho ra một hàng đã di trú và một hàng dựng trong RAM hành xử khác nhau — và
lớp lỗi đó không có test hành vi nào bắt được, vì mỗi bên chạy đúng theo bảng của nó.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from apps.vps import trang_thai_may as tt

MIGRATION = pathlib.Path("alembic/versions/20260909_1000_vps_v2_tach_trang_thai.py")


class _May:
    """Máy trần — cố ý CHỈ có mã cũ, để test luôn cả lớp tương thích."""

    def __init__(self, trang_thai="dang_chay"):
        self.id = "may-1"
        self.trang_thai = trang_thai
        self.ly_do = ""


# ── 1. Tổ hợp mà bản cũ không viết ra được ───────────────────────────────────

def test_bon_khai_niem_cung_dung_mot_luc():
    """Hợp đồng đòi biểu diễn được: hoạt động · muốn tắt · thấy đang chạy · đang tắt.

    Đây LÀ lý do tồn tại của cả pha này. Bản một-cột phải chọn một trong bốn.
    """
    may = tt.dat(_May(), vong_doi=tt.HOAT_DONG, dien_mong_muon=tt.TAT,
                 dien_quan_sat=tt.CHAY, tac_vu=tt.DANG_TAT)
    assert (may.vong_doi, may.dien_mong_muon, may.dien_quan_sat, may.tac_vu) == \
        (tt.HOAT_DONG, tt.TAT, tt.CHAY, tt.DANG_TAT)
    # Và hình chiếu phải nói theo thứ ĐO ĐƯỢC, không theo ý định: máy vẫn đang chạy.
    assert may.trang_thai == "dang_chay"


# ── 2. `khong_ro` không được thành `da_tat` ──────────────────────────────────

def test_quan_sat_khong_ro_khong_bien_thanh_da_tat():
    """Máy khách muốn chạy, Proxmox không trả lời ⇒ KHÔNG được nói "đã tắt".

    `da_tat` là một khẳng định: với khách nó nghĩa là "bấm Bật đi", với vòng thu
    phí nó nghĩa là máy vẫn thuộc diện thu. Phát ra khẳng định đó khi ta vừa hỏi
    thất bại là nói dối theo hướng làm người đọc hành động sai.
    """
    may = tt.dat(_May(), vong_doi=tt.HOAT_DONG, dien_mong_muon=tt.CHAY,
                 dien_quan_sat=tt.KHONG_RO)
    assert may.trang_thai == "dang_chay"


def test_khong_ro_ma_khach_muon_tat_thi_chieu_theo_y_dinh():
    may = tt.dat(_May(), vong_doi=tt.HOAT_DONG, dien_mong_muon=tt.TAT,
                 dien_quan_sat=tt.KHONG_RO)
    assert may.trang_thai == "da_tat"


def test_ghi_quan_sat_that_bai_dat_mat_lien_lac_va_van_dong_dau_thoi_gian():
    """Một lần hỏi thất bại vẫn là một sự kiện có thời điểm.

    Không đóng dấu thì `qua_cu()` không phân biệt được "chưa thử bao giờ" với
    "vừa thử xong và trượt", mà hai cái đó cần hai phản ứng khác nhau.
    """
    from datetime import datetime, timezone
    luc = datetime(2026, 9, 9, tzinfo=timezone.utc)
    may = tt.ghi_quan_sat(_May(), tt.KHONG_RO, now=luc)
    assert may.suc_khoe == tt.MAT_LIEN_LAC and may.quan_sat_luc == luc


def test_ghi_quan_sat_thanh_cong_dat_khoe():
    from datetime import datetime, timezone
    luc = datetime(2026, 9, 9, tzinfo=timezone.utc)
    may = tt.ghi_quan_sat(_May(), tt.CHAY, now=luc)
    assert may.suc_khoe == tt.KHOE and may.dien_quan_sat == tt.CHAY


# ── 3. `bi_treo` là chuyện tiền ──────────────────────────────────────────────

def test_bi_treo_song_sot_qua_moi_thay_doi_ve_dien():
    """Máy hết hạn thanh toán mà ai đó bật nó lên thì nó VẪN đang bị treo.

    Bản cũ không giữ được điều này: `trang_thai` là một chuỗi, nên ghi
    `dang_chay` lên đó là **xoá mất** sự thật rằng khách đang nợ tiền — và một
    máy nợ tiền mà hệ thống quên mất là một máy dùng miễn phí.
    """
    may = tt.dat(_May("bi_treo"), dien_quan_sat=tt.CHAY,
                 dien_mong_muon=tt.CHAY)
    assert may.vong_doi == tt.BI_TREO
    assert may.trang_thai == "bi_treo", "dien khong duoc de len vong doi"


def test_may_da_xoa_khong_bao_gio_hien_dang_chay():
    may = tt.dat(_May("da_xoa"), dien_quan_sat=tt.CHAY,
                 dien_mong_muon=tt.CHAY)
    assert may.trang_thai == "da_xoa"


# ── 4. Hình chiếu không được lệch khỏi mô hình ───────────────────────────────

@pytest.mark.parametrize("cu", sorted(tt.TU_MA_CU))
def test_hang_cu_nang_cap_roi_chieu_lai_ra_dung_ma_cu(cu):
    """Mỗi mã cũ, sau khi suy ra mô hình mới, phải chiếu lại ra **chính nó**.

    Đây là điều kiện để 18 tệp test và 7 template không đổi hành vi ở pha này.
    Một mã không quay về được chính nó nghĩa là ánh xạ mất thông tin.
    """
    may = tt.chuan_hoa(_May(cu))
    assert tt.chieu(may.vong_doi, may.dien_quan_sat, may.dien_mong_muon) == cu


def test_dat_luon_tinh_lai_hinh_chieu():
    may = tt.dat(_May("da_tat"), dien_mong_muon=tt.CHAY,
                 dien_quan_sat=tt.CHAY)
    assert may.trang_thai == "dang_chay"


def test_ma_la_di_ve_loi_khong_ve_hoat_dong():
    """Một mã ta không hiểu phải rơi về `loi`, không rơi về "mọi thứ bình thường".

    `loi` vẫn điều khiển được và vẫn hiện lý do cho khách; `hoat_dong` là một
    khẳng định rằng máy khoẻ — và ta vừa gặp thứ ta không hiểu.
    """
    may = tt.chuan_hoa(_May("mot_ma_la"))
    assert may.vong_doi == tt.LOI and may.trang_thai == "mot_ma_la"
    assert tt.dat(may).trang_thai == "loi", "dat() phai chuan hoa hinh chieu"


def test_chuan_hoa_khong_dap_len_mo_hinh_da_co():
    """Đã có mô hình mới thì hình chiếu KHÔNG được kéo ngược nó về.

    Nếu không, một máy `hoat_dong` mang hình chiếu cũ `bi_treo` (đúng lúc giữa
    hai lệnh gán) sẽ bị lôi ngược thành `bi_treo` — tức hình chiếu điều khiển
    ngược lại nguồn sự thật, đúng thứ ADR-01 sinh ra để chặn.
    """
    may = _May("bi_treo")
    may.vong_doi = tt.HOAT_DONG
    may.dien_mong_muon, may.dien_quan_sat = tt.CHAY, tt.CHAY
    tt.chuan_hoa(may)
    assert may.vong_doi == tt.HOAT_DONG


# ── 5. Giá trị sai phải nổ tại chỗ gọi ───────────────────────────────────────

@pytest.mark.parametrize("kw", [
    {"vong_doi": "khong_ton_tai"},
    {"dien_mong_muon": "khong_ro"},      # ý định thì KHÔNG được phép mơ hồ
    {"dien_quan_sat": "ngu"},
    {"tac_vu": "dang_bay"},
    {"suc_khoe": "tuyet_voi"},
])
def test_gia_tri_sai_nem_ngay(kw):
    with pytest.raises(ValueError):
        tt.dat(_May(), **kw)


def test_bat_dau_tac_vu_khong_nhan_chuoi_rong():
    """`bat_dau_tac_vu(may, "")` là một câu vô nghĩa — phải chặn, đừng im lặng."""
    with pytest.raises(ValueError):
        tt.bat_dau_tac_vu(_May(), tt.KHONG_CO)


def test_bat_dau_tac_vu_khong_doi_quan_sat():
    """Máy đang tắt DỞ thì vẫn đang chạy cho tới khi đo được ngược lại.

    Đây chính xác là chỗ bản cũ nói dối: nó ghi `da_tat` ngay lúc bấm nút.
    """
    may = tt.bat_dau_tac_vu(_May("dang_chay"), tt.DANG_TAT)
    assert may.dien_quan_sat != tt.TAT and may.trang_thai == "dang_chay"
    assert tt.dang_ban(may) is True
    assert tt.dang_ban(tt.ket_thuc_tac_vu(may)) is False


# ── 6. Độ tươi ───────────────────────────────────────────────────────────────

def test_chua_do_lan_nao_tinh_la_qua_cu():
    """Chưa đo bao giờ và đo từ tuần trước cho cùng một lượng hiểu biết: không có gì."""
    assert tt.qua_cu(tt.chuan_hoa(_May())) is True
    assert tt.tuoi_quan_sat(tt.chuan_hoa(_May())) is None


def test_vua_do_xong_thi_khong_qua_cu():
    from datetime import datetime, timedelta, timezone
    luc = datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc)
    may = tt.ghi_quan_sat(_May(), tt.CHAY, now=luc)
    assert tt.qua_cu(may, now=luc + timedelta(seconds=60)) is False
    assert tt.qua_cu(may, now=luc + timedelta(seconds=tt.QUA_CU_SAU_S + 1)) is True


def test_nguong_qua_cu_khong_duoc_chat_hon_nhip_bao_tri():
    """Ngưỡng đặt DƯỚI nhịp đo là một cảnh báo luôn bật.

    Vòng bảo trì chạy mỗi `bao_tri_moi_giay`; đặt ngưỡng chặt hơn nhịp đó thì
    **mọi** máy đều "cũ" trong gần hết khoảng giữa hai lượt — và một cảnh báo
    luôn bật là một cảnh báo người ta học cách bỏ qua.
    """
    from apps.vps.manifest import MANIFEST
    assert tt.QUA_CU_SAU_S >= MANIFEST.bao_tri_moi_giay / 4


# ── 7. Hai bản sao của bảng ánh xạ phải khớp ─────────────────────────────────

def _backfill_trong_migration() -> dict:
    """Đọc `_BACKFILL` bằng AST, **không** import migration.

    Import một migration kéo theo `alembic.op` (chỉ sống trong ngữ cảnh chạy di
    trú) và có thể chạy mã ở mức module. Đọc AST trả lời đúng câu đang hỏi —
    *"hằng số đó viết gì"* — mà không mở cửa nào khác.
    """
    cay = ast.parse(MIGRATION.read_text(encoding="utf-8"))
    for nut in cay.body:
        muc = getattr(nut, "targets", [])
        if muc and getattr(muc[0], "id", "") == "_BACKFILL":
            return ast.literal_eval(nut.value)
    raise AssertionError("khong tim thay _BACKFILL trong migration")


def test_bang_anh_xa_trong_ma_va_trong_migration_phai_giong_het():
    """Hai bản sao cố ý — nhưng lệch nhau thì không ai phát hiện được bằng hành vi.

    Một hàng đã di trú đi theo bảng của migration; một hàng dựng trong RAM đi
    theo bảng của `trang_thai_may`. Cả hai đều chạy "đúng" theo bảng của mình,
    nên mọi test hành vi vẫn xanh trong khi hai máy giống hệt nhau hành xử khác nhau.
    """
    assert _backfill_trong_migration() == tt.TU_MA_CU


def test_migration_co_duong_lui():
    """`downgrade` gỡ đúng những cột `upgrade` thêm — không thừa, không thiếu."""
    nguon = MIGRATION.read_text(encoding="utf-8")
    them = set(__import__("re").findall(r'sa\.Column\(\s*\n?\s*"([a-z_]+)"', nguon))
    for cot in them:
        assert cot in nguon.split("def downgrade")[1], f"{cot} khong duoc go"
