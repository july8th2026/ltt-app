"""
p01_cong0.py — CỔNG 0 của P01: hợp đồng phục vụ có khớp định dạng tool-call không.

Đặc tả: `docs/CHATLTT_V3/01_NGUONG_VA_MA_TRAN.md` §0 (chốt TRƯỚC lượt đo đầu).

## Nó trả lời đúng một câu, và câu đó chặn 2.400 lượt gọi phía sau

    llama-server co tra `tool_calls` CO CAU TRUC khong,
    hay loi goi tool roi vao `content` nhu VAN BAN THUONG?

Hai kết cục trông **giống hệt nhau** ở phía ChatLTT (0 tool call, không lỗi,
vẫn tính tiền) nhưng sửa ở hai nơi khác hẳn. Tách được chúng là toàn bộ giá trị
của tệp này.

    LECH DINH DANG  content CO `<tool_call>` / `<function=`  -> sua CAU HINH PHUC VU
    KHONG GOI       content KHONG co dau nao                 -> sua PROMPT/SCHEMA

## Vì sao gọi thẳng llama-swap, không qua ngăn xếp LTT

Cổng này đo **hợp đồng phục vụ** (model + template + parser), không đo đường
ống LTT. Gọi thẳng thì: 0 credit, không cần phiên đăng nhập, và một kết quả xấu
chỉ có **một** cách giải thích. Đo qua ngăn xếp LTT là việc của cổng sau — và
chỉ có nghĩa khi cổng này đã xanh.

## Đường đi

    máy A → Nexus controller → máy B → PowerShell → curl.exe → 127.0.0.1:8280

Thân JSON đi bằng **base64**: nó vượt qua ba tầng trích dẫn (bash → JSON →
PowerShell) mà không mất một ký tự nào. Đã trả giá để biết: `$_` bị nuốt, mảng
`args` không tới nơi, `curl` là bí danh của `Invoke-WebRequest`.
"""
from __future__ import annotations

import argparse
import base64
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import nexus_may_b as N                                         # noqa: E402

CONG_SWAP = "http://127.0.0.1:8280/v1/chat/completions"
MODEL = "qwen38-api"

# ── Bộ tool giả. Tất định, không tác dụng phụ, 0 credit. ────────────────────
TOOL_CALC = {
    "type": "function",
    "function": {
        "name": "calculator",
        "description": "Tinh mot bieu thuc so hoc. Dung khi can ket qua CHINH XAC.",
        "parameters": {
            "type": "object",
            "properties": {"expression": {"type": "string",
                                          "description": "Bieu thuc, vd '234*871'"}},
            "required": ["expression"]},
    },
}
TOOL_WEATHER = {
    "type": "function",
    "function": {
        "name": "weather_fake",
        "description": "Tra thoi tiet hien tai cua mot thanh pho.",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string"},
                           "unit": {"type": "string", "enum": ["c", "f"]}},
            "required": ["city"]},
    },
}
TOOLS = [TOOL_CALC, TOOL_WEATHER]

HE_THONG = ("Ban la tro ly cua LTT Studios. Khi can so lieu chinh xac hoac du "
            "lieu thoi gian thuc, HAY dung tool duoc cung cap. Khi khong can, "
            "tra loi thang.")


def _msg(*cap) -> list:
    ra = [{"role": "system", "content": HE_THONG}]
    for vai, noi in cap:
        ra.append({"role": vai, "content": noi})
    return ra


#: (ma, nhom, than_yeu_cau, ky_vong)
def dung_kich_ban() -> list:
    kb = []

    # G0-1 — mot tool ro rang. Con so CO Y xau de model khong tu tinh nham duoc.
    for i, bieu in enumerate(["8123 * 4471", "99823 / 7", "2^17 + 4519",
                              "18273 - 9481", "sqrt(1522756)"]):
        kb.append((f"G0-1.{i+1}", "G0-1",
                   {"model": MODEL, "messages": _msg(("user", f"Tinh giup toi {bieu}")),
                    "tools": TOOLS, "max_tokens": 512},
                   "co_tool"))

    # G0-2 — khong can tool. Bay duong tinh gia: cau NGHE NHU can tool.
    for i, cau in enumerate([
            "Chao ban, hom nay the nao?",
            "2 + 2 bang may?",
            "Viet mot cau tho ngan ve mua.",
            "Giai thich ngan gon HTTP 404 nghia la gi.",
            "Ban ten gi?"]):
        kb.append((f"G0-2.{i+1}", "G0-2",
                   {"model": MODEL, "messages": _msg(("user", cau)),
                    "tools": TOOLS, "max_tokens": 512},
                   "khong_tool"))

    # G0-3 — hai tool mot luot. !! parallel_tool_calls PHAI gui: llama.cpp TAT
    #        mac dinh (docs/function-calling.md:24). Khong gui la do mot thu da tat.
    for i in range(5):
        kb.append((f"G0-3.{i+1}", "G0-3",
                   {"model": MODEL,
                    "messages": _msg(("user", "Tinh 4471*8123 va cho toi biet "
                                              "thoi tiet Ha Noi.")),
                    "tools": TOOLS, "parallel_tool_calls": True, "max_tokens": 768},
                   "co_tool"))

    # G0-4 — noi tiep SAU ket qua tool. Day la thu V3 song bang.
    for i in range(5):
        kb.append((f"G0-4.{i+1}", "G0-4",
                   {"model": MODEL,
                    "messages": [
                        {"role": "system", "content": HE_THONG},
                        {"role": "user", "content": "Tinh 8123 * 4471"},
                        {"role": "assistant", "content": "",
                         "tool_calls": [{"id": "call_1", "type": "function",
                                         "function": {"name": "calculator",
                                                      "arguments": json.dumps(
                                                          {"expression": "8123 * 4471"})}}]},
                        # !! CON SO NAY CO Y SAI. 8123*4471 = 36.317.933, khong
                        #    phai 36.325.133 (lech 7.200). Ban dau la mot loi so
                        #    hoc cua toi, nhung GIU LAI vi no bien G0-4 thanh mot
                        #    doi chung: neu model lap lai 36.325.133 thi no THAT SU
                        #    doc ket qua tool. Voi so DUNG, ket qua se mo ho — model
                        #    co the tu tinh roi trung khop ngau nhien.
                        #    Do 04/09: 5/5 lap lai so cua tool.
                        {"role": "tool", "tool_call_id": "call_1",
                         "content": "36325133"}],
                    "tools": TOOLS, "max_tokens": 512},
                   "tra_loi_cuoi"))
    return kb


