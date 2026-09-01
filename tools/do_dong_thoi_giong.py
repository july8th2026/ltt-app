r"""
do_dong_thoi_giong.py — năm khách bấm cùng lúc thì chuyện gì xảy ra?

    powershell -ExecutionPolicy Bypass -File .\setup\do_dong_thoi_giong.ps1

## Câu hỏi

`ToolSpec` khai `admission_resource="vieneu_gpu"`, `admission_slots=1`, và cổng
giọng có một semaphore một suất. Nghĩa là **một lượt sinh tại một thời điểm**.
Điều đó hoàn toàn hợp lý với một GPU — nhưng chưa ai đo lượt thứ năm phải chờ
bao lâu, và đó là con số quyết định "bán rộng tới đâu thì gãy".

VoxServe và sglang-omni giải bài này bằng **gộp lô liên tục**. Trước khi nghĩ
tới việc đó, phải biết con số hiện tại xấu tới mức nào — đổi kiến trúc trước
khi đo là cách chắc chắn nhất để tối ưu nhầm chỗ.

## Cách đo

Nộp N job **cùng một lúc** qua đúng hàm mà route gọi, rồi bám theo từng job:
thời điểm nộp → lúc worker nhặt → lúc xong. Từ đó ra ba con số cho mỗi job:

  · **nhặt**     — nộp tới lúc worker nhặt (`created_at` → `started_at`).
  · **xếp hàng** — nhặt tới lúc giành được suất (`started_at` → `admitted_at`).
                   🔴 Đây mới là chỗ hàng đợi thật sự nằm.
  · **làm**      — giành suất tới xong. Thời gian LÀM VIỆC thật.
  · **tổng**     — nộp tới xong. Thứ khách cảm nhận.

⭐ Bản đầu của tệp này chỉ đo "chờ" và "chạy", và nó vẽ ra một bức tranh SAI:
   *chờ 0,4 giây* cho cả năm job, còn *chạy* tăng 22 → 46 → 67 → 88 → 109 giây.
   Đọc lên như thể job thứ năm chạy chậm gấp năm — trong khi thật ra nó làm việc
   đúng 22 giây và **đứng xếp hàng** 87 giây.

   Nền tảng đã ghi sẵn `admitted_at` (H41.9/Q3) đúng để tách hai thứ đó. Một
   phép đo không đọc nó thì tự tay trộn "chờ" vào "làm", rồi kết luận nhầm rằng
   hệ thống chậm dần khi tải lên.

⛔ NÓ CHẠM TIỀN THẬT. N job trả phí, giữ chỗ rồi quyết toán trong sổ credit.
   Dùng tài khoản thử `.local`, và in số dư trước/sau để đối chiếu.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

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

#: Câu ngắn, cố ý: ta đang đo HÀNG ĐỢI, không đo tốc độ sinh. Câu càng dài thì
#: thời gian chạy càng át thời gian chờ và phép đo càng mờ.
CAU = ("Đây là lượt thử số {i} trong phép đo đồng thời của hệ thống giọng nói "
       "LTT Studios.")


def _giay(a, b) -> float:
    if a is None or b is None:
        return -1.0
    return round((b - a).total_seconds(), 2)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--so-job", type=int, default=5)
    ap.add_argument("--email", default="thu.giongnoi@lttstudios.local")
    ap.add_argument("--cho-giay", type=int, default=600)
    ap.add_argument("--json", default="")
    a = ap.parse_args(argv)

    from sqlalchemy import select

    from platform_core import credit, users
    from platform_core.db import get_session
    from platform_core.job_submit import submit_with_credit
    from platform_core.models import JOB_CANCELLED, JOB_DONE, JOB_ERROR, Job
    from platform_core.registry import discover

    KET_THUC = (JOB_DONE, JOB_ERROR, JOB_CANCELLED)

    mf = next((i.manifest for i in discover() if i.manifest.slug == "ltt_voice"), None)
    if mf is None:
        print("khong thay app ltt_voice", file=sys.stderr)
        return 2
    tool = mf.tools[0]

    gen = get_session()
    db = next(gen)
    try:
        u = users.tim_theo_email(db, a.email)
        if u is None:
            print(f"khong thay {a.email}", file=sys.stderr)
            return 2
        truoc = credit.so_du(db, u.id)
        can = sum(mf.credit_cost({"text": CAU.format(i=i + 1)})
                  for i in range(a.so_job))
        print(f"Tai khoan: {u.email}")
        print(f"So du    : {truoc} credit   (bao gia {a.so_job} job: {can})")
        if truoc < can:
            print(f"\nDUNG: khong du credit ({truoc} < {can}).", file=sys.stderr)
            return 3

        # ── nộp TẤT CẢ trong một transaction, để chúng thật sự cùng lúc ──────
        ids = []
        t0 = time.time()
        for i in range(a.so_job):
            job = submit_with_credit(
                db, user_id=str(u.id), app_slug="ltt_voice",
                job_type="ltt_voice.synthesize",
                params={"text": CAU.format(i=i + 1), "voice_id": "",
                        "preset": "", "owner_id": u.id},
                admission_resource=tool.admission_resource,
                admission_slots=tool.admission_slots)
            ids.append(str(job.id))
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    print(f"Da nop {len(ids)} job cung luc luc {time.strftime('%H:%M:%S')}\n")

    # ── bám theo tới khi tất cả kết thúc ────────────────────────────────────
    xong: dict = {}
    while time.time() - t0 < a.cho_giay and len(xong) < len(ids):
        gen = get_session()
        db = next(gen)
        try:
            for jid in ids:
                if jid in xong:
                    continue
                j = db.execute(select(Job).where(Job.id == jid)).scalar_one_or_none()
                if j is not None and j.status in KET_THUC:
                    ad = getattr(j, "admitted_at", None)
                    xong[jid] = {
                        "job_id": jid[:8],
                        "status": j.status,
                        "nhat_s": _giay(j.created_at, j.started_at),
                        "admit_s": _giay(j.started_at, ad),
                        "lam_s": _giay(ad or j.started_at, j.finished_at),
                        "tong_s": _giay(j.created_at, j.finished_at),
                        "credit": (j.result or {}).get("credit_cost"),
                    }
                    m = xong[jid]
                    print(f"  xong {jid[:8]}  nhat {m['nhat_s']:>5.2f}s  "
                          f"xep hang {m['admit_s']:>6.2f}s  "
                          f"lam {m['lam_s']:>6.2f}s  "
                          f"tong {m['tong_s']:>6.2f}s  ({m['status']})")
        finally:
            try:
                next(gen)
            except StopIteration:
                pass
        if len(xong) < len(ids):
            time.sleep(2)

    thieu = [i for i in ids if i not in xong]
    if thieu:
        print(f"\nHET GIO sau {a.cho_giay}s — {len(thieu)} job chua ket thuc.")

    gen = get_session()
    db = next(gen)
    try:
        sau = credit.so_du(db, u.id)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    ds = sorted(xong.values(), key=lambda m: m["tong_s"])
    if ds:
        xh = [m["admit_s"] for m in ds if m["admit_s"] >= 0]
        lam = [m["lam_s"] for m in ds if m["lam_s"] >= 0]
        print(f"\n{'=' * 68}")
        print(f"  {len(ds)} job dong thoi, {tool.admission_slots} suat")
        print("=" * 68)
        if lam:
            print(f"  LAM VIEC that : {min(lam):>6.2f} - {max(lam):>6.2f}s  "
                  f"(tb {sum(lam) / len(lam):.2f}s)")
        if xh:
            print(f"  XEP HANG      : {min(xh):>6.2f} - {max(xh):>6.2f}s   "
                  f"<- cai gia cua MOT suat")
        print(f"  tong ca lo    : {max(m['tong_s'] for m in ds):>6.2f}s")
        if lam:
            tb = sum(lam) / len(lam)
            print()
            print(f"  Voi mot suat, job thu N cho khoang (N-1) x {tb:.0f}s.")
            print("  Xep hang KHONG lam job het gio: dong ho `max_runtime_s` chi bat")
            print("  dau SAU khi gianh duoc suat (`_canh_gio` chay trong")
            print("  `_chay_handler`, sau `hold_persisted`). Gioi han that nam o cho")
            print("  khac — moi job dang cho van GIU MOT SUAT WORKER.")

    print(f"\nSO TIEN: {truoc} -> {sau}  (da tru {truoc - sau}, "
          f"handler bao {sum(m.get('credit') or 0 for m in ds)})")

    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump({"so_job": len(ids), "suat": tool.admission_slots,
                       "job": ds, "credit_truoc": truoc, "credit_sau": sau},
                      f, ensure_ascii=False, indent=2)
        print(f"Da ghi: {a.json}")
    return 0 if not thieu else 1


if __name__ == "__main__":
    raise SystemExit(main())
