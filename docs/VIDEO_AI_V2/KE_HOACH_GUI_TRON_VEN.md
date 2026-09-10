# Kế hoạch dựng GUI `lttvideo` trọn vẹn — lấy tinh tuý từ Seedance Studio

**Ngày**: 2026-09-07 · **Nhánh**: `phien/video-v2-wangp` · **Không cần pod.**

---

## 0. Vì sao làm bây giờ, và vì sao nó KHÔNG chờ pod

`B-2` chứng minh bộ `py3.11/cu130` trên pod **không nhân nổi hai ma trận**
(§5e của `PLAN_V1_CHI_TIET.md`: cuBLAS vỡ ở cả `bf16`/`fp16`/`fp32`). Đó là
lỗi tầng thư viện, **không liên quan một dòng nào** của app.

⇒ Hai mạch chạy song song, không mạch nào chặn mạch nào:

| Mạch | Nội dung | Cần pod |
|---|---|---|
| **GUI** *(tài liệu này)* | dựng giao diện trọn vẹn | ❌ |
| **Ngăn xếp** | dựng lại môi trường về `cu128/py310` | ✅ |

---

## 1. Khoảng cách hiện tại — đo, không cảm tính

| | `lttvideo` hôm nay | `taovideo` (Seedance) |
|---|---|---|
| Template | 200 dòng | 111 dòng **đặc** + 60 dòng JS |
| Route | 4 endpoint | **8** endpoint |
| Bố cục | một biểu mẫu dọc | studio 3 khoang |
| Thư viện | danh sách 12 mục, không lọc | tab + đếm + 3 bộ lọc + lưới/danh sách |
| Tài nguyên của user | không có | kho tái dùng, có vai trò + @tên |
| Báo giá | tĩnh, dựng lúc render | sống, tính lại mỗi lần đổi |
| Tiến độ | **0% suốt 20 phút** | thanh tiến độ theo job |

⭐ **Điểm mấu chốt: `.tv-*` đã nằm trong `server/static/ltt.css`.** Style đã
   chuẩn hoá sẵn ở tệp dùng chung, đã deploy, đã cache-bust. Dựng lại giao diện
   này **không cần viết một dòng CSS nào** — đó là lý do việc này rẻ hơn vẻ ngoài
   của nó rất nhiều.

---

## 2. Lấy gì, bỏ gì — và lý do từng thứ

### 2.1 Lấy nguyên

| Tài nguyên | Cơ chế | Vì sao hợp với ta |
|---|---|---|
| `{% block page_mode %}immersive{% endblock %}` | `base.html:119` đổi `<main>` thành `page--immersive` | khoang toàn màn cho studio |
| Khung `tv-studio` 3 khoang | nav icon · bảng tạo · thư viện | CSS có sẵn |
| Drawer + scrim mobile | `inert` · `aria-expanded` · quản lý focus · `Escape` | phần khó nhất đã viết xong và đúng chuẩn trợ năng |
| Lưới ⇄ danh sách | `localStorage['ltt.taovideo.view']` | đổi khoá thành `ltt.lttvideo.view` |
| Tab trạng thái + số đếm | đếm trên `Job.status` | ta cũng dùng bảng `Job` của nền tảng |
| Thẻ kết quả | `<video>` xem tại chỗ · badge · thanh tiến độ · prompt · lỗi | thay `/taovideo/v/` bằng `/lttvideo/video/` đã có |
| **Kho tài nguyên theo user** | dựng từ **chính lịch sử job của chủ**; `storage_key` phải khớp job của họ | xem §2.3 |
| Ô đính tham chiếu | xem trước tại chỗ · **vai trò** mỗi tệp · **@tên gợi nhớ** · trần 4 | ánh xạ thẳng sang `image_start`/`video_guide` |
| Báo giá sống bằng htmx | `hx-trigger="load, change from:#sdform"` + trạng thái bận | ta đã có `cost.uoc_credit` |
| Hộp thoại Nâng cấp | `<dialog>` báo giá **trước** khi xác nhận | ta đã có `upscalevideo` |
| Lịch sử prompt | 10 prompt gần nhất, không trùng | đọc từ `Job.params` |

