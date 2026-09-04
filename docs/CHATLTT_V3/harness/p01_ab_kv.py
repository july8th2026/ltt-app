"""
p01_ab_kv.py — A/B `q8_0` vs `q4_0` cho tool-calling. Bốn bước, chạy RỜI từng bước.

    python p01_ab_kv.py sao-luu     # 1. chep yaml that ra tep .bak tren may B
    python p01_ab_kv.py dat         # 2. them HAI ho so tam + restart llama-swap
    python p01_ab_kv.py do          # 3. chay ma tran tren ca hai ho so
    python p01_ab_kv.py go          # 4. tra yaml ve nguyen trang + restart

⛔ **RỜI từng bước, không gộp thành một lệnh.** Bước 2 và 4 sửa cấu hình của một
   dịch vụ đang chạy trên máy khác và khởi động lại nó. Gộp chúng vào một script
   tự động nghĩa là một lỗi ở bước 3 sẽ để lại máy B ở trạng thái nửa vời — với
   hai hồ sơ tạm còn nguyên trong yaml và không ai nhớ để gỡ.

⭐ `sao-luu` chạy TRƯỚC và ghi ra `llama-swap.yaml.h44bak` **trên chính máy B**.
   Bản sao ở máy A không đủ: nếu phiên này chết giữa chừng, người khôi phục là
   người ngồi ở máy B, và họ cần tệp nằm ngay cạnh tệp thật.

## Vì sao hồ sơ tạm là `-c 65536` chứ không phải 200K

`q8_0` ở `-c 204800` **không nạp nổi** card 24 GB — đó chính là lý do D-0 chọn
`q4_0`, và là lý do không có cách nào A/B ở đúng cấu hình production. Nên phép
đo này so hai KV ở **cùng một cửa sổ nhỏ hơn**: nó trả lời *"q4_0 có kém hơn
q8_0 không, khi mọi thứ khác như nhau"*, chứ không trả lời *"production có bị
suy giảm không"*. Hai câu khác nhau, và tôi không được lẫn chúng.

## Vì sao vẫn đáng đo dù không đổi được production

Chủ dự án đã chốt giữ 200K (04/09) ⇒ `q4_0` bị khoá. Con số này vì thế **không
phải để chọn**, mà để **biết cái giá đang trả** — và để tiền sửa dồn đúng chỗ
nếu chất lượng tool-calling có vấn đề ở đâu đó về sau.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import nexus_may_b as N                                          # noqa: E402

YAML = "H:/LTT_LLM/gateway/llama-swap.yaml"
BAK = "H:/LTT_LLM/gateway/llama-swap.yaml.h44bak"
DICH_VU = "LTTLlamaSwap"

#: Hai hồ sơ tạm. `-c 65536` cho cả hai — biến duy nhất được đổi là KV.
HO_SO_TAM = """
  # ==== H44 P01 — HAI HO SO TAM, GO SAU KHI DO XONG ====================
  # Chi khac nhau MOT dong: cache-type. Moi thu con lai giong het nhau, vi
  # mot phep A/B doi hai bien cung luc thi khong tra loi duoc bien nao gay ra.
  qwen38-tooltest-q8:
    name: "H44 tooltest KV q8_0"
    description: "TAM THOI - do A/B tool-calling. Go sau khi xong."
    capabilities:
      in: ["text"]
      out: ["text"]
    cmd: |
      ${BIN}/llama-server.exe
      -m ${GGUF}
      ${CHUNG}
      -c 65536
      --cache-type-k q8_0 --cache-type-v q8_0
      --host 127.0.0.1 --port ${PORT}
    proxy: "http://127.0.0.1:${PORT}"
    ttl: 900
    unloadTimeout: 30

  qwen38-tooltest-q4:
    name: "H44 tooltest KV q4_0"
    description: "TAM THOI - do A/B tool-calling. Go sau khi xong."
    capabilities:
      in: ["text"]
      out: ["text"]
    cmd: |
      ${BIN}/llama-server.exe
      -m ${GGUF}
      ${CHUNG}
      -c 65536
      --cache-type-k q4_0 --cache-type-v q4_0
      --host 127.0.0.1 --port ${PORT}
    proxy: "http://127.0.0.1:${PORT}"
    ttl: 900
    unloadTimeout: 30
  # ==== het phan tam cua H44 ==========================================
