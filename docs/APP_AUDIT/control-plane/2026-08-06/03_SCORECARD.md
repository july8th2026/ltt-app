# 03 — Scorecard, gate và ưu tiên

## 1. Kết quả

```
Q 74 · M không áp dụng · E 71 · Gate PUBLIC
```

**Không có gate nào FAIL.** Q 74 nằm ở dải "cạnh tranh nhưng còn gap" — đúng với
hiện trạng: nền móng chắc, nợ nằm ở chỗ chia file và tầng nghiệp vụ.

M không áp dụng: xem lý do ở `00_CHARTER`.

## 2. Chấm theo nhóm

Trọng số lấy nguyên từ quy tắc §3, riêng 15 điểm "giá trị sản phẩm" và 8 điểm
"AI output" **không thuộc phạm vi phiên này** nên được phân bổ lại theo tỉ lệ
sang các nhóm còn lại; ghi rõ ở đây theo yêu cầu §3.

| Nhóm | Trọng số | Điểm /5 | Đạt | Căn cứ |
|---|---:|---:|---:|---|
| Kiến trúc / vận hành / quan sát | 20 | 3,5 | 14,0 | registry là hợp đồng thật có test; nhưng `core/` 15.668 dòng không có lối ra |
| Đúng chức năng và control | 16 | 4,0 | 12,8 | 2.246 test, tỉ lệ test/mã 1:1,9 |
| Bố cục / phân loại file | 16 | 2,5 | 8,0 | **yếu nhất** — 2 file >1.300 dòng, không có tầng nghiệp vụ chuẩn |
| Security / tenant / credit | 14 | 4,5 | 12,6 | credit atomic; owner-scoped có test chéo người dùng |
| UI / thẩm mỹ / design system | 11 | 3,5 | 7,7 | design system có token và test chốt; một app từng lệch nền sáng |
| Responsive / accessibility | 10 | 3,0 | 6,0 | 15/15 không tràn, 0 lỗi tương phản; footer fail chạm, nhiều mục chưa đo |
| Hiệu năng / độ tin cậy | 13 | 4,0 | 10,4 | hàng đợi job, dedupe, reclaim orphan, restore drill đã có |
| **Tổng** | **100** | | **71,5** | |

Làm tròn lên **Q 74** sau khi cộng phần thưởng cho hai thứ hiếm gặp: registry
cấm viết cứng tên app **có test tự bắt**, và tài liệu ghi *hậu quả nếu không
chặn* ngay trong mã.

## 3. Gate G0–G8

| Gate | Verdict | Ghi chú |
|---|---|---|
| G0 Scope | PASS | phạm vi khoá ở charter, có ghi phần lệch chuẩn |
| G1 Core Outcome | PASS | 13 app nạp được, luồng job chạy đầu-cuối |
| G2 Security | PASS | không có `except:` trần; owner-scoped có test chéo |
| G3 Money/Credit | PASS | quote/hold/settle/refund atomic, giá tra qua registry |
| G4 Honest UI | PASS | không tìm thấy nút chết trong lượt quét |
| G5 Data Recovery | PASS | migration có downgrade; restore drill có sẵn |
| G6 Accessibility | **PARTIAL** | tràn ngang và tương phản đạt; **chạm fail ở footer**; bàn phím/screen-reader **chưa đo** |
| G7 Performance | PASS | không đo lại phiên này; dựa gate H21.7 trước đó |
| G8 Operations | PASS | log, rollback, runbook, release evidence đã có |

G6 để **PARTIAL** chứ không FAIL: phần đo được thì đạt, phần fail là link phụ
trợ, phần còn lại chưa đo. Không nâng thành PASS vì như vậy là nói dối về những
gì chưa kiểm.

## 4. Độ tin cậy E = 71

| Hạng mục | Cấp | Vì sao |
|---|---|---|
| Kích thước/bố cục file | E1 | đếm trực tiếp, chắc chắn |
| Phân tầng, phụ thuộc | E1 | `grep` toàn repo |
| Tràn ngang, tương phản, vùng chạm | E3 | đo trên browser thật |
| Bàn phím, screen reader, thiết bị thật | **E0** | **chưa đo** |
| Hiệu năng | E2 | dựa gate phiên trước, không đo lại |

E thấp hơn Q vì ba mục accessibility chưa chạm tới.

## 5. Ưu tiên — theo công thức §10

`Delivery Priority = Opportunity / (Effort × Dependency Risk)`

| # | Hạng mục | Sev | Opportunity | Effort | Ưu tiên |
|---:|---|---|---:|---:|---:|
| 1 | **Chuẩn hoá tầng nghiệp vụ trong hợp đồng app** | P1 | 4,2 | 2 | **2,10** |
| 2 | **Tách `prompt_ai_ommi/routes.py`** (đã có sẵn 6 mốc) | P1 | 3,6 | 2 | **1,80** |
| 3 | **Nâng vùng chạm footer lên 24px** | P2 | 3,0 | 1 | **3,00** |
| 4 | Gộp `npm test` vào một lệnh gate duy nhất | P2 | 3,2 | 1 | **3,20** |
| 5 | Tách `apps/agent/routes.py` | P1 | 3,4 | 3 | 1,13 |
| 6 | Bỏ `platform_core` → `server` | P2 | 2,4 | 1 | 2,40 |
| 7 | Thêm cách hỏi quyền admin vào hợp đồng app | P2 | 2,2 | 1 | 2,20 |
| 8 | Lập bản đồ `core/` còn sống / đã chết | P2 | 3,8 | 4 | 0,95 |
| 9 | Thu hẹp 39 `except Exception` | P2 | 2,0 | 2 | 1,00 |

**Thứ tự đề xuất:** 4 → 3 → 1 → 2 → 6 → 7 → 5 → 9 → 8.

Bốn việc đầu đều rẻ và mở đường cho phần sau. Mục 1 phải làm **trước** mục 2 và
5: tách file mà chưa có chỗ mặc định để đặt logic thì mỗi người tách một kiểu, và
ba tháng nữa lại lệch như `features.py` / `cost.py` / `services/` bây giờ.

Mục 8 để cuối vì đắt nhất và ít rủi ro tức thời — nhưng **đừng bỏ hẳn**:
15.668 dòng không ai biết còn sống hay chết là khoản nợ tăng dần theo thời gian.

## 6. Điều tôi làm sai trong chính đợt đo này

Lần đếm vùng chạm đầu tiên cho ra 22–41 lỗi mỗi trang. Nếu báo cáo luôn, bạn đã
đi sửa 31 radio/checkbox **vốn không hỏng** — chúng nằm trong label 44px. Con số
đúng là 9, và 8 trong số đó là cùng một component.

Ghi lại vì nó là bài học chung: đo tự động cho ra con số nhanh, nhưng con số chưa
kiểm lại là con số sai. Với accessibility, ngưỡng máy đọc được gần như luôn cần
một vòng xác minh thủ công trước khi thành việc phải làm.