### 2.2 KHÔNG lấy — và vì sao

| Bỏ | Lý do |
|---|---|
| `assets.py` (232 dòng) | API ký của BytePlus/Ark. Đặc thù nhà cung cấp, ta không có |
| `modelark.py`, `quotes.py` | bảng giá theo model của nhà cung cấp. Ta **giá phẳng 30 credit/giây** |
| Thẻ chọn model `01 Model` | ⛔ **`A1` đã khoá**: người dùng không chọn model. Đây là ranh giới kiến trúc, không phải thiếu sót |
| `translate.py` (dịch prompt) | phụ thuộc LLM ngoài. Cân nhắc lại ở pha 5 qua `ltt_llm` nội bộ |

### 2.3 🔴 Kho tài nguyên theo user — chép **cơ chế**, không chép bảng

Seedance **không** có bảng tài sản riêng. Nó dựng danh sách từ chính lịch sử
job của chủ (`routes.py:81-95`), và khi nhận lại `storage_key` từ trình duyệt
thì **đối chiếu với đúng danh sách ấy**:

```python
allowed = {a["storage_key"]: a for a in _jobs_cua_toi_for_user(user_id)}
if allowed.get(key) is None or not storage.exists(key):
    raise ValueError('Tài sản đã lưu không hợp lệ hoặc không còn tồn tại.')
```

⭐ Chú thích gốc nói thẳng vì sao: *"browser không được tự khai storage key"*.
   Đây là cùng một họ bảo vệ với `_KHUON_KHOA` của ta — **danh sách trắng dựng
   từ dữ liệu của chủ**, không phải bộ lọc chuỗi.

⚠️ Với ta có một khác biệt phải xử lý: **`C2` xoá nội dung sau 3 ngày.** Nên
   `storage.exists(key)` sẽ `False` với tài sản cũ, và giao diện phải nói *"đã
   hết hạn"* chứ không im lặng bỏ qua.

---

## 3. Kiến trúc màn hình

```
┌─────┬────────────────────┬──────────────────────────────────┐
│ nav │  BẢNG TẠO          │  THƯ VIỆN                        │
│     │                    │                                  │
│  ▶  │ 01 Mô tả           │  [Tất cả 12][Đang chạy 1][Xong 9]│
│  ▣  │    + @tham chiếu   │  [lọc: tỉ lệ ▾][sắp xếp ▾] [▦][☷]│
│  ▦  │ 02 Đính media      │  ┌────────┐ ┌────────┐           │
│  ⚙  │    vai trò/@tên    │  │ video  │ │ ▓▓▓░ 62%│          │
│     │ 03 Tài sản đã lưu  │  │ ✓ Xong │ │ ● Đang  │          │
│     │ 04 Thiết lập       │  │Biến thể│ │  Huỷ    │          │
│     │    tỉ lệ · độ dài  │  └────────┘ └────────┘           │
│     │ ─────────────────  │                                  │
│     │ 150 credit  [Tạo]  │                                  │
└─────┴────────────────────┴──────────────────────────────────┘
```

**Khác Seedance ở ba chỗ, mỗi chỗ một lý do:**

1. **Không có khoang `01 Model`** — `A1` khoá.
2. **Thêm dải trạng thái máy** — Seedance gọi API luôn sẵn sàng; máy của ta
   **bật theo nhu cầu** (`B1`) và lượt đầu chờ tới 900 giây. Im lặng ở đây là
   người dùng tưởng hỏng.
3. **Thêm nhãn hạn giữ 3 ngày** — xem `F3` bên dưới.

---

## 4. Ba lỗi phải sửa **cùng lúc** với việc dựng

Không phải việc trang trí. Đây là lỗi chặn.

### F1 — `handle()` không hoàn thành nổi **một job thật nào** ⛔

| Mắt xích | Sự thật |
|---|---|
| `/result/{job}` phía cầu nối | **chặn-chờ** tới khi xong (~20 phút) |
| `client.result()` gọi với | `timeout=30.0` |
| `timeout` ấy là gì | tham số `urllib.urlopen` → timeout **socket** mỗi lần đọc |

