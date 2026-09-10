"""
image_gen — năng lực SINH ẢNH dùng chung cho mọi app.

⭐ Vì sao ở `platform_core` chứ không trong app: đây là năng lực nền tảng như
   `storage`/`api_pool`. App chỉ khai model muốn dùng, không tự dựng đường gọi.

Hiện có:
  · `prompt_dich`  — chuẩn bị prompt: dịch phần mô tả, giữ nguyên chữ-cần-vẽ (D-027)
  · `dich_llm`     — đường gọi LLM thật cho `prompt_dich`, qua LTT_LLM
  · `cong_render`  — client gọi cổng render trên máy B (D-028)

Đường đi một job sinh ảnh nội bộ:

    prompt khách
        → prompt_dich.dich_prompt_anh(goi_llm=dich_llm.tao_ham_dich(db))
        → cong_render.CongRender.gui(...)
        → máy B vẽ, đẩy thẳng lên R2 bằng presigned PUT
"""
