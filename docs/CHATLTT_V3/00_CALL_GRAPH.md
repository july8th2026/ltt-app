# P00 — ĐỒ THỊ LỜI GỌI THẬT

*Mọi mũi tên có `tệp:dòng`. Không mũi tên nào vẽ từ trí nhớ.* [S] toàn bộ.

---

## 1. Đường TEXT — từ trình duyệt tới máy B và ngược lại

```
frontend/chatltt/src/SoanThao.tsx  →  api.ts
  │  POST /chatltt/api/hoi-thoai/{conv_id}/luot   {text, model_alias, parent_id?,
  │                                                tao_lai_cua?, reasoning_effort, anh[]}
  ▼
routes/_p_luot.py:33  gui()
  ├─ kiem_csrf()                       _chung.py:44   (X-CSRF-Token hoặc thân)
  ├─ require_login / uid()             _chung.py:20
  ▼
services/luot.py:105  bat_dau()
  ├─ H.lay_hoi_thoai()                 hoi_thoai.py   (MỌI truy vấn có user_id — IDOR chặn ở service)
  ├─ trần 200.000 ký tự                luot.py:44     TRAN_KY_TU_LUOT
  ├─ _khoi_anh() → anh_vao.la_khoa_anh_vao()          (kiểm SỞ HỮU, không tin giao diện)
  ├─ H.them_thong_diep(user)  +  H.them_thong_diep(assistant, status="streaming")
  ├─ S.mo_execution(tool_name="text.chat", mode="stream")   su_kien.py:47
  └─ db.commit()  →  202 {conversation_id, user_message_id,
                          assistant_message_id, execution_id}
  ▼
routes/_p_luot.py:59  LUOT.khoi_chay_nen()  →  threading.Thread (daemon)
  ▼
services/luot.py:196  chay()          ── luồng nền, phiên CSDL RIÊNG ──
  ├─ H.duong_toi_la()                              đường gốc→cha
  ├─ dung_ngu_canh(duong, doc_anh=…)   luot.py:66  chỉ khối `text` (+`image` nếu alias khai reads_images)
  │    └─ doc_anh_duoc()               luot.py:150 đọc `constraints.reads_images` — KHÔNG suy từ tên
  ├─ params = {"model", "messages"}    luot.py:223  ⛔ KHÔNG có `tools`
  ├─ params["reasoning_effort"]        luot.py:228
  ▼
platform_core/runtime_noi_bo/luong.py:483  mo_luong()
  ├─ than["stream"]=True; stream_options.include_usage=True      luong.py:512-517
  ├─ chuan_bi()                                    luong.py:166
  │    ├─ tim_tool("text.chat") → ToolSpec         runtime_noi_bo/tim.py
  │    ├─ executor.aliases() — alias phải hợp lệ   (public_api/executor.for_tool)
  │    ├─ gui["model"] = executor.model_id(alias)  ⭐ alias→id nội bộ NGAY TRƯỚC khi rời nền tảng
  │    ├─ admission.acquire(resource="llm_remote", slots=1)  🔴 MỘT SUẤT TOÀN NỀN TẢNG
  │    ├─ uoc_tin_nhan(than) — **có tính khối `tools`**       luong.py:123
  │    ├─ tran_token_ra() → kẹp + GHI LẠI vào thân gửi        luong.py:129, 205
  │    ├─ thanh_toan.giu_cho_luot()  → giữ credit theo trần ước
  │    └─ db.commit()                🔴 CHỐT TRƯỚC KHI CHẠM MODEL
  ├─ yield response.started {request_id, model, credit_giu}    luong.py:521
  ├─ mo_thuong_nguon()                             luong.py:274  (ngân sách 75 s)
  │    └─ llm/luong_vlm.mo(duong="/v1/chat/completions")  →  llm_gateway :8299
  │         →  llama-swap  →  llama-server (qwen38-api)
  ├─ _DocSSE().nhin(byte)             luong.py:442  đệm tới đủ một dòng `data:`
  ├─ _su_kien_tu_goi(goi)             luong.py:462
  │    ├─ delta.reasoning_content → reasoning.delta            luong.py:471
  │    ├─ delta.content           → response.delta             luong.py:474
  │    └─ delta.tool_calls        → **tool_call.delta**        luong.py:477
  ├─ yield usage.updated                                       luong.py:560
  ├─ yield response.completed | response.failed                luong.py:564-568
  └─ _phat().finally → quyet_toan_luot() → NHẢ SUẤT            luong.py:322
  ▼
services/su_kien.py:63  ap_dung(ex, sk, message)
  ├─ response.delta   → ex.partial_text += …                   su_kien.py:70
  ├─ reasoning.delta  → ex.reasoning_text += …                 su_kien.py:72
  ├─ **tool_call.delta → `pass`**                              su_kien.py:72-73  ⛔ ỐNG BỊ BỊT
  ├─ usage/billing    → ex.usage / ex.credit_*
  └─ trả True nếu là sự kiện KẾT THÚC
  ▼
nen_ghi(1 s hoặc 200 ký tự hoặc kết thúc)  →  db.commit()      su_kien.py:127
  │  ⭐ D6: sự thật ở CSDL, không ở RAM trình duyệt
  ▼
dang_chay.phat(sk)  →  hàng đợi trong tiến trình
  ▼
GET /chatltt/api/luot/{execution_id}/stream    routes/_p_luot.py:128
  ├─ gửi `snapshot` trước (su_kien.snapshot — phần đã có + seq)
  ├─ rồi sự kiện canonical; `: ping` mỗi 15 s khi chờ
  └─ ⭐ SSE là CỬA XEM, không phải cửa chạy — đóng tab không giết lượt (AC-09)
```