⇒ Mọi job thật ném `socket.timeout` sau **30 giây**.

Test không thấy vì chúng tiêm `_client` giả trả về ngay. **Cùng một loại mù** đã
che lỗi `tools.video_cloud`: đường thật chưa từng chạy.

Dấu vết còn nguyên: **`NHIP_HOI_S = 5.0` được khai và không dùng ở đâu cả** — nó
ghi lại một ý định chưa bao giờ được nối dây.

### F2 — người dùng nhìn 0% suốt hơn 20 phút

`handle()` nhận `ctx` nhưng **không gọi `ctx.progress()` lần nào**, trong khi
`upscalevideo` dùng ở 5 chỗ. Cầu nối đã trả sẵn `phase` · `current_step` ·
`total_steps` · `giay_da_chay`.

⭐ **F1 và F2 chung một bản sửa** — thay lời gọi chặn-chờ bằng vòng hỏi tiến độ:

```python
job_id = client.submit(tham_so)
while True:
    time.sleep(NHIP_HOI_S)
    p = client.progress(job_id)          # da co san
    if ctx is not None:
        ctx.progress(_phan_tram(p), _loi_nhan(p))
    if p.get("xong"):
        break
kq = client.result(job_id)               # gio tra ve NGAY
```

Một thay đổi, hai lỗi, và nó biến `NHIP_HOI_S` từ hằng số chết thành hằng số
đang làm việc.

### F3 — không ai báo video chỉ giữ **3 ngày**

`C2` chốt 3 ngày; nền tảng mặc định **30 ngày**
(`platform_core.job_content.RETENTION_DAYS`). Người dùng quen nền tảng sẽ tưởng
30 và mất video. Giao diện hiện **không có một chữ nào**.

---

## 5. Thứ tự thi công

Mỗi pha kết thúc bằng: `--vong-lap` (15 giây) → soi trình duyệt thật → ghim test.
**Một** lượt gate đầy đủ ở cuối cùng, không phải mỗi pha.

### ✅ Pha 1 — Sửa đường job *(F1 + F2)* · không đụng giao diện — **XONG 07/09**

Kết quả: 10 phép kiểm mới ở `test_735`, **đỏ trước / xanh sau**. Cộng hai phép
kiểm ở `test_725` cho cờ `xong` phía cầu nối.

🔴 **Một sai lầm của chính tôi, đáng ghi lại.** Bản sửa đầu chỉ thoát vòng lặp
   khi thấy cờ `xong` — một cờ mà cầu nối **chưa gửi**. Nó treo vô hạn ngay
   trên bộ test. Viết mã cho hợp đồng mình *định* làm thay vì hợp đồng *đang
   có* là cách chắc chắn để hỏng ở chỗ không ai kiểm.

   ⇒ Bản đúng có **hai lối ra**: cờ `xong` *(rẻ, khi cầu nối đã nâng cấp)* và
     `result()` trả về được *(đúng với cầu nối hôm nay)*.

⭐ Căn cứ cho cờ `xong` lấy từ thượng nguồn chứ không phỏng đoán:
   `shared/api.py:379` cho thấy `iter()` chỉ `break` khi `_closed.is_set()`,
   còn hết giờ thì `continue`. Nên **thoát vòng `for` nghĩa là job đã xong**.
   Cờ đặt trong `finally`, và `/progress` còn hỏi thẳng `events.closed` làm
   nguồn thứ hai.


- `jobs.py`: vòng hỏi tiến độ, dùng `NHIP_HOI_S`, gọi `ctx.progress()`
- ánh xạ pha WanGP → phần trăm: `encoding_text` → 5% · `denoising` →
  `5 + 85*current_step/total_steps` · `encoding_video` → 92% · kéo tệp về → 96%
- **Test**: client giả **chậm** (trả tiến độ nhiều nhịp rồi mới xong) — bản cũ
  phải **đỏ** vì timeout
