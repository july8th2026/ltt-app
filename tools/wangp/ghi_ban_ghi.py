"""Máy ghi — công cụ **duy nhất** được phép ghi vào `apps/lttvideo/ban_ghi/`.

## Vì sao chỉ một cửa ghi

`ban_ghi/` là bản chép của một sự thật nằm ở nơi khác (WanGP). Nếu có hai đường
ghi vào đó thì có hai sự thật, và một trong hai sai mà không ai biết cái nào.
Mọi thứ khác **chỉ đọc**.

## Hai chế độ

```
python tools/wangp/ghi_ban_ghi.py --tu-anh-chup     # doi du lieu DA CO san
python tools/wangp/ghi_ban_ghi.py --pod             # hoi may that (HM-7)
```

⭐ `--pod` **không cần GPU lành.** Bốn đường tra cứu của WanGP đọc bản khai JSON
  và quét hệ tệp — không nhân một ma trận nào. Chúng chạy được cả khi stack CUDA
  đang hỏng, và đó là lý do bước ghi không phải chờ bước dựng lại stack.

## Phong bì

Mỗi bản ghi mang `nguon` để không bao giờ nhầm dữ liệu tạm với dữ liệu thật:

- `"ghi_tu_may"` — hỏi WanGP thật (kể cả gián tiếp, qua một ảnh chụp cũ của
  chính nó, miễn là ảnh chụp ấy ghim đúng SHA)
- `"khuon"` — ta dựng tạm cho đúng hình dạng; nội dung **chưa chắc đúng**

Một khuôn sót lại trông y hệt dữ liệu thật. Đó là lý do trường này bắt buộc.
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

GOC_KHO = Path(__file__).resolve().parents[2]
GOC_BAN_GHI = GOC_KHO / "apps" / "lttvideo" / "ban_ghi"

#: SHA thượng nguồn mọi bản ghi phải khớp. Lệch SHA nghĩa là bản ghi nói về một
#: engine khác bản, và mọi tham số trong đó mất nghĩa.
WANGP_SHA = "1e1dd2757f24923f008593d9d4ec09062234be20"


def _bay_gio() -> str:
    return datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()


def ghi(ten: str, du_lieu, *, nguon: str, goi: str,
        goc: Path | None = None) -> Path:
    """Ghi một bản ghi kèm phong bì. LF, UTF-8, không BOM.

    ⚠️ `write_text` trên Windows dịch `\\n` thành `\\r\\n`; dùng `write_bytes`.
    """
    if nguon not in {"ghi_tu_may", "khuon"}:
        raise SystemExit(f"nguon khong hop le: {nguon!r}")
    thu_muc = goc or GOC_BAN_GHI
    thu_muc.mkdir(parents=True, exist_ok=True)
    tep = thu_muc / f"{ten}.json"
    than = {"nguon": nguon, "sha_wangp": WANGP_SHA, "luc": _bay_gio(),
            "goi": goi, "du_lieu": du_lieu}
    tep.write_bytes(
        (json.dumps(than, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    return tep


# ══════════════════════════════════════════════════════════════════════════
#  Che do 1 — doi du lieu DA CHUP tu may that
# ══════════════════════════════════════════════════════════════════════════

def tu_anh_chup(anh_chup: Path, ho_so_data: Path, goc: Path | None = None) -> list[Path]:
    """Ảnh chụp `metadata` 225 model + hai bộ settings, đều đã rút từ máy thật.

    ⭐ Đây **không phải** dữ liệu bịa. `anh_chup` là đầu ra `get_model_schema()`
      của từng model, chụp trên C-CLOUD tại đúng SHA ghim; hai tệp `ho_so_data`
      là đầu ra `get_default_settings('t2v_2_2')` / `('i2v_2_2')` rút cùng ngày.
      Nên chúng mang `nguon="ghi_tu_may"`.
    """
    d = json.loads(anh_chup.read_text(encoding="utf-8"))
    if d.get("wangp_sha") != WANGP_SHA:
        raise SystemExit(
            f"anh chup ghim SHA {d.get('wangp_sha')!r}, khong khop {WANGP_SHA!r} "
            "— mot ban ghi lech SHA noi ve mot engine khac ban")
    theo_model: dict = d["model"]

    ra = []
    # `list_model_metadata()` tra mot DANH SACH cac ban ghi co `model_type` o
    # cap cao nhat va phan con lai trong `metadata` (docs_API.md:262).
    ra.append(ghi("liet_ke_model",
                  [{"model_type": k, "name": (v or {}).get("name") or k,
                    "metadata": v} for k, v in sorted(theo_model.items())],
                  nguon="ghi_tu_may", goi="list_model_metadata()", goc=goc))

    # ⭐ MOT tep cho ca 225 so do, khong phai 225 tep. Cung mot du lieu, nhung
    #    225 tep nho trong git lam moi lan ghi lai thanh mot diff khong doc noi.
    ra.append(ghi("so_do", theo_model, nguon="ghi_tu_may",
                  goi="get_model_schema(<moi model>)", goc=goc))

    for model_type, ten_tep in (("t2v_2_2", "ltt.video.chuan.v1.json"),
                                ("i2v_2_2", "ltt.video.anh.v1.json")):
        tep = ho_so_data / ten_tep
        if not tep.is_file():
            print(f"  bo qua {ten_tep} (khong co)", file=sys.stderr)
            continue
        ra.append(ghi(f"mac_dinh__{model_type}",
                      json.loads(tep.read_text(encoding="utf-8")),
                      nguon="ghi_tu_may",
                      goi=f"get_default_settings({model_type!r})", goc=goc))
    return ra


# ══════════════════════════════════════════════════════════════════════════
#  Che do 2 — hoi may that (HM-7)
# ══════════════════════════════════════════════════════════════════════════

def tu_pod(goc_url: str, khoa: str, goc: Path | None = None) -> list[Path]:
    """Hỏi bốn đường tra cứu của cầu nối.

    ⛔ Ghi **nguyên văn** thứ máy trả về. Không lọc, không sắp lại, không vá ô
       trống — một bản ghi đã bị dọn thì không còn là bản ghi.
    """
    sys.path.insert(0, str(GOC_KHO))
    from apps.lttvideo.cong.may_that import MayThat  # noqa: PLC0415

    may = MayThat(goc_url, khoa=khoa)
    ds = may.liet_ke_model()
    ra = [ghi("liet_ke_model", ds, nguon="ghi_tu_may",
              goi="list_model_metadata()", goc=goc)]

    so_do = {}
    kha_dung = {}
    for m in ds:
        mt = m["model_type"]
        so_do[mt] = may.so_do(mt)
        kha_dung[mt] = may.kha_dung(mt)
    ra.append(ghi("so_do", so_do, nguon="ghi_tu_may",
                  goi="get_model_schema(<moi model>)", goc=goc))
    ra.append(ghi("kha_dung", kha_dung, nguon="ghi_tu_may",
                  goi="get_model_availability(<moi model>)", goc=goc))
    return ra


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tu-anh-chup", action="store_true",
                   help="doi anh chup metadata da co san thanh ban ghi")
    p.add_argument("--pod", action="store_true", help="hoi may that (HM-7)")
    p.add_argument("--url", default="", help="goc URL cua cau noi C-CLOUD")
    p.add_argument("--khoa", default="", help="khoa endpoint")
    a = p.parse_args(argv)

    if a.tu_anh_chup:
        # ⚠️ Mot lan DI TRU, da chay 07/09/2026. Anh chup tho da duoc go sau do:
        #    noi dung cua no nam TRON VEN trong `so_do.json` (doi chieu bang
        #    phep so bang, giong het, 225 model) va o day co them xuat xu. Giu
        #    ca hai la giu HAI ban cua mot su that, va mot trong hai se troi.
        anh = GOC_BAN_GHI / "anh_chup_metadata_1e1dd275.json"
        if not anh.is_file():
            raise SystemExit(
                "anh chup tho da go sau lan di tru 07/09 — dung `--pod` de ghi "
                "lai tu may that")
        tep = tu_anh_chup(anh, GOC_KHO / "apps" / "lttvideo" / "ho_so_data")
    elif a.pod:
        if not a.url:
            p.error("--pod can --url")
        tep = tu_pod(a.url, a.khoa)
    else:
        p.error("chon --tu-anh-chup hoac --pod")
        return 2

    for t in tep:
        print(f"  ghi {t.relative_to(GOC_KHO)}  ({t.stat().st_size:,} byte)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
