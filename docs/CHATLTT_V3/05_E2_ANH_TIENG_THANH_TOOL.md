# P05 — ảnh và tiếng thành tool. Và câu hỏi E2, trả lời bằng đo

> `00_GAP_MATRIX.md` giao cho P05 một câu chặn: **`image.edit` có backend thật
> không?** Kèm một luật: *không có ⇒ HOÃN, không làm nửa vời.*

## §1 — E2: KHÔNG CÓ. Đo, không suy.

```
grep -rn 'name="image\.' apps/*/manifest.py
```

| Năng lực khai trong `manifest.py` | App | Job |
|---|---|---|
| `image.ltt` | `anhnoibo` | có |
| `image.generate` | `taoanh` | `taoanh.generate` |
| `image.batch_generate` | `taoanh` | `taoanh.generate` |
| `image.thumbnail` | `thumbnail` | `thumbnail.generate` |
| `image.upscale` | `upscalevideo` | `upscalevideo.render` |
| `speech.ltt` | `ltt_voice` | có |

**Không có `image.edit`.** Nó không nằm trong `manifest.py` nào, và
`chinh_sach.CONG_CU_CHO_PHEP` cũng chỉ liệt ba tên: `text.chat`, `image.ltt`,
`speech.ltt`.

⇒ **HOÃN.** Không khai một tool mà nền tảng không làm được. Model sẽ gọi nó —
P01 đo 98,8 % chọn đúng tool **trong số được mời**, nên mời sai là bảo đảm nó
sẽ gọi sai — rồi nhận một lỗi mà người dùng phải đọc.

⭐ Đây là ca mà gói prompt giả định một năng lực có sẵn. Giả định ấy sai, và chi
phí phát hiện là **một lệnh `grep`**. Chi phí *không* phát hiện là một tool
hỏng đứng trong danh mục cho tới khi có khách gọi nó.

## §2 — Vậy P05 làm gì

Hai năng lực có thật: `image.ltt` và `speech.ltt`. Cả hai **đã** phục vụ khách
qua nút bấm (`/api/hoi-thoai/{id}/tao`). P05 là mở cho **model tự gọi** chúng,
sau cổng duyệt của P04.

| Hạng mục | Trạng thái |
|---|---|
| Duyệt bền + báo giá + chạy sau duyệt | ✅ P04 |
| `CHO_MODEL_GOI` thêm `image.ltt`, `speech.ltt` | ❌ P05 |
| **Chờ job xong giữa một run** (`WAITING_BACKGROUND`) | ❌ P05 — phần nặng |
| `image.edit` | ⛔ **HOÃN** (§1) |
| `image.generate` mây (`taoanh`) | ⏸ chờ chủ dự án (§6b-6 kế hoạch) |

## §3 — Phần nặng: một run phải CHỜ ĐƯỢC một job

`image.ltt` và `speech.ltt` không trả kết quả trong một lời gọi hàm — chúng nộp
một **job** rồi trả ngay. Một lượt agentic gọi chúng phải chờ, và cái chờ ấy có
thể dài hơn giới hạn 100 giây của Cloudflare.

⭐ **Hình dạng đã có sẵn, và nó giống hệt cổng duyệt.** P04 dựng đường:

```
chay_tool -> CanDuyet     => AWAITING_APPROVAL, chay() return
             (nguoi bam)  => tiep_tuc(ket_qua_duyet=...)
```

P05 chỉ thêm một đường song song, dùng đúng cơ chế ấy:

```
chay_tool -> ChoJob       => WAITING_BACKGROUND, chay() return
             (job xong)   => tiep_tuc(ket_qua_job=...)
```

`WAITING_BACKGROUND` **đã có** trong `CHUYEN_HOP_LE` từ P03
(`TOOL_RUNNING → WAITING_BACKGROUND → TOOL_RESULT_READY`), và `luu_run.dung_lai`
đã dựng lại được một run từ CSDL. Nên phần thật sự mới là:

1. `ChoJob` — anh em của `CanDuyet`.
2. `chatltt_step.job_id` (cột **đã có** trong migration `4b8e21c6d907`).
3. Một chỗ móc khi job xong → `chay_tiep_nen`.

⛔ **Không dựng bộ đợi thứ hai.** `platform_core/job_runner.py` đã có vòng đời
job và `leases.py` đã có lease. Một vòng `while` chờ job trong luồng của run là
một bộ đợi thứ hai — và nó sẽ giữ luồng qua cả những lần khởi động lại mà
`job_runner` chịu được còn nó thì không.

## §4 — Thứ tự làm, và vì sao thứ tự ấy

1. `ChoJob` + `tiep_tuc(ket_qua_job=…)` — máy trạng thái trước, vì nó kiểm được
   bằng số học thuần, không cần job thật.