- ⭐ Đây là pha quan trọng nhất. Không có nó, mọi thứ còn lại là vỏ.

### Pha 2 — Khung studio
- `page_mode immersive` + `tv-studio` 3 khoang + drawer/scrim + lưới/danh sách
- route `""` truyền thêm: `job_counts`, `active_status/sort/aspect`, `jobs[]`
- **Test**: dựng template với `duoc_dung=True` và danh sách job giả

### Pha 3 — Thư viện
- tab trạng thái + đếm · lọc tỉ lệ/sắp xếp · thẻ có `<video>` · thanh tiến độ
- nút **Biến thể** (nạp lại tham số cũ vào bảng tạo) · **Tải** · **Nâng nét** ·
  **Nhật ký** (`/jobs/{id}`)
- trạng thái rỗng
- ⚠️ Thẻ phải phân biệt **hết hạn** với **chưa từng có** — `C2` xoá sau 3 ngày

### Pha 4 — Bảng tạo đầy đủ
- ô đính media: xem trước · **vai trò** (khung đầu / tham chiếu / video dẫn) ·
  **@tên gợi nhớ** · trần 4
- **kho tài sản đã lưu** (§2.3)
- lịch sử prompt
- **báo giá sống**: endpoint mới `POST /lttvideo/uoc-gia` trả HTML mảnh cho htmx
- **dải trạng thái máy**: `GET /lttvideo/trang-thai-may` → *"Máy đang tắt, lượt
  đầu mất thêm ~5 phút để bật"*

### Pha 5 — Nâng nét đúng chuẩn Seedance
- `<dialog>` + `POST /lttvideo/nang-net-bao-gia` → báo giá **trước** khi xác nhận
- thay biểu mẫu post thẳng hiện tại

### Pha 6 — Nhãn hạn giữ *(F3)* + soát trợ năng
- nhãn 3 ngày ở thẻ kết quả và dưới nút Tạo
- soát: `aria-live` cho báo giá · nhãn cho mọi ô · bẫy focus của drawer

---

## 6. Endpoint sau khi xong

| Đường | Có chưa | Việc |
|---|---|---|
| `GET /lttvideo` | ✅ | mở rộng ngữ cảnh |
| `POST /lttvideo/tao` | ✅ | thêm tham chiếu + tài sản đã lưu |
| `GET /lttvideo/video/{key}` | ✅ | giữ nguyên |
| `POST /lttvideo/uoc-gia` | ❌ | báo giá sống |
| `GET /lttvideo/trang-thai-may` | ❌ | dải trạng thái pod |
| `POST /lttvideo/nang-net-bao-gia` | ❌ | báo giá upscale |
| `POST /lttvideo/nang-net` | ❌ | xác nhận |

⚠️ **Trần hợp đồng app: 900 dòng / 30 handler** (`tools/lint_app_contract.py`).
`routes.py` đang 350 dòng. Bảy endpoint vẫn dư chỗ, **nhưng** nghiệp vụ phải nằm
ở `features.py`, không rơi vào route — đó đúng là cái bẫy đã sinh ra một tệp
route 1.799 dòng ở app khác.

---

## 7. Không làm trong đợt này

Tab Ảnh/Giọng nói/Nhạc · LoRA · VACE mask · nối video >15s · dịch prompt ·
chọn model · bán ra ngoài *(giấy phép WanGP §5.2(g))*.

---

## 8. Nghiệm thu

1. `--vong-lap` xanh sau mỗi pha
2. Playwright trên bản kiểm cô lập (`tools/lttvideo_browser_server.py`, cổng
   8137): 0 lỗi console · 0 request hỏng · mỗi luồng đi hết
3. `tools/lint_app_contract.py` PASS
4. **Một** lượt `tools/gate.py` đầy đủ ở cuối
5. ⛔ Còn **thiếu** cho tới khi deploy: kiểm trên `https://app.lttstudios.com`
   (`CLAUDE.md` mục 5b). Loopback bỏ qua Cloudflare, và kho này **đã** dính một
   lần CSS cũ được phục vụ 4 tiếng.
