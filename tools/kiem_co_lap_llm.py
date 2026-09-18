"""kiem_co_lap_llm.py — canary cô lập chéo phiên cho llama-server (llama.cpp #27148).

    python tools\\kiem_co_lap_llm.py --base http://127.0.0.1:8280 --model qwen38-api --lan 60 \\
        --kich-ban tuan_tu_khong_lien_quan,xoay_vuot_slot,dong_thoi,sentinel_tien_to_chung --ra ra.jsonl

Mã thoát: 0 = 0 rò · 3 = có rò · 2 = không đo được.
Rò ⇔ marker NGẪU NHIÊN của một phiên khác xuất hiện trong text hoặc reasoning. `cache_n` được ghi nhưng
KHÔNG là tiêu chí (dương tính giả khi cùng câu hỏi lặp — docs/ltt_llm_dual/serving_v2/02_BASELINE_2026-09-16.md §7).
Chỉ dữ liệu tổng hợp. Không đọc /slots để lấy nội dung.

`dong_thoi_lru_27148` = công thức GỐC của #27148: nạp `--n-nap` (> np) hội thoại dài khác nhau có lượt
tool_calls/tool, rồi bắn `--song-song` hội thoại mới CÙNG LÚC (nhiều slot LRU-evict một cửa sổ). Mọi lượt
được so với MỌI marker của cả lượt chạy (trừ của chính nó). Mặc định dừng ngay khi thấy rò.
"""
from __future__ import annotations

from typing import cast

import argparse
import json
import pathlib
import random
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

KICH_BAN = ("tuan_tu_khong_lien_quan", "xoay_vuot_slot", "dong_thoi", "sentinel_tien_to_chung",
            "dong_thoi_lru_27148")


class DungViRo(Exception):
    """Đã thấy rò và người gọi yêu cầu dừng ngay."""


class SoMarker:
    """Sổ marker của CẢ lượt chạy: rò từ kịch bản khác / vòng trước cũng bị bắt."""

    def __init__(self) -> None:
        self._tat_ca: set[str] = set()
        self._khoa = threading.Lock()

    def moi(self, tien_to: str) -> str:
        mk = _marker(tien_to)
        with self._khoa:
            self._tat_ca.add(mk)
        return mk

    def cua_nguoi_khac(self, cua_minh: set[str]) -> set[str]:
        with self._khoa:
            return set(self._tat_ca) - set(cua_minh)


@dataclass
class KetQua:
    ro: int = 0
    khong_do_duoc: int = 0
    tong: int = 0


def ma_thoat(kq: KetQua) -> int:
    if kq.ro:
        return 3
    if kq.tong == 0 or kq.khong_do_duoc == kq.tong:
        return 2
    return 0


def tim_ro(marker: str, van_ban: str) -> bool:
    return re.search(r"(?<![0-9A-Za-z])" + re.escape(marker) + r"(?![0-9])", van_ban or "") is not None


def _marker(tien_to: str) -> str:
    return f"{tien_to}{random.SystemRandom().randint(10**7, 10**8 - 1)}"


def _script(mk: str) -> str:
    return (f"#!/bin/bash\n# deploy helper {mk}\nSRC_{mk}=/opt/app\nfor f in $(ls $SRC_{mk}/*.conf)\n"
            f"do\n  cp $f /etc/{mk}/\ndone\nrm -rf $TARGET_{mk}/\necho done {mk}\n")


def _tai_lieu(ky_tu: int, hat: int) -> str:
    r = random.Random(hat)
    tu = ("request queue worker scheduler latency cache token prompt decode prefill slot "
          "budget fairness cancel stream credit invoice lease retry timeout backoff").split()
    dong: list[str] = []
    while sum(len(x) + 1 for x in dong) < ky_tu:
        dong.append("def ham_%d(%s):\n    return %d  # %s" % (
            r.randint(1, 10**6), r.choice(tu), r.randint(0, 999), " ".join(r.sample(tu, 6))))
    return "\n".join(dong)[:ky_tu]


_CONG_CU = [{"type": "function", "function": {
    "name": "lookup_ticket", "description": "Look up a deployment ticket by id.",
    "parameters": {"type": "object", "properties": {"ticket_id": {"type": "string"}}, "required": ["ticket_id"]}}}]


def _hoi_thoai_27148(mk: str, hat: int, ky_tu: int) -> list:
    """Công thức gốc #27148: system dài KHÁC nhau + user + assistant tool_calls + tool, marker trong tool."""
    ve = f"call_{hat % 10**8}"
    return [
        {"role": "system", "content": "You are an operations assistant. Internal reference follows.\n\n"
                                      + _tai_lieu(ky_tu, hat)},
        {"role": "user", "content": f"Look up ticket T{hat % 10**6} and tell me its secret code."},
        {"role": "assistant", "content": "", "tool_calls": [{
            "id": ve, "type": "function",
            "function": {"name": "lookup_ticket", "arguments": json.dumps({"ticket_id": f"T{hat % 10**6}"})}}]},
        {"role": "tool", "tool_call_id": ve, "content": f"Ticket found. The secret code for this ticket is {mk}."},
        {"role": "user", "content": "What is the secret code of the ticket? Reply only the code."},
    ]


