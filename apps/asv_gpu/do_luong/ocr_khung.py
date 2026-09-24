"""Runner OCR khung hinh — chay TRONG venv do luong (`venv.chay`).

    python ocr_khung.py vao.json ra.json

Vao: `{"video", "fps", "bat", "ket", "cat": [x, y, w, h] | null, "dem": px,
       "cuda": bool}`
Ra : `{"rong", "cao", "khung": [{"t", "dong": [{"hop", "chu", "diem"}]}],
       "engine", "ms_moi_khung", "so_khung"}`

Engine: RapidOCR 3.9.2 (Apache-2.0) + PP-OCRv6 small det/rec ONNX (Apache-2.0,
`python/MODEL_LICENSES.md` cua RapidOCR — da doc nguon 22/09). Model GHIM theo
SHA-256 duoi day, nam o `$HF_HOME/rapidocr/3.9.2/`; thieu thi tai DUNG URL ghim
roi kiem lai — sai checksum la loi, khong chay.

⛔ Khong import gi cua nen tang: venv do luong chi co goi cua bo do.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

PHIEN_BAN_RAPIDOCR = "3.9.2"
_GOC = f"https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/v{PHIEN_BAN_RAPIDOCR}/onnx"
#: ten -> (url, sha256). Nguon: `rapidocr/default_models.yaml` + MODEL_LICENSES.md §6.
MODEL = {
    "PP-OCRv6_det_small.onnx": (
        f"{_GOC}/PP-OCRv6/det/PP-OCRv6_det_small.onnx",
        "090f04abcd9d9a7498bc4ebf677e4cb9bdce1fe4197ddb7e529f1ef44e1ff94f"),
    "PP-OCRv6_rec_small.onnx": (
        f"{_GOC}/PP-OCRv6/rec/PP-OCRv6_rec_small.onnx",
        "6f327246b50388f3c176ae304bd95767ea6dc0c9ae92153ef8cbe210b3c14884"),
}
#: Luong CPU cho onnxruntime (xem L_OCR.md: 4 luong du cho 1 khung dai < 60 ms).
SO_LUONG = int(os.environ.get("LTT_OCR_LUONG") or 4)
ENGINE = f"rapidocr/{PHIEN_BAN_RAPIDOCR}+PP-OCRv6_small"


def thu_muc_model() -> Path:
    goc = os.environ.get("HF_HOME") or r"C:\LTTPlatform\hf-cache"
    return Path(goc) / "rapidocr" / PHIEN_BAN_RAPIDOCR


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for khoi in iter(lambda: f.read(1 << 20), b""):
            h.update(khoi)
    return h.hexdigest()


def bao_dam_model() -> dict[str, Path]:
    tm = thu_muc_model()
    tm.mkdir(parents=True, exist_ok=True)
    ra = {}
    for ten, (url, sha) in MODEL.items():
        p = tm / ten
        if not p.is_file():
            tam = p.with_suffix(".tai")
            urllib.request.urlretrieve(url, tam)
            tam.replace(p)
        if _sha(p) != sha:
            raise SystemExit(f"KHONG_KHA_DUNG: sai checksum {p}")
        ra[ten] = p
    return ra


def tao_engine(cuda: bool = False, *, dai: bool = False):
    try:
        from rapidocr import RapidOCR
    except ImportError as exc:                       # venv chua cai
        raise SystemExit(f"KHONG_KHA_DUNG: {exc}")
    m = bao_dam_model()
    return RapidOCR(params={
        "Global.log_level": "error",
        "Global.use_cls": False,          # phu de nam ngang; cls chi ton thoi gian
        "Det.model_path": str(m["PP-OCRv6_det_small.onnx"]),
        "Rec.model_path": str(m["PP-OCRv6_rec_small.onnx"]),
        "EngineConfig.onnxruntime.use_cuda": bool(cuda),
        # ⛔ Mac dinh -1 = MOI loi. May A la production: tran luong ghim.
        "EngineConfig.onnxruntime.intra_op_num_threads": SO_LUONG,
        "EngineConfig.onnxruntime.inter_op_num_threads": 1,
        # Dai phu de cat san (vd 864x96): mac dinh `limit_type: min` phong canh
        # NGAN len 736 px — tuc phong dai 8 lan. Voi dai, giu canh DAI <= 1280.
        **({"Det.limit_type": "max", "Det.limit_side_len": 1280} if dai else {}),
    })


def kich_thuoc(video: str) -> tuple[int, int]:
    """(rong, cao) cua khung ffmpeg GIAI MA ra — da tinh xoay (video dien thoai
    mang the xoay 90/270: ffmpeg tu xoay, nen rong/cao doi cho)."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height:stream_tags=rotate:stream_side_data=rotation",
         "-of", "json", video],
        capture_output=True, text=True, check=True)
    s = (json.loads(r.stdout).get("streams") or [{}])[0]
    w, h = int(s["width"]), int(s["height"])
    xoay = str((s.get("tags") or {}).get("rotate") or "")
    for sd in s.get("side_data_list") or ():
        if "rotation" in sd:
            xoay = str(sd["rotation"])
    if xoay.lstrip("-") in ("90", "270"):
        w, h = h, w
    return w, h


