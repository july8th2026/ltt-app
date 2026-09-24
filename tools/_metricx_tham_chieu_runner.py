"""Runner MetricX-24-Hybrid-Large che do **THAM CHIEU** — chay trong qc-venv.

    python _metricx_tham_chieu_runner.py vao.json ra.json

vao: {"cap": [{"ma", "nguon", "dich", "tham_chieu"}],
      "thiet_bi": "auto"|"cuda"|"cpu", "lo": 16}
ra : {"diem": {ma: float}, "thong_tin": {...so do...}}

## Khac gi `apps/asv_gpu/do_luong/_metricx/chay.py`?

`chay.py` chay che do **QE** (khong tham chieu): `"source: X candidate: Y"`.
Tep nay chay che do **tham chieu**: `"source: X candidate: Y reference: Z"`.
Cung MOT checkpoint — `metricx-24-**hybrid**` duoc huan luyen cho CA HAI che do.

⛔ Tep nay KHONG sua `chay.py`: duong QC san pham dang chay QE va phai giu nguyen.
   Day la duong **do chuan** (co ban dich nguoi de so), dung cho bench, khong
   nam trong duong chay cua khach.

## Nguon cua dinh dang dau vao — ⛔ khong tu bia

`google-research/metricx` commit `fc4978eb064670f7cc33e93ea4f52d38396b8ae6`,
tep `metricx24/predict.py`, ham `get_dataset._make_input`:

    if is_qe:  "source: " + source + " candidate: " + hypothesis
    else:      "source: " + source + " candidate: " + hypothesis
               + " reference: " + reference

Sau do: tokenize(max_length, truncation=True, padding=False) roi **bo token EOS**
(`_remove_eos`). Ba buoc ay duoc chep y nguyen o duoi.

Giay phep / ghi cong: `apps/asv_gpu/do_luong/_metricx/{LICENSE,NOTICE}`
(Apache-2.0, Copyright 2024 Google LLC). Tep nay dung lai `ban_ghim.py` (ghim ban
+ sha256) va `mt5_regression.py` (MT5ForRegression) cua thu muc do — ⛔ khong chep
lai lop model.

Thang diem: loi MQM du doan trong [0, 25], **THAP LA TOT**.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
_METRICX = GOC / "apps" / "asv_gpu" / "do_luong" / "_metricx"
if not _METRICX.is_dir():  # pragma: no cover - loi cai dat
    raise SystemExit(f"khong thay {_METRICX}")
sys.path.insert(0, str(_METRICX))

import ban_ghim  # noqa: E402  (nam trong _METRICX)


def _nap(thiet_bi: str):
    import torch
    import transformers
    from mt5_regression import MT5ForRegression

    mo_hinh = ban_ghim.kiem_muc("mo_hinh")
    tok = ban_ghim.kiem_muc("tokenizer")
    if thiet_bi == "auto":
        thiet_bi = "cuda" if torch.cuda.is_available() else "cpu"
    # bf16 tren GPU (checkpoint la bf16); CPU dung fp32 (bf16 CPU cham va lech so).
    dtype = torch.bfloat16 if thiet_bi == "cuda" else torch.float32
    tokenizer = transformers.T5TokenizerFast.from_pretrained(
        str(tok["spiece.model"].parent))
    model = MT5ForRegression.from_pretrained(
        str(mo_hinh["pytorch_model.bin"].parent), torch_dtype=dtype)
    model.to(thiet_bi).eval()
    return tokenizer, model, thiet_bi, dtype


def cham(cap: list[dict], *, thiet_bi: str = "auto", lo: int = 16) -> dict:
    """Cham tung cap o che do THAM CHIEU. Tra `{"diem": {ma: float}, ...}`."""
    import torch

    t0 = time.perf_counter()
    tokenizer, model, thiet_bi, dtype = _nap(thiet_bi)
    if thiet_bi == "cuda":
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
    giay_nap = time.perf_counter() - t0
    max_len = int(ban_ghim.PHIEN_BAN["max_input_length"])

    vao = []
    for c in cap:
        # ⛔ Thu tu ba manh la CUA UPSTREAM — doi thu tu la doi phep do.
        van_ban = ("source: " + str(c["nguon"])
                   + " candidate: " + str(c["dich"])
                   + " reference: " + str(c["tham_chieu"]))
        ids = tokenizer(van_ban, max_length=max_len, truncation=True,
                        padding=False)["input_ids"]
        vao.append((str(c["ma"]), ids[:-1]))  # bo EOS nhu upstream
    # Xep theo do dai de lo it dem (padding) — ket qua khong phu thuoc thu tu.
    vao.sort(key=lambda x: len(x[1]))

    diem: dict[str, float] = {}
    t1 = time.perf_counter()
    pad = tokenizer.pad_token_id
    for i in range(0, len(vao), max(1, lo)):
        khoi = vao[i:i + lo]
        dai = max(len(ids) for _, ids in khoi)
        ids = torch.full((len(khoi), dai), pad, dtype=torch.long)
        mask = torch.zeros((len(khoi), dai), dtype=torch.long)
        for j, (_, x) in enumerate(khoi):
            ids[j, :len(x)] = torch.tensor(x, dtype=torch.long)
            mask[j, :len(x)] = 1
        with torch.no_grad():
            du_doan = model(ids.to(thiet_bi), mask.to(thiet_bi)).float().cpu().tolist()
        # strict: mot diem cho MOI cap da gui — lech do dai la model tra thieu.
        for (ma, _), d in zip(khoi, du_doan, strict=True):
            diem[ma] = round(float(d), 4)
    if thiet_bi == "cuda":
        torch.cuda.synchronize()
    giay = time.perf_counter() - t1

    return {
        "diem": diem,
        "thong_tin": {
            "che_do": "tham_chieu",
            "thiet_bi": thiet_bi,
            "dtype": str(dtype),
            "so_cap": len(cap),
            "lo": lo,
            "giay_nap": round(giay_nap, 2),
            "giay_cham": round(giay, 2),
            "mo_hinh": ban_ghim.PHIEN_BAN["mo_hinh"]["repo_id"],
            "revision": ban_ghim.PHIEN_BAN["mo_hinh"]["revision"],
        },
    }


def main() -> None:
    vao = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    ra = cham(vao["cap"], thiet_bi=vao.get("thiet_bi", "auto"),
              lo=int(vao.get("lo", 16)))
    Path(sys.argv[2]).write_text(json.dumps(ra, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
