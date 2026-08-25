# 05 — ĐỊNH VỊ THAY ĐỔI / NƠI CODE NÊN SỐNG

**Ngày:** 2026-08-26 · **Đầu vào:** 00–04

> ⛔ **Không chẻ tệp theo hạn ngạch dòng.** Tiêu chí chính là **Change Locality**:
> code thay đổi *cùng một lý do* nên sống gần nhau. Số dòng chỉ là tín hiệu.

---

## 1. Bảng điểm điểm nóng

Đo bằng `git log --since="90 days ago"` — cột **"sửa cùng với"** là thứ quyết
định, không phải cột "dòng".

| Tệp | Dòng | Handler | Lần sửa | Sửa cùng với | Nhãn |
|---|---:|---:|---:|---|---|
| `platform_core/models.py` | 871 | — | 32 | `job_runner`(13) — trục schema | **KEEP** |
| `platform_core/job_runner.py` | 1.236 | — | 27 | `models`(13), `developer`(8) | **KEEP** |
| `server/app.py` | — | — | 22 | phân tán | **KEEP** |
| `platform_core/registry.py` | 893 | — | 21 | `job_runner`(7) | **KEEP** |
| `server/routes/developer.py` | **1.521** | **32** | 17 | `public_api/tables`(7), `invocation`(5), `examples`(5) | 🔴 **SPLIT_BY_USE_CASE** |
| `server/admin_api.py` | **1.897** | — | 16 | `public_api/tables`(4), `metrics`(3) | 🟡 **LEAVE_UNTIL_CHURN** |
| `apps/autosubvideo/routes.py` | **899** | 25 | 14 | `schemas.py`(5), `jobs.py`(5), test của chính nó(11) | ✅ **KEEP** |
| `apps/taovideo/routes.py` | 645 | 8 | 14 | `upscalevideo/routes`(4) | **KEEP** *(xem A-01)* |
| `server/admin.py` | 1.388 | — | 16 | — | 🟡 **LEAVE_UNTIL_CHURN** |

---

## 2. Ba kết luận, và cái thứ nhất đi ngược trực giác

### ✅ `apps/autosubvideo/routes.py` — 899 dòng, và **giữ nguyên**

899/900 dòng, 25/30 handler. Sát trần đúng một dòng. Trực giác nói "chẻ ngay".

**Số liệu nói ngược lại.** Nó sửa cùng với: test của chính nó (11), `schemas.py`
(5), `jobs.py` (5) — **toàn bộ trong cùng một app**. Đó là định vị thay đổi
**tốt**: một thay đổi về autosubvideo chạm autosubvideo và không chạm gì khác.

⇒ Chẻ nó bây giờ là **chẻ vì con số**, đúng thứ `02_EXECUTION_RULES.md` §E cấm.

⚠️ **Nhưng nó sẽ nổ.** Dòng tiếp theo ai đó thêm sẽ làm `lint_app_contract` đỏ.
Khi đó việc đúng là **chẻ theo use case** — dự án / render / phụ đề — không phải
cắt đôi cho dưới 900. Ghi ra trước để lần đó không thành một lần cắt vội.

### 🔴 `server/routes/developer.py` — 1.521 dòng / 32 handler, **chẻ**

Đây là ứng viên duy nhất có **bằng chứng thật**, và bằng chứng không nằm ở số dòng:

Nó sửa cùng với **`platform_core/public_api/tables`(7), `invocation`(5),
`examples`(5)** — ba module *miền*, không phải module vận chuyển. Một tệp route
mà mỗi lần đổi lại kéo theo ba module miền là dấu hiệu **nghiệp vụ đang sống
trong tầng vận chuyển**.

Nó cũng vượt **cả hai** ngưỡng hợp đồng app (900 dòng / 30 handler) — nhưng
**không bị lint chặn**, vì nó nằm trong `server/`, nơi hợp đồng app không với tới
(**G-01**).

**Đề xuất:** chẻ theo use case của cổng lập trình viên — khoá API · dự án/hạn
mức · sử dụng & hoá đơn · webhook · tài liệu. Và mở rộng lint sang `server/routes/`
với cùng ngưỡng.

### 🟡 `server/admin_api.py` 1.897 dòng — **để đó tới khi churn nói khác**

Tệp lớn nhất kho. Nhưng churn 16 và bạn đồng hành thưa (4/3/3). Một tệp lớn mà ít
thay đổi và thay đổi cô lập là **chi phí thấp** — chẻ nó là trả tiền hôm nay cho
một vấn đề chưa xuất hiện.

---

## 3. Khoảng trống hợp đồng: `server/` không có luật nào

`tools/lint_app_contract.py` thi hành 900 dòng / 30 handler cho `apps/`. `server/`
**không có ngưỡng nào**, và ba tệp lớn nhất kho đều nằm ở đó:

```
server/admin_api.py        1.897
server/routes/developer.py 1.521  (32 handler — vượt cả hai ngưỡng của apps/)
server/admin.py            1.388
```

Hợp đồng app ra đời sau khi đo được "route thành chỗ để mọi thứ rơi vào". Cùng
lực đó đang tác dụng lên `server/`, chỉ khác là không có gì cân nó.

**Đề xuất (G-01):** mở rộng linter sang `server/routes/` với cùng ngưỡng, chấp
nhận `admin_api.py`/`admin.py` như baseline hiện có (bánh cóc: không cho **tăng**),
đúng khuôn `check_silent_except`.

---

## 4. DANH SÁCH KHÔNG CHẺ

| Tệp | Vì sao |
|---|---|
| `platform_core/job_runner.py` | **Trái tim runtime.** Claim/lease/heartbeat/settle là một máy trạng thái — chẻ nó là chẻ một bất biến. Churn cao là bản chất của hub |
| `platform_core/models.py` | Schema tập trung; churn 32 là hệ quả của việc **có một chỗ** cho schema, và đó là điều đúng |
| `platform_core/registry.py` | Hợp đồng app. Một nguồn chân lý |
| `apps/autosubvideo/routes.py` | §2 — định vị thay đổi tốt |

---

```text
NO_RUNTIME_CHANGE: NO
```
