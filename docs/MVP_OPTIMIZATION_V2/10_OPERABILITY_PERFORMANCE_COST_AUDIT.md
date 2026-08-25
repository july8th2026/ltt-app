# 10 — VẬN HÀNH / QUAN SÁT / HIỆU NĂNG / CHI PHÍ

**Ngày:** 2026-08-26

---

## 1. 🔴 O-01 · P1 — Sao lưu: thiết kế đúng, **chưa từng chạy**

Đo trên chính máy chủ:

```
Get-ScheduledTaskInfo -TaskName 'LTTStudioBackup'  ⇒  TASK KHÔNG TỒN TẠI
C:\LTTPlatform\backups\   14 tệp, mới nhất  ltt_data_20260817_172426.zip  (2026-08-17)
Thư mục sao lưu bí mật (backups-secrets)          ⇒  KHÔNG TỒN TẠI
D:\LTTBackups                                     ⇒  có, nhưng ACL chặn — CHƯA KIỂM ĐƯỢC
```

**Chín ngày không có bản sao lưu nào**, trên một hệ thống **đang thu tiền thật**
(LLM bán từ 24/08, Nexus thu credit, VPS đã diễn tập thu tiền).

⛔ **Phần nặng hơn không phải dữ liệu.** `LTT_TOKEN_ENCRYPTION_KEY` và
`LTT_API_KEY_PEPPER` chưa có bản sao nào kiểm chứng được. Mất chúng **không phải**
mất một bản sao — nó làm **mọi token đã mã hoá và mọi hash khoá API của khách trở
thành rác vĩnh viễn**, kể cả khi bản dump CSDL còn nguyên vẹn.

⭐ Và điều mỉa mai đáng ghi: `deploy/windows/backup.ps1` **thiết kế đúng** — nó
tách hai bản sao riêng, và viết ra lý do (một bản bị lấy cắp không đủ để vừa đọc
token vừa tấn công khoá API ngoại tuyến). `5-lich-backup.ps1` cũng sẵn sàng.
**Một thiết kế đúng chưa bao giờ chạy thì bảo vệ được số không.**

Cùng họ với M-01 và M-02: máy móc có, chưa ai cắm điện. ⇒ **P-01**.

### Việc phải làm — cần quyền Administrator

```powershell
powershell -ExecutionPolicy Bypass -File .\deploy\windows\5-lich-backup.ps1
powershell -ExecutionPolicy Bypass -File .\deploy\windows\backup.ps1 -IncludeSecrets
```

