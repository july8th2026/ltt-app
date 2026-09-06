"""ghi_nho.py — ChatLTT nhớ gì về người dùng, và họ xem/sửa/xoá được. (P07 b1)

## 🔴 Tệp này CỐ TÌNH chưa có đường tự động ghi

Kế hoạch tổng đòi *"ba tầng memory tách bạch, người dùng **thấy và sửa được**,
không âm thầm lưu mọi thứ"*. Vế cuối là vế chịu lực, và nó quyết định **thứ tự
xây**: hiện ra và xoá được **trước**, tự động ghi **sau**.

⭐ Một hệ ghi nhớ ghi âm thầm là một hệ mà người dùng **không biết mình đã nói
   gì cho nó**. Ngày họ phát hiện, thứ họ mất không phải một tính năng mà là
   niềm tin — và niềm tin không có nút hoàn tác.

⇒ Ở bước 1 chỉ có **một** đường ghi: `them()`, do người dùng bấm. `test_829`
  chốt bằng phép quét AST rằng không hàm nào khác trong `apps/chatltt` dựng một
  `ChatlttGhiNho` — không bằng một dòng ghi chú, vì ghi chú không đỏ được.

## Ba tầng, và vì sao chúng KHÔNG phải ba phạm vi tìm kiếm của P06

    P06 pham vi tim kiem   luot / hoi thoai / project   <- TAI LIEU nam o dau
    P07 tang ghi nho       hoi thoai / du an / tai khoan <- TRI THUC dung o dau

Kế hoạch tổng nói thẳng *"không trộn với memory"*. Hai trục khác nhau: tài liệu
là thứ khách **đưa vào**, ghi nhớ là thứ ta **rút ra về** khách. Trộn chúng thì
xoá một tài liệu sẽ xoá một điều ta biết, hoặc ngược lại.

## Xoá là xoá THẬT

Xem docstring của `ChatlttGhiNho`. Tóm tắt: khi khách bấm xoá một điều ta biết
về họ, ý họ là *"đừng biết điều này nữa"* — một bản ghi mềm vẫn đọc được là đã
không giữ lời hứa ấy.
"""
from __future__ import annotations

from sqlalchemy import select

from apps.chatltt.tables import ChatlttGhiNho, NGUON_NGUOI_DUNG, TANG_GHI_NHO

#: Trần ký tự một mục. Một "điều cần nhớ" dài hơn thế là một tài liệu — và tài
#: liệu có đường riêng (P06), có tính tiền riêng, có trích dẫn riêng.
TRAN_KY_TU = 2_000

#: Trần số mục mỗi tầng, mỗi phạm vi.
#:
#: ⚠️ Trần đặt DƯỚI nhu cầu bình thường biến thất bại thành MẶC ĐỊNH. 200 mục ở
#:    tầng tài khoản là rất nhiều cho một người dùng thật; nó chặn ca bệnh lý
#:    (một vòng lặp ghi tự động sau này) chứ không chặn ca thường.
TRAN_SO_MUC = 200

TANG_HOI_THOAI, TANG_DU_AN, TANG_TAI_KHOAN = TANG_GHI_NHO


class KhongDuocPhep(Exception):
    """Mục không thuộc người gọi."""


class DauVaoSai(ValueError):
    """Tầng lạ, nội dung rỗng, hoặc vượt trần."""


def _kiem(tang: str, pham_vi_id: str, noi_dung: str) -> tuple[str, str, str]:
    tang = str(tang or "")
    if tang not in TANG_GHI_NHO:
        raise DauVaoSai(f"tang phai la mot trong {list(TANG_GHI_NHO)}")
    noi = str(noi_dung or "").strip()
    if not noi:
        raise DauVaoSai("noi dung khong duoc rong")
    if len(noi) > TRAN_KY_TU:
        raise DauVaoSai(f"noi dung dai {len(noi)} ky tu, tran {TRAN_KY_TU}")

    pv = str(pham_vi_id or "")
    if tang == TANG_TAI_KHOAN:
        # ⛔ Tang tai khoan KHONG co pham vi. Nhan mot `pham_vi_id` o day roi bo
        #    qua no la nhan mot y dinh roi lam khac — nguoi goi se tuong da gioi
        #    han pham vi trong khi khong.
        if pv:
            raise DauVaoSai("tang tai khoan khong nhan pham_vi_id")
    elif not pv:
        raise DauVaoSai(f"tang {tang!r} bat buoc co pham_vi_id")
    return tang, pv, noi


