"""
chuan_hoa_anh.py — đưa hai bộ ảnh về **cùng kích thước, cùng định dạng** trước khi
dựng lô so mù.

    py tools/chuan_hoa_anh.py --vao bench/G6b_gemini --vao bench/G6b_ta \\
                             --ra bench/G6b_chuan

⭐ VÌ SAO PHẢI CÓ BƯỚC NÀY — HAI LÝ DO, VÀ LÝ DO THỨ HAI NẶNG HƠN:

 ① **Công bằng.** Đo thật 22/08: Gemini trả **1376×768 JPEG**, phía ta chạy
    **2560×1440 PNG**. Chênh 1,86 lần chiều dài, và lệch **về phía có lợi cho ta** —
    ảnh to hơn, không nén mất mát, thì trông nét hơn *bất kể model nào vẽ*. So mù
    trên hai bộ đó là đo độ phân giải, không phải đo model.

 ② ⛔ **TÍNH MÙ.** `cham_mu.ghi_lo` chép ảnh và **giữ nguyên đuôi tệp gốc**. Một bên
    toàn `.jpg`, một bên toàn `.png` thì người chấm chỉ cần nhìn tên tệp là biết
    nguồn — **và cả lô mất giá trị**. Đây không phải rủi ro lý thuyết: đó chính xác
    là hình dạng dữ liệu ta đang có.

⚠️ **THỨ BƯỚC NÀY KHÔNG CHỮA ĐƯỢC, ghi ra để không ai tưởng là đã chữa:** ảnh Gemini
   **đã đi qua JPEG một lần ở nguồn**. Hạ kích thước làm nhiễu nén mờ đi chứ không
   xoá nó. Ta không tái tạo được bản gốc chưa nén mà Gemini không hề trả ra.

   Đây là **giới hạn thật của phép so**, và nó nghiêng về phía *bất lợi cho Gemini*.
   Nếu kết quả cuối cùng sát nhau thì phải nói rõ điều đó khi kết luận.

⭐ **MỘT QUAN SÁT VỀ SẢN PHẨM, tách khỏi phép so về model:** thứ Gemini **giao cho
   khách** là 1376×768 JPEG, thứ ta giao là 2560×1440 PNG. Đó là một khác biệt sản
   phẩm **có thật và có lợi cho ta** — nhưng nó phải được nói riêng, không được lẫn
   vào câu "model nào vẽ đẹp hơn". Lô chuẩn hoá trả lời câu về **model**; khác biệt
   như-giao ghi ở bản kê để trả lời câu về **sản phẩm**.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Optional

DUOI_VAO = (".png", ".jpg", ".jpeg", ".webp")

#: Định dạng ra. PNG cho **mọi** ảnh: một đuôi duy nhất thì đuôi tệp không còn nói
#: gì về nguồn. Không nén lại sang JPEG vì làm thế là thêm một lần mất mát nữa lên
#: bộ vốn đã bị nén — và lần đó thì ta tự gây ra.
DUOI_RA = ".png"


class LoiChuanHoa(Exception):
    pass


def anh_trong(thu_muc: pathlib.Path) -> list[pathlib.Path]:
    return sorted(p for p in thu_muc.iterdir()
                  if p.is_file() and p.suffix.lower() in DUOI_VAO)


def khung_chung(kich_co: list[tuple[int, int]]) -> tuple[int, int]:
    """Một khung **duy nhất** (rộng, cao) mà mọi ảnh sẽ được đưa về.

    ⛔ VÌ SAO KHÔNG CHỈ KHỚP CẠNH DÀI — đo thật 22/08: Gemini khai "16:9" nhưng trả
    **1376×768**, tỉ lệ **1,7917**; phía ta chạy **2560×1440**, tỉ lệ **1,7778**.
    Khớp riêng cạnh dài cho ra 1376×768 và 1376×774 — lệch **6 pixel chiều cao**,
    và lệch **y hệt nhau trên mọi cặp**. Một khác biệt nhỏ nhưng **hệ thống** thì
    người chấm nhận ra sau vài cặp, và từ đó họ biết bên nào là bên nào.

    Đó đúng là loại dấu vết vừa bịt ở đuôi tệp — bịt một chỗ mà bỏ chỗ kia thì tính
    mù vẫn vỡ.

    Cách làm: lấy **tỉ lệ hẹp nhất** làm đích, cắt giữa những ảnh rộng hơn cho khớp,
    rồi hạ tất cả về cùng cạnh dài. Chọn tỉ lệ hẹp nhất vì như vậy **không bao giờ
    phải chèn viền** — chèn viền là thêm một dấu vết mới thay cho dấu vết cũ.
    """
    if not kich_co:
        raise LoiChuanHoa("khong co anh nao de do")
    ti_le = min(max(r, c) / min(r, c) for r, c in kich_co)

    # ⛔ Cạnh dài phải đo **SAU** khi cắt, không phải trước. Bản đầu đo trước và ra
    #    1376×774: ảnh Gemini bị cắt còn 1365 rồi **phóng lên** 1376 — đúng cái tôi
    #    vừa viết là không bao giờ được làm, ở ngay hàm bên cạnh. Phóng 0,8 % làm
    #    ảnh mềm đi một chút, và nó chỉ xảy ra với MỘT bên ⇒ thiên lệch.
    dai = min(min(max(r, c), min(r, c) * ti_le) for r, c in kich_co)
    dai = max(1, int(dai))                    # `int` = luôn đi xuống, khong lam tron len
    ngan = max(1, round(dai / ti_le))
    return dai, ngan


def canh_dai_chung(kich_co: list[tuple[int, int]]) -> int:
    """Cạnh dài chung = **nhỏ nhất** trong các cạnh dài.

    Luôn đi xuống, không bao giờ phóng to. Phóng ảnh nhỏ lên cho bằng ảnh to là
    **bịa ra chi tiết chưa từng có**, và người chấm sẽ chấm cái mờ do nội suy chứ
    không chấm model.
    """
    if not kich_co:
        raise LoiChuanHoa("khong co anh nao de do")
    return min(max(r, c) for r, c in kich_co)


def _cat_giua(im, ti_le: float):
    """Cắt GIỮA cho khớp tỉ lệ đích. Không chèn viền, không xoay.

    Cắt giữa chứ không cắt mép: chủ thể của một tấm ảnh gần như luôn ở giữa, nên cắt
    lệch là bỏ đi đúng thứ đang được chấm.
    """
    hien = im.width / im.height
    if abs(hien - ti_le) < 1e-9:
        return im
    if hien > ti_le:                      # qua rong -> cat bot chieu ngang
        w = max(1, round(im.height * ti_le))
        x = (im.width - w) // 2
        return im.crop((x, 0, x + w, im.height))
    h = max(1, round(im.width / ti_le))   # qua cao -> cat bot chieu doc
    y = (im.height - h) // 2
    return im.crop((0, y, im.width, y + h))


def _doc(p: pathlib.Path):
    from PIL import Image
    try:
        im = Image.open(p)
        im.load()
        return im
    except Exception as e:                       # noqa: BLE001
        raise LoiChuanHoa(f"{p.name}: khong doc duoc anh ({e})") from e


def chuan_hoa(vao: list[pathlib.Path], ra: pathlib.Path,
              canh_dai: Optional[int] = None) -> dict:
    """Hạ mọi ảnh về cùng cạnh dài và ghi ra PNG. Trả bản kê."""
    from PIL import Image

    if len(vao) < 2:
        raise LoiChuanHoa("can it nhat hai thu muc de so")

    bo: dict[str, list[pathlib.Path]] = {}
    for d in vao:
        if not d.is_dir():
            raise LoiChuanHoa(f"khong phai thu muc: {d}")
        ds = anh_trong(d)
        if not ds:
            raise LoiChuanHoa(f"{d.name}: khong co anh nao")
        bo[d.name] = ds

    # Đo trước, đổi sau: phải biết cạnh dài chung của TOÀN BỘ rồi mới hạ.
    truoc: dict[str, list[dict]] = {}
    moi_kich_co: list[tuple[int, int]] = []
    for ten, ds in bo.items():
        truoc[ten] = []
        for p in ds:
            im = _doc(p)
            truoc[ten].append({"tep": p.name, "rong": im.width, "cao": im.height,
                               "dinh_dang": (im.format or "?").lower()})
            moi_kich_co.append((im.width, im.height))
            im.close()

    dai, ngan = khung_chung(moi_kich_co)
    if canh_dai:
        ngan = max(1, round(ngan * int(canh_dai) / dai))
        dai = int(canh_dai)
    if dai <= 0:
        raise LoiChuanHoa("canh dai phai duong")

    ra.mkdir(parents=True, exist_ok=True)
    sau: dict[str, list[dict]] = {}
    for ten, ds in bo.items():
        thu_muc = ra / ten
        thu_muc.mkdir(exist_ok=True)
        sau[ten] = []
        for p in ds:
            im = _doc(p).convert("RGB")
            # Ảnh dọc thì khung đích cũng phải dọc — không xoay ảnh của ai cả.
            dich_w, dich_h = (dai, ngan) if im.width >= im.height else (ngan, dai)
            im = _cat_giua(im, dich_w / dich_h)
            im = im.resize((dich_w, dich_h), Image.LANCZOS)
            dich_tep = thu_muc / (p.stem + DUOI_RA)
            im.save(dich_tep, format="PNG")
            sau[ten].append({"tep": dich_tep.name, "rong": im.width, "cao": im.height})
            im.close()

    ban_ke = {
        "khung_chung": f"{dai}x{ngan}",
        "canh_dai_chung": dai,
        "truoc": truoc,
        "sau": sau,
        "_doc": (
            "Da chuan hoa ve cung canh dai va cung dinh dang PNG. HAI ly do: "
            "(1) cong bang - anh to hon trong net hon bat ke model; "
            "(2) TINH MU - cham_mu.ghi_lo giu nguyen duoi tep goc, nen mot ben .jpg "
            "mot ben .png la nguoi cham nhin ten tep cung doan duoc nguon. "
            "KHONG chua duoc: anh Gemini da qua JPEG mot lan o nguon; ha kich thuoc "
            "lam nhieu nen mo di chu khong xoa - dieu nay nghieng ve phia BAT LOI "
            "cho Gemini, phai noi ro khi ket luan neu ket qua sat nhau. "
            "Khac biet NHU-GIAO (Gemini 1376x768 JPEG vs ta 2560x1440 PNG) la mot "
            "su that ve SAN PHAM, ghi o 'truoc' - dung lan no vao cau hoi ve MODEL. "
            "MOI anh ra deu CUNG MOT KHUNG: Gemini khai 16:9 nhung tra ti le 1,7917 "
            "con ta 1,7778, nen khop rieng canh dai van de lai lech 6 pixel chieu "
            "cao - nho nhung HE THONG, tuc la mot dau vet nguon."),
    }
    (ra / "ban_ke_chuan_hoa.json").write_text(
        json.dumps(ban_ke, ensure_ascii=False, indent=2), encoding="utf-8")
    return ban_ke


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Chuan hoa hai bo anh truoc khi so mu")
    p.add_argument("--vao", action="append", required=True,
                   help="thu muc anh (lap lai cho tung ben)")
    p.add_argument("--ra", required=True, help="thu muc ket qua")
    p.add_argument("--canh-dai", type=int, default=None,
                   help="ep canh dai (mac dinh: nho nhat trong ca hai ben)")
    a = p.parse_args(argv)
    try:
        bk = chuan_hoa([pathlib.Path(x) for x in a.vao], pathlib.Path(a.ra),
                       a.canh_dai)
    except LoiChuanHoa as e:
        print(f"LOI: {e}", file=sys.stderr)
        return 1
    print(f"canh dai chung: {bk['canh_dai_chung']}")
    for ten, ds in bk["truoc"].items():
        co = sorted({f"{x['rong']}x{x['cao']}" for x in ds})
        dd = sorted({x["dinh_dang"] for x in ds})
        moi = sorted({f"{x['rong']}x{x['cao']}" for x in bk["sau"][ten]})
        print(f"  {ten:22} {len(ds):>3} anh  {co} {dd}  ->  {moi} ['png']")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
