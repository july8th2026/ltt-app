r"""
voice_mock_sidecar.py — cong giong GIA LAP, tat dinh, cho tang CI.

    python tools\voice_mock_sidecar.py --cong 8131 --token mock-abc

## Vi sao co tep nay

Duong sinh tieng dau-cuoi (worker -> `features.goi_cong` -> `sidecar_client` ->
HTTP -> ffprobe -> kho -> so credit) chi chay khi CO mot cong giong tra loi o
`127.0.0.1:812x`. Cong that can GPU + model VieNeu, khong ton tai trong CI. Tep
nay tra loi DUNG hop dong HTTP ma `sidecar_client.py` mong doi, bang mot tep WAV
that (sin, doc duoc bang ffprobe) co thoi luong TAT DINH theo so ky tu — nen ca
duong ong thuc chay ma khong dung mot GPU nao.

## ⛔ DAY LA SUY DIEN GIA LAP (SIMULATED INFERENCE), KHONG PHAI TIENG THAT

Moi phan hoi tu khai minh la gia lap tren BA kenh doc lap, de mot bo test ten
"live" co the CHUNG MINH no khong dung nham cong nay:

  1. header `X-Voice-Mock: 1` tren MOI phan hoi (ke ca WAV nhi phan);
  2. khoa `"mock": true` trong moi phan hoi JSON;
  3. WAV mang mot tan so sin co dinh (`TAN_SO_HZ`) va mot chunk metadata
     `INFO/ISFT = "ltt-voice-mock"` — dau van tay nghe/doc duoc.

⇒ Cong chat luong THAT (`tools/cong_chat_luong_voice.py`) va lo chay thu THAT
   (`tools/chay_thu_ltt_voice.py`) KHONG BAO GIO duoc tro vao cong nay. Tang LIVE
   phai chay tren dich vu `LTTStudioVoice` that. Guard o `tools/check_voice_qa.py`
   cuong che ranh gioi do.

## Hop dong phuc vu (khop `apps/ltt_voice/sidecar_client.py`)

    GET  /health              -> {"ok": true, "mock": true}
    GET  /v1/capabilities     -> {"engine": "mock", "languages": ["vi","en"], ...}
    GET  /v1/voices           -> {"items": [...]}
    POST /v1/speech           -> WAV, header X-Duration-S / x-rtf
    POST /v1/speech-dai       -> WAV (ghep nhieu doan), header X-Duration-S
    POST /v1/batch            -> {"items": [{...}]}
    POST /v1/enroll           -> {"ref_b64": "...", "emb_dim": 192, ...}
    POST /v1/enroll-kho       -> nhu tren, kem `chon_doan`
    POST /v1/lo-ra-tep        -> ghi WAV THANG RA DIA tai moi `duong_ra`,
                                  tra {"items": [...], "gen_s": <tong giay>}
    POST /v1/ghep-tep         -> ghi MOT WAV gop tai `duong_ra`,
                                  tra {"duong_ra", "so_doan", "gen_s": 0.0}
    POST /v1/stream           -> WAV mot hoi (client tu doc theo khoi 8192 byte)

Thieu `Authorization: Bearer <token>` khop -> 401 (giong cong that), de duong
`san_sang()`/`song()` va phep kiem xac thuc deu co dat.

## ⚠️ `/v1/stream` KHONG mang dau ISFT trong header

`apps/ltt_voice/gia.py::doc_sample_rate` doc kenh/sample-rate/bit tai VI TRI
CO DINH (22:24 / 24:28 / 34:36) tren khoi DAU TIEN client nhan duoc — dung
`DAI_HEADER_WAV = 44`, tuc header "wave" sinh KHONG kem chunk phu. Chen chunk
`LIST/INFO` (nhu `_wav_sin` lam cho nam cua kia) o day se day fmt/data chunk
lui lai, va phep doc offset co dinh se ra rac. Nen `/v1/stream` dung
`_wav_sin_raw()` — cung mot bo sinh sin tat dinh, chi bo qua buoc dan nhan.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import math
import os
import struct
import sys
import wave

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ── tham so tat dinh cua "engine" gia lap ────────────────────────────────────

#: Toc do doc gia lap: giay tieng cho moi ky tu van ban da chuan hoa.
#:
#: ⚠️ Con so nay la MOT QUY UOC, khong phai mot phep do. No chi can TAT DINH va
#:    duong tinh, de mot bai dai hon cho ra tep dai hon va credit cao hon — dung
#:    hinh dang ma phep kiem dau-cuoi khang dinh. No KHONG dai dien cho toc do
#:    that cua VieNeu (thu do o `tham_so_cong_khai.py`, ~0,05 s/ky tu cung thang
#:    nhung day la trung hop, khong phai rang buoc).
GIAY_MOI_KY_TU = 0.05

#: San/tran thoi luong mot luot, de mot cau rong hay mot cuon sach deu ra tep
#: hop le va khong ngon dia CI.
GIAY_TOI_THIEU = 1.0
GIAY_TOI_DA = 90.0

SR = 48_000            # 48 kHz mono 16-bit — dung dinh dang cong that khai
#: Tan so sin co dinh: dau van tay nghe duoc rang day la tieng GIA LAP.
TAN_SO_HZ = 220.0
#: Nhan trong chunk INFO/ISFT cua WAV — dau van tay DOC duoc.
NHAN_ISFT = "ltt-voice-mock"

RTF_GIA = 0.15         # real-time factor gia, chi de header co gia tri hop ly.


def _giay_cho(text: str) -> float:
    n = len((text or "").strip())
    return max(GIAY_TOI_THIEU, min(GIAY_TOI_DA, n * GIAY_MOI_KY_TU))


def _wav_sin_raw(giay: float, *, seed: str = "") -> bytes:
    """WAV sin CHUA gan dau van tay ISFT — header 44-byte "wave" sinh, KHONG
    chunk phu. Dung cho `/v1/stream`, noi client doc kenh/sample-rate theo
    VI TRI CO DINH trong header (xem docstring module).
    """
    n_mau = int(SR * giay)
    # Bien do 0.2 toan thang, pha lech theo seed de hai bai khac nhau khong ra
    # byte y het (chi de deu, khong co y nghia am hoc).
    pha = (int(hashlib.sha256((seed or "").encode()).hexdigest()[:4], 16) / 65535.0) * math.tau
    khung = bytearray()
    bien = 0.2
    for i in range(n_mau):
        v = bien * math.sin(pha + math.tau * TAN_SO_HZ * (i / SR))
        khung += struct.pack("<h", int(v * 32767))

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(bytes(khung))
    return buf.getvalue()


def _wav_sin(giay: float, *, seed: str = "") -> bytes:
    """Tep WAV that (48 kHz mono 16-bit), sin `TAN_SO_HZ`, doc duoc bang ffprobe.

    Bien do nho co dinh — du de ffprobe/`decodeAudioData` thay song that, khong
    lon toi muc lam vo tai nghe cua ai lo mo no ra.
    """
    return _nhet_isft(_wav_sin_raw(giay, seed=seed))


def _nhet_isft(wav: bytes) -> bytes:
    """Chen mot chunk LIST/INFO/ISFT = NHAN_ISFT vao ngay sau header WAV.

    Day la dau van tay DOC DUOC: mot phep kiem "live" co the mo tep WAV ra va tu
    choi neu thay nhan nay. Chunk INFO la hop le trong RIFF nen ffprobe/trinh
    phat bo qua no ma khong vo.
    """
    if wav[:4] != b"RIFF" or wav[8:12] != b"WAVE":
        return wav
    isft = NHAN_ISFT.encode("ascii") + b"\x00"
    if len(isft) % 2:
        isft += b"\x00"
    info = b"INFO" + b"ISFT" + struct.pack("<I", len(isft)) + isft
    list_chunk = b"LIST" + struct.pack("<I", len(info)) + info
    than = wav[12:]
    moi = b"RIFF" + struct.pack("<I", 4 + len(list_chunk) + len(than)) + b"WAVE" + list_chunk + than
    return moi


def _ref_b64_gia(seed: str) -> str:
    """Bieu dien giong gia — 192 float32 tat dinh theo seed. Chi la byte hop le."""
    h = hashlib.sha256(("ref:" + seed).encode()).digest()
    raw = (h * 24)[:192 * 4]           # 192 * 4 = 768 byte
    return base64.b64encode(raw).decode("ascii")


GIONG_GIA = [
    {"id": "Adam", "ten": "Adam (mock)", "ngon_ngu": "vi"},
    {"id": "Sophia", "ten": "Sophia (mock)", "ngon_ngu": "vi"},
    {"id": "Michael", "ten": "Michael (mock)", "ngon_ngu": "en"},
]


class _Handler(BaseHTTPRequestHandler):
    server_version = "ltt-voice-mock/1.0"

    # ── tien ich ──────────────────────────────────────────────────────────────
    def _token_ok(self) -> bool:
        can = getattr(self.server, "token", "") or ""
        if not can:
            return True                     # khong dat token -> chap nhan het
        got = self.headers.get("Authorization", "")
        return got == f"Bearer {can}"

    def _json(self, code: int, payload: dict) -> None:
        payload = dict(payload)
        payload.setdefault("mock", True)
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Voice-Mock", "1")
        self.end_headers()
        self.wfile.write(body)

    def _wav(self, wav: bytes, giay: float) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Content-Length", str(len(wav)))
        self.send_header("X-Duration-S", f"{giay:.3f}")
        self.send_header("x-rtf", f"{RTF_GIA:.3f}")
        self.send_header("X-Voice-Mock", "1")
        self.end_headers()
        self.wfile.write(wav)

    def _body(self) -> dict:
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except (TypeError, ValueError):
            n = 0
        if n <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return {}

    def log_message(self, *a):        # im lang — nhat ky da du o tang goi
        pass

    # ── GET ────────────────────────────────────────────────────────────────────
    def do_GET(self):
        if self.path.startswith("/health"):
            return self._json(200, {"ok": True})
        if not self._token_ok():
            return self._json(401, {"error": "thieu hoac sai token"})
        if self.path.startswith("/v1/capabilities"):
            return self._json(200, {"engine": "mock", "languages": ["vi", "en"],
                                    "san_sang": True})
        if self.path.startswith("/v1/voices"):
            return self._json(200, {"items": GIONG_GIA})
        return self._json(404, {"error": "khong co cua nay"})

    # ── POST ───────────────────────────────────────────────────────────────────
    def do_POST(self):
        if not self._token_ok():
            return self._json(401, {"error": "thieu hoac sai token"})
        b = self._body()

        if self.path.startswith("/v1/speech-dai"):
            texts = list(b.get("texts") or [])
            giay = sum(_giay_cho(t) for t in texts) or GIAY_TOI_THIEU
            giay = min(GIAY_TOI_DA, giay)
            return self._wav(_wav_sin(giay, seed="|".join(texts)), giay)

        if self.path.startswith("/v1/speech"):
            text = str(b.get("text") or "")
            giay = _giay_cho(text)
            return self._wav(_wav_sin(giay, seed=text), giay)

        if self.path.startswith("/v1/batch"):
            texts = list(b.get("texts") or [])
            items = []
            for t in texts:
                giay = _giay_cho(t)
                items.append({"wav_b64": base64.b64encode(_wav_sin(giay, seed=t)).decode(),
                              "duration_s": round(giay, 3), "mock": True})
            return self._json(200, {"items": items})

        if self.path.startswith("/v1/lo-ra-tep"):
            return self._lo_ra_tep(b)

        if self.path.startswith("/v1/ghep-tep"):
            return self._ghep_tep(b)

        if self.path.startswith("/v1/stream"):
            return self._stream(b)

        if self.path.startswith("/v1/enroll"):
            # /v1/enroll va /v1/enroll-kho
            seed = str(b.get("duong_wav") or "enroll")
            out = {"ref_b64": _ref_b64_gia(seed), "emb_dim": 192}
            if self.path.startswith("/v1/enroll-kho"):
                out["chon_doan"] = {"bat_dau_s": 0.0, "ket_thuc_s": 6.0,
                                    "so_clip": int(b.get("so_clip") or 5),
                                    "diem": 0.87, "mock": True}
            else:
                out["chon_doan"] = {"bat_dau_s": 0.0, "ket_thuc_s": 6.0,
                                    "diem": 0.87, "mock": True}
            return self._json(200, out)

        return self._json(404, {"error": "khong co cua nay"})

    # ── ba cua duong VAN BAN DAI (khop `apps/ltt_voice/sidecar_client.py`) ──────

    def _lo_ra_tep(self, b: dict) -> None:
        """`lo_ra_tep()`: sinh tung doan roi GHI THANG RA DIA — khong qua HTTP.

        Client (`ban_doc_dai.py::_sinh_mot_lo`) sau do `open(duong, "rb")` tren
        TUNG duong trong `duong_ra`, nen mock phai ghi tep THAT tai dung duong
        do — tra JSON khong du. `gen_s` la khoa DUY NHAT client doc tu phan hoi
        nay (`_cong_gen_s`), nen phai cong dong that.
        """
        texts = list(b.get("texts") or [])
        duong_ra = list(b.get("duong_ra") or [])
        items = []
        tong_giay = 0.0
        for text, duong in zip(texts, duong_ra, strict=True):
            giay = _giay_cho(text)
            wav = _wav_sin(giay, seed=text)
            thu_muc = os.path.dirname(duong)
            if thu_muc:
                os.makedirs(thu_muc, exist_ok=True)
            with open(duong, "wb") as f:
                f.write(wav)
            tong_giay += giay
            items.append({"duong": duong, "duration_s": round(giay, 3), "mock": True})
        return self._json(200, {"items": items, "gen_s": round(tong_giay, 3)})

    def _ghep_tep(self, b: dict) -> None:
        """`ghep_tep()`: ghep cac doan DA CO TREN DIA thanh MOT tep tai `duong_ra`.

        Client (`ban_doc_dai.py::dung`) kiem `os.path.isfile(ra)` ngay sau loi
        goi nay, nen mock phai ghi tep THAT. Khong chay model nen `gen_s` = 0.0
        — dung ngu nghia cua cua that (`ho_so["gen_s"]` bi doi de sau boi so ke
        vong SINH, khong phai boi cua ghep).
        """
        duong_vao = list(b.get("duong_vao") or [])
        duong_ra = str(b.get("duong_ra") or "")
        tong_giay = 0.0
        for duong in duong_vao:
            try:
                with wave.open(duong, "rb") as w:
                    khung = w.getnframes()
                    sr = w.getframerate() or SR
                    tong_giay += khung / float(sr)
            except (OSError, wave.Error, EOFError):
                tong_giay += GIAY_TOI_THIEU
        giay = max(GIAY_TOI_THIEU, min(GIAY_TOI_DA, tong_giay or GIAY_TOI_THIEU))
        wav = _wav_sin(giay, seed="ghep:" + "|".join(duong_vao))
        thu_muc = os.path.dirname(duong_ra)
        if thu_muc:
            os.makedirs(thu_muc, exist_ok=True)
        with open(duong_ra, "wb") as f:
            f.write(wav)
        return self._json(200, {"duong_ra": duong_ra, "so_doan": len(duong_vao),
                                "gen_s": 0.0})

    def _stream(self, b: dict) -> None:
        """`phat_dan()`: MOT WAV gui mot hoi, client tu doc theo khoi 8192 byte.

        Khoi DAU TIEN client nhan phai la header 44-byte "sach" (khong chunk
        `LIST/INFO`) vi `gia.doc_sample_rate` doc kenh/sample-rate/bit tai VI
        TRI CO DINH — xem canh bao o dau tep. Dung `_wav_sin_raw`, khong phai
        `_wav_sin`.
        """
        text = str(b.get("text") or "")
        giay = _giay_cho(text)
        wav = _wav_sin_raw(giay, seed=text)
        self.send_response(200)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Content-Length", str(len(wav)))
        self.send_header("X-Voice-Mock", "1")
        self.end_headers()
        self.wfile.write(wav)


class _MockServer(ThreadingHTTPServer):
    """ThreadingHTTPServer mang them `token` — de mypy biet thuoc tinh nay."""
    token: str = ""


def chay(cong: int, token: str) -> int:
    srv = _MockServer(("127.0.0.1", cong), _Handler)
    srv.token = token
    print(f"[voice-mock] SIMULATED sidecar tren http://127.0.0.1:{cong} "
          f"(token {'co' if token else 'mo'}) — day la tieng GIA LAP.",
          flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Cong giong GIA LAP cho CI.")
    ap.add_argument("--cong", type=int,
                    default=int(os.environ.get("LTT_VOICE_MOCK_CONG") or 8131))
    ap.add_argument("--token",
                    default=os.environ.get("LTT_VOICE_MOCK_TOKEN") or "mock-token")
    a = ap.parse_args(argv)
    return chay(a.cong, a.token)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    raise SystemExit(main())
