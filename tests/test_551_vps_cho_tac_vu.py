"""VPS V2 Pha 02 — bộ chờ tác vụ Proxmox: "nhận việc" ≠ "xong việc".

Mỗi ca ở đây tương ứng một cách mà bản cũ nói dối, và **không ca nào** kiểm được
bằng cách so thứ tự gọi hàm — đó chính là lý do bộ này tồn tại.

⚠️ Đối chứng nằm ở `test_bo_cho_that_su_cho`: nó chứng minh fake **có** trạng thái
thật, tức là một bản sửa hỏng sẽ đỏ. Không có nó thì mọi ca dưới đây có thể xanh
vì fake dễ dãi chứ không vì mã đúng.
"""
from __future__ import annotations

import pytest

from apps.vps.services import tac_vu
from tests.fixtures.vps_proxmox_gia import ProxmoxGia, nhip_gia


def _px(**kw) -> ProxmoxGia:
    return ProxmoxGia(**kw)


# ── Đối chứng: fake có thật sự bất đồng bộ không ─────────────────────────────

def test_bo_cho_that_su_cho():
    """Máy KHÔNG được đổi trạng thái ngay khi Proxmox nhận lệnh.

    Đây là đối chứng của cả tệp. Nếu ca này xanh nhầm (fake đổi điện ngay lúc
    nhận lệnh) thì mọi ca còn lại mất hết ý nghĩa, vì bản sai cũng sẽ xanh.
    """
    px = _px(dien="running", buoc=3)
    px.tat_mem(px.vmid)
    assert px.trang_thai_vm(px.vmid)["status"] == "running", \
        "nhan lenh KHONG duoc lam may tat ngay"


# ── cho_xong ─────────────────────────────────────────────────────────────────

def test_cho_xong_tra_ve_khi_tac_vu_ket_thuc_tot():
    px = _px(buoc=3)
    upid = px.bat(px.vmid)
    ket = tac_vu.cho_xong(px, upid, nhip=nhip_gia())
    assert ket["status"] == "stopped" and ket["exitstatus"] == "OK"
    assert px.dien == "running"


def test_exitstatus_khac_OK_la_that_bai_du_status_la_stopped():
    """Proxmox trả `status=stopped` cho CẢ thành công lẫn thất bại.

    `exitstatus` là chỗ duy nhất phân biệt. Bỏ qua nó là ghi "đã xong" cho một
    việc vừa hỏng — và đó đúng là hình dạng của lỗi V-02.
    """
    px = _px(buoc=2)
    upid = px._nhan_viec("bat", exitstatus="unable to start VM")
    with pytest.raises(tac_vu.TacVuThatBai) as loi:
        tac_vu.cho_xong(px, upid, nhip=nhip_gia())
    assert "unable to start VM" in str(loi.value)


def test_tac_vu_that_bai_thi_the_gioi_that_KHONG_doi():
    px = _px(dien="stopped", buoc=2)
    upid = px._nhan_viec("bat", exitstatus="loi",
                         khi_xong=px._dat_dien("running"))
    with pytest.raises(tac_vu.TacVuThatBai):
        tac_vu.cho_xong(px, upid, nhip=nhip_gia())
    assert px.dien == "stopped"


def test_qua_han_nem_TacVuQuaHan_chu_khong_phai_ThatBai():
    """Quá hạn ≠ thất bại, và gộp hai cái là mời người ta làm lại một việc đang chạy.

    Một tác vụ quá hạn có thể vẫn đang chạy và vẫn sẽ thành công. Đường xử lý
    đúng là hỏi lại thế giới thật, không phải bắn thêm một lệnh nữa.
    """
    px = _px(buoc=10_000)
    upid = px.bat(px.vmid)
    with pytest.raises(tac_vu.TacVuQuaHan) as loi:
        tac_vu.cho_xong(px, upid, han_s=0, nhip=nhip_gia())
    assert not isinstance(loi.value, tac_vu.TacVuThatBai)


def test_mang_chop_mot_lan_khong_lam_hong_ca_viec():
    """Một lần đọc hỏng không được huỷ một việc đã chạy được nửa đường."""
    px = _px(buoc=3)
    upid = px.bat(px.vmid)
    px.doc_hong_con = 2                    # dưới trần DOC_HONG_TOI_DA
    assert tac_vu.cho_xong(px, upid, nhip=nhip_gia())["exitstatus"] == "OK"


def test_doc_hong_lien_tiep_qua_tran_thi_bo_cuoc():
    """Có trần, chứ không chịu đựng vô hạn.

    Một endpoint hỏng vĩnh viễn mà cứ hỏi mãi là một vòng lặp im lặng giữ worker
    cho tới khi hết hạn — mất cả một suất worker cho một thứ đã biết là hỏng.
    """
    px = _px(buoc=3)
    upid = px.bat(px.vmid)
    px.doc_hong_con = 99
    with pytest.raises(tac_vu.KhongDocDuoc):
        tac_vu.cho_xong(px, upid, nhip=nhip_gia())


def test_upid_rong_nem_ngay():
    with pytest.raises(tac_vu.TacVuLoi):
        tac_vu.cho_xong(_px(), "", nhip=nhip_gia())


# ── doc_dien / cho_dien ──────────────────────────────────────────────────────

@pytest.mark.parametrize("pve,cua_ta", [
    ("running", "chay"), ("stopped", "tat"),
    ("paused", "tam_dung"), ("suspended", "tam_dung"),
])
def test_doc_dien_dich_dung_ma_cua_proxmox(pve, cua_ta):
    assert tac_vu.doc_dien(_px(dien=pve), 200) == cua_ta