**Dừng:** `POST /api/luot/{id}/dung` → `luot.dung()` ghi `status='cancelled'` xuống
CSDL (chắc) **và** đặt cờ trong tiến trình (nhanh) — `luot.py:295`.
Luồng nền đọc lại bằng SELECT vô hướng (`_da_huy_trong_csdl`, `luot.py:186`),
**không** `refresh()` — refresh sẽ đè `partial_text` đang giữ trong bộ nhớ.

---

## 2. Đường ẢNH / TIẾNG — người dùng bấm, model không quyết

```
frontend/chatltt/src/TaoMedia.tsx
  │  POST /chatltt/api/bao-gia   {nang_luc, params}
  ▼
routes/_p_media.py:34  →  services/tao_media.py:47  bao_gia()
  ├─ chinh_sach.kiem_cho_phep(ten)          chinh_sach.py:52  fail-closed
  ├─ nếu speech.ltt và khách CHƯA chọn giọng:
  │    chon_giong.chon()  ⭐ MODEL tự chọn giọng — TỐN 1 CREDIT, và báo giá NÓI RA
  ├─ runtime_noi_bo/job.py:47  bao_gia()
  │    ├─ validate_tool_params (kể cả tuỳ chọn động theo user)
  │    ├─ tool.lane_for(sach) → job_type thật
  │    └─ registry.credit_for(lane, sach)
  └─ → {nang_luc, credit, phien_ban_gia, tham_so, giong?}
  │
  │  ── NGƯỜI DÙNG XÁC NHẬN TRONG TRÌNH DUYỆT ──  ⛔ không bền, không nối lại được
  │
  │  POST /chatltt/api/hoi-thoai/{id}/tao   {nang_luc, params, credit_da_bao}
  ▼
routes/_p_media.py:53  →  services/tao_media.py:120  tao()
  ├─ BÁO GIÁ LẠI; lệch với `credit_da_bao` ⇒ TỪ CHỐI    tao_media.py:135
  ├─ H.them_thong_diep(assistant, status="queued")
  ├─ S.mo_execution(mode="job")
  ├─ runtime_noi_bo/job.py:80  nop_job()
  │    └─ job_submit.submit_with_credit(owner_id=user_id ÉP, quoted_credit,
  │                                     dedupe_key="chatltt:{ex.id}", admission_*)
  └─ db.commit() → {message_id, execution_id, job_id, credit}
  ▼
  ⭐ KHÔNG có "đẩy" từ worker sang web ⇒ client HỎI THEO NHỊP (Q87: 2 s, backoff khi lỗi)
  GET /chatltt/api/luot/{id}/trang-thai   routes/_p_media.py:78
  ▼
services/tao_media.py:203  dong_bo()   (an toàn gọi nhiều lần)
  ├─ job_history.get_owned(db, user_id, job_id)     ⭐ kiểm sở hữu
  ├─ done   → _khoi_artifact() đọc `tool.returns` → khối image/audio
  │            + billing.updated {thu, hoan}
  ├─ error/cancelled → execution.failed + hoàn ĐỦ
  └─ queued → execution.progress + `cho_tai_nguyen` (giây còn lại từ job.next_run_at)
  ▼
GET /chatltt/tai-san/{key:path}    routes/_p_media.py:122
  └─ tao_media.kiem_so_huu_khoa()   tao_media.py:280
       ⛔ kiểm TỪNG ĐOẠN trước khi kiểm tiền tố — chỉ so tiền tố thì
          `anhnoibo/<uid>/../../secrets/app.env` LỌT (test_625 bắt ở lượt đầu)
```

---

## 3. Sự thật khi tải lại trang

```
GET /chatltt/api/hoi-thoai/{conv_id}     routes/_p_hoi_thoai.py:36
  └─ hoi_thoai.su_that()
       ├─ danh sách message phẳng (cây dựng lại bằng `parent_id`, không có cột children)
       ├─ `current_leaf_id` ở CSDL — reload giữa nhánh cũ quay lại ĐÚNG nhánh (AC-07)
       └─ với execution đang chạy: `execution.partial_text` (chưa `dong_bo_khoi_text`)
```

---

## 4. Nơi V3 phải cắt vào — bốn điểm, không hơn

| # | Điểm cắt | Tệp:dòng | Việc |
|---|---|---|---|
| **1** | dựng `params` | `luot.py:223` | thêm `tools` (chiếu từ registry) + `parallel_tool_calls` |
| **2** | tiêu thụ sự kiện | `su_kien.py:72` | gộp mảnh `tool_call.delta`, ghi `chatltt_step` |
| **3** | sau khi luồng cạn | `luot.py:230-262` | nếu có tool → thi hành → vòng model kế, thay vì kết thúc lượt |
| **4** | chính sách | `chinh_sach.py` | từ allowlist *hiển thị* 3 năng lực → thêm **lớp chính sách** + phép chiếu schema |

⭐ Bốn điểm này đều nằm **trong `apps/chatltt/`**. Không điểm nào buộc sửa
`platform_core/runtime_noi_bo/luong.py` — nó đã nhận `params` tuỳ ý và đã phát
`tool_call.delta`. Đó là bằng chứng mạnh nhất cho phương án **A** ở ADR P02.

⛔ Ngoại lệ duy nhất có thể buộc chạm lõi: **R1** (một suất LLM) nếu ADR chọn
phương án B. Đó là lý do R1 phải được quyết ở P02 chứ không phát hiện ở P03.
