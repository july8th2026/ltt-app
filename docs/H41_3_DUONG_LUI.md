# H41.3 — đường lùi, viết TRƯỚC khi sửa dòng đầu tiên

Việc này chạm **đường tiền**. `AGENTS.md` và `CLAUDE.md` đòi đường lùi phải có
trước, nên đây là tài liệu đó — không phải bản tường thuật viết sau.

---

## 1. Phạm vi thật, sau khi đọc mã

⭐ **Không cần đổi schema, và đó là phát hiện đầu tiên.**

Kế hoạch ghi *"`hold_expires_at` + tự hoàn ⇒ đụng schema + đường tiền"*. Nhưng
`credit.giu_cho_treo()` **đã** tính đủ: nó trả về `user_id`, `job_id`, `credit`,
`tao_luc`, `ly_do` cho từng khoản treo. Một cột `hold_expires_at` chỉ lặp lại
thứ suy được từ `created_at + TREO_SAU`.

⛔ Thêm một cột như thế phải **migration + backfill trên bảng tiền đang sống**,
để đổi lấy đúng con số đã có. Nên phần "đụng schema" **bị bỏ**, và mức rủi ro
của cả hạng mục tụt hẳn: còn đúng một nửa — đường tiền.

## 2. Thay đổi

| Tệp | Gì |
|---|---|
| `platform_core/credit.py` | thêm `tu_hoan_treo()` — **hàm mới**, không sửa hàm cũ |
| `platform_core/job_runner.py` | gọi nó trong `_mot_luot_bao_tri`, **dưới lease** |
| `tests/test_331_*.py` | mới |

**Không** sửa `giu_cho_treo()`, `hoan()`, `quyet_toan()`, `giu_cho()`.

## 3. Đường lùi

```bash
git revert <commit>
```

- **Không migration** ⇒ không có gì phải hoàn ở CSDL.
- Gỡ lời gọi trong `_mot_luot_bao_tri` là đủ để tắt hẳn tính năng; hàm còn nằm
  đó cũng vô hại vì không ai gọi.
- Cờ tắt nhanh **không cần**: hàm đọc `TU_HOAN_SAU`; đặt nó rất lớn là vô hiệu
  hoá mà không phải deploy lại mã.

⚠️ **Bút toán đã ghi thì KHÔNG lùi được bằng revert.** Sổ credit là **chỉ ghi
thêm** (append-only) — đó là thiết kế, không phải hạn chế. Nếu một lần hoàn là
sai thì cách sửa là **một bút toán bù**, không phải xoá dòng.

⇒ Hệ quả cho việc nghiệm thu: sai sót ở đây **không lùi sạch được**, nên hàng
rào phải nằm ở chỗ *quyết định hoàn hay không*, chứ không nằm ở chỗ *sửa sau*.

## 4. Bốn hàng rào, và vì sao mỗi cái cần

**1. Ngưỡng tự hoàn DÀI HƠN ngưỡng báo chuông.**
Chuông kêu ở `TREO_SAU = 6 giờ`; tự hoàn ở `TU_HOAN_SAU = 24 giờ`. Người trực
**thấy trước** và còn 18 tiếng để can thiệp nếu đó là báo động giả.
⛔ Bằng nhau là hỏng: máy sẽ hoàn trước khi có ai kịp nhìn, và một chẩn đoán sai
biến thành tiền đã trả.

**2. Chỉ hoàn khoản CÓ `job_id`.**
`hoan()` tra theo `job_id`; khoản `ly_do="khong_co_khoa"` (job_id rỗng) **không
có đường kết sổ nào** và phải để người xử. Tự động hoá đường đó nghĩa là đoán
xem tiền thuộc về ai — đúng thứ không được đoán.

**3. Trần mỗi lượt.**
Một lỗi khiến hàng nghìn khoản bị coi là treo thì trần giữ cho nó thành *một
sự cố nhỏ nhìn thấy được* thay vì *một lần hoàn hàng loạt*. Chạm trần thì ghi
log ở mức cảnh báo — im lặng cắt bớt là thứ tệ hơn cả không có trần.

**4. Chạy DƯỚI LEASE.**
Số tiến trình worker mặc định bằng số GPU (H36). Không có lease thì N tiến
trình cùng quét — `hoan()` idempotent nên tiền không sai, nhưng log và cảnh báo
nhân N. Đặt trong `_mot_luot_bao_tri` là đúng chỗ đã có lease.

## 5. Nghiệm thu

- `python tools/gate.py` **trước** khi sửa và **sau** khi sửa.
- Test phải chốt cả **chiều không được hoàn**: chưa đủ hạn · không có `job_id` ·
  job còn `queued`/`running` · đã `settle` rồi.
- Kiểm **có răng**: tháo từng hàng rào một, mỗi lần phải đỏ đúng một phép kiểm
  khác nhau — ba phép kiểm cùng đỏ vì một thứ là ba phép kiểm canh một thứ.