Nghiệm thu: task tồn tại với `LastTaskResult = 0` · có tệp mới trong `backups\` ·
có `backups-secrets\ltt_secrets_*.zip` · **và một lần diễn tập khôi phục**
(`tools/restore_drill_schema.py`) — một bản sao chưa khôi phục thử là một lời
hứa, không phải một bản sao.

⚠️ Phiên này **không có quyền Administrator**; đây là việc cần chủ sản phẩm bấm UAC.

---

## 2. Quan sát được — khá tốt, và có một lỗ vừa vá

| Câu hỏi vận hành | Trả lời được? |
|---|---|
| Job này đang ở đâu? | ✅ `jobs.status` + `job_events` dòng thời gian |
| Vì sao hỏng? | ✅ lớp lỗi provider trong sự kiện |
| Tiền xử lý thế nào? | ✅ `credit_entries` theo `job_id` |
| Artifact đâu? | ✅ `storage` + `job_content` |
| Lượt retry/cancel? | ✅ `attempts`, sự kiện |
| **Một giữ chỗ TREO hiện ở đâu?** | ⛔ trước 26/08: **không đâu cả** → ✅ nay: cảnh báo `HOLD_STRANDED` + email |

**Cảnh báo đang có:** thiếu credit · ngưỡng/vượt ngân sách · gần/vượt hạn mức ·
khoá sắp hết hạn · webhook hỏng · **biên lợi nhuận âm** *(vừa được cắm điện ở
`a5274bf` — trước đó nó chưa từng nổ)* · **giữ chỗ treo** *(mới)* · ngưỡng vận
hành qua `ops_alerts`.

---

## 3. Sức khoẻ / khởi động lại

| | |
|---|---|
| `/live` `/ready` `/version` | ✅ |
| `/ready` **không** đọc tệp cấu hình nào | ✅ — đã xoá cả một lớp lỗi (xem 08 §2.2) |
| Đường lùi khi deploy | ✅ `app.previous` giữ bản trước |
| `deploy-self.ps1` khởi động lại | `LTTStudioWeb`, `LTTStudioWorker`, `LTTStudioCodex` — **đúng, đủ** |

**~~O-03~~ — GIẢ THUYẾT SAI, ĐÃ BÁC BỎ.** Bản nháp của mục này ghi *"`LTTNexus`
chạy mã trong `app\` nhưng không được khởi động lại ⇒ chạy mã cũ sau deploy"*.

Kiểm bằng `Win32_Service`:

```
LTTNexus         "C:/Program Files/LTTNexus/LTTNexus.exe" --service
LTTStudioWeb      C:/LTTPlatform/tools/nssm.exe
LTTStudioWorker   C:/LTTPlatform/tools/nssm.exe
LTTStudioCodex    C:/LTTPlatform/tools/nssm.exe
```

`LTTNexus` là **một nhị phân riêng**, không chạy mã trong `app\`. Nó **không
cần** khởi động lại khi deploy, và ba dịch vụ trong danh sách là **đúng và đủ**.

⭐ Ghi lại chỗ suýt sai này vì bài học lớn hơn bản thân nó: tôi suýt sửa một
đường deploy **đang chạy đúng** dựa trên suy luận từ tên dịch vụ. Chính đường đó
đã làm production ngừng 20 phút ngày 2026-08-05. Một thay đổi "hiển nhiên đúng"
vào đường deploy là thay đổi tốn kém nhất khi nó sai.

---

## 4. Hiệu năng — baseline **chưa có**, và không được bịa

```text
Độ trễ trang         : CHƯA ĐO
Thời gian chờ hàng đợi: CHƯA ĐO
Thời lượng job       : CHƯA ĐO trên lưu lượng thật
Bundle frontend      : agent-canvas 466 KB · autosub 231 KB · ommi 235 KB
```

⚠️ **Một cái bẫy phải ghi kèm mọi con số thời gian chạy test:** `tests/conftest.py`
từng có **ba fixture `autouse`** chạy trước **mọi** test; chúng đi cùng đợt xoá
Q108. Bộ test nay nhanh hơn vì **bớt việc mỗi test**, không phải vì mã tốt lên.
So sánh trước/sau mà không nói câu này sẽ được đọc thành một cải thiện không có thật.

`10.1` — Prompt 15 không được đặt ngưỡng hiệu năng phút cuối. Không có baseline
thì kết luận đúng là *"chưa đo"*, không phải *"đạt"*.

---

## 5. Chi phí

| | |
|---|---|
| Nguồn giá vốn | ✅ **một** — `gia_von.json`, milli-credit số nguyên |
| Chặn bán dưới giá vốn | ✅ `test_261`, miễn trừ có chữ ký + hạn |
| Quan sát biên lợi nhuận | ✅ `costing.margin` |
| **Cảnh báo biên âm** | ⛔ viết xong từ lâu, **chưa ai gọi** → ✅ đã cắm `a5274bf` |
| Retry có nhân chi phí? | ✅ `attempts` có trần; job làm treo worker không quay lại vô hạn |
| Đường đắt có trần | ✅ `render_gateway/ngan_sach.py` từ chối cấu hình vượt `TOKEN_DA_DO_TOI_DA` **trước khi chạm GPU** |

⭐ **M-02 đáng đọc kỹ ở đây.** `docs/PHAN_TICH_MVP_2026-08-23.md` đo được nền tảng
bán ảnh ở **45–57 % giá vốn suốt 22 ngày**. Cảnh báo "biên lợi nhuận âm" đã tồn
tại trong mã suốt thời gian đó — có docstring, có test, có trong `__all__` — và
**không gì gọi nó**. Nghĩa là hệ thống đã có sẵn thứ để phát hiện chuyện đó, và
nó im lặng vì chưa ai cắm dây.

---

## 6. Hợp đồng vận hành MVP tối thiểu

```text
1. Sao lưu CHẠY THEO LỊCH + bí mật tách riêng + một lần khôi phục thử   ← O-01, ĐANG NỢ
2. Mọi cảnh báo đã viết đều được GỌI                                    ← đã đóng a5274bf
3. Từ một job_id giải thích được: trạng thái · lỗi · tiền · artifact     ← có
4. Đường lùi khi deploy                                                 ← có (app.previous)
5. `/ready` phản ánh phụ thuộc thật, không phụ thuộc của một app         ← có
```

## 7. Việc còn nợ

| ID | Mức | Việc |
|---|---|---|
| **O-01** | **P1** | Bật lịch sao lưu + sao lưu bí mật + diễn tập khôi phục *(cần Administrator)* |
| **O-02** | **P1** | Bốn khoảng trống bằng chứng của H40 — xem Prompt 15 |
| **O-04** | P2 | Baseline hiệu năng cho Golden Journey |

```text
NO_RUNTIME_CHANGE: NO
```
