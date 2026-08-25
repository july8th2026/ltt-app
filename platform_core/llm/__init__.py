"""
llm — năng lực GỌI MODEL NGÔN NGỮ dùng chung cho mọi app. (H38)

⭐ Vì sao ở `platform_core` chứ không trong app: đây là năng lực nền tảng như
   `storage`/`api_pool`/`image_gen`. App chỉ khai model muốn dùng, không tự dựng
   đường gọi.

⭐ VÌ SAO GÓI NÀY TỒN TẠI — nợ kiến trúc có sẵn từ trước, không phải do H38 sinh ra.
   Trước gói này, **ba nơi tự gọi nhà cung cấp, mỗi nơi một kiểu**:

     platform_core/agent/planner.py   ghi cứng `thu_tu_provider=["gemini"]` VÀ
                                      ghi cứng luôn HTTP của Gemini
     apps/autosubvideo/ai_workflows.py
     apps/<slug>/jobs.py

   Hệ quả: cascade đa-provider của H8 có tồn tại, nhưng chỉ ở tầng **cấp key** —
   không ai bắc cầu nó sang tầng **gọi model**. Nên thêm một provider vào
   `REGISTRY` sẽ **không làm app nào dùng nó cả**.

   Gói này là cây cầu đó. Thêm provider mới ⇒ sửa **một** chỗ, không phải ba.

Hiện có:
  · `cong_vlm` — client phía MÁY A gọi cổng VLM trên máy B.
"""
from __future__ import annotations

__all__ = ["cong_vlm"]
