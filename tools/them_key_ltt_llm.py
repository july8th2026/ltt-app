"""them_key_ltt_llm.py — ghi bearer token của cổng VLM máy B vào sổ khoá. (H38)

    python tools/them_key_ltt_llm.py --token <BEARER> [--base-url http://192.168.2.66:8299]

Chạy MỘT lần trên máy chủ. Idempotent: đã có khoá `ltt_llm` thì chỉ cập nhật
credential và base_url, **không** tạo bản ghi thứ hai.

⭐ VÌ SAO CẦN BƯỚC NÀY: `api_pool.chon_key()` cấp phát từ bảng `api_keys`. Không có
   bản ghi ở đó thì `dieu_phoi.goi()` sẽ bỏ qua provider `ltt_llm` và im lặng rơi
   sang Gemini — **đúng thứ trông giống "model nhà chưa chạy" nhất, mà thật ra là
   "chưa ai khai khoá"**.

⛔ TOKEN LÀ BÍ MẬT. Nó được mã hoá bằng `secretbox` trước khi vào CSDL. Script này
   **không in nó ra**, và đừng dán nó vào log, ảnh chụp màn hình hay tóm tắt.

⛔ Token này KHÔNG phải bí mật của nền tảng theo nghĩa Q102 — nó chỉ bảo vệ cổng VLM
   trên LAN. Máy B vẫn không giữ mật khẩu CSDL, khoá R2 hay khoá mã hoá nào.

Lấy token ở đâu (chạy trên máy A):

    ssh -i %USERPROFILE%\\.ssh\\nexus_b lengo@192.168.2.66 ^
        "findstr LTT_LLM_TOKEN C:\\ProgramData\\LTTLlm\\gateway.env"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEN_PROVIDER = "ltt_llm"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Ghi bearer token cong VLM may B vao so khoa.")
    ap.add_argument("--token", required=True, help="bearer token cua cong VLM")
    ap.add_argument("--base-url", default="http://192.168.2.66:8299",
                    help="dia chi cong VLM tren LAN")
    ap.add_argument("--models", default="ltt_llm,ltt_llm_vision",
                    help="danh sach model khoa nay phuc vu")
    # Ưu tiên THẤP hơn số mặc định 100 nghĩa là được chọn TRƯỚC (xem `api_pool`).
    # Model nhà nên đi trước đám mây: nó rẻ hơn và dữ liệu không rời máy.
    ap.add_argument("--priority", type=int, default=50)
    a = ap.parse_args(argv)

    tok = (a.token or "").strip()
    if not tok:
        print("LOI: token rong")
        return 1

    from platform_core import api_keys
    from platform_core.db import get_session
    from platform_core.models import APIKEY_CAT_CHAT, ApiKey
    from sqlalchemy import select

    models = [m.strip() for m in a.models.split(",") if m.strip()]

    gen = get_session()
    db = next(gen)
    try:
        cu = db.execute(
            select(ApiKey).where(ApiKey.provider == TEN_PROVIDER)
        ).scalars().first()

        if cu is not None:
            api_keys.dat_credential(db, cu, tok)
            cu.base_url = a.base_url
            cu.supported_models = models
            cu.default_model = models[0] if models else ""
            cu.priority = a.priority
            db.commit()
            print(f"DA CAP NHAT khoa '{TEN_PROVIDER}' (id={cu.id[:8]}) "
                  f"-> {a.base_url}, models={models}")
            return 0

        key = api_keys.tao_key(
            db, provider=TEN_PROVIDER, credential=tok,
            name="LTT LLM (may B)",
            categories=[APIKEY_CAT_CHAT],
            base_url=a.base_url,
            supported_models=models,
            default_model=models[0] if models else "",
            priority=a.priority,
        )
        db.commit()
        print(f"DA TAO khoa '{TEN_PROVIDER}' (id={key.id[:8]}) "
              f"-> {a.base_url}, models={models}, priority={a.priority}")
        print("Token da duoc MA HOA truoc khi luu. Script nay khong in no ra.")
        return 0
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
