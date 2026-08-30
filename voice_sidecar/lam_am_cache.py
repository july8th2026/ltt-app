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
import os
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

    # Windows không có symlink cho tài khoản thường, nên `huggingface_hub` rơi về
    # chế độ chép tệp. Cảnh báo đó là bình thường và không cần in mỗi lần cài.
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

    from huggingface_hub import snapshot_download

    mau = list(MAU_GPU)
    if args.include_onnx:
        mau += MAU_ONNX

    # 🔴 `max_workers=1` VÀ CÓ THỬ LẠI — cả hai đều từ một lần hỏng thật.
    #
    #    Lượt cài đầu tiên ngày 30/08 chết với:
    #      FileNotFoundError: ...\blobs\5c9785c19639481f69f407f8b96859f0ea0d65af
    #    rồi lượt chạy lại ngay sau đó **thành công không sửa gì**.
    #
    #    Cơ chế: trên Windows không có symlink, `huggingface_hub` tải vào `blobs\`
    #    rồi CHÉP sang `snapshots\`. Tải song song nhiều tệp làm hai bước đó đua
    #    nhau và một blob biến mất giữa chừng.
    #
    #    ⛔ Đừng đọc lỗi này thành "mạng hỏng" hay "repo sai" — nó tái hiện được
    #       và nó là một cuộc đua cục bộ. Một luồng thì hết đua; thử lại thì che
    #       nốt phần còn lại (quét virus giữ tệp, đĩa bận).
    loi = None
    for lan in range(1, 4):
        try:
            duong = snapshot_download(repo_id=args.repo, revision=args.revision,
                                      allow_patterns=mau, max_workers=1)
            print(duong)
            return 0
        except (FileNotFoundError, OSError) as e:
            loi = e
            print(f"lan {lan} that bai ({type(e).__name__}), thu lai...",
                  file=sys.stderr)
    print(f"tai model that bai sau 3 lan: {loi}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