DAU_TOOL_TRONG_CHU = ("<tool_call>", "<function=", '"name":', "<parameter=")


def phan_loai(goi: dict) -> dict:
    """Một phản hồi → phán quyết. Đây là chỗ 🟡 và 🔴 được tách ra."""
    try:
        ch = (goi.get("choices") or [{}])[0]
        tin = ch.get("message") or {}
    except (AttributeError, IndexError, TypeError):
        return {"loai": "vo", "chi_tiet": "khong doc duoc choices"}
    tc = tin.get("tool_calls") or []
    noi = tin.get("content") or ""
    ly = ch.get("finish_reason") or ""
    if tc:
        ten = [((t.get("function") or {}).get("name") or "?") for t in tc]
        return {"loai": "tool_co_cau_truc", "so_loi_goi": len(tc), "ten": ten,
                "finish_reason": ly}
    dau = [d for d in DAU_TOOL_TRONG_CHU if d in noi]
    if dau:
        # 🟡 Model LAM DUNG; parser khong bat. Loi o hop dong phuc vu.
        return {"loai": "lech_dinh_dang", "dau_thay": dau,
                "trich": noi[:240], "finish_reason": ly}
    return {"loai": "chi_van_ban", "trich": noi[:240], "finish_reason": ly}


def goi_may_b(than: dict, *, timeout: float) -> tuple[bool, dict | str]:
    b64 = base64.b64encode(json.dumps(than, ensure_ascii=False).encode("utf-8")).decode()
    # Mot dong PowerShell. base64 vuot qua ba tang trich dan ma khong mat ky tu.
    ps = (f"$b='{b64}'; $p=Join-Path $env:TEMP 'h44_cong0.json'; "
          f"[IO.File]::WriteAllBytes($p,[Convert]::FromBase64String($b)); "
          f"curl.exe -sS --max-time {int(timeout)} "
          f"-H 'Content-Type: application/json' -d \"@$p\" {CONG_SWAP}")
    ma, tra = N.goi("exec", {"command": ps, "args": [], "cwd": "C:/Users",
                             "reason": "H44 P01 Cong 0: do khop dinh dang tool-call"},
                    method="POST", timeout=timeout + 30)
    if ma not in (200, 201):
        return False, f"nexus HTTP {ma}: {tra[:200]}"
    d = (json.loads(tra).get("data") or {})
    if d.get("exit_code") != 0:
        return False, f"curl exit {d.get('exit_code')}: {(d.get('stderr') or '')[:200]}"
    out = d.get("stdout") or ""
    try:
        return True, json.loads(out)
    except ValueError:
        return False, f"khong phai JSON: {out[:200]}"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out", default=str(pathlib.Path(__file__).parent.parent
                                        / "artifacts" / "01_cong0.json"))
    p.add_argument("--timeout", type=float, default=300.0)
    p.add_argument("--chi", default="", help="chi chay nhom nay (vd G0-1)")
    a = p.parse_args()

    kb = [k for k in dung_kich_ban() if not a.chi or k[1] == a.chi]
    print(f"Cong 0: {len(kb)} luot goi -> {CONG_SWAP}")
    print("!! Luot dau nap model (~25-75 s). Khong tinh vao do tre.\n")

    ket: list = []
    dem: dict = {}
    for i, (ma, nhom, than, ky_vong) in enumerate(kb, 1):
        t0 = time.monotonic()
        ok, tra = goi_may_b(than, timeout=a.timeout)
        giay = round(time.monotonic() - t0, 1)
        if not ok:
            pl = {"loai": "loi_goi", "chi_tiet": str(tra)[:300]}
        else:
            pl = phan_loai(tra)
        dem[pl["loai"]] = dem.get(pl["loai"], 0) + 1
        ket.append({"ma": ma, "nhom": nhom, "ky_vong": ky_vong,
                    "giay": giay, "phan_loai": pl})
        print(f"  [{i:2}/{len(kb)}] {ma:<8} {giay:6.1f}s  {pl['loai']:<18} "
              f"{pl.get('ten') or pl.get('dau_thay') or ''}")

    ra = pathlib.Path(a.out)
    ra.parent.mkdir(parents=True, exist_ok=True)
    ra.write_text(json.dumps({"cong": 0, "so_luot": len(kb), "dem": dem,
                              "ket_qua": ket}, ensure_ascii=False, indent=2) + "\n",
                  encoding="utf-8")
    print(f"\nTong: {dem}")
    print(f"Ghi: {ra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
