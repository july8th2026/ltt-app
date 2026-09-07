"""HM-1 — mối nối `apps/lttvideo/cong/`: một giao ước, hai hiện thực.

## Vì sao mối nối này tồn tại

V2.1 đạt độ phủ **2/46 model** không phải vì WanGP khó, mà vì mỗi model tốn một
hồ sơ rút tay — và hồ sơ ấy tồn tại vì tầng gọi WanGP (`wangp_client`) trộn lẫn
*cách nói chuyện* với *biết gì về model*. Mối nối tách hai thứ ấy ra:

    tầng trên  ──►  May (8 phương thức)  ──►  MayThat   (HTTP tới pod)
                                          └─►  MayGiaLap (phát lại bản ghi)

⇒ Sổ đăng ký · danh mục tác vụ · đường ống · GUI đều xây và nghiệm thu được
  **không cần pod, không cần GPU**.

## Hai phép kiểm ở đây canh hai mệnh đề khác nhau

1. `MayGiaLap` thực hiện **đủ** giao ước — thiếu một phương thức thì tầng trên
   vỡ ở *runtime* chứ không vỡ ở test, và vỡ đúng lúc có người dùng thật.
2. Thiếu bản ghi thì nó **NÉM**, không trả rỗng. Đây mới là phép kiểm quan
   trọng: một máy giả lập trả rỗng biến *"chưa ghi"* thành *"model không có
   năng lực đó"*, và cái nhầm ấy đi thẳng vào GUI mà không để lại dấu vết nào.
"""
from __future__ import annotations

import json

import pytest


def _thanh_vien_giao_uoc(giao_uoc) -> set[str]:
    """Tên các phương thức một Protocol đòi hỏi.

    `typing.get_protocol_members` có từ 3.13; `__protocol_attrs__` là đường lùi
    cho bản cũ hơn. Đọc qua API công khai trước — thuộc tính gạch dưới là chi
    tiết hiện thực và nó đã đổi tên giữa các bản Python.
    """
    import typing

    lay = getattr(typing, "get_protocol_members", None)
    if lay is not None:
        return set(lay(giao_uoc))
    return set(getattr(giao_uoc, "__protocol_attrs__", ()))


def test_giao_uoc_khai_dung_TAM_phuong_thuc():
    """⛔ Chốt **kích cỡ** bề mặt, không chỉ chốt sự tồn tại của nó.

    Bề mặt WanGP rất rộng (33 model type, hậu kỳ, âm thanh, LoRA…). Mối nối chỉ
    có giá trị khi nó **hẹp**: mỗi phương thức thêm vào là một đường mà tầng
    trên có thể lệ thuộc, và là một đường `MayGiaLap` phải giả lập.

    Thêm phương thức thứ chín là một quyết định, nên nó phải làm phép kiểm này
    đỏ để người thêm dừng lại một nhịp — chứ không trôi vào âm thầm.
    """
    from apps.lttvideo.cong.giao_uoc import May

    assert _thanh_vien_giao_uoc(May) == {
        "liet_ke_model", "so_do", "mac_dinh", "kha_dung",
        "gui_viec", "tien_do", "ket_qua", "huy",
    }


def test_may_gia_lap_thuc_hien_DU_giao_uoc():
    """Thiếu một phương thức thì tầng trên vỡ ở runtime, không vỡ ở test."""
    from apps.lttvideo.cong.giao_uoc import May
    from apps.lttvideo.cong.may_gia_lap import MayGiaLap

    thieu = [t for t in _thanh_vien_giao_uoc(May)
             if not callable(getattr(MayGiaLap, t, None))]
    assert not thieu, f"MayGiaLap thieu: {thieu}"


def test_thieu_ban_ghi_thi_NEM_chu_khong_tra_rong(tmp_path):
    """🔑 Phép kiểm trung tâm của HM-1.

    Trả rỗng khi thiếu dữ liệu là biến một **khoảng trống đã biết** thành một
    **câu trả lời sai tự tin** — đúng cơ chế đã làm `CLAUDE.md` phải gỡ bảng
    trạng thái chép tay: nó không có cách nào tự biết mình đã cũ.
    """
    from apps.lttvideo.cong.giao_uoc import LoiMay
    from apps.lttvideo.cong.may_gia_lap import MayGiaLap

    m = MayGiaLap(goc=tmp_path)
    with pytest.raises(LoiMay, match="chua co ban ghi"):
        m.so_do("t2v_2_2")


def test_ban_ghi_deu_khai_NGUON_va_SHA(tmp_path):
    """Mỗi bản ghi phải tự nói nó là khuôn tạm hay ghi từ máy thật.

    ⭐ Không có trường này thì tới HM-7 không ai phân biệt được bản ghi nào đã
      được thay bằng dữ liệu thật — và một khuôn sót lại trông y hệt dữ liệu
      thật, chỉ khác là nó sai.
    """
    from apps.lttvideo.cong.may_gia_lap import MayGiaLap

    (tmp_path / "so_do__x.json").write_bytes(json.dumps(
        {"nguon": "khuon", "sha_wangp": "1e1dd275", "du_lieu": {"a": 1}},
        ensure_ascii=False).encode("utf-8"))
    m = MayGiaLap(goc=tmp_path)
    assert m.so_do("x") == {"a": 1}
    assert m.nguon_cua("so_do__x") == "khuon"


