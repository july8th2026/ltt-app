"""
co_v3.py — cờ tính năng của ChatLTT V3. Đọc mỗi lần, không nhớ. (H44 P03)

## Vì sao ĐỌC MỖI LẦN chứ không đọc lúc import

Một cờ đọc lúc import thì tắt nó phải **khởi động lại dịch vụ** — và lúc cần
tắt gấp là đúng lúc không ai muốn khởi động lại. Đọc mỗi lần tốn một lời gọi
`os.environ.get`, đổi lấy một cái van vặn được ngay.

⭐ Và nó làm test không phải `importlib.reload` để đổi cờ — chính `reload` là
   thứ đã làm 16 phép kiểm đỏ ở **bảy tệp khác** và sinh ra `test_631`.

## Hai cờ, hai việc khác nhau

    LTT_CHATLTT_V3_TOOLS        vong lap tool co chay khong
    LTT_CHATLTT_V3_PAID_TOOLS   model co duoc TU GOI tool CO PHI khong

⛔ Cờ thứ hai **không** tự bật theo cờ thứ nhất. Vòng lặp chạy với tool miễn
   phí là một mức rủi ro; model tự tiêu tiền của khách là mức khác hẳn. Gộp hai
   cờ lại là để một lần bật vô tình mở cả hai.

## Cờ KHÔNG phải cổng an toàn

`02_ADR_ORCHESTRATION.md` §7: cờ là **cổng phát hành**. Thứ chặn model tiêu tiền
là `chieu_tool.CHO_MODEL_GOI` + duyệt bền (P04), không phải một biến môi trường
mà bất kỳ ai sửa `app.env` cũng đổi được.
"""
from __future__ import annotations

import os

CO_TOOLS = "LTT_CHATLTT_V3_TOOLS"
CO_TOOL_CO_PHI = "LTT_CHATLTT_V3_PAID_TOOLS"

#: 🔴 Co cua NHOM P06 (tep/tri thuc/tim kiem). Them 06/09 (B3).
#:
#:    Ke hoach tong ghi "Lan B — moi nhom mot co", va toi bo sot no suot
#:    ca P06 lan B1/B2. Hau qua neu deploy nguyen trang: bat NGAY mot tinh
#:    nang TINH TIEN o mot gia con tam (`gia_trich.CHU_DU_AN_DA_CHOT` =
#:    False).
#:
#: ⛔ KHONG dung lai `CO_TOOLS`: co do gac VONG LAP TOOL. Dinh mot tai lieu
#:    la mot nang luc khac — no ton tien ngay ca khi vong lap tool tat.
#:    Mot co gac hai thu khac nhau la mot co khong ai bat duoc dung.
CO_TEP = "LTT_CHATLTT_V3_FILES"

#: 🔴 Co cua nhom B4 (ghi nho). Them 06/09.
#:
#: ⛔ KHONG dung lai `CO_TEP` hay `CO_TOOLS`. Ghi nho khac hai thu do o mot
#:    diem quyet dinh: no doi **ngu canh cua MOI luot** trong pham vi, ke ca
#:    luot khong dinh tep va khong goi tool. Bat nham no la doi hanh vi cua
#:    toan bo san pham chu khong mo them mot cua.
#:
#: ⭐ Va vi the no phai tat duoc NGAY: mot mau ghi nho sai lam hong moi cau
#:    tra loi sau do, khong phai mot cau.
CO_GHI_NHO = "LTT_CHATLTT_V3_MEMORY"

#: Co cua nhom B5 (du an). Them 06/09.
#:
#: ⭐ Khac `_MEMORY` o be rong: du an gac mot CUA (tat thi route 404, phan
#:    con lai y nguyen). No dung nhom voi `_FILES`, khong dung nhom voi
#:    `_MEMORY` — va do la ly do no la mot co RIENG chu khong an theo.
CO_DU_AN = "LTT_CHATLTT_V3_PROJECTS"

