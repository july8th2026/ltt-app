# LTT VOICE — CHUẨN VẬN HÀNH CỦA CỬA

> Audit 2026-09-11. Nguồn chân lý cho câu hỏi *"một cửa tạo việc sinh tiếng
> phải làm gì, theo thứ tự nào"*.
>
> ⛔ Tài liệu này **không** chép lại giá trị nào từ mã. Nó khai **thứ tự** và
> **ai chịu trách nhiệm**. Con số ở `gia.py`, `tham_so_cong_khai.py`; luật làn ở
> `lan_ngon_ngu.py`. Chép chúng vào đây là dựng bản sao thứ hai — đúng thứ cả
> Q121 lẫn tài liệu này đi dọn.

## 1. Vì sao có tài liệu này

`features.py` mở đầu bằng một lời hứa đã đúng từ đầu:

> *"Nghiệp vụ ở `features.py`, dùng chung mọi cửa — hai cửa tự xử lý riêng ⇒
> ngày chúng lệch nhau là ngày một yêu cầu bị tính hai giá."*

Cho tới 11/09/2026 lời hứa ấy được giữ bằng **quy ước**: người viết cửa mới phải
**nhớ**. Không phép kiểm nào đếm xem đã nhớ đủ chưa.

Audit đếm thật: **sáu** cửa tiêu tiền hoặc chạm GPU. **Năm** cửa nhớ. **Một**
cửa quên.

⭐ Và bản thân lượt audit **thủ công** cũng đếm thiếu: nó tìm ra năm cửa. Cửa
thứ sáu (`_p_giong.py::tao_giong`) do **phép quét cơ học** trong
`tests/test_356_moi_cua_tieu_tien_deu_qua_mot_cong.py` tìm ra. Đó là toàn bộ lý
do một ranh giới cơ học hơn một giao ước: *người đọc kỹ vẫn đếm thiếu, phép đếm
thì không.*

## 2. Bản đồ cửa — đo 11/09/2026

| Cửa | `chuan_hoa` | `giai_giong`<br>(sở hữu + làn) | Tiền | Suất GPU |
|---|:--:|:--:|---|---|
| `routes/_p_tao.py::tao` — Studio | ✅ | ✅ | `submit_with_credit` | qua hàng đợi job |
| `routes/_p_du_an.py::_nop_mot_khoi` — Dự án | ✅ | ✅ | `submit_with_credit` | qua hàng đợi job |
| `routes/_p_phat_dan.py::phat_dan` — phát dần | ✅ | ✅ | `giu_cho` + `_quyet_toan` | `admission.acquire` (giữ suốt generator) |
| `routes/_p_lich_su.py::doc_lai` — đọc lại | ✅¹ | ✅¹ | `submit_with_credit` | qua hàng đợi job |
| `routes/_p_nghe_thu.py::nghe_thu_van_ban` | — ² | — ² | **miễn phí** + rate-limit/giờ | `admission.hold_persisted` |
| `routes/_p_giong.py::tao_giong` — ghi danh | — ³ | — ³ | `submit_with_credit` (giá cố định) | qua hàng đợi job |
| `jobs.py::_tao_tieng` — worker | ✅ | ✅ | — (báo `credit_cost`) | — |

¹ **Thêm 11/09/2026.** Trước đó cửa này thiếu cả hai — xem mục 4.
² Miễn trừ có lý do: miễn phí, chỉ nhận `preset` (không nhận `voice_id`) nên
không có câu hỏi sở hữu nào. Cổng riêng: `giong_mau.hop_le` + trần ký tự +
rate-limit + admission.
³ Miễn trừ có lý do: ghi danh giọng **mới** — không có giọng cũ để kiểm sở hữu,
không có văn bản để đối chiếu làn. Cổng riêng: `dong_y == "1"` (cổng pháp lý),
tên không rỗng, `features.kiem_ghi_danh`.

## 3. Thứ tự bắt buộc của một cửa tiêu tiền

```
  ①  CSRF (cửa web)                    -> 400/303, chưa chạm gì
  ②  features.chuan_hoa(params)        -> có text? XOR voice_id/preset? preset có thật?
  ③  features.giai_giong(db, yc)       -> SỞ HỮU giọng + LÀN ngôn ngữ (Q121)
  ④  trần ký tự công khai              -> 400
  ⑤  GIỮ CREDIT / GIÀNH SUẤT           -> từ đây trở đi mới chạm tiền và máy
  ⑥  nộp job (hoặc chạy đồng bộ)
```

🔴 **Ranh giới thật nằm giữa ④ và ⑤.** Mọi thứ trước ⑤ là *"trả lời một câu hỏi
ta đã biết"*; mọi thứ từ ⑤ là *"tiêu một thứ có thật của khách"*. Một phép kiểm
đặt sai phía ranh giới ấy không sai về **kết quả** — worker vẫn chặn — mà sai về
**cái giá của việc biết**: khách bị giữ tiền, xếp hàng, và chờ để nghe một câu
mà cửa vào đã biết ngay từ đầu.

