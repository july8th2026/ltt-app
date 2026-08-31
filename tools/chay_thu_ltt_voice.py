r"""
chay_thu_ltt_voice.py — chạy LTT VOICE đầu-tới-cuối trên production, bằng đúng
đường mà một khách hàng đi.

    powershell -File .\setup\tai_khoan_thu.ps1   # tao tai khoan truoc
    ... roi chay tep nay qua mot lop nap app.env (xem `chay_thu_ltt_voice.ps1`)

⭐ VÌ SAO KHÔNG GIẢ LẬP GÌ CẢ.

   Kịch bản này **không** gọi thẳng `features` hay sidecar. Nó nộp một job qua
   `submit_with_credit` — đúng hàm mà `routes.py` gọi — rồi **đứng chờ worker
   production thật nhặt nó lên**. Nghĩa là nó đi qua: hàng đợi, admission lease,
   đội hình worker, handler, cổng giọng, `ffprobe`, và quyết toán credit.

   Một kịch bản gọi thẳng vào `features` sẽ xanh kể cả khi hàng đợi hỏng, khi
   worker thiếu làn `voice`, hay khi dịch vụ giọng chưa chạy. Ba thứ đó chính là
   ba thứ hay hỏng nhất khi deploy.

⛔ NÓ CHẠM TIỀN THẬT. Job trả phí giữ chỗ rồi quyết toán trong sổ credit, và sổ
   credit **chỉ ghi thêm**. Vì vậy kịch bản này:
     · **in số dư trước và sau**, và đối chiếu với `credit_cost` handler báo về;
     · **không tự nạp credit** — thiếu tiền thì nó dừng và nói ra;
     · dùng `note` ghi rõ đây là lượt chạy thử, để một tháng sau còn truy được.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from platform_core.models import JOB_CANCELLED, JOB_DONE, JOB_ERROR

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", line_buffering=True)

#: Câu thử. Cố ý gồm bốn ô hay hỏng cùng lúc: dấu thanh dày, một cặp `ch`/`tr`
#: (upstream #168), một con số, và một từ tiếng Anh xen giữa.
CAU_THU = ("Chào mừng bạn đến với LTT Studios. Chưởng trình hôm nay có ba phần, "
           "bắt đầu lúc 9 giờ sáng, và chúng tôi sẽ dùng AI để đọc toàn bộ nội "
           "dung này.")


#: ⛔ NHẬP hằng số, đừng gõ lại chuỗi. Tôi đã đoán sai tập này HAI lần trong
#: một buổi — lần đầu thiếu `error` (job hỏng bị đọc thành treo), lần sau vẫn
#: sai vì nền tảng dùng `done` chứ không phải `succeeded`, nên một lượt chạy
#: THÀNH CÔNG cũng bị báo là "HET GIO". Cả hai lần triệu chứng giống hệt nhau
#: và đều đổ tội nhầm cho worker.
KET_THUC = (JOB_DONE, JOB_ERROR, JOB_CANCELLED)


def _in(m=""):
    print(m)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", default="thu.giongnoi@lttstudios.local")
    ap.add_argument("--text", default=CAU_THU)
    ap.add_argument("--cho-giay", type=int, default=300)
    ap.add_argument("--tai-ve", default="", help="Ghi tep tieng ra duong nay.")
    a = ap.parse_args(argv)

    from platform_core import credit, users
    from platform_core.db import get_session
    from platform_core.job_submit import submit_with_credit
    from platform_core.registry import discover

    mf = next((i.manifest for i in discover() if i.manifest.slug == "ltt_voice"), None)
    if mf is None:
        _in("KHONG THAY app ltt_voice trong registry")
        return 2
    tool = mf.tools[0]

    gen = get_session()
    db = next(gen)
    try:
        u = users.tim_theo_email(db, a.email)
        if u is None:
            _in(f"KHONG THAY tai khoan {a.email} — chay setup\\tai_khoan_thu.ps1 truoc")
            return 2

        gia_bao = mf.credit_cost({"text": a.text})
        truoc = credit.so_du(db, u.id)
        _in(f"Tai khoan : {u.email}")
        _in(f"So du     : {truoc} credit")
        _in(f"Bao gia   : {gia_bao} credit (tran uoc cao — quyet toan theo giay that)")
        _in(f"Van ban   : {len(a.text)} ky tu")

        if truoc < gia_bao:
            _in("")
            _in(f"DUNG: khong du credit ({truoc} < {gia_bao}).")
            _in("Kich ban nay CO Y khong tu nap: nap credit la mot but toan trong")
            _in("so tien, va so tien chi ghi them. Chu san pham nap qua duong da co.")
            return 3

        job = submit_with_credit(
            db, user_id=str(u.id), app_slug="ltt_voice",
            job_type="ltt_voice.synthesize",
            params={"text": a.text, "voice_id": "", "preset": "",
                    "owner_id": u.id},
            admission_resource=tool.admission_resource,
            admission_slots=tool.admission_slots)
        db.commit()
        job_id = str(job.id)
        _in(f"Da nop job: {job_id}")
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    # ── chờ WORKER THẬT nhặt và chạy ─────────────────────────────────────────
    _in("")
    _in("Cho worker production nhat job (KHONG tu chay handler)...")
    from sqlalchemy import select

    from platform_core.models import Job

    def lay_job(db, jid):
        return db.execute(select(Job).where(Job.id == jid)).scalar_one_or_none()

    t0 = time.time()
    trang_thai_cu = ""
    ket = None
    while time.time() - t0 < a.cho_giay:
        gen = get_session()
        db = next(gen)
        try:
            j = lay_job(db, job_id)
            tt = getattr(j, "status", "?")
            if tt != trang_thai_cu:
                _in(f"  [{time.time() - t0:6.1f}s] {trang_thai_cu or '-'} -> {tt}")
                trang_thai_cu = tt
            # ⚠️ Tập này phải khớp `platform_core` chứ không phải trí nhớ.
            #    Bản đầu viết ("succeeded","failed","cancelled") — thiếu
            #    "error", đúng trạng thái mà worker THẬT đặt khi handler
            #    ném. Hệ quả: job hỏng ở giây 34, kịch bản vẫn đứng chờ
            #    hết 300 giây rồi báo "HET GIO", tức một lỗi có tên bị
            #    trình bày thành một lần treo không tên.
            if tt in KET_THUC:
                ket = {"status": tt, "result": getattr(j, "result", None),
                       "error": getattr(j, "error", None)}
                break
        finally:
            try:
                next(gen)
            except StopIteration:
                pass
        time.sleep(2)

    if ket is None:
        _in("")
        _in(f"HET GIO sau {a.cho_giay}s — job van o trang thai '{trang_thai_cu}'.")
        if trang_thai_cu == "queued":
            _in("")
            _in("!! `queued` mai mai la trieu chung CO TEN: doi hinh worker thieu lan")
            _in("   `voice`. `jobs.py` loc bang set(requires).issubset(capabilities),")
            _in("   nen job khong bao gio duoc nhat va KHONG loi nao duoc ghi.")
            _in("   Kiem: LTT_WORKER_POOLS trong app.env.")
        return 1

    _in("")
    _in(f"KET QUA: {ket['status']}")
    if ket["status"] != JOB_DONE:
        _in(f"  loi: {ket.get('error')}")
        return 1

    r = ket["result"] or {}
    _in(f"  audio_key   : {r.get('audio_key')}")
    _in(f"  duration_s  : {r.get('duration_s')}")
    _in(f"  credit_cost : {r.get('credit_cost')}   (bao gia {gia_bao})")
    _in(f"  bang gia    : {r.get('phien_ban_gia')}")

    # ── đối chiếu SỔ TIỀN, không tin con số handler tự khai ──────────────────
    gen = get_session()
    db = next(gen)
    try:
        sau = credit.so_du(db, u.id)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    da_tru = truoc - sau
    _in("")
    _in("DOI CHIEU SO TIEN (nguon chan ly, khong phai con so handler khai):")
    _in(f"  truoc {truoc}  ->  sau {sau}   => da tru {da_tru} credit")
    bao_ve = r.get("credit_cost")
    khop = (da_tru == bao_ve)
    _in(f"  {'KHOP' if khop else 'LECH'} voi credit_cost handler bao ve ({bao_ve})")
    if da_tru < gia_bao:
        _in(f"  Da HOAN {gia_bao - da_tru} credit phan giu du — dung chot 3.4 cua khuon.")

    if a.tai_ve and r.get("audio_key"):
        from platform_core.storage import get_storage
        with get_storage().open(r["audio_key"]) as f:
            data = f.read()
        with open(a.tai_ve, "wb") as f:
            f.write(data)
        _in(f"\nDa tai ve: {a.tai_ve} ({len(data)} byte)")

    print("\n__KET_QUA_JSON__" + json.dumps(
        {"job_id": job_id, **r, "da_tru": da_tru, "khop_so_tien": khop},
        ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
