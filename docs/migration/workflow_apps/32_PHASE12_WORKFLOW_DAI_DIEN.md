# 32 — Phase 12: bốn workflow đại diện, và hai tầng workflow chỉ một tầng chạy

**Ngày:** 2026-09-10 · **Bằng chứng:** `tests/test_1111_phase12_workflow_dai_dien.py`

Phase 12 hỏi: *"4 App có thay được orchestration của bot cũ không?"* Tài liệu này
trả lời bằng cách **chạy**, không bằng cách đọc mã.

---

## 1. 🔴 Hai tầng workflow, chỉ MỘT tầng chạy

| Tầng | Có gì | Ai lái |
|---|---|---|
| `platform_core/workflow/` (V2) | `dinh_nghia` · `thi_hanh` · `dieu_khien` · `bao_gia` | **không ai** |
| `platform_core/agent/` (M1) | `executor.tick` → `submit_child` → hàng đợi Job | `agent.advance` |

Bốn phép đo, không phải suy luận:

1. `sinh_job()` (`dieu_khien.py:28`) — thứ quyết định một node có sinh Job không
   — **chỉ** được gọi bởi `bao_gia.py:51`, tức đường **báo giá**.
2. `thi_hanh.py` chỉ có `tao_run` · `ghi_chuyen` · `anh_chup_hien_tai`: nó **ghi**
   trạng thái, không **đẩy** nó.
3. Không tệp nào trong `platform_core/workflow/` tạo một `Job`.
4. `job_runner.py` và `server/` không nhắc tới `workflow`.

⇒ Tầng V2 định nghĩa, phiên bản hoá, băm tất định, báo giá và ghi trạng thái
được — nhưng **không có bộ thi hành**. Đường sống là executor Agent (M1).

⚠️ Đọc mã không nói được điều đó: cả hai tầng đều trông như đang sống, có model,
   có test, có route. Đúng dạng "năng lực có, không ai đi trên đường".

⇒ **"Dựng lại hành vi bot bằng Nodes" hôm nay nghĩa là `plan` của AgentRun,
  không phải `graph` của `WorkflowVersion`.**

---

## 2. Bốn App đều tới được executor

`discover_tools()` trả 19 tool, đủ cả bốn (`transcript.run`, `audio_pause.run`,
`prompt_canh.run`, `video_assembly.run`), đúng `job_type`. Điều kiện **cần**.

---

## 3. Chạy thật: mỗi App là một node, và dữ liệu chảy giữa hai node

Đường đi đúng như production: **cấp credit → báo giá → phê duyệt (giữ tiền) →
tick**. Mỗi App sinh **đúng một** Job mang `job_type`, `step_id`, `plan_id` và
`owner_id` do máy chủ tiêm.

```
s1 transcript.run    params.audio    = $input.audio  ->  "artifact://a.wav"
s2 prompt_canh.run   params.kich_ban = $s1.text      ->  "loi thoai"
```

Một App chạy một mình chỉ chứng minh nó là một job. Thứ thay được bot là **đầu
ra bước trước thành đầu vào bước sau** — ở bot cũ, đó là việc mã bot-local làm.

---

## 4. Hai thứ phép kiểm đầu của tôi làm SAI, và cả hai đáng ghi

### 4.1 Cổng ngân sách là `estimated`, không phải `budget_max`

Bản đầu đặt thẳng `run.status = AGENT_RUNNING` + `budget_max`, và **không job
con nào được tạo**. Lý do đọc từ chính checkpoint executor ghi: `fault: policy`,
"Không đủ phần ngân sách đã duyệt". `budget.ensure_can_spend` nói thẳng: thực
chi không bao giờ được vượt **khoản đã GIỮ**.

⭐ Ở bản sai ấy **`prompt_canh.run` vẫn qua** trong khi ba App kia trượt — vì
`credit_cost` của nó là **0 có chủ đích** (tiền thu ở tầng `runtime_noi_bo` theo
từng lượt gọi model). Một lỗi ở cổng ngân sách **không biểu hiện đều** trên bốn
App; thử mỗi App ấy thì phép kiểm xanh trên một đường đang hỏng.

### 4.2 Trạng thái bước là HÀM của hàng đợi job

Bản đầu ghi thẳng `run.checkpoint` để nối sang `s2`, và `s2` vẫn không chạy:
`_sync_children` **dựng lại** checkpoint từ các Job con mỗi nhịp. Thiết kế đúng
— và một phép kiểm ghi tắt sẽ **chứng minh một đường production không đi**.

---

## 5. Còn thiếu để đóng Phase 12

| | Hạng mục | Vì sao chưa |
|---|---|---|
| a | chạy `handle()` thật của bốn App qua worker | cần GPU + tệp media thật |
| b | Drive/Sheets connector | Phase 12 nói **không** nhét vào 4 App; phải là App/Tool riêng, chưa audit |
| c | browser/Canvas E2E | Canvas nối vào tầng **không có executor** — phải quyết trước |
| d | failure cases qua worker | phụ thuộc (a) |

⛔ Mục (c) là một **quyết định kiến trúc**, không phải việc còn tồn: nối Canvas
vào tầng V2 nghĩa là phải viết bộ thi hành cho nó — tức sửa `platform_core/`,
thứ mà `CLAUDE.md` luật 20 bảo phải **dừng lại và nói rõ vì sao**. Đây là chỗ nói.