def test_ban_ghi_thieu_NGUON_bi_tu_choi(tmp_path):
    """⛔ Đối chứng cho phép kiểm trên. Nếu thiếu `nguon` mà vẫn đọc được thì
    trường ấy chỉ là trang trí, và HM-7/B4 (*"không bản ghi nào còn khuôn"*) sẽ
    xanh vĩnh viễn mà không canh gì."""
    from apps.lttvideo.cong.giao_uoc import LoiMay
    from apps.lttvideo.cong.may_gia_lap import MayGiaLap

    (tmp_path / "so_do__x.json").write_bytes(
        json.dumps({"du_lieu": {"a": 1}}).encode("utf-8"))
    with pytest.raises(LoiMay, match="nguon"):
        MayGiaLap(goc=tmp_path).so_do("x")


def test_vong_doi_mot_viec_chay_TRON_VEN_khong_can_pod(tmp_path):
    """Đường ống (HM-5) phải chạy hết được trong test. Nếu `MayGiaLap` không
    đưa nổi một việc từ `gui_viec` tới `ket_qua` thì HM-5 vẫn phải chờ pod, và
    cả kế hoạch "giả lập trước" mất ý nghĩa."""
    from apps.lttvideo.cong.may_gia_lap import MayGiaLap

    m = MayGiaLap(goc=tmp_path, kich_ban=[
        {"pha": "nap_model", "phan_tram": 10.0, "xong": False},
        {"pha": "khu_nhieu", "phan_tram": 90.0, "xong": False},
        {"pha": "xong", "phan_tram": 100.0, "xong": True},
    ])
    ma = m.gui_viec({"model_type": "t2v_2_2", "prompt": "mot dong song"})
    thay = [m.tien_do(ma) for _ in range(3)]
    assert [t["pha"] for t in thay] == ["nap_model", "khu_nhieu", "xong"]
    assert thay[-1]["xong"] is True

    kq = m.ket_qua(ma)
    assert kq["tep"] and not kq["loi"] and kq["huy"] is False


def test_huy_lam_ket_qua_bao_HUY_chu_khong_bao_loi(tmp_path):
    """Huỷ là một kết cục **bình thường**, không phải một lỗi.

    ⛔ Nhầm hai thứ này ở tầng dưới thì tầng trên hoàn credit cho một lần huỷ
    rồi lại ghi một dòng lỗi — nền tảng đã có `POST /jobs/{id}/cancel` lo việc
    hoàn tiền, nên một dòng lỗi thừa ở đây là một báo động giả vĩnh viễn.
    """
    from apps.lttvideo.cong.may_gia_lap import MayGiaLap

    m = MayGiaLap(goc=tmp_path)
    ma = m.gui_viec({"model_type": "t2v_2_2", "prompt": "x"})
    m.huy(ma)
    kq = m.ket_qua(ma)
    assert kq["huy"] is True
    assert not kq["loi"], "huy KHONG phai loi"


def test_may_gia_lap_KHONG_GHI_vao_cay_kho():
    """🔴 Lỗi thật, tự tôi gây ra rồi tự bắt trong cùng một hạng mục.

    Bản đầu của `ket_qua()` ghi `gia_lap_<ma>.mp4` vào `self.goc`, mà `self.goc`
    mặc định là `apps/lttvideo/ban_ghi/` — **nằm trong kho**.

    ⭐ Vì sao nó đắt hơn vẻ ngoài: một tệp lạ sinh ra trong cây giữa lượt gate
      làm chính lượt gate ấy mất giá trị (`cay_da_doi_giua_chung`), và một lượt
      gate đầy đủ mất **10 phút** để nói cho ta biết điều đó. Đây đúng cái bẫy
      `docs/BAY_TRONG_CONG_CHAT_LUONG.md` đã ghi: phép kiểm ghi vào cây tự phá
      lượt chứa nó.

    ⇒ `ban_ghi/` là **chỉ đọc lúc chạy**. Đầu ra đi vào thư mục tạm.
    """
    import pathlib

    from apps.lttvideo.cong.may_gia_lap import GOC_BAN_GHI, MayGiaLap

    m = MayGiaLap()                       # CO Y dung goc mac dinh
    ma = m.gui_viec({"model_type": "t2v_2_2", "prompt": "x"})
    tep = pathlib.Path(m.ket_qua(ma)["tep"][0]).resolve()

    assert GOC_BAN_GHI.resolve() not in tep.parents, (
        f"MayGiaLap ghi vao cay kho: {tep}")
    kho = pathlib.Path(__file__).resolve().parents[1]
    assert kho not in tep.parents, f"ghi vao trong kho: {tep}"
