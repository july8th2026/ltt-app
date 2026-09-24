# Task 1 — Đấu dây node AI → ToolSpec

**Nguồn tra:** `apps/ltt_llm/manifest.py:267-268` (`ToolSpec(name="text.chat",
job_type="ltt_llm.chat", ...)`), `:354` (`returns`), `:368-370`
(`side_effect="external"`, `resource={"class":"api"}`) — job_type/pricing
lấy đúng chuỗi từ đây, không suy đoán. `platform_core/workflow/nut.py` (mẫu
`tu_toolspec`, `Gia.theo_registry`), spec §4.3/§4.5 (bảng: `ai.*` "khai
trong mã", khác `app.*`).

**Đỏ:** `tests/test_2902_ai_llm_dinh_nghia.py` — `ImportError: cannot import
name 'ai_llm'`.

**Xanh:** `platform_core/workflow/nut_loi/ai_llm.py` (mới) — `AI_LLM`,
`AI_EXTRACT`, đăng ký qua `nut_loi.dang_ky()` có sẵn. `thi_hanh="job"`,
`job_type="ltt_llm.chat"`, `Gia.theo_registry("ltt_llm.chat")`. 9/9 test
xanh, gộp cả `test_1755_wf_nut_ba_nguon.py` (ba nguồn cũ) vẫn xanh — không
phá `dang_ky` chung.

**Chưa làm được:**

1. **Chưa "sống" trong palette thật.** `dang_ky()` chỉ chạy khi module
   `ai_llm.py` được import; `nut_loi/__init__.py` (chỉ có `trigger.manual`)
   chưa import nó. Việc nối import này là một dòng ở `__init__.py` —
   NGOÀI phạm vi tệp cho phép của làn p7 (`nut_loi/ai_*.py` + test), và tự
   nhiên rơi vào Task 5 (đóng phase) mà brief bảo tôi không làm. Test chứng
   minh cơ chế ĐÚNG bằng cách tự import `ai_llm` trực tiếp.
2. **Chưa nối `cau_noi.nop_job`.** Cầu nối job chung suy tên ToolSpec bằng
   `node["type"][4:]` (cắt 4 ký tự tiền tố `"app."`) — áp cho `"ai.llm"` ra
   `"lm"`, sai. Tổng quát hoá đòi sửa `platform_core/workflow/cau_noi.py`,
   cũng ngoài phạm vi tệp cho phép.
3. `tham_so` là từ vựng riêng của node (`prompt`, không phải `messages` thô
   của `text.chat`) — chưa có bộ dịch `tham_so ai.* -> params text.chat`
   (việc của compiler, chưa publish_duoc).
