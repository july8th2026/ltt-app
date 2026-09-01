r"""
do_dung_chay_lo.py — có ai thật sự dùng màn CHẠY LÔ không?

    powershell -ExecutionPolicy Bypass -File .\setup\do_dung_chay_lo.ps1

## Vì sao đo trước khi bàn gỡ

Tiền lệ của dự án này là Q108/Q109: app `socialbot` chỉ bị gỡ **sau khi** đo
được `0` job, `0` `app_access`, `0` `app_projects` và không có `tokens.enc` —
tức chưa khách nào từng kết nối. Con số đó biến một cuộc tranh luận về khẩu vị
thành một quyết định.

⛔ Và nó cắt theo cả hai chiều. Nếu có người đang dùng, thì "gỡ cho gọn" là lấy
   đi một thứ họ đang trả tiền để dùng — và không con số nào ở đây làm việc đó
   trở nên đúng.
"""
from __future__ import annotations

import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    # 🔴 `line_buffering=True` KHÔNG phải chuyện gọn gàng — nó là thứ quyết định
    #    một phép đo dài có theo dõi được hay không.
    #
    #    Khi stdout đi ra MÀN HÌNH, Python tự đệm theo dòng. Khi nó đi ra một
    #    TỆP — tức mọi lần chạy qua trình bọc PowerShell với `*> log.txt` — nó
    #    chuyển sang đệm KHỐI, và tệp log nằm im ở 0 byte suốt hàng chục phút.
    #
    # ⛔ Hệ quả không phải bất tiện: tôi mất hai lượt chờ vì không phân biệt được
    #    "đang chạy" với "đã treo", và phải đi hỏi `nvidia-smi` để biết tiến
    #    trình còn sống. Một công cụ đo mà không nói nó đang ở đâu thì mọi sự cố
    #    của nó đều trông giống nhau.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace",
                           line_buffering=True)


def main(argv=None) -> int:
    from sqlalchemy import func, select

    from apps.ltt_voice.tables_du_an import VoiceBlock, VoiceProject
    from platform_core.db import get_session
    from platform_core.models import Job

    gen = get_session()
    db = next(gen)
    try:
        print("=" * 62)
        print("  MAN CHAY LO — co ai dung khong?")
        print("=" * 62)

        # `loai` phan biet Du an voi Lo; hai ben dung chung bang.
        theo_loai = db.execute(
            select(VoiceProject.loai, func.count(VoiceProject.id))
            .group_by(VoiceProject.loai)).all()
        print("\nBan ghi trong `voice_du_an` theo loai:")
        for loai, so in theo_loai or [("(khong co dong nao)", 0)]:
            print(f"    {str(loai):12} {so}")

        lo_ids = [r[0] for r in db.execute(
            select(VoiceProject.id).where(VoiceProject.loai == "lo")).all()]
        print(f"\nSo LO: {len(lo_ids)}")
        if lo_ids:
            so_khoi = db.execute(
                select(func.count(VoiceBlock.id))
                .where(VoiceBlock.project_id.in_(lo_ids))).scalar() or 0
            chu = db.execute(
                select(func.count(func.distinct(VoiceProject.owner_id)))
                .where(VoiceProject.loai == "lo")).scalar() or 0
            print(f"  so dong (khoi) trong cac lo : {so_khoi}")
            print(f"  so CHU SO HUU khac nhau     : {chu}")

        # Job sinh ra tu man Lo mang `nguon='lo'` trong params.
        tong = db.execute(select(func.count(Job.id)).where(
            Job.job_type == "ltt_voice.synthesize")).scalar() or 0
        print(f"\nJob `ltt_voice.synthesize` tong cong: {tong}")
        theo_nguon = {}
        for (p,) in db.execute(select(Job.params).where(
                Job.job_type == "ltt_voice.synthesize")).all():
            n = str((p or {}).get("nguon") or "(khong ghi)")
            theo_nguon[n] = theo_nguon.get(n, 0) + 1
        for n, so in sorted(theo_nguon.items(), key=lambda x: -x[1]):
            print(f"    nguon {n:14} {so}")

        print("\n" + "=" * 62)
        print("  ⛔ Con so tren KHONG tu quyet dinh duoc gi. Chung tra loi mot")
        print("     cau hep: 'da co ai dung chua'. Chung khong tra loi 'no co")
        print("     dang gia khong' — mot man moi xay xong thi luon co so 0.")
        return 0
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
