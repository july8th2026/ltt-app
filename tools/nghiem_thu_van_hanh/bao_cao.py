"""bao_cao.py — bản ghi JSON → bảng chất lượng. **Hàm thuần, không I/O.**

Điểm vào của chương trình: `docs/VAN_HANH_THAT.md`.

⭐ Thuần **có chủ đích**: một báo cáo gọi mạng là một báo cáo **không tái lập
   được** từ bản ghi đã lưu — và lúc đó bản ghi mất giá trị làm bằng chứng. Chạy
   lại trên cùng một tệp JSON phải cho ra cùng một bảng, hôm nay và sau sáu
   tháng.

## 🔴 Hai điều bảng này BẮT BUỘC in ra

1. **Commit production.** Không có nó thì con số không tái lập được: ta có một
   bảng đẹp mà không biết nó nói về bản nào. Thiếu ⇒ `BanGhiThieu`, **không** in
   một bảng khuyết.
2. **Lượt NHIỄM, đếm riêng, kèm lý do.** Ngày 13/09 một lượt đo bị deploy của
   phiên khác làm hỏng, và nó trông y hệt một phát hiện lớn. Gộp nó vào tỉ lệ
   "đạt" là giấu mất một lượt **chưa hề đo được**.
"""
from __future__ import annotations

from typing import Any


class BanGhiThieu(Exception):
    """Bản ghi thiếu thứ làm nó tái lập được. In bảng lúc này là nói dối."""


def _doi(ban_ghi: dict) -> None:
    if not ban_ghi.get("commit_production"):
        raise BanGhiThieu(
            "ban ghi khong co `commit_production` — mot bang khong noi ve ban "
            "nao thi khong tai lap duoc, va khong dung lam bang chung duoc")


def tham_so_do_duoc(ban_ghi: dict) -> dict[str, Any]:
    """Các tham số tổng hợp. Hàm thuần — không sửa `ban_ghi`."""
    _doi(ban_ghi)
    ks = ban_ghi.get("kich_ban") or []
    dat = sum(1 for k in ks if k.get("dat") is True)
    truot = sum(1 for k in ks if k.get("dat") is False)
    nhiem = sum(1 for k in ks if k.get("nhiem"))
    return {
        "commit_production": ban_ghi["commit_production"],
        "so_dat": dat,
        "so_truot": truot,
        "so_nhiem": nhiem,
        # ⛔ Mẫu số KHÔNG gồm lượt nhiễm. Tính nó là "trượt" thì báo động giả;
        #    tính là "đạt" thì giấu một lượt chưa đo được.
        "mau_so": dat + truot,
        "tong_kich_ban": len(ks),
        "ma_truot": [k["ma"] for k in ks if k.get("dat") is False],
        "ma_nhiem": [k["ma"] for k in ks if k.get("nhiem")],
    }


def bang_chat_luong(ban_ghi: dict) -> str:
    """Bảng Markdown đọc được cho chủ sản phẩm."""
    t = tham_so_do_duoc(ban_ghi)
    ks = ban_ghi.get("kich_ban") or []
    d: list[str] = []

    d.append("# Bảng chất lượng — VẬN HÀNH THẬT")
    d.append("")
    d.append(f"**Commit production:** `{t['commit_production']}`")
    d.append("")
    d.append(f"Đạt **{t['so_dat']}** / kết luận được **{t['mau_so']}**"
             + (f" · **{t['so_nhiem']} lượt NHIỄM, không tính vào mẫu số**"
                if t["so_nhiem"] else ""))
    d.append("")

    d.append("| kịch bản | kết quả | đo được |")
    d.append("|---|---|---|")
    for k in ks:
        if k.get("nhiem"):
            kq = "⛔ NHIỄM"
        elif k.get("dat") is True:
            kq = "✅ đạt"
        elif k.get("dat") is False:
            kq = "❌ **TRƯỢT**"
        else:
            kq = "— chưa chấm được"
        so = ", ".join(f"{a}={b}" for a, b in (k.get("do_duoc") or {}).items())
        d.append(f"| `{k['ma']}` | {kq} | {so or '—'} |")
    d.append("")

    if t["ma_nhiem"]:
        d.append("## ⛔ Lượt bị loại vì NHIỄM")
        d.append("")
        d.append("Không diễn giải những lượt này. Chạy lại khi nền sạch.")
        d.append("")
        for k in ks:
            if k.get("nhiem"):
                d.append(f"- `{k['ma']}` — {k.get('ly_do_nhiem') or 'khong ro'}")
        d.append("")

    if t["ma_truot"]:
        d.append("## ❌ Trượt — mỗi dòng là một phát hiện cần xử")
        d.append("")
        for k in ks:
            if k.get("dat") is False:
                so = ", ".join(f"{a}={b}"
                               for a, b in (k.get("do_duoc") or {}).items())
                d.append(f"- `{k['ma']}` — đo được: {so or 'khong co so'}")
        d.append("")

    return "\n".join(d)
