"""do_tool_stream_api.py — B24: tool-call qua cửa STREAMING của `/api/v1`.

    python tools/do_tool_stream_api.py --token-file tmp/canary.token

## Vì sao tách khỏi `do_duong_tien_api.py`

Cửa streaming khác hẳn cửa job về hình dạng: không quote token, không
`Idempotency-Key`, và câu trả lời đi ra theo **sự kiện** chứ không theo một thân
JSON. Gộp vào một tệp sẽ làm cả hai khó đọc.

## Phép thử thật của một vòng tool là VÒNG KHÉP KÍN

Thấy `tool_use` trong luồng **chưa chứng minh gì**. Một model có thể phát ra một
lời gọi tool đúng khuôn rồi **bỏ qua kết quả trả về** và bịa câu trả lời cuối.

⇒ Bài `b24-02` gửi lại một `tool_result` chứa **một con số không đoán được**
  (`ton: 42`) và đòi con số ấy xuất hiện trong câu trả lời cuối. Đó là khác biệt
  giữa *"model biết gọi tool"* và *"model dùng được kết quả của tool"* — và chỉ
  cái sau mới có ích cho khách.

## ⛔ Đối chứng: 503 KHÁC "không hỗ trợ"

`/api/v1/responses` trả `503 service_unavailable` ở lượt đo đầu 01/09. Đó **không
phải** bằng chứng rằng cửa ấy không nhận tool — máy B chỉ nạp được một model tại
một thời điểm, và lượt trước đó vừa nạp `qwen38-vision`. Bộ đo này **thử lại**
khi gặp 503 và ghi rõ đã thử mấy lần, thay vì đóng đinh một kết luận vào một
khoảnh khắc của llama-swap.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GOC = "https://app.lttstudios.com"

#: 🔴 KHUON NATIVE CUA ANTHROPIC: `name`/`description`/`input_schema` o MUC TREN
#: CUNG. KHONG phai khuon OpenAI (`{"type":"function","function":{...}}`).
#:
#: Ban dau toi gui khuon OpenAI vao cua nay. Ket qua: HTTP 200, va model tra loi
#: **"Xin loi, hien tai toi khong co tool nao"**. Toi suyt ghi mot khuyet tat
#: nghiem trong ("cua /messages danh roi truong tools") vao ho so cua mot he
#: thong dang chay DUNG.
#:
#: ⚠️ Nhung quan sat con lai VAN dang gia: `tools` sai khuon bi BO QUA IM LANG,
#:    khong phai `400`. Khach go sai hinh dang se nhan mot cau tra loi hop ly ma
#:    sai, thay vi mot loi noi ro. Cho nay lech chuan voi phan con lai cua khu
#:    API, noi ma loi goi ten dung scope thieu va dinh kem `retry: never`.
TOOLS = [{"name": "tra_ton_kho",
          "description": "Tra so luong ton kho cua mot ma hang",
          "input_schema": {"type": "object", "required": ["ma_hang"],
                           "properties": {"ma_hang": {"type": "string"}}}}]

#: Con số KHÔNG ĐOÁN ĐƯỢC. Model chỉ nói ra được nếu nó thật sự đọc `tool_result`.
TON_KHO = 42


def _stream(duong: str, tok: str, than: dict, timeout=120.0) -> dict:
    yc = urllib.request.Request(
        GOC + duong, data=json.dumps(than).encode(), method="POST",
        headers={"Authorization": f"Bearer {tok}", "User-Agent": "ltt-b24/1.0",
                 "Content-Type": "application/json"})
    t0 = time.monotonic()
    dong, loai = [], []
    try:
        with urllib.request.urlopen(yc, timeout=timeout) as r:
            ct = r.headers.get("content-type", "")
            for d in r:
                s = d.decode("utf-8", "replace").strip()
                if not s or s.startswith(":"):
                    continue
                dong.append(s)
                if s.startswith("event: "):
                    loai.append(s[7:])
                elif s.startswith("data: ") and s[6:] != "[DONE]":
                    try:
                        t = json.loads(s[6:]).get("type")
                        if t:
                            loai.append(t)
                    except ValueError:
                        pass
    except urllib.error.HTTPError as e:
        return {"ma": e.code,
                "than": e.read().decode("utf-8", "replace")[:220]}
    return {"ma": 200, "ct": ct, "dong": dong, "loai": loai,
            "giay": round(time.monotonic() - t0, 1)}


def _thu_lai_503(duong, tok, than, lan=3) -> dict:
    """503 = llama-swap đang đổi model, KHÔNG phải 'cửa không hỗ trợ'."""
    for i in range(lan):
        r = _stream(duong, tok, than)
        if r.get("ma") != 503:
            r["so_503"] = i
            return r
        print(f"     503 (lan {i + 1}/{lan}) -- may B doi model, cho roi thu lai")
        time.sleep(20)
    r["so_503"] = lan
    return r


def _gom_tool(dong: list[str]) -> tuple[str, str, str]:
    """(ten tool, id, chuoi tham so) gom từ các delta của luồng."""
    ten = tid = ""
    tham = []
    for s in dong:
        if not s.startswith("data: "):
            continue
        try:
            j = json.loads(s[6:])
        except ValueError:
            continue
        cb = j.get("content_block") or {}
        if cb.get("type") == "tool_use":
            ten = cb.get("name", "") or ten
            tid = cb.get("id", "") or tid
        d = j.get("delta") or {}
        if d.get("type") == "input_json_delta":
            tham.append(d.get("partial_json", ""))
        if d.get("type") == "tool_use" or d.get("name"):
            ten = d.get("name", "") or ten
    return ten, tid, "".join(tham)


def main() -> int:
    global GOC
    p = argparse.ArgumentParser(description="B24: tool-call qua cua streaming.")
    p.add_argument("--token-file", type=Path, required=True)
    p.add_argument("--base-url", default=GOC)
    a = p.parse_args()
    GOC = a.base_url.rstrip("/")
    tok = a.token_file.read_text(encoding="utf-8").strip()

    ket: list[tuple[str, bool, str]] = []
    hoi = [{"role": "user",
            "content": "Con bao nhieu cai ma hang ABC-123 trong kho?"}]

    print("== b24-01: cua /api/v1/messages co phat tool_use trong luong khong ==")
    r = _thu_lai_503("/api/v1/messages", tok, {
        "model": "ltt-3.8", "max_tokens": 300, "stream": True,
        "tools": TOOLS, "messages": hoi})
    if r.get("ma") != 200:
        print(f"  KHONG DO DUOC: {r.get('ma')} {r.get('than', '')[:150]}")
        return 2
    ten, tid, tham = _gom_tool(r["dong"])
    print(f"  {r['giay']}s, {len(r['dong'])} dong, {len(set(r['loai']))} loai su kien")
    print(f"  tool: ten={ten!r} id={tid!r} tham={tham!r}")
    ket.append(("b24-01 luong SSE dung dinh dang",
                "event-stream" in r.get("ct", ""), r.get("ct", "")))
    ket.append(("b24-01 phat dung ten tool", ten == "tra_ton_kho", f"ten={ten!r}"))
    ket.append(("b24-01 tham so la JSON hop le va co ma_hang",
                "ABC-123" in tham, f"tham={tham[:60]!r}"))

    print("\n== b24-02: VONG KHEP KIN -- gui tool_result, doi so 42 trong tra loi ==")
    if not tid:
        print("  BO QUA: khong lay duoc tool_use id")
        ket.append(("b24-02 vong khep kin", False, "khong co tool id"))
    else:
        tiep = hoi + [
            {"role": "assistant", "content": [
                {"type": "tool_use", "id": tid, "name": ten,
                 "input": {"ma_hang": "ABC-123"}}]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": tid,
                 "content": json.dumps({"ma_hang": "ABC-123", "ton": TON_KHO})}]}]
        r2 = _thu_lai_503("/api/v1/messages", tok, {
            "model": "ltt-3.8", "max_tokens": 300, "stream": True,
            "tools": TOOLS, "messages": tiep})
        if r2.get("ma") != 200:
            print(f"  KHONG DO DUOC: {r2.get('ma')} {r2.get('than', '')[:150]}")
            ket.append(("b24-02 vong khep kin", False, f"HTTP {r2.get('ma')}"))
        else:
            van = "".join(
                json.loads(s[6:]).get("delta", {}).get("text", "")
                for s in r2["dong"] if s.startswith("data: ") and s[6:] != "[DONE]"
                for _ in (0,) if _kha_json(s[6:]))
            print(f"  {r2['giay']}s -- tra loi: {van[:150]!r}")
            ket.append((f"b24-02 tra loi CHUA so {TON_KHO} tu tool_result",
                        str(TON_KHO) in van, f"van={van[:60]!r}"))

    print("\n" + "=" * 62)
    dat = sum(1 for _, ok, _ in ket if ok)
    for ten_b, ok, vi in ket:
        print(f"  {'DAT ' if ok else 'TRUOT'} {ten_b:<46} {vi}")
    print(f"\n  {dat}/{len(ket)}")
    return 0 if dat == len(ket) else 1


def _kha_json(s: str) -> bool:
    try:
        json.loads(s)
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    sys.exit(main())
