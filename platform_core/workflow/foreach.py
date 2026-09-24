"""ForEach: `max_items` bắt buộc · `parallelism` khai được · khôi phục theo CHỈ SỐ.

Nguồn thiết kế: `27_29 §4.3` (`G13`), ngưỡng `M7` và `M4`.

🔴 **`M7`** — *100 phần tử, crash giữa chừng → **100 kết quả, 0 lượt lặp***.

   Hai nửa, và nửa thứ hai mới khó. "Không lặp" nghĩa là một phần tử **đã chạy**
   không được chạy lại sau khôi phục: nếu nó gọi model thì một lượt lặp là tiền
   thật **và** một kết quả khác.

⇒ Nên trạng thái phải nằm **theo chỉ số, trong CSDL** — không phải một con trỏ
  "đã tới đâu". Con trỏ chỉ đúng khi các phần tử chạy tuần tự; với
  `parallelism > 1` thì phần tử 7 có thể xong trước phần tử 3, và một con trỏ
  không biểu đạt nổi trạng thái ấy.
"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select, update

from platform_core.models import ForeachMuc, ForeachVong

#: `M4`: hôm nay **4 cứng**. V2 khai được, mặc định **8**.
PARALLELISM_MAC_DINH = 8


class VuotTran(ValueError):
    """Số phần tử vượt `max_items`.

    ⛔ Ném **trước khi chạy**, không dừng giữa chừng. Dừng giữa chừng nghĩa là
       đã tiêu một phần tiền cho một lượt chạy chắc chắn thất bại — tệ hơn cả
       không chạy.
    """


def mo_vong(db, *, run_id: str, node_id: str, muc: list,
            max_items: int, parallelism: Optional[int] = None) -> ForeachVong:
    """Mở một vòng lặp, ghi sẵn một hàng cho MỖI phần tử.

    ⚠️ Ghi sẵn tất cả các hàng — không sinh dần. Đó là thứ làm
       `chi_so_chua_xong()` trả lời được **chính xác** sau một lần chết: tập
       phần tử đã biết từ đầu, chỉ có cột `xong` thay đổi.
    """
    if not max_items or int(max_items) <= 0:
        raise ValueError(
            "`max_items` bat buoc va phai huu han: khong co chan tren thi "
            "khong tinh duoc tran chi phi (`WF-501`)")
    if len(muc) > int(max_items):
        raise VuotTran(
            f"{len(muc)} phan tu > max_items={max_items} — tu choi TRUOC khi "
            "chay, khong dung giua chung")

    # Xin 50 luồng cho 3 phần tử là một con số vô nghĩa đi vào bộ xếp chỗ.
    xin = int(parallelism or PARALLELISM_MAC_DINH)
    thuc = max(1, min(xin, len(muc))) if muc else max(1, xin)

    vong = ForeachVong(run_id=run_id, node_id=node_id,
                       max_items=int(max_items), parallelism=thuc,
                       so_muc=len(muc))
    db.add(vong)
    db.flush()
    for i, gia_tri in enumerate(muc):
        db.add(ForeachMuc(vong_id=vong.id, chi_so=i,
                          dau_vao={"v": gia_tri}, xong=False))
    db.flush()
    return vong


def ghi_ket_qua(db, vong: ForeachVong, *, chi_so: int, ket_qua: Any) -> bool:
    """Ghi kết quả của MỘT phần tử. Trả `False` nếu phần tử ấy đã xong.

    ⭐ Luỹ đẳng **theo chỉ số**: một worker phát lại sẽ thử ghi lại, và bản ghi
       **đầu tiên thắng**. Ghi đè bản cũ là làm mất kết quả thật của một lượt đã
       tính tiền — và không ai phát hiện, vì hàng vẫn ở đó với một giá trị hợp lý.

    🔴 **Điều kiện "chưa xong" phải nằm trong CÂU LỆNH, không nằm trong Python.**

       Bản đầu (tới 2026-09-09) đọc hàng bằng `db.get()`, xem `row.xong` trong
       tiến trình, rồi mới ghi. Ba câu ấy không nguyên tử: hai worker cùng đọc
       `xong=False`, cả hai đi qua cửa, cả hai ghi — và **cả hai trả `True`**.
       Câu "bản ghi đầu tiên thắng" ở trên khi đó là một lời hứa mà mã không
       cưỡng chế được; thứ thực sự xảy ra là **bản ghi cuối cùng thắng**.

       `parallelism` mặc định là 8, tức tình huống ấy là chế độ chạy bình thường
       của ForEach chứ không phải một ca hiếm. Và hậu quả không dừng ở một giá
       trị sai: `so_luot_chay()` đếm hàng `xong=True`, nên một phần tử chạy hai
       lần vẫn hiện là **một** lượt — `M7` ("0 lượt lặp") sẽ báo đạt trong khi
       tiền đã tiêu hai lần.

    ⇒ Một `UPDATE … WHERE xong = false` để **cơ sở dữ liệu** phân xử, và
      `rowcount` là câu trả lời. Đúng khuôn mà `jobs.claim()` đã dùng, và cùng
      lý do: giành một tài nguyên bằng cách lật một cột trong bộ nhớ thì không
      giành được gì (xem memory *bất biến canh trên trạng thái động*).

    ⚠️ `synchronize_session=False` là bắt buộc ở đây: mặc định của SQLAlchemy sẽ
       đi tìm các đối tượng đã nạp để đồng bộ, và ta **không** muốn phiên này
       tin vào bản sao trong bộ nhớ của chính nó — đó chính là thứ vừa bị bỏ.
    """
    gia_tri = {"v": ket_qua} if not isinstance(ket_qua, dict) else ket_qua
    kq = db.execute(
        update(ForeachMuc)
        .where(ForeachMuc.vong_id == vong.id,
               ForeachMuc.chi_so == int(chi_so),
               ForeachMuc.xong.is_(False))
        .values(ket_qua=gia_tri, xong=True)
        .execution_options(synchronize_session=False))
    db.flush()
    # ⛔ Hàng vừa đổi dưới CSDL mà bản sao trong bộ nhớ thì chưa biết. Không đuổi
    #    nó đi thì `chi_so_chua_xong()` gọi ngay sau đây có thể đọc `xong=False`
    #    từ cache của phiên — và trả về một chỉ số vừa được ghi xong.
    db.expire_all()
    return bool(kq.rowcount)


def chi_so_chua_xong(db, vong: ForeachVong) -> list[int]:
    """Chính xác những chỉ số còn phải chạy. Đây là toàn bộ trạng thái khôi phục."""
    return list(db.execute(
        select(ForeachMuc.chi_so)
        .where(ForeachMuc.vong_id == vong.id, ForeachMuc.xong.is_(False))
        .order_by(ForeachMuc.chi_so)).scalars())


def muc_chua_xong(db, vong: ForeachVong, *, sau_chi_so: int = -1,
                  gioi_han: int = 16) -> list[tuple[int, Any]]:
    """`[(chi_so, dau_vao)]` của những phần tử **CHƯA XONG**, đi bằng KEYSET.

    🔴 VÌ SAO HÀM NÀY TỒN TẠI — một con số, không phải một sở thích

    Làn p3b đo trên PostgreSQL thật
    (`docs/superpowers/reports/p3b-do-tai/report.md`): bộ lái vòng lặp tải
    **toàn bảng** `foreach_muc` mỗi tick rồi bỏ `xong` bằng Python, nên tổng
    công là **`N²/P`** — dự đoán 125 000 hàng cho `N=1000, P=8`, đo được
    **127 000** và **31,67 giây** bookkeeping thuần cho MỘT run.

    ⭐ Và đây là chỗ dễ đo nhầm nhất: số **câu SQL** mỗi tick gần như KHÔNG đổi
       theo N (226 → 409 qua cả ba mức). Một phép kiểm đếm câu sẽ báo "không có
       vấn đề". Thứ suy biến là số **HÀNG** nạp.

    ⛔ `sau_chi_so` là KEYSET (`chi_so > :sau`), không phải `OFFSET`: `OFFSET k`
       vẫn bắt CSDL đi qua k hàng đầu, nên nó chỉ dời chỗ của chính `O(N²)` chứ
       không xoá nó. Chỉ số bộ phận `ix_foreach_muc_chua_xong` phục vụ đúng
       hình dạng `WHERE vong_id = … AND xong = false ORDER BY chi_so`.

    ⚠️ Trả **tuple thuần**, không trả đối tượng ORM, và đó là chủ ý:
       `ghi_ket_qua()` gọi `db.expire_all()` (nó phải, xem docstring ở đó), nên
       một hàng ORM cầm sẵn sẽ **nạp lại một câu SQL cho mỗi lần đọc thuộc
       tính** sau đó — đúng thứ hàm này sinh ra để bỏ.
    """
    hang = db.execute(
        select(ForeachMuc.chi_so, ForeachMuc.dau_vao)
        .where(ForeachMuc.vong_id == vong.id,
               ForeachMuc.xong.is_(False),
               ForeachMuc.chi_so > int(sau_chi_so))
        .order_by(ForeachMuc.chi_so)
        .limit(max(1, int(gioi_han)))).all()
    return [(int(i), (dv or {}).get("v")) for i, dv in hang]


def ket_qua_theo_chi_so(db, vong: ForeachVong) -> list[tuple[int, dict]]:
    """`[(chi_so, ket_qua)]` của MỌI phần tử, theo thứ tự đầu vào.

    ⚠️ Đây là phép đọc `O(N)` **một lần**, ở cuối vòng lặp — chỗ duy nhất thật
       sự cần cả bảng (gom `results` + `errors`). Nó khác hẳn một phép đọc
       `O(N)` **mỗi tick**, và tách hai vai đó ra là toàn bộ bản sửa.
    """
    return [(int(i), dict(kq or {})) for i, kq in db.execute(
        select(ForeachMuc.chi_so, ForeachMuc.ket_qua)
        .where(ForeachMuc.vong_id == vong.id)
        .order_by(ForeachMuc.chi_so)).all()]


def so_luot_chay(db, vong: ForeachVong) -> int:
    return len(db.query(ForeachMuc).filter_by(vong_id=vong.id,
                                              xong=True).all())


def gom_ket_qua(db, vong: ForeachVong) -> list:
    """Kết quả theo **thứ tự đầu vào**, không theo thứ tự hoàn thành.

    Với `parallelism > 1` hai thứ tự ấy khác nhau, và thứ tự đầu vào là thứ
    người dùng thấy trên Canvas.
    """
    return [r.ket_qua for r in db.execute(
        select(ForeachMuc)
        .where(ForeachMuc.vong_id == vong.id, ForeachMuc.xong.is_(True))
        .order_by(ForeachMuc.chi_so)).scalars()]