def them(db, *, user_id: str, tang: str, noi_dung: str,
         pham_vi_id: str = "") -> ChatlttGhiNho:
    """Thêm một mục. **Đường ghi DUY NHẤT**, và nó do người dùng khởi xướng.

    ⛔ Ngày ai đó thêm một đường ghi thứ hai — một bộ rút trích tự động, một
       hook sau mỗi lượt — đó là một **quyết định sản phẩm**, không phải một
       bản vá. Nó đổi lời hứa "không âm thầm lưu mọi thứ".
    """
    tang, pv, noi = _kiem(tang, pham_vi_id, noi_dung)

    dem = len(cua_toi(db, user_id=user_id, tang=tang, pham_vi_id=pv))
    if dem >= TRAN_SO_MUC:
        raise DauVaoSai(
            f"da co {dem} muc o tang {tang!r}, tran {TRAN_SO_MUC} — xoa bot truoc")

    m = ChatlttGhiNho(user_id=str(user_id), tang=tang, pham_vi_id=pv,
                      noi_dung=noi, nguon=NGUON_NGUOI_DUNG)
    db.add(m)
    db.flush()
    return m


def cua_toi(db, *, user_id: str, tang: str = "",
            pham_vi_id: str = "") -> list[ChatlttGhiNho]:
    """Mục của **một** người. Lọc thêm theo tầng/phạm vi nếu có.

    ⛔ `user_id` là điều kiện, không phải một bộ lọc tuỳ chọn: không có đường
       nào gọi hàm này mà không nêu chủ.
    """
    q = select(ChatlttGhiNho).where(ChatlttGhiNho.user_id == str(user_id))
    if tang:
        q = q.where(ChatlttGhiNho.tang == str(tang))
        if tang != TANG_TAI_KHOAN and pham_vi_id:
            q = q.where(ChatlttGhiNho.pham_vi_id == str(pham_vi_id))
    return list(db.execute(q.order_by(ChatlttGhiNho.created_at)).scalars())


def mot(db, *, user_id: str, muc_id: str) -> ChatlttGhiNho | None:
    """Một mục theo id. `None` cho người lạ — không phân biệt "cấm" với "không
    có", vì phân biệt là tự khai rằng id ấy tồn tại."""
    m = db.get(ChatlttGhiNho, str(muc_id))
    return m if m is not None and m.user_id == str(user_id) else None


def sua(db, *, user_id: str, muc_id: str, noi_dung: str) -> ChatlttGhiNho:
    """Sửa nội dung một mục. Không đổi được tầng/phạm vi.

    ⭐ Đổi tầng nghĩa là *"điều này giờ đúng ở chỗ khác"* — về bản chất là một
       mục khác. Cho sửa tầng tại chỗ thì lịch sử của mục nói dối: nó trông như
       luôn thuộc tầng mới.
    """
    m = mot(db, user_id=user_id, muc_id=muc_id)
    if m is None:
        raise KhongDuocPhep("muc khong thuoc nguoi goi")
    _kiem(m.tang, m.pham_vi_id, noi_dung)
    m.noi_dung = str(noi_dung).strip()
    db.flush()
    return m


def xoa(db, *, user_id: str, muc_id: str) -> bool:
    """Xoá **thật**. `False` khi không có quyền hoặc không tồn tại.

    ⛔ Không xoá mềm. Xem docstring `ChatlttGhiNho`: khi khách bấm xoá một điều
       ta biết về họ, ý họ là *"đừng biết điều này nữa"*.
    """
    m = mot(db, user_id=user_id, muc_id=muc_id)
    if m is None:
        return False
    db.delete(m)
    db.flush()
    return True


def xoa_het(db, *, user_id: str, tang: str = "", pham_vi_id: str = "") -> int:
    """Xoá mọi mục (của một tầng/phạm vi nếu nêu). Trả về số mục đã xoá.

    ⭐ Cửa này tồn tại vì *"xoá từng cái một"* không phải một lời hứa thật khi
       có 200 mục. Một người muốn ChatLTT quên hết về mình phải làm được điều đó
       trong một thao tác.
    """
    ds = cua_toi(db, user_id=user_id, tang=tang, pham_vi_id=pham_vi_id)
    for m in ds:
        db.delete(m)
    db.flush()
    return len(ds)
