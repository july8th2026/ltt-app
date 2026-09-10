"""`A5` — chỉnh `wgp_config.json` trên volume để bộ mở rộng mô tả chạy được.

    py tools/wangp/cau_hinh_enhancer.py          # XEM: in ra truoc/sau, khong ghi
    py tools/wangp/cau_hinh_enhancer.py --ghi    # ghi that

⛔ **Mặc định là xem thôi.** Đây là cấu hình của một runtime dùng chung; ghi đè
   im lặng một tệp mà WanGP cũng tự ghi vào là cách chắc chắn để mất một thiết
   lập không ai nhớ đã đặt.

🔴 **Vì sao cần script này — bốn khoá, và ba trong số đó đang trỏ đúng vào thứ
   hỏng.** Đọc `wgp_config.json` thật trên volume ngày 07/09:

   | khoá | đang là | phải là | vì sao |
   |---|---|---|---|
   | `enhancer_enabled` | `5` | `4` | `5` = `Qwen3.8-27B Uncensored`, model đang chặn bởi lỗi cuBLAS đo được ở P01. `4` = `Qwen3.5-9B Abliterated`. |
   | `prompt_enhancer_quantization` | `"gguf"` | `"quanto_int8"` | nhân GGUF CUDA **không nạp được** trên ngăn xếp py3.11/cu130 (`bao_cao_moi_truong.py` đo mỗi lần khởi động). Int8 đi đường khác, không chạm GGUF. |
   | `enhancer_mode` | *vắng* ⇒ `1` | `0` | `1` là **on-demand**: chỉ chạy khi người ta bấm nút trên giao diện Gradio. Ta submit qua API và không bấm nút nào, nên với `1` thì khoá `prompt_enhancer` bị bỏ qua **hoàn toàn im lặng** (`wgp.py:6853`). |
   | `prompt_enhancer_speculative_decoding` | `2` (auto) | `0` | `2` + VRAM 99 GB ⇒ tự bật speculative decoding, kéo thêm tệp `_mtp_` và một đường giải mã chưa từng chạy ở đây. Lượt đầu chỉ nên hỏng vì **một** lý do. Bật lại sau khi có một lượt xanh. |

   ⭐ Ba dòng đầu **không phải cấu hình tồi** — chúng là mặc định xuất xưởng của
      WanGP cho một máy đủ mạnh. Chúng sai với **máy này**, và đó đúng là loại
      khác biệt không đọc tài liệu ra được, chỉ đo mới biết.

🔑 **Đánh số họ model không phải phỏng đoán.** Đọc thẳng
   `shared/prompt_enhancer/qwen35_vl.py`::

       def get_qwen35_prompt_enhancer_variant(model_no) -> str:
           return {3: QWEN35_VARIANT_4B, 4: QWEN35_VARIANT_9B,
                   5: QWEN38_VARIANT_27B}[int(model_no)]

   và `loader.py:44,54` cho `1` = Florence2+Llama3.2, `2` = Florence2+LlamaJoy.

⛔ **Chỉ ghi khi pod đang TẮT.** `wgp.py` giữ `server_config` trong RAM và ghi đè
   cả tệp ở nhiều chỗ (`wgp.py:2661`, `9553`, `10575`, `11145`). Ghi vào lúc nó
   đang chạy là viết lên thứ sắp bị viết đè — im lặng, không lỗi.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from tools.wangp.may_cloud import (nap_env, tao_client,  # noqa: E402
                                   tim_app_env)

BUCKET = "uizchbiet5"
KHOA_CONFIG = "Wan2GP/wgp_config.json"

#: Bộ giá trị đích. Khoá nào không có ở đây thì **không đụng tới**.
MUON: dict[str, object] = {
    "enhancer_enabled": 4,                        # Qwen3.5-9B Abliterated
    "enhancer_mode": 0,                           # 0 = tu dong, 1 = bam nut
    "prompt_enhancer_quantization": "quanto_int8",
    "prompt_enhancer_speculative_decoding": 0,
}


def _s3():
    import boto3  # noqa: PLC0415
    from botocore.config import Config  # noqa: PLC0415

    thieu = [t for t in ("RUNPOD_S3_ENDPOINT", "RUNPOD_S3_REGION",
                         "RUNPOD_S3_ACCESS_KEY", "RUNPOD_S3_SECRET_KEY")
             if not os.environ.get(t)]
    if thieu:
        raise SystemExit("thieu bien moi truong: " + ", ".join(thieu))
    return boto3.client(
        "s3", endpoint_url=os.environ["RUNPOD_S3_ENDPOINT"],
        region_name=os.environ["RUNPOD_S3_REGION"],
        aws_access_key_id=os.environ["RUNPOD_S3_ACCESS_KEY"],
        aws_secret_access_key=os.environ["RUNPOD_S3_SECRET_KEY"],
        config=Config(signature_version="s3v4", retries={"max_attempts": 2},
                      connect_timeout=15, read_timeout=90))


def pod_dang_chay(pod_id: str) -> bool:
    """`True` nếu pod còn chạy. Ném lỗi nếu không hỏi được — **không** đoán."""
    api = tao_client()
    return str(api.rest("GET", f"/pods/{pod_id}").get("desiredStatus") or
               "").upper() == "RUNNING"


def khac_biet(hien_tai: dict) -> dict:
    """Khoá nào thật sự phải đổi. Rỗng ⇒ không có gì để làm."""
    return {k: v for k, v in MUON.items() if hien_tai.get(k) != v}


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    ghi = "--ghi" in argv
    # `--env <duong-dan>`: ghi de cho ban kiem, hoac cho may khong phai kho git.
    tuy = None
    if "--env" in argv:
        i = argv.index("--env")
        if i + 1 >= len(argv):
            print("[dung] `--env` thieu duong dan.")
            return 2
        tuy = argv[i + 1]

    nap_env(tim_app_env(tuy))
    pod = (os.environ.get("LTTV_POD_ID") or "").strip()
    if ghi and pod and pod_dang_chay(pod):
        print(f"[dung] pod {pod} DANG CHAY. Tat pod roi ghi — WanGP giu "
              "server_config trong RAM va se ghi de len thay doi cua ta.")
        return 2

    s3 = _s3()
    tho = s3.get_object(Bucket=BUCKET, Key=KHOA_CONFIG)["Body"].read()
    cu = json.loads(tho.decode("utf-8"))

    doi = khac_biet(cu)
    print(f"[doc] {KHOA_CONFIG}: {len(tho)} byte, {len(cu)} khoa")
    for k in MUON:
        dau = "  " if k not in doi else "=>"
        print(f" {dau} {k}: {cu.get(k, '<VANG>')!r} -> {MUON[k]!r}")
    if not doi:
        print("[xong] da dung roi, khong ghi gi.")
        return 0
    if not ghi:
        print(f"[xem] {len(doi)} khoa se doi. Them `--ghi` de ghi that.")
        return 0

    moi = dict(cu)
    moi.update(MUON)
    # `indent=4` giong het bản WanGP tu ghi ra, de `git diff` va mat nguoi doc
    # deu chi thay bon dong that su doi.
    than = json.dumps(moi, indent=4, ensure_ascii=False).encode("utf-8")
    s3.put_object(Bucket=BUCKET, Key=KHOA_CONFIG, Body=than,
                  ContentType="application/json")

    # Doc lai tu nguon — mot lenh put tra 200 khong chung minh noi dung da dung.
    lai = json.loads(s3.get_object(Bucket=BUCKET,
                                   Key=KHOA_CONFIG)["Body"].read().decode("utf-8"))
    con = khac_biet(lai)
    if con:
        print(f"[LOI] ghi xong ma van lech: {con}")
        return 3
    print(f"[ghi] xong {len(doi)} khoa, doc lai da khop. "
          f"{len(lai)} khoa (truoc: {len(cu)}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
