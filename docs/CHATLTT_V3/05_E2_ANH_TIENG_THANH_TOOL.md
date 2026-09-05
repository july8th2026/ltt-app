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