def test_doc_dien_khong_hoi_duoc_tra_khong_ro_chu_khong_nem():
    """Câu hỏi là "máy đang thế nào"; trả lời trung thực khi mù là "không biết".

    Ném ngoại lệ ở đây buộc mọi chỗ gọi phải bọc `try`, và chỗ nào quên sẽ suy ra
    `tat` — đúng cái sai mà mô hình trạng thái mới sinh ra để chặn.
    """
    assert tac_vu.doc_dien(_px(vmid=1), 999) == "khong_ro"


def test_cho_dien_tra_ve_khi_may_that_su_toi_noi():
    px = _px(dien="running", buoc=1)
    upid = px.tat_mem(px.vmid)
    tac_vu.cho_xong(px, upid, nhip=nhip_gia())
    assert tac_vu.cho_dien(px, px.vmid, "tat", nhip=nhip_gia()) == "tat"


def test_cho_dien_qua_han_neu_may_khong_toi_noi():
    px = _px(dien="running")
    with pytest.raises(tac_vu.DienKhongDat) as loi:
        tac_vu.cho_dien(px, px.vmid, "tat", han_s=0, nhip=nhip_gia())
    # Thông điệp phải nói máy đang KẸT Ở ĐÂU, không chỉ nói "hỏng".
    assert "'chay'" in str(loi.value) and "'tat'" in str(loi.value)


# ── cho_va_xac_minh — ca quan trọng nhất ─────────────────────────────────────

def test_tac_vu_OK_ma_may_khong_toi_noi_van_la_that_bai():
    """Windows hiện hộp thoại "có muốn lưu không" và không tắt.

    Proxmox nhận `shutdown`, gửi ACPI, tác vụ kết thúc **OK** — mà máy vẫn chạy.
    Chỉ kiểm `exitstatus` thôi thì kết luận "đã tắt" cho một máy đang chạy.

    Mọi test so thứ tự gọi hàm đều bỏ lọt ca này, vì thứ tự gọi hàm hoàn toàn
    đúng.
    """
    px = _px(dien="running", buoc=1)
    upid = px._nhan_viec("tat_mem", exitstatus="OK", khi_xong=None)
    with pytest.raises(tac_vu.DienKhongDat):
        tac_vu.cho_va_xac_minh(px, upid, px.vmid, "tat", han_dien_s=0,
                               nhip=nhip_gia())


def test_cho_va_xac_minh_duong_thanh_cong():
    px = _px(dien="stopped", buoc=2)
    upid = px.bat(px.vmid)
    assert tac_vu.cho_va_xac_minh(px, upid, px.vmid, "chay",
                                  nhip=nhip_gia()) == "chay"


def test_cho_va_xac_minh_khong_xac_minh_truoc_khi_tac_vu_xong():
    """Xác minh phải chạy SAU khi chờ, không phải trước.

    Đảo thứ tự thì nó đọc trạng thái **cũ** và kết luận sai ngay lập tức: máy
    đang chạy, ta vừa gửi lệnh bật, và nó báo "đã bật" trong khi tác vụ chưa
    chạy xong bước nào.
    """
    px = _px(dien="running", buoc=4)
    upid = px.tat_mem(px.vmid)
    # Trước khi chờ: máy vẫn chạy. Nếu `cho_va_xac_minh` đọc điện trước, nó sẽ
    # thấy `chay` và ném ngay — nên ca này xanh chứng minh nó chờ trước.
    assert tac_vu.cho_va_xac_minh(px, upid, px.vmid, "tat",
                                  nhip=nhip_gia()) == "tat"


# ── Hằng số phải nhất quán với phần còn lại của hệ ───────────────────────────

def test_han_cho_moi_job_deu_ngan_hon_tran_cua_chinh_job_do():
    """Trần chờ phải NGẮN hơn `max_runtime_s` của **từng** job, không phải nói chung.

    Hai kiểu chết nhìn giống nhau trong log — "job hết hạn" và "tác vụ Proxmox
    hết hạn" — nhưng cần hai cách xử lý khác nhau. Để bộ chờ hết hạn TRƯỚC thì
    job còn kịp ghi lại lý do thật, hoàn credit, và dọn dẹp.

    ⚠️ Ca này **đã bắt được một lỗi có sẵn**: hằng số cũ `jobs.CHO_TAC_VU_S`
       là 1200 giây, dùng chung cho cả `vps.destroy` mà trần chỉ **600**. Phép
       kiểm duyệt theo TỪNG job type, nên thêm một job mới có trần ngắn cũng
       không tái tạo lại được nó.
    """
    from apps.vps.manifest import MANIFEST
    for job_type, tran in MANIFEST.max_runtime_s.items():
        assert tac_vu.han_theo_job(job_type) < tran, job_type


def test_han_theo_job_cho_job_la_van_co_tran():
    """Một job type lạ phải rơi về mặc định, không rơi về vô hạn."""
    assert tac_vu.han_theo_job("khong_ton_tai") == tac_vu.HAN_MAC_DINH_S


def test_ma_dien_cua_bo_cho_khop_voi_mo_hinh_trang_thai():
    """Bộ chờ và mô hình trạng thái phải nói cùng một thứ tiếng.

    Hai bảng từ vựng lệch nhau thì `cho_dien(..., "chay")` không bao giờ khớp,
    và triệu chứng là một timeout khó hiểu chứ không phải một lỗi rõ ràng.
    """
    from apps.vps import trang_thai_may as tt
    assert set(tac_vu._TU_PROXMOX.values()) | {"khong_ro"} <= tt.DIEN_QUAN_SAT