def _goi(base: str, model: str, messages: list, max_tokens: int, timeout: float = 600.0,
         them: dict | None = None) -> dict:
    body = {"model": model, "messages": messages, "max_tokens": max_tokens, "stream": True,
            "reasoning_effort": "low", "cache_prompt": True, "stream_options": {"include_usage": True}}
    body.update(them or {})
    req = urllib.request.Request(base + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 method="POST", headers={"Content-Type": "application/json"})
    text: list[str] = []
    reas: list[str] = []
    finish: str | None = None
    timings: dict = {}
    status: int | None = None
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            status = r.status
            for line in r:
                line = line.strip()
                if not line.startswith(b"data:") or line[5:].strip() == b"[DONE]":
                    continue
                try:
                    d = json.loads(line[5:].strip())
                except ValueError:
                    continue
                timings = d.get("timings") or timings
                for ch in d.get("choices") or []:
                    de = ch.get("delta") or {}
                    text.append(de.get("content") or "")
                    reas.append(de.get("reasoning_content") or "")
                    finish = ch.get("finish_reason") or finish
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        return {"status": None, "loi": type(e).__name__}
    return {"status": status, "text": "".join(text), "reasoning": "".join(reas), "finish": finish,
            "timings": timings}


def _ghi(ra: pathlib.Path, khoa: threading.Lock, **kw) -> None:
    with khoa, ra.open("a", encoding="utf-8") as f:
        f.write(json.dumps(kw, ensure_ascii=False) + "\n")


