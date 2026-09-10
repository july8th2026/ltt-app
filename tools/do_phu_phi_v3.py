# -*- coding: utf-8 -*-
"""Đo phụ phí V3 lên một lượt **text thuần** — thứ quyết định TTFT.

## Vì sao KHÔNG đo TTFT bằng đồng hồ

Tiêu chí P10 viết: *"TTFT lượt không-tool **không xấu hơn baseline quá 10 %**"*.
Nghe như một phép bấm giờ. Nhưng bấm giờ ở đây trả lời sai câu hỏi:

- **Không có baseline nào được ghi.** Baseline phải dựng trước, và nó chỉ có
  nghĩa nếu đo trên **cùng máy, cùng model, xen kẽ** để triệt trôi.
- **Phương sai của model nuốt tín hiệu.** Một lượt thật dao động hàng trăm mili
  giây; phụ phí V3 là vài mili giây cộng với phần **prefill dài thêm**. Đo bằng
  đồng hồ là đo nhiễu.
- **Máy này dùng chung.** Một cây khác chạy nặng là số đo lệch về phía *"chậm"*
  ⇒ báo động giả. Sai số **có chiều** thì không có bản hiệu chỉnh nào cứu được.

⭐ Nên đo cái **gây ra** TTFT thay vì đo TTFT: TTFT của một lượt không-tool =
  phụ phí CPU trước lời gọi + thời gian prefill, mà prefill tỉ lệ với **số token
  của prompt**. Cả hai đều đếm được **tất định**, không cần model, không nhiễu.

⛔ Và phép đo này KHÔNG thay thế một lượt bấm giờ thật trên production sau P12.
   Nó trả lời *"V3 có làm prompt phình ra không"* — một câu hẹp hơn. Câu rộng
   hơn cần một model thật và một máy yên, và nó nằm ở nghiệm thu P12.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import tempfile
import time

# Neo goc kho bang TEN thu muc, khong bang so cap (`CLAUDE.md`: dem cap thu muc
# sai ngay khi tep doi cho, va hong lang le).
from pathlib import Path

GOC = next(p for p in Path(__file__).resolve().parents
           if (p / "platform_core").is_dir())
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))


def _dat_co(bat: bool) -> None:
    for ten in ("LTT_CHATLTT_V3_TOOLS", "LTT_CHATLTT_V3_PAID_TOOLS",
                "LTT_CHATLTT_V3_MEMORY"):
        os.environ[ten] = "1" if bat else "0"


def _do_mot_lan(db, *, user_id: str, bat: bool) -> dict:
    """Dựng phần `tools` của một lượt với cờ bật/tắt. Trả số đo, không trả dữ liệu."""
    from apps.chatltt.services import luot_v3

    _dat_co(bat)

    t0 = time.perf_counter()
    khoi = luot_v3.nen_dung_v3(db, user_id=user_id)
    giay = time.perf_counter() - t0

    # ⭐ Đếm ký tự của JSON đã tuần tự hoá — đây đúng là thứ đi vào prompt.
    #    Không dùng bộ đếm token của một nhà cung cấp cụ thể: tỉ lệ ký tự/token
    #    ổn định trong cùng một họ model, và ta đang so HAI bản với NHAU chứ
    #    không tuyên bố một con số tuyệt đối.
    chu = json.dumps(khoi, ensure_ascii=False) if khoi else ""
    return {"so_tool": len(khoi), "ky_tu": len(chu), "giay": giay}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lan", type=int, default=5, help="so lan lap moi ve")
    ap.add_argument("--user", default="", help="user_id that; rong = dung DB rong")
    a = ap.parse_args()

    # ⛔ Mặc định KHÔNG chạm CSDL vận hành. Một công cụ đo mà mặc định nối vào
    #    kho thật là một công cụ sẽ có ngày ghi vào đó — và ở đây không có gì
    #    cần dữ liệu thật: bảng chiếu tool đọc từ **sổ đăng ký**, không từ hàng
    #    của người dùng.
    if not os.environ.get("LTT_DATABASE_URL"):
        tam = tempfile.mkdtemp(prefix="do_phu_phi_v3_")
        os.environ["LTT_DATABASE_URL"] = "sqlite:///" + (
            pathlib.Path(tam) / "t.db").as_posix()
        print(f"  [csdl tam] {tam}")

    import platform_core.models  # noqa: F401  — dang ky bang truoc create_all
    from platform_core.db import Base, get_engine, get_session
    from platform_core.registry import load_app_tables
    load_app_tables()
    Base.metadata.create_all(get_engine())

    gen = get_session()
    db = next(gen)
    try:
        uid = a.user or "u-do-phu-phi"
        # ⛔ Xen kẽ TAT/BAT/TAT/BAT... chứ không chạy hết một vế rồi mới vế kia.
        #    Máy nóng lên hoặc một cây khác khởi động giữa chừng sẽ dồn hết sai
        #    số vào vế chạy sau — và ta sẽ đọc cái trôi ấy thành "phụ phí V3".
        tat, bat = [], []
        for _ in range(a.lan):
            tat.append(_do_mot_lan(db, user_id=uid, bat=False))
            bat.append(_do_mot_lan(db, user_id=uid, bat=True))
    finally:
        _dat_co(False)
        try:
            next(gen)
        except StopIteration:
            pass

    def trung_vi(ds, khoa):
        """🔴 TRUNG VỊ, không phải trung bình.

        Đo 07/09 lượt đầu tiên tốn **987 ms** (nạp module) rồi ổn định ở
        **2,7 ms**. Trung bình của dãy ấy ra **204 ms** — một con số **không mô
        tả lượt nào cả**, và nó lệch về phía *"chậm"*, tức về phía báo động giả.

        ⛔ Một phép đo có một mẫu khác biệt bậc độ lớn thì trung bình là thống
           kê SAI, không phải thống kê thô.
        """
        v = sorted(d[khoa] for d in ds)
        n = len(v)
        return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2

    print(f"  ve TAT : {tat[0]['so_tool']:3d} tool | {trung_vi(tat,'ky_tu'):8.0f} ky tu"
          f" | {trung_vi(tat,'giay')*1000:7.2f} ms (trung vi)")
    print(f"  ve BAT : {bat[0]['so_tool']:3d} tool | {trung_vi(bat,'ky_tu'):8.0f} ky tu"
          f" | {trung_vi(bat,'giay')*1000:7.2f} ms (trung vi)")
    print(f"  luot DAU ve BAT: {bat[0]['giay']*1000:.0f} ms"
          f"  <- nap module, MOT LAN moi tien trinh, khong phai phu phi moi luot")
    them = trung_vi(bat, "ky_tu") - trung_vi(tat, "ky_tu")
    print(f"  => V3 them {them:.0f} ky tu vao prompt cua MOI luot,"
          f" ke ca luot khong dung tool")
    print("  => phan PREFILL cua {them} ky tu ay CHUA do duoc o day: no can mot"
          .format(them=int(them)))
    print("     model that va mot may yen. Do la viec cua nghiem thu P12.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
