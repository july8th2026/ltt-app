"""Giả lập MỘT KHÁCH THẬT gọi `image.ltt` — chạy trên máy ngoài, qua Internet.

    python tools\\khach_gia_lap_anh.py            # vẽ một ảnh, tải về
    python tools\\khach_gia_lap_anh.py --mo-ta "..." --so 2

🔴 VÌ SAO TỆP NÀY TỒN TẠI. Cả tuần này ta đo API bằng `TestClient`, bằng loopback
   `127.0.0.1:8100`, và bằng test chạy trong chính kho mã. **Không cái nào là
   máy khách.** Chúng bỏ qua Cloudflare, bỏ qua DNS, bỏ qua việc khách chỉ có
   đúng hai thứ: một khoá và trang tài liệu.

⛔ Và mọi lỗi đắt nhất tuần này đều CHỈ lộ ra ở lượt gọi thật đầu tiên từ máy
   khách: `User-Agent` mặc định của `urllib` bị Cloudflare trả 403, tiền kẹt
   trong hold, ngữ cảnh gửi model bị bóp méo, ví dụ mẫu tự mâu thuẫn.

⭐ NÊN TỆP NÀY CỐ Ý NGHÈO NÀN:
   * chỉ dùng thư viện chuẩn — không `httpx`, không SDK của ta;
   * **không** import bất cứ thứ gì từ `platform_core`/`server`;
   * chỉ gọi những endpoint đã công bố, đúng thứ tự trang tài liệu ghi.

   Nếu nó chạy được thì khách chạy được. Nếu nó cần một thứ không có trong tài
   liệu thì **tài liệu thiếu**, chứ không phải khách sai.

⚠️ NÓ TIÊU TIỀN THẬT. Mỗi ảnh là một lượt vẽ có thật trên GPU và một bút toán có
   thật trong sổ credit.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import time
import urllib.error
import urllib.request
import uuid

# 🔴 BẮT BUỘC. Cloudflare trả 403 cho `User-Agent` mặc định của `urllib`
#    **trước khi** request tới được máy chủ — nên triệu chứng là "khoá sai",
#    và người ta đi kiểm khoá. Đã mất một buổi vì đúng chỗ này.
UA = "ltt-khach-gia-lap/1.0"


def goi(goc: str, khoa: str, method: str, duong: str,
        than: dict | None = None, headers: dict | None = None) -> tuple:
    du = json.dumps(than).encode() if than is not None else None
    rq = urllib.request.Request(
        goc.rstrip("/") + "/api/v1" + duong, data=du, method=method,
        headers={"Authorization": "Bearer " + khoa,
                 "Content-Type": "application/json",
                 "User-Agent": UA, **(headers or {})})
    try:
        with urllib.request.urlopen(rq, timeout=120) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        noi = e.read()
        try:
            return e.code, json.loads(noi or b"{}")
        except ValueError:
            return e.code, {"raw": noi[:400].decode("utf-8", "replace")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--goc", default=os.environ.get(
        "LTT_BASE_URL", "https://app.lttstudios.com"))
    ap.add_argument("--khoa", default=os.environ.get("LTT_API_KEY", ""))
    ap.add_argument("--mo-ta", dest="mo_ta",
                    default="A calico cat sleeping on a windowsill, "
                            "afternoon light, photographic")
    ap.add_argument("--so", type=int, default=1)
    ap.add_argument("--ra", default="anh_khach_gia_lap")
    a = ap.parse_args()

    if not a.khoa:
        print("Thieu khoa. Dat LTT_API_KEY hoac dung --khoa.")
        return 1

    print(f"Goc     : {a.goc}")
    print(f"Khoa    : {len(a.khoa)} ky tu\n")

    # ── Bước 0: ta là ai, và có bao nhiêu tiền ──────────────────────────────
    ma, me = goi(a.goc, a.khoa, "GET", "/me")
    print(f"GET  /me                -> {ma}")
    if ma != 200:
        print(f"     {me}")
        return 1
    print(f"     scopes={me.get('scopes')}")
    print(f"     allowed_tools={me.get('allowed_tools') or 'tat ca'}")

    ma, du = goi(a.goc, a.khoa, "GET", "/credits/balance")
    truoc = du.get("balance")
    print(f"GET  /credits/balance   -> {ma}  so du {truoc}\n")

    # ── Bước 1: công cụ nào đang mở ─────────────────────────────────────────
    ma, ds = goi(a.goc, a.khoa, "GET", "/tools")
    ten = [t.get("name") for t in (ds.get("items") or [])]
    print(f"GET  /tools             -> {ma}  {ten}")
    if "image.ltt" not in ten:
        print("     `image.ltt` khong nam trong danh sach -> khoa nay khong goi duoc no.")
        return 1

    # ── Bước 2: báo giá ─────────────────────────────────────────────────────
    dau_vao = {"prompt": a.mo_ta, "mode": "t2i", "count": a.so}
    ma, bao_gia = goi(a.goc, a.khoa, "POST", "/quotes",
                      {"tool": "image.ltt", "input": dau_vao})
    print(f"POST /quotes            -> {ma}")
    if ma != 200:
        print(f"     {bao_gia}")
        return 1
    print(f"     gia={bao_gia.get('credits')} credit  het han={bao_gia.get('expires_at')}")

    # ── Bước 3: chạy ────────────────────────────────────────────────────────
    # ⚠️ Khoá idempotency sinh MỘT lần và dùng lại cho mọi lần thử lại của
    #    **chính lượt này**. Sinh khoá mới khi thử lại là tạo job thứ hai và
    #    trả tiền hai lần.
    khoa_idem = uuid.uuid4().hex
    ma, job = goi(a.goc, a.khoa, "POST", "/jobs",
                  {"tool": "image.ltt", "quote": bao_gia.get("quote"),
                   "input": dau_vao},
                  headers={"Idempotency-Key": khoa_idem})
    print(f"POST /jobs              -> {ma}")
    if ma not in (200, 201):
        print(f"     {job}")
        return 1
    job_id = job.get("job_id") or job.get("id")
    print(f"     job_id={job_id}  trang thai={job.get('status')}")

    # ── Bước 4: chờ ─────────────────────────────────────────────────────────
    bat_dau = time.monotonic()
    trang_thai, cuoi = "", {}
    while time.monotonic() - bat_dau < 600:
        time.sleep(5)
        ma, cuoi = goi(a.goc, a.khoa, "GET", f"/jobs/{job_id}")
        trang_thai = str(cuoi.get("status") or "")
        print(f"     GET /jobs/{job_id[:12]}… -> {ma}  {trang_thai}"
              f"  ({int(time.monotonic() - bat_dau)}s)")
        if trang_thai in {"succeeded", "failed", "cancelled"}:
            break
    if trang_thai != "succeeded":
        print(f"\nJob khong thanh cong: {trang_thai}")
        print(json.dumps(cuoi, ensure_ascii=False, indent=2)[:900])
        return 1

    # ── Bước 5: lấy ảnh ─────────────────────────────────────────────────────
    #
    # 🔴 ARTIFACT NẰM Ở `outputs[]`, KHÔNG Ở `result`.
    #
    #    Bản đầu của tệp này đi tìm `result.image_keys` — vì trang tham chiếu
    #    liệt kê `image_keys: artifact[]` trong bảng "Kết quả", nên suy ra thế là
    #    tự nhiên. Chỗ đó **không có gì**: `result` chỉ giữ phần dữ liệu thuần
    #    (với `image.ltt` là `prompt`).
    #
    # ⛔ Và đó là toàn bộ giá trị của bài thử này: kịch bản dừng lại **sau khi
    #    job đã xong và tiền đã bị thu**. Không một lỗi nào từ máy chủ. Tài liệu
    #    đã được sửa cùng ngày; giữ chú thích để không ai "dọn" nó về chỗ cũ.
    ids = [o.get("id") for o in (cuoi.get("outputs") or []) if o.get("id")]
    print(f"\n     artifact: {ids}")
    if not ids:
        print(json.dumps(cuoi, ensure_ascii=False, indent=2)[:900])
        return 1

    thu_muc = pathlib.Path(a.ra)
    thu_muc.mkdir(parents=True, exist_ok=True)
    for i, aid in enumerate(ids, 1):
        ma, tra = goi(a.goc, a.khoa, "GET", f"/artifacts/{aid}")
        print(f"GET  /artifacts/{str(aid)[:14]}… -> {ma}")
        if ma != 200:
            print(f"     {tra}")
            return 1
        url = tra.get("url") or tra.get("download_url")
        rq = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(rq, timeout=120) as r:
            noi = r.read()
        tep = thu_muc / f"anh_{i}.png"
        tep.write_bytes(noi)
        print(f"     da tai {len(noi):,} byte -> {tep}")

    # ── Bước 6: tiền ────────────────────────────────────────────────────────
    ma, du2 = goi(a.goc, a.khoa, "GET", "/credits/balance")
    sau = du2.get("balance")
    print(f"\nGET  /credits/balance   -> {ma}  so du {sau}")
    print(f"     da thu: {truoc} - {sau} = {(truoc or 0) - (sau or 0)} credit")
    print(f"     bao gia noi truoc: {bao_gia.get('credits')} credit")
    print("\nXONG.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