def doc_khung(video: str, *, fps: float, bat: float = 0.0, ket=None, cat=None):
    """Sinh (t, anh BGR numpy) theo `fps` bang ffmpeg, cat san neu co."""
    import numpy as np

    w, h = kich_thuoc(video)
    loc = [f"fps={fps}"]
    if cat:
        # 🔴 Kich thuoc CHAN. Khung yuv420p cat so le thi ffmpeg lam tron, va
        #    doc `w*h*3` byte/khung se TRUOT mot hang moi khung — chu "troi" len
        #    va lap lai (do that o v2, dai cao 115 px: CER 2% -> vo dong).
        x, y, cw, ch = (int(v) for v in cat)
        x, y = x - x % 2, y - y % 2
        cw, ch = min(cw - cw % 2, w - x), min(ch + ch % 2, h - y)
        cw, ch = cw - cw % 2, ch - ch % 2
        loc.append(f"crop={cw}:{ch}:{x}:{y}")
        w, h = cw, ch
    lenh = ["ffmpeg", "-v", "error", "-nostdin"]
    if bat:
        lenh += ["-ss", str(bat)]
    lenh += ["-i", video]
    if ket is not None:
        lenh += ["-t", str(float(ket) - float(bat or 0))]
    lenh += ["-an", "-vf", ",".join(loc), "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    p = subprocess.Popen(lenh, stdout=subprocess.PIPE)
    co = w * h * 3
    i = 0
    try:
        while True:
            buf = p.stdout.read(co)
            if len(buf) < co:
                break
            yield float(bat or 0) + i / float(fps), np.frombuffer(buf, np.uint8).reshape(h, w, 3)
            i += 1
    finally:
        p.stdout.close()
        p.wait()


def ocr_video(eng, video: str, *, fps: float, bat=0.0, ket=None, cat=None,
              dem: int = 0) -> dict:
    """`dem` = so px VIEN DEN them tren/duoi dai truoc khi det.

    🔑 Do tren v1 (dai sat day khung): det PP-OCRv6 bo sot chu `一` dung dau
       dong (`一份售价…` -> `份售价…`) khi dai cat sat chu; vien den >= 96 px
       tra lai du. Xem L_OCR.md §3.
    """
    goc_w, goc_h = kich_thuoc(video)
    dx, dy = (int(cat[0]) - int(cat[0]) % 2, int(cat[1]) - int(cat[1]) % 2) if cat else (0, 0)
    dem = int(dem or 0) if cat else 0
    if dem:
        import cv2
    khung, t0 = [], time.perf_counter()
    for t, anh in doc_khung(video, fps=fps, bat=bat, ket=ket, cat=cat):
        if dem:
            anh = cv2.copyMakeBorder(anh, dem, dem, 0, 0, cv2.BORDER_CONSTANT, value=(0, 0, 0))
        r = eng(anh)
        dong = []
        for hop, chu, diem in zip(r.boxes if r.boxes is not None else [],
                                  r.txts or [], r.scores or [], strict=False):
            xs = [float(p[0]) for p in hop]
            ys = [float(p[1]) for p in hop]
            dong.append({"hop": [min(xs) + dx, min(ys) + dy - dem, max(xs) + dx,
                                 max(ys) + dy - dem],
                         "chu": chu, "diem": round(float(diem), 4)})
        khung.append({"t": round(t, 3), "dong": dong})
    dt = time.perf_counter() - t0
    return {"rong": goc_w, "cao": goc_h, "khung": khung, "engine": ENGINE,
            "so_khung": len(khung),
            "ms_moi_khung": round(1000 * dt / max(1, len(khung)), 1)}


def main(vao: str, ra: str) -> None:
    dv = json.loads(Path(vao).read_text(encoding="utf-8"))
    eng = tao_engine(bool(dv.get("cuda")), dai=bool(dv.get("cat")))
    kq = ocr_video(eng, dv["video"], fps=float(dv["fps"]), bat=float(dv.get("bat") or 0),
                   ket=dv.get("ket"), cat=dv.get("cat"), dem=int(dv.get("dem") or 0))
    Path(ra).write_text(json.dumps(kq, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