2. Nộp job từ `bo_chay_tool` (dùng `tao_media.tao`, **không** viết lại).
3. Móc job-xong → `chay_tiep_nen`.
4. Mở `CHO_MODEL_GOI` — **bước cuối**, vì trước đó mọi thứ vẫn tắt với model.

🔑 Bước 4 cuối cùng là cố ý: ba bước đầu không đổi một hành vi nào mà người dùng
thấy được. Nếu chúng sai, cái sai nằm trong test, không nằm trong sản phẩm.

---

## §5 — Bốn bước ấy đã làm xong. Và bước 3 giấu hai lỗi.

Bước 1–2–4 đúng như dự liệu: `ChoJob` kiểm được bằng số học thuần (`test_815`),
nộp job dùng lại `tao_media.tao` (`test_816`), cổng thứ tư mở cuối (`test_802`).

**Bước 3 — "móc job-xong → `chay_tiep_nen`" — là chỗ mọi thứ thật sự chạm nhau,
và không phép kiểm nào đi qua nó cho tới `test_819`.** Đo 05/09: `_dat_khoi`
0 tệp nhắc tên, `con_cho_job` 0 tệp, `tao_media.dong_bo` chỉ xuất hiện ở dải 600
— tức đường V1 nút bấm, không phải đường V3.

Lý do khoảng trống ấy tồn tại rất bình thường: `test_816` **thay `tao_media.tao`
bằng một hàm giả** để khỏi kéo cả hàng đợi job vào một phép kiểm về máy trạng
thái. Quyết định đúng cho phạm vi của nó. Hệ quả là hàng `chatltt_execution` của
job **chưa từng tồn tại** trong một phép kiểm nào — và nó chính là thứ hỏng.

### Lỗi 1 — vòng model sau một job được mở bằng `image.ltt`

`su_kien.mo_execution()` ghi `message.execution_id = ex.id` **mỗi lần** nó mở một
hàng mới. `tao_media.tao` gọi nó với `tool_name="image.ltt", mode="job"`. Nên sau
khi nộp job, con trỏ ấy trỏ vào hàng của **job**.

`tiep_sau_duyet` lại đọc đúng trường ấy để biết mở luồng bằng năng lực nào, và
`luot.dong_su_kien` truyền `ex.tool_name` **thẳng** vào `L.mo_luong()`:

```
RuntimeError: tool 'image.ltt' has no sync executor
```

⛔ Không phải một cái nhãn sai — **lượt vỡ**. Hỏi cỗ máy vẽ ảnh một câu hỏi chữ.

⭐ Bản sửa không thêm khái niệm nào: `_execution_dau(run_id)` đã là câu trả lời
đúng cho **đúng câu hỏi này** ở `chay_tiep_nen` (*"hàng nào là danh tính của
run"* — thứ trình duyệt đang nghe). Dùng chung một nguồn thay vì hai.

### Lỗi 2 — model chưa bao giờ biết id bức ảnh nó vừa vẽ

`ket_qua_job` **đoán** tên cổng ra:

```python
kq.get("files") or kq.get("outputs") or kq.get("keys") or []
```

Không tên nào trong ba cái đó tồn tại. `image.ltt` khai `image_keys`;
`speech.ltt` khai `audio_key`. Nên với **cả hai** tool job, model luôn đọc:

```json
{"tao_xong": true, "tep": []}
```

🔴 Một câu **tự mâu thuẫn** — "xong rồi, và không có gì cả" — và là lý do nó
không thể tham chiếu ảnh cũ ở lượt sau, đúng thứ §2 đòi: *"bằng id artifact,
không bằng đoán tên tệp"*.

⭐ Bản sửa dùng lại `khoi_artifact()` — thứ dựng khối cho **người dùng** xem, và
đã viết đúng luật từ đầu: *"Khong doan: chi doc dung cong ra da khai."* Hai nguồn
cho câu hỏi *"job này đẻ ra những gì"* là hai nguồn sẽ lệch, và chỗ chúng lệch là
chỗ người dùng thấy một bức ảnh trong khi model nói nó không tạo được gì.

### Giới hạn KÉO — ghim lại, không vá vội

`dong_bo` chỉ chạy khi **client hỏi**. Không ai mở hội thoại thì run nằm im ở
`WAITING_BACKGROUND`. Chấp nhận được cho bản đầu và **không mất dữ liệu**: job đã
xong, tiền đã quyết toán, kết quả đã nằm trong `blocks`; thứ chưa xảy ra chỉ là
vòng model **nói về** bức ảnh.

Đường ĐẨY thật là một chỗ móc trong `job_runner` — `platform_core`, ngoài ranh
giới app này. `test_819` ghim giới hạn ấy bằng một phép kiểm, để ngày ai đó làm
đường đẩy thì phép kiểm đó **đỏ** và buộc người ta đọc lại đoạn này.
