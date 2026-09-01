"""Mọi lời gọi PIL đang dùng trong mã sống, chạy trên pillow 12 — chạy hay vỡ?

Không import mã ứng dụng (nó kéo theo cả nền tảng). Thay vào đó gọi **đúng
những API mà `grep` tìm thấy trong `apps/` và `platform_core/`**, trên ảnh thật.
"""
import io, sys, traceback
from PIL import Image
print("pillow", Image.__version__ if hasattr(Image, "__version__") else __import__("PIL").__version__)

ket = []
def thu(ten, f):
    try:
        f(); ket.append((ten, True, ""))
    except Exception as e:
        ket.append((ten, False, f"{type(e).__name__}: {e}"))

# Anh that de thu
bo = io.BytesIO()
Image.new("RGB", (120, 90), (200, 60, 60)).save(bo, format="PNG")
png = bo.getvalue()
bo2 = io.BytesIO()
Image.new("RGB", (120, 90), (60, 200, 60)).save(bo2, format="JPEG")
jpg = bo2.getvalue()

thu("Image.open(PNG)", lambda: Image.open(io.BytesIO(png)).load())
thu("Image.open(JPEG)", lambda: Image.open(io.BytesIO(jpg)).load())
thu(".convert('RGB')", lambda: Image.open(io.BytesIO(png)).convert("RGB"))
thu(".convert('RGBA')", lambda: Image.open(io.BytesIO(png)).convert("RGBA"))
thu(".convert('L')", lambda: Image.open(io.BytesIO(png)).convert("L"))
thu(".resize(...)", lambda: Image.open(io.BytesIO(png)).resize((60, 45)))
thu(".resize + Resampling.LANCZOS",
    lambda: Image.open(io.BytesIO(png)).resize((60, 45), Image.Resampling.LANCZOS))
thu("Image.Resampling.BICUBIC ton tai", lambda: Image.Resampling.BICUBIC)
thu(".thumbnail(...)", lambda: Image.open(io.BytesIO(png)).thumbnail((50, 50)))
thu(".crop(...)", lambda: Image.open(io.BytesIO(png)).crop((0, 0, 50, 50)))
thu(".paste(...)", lambda: Image.new("RGB",(200,200)).paste(Image.open(io.BytesIO(png)), (0,0)))
thu("Image.MIME (sau khi init)",
    lambda: (Image.init(), Image.MIME["PNG"], Image.MIME["JPEG"]))
thu("format + size", lambda: (Image.open(io.BytesIO(jpg)).format, Image.open(io.BytesIO(jpg)).size))
thu(".save(PNG)", lambda: Image.open(io.BytesIO(png)).save(io.BytesIO(), format="PNG"))
thu(".save(JPEG quality)", lambda: Image.open(io.BytesIO(jpg)).save(io.BytesIO(), format="JPEG", quality=88))
try:
    import numpy as np
    thu("Image.fromarray(numpy)", lambda: Image.fromarray(np.zeros((10,10,3), dtype="uint8")))
except ImportError:
    ket.append(("Image.fromarray(numpy)", None, "khong co numpy trong venv nay"))

do = sum(1 for _, ok, _ in ket if ok is False)
for ten, ok, vi in ket:
    nhan = "DAT " if ok else ("BOQUA" if ok is None else "VO  ")
    print(f"  {nhan} {ten:<34} {vi}")
print(f"\n  {sum(1 for _,ok,_ in ket if ok)}/{sum(1 for _,ok,_ in ket if ok is not None)} dat, {do} vo")
sys.exit(1 if do else 0)