def chay(base: str, model: str, lan: int, kich_ban: list[str], ra: pathlib.Path,
         doc_ky_tu: int = 18_000, n_nap: int = 4, song_song: int = 2,
         dung_khi_ro: bool = False) -> KetQua:
    """`n_nap`/`song_song` chỉ cho `dong_thoi_lru_27148`: nạp > np hội thoại rồi bắn `song_song` cùng lúc."""
    kq, khoa = KetQua(), threading.Lock()
    so = SoMarker()
    ra.parent.mkdir(parents=True, exist_ok=True)

    def _marker(tien_to: str) -> str:  # mọi marker của lượt chạy đi qua sổ toàn cục
        return so.moi(tien_to)

    def cham(kb: str, i: int, cua: dict, marker_la: list[str], cua_minh: set[str] | None = None,
             pha: str | None = None) -> None:
        # Tiêu chí = MỌI marker của lượt chạy trừ của chính phiên này (marker_la luôn là tập con).
        minh = cua_minh or set()
        khac = so.cua_nguoi_khac(minh) | (set(marker_la) - minh)
        blob = (cua.get("text") or "") + (cua.get("reasoning") or "")
        thay = sorted(m for m in khac if tim_ro(m, blob))
        with khoa:
            kq.tong += 1
            if cua.get("status") != 200:
                kq.khong_do_duoc += 1
            kq.ro += int(bool(thay))
        t = cua.get("timings") or {}
        trich = None
        if thay:
            k = blob.find(thay[0])
            trich = blob[max(0, k - 200):k + 200]
        _ghi(ra, khoa, kich_ban=kb, pha=pha, lan=i, model=model, ro=bool(thay), marker_ro=thay or None,
             marker_minh=sorted(minh) or None,
             trich_ro=trich, dung_ma=(any(tim_ro(m, cua.get("text") or "") for m in minh) if minh else None),
             status=cua.get("status"), finish_reason=cua.get("finish"),
             reasoning_ky_tu=len(cua.get("reasoning") or ""), content_ky_tu=len(cua.get("text") or ""),
             cache_n=t.get("cache_n"), prompt_n=t.get("prompt_n"), loi=cua.get("loi"), t=round(time.time(), 1))
        if thay and dung_khi_ro:
            raise DungViRo(f"{kb} vong {i}: thay {thay}")

    for i in range(lan):
        hat = random.SystemRandom().randint(0, 10**9)
        if "tuan_tu_khong_lien_quan" in kich_ban:
            mk = _marker("QX")
            _goi(base, model, [{"role": "user", "content": "Find the bugs in this bash script:\n\n" + _script(mk)}], 2000)
            b = _goi(base, model, [{"role": "user", "content": _tai_lieu(doc_ky_tu, hat)
                                    + "\n\nList the function names above that return 0."}], 4000)
            cham("tuan_tu_khong_lien_quan", i, b, [mk])
        if "xoay_vuot_slot" in kich_ban:
            mks = [_marker("QY") for _ in range(5)]
            for j, mk in enumerate(mks):
                _goi(base, model, [{"role": "user", "content": f"Session {j}. Find the bugs:\n\n" + _script(mk)}], 600)
            b = _goi(base, model, [{"role": "user", "content": _tai_lieu(doc_ky_tu, hat + 1)
                                    + "\n\nHow many functions are defined above?"}], 4000)
            cham("xoay_vuot_slot", i, b, mks)
        if "dong_thoi" in kich_ban:
            mks = [_marker("ZT") for _ in range(3)]
            ra_ = [None] * 3

            def mot(k: int, mks: list[str] = mks, ra_: list = ra_) -> None:
                ra_[k] = _goi(base, model, [{"role": "user", "content": f"Remember code {mks[k]}. Reply OK."},
                                            {"role": "assistant", "content": "OK."},
                                            {"role": "user", "content": "What is the secret code? Reply only the code."}], 1500)
            ths = [threading.Thread(target=mot, args=(k,)) for k in range(3)]
            for t in ths:
                t.start()
            for t in ths:
                t.join()
            for k in range(3):
                cham("dong_thoi", i, cast(dict, ra_[k]), [m for n, m in enumerate(mks) if n != k], {mks[k]})
        if "sentinel_tien_to_chung" in kich_ban:
            chung = [{"role": "system", "content": "You are careful. " + _tai_lieu(doc_ky_tu // 2, 777)}]
            mk = _marker("KP")
            _goi(base, model, chung + [{"role": "user", "content": f"Remember code {mk}. Reply OK."},
                                       {"role": "assistant", "content": "OK."},
                                       {"role": "user", "content": "What is the secret code? Reply only the code."}], 1500)
            b = _goi(base, model, chung + [{"role": "user", "content": "Was any secret code given earlier in THIS "
                                            "conversation? If none, reply exactly NONE."}], 1500)
            cham("sentinel_tien_to_chung", i, b, [mk])
        if "dong_thoi_lru_27148" in kich_ban:
            ky = max(200, doc_ky_tu // 2)
            them = {"tools": _CONG_CU}
            # Pha nạp: n_nap (> np) hội thoại dài KHÁC nhau, tuần tự => pool RAM + mọi slot giữ hội thoại đã xong.
            for _j in range(n_nap):
                mk = _marker("QN")
                h = random.SystemRandom().randint(0, 10**9)
                r = _goi(base, model, _hoi_thoai_27148(mk, h, ky), 800, them=them)
                cham("dong_thoi_lru_27148", i, r, [], {mk}, pha="nap")
            # Pha đồng thời: song_song hội thoại mới CÙNG LÚC => nhiều slot bị LRU-evict trong một cửa sổ.
            mks = [_marker("QD") for _ in range(song_song)]
            hats = [random.SystemRandom().randint(0, 10**9) for _ in range(song_song)]
            kq_: list = [None] * song_song
            rao = threading.Barrier(song_song)

            def mot_lru(k: int, mks: list[str] = mks, hats: list[int] = hats, kq_: list = kq_,
                        rao: threading.Barrier = rao, ky: int = ky, them: dict = them) -> None:
                rao.wait()
                kq_[k] = _goi(base, model, _hoi_thoai_27148(mks[k], hats[k], ky), 800, them=them)
            ths = [threading.Thread(target=mot_lru, args=(k,)) for k in range(song_song)]
            for t in ths:
                t.start()
            for t in ths:
                t.join()
            for k in range(song_song):
                cham("dong_thoi_lru_27148", i, kq_[k], [], {mks[k]}, pha="dong_thoi")
    return kq


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8280")
    ap.add_argument("--model", required=True)
    ap.add_argument("--lan", type=int, default=60)
    ap.add_argument("--kich-ban", default=",".join(KICH_BAN))
    ap.add_argument("--ra", required=True)
    ap.add_argument("--n-nap", type=int, default=4)
    ap.add_argument("--song-song", type=int, default=2)
    ap.add_argument("--khong-dung-khi-ro", action="store_true")
    a = ap.parse_args(argv)
    kb = [x for x in a.kich_ban.split(",") if x in KICH_BAN]
    t0 = time.time()
    try:
        kq = chay(a.base, a.model, a.lan, kb, pathlib.Path(a.ra), n_nap=a.n_nap, song_song=a.song_song,
                  dung_khi_ro=not a.khong_dung_khi_ro)
    except DungViRo as e:
        print(f"model={a.model} RO -> DUNG NGAY: {e} giay={time.time() - t0:.0f}")
        return 3
    print(f"model={a.model} tong={kq.tong} ro={kq.ro} khong_do_duoc={kq.khong_do_duoc} "
          f"giay={time.time() - t0:.0f}")
    return ma_thoat(kq)


if __name__ == "__main__":
    sys.exit(main())
