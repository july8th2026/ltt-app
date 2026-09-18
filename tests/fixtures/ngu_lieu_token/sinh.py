"""sinh.py — sinh TẤT ĐỊNH ngữ liệu vi sai token (S4 §3.2, test_1416) và (tuỳ chọn) đo số token engine.

    python tests/fixtures/ngu_lieu_token/sinh.py                          # chỉ sinh mẫu
    python tests/fixtures/ngu_lieu_token/sinh.py --engine http://127.0.0.1:18280   # sinh + đo ⇒ ky_vong_engine.json

Lớp nội dung = đúng các lớp của `docs/ltt_llm_dual/artifacts/serving_v2/b4_ti_le_uoc_theo_noi_dung.json`
(những lớp làm bộ ước `chars/2.5` cũ sai: chữ Trung, emoji, số, hex, base64, JSON nén) + mẫu có cấu trúc
(60 tool, lịch sử tool_call). Số engine = MAX qua hai model (qwen38-api, qwen35-api).
"""
from __future__ import annotations

import argparse
import base64
import json
import pathlib
import random
import urllib.request

GOC = pathlib.Path(__file__).resolve().parent
KB = 8000


def _cat(s: str) -> str:
    b = s.encode("utf-8")[:KB]
    return b.decode("utf-8", "ignore")


def _lop(r: random.Random) -> dict[str, str]:
    tu = "the quick brown fox jumps over lazy dog while engineers measure latency and cache".split()
    return {
        "en_prose": " ".join(r.choice(tu) for _ in range(2000)),
        "code_py": "\n".join(f"def ham_{i}(x):\n    return x * {i} + {r.randint(0, 99)}" for i in range(400)),
        "vi_markdown": "\n".join(f"## Mục {i}\nNền tảng xử lý hàng đợi và bộ nhớ đệm cho phiên số {i}." for i in range(200)),
        "stacktrace": "\n".join(f'  File "/app/mod_{i}.py", line {r.randint(1, 900)}, in ham_{i}\n    raise ValueError("x")'
                                for i in range(150)),
        "ja_mixed": "".join(r.choice("キャッシュのトークン数を測定する日本語テキストとAPI呼び出し") for _ in range(2600)),
        "json_minified": json.dumps([{"id": i, "k": r.randint(0, 10**6), "v": [r.random()]} for i in range(300)],
                                    separators=(",", ":")),
        "base64": base64.b64encode(bytes(r.getrandbits(8) for _ in range(6000))).decode(),
        "hex": "".join(f"{r.getrandbits(128):032x}\n" for _ in range(240)),
        "numbers_csv": "\n".join(",".join(str(r.randint(0, 99999)) for _ in range(12)) for _ in range(120)),
        "cjk_zh": "".join(r.choice("缓存令牌测量中文文本系统队列延迟模型推理服务") for _ in range(2600)),
        "emoji": "".join(r.choice("😀🚀🔥✅📦🧪🧠💡🎯🐍") for _ in range(1900)),
    }


def _tool(i: int) -> dict:
    return {"name": f"mcp__srv{i % 6}__op{i}", "description": f"Operation {i} on server {i % 6}. Returns JSON.",
            "input_schema": {"type": "object", "properties": {"path": {"type": "string", "description": "file path"},
                                                                "limit": {"type": "integer"}}, "required": ["path"]}}


def mau() -> dict[str, dict]:
    r = random.Random(20260917)
    ra = {}
    for ten, van in _lop(r).items():
        ra[ten] = {"giao_thuc": "messages", "than": {"max_tokens": 16, "messages": [
            {"role": "user", "content": _cat(van) + "\n\nSummarize."}]}}
    ra["tools_60"] = {"giao_thuc": "messages", "than": {"max_tokens": 16, "tools": [_tool(i) for i in range(60)],
                                                        "messages": [{"role": "user", "content": "Pick a tool."}]}}
    lich_su = [{"role": "user", "content": "Read files."}]
    for i in range(12):
        lich_su.append({"role": "assistant", "content": None, "tool_calls": [
            {"id": f"c{i}", "type": "function", "function": {"name": "read", "arguments": json.dumps({"path": f"a{i}.py"})}}]})
        lich_su.append({"role": "tool", "tool_call_id": f"c{i}", "content": f"print({i})"})
    lich_su.append({"role": "user", "content": "Done?"})
    ra["tool_calls_history"] = {"giao_thuc": "chat", "than": {"messages": lich_su, "tools": [
        {"type": "function", "function": {"name": "read", "description": "read file",
                                          "parameters": {"type": "object", "properties": {"path": {"type": "string"}}}}}]}}
    return ra


DUONG = {"messages": "/v1/messages/count_tokens", "chat": "/v1/chat/completions/input_tokens",
         "responses": "/v1/responses/input_tokens"}


def dem_engine(base: str, model: str, giao_thuc: str, than: dict) -> int:
    req = urllib.request.Request(f"{base}/upstream/{model}{DUONG[giao_thuc]}",
                                 data=json.dumps(dict(than, model=model)).encode(),
                                 headers={"Content-Type": "application/json"})
    return int(json.loads(urllib.request.urlopen(req, timeout=120).read())["input_tokens"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine")
    a = ap.parse_args()
    ds = mau()
    for ten, m in ds.items():
        (GOC / f"{ten}.json").write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    if a.engine:
        ky = {ten: {"giao_thuc": m["giao_thuc"],
                    "engine_tokens": max(dem_engine(a.engine, md, m["giao_thuc"], m["than"])
                                         for md in ("qwen38-api", "qwen35-api"))}
              for ten, m in ds.items()}
        (GOC / "ky_vong_engine.json").write_text(json.dumps(ky, indent=1, sort_keys=True), encoding="utf-8",
                                                 newline="\n")
        print(json.dumps(ky))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
