"""
doi_chung_gemini.py — sinh **nửa đối chứng Gemini** cho cổng chất lượng G6b.

    py tools/doi_chung_gemini.py --ra bench/G6b_gemini            # THU KHO, khong tieu tien
    py tools/doi_chung_gemini.py --ra bench/G6b_gemini --that     # goi that

⭐ VÌ SAO TỆP NÀY TỒN TẠI VÀ VÌ SAO NÓ CHẠY ĐƯỢC KHI GPU BẬN:

   G6b hỏi *"model nhà có đáng bán không"* bằng cách so mù với **Gemini 3 Pro Image**
   — thứ ta **đang bán**. Nửa Gemini là **API đám mây, không chạm GPU máy B một
   giây nào**. Nên nó làm được ngay cả khi card đang dành cho dự án khác, và khi tới
   lượt GPU rảnh thì **chỉ còn nửa của ta** phải chạy: phiên GPU ngắn đi một nửa.

⛔ BỐN ĐIỀU TỆP NÀY CƯỠNG CHẾ BẰNG MÃ, KHÔNG BẰNG TRÍ NHỚ:

 ① **Mặc định KHÔNG tiêu tiền.** Không có `--that` thì nó chỉ in ra sẽ gọi những gì
    và tốn khoảng bao nhiêu. Một lệnh gõ nhầm không được phép thành một hoá đơn.

 ② **CÙNG MỘT VĂN BẢN cho cả hai bên.** Đọc `bench/prompts_30_en.json` — đúng bộ mà
    phía ta dùng. So hai model bằng hai prompt khác nhau thì con số đo được là khác
    biệt giữa hai *prompt*, không phải giữa hai *model*.

 ③ **Ghi lại KÍCH THƯỚC THẬT của từng ảnh.** Hai bên ra ảnh khác kích thước là một
    biến gây nhiễu có thật: ảnh to hơn trông "nét hơn" bất kể model. Không tự ý
    resize ở đây — chỉ **ghi số** để bước dựng lô so mù chuẩn hoá, và để người đọc
    biết mà không phải đoán.

 ④ **Chạy lại được, không sinh trùng.** Ảnh đã có thì bỏ qua. Một lần gọi hỏng giữa
    chừng không bắt trả tiền lại từ đầu cho 29 ảnh đã xong.

⚠️ **MỘT ĐIỀU TỆP NÀY KHÔNG GIẢI ĐƯỢC, ghi ra để không ai tưởng là đã giải:**
   ta nạp prompt **tiếng Anh** cho cả hai bên, vì đó là so sánh *cùng đầu vào*.
   Nhưng sản phẩm thật thì khách gõ **tiếng Việt**: đường của ta là
   *dịch → model nhà*, còn Gemini **hiểu thẳng tiếng Việt**. Nên kết quả ở đây trả
   lời *"model nào vẽ đẹp hơn với cùng một câu tiếng Anh"*, **không** trả lời
   *"khách gõ tiếng Việt thì bên nào ra ảnh đúng ý hơn"*. Câu thứ hai cần một lô
   riêng, và nó đo cả lớp dịch chứ không chỉ model.
"""
from __future__ import annotations

import argparse
import base64
import json
import pathlib
import struct
import sys
import time
from typing import Optional

GOC = pathlib.Path(__file__).resolve().parent.parent

#: Bộ prompt dùng chung với phía ta. Đổi tệp này = so một thứ khác.
BO_PROMPT = GOC / "bench" / "prompts_30_en.json"

#: Model đối chứng. Đây là thứ **đang bán**, nên nó là đối thủ quan trọng nhất.
MODEL = "gemini-3-pro-image"

#: Tỉ lệ khung. Phía ta chạy 2560×1440 (16:9) ở G3 — phải khớp, không thì so hai
#: bố cục khác nhau.
TI_LE = "16:9"

#: Ước lượng để người bấm nút biết mình đang tiêu gì. Không phải giá chính thức.
UOC_GIA_USD_MOI_ANH = 0.13

TIMEOUT_S = 180.0


class LoiDoiChung(Exception):
    pass


def kich_thuoc_png(du_lieu: bytes) -> Optional[tuple[int, int]]:
    """(rộng, cao) từ header PNG. `None` nếu không phải PNG.

    Đọc thẳng 24 byte đầu thay vì kéo Pillow vào: tệp này chạy trong môi trường
    vận hành, và một phụ thuộc thêm là một lý do nữa để nó không chạy được.
    """
    if len(du_lieu) < 24 or du_lieu[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    if du_lieu[12:16] != b"IHDR":
        return None
    rong, cao = struct.unpack(">II", du_lieu[16:24])
    return int(rong), int(cao)


def doc_prompt(duong: pathlib.Path = BO_PROMPT) -> list[dict]:
    d = json.loads(duong.read_text(encoding="utf-8"))
    muc = d.get("prompts") if isinstance(d, dict) else d
    if not isinstance(muc, list) or not muc:
        raise LoiDoiChung(f"{duong.name}: khong doc duoc danh sach prompt")
    for m in muc:
        if not m.get("id") or not m.get("text"):
            raise LoiDoiChung(f"{duong.name}: mot muc thieu 'id' hoac 'text'")
    return muc


def _goi_gemini_anh(prompt: str, api_key: str, *, model: str = MODEL,
                    ti_le: str = TI_LE, http=None) -> bytes:
    """Một lượt gọi → bytes ảnh. Khuôn thân yêu cầu lấy từ `apps/taoanh/jobs.py`,
    không tự bịa: đó là khuôn đang phục vụ khách thật."""
    import httpx

    from platform_core.providers import resolve_model_id

    goi = http or httpx.post
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           f"{resolve_model_id(model)}:generateContent")
    than = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE", "TEXT"],
                             "imageConfig": {"aspectRatio": ti_le}},
    }
    r = goi(url, json=than, headers={"x-goog-api-key": api_key}, timeout=TIMEOUT_S)
    if r.status_code != 200:
        # ⛔ KHONG in `r.text` nguyen ven: than loi cua Gemini co the vong lai khoa.
        raise LoiDoiChung(f"Gemini HTTP {r.status_code}")
    d = r.json()
    if (d.get("promptFeedback") or {}).get("blockReason"):
        raise LoiDoiChung(f"bi chan: {d['promptFeedback']['blockReason']}")
    for c in (d.get("candidates") or []):
        for p in ((c.get("content") or {}).get("parts") or []):
            inline = p.get("inlineData") or p.get("inline_data")
            if inline and inline.get("data"):
                return base64.b64decode(inline["data"])
    raise LoiDoiChung("khong co anh trong phan hoi")


