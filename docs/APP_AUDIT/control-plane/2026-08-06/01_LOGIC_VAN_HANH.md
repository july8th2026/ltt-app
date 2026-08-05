# 01 — Logic vận hành và phân tầng

## 1. Sơ đồ phụ thuộc thực tế (đo, không phải theo thiết kế)

```
apps/<slug>/          ──> platform_core/   (registry, jobs, credit, storage)
      │                        │
      └──> server/*            └──> server.auth.password_hashing   ← NGƯỢC
           (deps, session,          (platform_core/users.py:25)
            csrf, templating)
server/services/*     ──> core/            (di sản desktop, 15.668 dòng)
```

## 2. Điểm mạnh — nói trước vì chúng thật

**Registry là hợp đồng thật, không phải quy ước miệng.** `platform_core/registry.py`
quét `apps/*/manifest.py` và từ chối ngay lúc nạp khi: slug trùng, route_prefix
trùng, job_type trùng giữa hai app, tool name trùng, khai `job_types` mà thiếu
`credit_cost`, tiền tố bảng trùng, hay bảng sai tiền tố. Mỗi luật đều kèm lời
giải thích *hậu quả nếu không chặn*. Có test chốt rằng **tên app không được viết
cứng trong `platform_core/`** — và nó đã bắt tôi vi phạm trong phiên trước.

**Tiền đi qua đúng một đường.** `submit_with_credit` giữ chỗ credit trong cùng
transaction với việc nộp job, nên job và credit cùng thành hoặc cùng bại. Giá tra
theo `job_type` qua registry, không app nào tự đặt giá cho mình.

**Worker phân việc theo `job_type` chứ không theo `app_slug`.** Nhờ đó một app
đặt hàng job của app khác là hợp lệ và tính đúng giá — chính là thứ cho phép
OMMI dùng lại engine ảnh mà không dựng engine thứ hai.

**Một app lỗi không làm sập nền tảng.** `discover()` bắt lỗi từng app, ghi lý do
và đánh dấu `enabled=False`; bạn vẫn vào được hệ thống để xem app nào hỏng.

**Không có `except:` trần ở đâu trong toàn bộ `apps/`, `platform_core/`, `server/`.**

## 3. Điểm yếu

### 3.1 Một phụ thuộc ngược tầng — P2

`platform_core/users.py:25` import `server.auth.password_hashing`. Nền tảng
không được phụ thuộc vào tầng web: nó biến `platform_core` thành thứ không dùng
được nếu thiếu `server`, và làm sơ đồ tầng thành hình tròn.

Chỉ **một** chỗ, dễ sửa (chuyển hàm băm xuống `platform_core`), nhưng nên sửa
sớm trước khi nó thành tiền lệ.

### 3.2 `apps/upscalevideo/routes.py:267` import `server.admin._is_admin` — P2

Một app gọi vào **hàm private của module admin**. Dấu gạch dưới nghĩa là "không
phải API công khai". Đây là hợp đồng app còn thiếu một thứ: cách hỏi "người này
có phải admin không". App khác hỏi qua `user.role`; app này đi vòng.

### 3.3 `core/` — 15.668 dòng di sản chưa có lối ra — P2

`core/` là mã thời desktop, vẫn được `server/services/*` và `server/settings.py`
dùng. Nó lớn hơn cả `platform_core/` (6.030) và `server/` (7.570) **cộng lại
chưa tới**. Không có tài liệu nào nói phần nào còn sống, phần nào chết, và không
có kế hoạch thu hồi.

Rủi ro thật: người sửa lỗi không biết nên sửa ở `core/` hay `platform_core/`.

### 3.4 Không có tầng nghiệp vụ chuẩn trong hợp đồng app — P1

Hợp đồng quy định `manifest.py` và `routes.py`, ngầm hiểu `jobs.py`. Nhưng
**không nói logic nghiệp vụ nằm ở đâu**. Kết quả đo được: 5 app dùng
`features.py`, 5 app dùng `cost.py`, 1 app dùng `services/`, còn lại nhét thẳng
vào route.

Đây là **nguyên nhân gốc** của mục 3.5, không phải triệu chứng.

### 3.5 Hai file route quá lớn — P1

| File | Dòng | Handler | Miền tách được |
|---|---:|---:|---|
| `apps/prompt_ai_ommi/routes.py` | 1.799 | 64 | 6 nhóm, **đã có tiêu đề phân đoạn sẵn** |
| `apps/agent/routes.py` | 1.313 | 48 | **0 tiêu đề phân đoạn** |

OMMI đã có sẵn 6 dòng `# ── <miền> ──` đánh dấu ranh giới, nên tách thành 6
module là việc cơ học. `agent` không có mốc nào — tách sẽ tốn công đọc hiểu hơn.

**Đây là file tôi tự viết trong phiên trước.** Tôi tách service ra
(`services/resources.py`, `library.py`, `storyboard.py`) nhưng để toàn bộ 64
handler trong một file, và nó trở thành file nguồn lớn nhất repo. Tôi làm đúng
một nửa.

### 3.6 39 `except Exception` trong một file — P2

| App | `except Exception` |
|---|---:|
| **prompt_ai_ommi** | **39** |
| chataistudio | 12 |
| autosubvideo | 5 |
| còn lại | ≤ 3 |

Cả 39 đều của tôi. Ba helper (`_resource_error`, `_library_error`,
`_storyboard_error`) **có re-raise** lỗi máy chủ nên hiện không nuốt lỗi —
tôi đã kiểm. Nhưng chính khuôn mẫu này là chỗ sinh ra lỗi "map mọi exception
thành 400" mà browser bắt được ở phiên trước. Bắt `Exception` quanh **mọi** lời
gọi là lưới quá rộng; bắt đúng loại lỗi nghiệp vụ thì hẹp và tự tài liệu hoá.

## 4. Kiểm thử

| Tầng | Số file test nhắc tới |
|---|---:|
| `server` | 72 |
| `platform_core` | 64 |
| `apps` | 43 |
| setup/deploy | 13 |
| `frontend` | 4 |

Mọi app đều có ít nhất 1 file test; `taovideo` (9) và `agent` (8) nhiều nhất.
`mediatools` và `socialbot` chỉ 1 — nhưng `socialbot` đã đóng băng có chủ ý.

**Điểm yếu:** `frontend` chỉ được 4 file test Python nhắc tới, và test frontend
thật nằm trong `vitest` (51 + 11 + 15 = 77 test). `python -m pytest` **không**
chạy chúng, nên "full regression xanh" không bao gồm frontend. Người chạy gate
phải nhớ chạy `npm test` ở ba thư mục — một bước thủ công dễ quên.
