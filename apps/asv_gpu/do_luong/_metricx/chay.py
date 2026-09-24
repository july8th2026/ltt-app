"""Runner MetricX-24-Hybrid-Large (che do QE, khong tham chieu) — chay trong qc-venv.

    python chay.py vao.json ra.json

vao: {"cap": [{"ma", "nguon", "dich"}], "thiet_bi": "auto"|"cuda"|"cpu", "lo": 16}
ra : {"diem": {ma: float}, "thong_tin": {...so do...}}

Diem = loi MQM du doan, [0, 25], THAP LA TOT (0 = khong loi). Dau vao dung dinh
dang QE cua upstream `metricx24/predict.py`: "source: <nguon> candidate: <dich>",
bo token EOS, cat o 1536 token.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

GOC = Path(__file__).resolve().parent
sys.path.insert(0, str(GOC))

import ban_ghim  # noqa: E402


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
        ids = tokenizer("source: " + str(c["nguon"]) + " candidate: " + str(c["dich"]),
                        max_length=max_len, truncation=True, padding=False)["input_ids"]
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
        du_doan = model(ids.to(thiet_bi), mask.to(thiet_bi)).float().cpu().tolist()
        # strict: mot diem cho MOI cap da gui — lech do dai la model tra thieu.
        for (ma, _), d in zip(khoi, du_doan, strict=True):
            diem[ma] = round(float(d), 4)
    if thiet_bi == "cuda":
        torch.cuda.synchronize()
    giay = time.perf_counter() - t1

    thong_tin = {
        "mo_hinh": ban_ghim.PHIEN_BAN["mo_hinh"]["repo_id"],
        "revision": ban_ghim.PHIEN_BAN["mo_hinh"]["revision"],
        "thiet_bi": thiet_bi, "dtype": str(dtype).replace("torch.", ""),
        "so_cap": len(cap), "lo": lo,
        "giay_nap": round(giay_nap, 3), "giay_cham": round(giay, 3),
        "ms_moi_cap": round(1000 * giay / max(1, len(cap)), 2),
    }
    if thiet_bi == "cuda":
        thong_tin["vram_dinh_mb"] = round(torch.cuda.max_memory_allocated() / 2**20, 1)
        thong_tin["gpu"] = torch.cuda.get_device_name(0)
    return {"diem": diem, "thong_tin": thong_tin}


def main(argv: list[str]) -> int:
    vao, ra = Path(argv[1]), Path(argv[2])
    d = json.loads(vao.read_text(encoding="utf-8"))
    try:
        kq = cham(d["cap"], thiet_bi=d.get("thiet_bi", "auto"), lo=int(d.get("lo", 16)))
    except ImportError as e:
        # ⚠️ **THIEU THU VIEN la "khong do duoc", KHONG phai "bo do hong".**
        #
        #    `_nap()` nhap `torch`/`transformers`/`mt5_regression` muon. Thieu
        #    mot goi trong qc-venv thi `ModuleNotFoundError` bay len nguyen ven,
        #    tien trinh thoat khac 0 ma KHONG mang dau `KHONG_KHA_DUNG`, nen
        #    `venv.chay` nem `DoLuongLoi` va bao cao ghi `trang_thai: "loi"`.
        #
        # ⛔ Hai tinh huong KHAC LOAI bi gop lam mot: "cai dat thieu" (nguoi
        #    van hanh sua) va "bo do chay ma hong" (nguoi viet ma sua). Bon
        #    runner con lai (`gioi`/`giong`/`squim`/`ocr_khung`) deu da phan
        #    biet; rieng tep nay thi chua.
        print(f"KHONG_KHA_DUNG: thieu thu vien trong qc-venv: {e}", flush=True)
        return 3
    except ban_ghim.KhongKhaDung as e:
        print(str(e), flush=True)
        return 3
    ra.write_text(json.dumps(kq, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
