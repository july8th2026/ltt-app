"""soi_troi_may_b.py — máy B đang phục vụ bề mặt nào, so với bề mặt cây KHAI?

## 🔴 Vì sao công cụ này tồn tại — sự cố L-07, 13/09/2026

`ltt-3.8` trả **429 cho mọi yêu cầu suốt 32 phút**. Gốc: cổng render trên máy B
chạy một bản từ **04/09**, thiếu hẳn `/v1/nha_comfy`. Trọng tài residency gọi
đường ấy để bật lại ComfyUI trước khi mở cửa sổ ảnh; nó nhận **404**, không vào
được trạng thái `anh`, và ở lại `nha_llm` — nơi lúc ấy chưa có đường lui.

⛔ Không có gì phát hiện ra sự trôi bản ấy. Gate của máy A **cố ý** không hỏi máy
   B (một cổng chất lượng không được phụ thuộc một máy ở xa đang bật), nên bề
   mặt thật của máy B chưa bao giờ được đối chiếu với cây. Nó trôi bốn ngày
   trong im lặng, và chỉ lộ ra khi một job ảnh chạm vào.

⭐ Cùng nguyên tắc với `api_prod_canary.py` và luật 5 của `CLAUDE.md`: *"cái gì
   đang sống thì HỎI MÁY CHỦ, đừng đọc một bảng chép tay"*. Bộ này hỏi.

## Nó KHÔNG làm gì

⛔ **Không phải một bước gate.** Nó cần mạng và cần máy B bật; một cổng chất
   lượng đỏ vì máy B đang bảo trì là một cổng sẽ bị bỏ qua. Chạy nó **trước và
   sau deploy**, hoặc khi nghi ngờ.

⛔ **Không so nội dung hàm.** Hai bản có thể cùng đường mà khác hành vi. Bộ này
   chỉ trả lời một câu, và trả lời chắc chắn: *"đường nào cây có mà máy B
   không?"* — đúng câu mà L-07 cần và không ai hỏi.

## Chạy

    python tools/soi_troi_may_b.py
    python tools/soi_troi_may_b.py --render http://192.168.2.66:8199 --llm http://192.168.2.66:8299
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

GOC = pathlib.Path(__file__).resolve().parents[1]

# ⛔ MỌI CHUỖI IN RA PHẢI THUẦN ASCII. Console Windows mặc định là cp1252; một
#    chữ có dấu trong `print` làm công cụ **chết ở dòng cuối** sau khi đã làm
#    xong việc — đúng thứ đã xảy ra ở lượt chạy đầu tiên của chính tệp này.
#    Chú thích và docstring thì tự do: chúng không đi qua stdout.

#: Cổng nào đọc tuyến từ tệp nào. Thêm cổng mới ⇒ thêm một dòng.
CAC_CONG = {
    "render": ("render_gateway/api.py", "LTT_RENDER_BASE_URL",
               "http://192.168.2.66:8199"),
    "llm": ("llm_gateway/api.py", "LTT_LLM_BASE_URL",
            "http://192.168.2.66:8299"),
}

#: Đường chỉ có ở tầng framework hoặc chỉ bật theo cấu hình — bỏ khỏi phép so.
#:
#: ⚠️ Danh sách này là chỗ một phép kiểm chết dần: mỗi lần thêm một tên vào đây
#:    là bớt một câu hỏi. Thêm thì phải kèm lý do, và lý do phải là *"đường này
#:    KHÔNG BAO GIỜ ở trên máy B"*, không phải *"lần này nó không có"*.
BO_QUA = {"/openapi.json", "/docs", "/redoc", "/docs/oauth2-redirect"}


def tuyen_trong_cay(tep: str) -> set[str]:
    """Đọc tuyến bằng **AST**, không import và không regex.

    ⛔ Không import: `api.py` dựng app từ cấu hình, và một lần import hỏng vì
       thiếu biến môi trường sẽ biến bộ dò này thành một bộ dò không chạy được.
    ⛔ Không regex: một chuỗi `"@app.post("` trong chú thích cũng khớp, và khi
       ấy bộ dò báo thiếu một đường chưa bao giờ tồn tại.
    """
    cay = ast.parse((GOC / tep).read_text(encoding="utf-8"))
    ra: set[str] = set()
    for nut in ast.walk(cay):
        if not isinstance(nut, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for tt in nut.decorator_list:
            if not (isinstance(tt, ast.Call) and isinstance(tt.func, ast.Attribute)):
                continue
            if tt.func.attr not in ("get", "post", "put", "delete", "patch"):
                continue
            if not tt.args:
                continue
            a0 = tt.args[0]
            if isinstance(a0, ast.Constant) and isinstance(a0.value, str):
                ra.add(a0.value)
    return ra


def tuyen_tren_may_b(goc: str) -> tuple[set[str], str]:
    """Hỏi chính máy B. Trả `(tập đường, lỗi)` — lỗi rỗng nghĩa là hỏi được."""
    try:
        with urllib.request.urlopen(goc.rstrip("/") + "/openapi.json",
                                    timeout=20) as f:
            d = json.loads(f.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as e:
        return set(), f"{type(e).__name__}: {str(e)[:120]}"
    return set((d.get("paths") or {})), ""


def main() -> int:
    ap = argparse.ArgumentParser()
    for ten, (_, bien, mac_dinh) in CAC_CONG.items():
        ap.add_argument(f"--{ten}", default=os.environ.get(bien) or mac_dinh)
    a = ap.parse_args()

    tong_thieu = 0
    khong_hoi_duoc = 0
    for ten, (tep, bien, _) in CAC_CONG.items():
        goc = getattr(a, ten)
        print(f"== cong {ten}  ({goc}) ==")
        print(f"   cay khai o: {tep}   (bien moi truong: {bien})")
        cay = {d for d in tuyen_trong_cay(tep) if d not in BO_QUA}
        may, loi = tuyen_tren_may_b(goc)
        if loi:
            # ⚠️ Hoi khong duoc KHONG phai la "khop". Dem rieng, va ma thoat
            #    khac han — mot bo do im lang vi khong hoi duoc la mot bo do
            #    dang noi doi theo huong de chiu.
            print(f"   !! KHONG HOI DUOC: {loi}")
            print("      => khong ket luan gi ve cong nay.")
            khong_hoi_duoc += 1
            print()
            continue
        may = {d for d in may if d not in BO_QUA}
        thieu = sorted(cay - may)
        thua = sorted(may - cay)
        print(f"   cay khai {len(cay)} duong | may B phuc vu {len(may)} duong")
        for d in thieu:
            print(f"   THIEU tren may B : {d}")
        for d in thua:
            print(f"   chi co o may B   : {d}")
        if not thieu and not thua:
            print("   => KHOP")
        elif not thieu:
            print("   => may B co them duong (ban moi hon cay, hoac cay vua lui)")
        tong_thieu += len(thieu)
        print()

    print("== KET ==")
    if khong_hoi_duoc:
        print(f"  {khong_hoi_duoc} cong khong hoi duoc — chua tra loi duoc cau hoi.")
    if tong_thieu:
        print(f"  {tong_thieu} duong cay CO ma may B KHONG co.")
        print("  Do la hinh dang cua L-07: mot lenh goi len may B se nhan 404, va")
        print("  ben goi co the khong co duong lui.")
        print("  => deploy lai cong tuong ung roi khoi dong lai dich vu cua no.")
        return 1
    if not khong_hoi_duoc:
        print("  Moi cong: may B phuc vu du be mat cay khai.")
    return 2 if khong_hoi_duoc else 0


if __name__ == "__main__":
    sys.exit(main())
