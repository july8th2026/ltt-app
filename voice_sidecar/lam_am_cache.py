"""
lam_am_cache.py — tải trước trọng số VieNeu vào cache HuggingFace.

    python lam_am_cache.py --repo pnnbao-ump/VieNeu-TTS-v3-Turbo --revision <sha>

⭐ VÌ SAO PHẢI TẢI LÚC CÀI, KHÔNG ĐỂ DỊCH VỤ TỰ TẢI LÚC CHẠY:

   Lần khởi động đầu tiên sẽ kéo ~320 MB. Trong lúc đó dịch vụ **im lặng** — không
   log, không lỗi, chỉ là chưa lên. Người vận hành nhìn vào chỉ thấy `LTTStudioVoice`
   ở trạng thái `Running` mà `/live` không trả lời, và kết luận sai là nó treo.

   Tải lúc cài biến việc đó thành một dòng tiến độ trong bộ cài — đúng chỗ người
   ta đang chờ.

⛔ TẢI THEO REVISION, KHÔNG THEO `main`. Bản v3 full sắp ra và sẽ đổi hành vi mà
   **không đổi tên repo**. Một bản cài hôm nay và một bản cài tháng sau phải cho
   ra cùng một model, nếu không thì bảng đo của V1 không còn nghĩa gì.

⛔ CHỈ TẢI THỨ ĐANG DÙNG. Kho đầy đủ là 1.678 MB nhưng đường PyTorch/GPU chỉ cần
   `update/` + hai tệp ONNX phụ trợ = ~320 MB:

     update/model.safetensors   248,0 MB   backbone (mac dinh `model_subfolder='update'`)
     denoiser.onnx               42,7 MB   khu nhieu clip tham chieu
     speaker_encoder.onnx        28,3 MB   trich speaker embedding khi ghi danh
     *.json                       nho      config + tokenizer

   Bốn thư mục `onnx/`, `onnx_int8/`, `onnx_update/` và `model.safetensors` ở gốc
   là của **đường CPU/ONNX** — chỉ tải khi bật `--include-onnx`.
"""
from __future__ import annotations

import argparse
import sys

#: Đường PyTorch/GPU. `update/` là subfolder mặc định của
#: `VieNeuTTSv3Turbo.__init__(model_subfolder='update')`.
MAU_GPU = ["*.json", "denoiser.onnx", "speaker_encoder.onnx", "update/*"]

#: Đường CPU/ONNX int8 — làn dự phòng. `precision="int8"` ánh xạ sang
#: subfolder `onnx_int8` (xem `v3turbo.py`: {"int8": "onnx_int8", "fp32": "onnx_update"}).
MAU_ONNX = ["onnx_int8/*"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--revision", required=True,
                    help="SHA đầy đủ. KHÔNG nhận 'main'.")
    ap.add_argument("--include-onnx", action="store_true",
                    help="Tải thêm đường CPU/ONNX int8 (làn dự phòng).")
    args = ap.parse_args(argv)

    if args.revision.strip().lower() in {"main", "master", "head", ""}:
        print("revision phai la mot SHA cu the, khong phai mot nhanh dang chay.",
              file=sys.stderr)
        return 2

    from huggingface_hub import snapshot_download

    mau = list(MAU_GPU)
    if args.include_onnx:
        mau += MAU_ONNX

    duong = snapshot_download(repo_id=args.repo, revision=args.revision,
                              allow_patterns=mau)
    print(duong)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
