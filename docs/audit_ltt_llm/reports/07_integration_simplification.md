# Prompt 07 — Integrated Architecture & Evidence-Based Simplification

**31/08/2026.** Ownership: G01–G16.

---

## 1. Kiến trúc sau các thay đổi (G01)

```
khach --khoa LTT--> /api/v1 (may A)
   |
   +-- /quotes -> /jobs -------> hang doi job -> worker ----+
   +-- /chat/completions  SYNC_BILLED --------------------+ |
   +-- /messages | /responses  STREAM --------------------+ |
                                                          | |
   admission.acquire  ->  thanh_toan.giu_cho  ->  db.commit  ->  luong_vlm.mo
                                                          | |
                                            http://192.168.2.66:8299 (may B)
                                              gioi_han (1 suat, co HAN GIU)
                                              trong_tai (biet tai NAO la cua ta)
                                              don_dep -> llama-swap:8280
                                                          -> llama-server
   quyet toan: DemToken (doc usage doc duong) -> quyet_toan_hoac_hoan
```

**Khác baseline ở bốn chỗ**, tất cả do chương trình này:

| | Baseline | Nay |
|---|---|---|
| suất của cổng B | rò được, giữ vĩnh viễn | `BackgroundTask` + **hạn giữ 1.200 s** + `giu_lau_nhat_giay`/`da_thu_hoi` |
| trọng tài GPU | quy tải của ta cho ComfyUI | biết `model_cua_ta_dang_chay` |
| máy A báo bận | vứt lý do của B, không đếm `CAPACITY_REFUSED` | mang lý do đi theo + đếm + ghi log |
| `gate.py` | bước bỏ qua trông như bước đạt | ba trạng thái, dòng RESULT tự khai |

---

## 2. Sở hữu bất biến (G02) — phân loại từng chỗ trùng

| Bất biến | Chủ | Chỗ trùng | Phân loại |
|---|---|---|---|
| ngữ cảnh / trần token | `apps/ltt_llm/ngan_sach.py` | `llm_gateway/config.py`, `catalog.py`, `providers.py`, `examples.py`, `tools.py` | **bản sao dẫn xuất có phép kiểm chống trôi** — `test_334` (40 phép kiểm). Không thể dùng `import` vì `platform_core`/`server` **không được** phụ thuộc `apps/` |
| đồng thời | `llm_gateway/gioi_han.py` (=1) | `ngan_sach.DONG_THOI_MAY_B` | **bản sao có phép kiểm** — `test_dong_thoi_cua_ta_khong_vuot_may_B` |
| bận / lỗi | máy B sinh, máy A **dịch** | — | **phòng thủ nhiều lớp CẦN THIẾT**: B trả 429 (bận ≠ hỏng) để A không disable khoá |
| nhận vào | `admission` (A) + `gioi_han` (B) | — | **hai tầng KHÁC nhau**, xem §3.1 |
| usage / tiền | `cong_vlm.doc_su_dung` + `DemToken` | — | **một nguồn, hai cách đọc** — không phải hai SSOT |
| cấu hình runtime | `C:\ProgramData\LTTLlm\gateway.env` | `llama-swap.yaml` | ⚠️ **hai tệp, hai vòng đời**; nay deploy có cảnh báo |

---

## 3. Chứng minh xuyên tầng (G03)

### 3.1 Nhận vào + cổng **KHÔNG** tạo hàng đợi kép

`admission` (A) giới hạn theo tài khoản; `gioi_han` (B) giới hạn 1 lượt/GPU. Nếu
A nhận 5 mà B chỉ chạy 1, bốn lượt kia **không xếp hàng ở đâu cả** — chúng bị
**từ chối ngay**:

```
A ma=200 1,59s     B ma=429 0,05s retry_after=15
```

⇒ Hai tầng, **không phải hai hàng đợi**. Chờ vô hình còn tệ hơn một cái 429 rõ
ràng, và ở đây không có chờ vô hình.

### 3.2 Bận **không** kích hoạt disable provider

`luong_vlm` khi gặp 429 **không** gọi `api_pool.danh_dau_loi`. Bằng chứng sống:
sau **89 lượt hỏng** ngày 31/08, khoá `ltt_llm` vẫn `status=active`.

⇒ Bẫy D-005 (*"một tối chạy video sẽ tự tắt vĩnh viễn model nhà"*) **đóng**.

