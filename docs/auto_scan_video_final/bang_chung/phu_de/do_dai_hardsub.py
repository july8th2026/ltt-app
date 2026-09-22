"""Do dai phu de cung (hardsub) tren 4 clip that. Chi DOC video, ghi JSON bang chung.

Phep do (loai A — hinh hoc tren diem anh, khong phai diem so):
  diem anh "chu co vien" = luma >= 200 VA co diem anh luma <= 60 trong cua so 5x5.
  Hardsub la chu trang vien den; nen canh (troi, ao trang) sang nhung KHONG co vien toi sat ben.
  Dai = cac hang ma ti le diem "chu co vien" (trung binh 60 khung) >= 25% cua dinh.
"""
import json, subprocess, sys
from pathlib import Path
import numpy as np

src = Path(r"C:\Users\Thang Tuong\Desktop\TEST VIDEO")
W = 512
N = 60
ket = []
for vid in sorted(src.glob("*.mp4")):
    p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height:format=duration", "-of", "json", str(vid)],
                       capture_output=True, text=True, check=True)
    j = json.loads(p.stdout)
    w0, h0 = j["streams"][0]["width"], j["streams"][0]["height"]
    dur = float(j["format"]["duration"])
    H = int(round(h0 * W / w0 / 2) * 2)
    fps = N / dur
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(vid), "-vf",
                          f"fps={fps:.6f},scale={W}:{H},format=gray", "-frames:v", str(N),
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    f = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.int16)
    sang = f >= 200
    toi = f <= 60
    # toi trong cua so 5x5 (gian no)
    from numpy.lib.stride_tricks import sliding_window_view
    pad = np.pad(toi, ((0, 0), (2, 2), (2, 2)))
    gan_toi = sliding_window_view(pad, (5, 5), axis=(1, 2)).any(axis=(-1, -2))
    chu = sang & gan_toi
    # chi xet 20%..80% chieu ngang (phu de canh giua; logo goc bi loai)
    hang = chu[:, :, int(W * .2):int(W * .8)].mean(axis=(0, 2))
    dinh = hang.max()
    y_dinh = int(hang.argmax())
    nguong = dinh * 0.25
    y0 = y_dinh
    while y0 > 0 and hang[y0 - 1] >= nguong:
        y0 -= 1
    y1 = y_dinh
    while y1 < H - 1 and hang[y1 + 1] >= nguong:
        y1 += 1
    nen = float(np.median(hang))
    ket.append({"tep": vid.name[:24], "rong": w0, "cao": h0, "giay": round(dur, 1),
                "so_khung": int(f.shape[0]),
                "dai_y0": round(y0 / H, 3), "dai_y1": round((y1 + 1) / H, 3),
                "dinh_ti_le": round(float(dinh), 4), "trung_vi_ti_le": round(nen, 4),
                "dinh_tren_nen": round(float(dinh) / max(nen, 1e-4), 1)})
    print(json.dumps(ket[-1], ensure_ascii=False))
out = Path(sys.argv[1])
out.write_text(json.dumps({"phep_do": __doc__.strip(), "ket_qua": ket}, ensure_ascii=False, indent=1),
               encoding="utf-8")
