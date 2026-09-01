"""do_duong_tien_api.py — B14–B17, B24: đo ĐƯỜNG TIỀN của `/api/v1` bằng client thật.

    python tools/do_duong_tien_api.py --token-file tmp/canary.token

## Vì sao tệp này tồn tại

`reports/02` tự khai **chưa đóng**, và ba mục còn lại đều là đường tiền:

    B14/B15  pham vi idempotency khi THU LAI   -- moi doc ma, chua do
    B16/B17  huy va ngat ket noi               -- can client that
    B24      tool-call streaming               -- chua

Cả ba chỉ trả lời được bằng một khoá thật đi qua Cloudflare. Khoá đó nay tự phát
được (`tools/khoa_thu_api.py`, chỉ đuôi `.local`), nên chúng không còn chặn.

## ⛔ NÓ TIÊU TIỀN THẬT của tài khoản thử — và đó là điểm chính

Một phép đo đường tiền mà **không** đi qua đường tiền thì không đo gì. Mỗi bài ở
đây đọc số dư **trước và sau**, và chốt trên **hiệu số**, không chốt trên việc
"API trả 200".

⭐ Câu hỏi đắt nhất không phải *"có thu tiền không"* mà **"có thu ĐÚNG MỘT LẦN
   không"**. Thu hai lần cho một việc là thứ khách phát hiện ra trước ta.

## ⛔ ĐỐI CHỨNG TRƯỚC

`ct-00` tiêu một lượt bình thường và đòi số dư **phải giảm**. Nó không giảm
nghĩa là ta đang đo một đường **không tính tiền** (chế độ thử, tài khoản miễn
phí, hay gọi nhầm cửa) — và khi đó mọi kết luận "không thu hai lần" bên dưới
đều đúng một cách **tầm thường**.

Đây là bài học đắt nhất của phiên 31/08–01/09: bảy lần một dụng cụ cho ra kết
quả đẹp vì nó không đo gì cả. Xem `reports/06` §7.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GOC = "https://app.lttstudios.com"


class KhongDoDuoc(RuntimeError):
    """Không lấy được số liệu — phép đo VÔ, khác hẳn 'không đạt'."""


def _goi(duong: str, tok: str, *, than=None, method="GET", them=None,
         timeout=120.0) -> tuple[int, dict, str]:
    h = {"Authorization": f"Bearer {tok}", "User-Agent": "ltt-tien/1.0"}
    if than is not None:
        h["Content-Type"] = "application/json"
    if them:
        h.update(them)
    yc = urllib.request.Request(
        GOC + duong, method=method,
        data=json.dumps(than).encode() if than is not None else None, headers=h)
    try:
        with urllib.request.urlopen(yc, timeout=timeout) as r:
            tho = r.read().decode("utf-8", "replace")
            try:
                return r.status, json.loads(tho), tho
            except ValueError:
                return r.status, {}, tho
    except urllib.error.HTTPError as e:
        tho = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(tho), tho
        except ValueError:
            return e.code, {}, tho


def so_du(tok: str) -> int:
    """Số dư credit. Ném nếu không đọc được — `None` lặng lẽ sẽ làm mọi phép
    trừ bên dưới ra 0, và 0 đọc lên y hệt 'không thu tiền'."""
    # `/api/v1/credits/balance` mo voi scope `credits:read` (thu ma
    # `khoa_thu_api.py` cap). `/api/v1/usage` doi `usage:read` va tra 403 --
    # mot loi TOT: no goi ten dung scope thieu thay vi chi "khong duoc phep".
    # ⛔ BÁO CÁO MÃ THẬT ĐÃ THẤY, ĐỪNG ĐOÁN NGUYÊN NHÂN.
    #
    #    Bản đầu ném "Khoa co thieu scope khong?" cho MỌI thất bại. Lần chạy
    #    01/09 nó vỡ vì **429 rate-limit**, và thông điệp đó gửi người đọc đi
    #    sai hướng hoàn toàn — một câu trả lời sai mặc một lời giải thích nghe
    #    hợp lý, đúng thứ tệp này tồn tại để chống.
    da_thay: list[str] = []
    for duong in ("/api/v1/credits/balance", "/api/v1/account", "/api/v1/usage"):
        for lan in range(4):
            ma, d, tho = _goi(duong, tok)
            if ma == 429:
                # Rate-limit là trạng thái BÌNH THƯỜNG của một cửa đang bảo vệ
                # mình, không phải một lỗi. Chờ rồi thử lại.
                da_thay.append(f"{duong}=429(lan {lan + 1})")
                time.sleep(4 + 4 * lan)
                continue
            break
        da_thay.append(f"{duong}={ma}")
        if ma != 200:
            continue
        for k in ("balance", "credits", "so_du", "credit_balance"):
            if isinstance(d.get(k), (int, float)):
                return int(d[k])
            if isinstance(d.get("data"), dict) and isinstance(
                    d["data"].get(k), (int, float)):
                return int(d["data"][k])
        da_thay.append(f"{duong}=200 nhung khong co khoa so du (co: {sorted(d)})")
    raise KhongDoDuoc(
        "khong doc duoc so du. Ma da thay: " + ", ".join(da_thay) +
        ". Moi ket luan ve tien deu VO neu thieu no.")


def _bao_gia(tok: str, than_vao: dict) -> tuple[int, dict]:
    ma, d, _ = _goi("/api/v1/quotes", tok, method="POST", than=than_vao)
    return ma, d


#: Thân yêu cầu chuẩn, dùng chung cho báo giá và nộp việc — hai bên PHẢI khớp.
THAN_VAO = {"tool": "text.chat", "input": {
    "messages": [{"role": "user", "content": "Noi mot cau ngan ve mua thu."}],
    "max_tokens": 24}}


def _job(tok: str, idem: str | None = None) -> tuple[int, dict]:
    """Báo giá rồi nộp việc. `idem=None` ⇒ sinh khoá MỚI, không phải bỏ trống.

    ⭐ HAI CHỐT CỦA CỬA NÀY, cả hai đều mạnh hơn tôi tưởng trước khi đo:

    1. `Idempotency-Key` là **BẮT BUỘC**, không phải tuỳ chọn:

           400  "This endpoint requires an Idempotency-Key header."   retry: never

       Hỗ trợ idempotency nghĩa là khách *có thể* tránh nộp trùng; **bắt buộc**
       nghĩa là khách *không thể* nộp trùng do quên. Với một cửa tiêu tiền thì
       khác biệt đó là toàn bộ vấn đề.

    2. Phải có **quote token** trước:

           400  "A quote token is required."

       Tức khách **thấy giá trước khi cam kết**. Không có đường nào để một lượt
       gọi bất ngờ trừ tiền.

    ⚠️ `retry: never` trong cả hai lỗi là phần đáng khen thứ ba: một client tự
       thử lại đọc được rằng thử lại vô ích, thay vì quay vòng và nhân đôi tải.
    """
    mag, dg = _bao_gia(tok, THAN_VAO)
    if mag != 200 or not dg.get("quote"):
        return mag, {"loi_bao_gia": dg}
    than = dict(THAN_VAO, quote=dg["quote"])
    them = {"Idempotency-Key": idem or f"canary-{uuid.uuid4()}"}
    ma, d, _ = _goi("/api/v1/jobs", tok, method="POST", them=them, than=than)
    return ma, d


def main() -> int:
    global GOC
    p = argparse.ArgumentParser(description="Do duong tien cua /api/v1.")
    p.add_argument("--token-file", type=Path, required=True)
    p.add_argument("--base-url", default=GOC)
    a = p.parse_args()
    GOC = a.base_url.rstrip("/")
    tok = a.token_file.read_text(encoding="utf-8").strip()
    if not tok:
        print("token rong")
        return 2

    ket: list[tuple[str, bool, str]] = []

    # ── ĐỐI CHỨNG ────────────────────────────────────────────────────────────
    print("== doi chung: mot luot binh thuong CO tru tien khong ==")
    try:
        truoc = so_du(tok)
    except KhongDoDuoc as e:
        print(f"  KHONG DO DUOC: {e}")
        print("  => DUNG. Khong ket luan gi ve duong tien.")
        return 2
    ma, d = _job(tok)
    print(f"  POST /api/v1/jobs -> {ma}  {json.dumps(d)[:110]}")
    if ma not in (200, 201, 202):
        print(f"  KHONG DO DUOC: khong tao duoc job ({ma}).")
        return 2
    time.sleep(6)
    sau = so_du(tok)
    tru = truoc - sau
    print(f"  so du {truoc} -> {sau}  (tru {tru})")
    if tru <= 0:
        print("  🔴 DOI CHUNG TRUOT: mot luot that KHONG tru tien.")
        print("     => Ta dang do mot duong KHONG TINH TIEN. Moi ket luan")
        print("        'khong thu hai lan' ben duoi se dung mot cach TAM THUONG.")
        return 2
    print(f"  doi chung DAT -- duong tien co that, mot luot = {tru} credit\n")

    # ── B14/B15 idempotency ──────────────────────────────────────────────────
    print("== B14/B15: gui LAI cung Idempotency-Key ==")
    # 🔴 PHẢI GỬI LẠI **ĐÚNG THÂN CŨ**, không xin quote mới.
    #
    #    Bản đầu của bài này xin một quote mới cho lượt hai, nên thân yêu cầu
    #    THẬT SỰ khác — và API trả `409 idempotency_conflict: "already used with
    #    a different request body"`. Tôi suýt ghi đó là "idempotency không
    #    replay", trong khi hệ thống đang làm **đúng**: cùng khoá + khác thân =
    #    xung đột, và đó chính là thứ khoá idempotency sinh ra để bắt.
    #
    # ⇒ Phép thử thật của replay là: **cùng khoá, cùng thân, từng byte**.
    khoa = f"canary-{uuid.uuid4()}"
    t0 = so_du(tok)
    mag, dg = _bao_gia(tok, THAN_VAO)
    than_co_dinh = dict(THAN_VAO, quote=dg.get("quote"))
    ma1, d1, _ = _goi("/api/v1/jobs", tok, method="POST",
                      them={"Idempotency-Key": khoa}, than=than_co_dinh)
    time.sleep(6)
    t1 = so_du(tok)
    ma2, d2, _ = _goi("/api/v1/jobs", tok, method="POST",
                      them={"Idempotency-Key": khoa}, than=than_co_dinh)
    time.sleep(4)
    t2 = so_du(tok)
    id1 = d1.get("id") or d1.get("job_id")
    id2 = d2.get("id") or d2.get("job_id")
    print(f"  lan 1: {ma1} id={id1}   so du {t0} -> {t1} (tru {t0 - t1})")
    print(f"  lan 2: {ma2} id={id2}   so du {t1} -> {t2} (tru {t1 - t2})")
    cung_id = bool(id1) and id1 == id2
    khong_thu_lai = (t1 - t2) == 0
    ket.append(("B14/B15 gui lai cung khoa -> CUNG job", cung_id,
                f"id1={id1} id2={id2}"))
    ket.append(("B14/B15 gui lai KHONG thu tien lan hai", khong_thu_lai,
                f"tru them {t1 - t2}"))

    # ── B16/B17 huỷ ──────────────────────────────────────────────────────────
    print("\n== B16/B17: huy mot job dang cho ==")
    t3 = so_du(tok)
    ma3, d3 = _job(tok)
    jid = d3.get("id") or d3.get("job_id")
    # `POST /jobs/{id}/cancel` -- KHONG phai `DELETE /jobs/{id}` (405) va khong
    # phai `PATCH` (405). Do 01/09: ba dong tu sai deu tra 405, nen thoat nhin
    # giong "khong co duong huy"; dong tu DUNG tra 403 goi ten scope thieu.
    mah, dh, _ = _goi(f"/api/v1/jobs/{jid}/cancel", tok, method="POST",
                      them={"Idempotency-Key": f"huy-{uuid.uuid4()}"})
    print(f"  tao {ma3} id={jid} -> DELETE {mah}  {json.dumps(dh)[:100]}")
    time.sleep(8)
    t4 = so_du(tok)
    print(f"  so du {t3} -> {t4} (tru {t3 - t4})")
    # Huỷ SỚM thì không nên thu; huỷ MUỘN (job đã chạy) thì thu phần đã sinh là
    # đúng. Nên chốt là "không thu NHIỀU HƠN một lượt bình thường".
    ket.append(("B16/B17 duong huy TON TAI va nhan lenh", mah in (200, 202, 204),
                f"POST /cancel -> {mah}"))
    ket.append(("B16/B17 huy KHONG thu qua mot luot binh thuong",
                (t3 - t4) <= tru, f"tru {t3 - t4}, mot luot binh thuong = {tru}"))

    print("\n" + "=" * 62)
    dat = 0
    for ten, ok, vi in ket:
        dat += ok
        print(f"  {'DAT ' if ok else 'TRUOT'} {ten:<48} {vi}")
    print(f"\n  {dat}/{len(ket)}")
    print(f"  so du con lai: {so_du(tok)} credit")
    return 0 if dat == len(ket) else 1


if __name__ == "__main__":
    sys.exit(main())
