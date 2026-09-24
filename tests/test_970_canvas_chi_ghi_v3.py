"""Đợt 5.2 phần D — trình soạn Canvas **chỉ được ghi qua cửa v3**.

## 🔴 Vì sao một đường ghi HỖN HỢP tệ hơn cả hai lựa chọn

`CanvasShell.tsx` có **ba** chỗ lưu: tự động lưu, lưu trước khi chạy, và lưu khi
đổi tên. Nếu một trong ba còn trỏ `saveWorkflow` (v2) thì:

```
AgentWorkflow.document   nhan mot phan cac lan sua
WorkflowDraft.document   nhan phan con lai
```

Hai bảng **trôi khỏi nhau**, và không lỗi nào báo — người dùng chỉ thấy "workflow
tự quay lại bản cũ" ở một số thao tác chứ không phải mọi thao tác. Đó là hình
dạng khó truy nhất: lỗi **có điều kiện** trên một thao tác thường ngày.

⛔ Nên phép kiểm này chốt **sự vắng mặt**, và sự vắng mặt là thứ không ai nhớ
   kiểm. Ai thêm chỗ lưu thứ tư sẽ với tay lấy cái tên quen thuộc nhất.

## Đọc AST, không `grep`

`grep "saveWorkflow"` khớp cả `saveWorkflowV3` — tiền tố của nhau. Một bộ dò
chuỗi ở đây sẽ báo động trên chính bản đã sửa đúng. Phép kiểm đọc **lời gọi**
trong nguồn TypeScript bằng một biểu thức chỉ khớp **tên hàm đứng trước `(`**,
và có một bài tự đối chứng bên dưới.
"""
from __future__ import annotations

import pathlib
import re

import pytest

GOC = pathlib.Path(__file__).resolve().parent.parent
SHELL = GOC / "frontend" / "agent-canvas" / "src" / "CanvasShell.tsx"
API = GOC / "frontend" / "agent-canvas" / "src" / "workflowApi.ts"

#: Tên hàm đứng ngay trước `(`. `\b` sau tên chưa đủ — `saveWorkflowV3(` cũng
#: khớp `saveWorkflow\b`. Đòi ký tự kế tiếp KHÔNG phải chữ/số mới tách được hai
#: cái tên lồng tiền tố.
def _goi(nguon: str, ten: str) -> int:
    return len(re.findall(rf"\b{re.escape(ten)}\s*\(", nguon))


@pytest.fixture(scope="module")
def shell() -> str:
    assert SHELL.exists(), f"khong thay {SHELL}"
    return SHELL.read_text(encoding="utf-8")


def test_trinh_soan_KHONG_con_loi_goi_ghi_v2_nao(shell):
    """⛔ Ba chỗ lưu phải cùng đi một cửa. Một chỗ sót lại làm hai bảng trôi."""
    sot = {ten: _goi(shell, ten)
           for ten in ("saveWorkflow", "loadOrCreateWorkflow")
           if _goi(shell, ten)}
    assert not sot, (
        f"CanvasShell van goi cua v2: {sot}\n"
        "Dung `saveWorkflowV3` / `loadOrCreateWorkflowV3`. Mot duong ghi hon "
        "hop lam `AgentWorkflow.document` va `WorkflowDraft.document` troi "
        "khoi nhau, va khong loi nao bao.")


def test_trinh_soan_CO_dung_cua_v3(shell):
    """⭐ Vế hợp lệ. Không có nó, một `CanvasShell.tsx` **rỗng** cũng làm bài
    trên xanh — phép kiểm sẽ đo sự vắng mặt của cả hai thứ."""
    assert _goi(shell, "saveWorkflowV3") >= 3, (
        "phai co du BA cho luu di qua v3: tu dong luu, truoc khi chay, doi ten")
    assert _goi(shell, "loadOrCreateWorkflowV3") >= 1


def test_bieu_thuc_do_PHAN_BIET_duoc_hai_ten_long_tien_to():
    """🔑 Đối chứng cho chính bộ dò.

    `saveWorkflow` là tiền tố của `saveWorkflowV3`. Nếu biểu thức không tách
    được hai cái tên thì `test_trinh_soan_KHONG_con_loi_goi_ghi_v2_nao` sẽ đỏ
    **vĩnh viễn** trên bản đã sửa đúng — và người sau sẽ nới nó ra.
    """
    mau = "saveWorkflowV3(a); saveWorkflowV3(b);"
    assert _goi(mau, "saveWorkflow") == 0
    assert _goi(mau, "saveWorkflowV3") == 2
    assert _goi("saveWorkflow(x)", "saveWorkflow") == 1