def _lay_key() -> str:
    """Khoá Gemini qua bộ máy APIKEYS. Không đọc biến môi trường."""
    from platform_core import api_keys, api_pool
    from platform_core.db import get_session
    from platform_core.models import APIKEY_CAT_IMAGE

    gen = get_session()
    db = next(gen)
    try:
        key = api_pool.lay_key(db, "gemini", category=APIKEY_CAT_IMAGE, model=MODEL)
        cred = api_keys.lay_credential(db, key)
        db.commit()
        return cred
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def chay(ra: pathlib.Path, *, that: bool, prompts: list[dict],
         goi=None, lay_key=None) -> dict:
    """Sinh ảnh đối chứng. `that=False` chỉ in kế hoạch, không gọi mạng."""
    ra.mkdir(parents=True, exist_ok=True)
    can_lam, da_co = [], []
    for m in prompts:
        (da_co if (ra / f"{m['id']}.png").exists() else can_lam).append(m)

    print(f"bo prompt : {len(prompts)} muc")
    print(f"da co     : {len(da_co)}  (bo qua, khong goi lai)")
    print(f"se goi    : {len(can_lam)}")
    print(f"model     : {MODEL} @ {TI_LE}")
    print(f"uoc tinh  : ~{len(can_lam) * UOC_GIA_USD_MOI_ANH:.2f} USD")
    if not that:
        print("\n[THU KHO] Chua goi gi ca. Them --that de goi that.")
        return {"thu_kho": True, "se_goi": [m["id"] for m in can_lam]}
    if not can_lam:
        print("\nKhong con gi de goi.")

    key = (lay_key or _lay_key)()
    ghi: list[dict] = []
    hong: list[dict] = []
    for i, m in enumerate(can_lam, 1):
        try:
            anh = _goi_gemini_anh(m["text"], key, http=goi)
        except Exception as e:                       # noqa: BLE001
            # Mot prompt hong khong duoc lam hong ca lo: 29 anh kia da tra tien roi.
            print(f"  [{i}/{len(can_lam)}] {m['id']}  HONG: {e}")
            hong.append({"id": m["id"], "loi": str(e)[:200]})
            continue
        tep = ra / f"{m['id']}.png"
        tep.write_bytes(anh)
        kt = kich_thuoc_png(anh)
        print(f"  [{i}/{len(can_lam)}] {m['id']}  {len(anh):>8,} B  "
              f"{(f'{kt[0]}x{kt[1]}' if kt else 'khong ro kich thuoc')}")
        ghi.append({"id": m["id"], "cat": m.get("cat", ""), "tep": tep.name,
                    "bytes": len(anh),
                    "rong": kt[0] if kt else None, "cao": kt[1] if kt else None})
        time.sleep(0.5)

    ban_ke = {
        "model": MODEL, "ti_le": TI_LE, "bo_prompt": BO_PROMPT.name,
        "so_thanh_cong": len(ghi), "so_hong": len(hong),
        "anh": ghi, "hong": hong,
        "_doc": ("Nua doi chung Gemini cho G6b. Cung van ban tieng Anh voi phia ta. "
                 "KICH THUOC co the khac phia ta - phai chuan hoa truoc khi dung lo "
                 "so mu, neu khong thi dang do 'anh nao to hon' chu khong phai "
                 "'model nao dep hon'."),
    }
    (ra / "ban_ke.json").write_text(
        json.dumps(ban_ke, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nxong: {len(ghi)} anh, {len(hong)} hong -> {ra / 'ban_ke.json'}")
    return ban_ke


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    p.add_argument("--ra", required=True, help="thu muc ghi anh")
    p.add_argument("--bo", default=str(BO_PROMPT), help="tep bo prompt")
    p.add_argument("--that", action="store_true",
                   help="GOI THAT va TIEU TIEN. Khong co co nay thi chi in ke hoach.")
    a = p.parse_args(argv)
    try:
        prompts = doc_prompt(pathlib.Path(a.bo))
        chay(pathlib.Path(a.ra), that=a.that, prompts=prompts)
    except LoiDoiChung as e:
        print(f"LOI: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