"""
MOC = "models:\n"


def _doc(duong: str) -> str | None:
    ma, tra = N.goi(f"files/read?path={duong}", timeout=60)
    if ma != 200:
        return None
    d = (json.loads(tra).get("data") or {})
    if d.get("truncated"):
        print("!! files/read CAT BOT — khong dung ban nay.", file=sys.stderr)
        return None
    return d.get("content")


def _ghi(duong: str, noi: str, ly_do: str) -> bool:
    ma, _ = N.goi("files/write", {"path": duong, "content": noi, "reason": ly_do},
                  method="POST", timeout=120)
    return ma in (200, 201)


def _chay(lenh: str, ly_do: str, timeout: float = 120):
    ma, tra = N.goi("exec", {"command": lenh, "args": [], "cwd": "C:/Users",
                             "reason": ly_do}, method="POST", timeout=timeout + 30)
    if ma not in (200, 201):
        return None
    return (json.loads(tra).get("data") or {})


def lenh_sao_luu(_a) -> int:
    noi = _doc(YAML)
    if noi is None:
        print("Khong doc duoc yaml.", file=sys.stderr); return 1
    if _doc(BAK) is not None:
        print(f"Da co ban sao luu {BAK} — GIU NGUYEN, khong ghi de.")
        return 0
    if not _ghi(BAK, noi, "H44 P01: sao luu yaml truoc khi them ho so tam"):
        print("Ghi sao luu that bai.", file=sys.stderr); return 1
    print(f"Da sao luu -> {BAK} ({len(noi)} ky tu)")
    return 0


def lenh_dat(_a) -> int:
    if _doc(BAK) is None:
        print("CHUA sao luu. Chay `sao-luu` truoc.", file=sys.stderr); return 1
    noi = _doc(YAML)
    if noi is None:
        return 1
    if "qwen38-tooltest-q8" in noi:
        print("Ho so tam DA co san.")
    else:
        if MOC not in noi:
            print(f"Khong tim thay moc {MOC!r}.", file=sys.stderr); return 1
        noi = noi.replace(MOC, MOC + HO_SO_TAM, 1)
        if not _ghi(YAML, noi, "H44 P01: them hai ho so tam de A/B KV"):
            return 1
        print("Da them hai ho so tam.")
    d = _chay(f"Restart-Service {DICH_VU} -Force; Start-Sleep 3; "
              f"(Get-Service {DICH_VU}).Status",
              "H44 P01: khoi dong lai llama-swap de nap ho so tam", timeout=180)
    print("Trang thai dich vu:", (d or {}).get("stdout", "").strip() or "(khong ro)")
    return 0


def lenh_go(_a) -> int:
    bak = _doc(BAK)
    if bak is None:
        print("KHONG CO ban sao luu — khong tu doan. Khoi phuc tay.", file=sys.stderr)
        return 1
    if not _ghi(YAML, bak, "H44 P01: tra yaml ve nguyen trang sau khi do xong"):
        return 1
    d = _chay(f"Restart-Service {DICH_VU} -Force; Start-Sleep 3; "
              f"(Get-Service {DICH_VU}).Status",
              "H44 P01: khoi dong lai llama-swap sau khi go ho so tam", timeout=180)
    print("Da tra yaml ve nguyen trang. Dich vu:",
          (d or {}).get("stdout", "").strip() or "(khong ro)")
    lai = _doc(YAML)
    print("Con sot ho so tam?", "CON — KIEM TAY" if lai and "tooltest" in lai else "khong")
    return 0


def lenh_do(a) -> int:
    """Chạy ma trận trên cả hai hồ sơ tạm, xen kẽ để loại nhiễu theo thời gian."""
    import p01_lo_chinh as L
    import p01_kich_ban as KB
    ds = KB.dung(a.lap)
    if a.nhom:
        ds = [k for k in ds if k["nhom"].startswith(a.nhom)]
    ra = pathlib.Path(a.out); ra.parent.mkdir(parents=True, exist_ok=True)
    ket: dict = {"q8": [], "q4": []}
    for i, k in enumerate(ds, 1):
        for nhan, model in (("q8", "qwen38-tooltest-q8"), ("q4", "qwen38-tooltest-q4")):
            than = {"model": model, "messages": k["messages"], "tools": k["tools"],
                    "max_tokens": 768}
            if k["song_song"]:
                than["parallel_tool_calls"] = True
            goi_tra, loi = L.goi(than, timeout=a.timeout)
            if loi:
                ket[nhan].append({"ma": k["ma"], "nhom": k["nhom"], "loi": loi})
            else:
                r = L._rut(goi_tra)
                ket[nhan].append({"ma": k["ma"], "nhom": k["nhom"],
                                  "ky_vong": k["ky_vong"], "cham": L.cham(k, r)})
        if i % 10 == 0 or i == len(ds):
            ra.write_text(json.dumps(ket, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
            print(f"  [{i}/{len(ds)}] {k['nhom']}")
    tt = {n: L.tong_hop(v) for n, v in ket.items()}
    ra.write_text(json.dumps({"tong_hop": tt, "ket_qua": ket}, ensure_ascii=False,
                             indent=2) + "\n", encoding="utf-8")
    print(f"\n{'chi so':<16}{'q8_0':>10}{'q4_0':>10}{'chenh':>9}")
    print("-" * 45)
    for t in tt["q8"]:
        if tt["q8"][t].get("tong"):
            x, y = tt["q8"][t]["ty_le"]*100, tt["q4"][t]["ty_le"]*100
            print(f"{t:<16}{x:9.1f}%{y:9.1f}%{y-x:+8.1f}")
    print(f"\nGhi: {ra}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="b", required=True)
    sub.add_parser("sao-luu").set_defaults(f=lenh_sao_luu)
    sub.add_parser("dat").set_defaults(f=lenh_dat)
    sub.add_parser("go").set_defaults(f=lenh_go)
    d = sub.add_parser("do")
    goc = pathlib.Path(__file__).parent.parent
    d.add_argument("--out", default=str(goc / "artifacts" / "01_ab_kv.json"))
    d.add_argument("--lap", type=int, default=2)
    d.add_argument("--nhom", default="")
    d.add_argument("--timeout", type=float, default=180.0)
    d.set_defaults(f=lenh_do)
    a = p.parse_args()
    return a.f(a)


if __name__ == "__main__":
    raise SystemExit(main())