def test_trinh_soan_KHONG_con_loi_goi_CHAY_v2_nao(shell):
    """Ba lời gọi chạy v2 phải biến mất cùng lúc. Sót một cái là Canvas vừa
    tạo `WorkflowRun` v3 vừa lái `AgentRun` v1 — hai sổ tiền song song."""
    sot = {ten: _goi(shell, ten) for ten in
           ("validateWorkflow", "createRun", "tickRun", "approveRun",
            "runAgain", "restoreRunAsWorkflow", "loadRunHistory")
           if _goi(shell, ten)}
    assert not sot, f"CanvasShell van goi duong chay v2: {sot}"


def test_trinh_soan_CO_dung_duong_chay_v3(shell):
    """🔑 Vế đối chứng: một `CanvasShell.tsx` rỗng cũng làm bài trên xanh.

    🔴 SỬA 24/09: bản trước đòi đúng tên `loadRunV3`. Làn `p10`/`P9b` đổi cửa
       ĐỌC từ vòng poll sang **SSE** (`theoDoiRunV3`, gọi ở `CanvasShell.tsx`),
       nên cái tên cũ biến mất — trong khi **tính chất vẫn nguyên**: trình soạn
       vẫn đọc run qua đường v3.

    ⛔ Đó là chốt **CÁCH GÕ** thay vì chốt **tính chất** — đúng lớp lỗi phiên
       ASV vừa gặp ở `test_480` cùng ngày. Một bánh cóc kiểu ấy đỏ khi người ta
       làm đúng, và sự đỏ oan đẩy người ta đi nới nó.

    ⭐ Nay hỏi đúng bốn **việc**, mỗi việc chấp nhận mọi cửa v3 làm được việc đó:
       tạo run · ĐỌC run · huỷ run · publish.
    """
    viec = {
        "tao run": ("createRunV3",),
        "doc run": ("loadRunV3", "theoDoiRunV3"),   # poll HOAC SSE
        "huy run": ("cancelRunV3",),
        "publish": ("publishWorkflowV3",),
    }
    thieu = [v for v, tens in viec.items()
             if not any(_goi(shell, t) >= 1 for t in tens)]
    assert not thieu, f"trinh soan khong lam cac viec v3 nay: {thieu}"
    # 🔑 Đối chứng của chính vế đối chứng: nếu `_goi` hỏng và luôn trả 0 thì
    #    khẳng định trên đỏ; nếu nó luôn trả > 0 thì bài vô nghĩa. Chốt rằng
    #    một tên KHÔNG hề có trong tệp phải đếm ra 0.
    assert _goi(shell, "ham_khong_bao_gio_ton_tai_o_day") == 0


def test_lop_khach_v3_van_GIU_ham_v2_cho_duong_khac(shell):
    """⚠️ `workflowApi.ts` **vẫn** xuất `saveWorkflow` v2, và đó là cố ý.

    `loadOrCreateWorkflow` v2 còn phục vụ đường Plan v1 (`/agent/api/workflows`)
    cho tới khi lớp ấy được gỡ. Xoá nó bây giờ là gỡ hai thứ trong một lần —
    và lần gỡ đó phải đi cùng lần gỡ Plan v1, không đi cùng lần chuyển Canvas.
    """
    api = API.read_text(encoding="utf-8")
    assert "export async function saveWorkflow(" in api
    assert "export async function saveWorkflowV3(" in api


def test_cua_v3_gui_di_dung_luoc_do_v3():
    """Lời gọi lưu phải `toV3(...)` trước khi gửi — nếu không, máy chủ nhận một
    tài liệu v2 và `_sinh_chi_muc` sẽ đọc `source_port` ra chuỗi rỗng."""
    api = API.read_text(encoding="utf-8")
    m = re.search(r"export async function saveWorkflowV3.*?\n\}", api, re.S)
    assert m, "khong tim thay `saveWorkflowV3`"
    assert "toV3(workflow.canvas)" in m.group(0), (
        "`saveWorkflowV3` phai chuyen sang v3 truoc khi gui")