#: Co cua nhom B6 (nghien cuu). Them 07/09.
#:
#: ⛔ KHONG an theo `CO_TEP` du no doc cung mot kho (`chatltt_doan`). Dinh mot
#:    tai lieu la mot viec khach LAM MOT LAN va nhin thay ket qua ngay; mot
#:    vong nghien cuu la N luot model chay NEN, va no ton tien theo N chu
#:    khong theo mot. Hai muc rui ro khac nhau ⇒ hai cai van khac nhau.
#:
#: ⭐ Va no phai tat duoc rieng: ngay do vong lap ra bao cao te, thu can tat la
#:    vong lap — khong phai kha nang dinh tep, thu ma moi luot chat deu dung.
CO_NGHIEN_CUU = "LTT_CHATLTT_V3_RESEARCH"

#: Giá trị được coi là BẬT. Fail-closed: mọi thứ khác là tắt, kể cả `"true"`
#: viết hoa lạ hay `"yes"` — một cờ nhận nhiều cách viết là một cờ mà người ta
#: tưởng đã bật trong khi chưa.
BAT = frozenset({"1", "true", "on"})


def _bat(ten: str) -> bool:
    return (os.environ.get(ten) or "").strip().lower() in BAT


def tool_bat() -> bool:
    """Vòng lặp tool có chạy không. **Mặc định TẮT.**"""
    return _bat(CO_TOOLS)


def tool_co_phi_bat() -> bool:
    """Model có được tự gọi tool có phí không. **Mặc định TẮT**, và độc lập.

    ⛔ `tool_bat()` bật **không** kéo theo cái này. Xem docstring module.
    """
    return _bat(CO_TOOL_CO_PHI)


def tep_bat() -> bool:
    """Dinh tai lieu vao hoi thoai co mo khong. **Mac dinh TAT.**

    ⭐ Doc MOI LAN, khong chup mot lan — cung ly do `tool_bat()`: tat gap
       phai an ngay, ke ca giua mot luot dang chay.
    """
    return _bat(CO_TEP)


def ghi_nho_bat() -> bool:
    """Kho ghi nho co duoc tiem vao ngu canh khong. **Mac dinh TAT.**

    ⛔ Tat co nay phai lam ngu canh **khong doi mot byte** — khong phai "tiem
       mot khoi rong". Mot khoi rong van ton token va van day model rang no co
       mot kho de vien dan. `test_831` chot dieu do bang cach so **byte**.
    """
    return _bat(CO_GHI_NHO)


def du_an_bat() -> bool:
    """Du an co mo khong. **Mac dinh TAT.**"""
    return _bat(CO_DU_AN)


def nghien_cuu_bat() -> bool:
    """Vong nghien cuu co mo khong. **Mac dinh TAT.**"""
    return _bat(CO_NGHIEN_CUU)


def trang_thai() -> dict:
    """Cho `/api/danh-muc` và log — để người trực biết cờ nào đang bật."""
    return {"tools": tool_bat(), "tool_co_phi": tool_co_phi_bat(),
            "tep": tep_bat(), "ghi_nho": ghi_nho_bat(),
            "du_an": du_an_bat(), "nghien_cuu": nghien_cuu_bat()}


#: ⚠️ Sua 06/09: ban truoc thieu `tep_bat`/`CO_TEP` — `__all__` da troi khoi
#:    module tu B3. Mot `__all__` thieu khong bao loi, no chi lam
#:    `from ... import *` im lang bo qua thu moi.
__all__ = ["tool_bat", "tool_co_phi_bat", "tep_bat", "ghi_nho_bat",
           "du_an_bat", "nghien_cuu_bat", "trang_thai", "CO_TOOLS",
           "CO_TOOL_CO_PHI", "CO_TEP", "CO_GHI_NHO", "CO_DU_AN",
           "CO_NGHIEN_CUU"]
