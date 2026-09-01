r"""
dat_giong_dung_chung.py — đưa một giọng nhân bản vào KHO CHUNG của nền tảng.

    powershell -File .\setup\dat_giong_dung_chung.ps1 -Xem
    powershell -File .\setup\dat_giong_dung_chung.ps1 -VoiceId vc_... -Bat
    powershell -File .\setup\dat_giong_dung_chung.ps1 -VoiceId vc_... -Tat

## Vì sao là một công cụ chứ không phải một nút trên giao diện

Bật một giọng lên kho chung là hành động **không đối xứng**: tắt đi thì giọng
biến khỏi danh sách, nhưng thứ khách đã nghe thì đã nghe, và bản tiếng họ đã
tạo thì đã có. Một nút trên giao diện mời người ta bấm thử; một dòng lệnh thì
không.

⛔ Và nó chạm **dữ liệu sinh trắc của một con người**. Nên công cụ này:

  · làm **từng giọng một** — không có `--tat-ca`, có chủ ý;
  · **in ra** tên, chủ sở hữu và ngày cam kết trước khi đổi, để người chạy nhìn
    thấy thứ mình đang công khai;
  · **từ chối** giọng không có `VoiceConsent` — không có bút toán cam kết quyền
    thì không có gì để đứng sau khi ai đó hỏi.

⚠️ Bật cột này KHÔNG chuyển quyền sở hữu và KHÔNG chuyển trách nhiệm. Nó chỉ
   đổi **ai đọc được**. Chủ sở hữu vẫn là chủ sở hữu, và vẫn là người duy nhất
   sửa hay tắt được giọng đó.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice-id", default="")
    ap.add_argument("--bat", action="store_true")
    ap.add_argument("--tat", action="store_true")
    ap.add_argument("--xem", action="store_true", help="Liet ke kho chung.")
    a = ap.parse_args(argv)

    from sqlalchemy import select

    from apps.ltt_voice.tables import VoiceConsent, VoiceProfile
    from platform_core.db import get_session

    gen = get_session()
    db = next(gen)
    try:
        if a.xem or not a.voice_id:
            ds = list(db.execute(select(VoiceProfile).where(
                VoiceProfile.dung_chung.is_(True))
                .order_by(VoiceProfile.ten_hien_thi)).scalars())
            print(f"KHO CHUNG — {len(ds)} giong")
            for h in ds:
                print(f"  {h.public_id}  {h.trang_thai:10} {h.ten_hien_thi}")
            if not a.voice_id:
                return 0

        ho_so = db.execute(select(VoiceProfile).where(
            VoiceProfile.public_id == a.voice_id)).scalar_one_or_none()
        if ho_so is None:
            print(f"KHONG THAY {a.voice_id}", file=sys.stderr)
            return 2

        ck = db.execute(select(VoiceConsent).where(
            VoiceConsent.profile_id == ho_so.id)).scalars().first()

        print(f"\n  giong      : {ho_so.ten_hien_thi}")
        print(f"  public_id  : {ho_so.public_id}")
        print(f"  chu so huu : {ho_so.owner_id}")
        print(f"  trang thai : {ho_so.trang_thai}")
        print(f"  dung chung : {ho_so.dung_chung}")
        print(f"  cam ket    : {'co, ' + str(ck.tao_luc)[:19] if ck else 'KHONG CO'}")

        if not (a.bat or a.tat):
            print("\n(chi xem — dung `--bat` hoac `--tat` de doi)")
            return 0

        if a.bat:
            if ck is None:
                # ⛔ Không có bút toán cam kết thì không công khai. Đây là chốt
                #    pháp lý, không phải một phép kiểm dữ liệu: khi ai đó hỏi
                #    "giọng này ở đâu ra", `VoiceConsent` là câu trả lời duy
                #    nhất ta có.
                print("\nTU CHOI: giong nay khong co ban ghi `VoiceConsent`.",
                      file=sys.stderr)
                return 2
            if ho_so.trang_thai != "active":
                print(f"\nTU CHOI: giong dang `{ho_so.trang_thai}`, chua the "
                      f"dua vao kho chung.", file=sys.stderr)
                return 2
            ho_so.dung_chung = True
            print("\n=> DA DUA VAO KHO CHUNG. Moi khach deu se thay giong nay.")
        else:
            ho_so.dung_chung = False
            print("\n=> DA GO KHOI KHO CHUNG. Ban tieng da tao van con nguyen.")
        db.commit()
        return 0
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