⚠️ Đây không phải một lo ngại lý thuyết. Nó là sự cố production **31/08/2026**
đã ghi trong `routes/_p_tao.py`: tài khoản B gửi `voice_id` của tài khoản A và
nhận **HTTP 200 kèm job_id** — giọng không bị dùng, nhưng credit vẫn bị giữ và
job bị thử lại ba lần.

## 4. Cửa đã quên, và phép đo bắt được nó

`routes/_p_lich_su.py::doc_lai` gọi `submit_with_credit` mà **không** gọi
`chuan_hoa` lẫn `giai_giong`.

⭐ Và nó là cửa **có nhiều khả năng mang tham chiếu ôi nhất**, theo đúng thiết
kế: nó phát lại `params` **CŨ**. Giữa lần chạy đầu và lần bấm "đọc lại", ba thứ
có thể đã đổi:

- giọng nhân bản bị **tắt / thu hồi** (`trang_thai != "active"`);
- làn ngôn ngữ được khai lại, biến một cặp từng hợp lệ thành **lệch làn** (Q121);
- engine nâng cấp, một `preset` cũ **không còn tồn tại**.

**Đo thật** trên `studio_dev`, cùng một cặp văn bản + giọng:

```
                                          HTTP   job   số dư
POST /ltt-voice/tao                  ->   400    ✗     500  (không đổi)
POST /ltt-voice/lich-su/<id>/doc-lai ->   200    ✓     499  ← giữ 1 credit
```

Sau bản vá 11/09:

```
POST /ltt-voice/lich-su/<id>/doc-lai ->   400    ✗     500  (không đổi)
                                          ma_loi = voice_language_mismatch
```

⛔ **KIỂM bằng `chuan_hoa`, nhưng vẫn NỘP `params` GỐC.** Hai việc khác nhau:
`chuan_hoa` là **phép kiểm**, `p` là **tải trọng**. Dựng lại params từ `YeuCau`
sẽ đánh rơi mọi khoá mà `YeuCau` không biết (`nguon`, `project_id`, `block_id`,
và khoá tiếp theo ai đó thêm) — đúng thứ docstring của `doc_lai` đã cảnh báo
theo chiều ngược lại.

## 5. Chuẩn được cưỡng chế bằng gì

`tests/test_356_moi_cua_tieu_tien_deu_qua_mot_cong.py` — quét **cây cú pháp**
(không khớp chuỗi) mọi hàm trong `apps/ltt_voice/`, tìm hàm nào gọi
`submit_with_credit` · `giu_cho` · `goi_cong`, và đòi nó cũng gọi `giai_giong`.

Miễn trừ phải khai **từng cái, kèm lý do dài đủ để cãi lại**, theo khoá
`(tệp, hàm)` — không phải tên hàm trần, vì một miễn trừ trôi sang tệp khác là
một lỗ mở ra âm thầm.

Ba phép kiểm phụ giữ cho chính bánh cóc không mục:

- **đối chứng cho phép quét**: nó phải *thấy được* những cửa ta biết chắc là có
  — một phép quét trả rỗng sẽ làm mọi phép kiểm khác xanh-rỗng;
- **miễn trừ mồ côi**: một điều khoản miễn trừ không được sống lâu hơn thứ nó
  miễn trừ;
- **lý do đủ dài**: một miễn trừ không có lý do là một cửa bị quên đội lốt một
  quyết định.

## 6. Còn để mở — không chốt ở lượt audit này

| Vấn đề | Vì sao chưa chốt |
|---|---|
| **Nghe thử cho qua thứ cửa nộp từ chối.** Khách nghe thử EN trên giọng VI được, rồi bấm Tạo thì bị từ chối. | Đây là **quyết định sản phẩm**, không phải lỗi. Nghe thử tồn tại để khách *nghe thấy* giọng không hợp — chặn nó là bỏ mất cách rẻ nhất để khám phá ràng buộc. Nhưng bất đối xứng này đang **không được nói ra ở đâu**, nên nó trông như một chỗ sót. Cần một câu ở giao diện, không cần một cửa chặn. |
| **Đường Public API giữ credit rồi mới từ chối.** | `ToolSpec` không có hook kiểm tham số trước `submit_with_credit`; thêm hook là sửa `platform_core`. Credit **được hoàn**, GPU không bị chạm. |
| **`jobs.py::_ghi_danh` chưa truyền làn xuống `nghe_thu.dung`.** | WS02 sở hữu `jobs.py`. Hôm nay không đổi hành vi (hồ sơ mới luôn `ngon_ngu` mặc định). |

## 7. Điều đáng nhớ hơn cả bản đồ

Bốn cửa đúng **không chứng minh gì** về cửa thứ năm; và cửa thứ năm được sửa
cũng **không chứng minh gì** về cửa thứ sáu. Chỉ một phép đếm **trên toàn bộ tập
cửa** mới làm được — và chính lượt audit thủ công của phiên này đã đếm thiếu
một, rồi bị phép đếm cơ học sửa lại.

⇒ Sửa một cửa là vá một **lỗ**. Đếm mọi cửa là đóng một **hạng lỗi**.
