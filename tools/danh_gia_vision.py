"""danh_gia_vision.py — bài đánh giá cho `qwen38-vision`. (Prompt 04, nợ D-vision)

    python tools/danh_gia_vision.py --thu-thap --ra vision.json    # tren MAY B
    python tools/danh_gia_vision.py --cham vision.json             # o dau cung

## Vì sao tệp này tồn tại

`qwen38-vision` **đang bán** qua `/api/v1` và **chưa có một bài đánh giá nào**.
`tools/danh_gia_llm.py` phủ tám chiều cho model chữ; `grep vision` trong đó trả
về **rỗng**. Tức ta đang thu tiền cho một năng lực chưa từng đo.

## Nguyên tắc: ẢNH SINH BẰNG MÃ, ĐÁP ÁN LÀ SỰ THẬT CHÍNH XÁC

Không dùng ảnh sưu tầm và không chấm bằng *"nó mô tả có hay không"*. Mỗi ảnh
được vẽ bằng PIL từ một mô tả máy đọc được, nên đáp án đúng là một **sự kiện**:
có đúng 7 hình tròn, chữ là `K7QX`, ô vuông nằm bên trái.

⭐ Lý do không phải "cho gọn". Là: một phép chấm chủ quan **không thể trượt** —
   ai đọc cũng thấy câu trả lời "hợp lý", và một bộ đề không bao giờ đỏ thì
   không đo gì cả. Cả phiên 31/08–01/09 này là một chuỗi bài học về đúng điều
   đó, và §7 của `reports/06` ghi bảy lần dụng cụ tự cho ra kết quả đẹp.

## ⛔ PHẢI CÓ ĐỐI CHỨNG, VÀ NÓ PHẢI Ở ĐẦU

Bài `ctrl-01` hỏi một câu mà **không thể sai** nếu đường đi thông (ảnh đỏ toàn
phần → "màu gì?"). Nó trượt nghĩa là **bộ đo hỏng**, không phải model kém —
ảnh không tới nơi, hồ sơ vision không nạp, hay ta gọi nhầm model.

Không có bước này thì một đường ống hỏng cho ra "0/12" trông y hệt một model
tệ, và ta sẽ đi sửa model.

## ⚠️ Không đặt `temperature`/`top_k`/`top_p`

Chúng **không nằm trong hợp đồng công khai** và cache CUDA graph khoá theo
`(B, temp, top_k, top_p)` — đặt vào là đo một cấu hình khác với cấu hình khách
thật sự dùng.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MAU = {"do": (220, 30, 30), "xanh_la": (30, 170, 60), "xanh_duong": (40, 80, 210),
       "vang": (240, 200, 20), "trang": (255, 255, 255), "den": (20, 20, 20)}


def _anh_thanh_data_url(im) -> str:
    bo = io.BytesIO()
    im.save(bo, format="PNG")
    return "data:image/png;base64," + base64.b64encode(bo.getvalue()).decode()


#: Ảnh đã vẽ sẵn, nạp từ `--anh`. Xem `sinh_anh()`.
_ANH_SAN: dict[str, str] = {}


def _lay_anh(de: dict) -> str:
    """Ảnh cho một bài: lấy từ tệp đã sinh, hoặc vẽ tại chỗ nếu có PIL.

    ⭐ VÌ SAO TÁCH LÀM HAI BƯỚC. Máy B **không có `PIL`**, và cài thêm một gói
       lên máy đang phục vụ chỉ để chạy một bộ đo là một cái giá không đáng.

    ⛔ Nhưng lý do thật thì tốt hơn thế: sinh ảnh **một lần, một nơi** làm cho
       *sự thật gốc* và *thứ thực sự được gửi đi* là *cùng một vật*. Nếu mỗi máy
       tự vẽ, một khác biệt phiên bản `PIL` (kiểu chữ, khử răng cưa) sẽ làm hai
       bên chấm trên hai ảnh khác nhau mà **không ai thấy** — và điểm số vẫn ra
       một con số trông bình thường.
    """
    if de["ma"] in _ANH_SAN:
        return _ANH_SAN[de["ma"]]
    return _ve(de["anh"])


def sinh_anh(duong: Path) -> None:
    """Vẽ toàn bộ ảnh của bộ đề ra một tệp JSON (chạy ở nơi CÓ `PIL`)."""
    d = {de["ma"]: _ve(de["anh"]) for de in BO_DE}
    duong.write_text(json.dumps(d), encoding="utf-8")
    tong = sum(len(v) for v in d.values())
    print(f"da sinh {len(d)} anh -> {duong}  ({tong // 1024} KB base64)")


def _ve(mo_ta: dict) -> str:
    """Vẽ một ảnh từ mô tả máy đọc được. Đây là NƠI DUY NHẤT biết sự thật."""
    from PIL import Image, ImageDraw

    w, h = mo_ta.get("kich_thuoc", (640, 480))
    im = Image.new("RGB", (w, h), MAU[mo_ta.get("nen", "trang")])
    d = ImageDraw.Draw(im)

    if mo_ta["loai"] == "mau_phang":
        d.rectangle([0, 0, w, h], fill=MAU[mo_ta["mau"]])

    elif mo_ta["loai"] == "dem_hinh":
        # Lưới cố định: đếm được bằng mắt, và KHÔNG chồng lấn nhau.
        n, r = mo_ta["so_luong"], 34
        for i in range(n):
            cx = 70 + (i % 6) * 95
            cy = 80 + (i // 6) * 110
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=MAU[mo_ta["mau"]])

    elif mo_ta["loai"] == "chu":
        from PIL import ImageFont
        try:
            f = ImageFont.truetype("arial.ttf", mo_ta.get("co", 150))
        except OSError:
            f = ImageFont.load_default()
        d.text((w // 2, h // 2), mo_ta["chu"], fill=MAU["den"], font=f,
               anchor="mm")

    elif mo_ta["loai"] == "trai_phai":
        d.rectangle([60, 170, 260, 370], fill=MAU[mo_ta["trai"]])
        d.ellipse([380, 170, 580, 370], fill=MAU[mo_ta["phai"]])

    return _anh_thanh_data_url(im)


#: Mỗi bài: ảnh sinh từ `anh`, và `dap` là sự thật lấy từ chính mô tả đó.
BO_DE = [
    # ── ĐỐI CHỨNG. Trượt = bộ đo hỏng, KHÔNG phải model kém. Xem docstring.
    {"ma": "ctrl-01", "nhom": "doi_chung", "cham": "chua_mot_trong",
     "anh": {"loai": "mau_phang", "mau": "do"},
     "nhac": "Anh nay mau gi? Tra loi bang MOT tu tieng Viet khong dau.",
     "dap": ["do", "red"]},

    # ── đếm: sai một đơn vị là sai, không có "gần đúng"
    {"ma": "dem-07", "nhom": "dem", "cham": "so_dung",
     "anh": {"loai": "dem_hinh", "so_luong": 7, "mau": "xanh_duong"},
     "nhac": "Trong anh co bao nhieu hinh tron? Tra loi DUNG MOT CHU SO, "
             "khong giai thich.",
     "dap_so": 7},
    {"ma": "dem-12", "nhom": "dem", "cham": "so_dung",
     "anh": {"loai": "dem_hinh", "so_luong": 12, "mau": "xanh_la"},
     "nhac": "Trong anh co bao nhieu hinh tron? Tra loi DUNG MOT SO, "
             "khong giai thich.",
     "dap_so": 12},

    # ── đọc chữ: chuỗi ngẫu nhiên nên không đoán được từ ngữ cảnh
    {"ma": "chu-01", "nhom": "doc_chu", "cham": "chua_mot_trong",
     "anh": {"loai": "chu", "chu": "K7QX"},
     "nhac": "Anh co mot chuoi ky tu. Chep lai DUNG chuoi do, khong them gi.",
     "dap": ["K7QX"]},
    {"ma": "chu-02", "nhom": "doc_chu", "cham": "chua_mot_trong",
     "anh": {"loai": "chu", "chu": "48372"},
     "nhac": "Anh co mot day so. Chep lai DUNG day so do, khong them gi.",
     "dap": ["48372"]},

    # ── quan hệ không gian: chỗ model ảnh hay hỏng nhất
    {"ma": "vitri-01", "nhom": "khong_gian", "cham": "chua_mot_trong",
     "anh": {"loai": "trai_phai", "trai": "do", "phai": "xanh_duong"},
     "nhac": "Trong anh co mot hinh VUONG va mot hinh TRON. Hinh nao nam ben "
             "TRAI? Tra loi mot tu: 'vuong' hoac 'tron'.",
     "dap": ["vuong", "square"]},
    {"ma": "vitri-02", "nhom": "khong_gian", "cham": "chua_mot_trong",
     "anh": {"loai": "trai_phai", "trai": "vang", "phai": "xanh_la"},
     "nhac": "Hinh TRON trong anh mau gi? Tra loi mot tu tieng Viet khong dau.",
     "dap": ["xanh la", "xanh_la", "xanh luc", "green", "xanh"]},

    # ── từ chối bịa: ảnh KHÔNG có thứ được hỏi
    {"ma": "bia-01", "nhom": "khong_bia", "cham": "khong_chua",
     "anh": {"loai": "mau_phang", "mau": "xanh_duong"},
     "nhac": "Trong anh co con meo nao khong? Neu khong co thi noi ro la khong co.",
     "cam": ["co mot con meo", "co con meo", "mot con meo dang"]},
]


def _goi(url: str, tok: str, model: str, de: dict, timeout: float) -> dict:
    than = {"model": model, "max_tokens": 200,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": de["nhac"]},
                {"type": "image_url",
                 "image_url": {"url": _lay_anh(de)}}]}]}
    yc = urllib.request.Request(
        url.rstrip("/") + "/v1/chat/completions",
        data=json.dumps(than).encode(), method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {tok}",
                 "User-Agent": "ltt-vision/1.0"})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(yc, timeout=timeout) as r:
            d = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"loi": f"HTTP {e.code}",
                "than": e.read().decode("utf-8", "replace")[:300]}
    except Exception as e:                                      # noqa: BLE001
        return {"loi": f"{type(e).__name__}: {e}"}
    try:
        van = d["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        van = ""
    return {"van": van, "giay": round(time.monotonic() - t0, 2),
            "usage": d.get("usage")}


def _chuan(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def cham_mot(de: dict, b: dict) -> tuple[bool, str]:
    if "loi" in b:
        return False, b["loi"]
    van = _chuan(b.get("van", ""))
    if not van:
        return False, "tra ve RONG"

    if de["cham"] == "chua_mot_trong":
        for d in de["dap"]:
            if _chuan(d) in van:
                return True, ""
        return False, f"khong thay dap an nao trong {de['dap']}"

    if de["cham"] == "so_dung":
        so = re.findall(r"-?\d+", van)
        if not so:
            return False, "khong co so nao trong cau tra loi"
        # Lấy số ĐẦU TIÊN: nhắc đã yêu cầu "đúng một số", nên một câu trả lời
        # rải nhiều số là đã không theo yêu cầu.
        return (int(so[0]) == de["dap_so"],
                f"tra {so[0]}, dung la {de['dap_so']}")

    if de["cham"] == "khong_chua":
        for c in de["cam"]:
            if _chuan(c) in van:
                return False, f"da BIA: co cum '{c}'"
        return True, ""

    return False, f"khong biet cach cham '{de['cham']}'"


def thu_thap(url: str, tok: str, model: str, timeout: float,
             ra_tep: Path | None = None) -> dict:
    """Chạy cả bộ đề, GHI XUỐNG TỆP SAU MỖI BÀI.

    ⛔ Không gom rồi ghi một lần ở cuối. Lượt đầu của bộ này phải nạp model
       vision (~vài chục giây) và cả bộ có thể vượt **trần cứng 120 s** của
       Nexus — một phép đo 150 s đã bị cắt mất sạch kết quả đêm 31/08.

       Ghi từng bài thì một lần đứt vận chuyển chỉ mất **bài đang chạy**, và
       phần đã đo vẫn chấm được. Cùng bài học với lô đo ảnh ghi kết quả sau mỗi
       ảnh (`test_266`).
    """
    ra = {"model": model, "luc": time.strftime("%Y-%m-%d %H:%M:%S"), "bai": []}
    for de in BO_DE:
        b = _goi(url, tok, model, de, timeout)
        b["ma"] = de["ma"]
        ra["bai"].append(b)
        print(f"  {de['ma']:<10} {b.get('giay', '?')}s  "
              f"{(b.get('van') or b.get('loi', ''))[:70]!r}", flush=True)
        if ra_tep is not None:
            ra_tep.write_text(json.dumps(ra, ensure_ascii=False, indent=1),
                              encoding="utf-8")
    return ra


def cham(duong: Path) -> int:
    d = json.loads(duong.read_text(encoding="utf-8"))
    theo_ma = {b["ma"]: b for b in d["bai"]}

    # ĐỐI CHỨNG TRƯỚC. Xem docstring: nó trượt thì mọi con số dưới đây vô nghĩa.
    dc = [de for de in BO_DE if de["nhom"] == "doi_chung"]
    for de in dc:
        ok, vi = cham_mot(de, theo_ma.get(de["ma"], {}))
        if not ok:
            print(f"🔴 DOI CHUNG TRUOT ({de['ma']}): {vi}")
            print("   => BO DO HONG, khong phai model kem. Anh khong toi noi,")
            print("      ho so vision khong nap, hoac goi nham model.")
            print("   => KHONG doc cac con so ben duoi.")
            return 2
    print(f"  doi chung: {len(dc)}/{len(dc)} OK -- duong di thong, so lieu co nghia\n")

    nhom: dict = {}
    dat = 0
    for de in BO_DE:
        ok, vi = cham_mot(de, theo_ma.get(de["ma"], {}))
        dat += ok
        n = nhom.setdefault(de["nhom"], [0, 0])
        n[0] += ok
        n[1] += 1
        print(f"  {'DAT ' if ok else 'TRUOT'} {de['ma']:<10} {vi}")

    print()
    for ten, (a, b) in sorted(nhom.items()):
        print(f"  {ten:<14} {a}/{b}")
    print(f"\n  TONG: {dat}/{len(BO_DE)}")
    return 0 if dat == len(BO_DE) else 1


def main() -> int:
    p = argparse.ArgumentParser(description="Danh gia qwen38-vision.")
    p.add_argument("--thu-thap", action="store_true")
    p.add_argument("--sinh-anh", type=Path,
                   help="ve bo anh ra JSON (chay o noi CO pillow)")
    p.add_argument("--anh", type=Path,
                   help="nap bo anh da sinh (khong can pillow)")
    p.add_argument("--cham", type=Path)
    p.add_argument("--url", default="http://127.0.0.1:8299")
    p.add_argument("--token", default="")
    p.add_argument("--model", default="qwen38-vision")
    p.add_argument("--timeout", type=float, default=300.0)
    p.add_argument("--ra", type=Path, default=Path("vision.json"))
    a = p.parse_args()

    if a.sinh_anh:
        sinh_anh(a.sinh_anh)
        return 0
    if a.cham:
        return cham(a.cham)
    if not a.thu_thap:
        p.error("chon --thu-thap hoac --cham")

    if a.anh:
        _ANH_SAN.update(json.loads(a.anh.read_text(encoding="utf-8")))
        thieu = [d["ma"] for d in BO_DE if d["ma"] not in _ANH_SAN]
        # Thieu anh = phep do VO cho bai do, khong phai "model truot".
        if thieu:
            print(f"THIEU anh cho: {thieu} -- dung, sinh lai bo anh")
            return 2

    tok = a.token
    if not tok:
        env = Path(r"C:\ProgramData\LTTLlm\gateway.env")
        if env.exists():
            for d in env.read_text(encoding="utf-8-sig").splitlines():
                if d.startswith("LTT_LLM_TOKEN="):
                    tok = d.split("=", 1)[1].strip()
    if not tok:
        print("khong co token")
        return 1

    thu_thap(a.url, tok, a.model, a.timeout, ra_tep=a.ra)
    print(f"\nDA LUU: {a.ra}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
