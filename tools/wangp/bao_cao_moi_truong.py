"""Báo cáo môi trường trên C-CLOUD. Chạy ở **mọi** lần khởi động.

🔴 Vì sao tách khỏi `cai_dat.sh`. Bước báo cáo trước đây nằm ở cuối đường cài
   đặt, nên một lần khởi động **bỏ qua cài đặt** (trường hợp phổ biến nhất — môi
   trường đã có sẵn trên volume) **không để lại báo cáo nào**. Đúng lúc cần trả
   lời *"nhân GGUF nạp được chưa"* thì không có gì để đọc.

⭐ Một lần khởi động phải **tự mô tả được**, không phụ thuộc vào việc nó có cài
   gì hay không. Cài đặt và báo cáo là hai việc khác nhau.

Ghi ra `/data/ket_qua/moi_truong.json`.
"""
from __future__ import annotations

import json
import platform
import sys

RA = "/data/ket_qua/moi_truong.json"
KHO = "/data/Wan2GP"


def _phien_ban(mod: str) -> str:
    try:
        from importlib.metadata import version

        return version(mod)
    except Exception as e:  # noqa: BLE001
        return f"THIEU: {str(e)[:60]}"


def _gguf() -> dict:
    """Nhân GGUF CUDA có **nạp được** không, và nếu không thì **vì sao**.

    ⛔ Gói cài được ≠ nhân nạp được. Ngày 07/09 báo cáo ghi đủ phiên bản
       `llamacpp_gguf_cuda` mà WanGP vẫn in *"kernels unavailable, using
       fallback"*. Một dòng phiên bản không phải một phép nghiệm thu.

    ⭐ WanGP **giữ** đúng ngoại lệ đó ở `_GGUF_CUDA_LOAD_ERROR`. Hỏi thẳng nó,
       thay vì đoán trong bốn chỗ hỏng mà `_validate_gguf_cuda_module` có.
    """
    try:
        sys.path.insert(0, KHO)
        from shared.qtypes import gguf as g

        g._probe_gguf_cuda_runtime(force=True)
        loi = getattr(g, "_GGUF_CUDA_LOAD_ERROR", None)
        return {
            "nap_duoc": bool(getattr(g, "_GGUF_CUDA_KERNELS_ENABLED_CACHE", False)),
            "ly_do_hong": f"{type(loi).__name__}: {loi}" if loi else "",
        }
    except Exception as e:  # noqa: BLE001
        return {"nap_duoc": False,
                "ly_do_hong": f"khong hoi duoc: {type(e).__name__}: {e}"}


def main() -> int:
    ra: dict = {"python": sys.version, "platform": platform.platform()}
    try:
        import torch

        ra.update(torch=torch.__version__, cuda=torch.version.cuda,
                  cuda_available=torch.cuda.is_available(),
                  gpu=[torch.cuda.get_device_name(i)
                       for i in range(torch.cuda.device_count())],
                  sm=[list(torch.cuda.get_device_capability(i))
                      for i in range(torch.cuda.device_count())],
                  vram_gb=[round(torch.cuda.get_device_properties(i).total_memory / 1e9, 2)
                           for i in range(torch.cuda.device_count())])
    except Exception as e:  # noqa: BLE001
        ra["torch_loi"] = str(e)

    for ten in ("mmgp", "sageattention", "gguf", "llamacpp_gguf_cuda"):
        ra[ten] = _phien_ban(ten)

    ra["gguf_cuda"] = _gguf()

    with open(RA, "w", encoding="utf-8") as f:
        json.dump(ra, f, ensure_ascii=False, indent=1)
    print(json.dumps(ra, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