### 3.3 Thử lại **không thể** thu tiền hai lần

```
credit.giu_cho()  ->  _giu_cho_da_niem_phong(job_id)  ->  hap thu, ghi job_event
                  ->  _khoa_so_du_user()  TRUOC khi doc so du
```

Hai lớp: **niêm phong theo `job_id`/`request_id`** (giữ chỗ thứ hai không tạo
bút toán mới) và **khoá dòng trước khi đọc số dư** (check-then-write thành
nguyên tử, hết double-spend).

⭐ Và nó **hấp thụ chứ không giết job**: phần chênh là variance nội bộ. Ném lỗi ở
đây sẽ giết job của khách vì một khác biệt làm tròn một credit — tệ hơn hẳn thứ
nó định bảo vệ.

### 3.4 Quyết toán stream nhất quán

`DemToken` đọc `usage` **thật** của thượng nguồn, quét mọi khối và giữ max — cần
thiết vì cửa Anthropic đặt `input_tokens` ở **đầu** luồng (đo Prompt 05).

### 3.5 Trần A/B/client khớp theo **hợp đồng**

131.072 (engine) · 96.256 (trần vào cứng) · 88.555 (công bố) — ba số cho ba
việc, và `test_334` giữ cả ba khớp qua sáu tệp.

### 3.6 Alias **không** rò sang tầng sai

Chứng minh bằng phép đo, không bằng đọc: gửi `model:"ltt_llm"` thẳng vào máy B
⇒ **404** kèm `["qwen38-api","qwen38-vision"]`. Máy B **không biết alias** — ánh
xạ nằm đúng một chỗ (`features.py:39`).

### 3.7 Deploy **một máy** thất bại an toàn — chứng minh bằng việc đã làm

Hôm nay deploy **A trước, B sau, cách nhau 20 phút**; rồi deploy **B một mình**
lúc 21:30 trong khi A không đổi. Cả ba lượt dịch vụ đều chạy.

⇒ Hai máy **không** đòi phiên bản khớp nhau. Đó là bằng chứng thật, không phải
suy luận — và nó có được vì hôm nay tình cờ phải làm đúng thứ tự ấy.

---

## 4. Ứng viên đơn giản hoá (G04) — **KHÔNG XOÁ GÌ**

| Ứng viên | Quyết định | Vì sao |
|---|---|---|
| Sáu bản sao hằng số ngữ cảnh | **KEEP** | Không gộp được: hợp đồng app cấm `platform_core` phụ thuộc `apps`. Phép kiểm **là** cơ chế ghép |
| `admission` (A) + `gioi_han` (B) | **KEEP** | Hai tầng khác nhau, không phải trùng lặp — §3.1 |
| `_dem_toi_thieu` đường lùi trong `trong_tai` | **KEEP** | Cần khi `render_gateway` không deploy cùng |
| `DemToken` bên cạnh `doc_su_dung` | **KEEP** | Hai hình dạng luồng khác nhau cho cùng một nguồn |
| Ba cửa streaming/sync | **KEEP** | Codex nói Responses, Claude Code nói Messages — bỏ cửa nào là bỏ một client |

⛔ **Không có ứng viên xoá nào đạt ngưỡng.** `OPERATING_CONTRACT §5`: không
`CHANGE` chỉ vì "trông trùng". Mọi chỗ trùng ở đây đều có lý do đã được chứng
minh, và phần lớn đã có phép kiểm giữ.

---

## 5. Baseline → nay

| Chiều | Baseline | Nay | Δ |
|---|---:|---:|---:|
| Correctness & invariants | 16 | 17 | +1 |
| Money/admission/failure | 13 | 14 | +1 |
| Model quality & tool/context | 6 | 12 | **+6** |
| Performance/resource | 7 | 11 | **+4** |
| Reliability/recovery | 7 | 8 | +1 |
| Security boundaries | 8 | 9 | +1 |
| Observability/operations | 4 | 5 | +1 |
| Tests/evidence | 4 | 5 | +1 |
| Maintainability/SSOT | 4 | 5 | +1 |
| **TỔNG** | **69** | **86** | **+17** |

⛔ **86 không phải điểm phát hành.** Ba phase còn nợ phần khó nhất: bảy cửa sổ
sự cố của `02`, F01–F28 của `06`, canary client thật của `05`. Điểm phản ánh
**thứ đã chứng minh**, không phải thứ đã làm xong.
