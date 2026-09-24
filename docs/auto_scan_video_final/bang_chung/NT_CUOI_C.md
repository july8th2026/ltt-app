# NT_CUOI lượt C — cắt thông minh · USER_SELECTED `Minh Đức` · zh→vi

Nhánh `phien/asvf-nghiem-thu-v2` · 24/09/2026 10:47–11:49 (UTC+7)
⛔ **DỪNG CÓ CHỦ Ý ở `qc_ai` vòng 2** — không phải lượt hỏng.

## Vì sao dừng

Chủ dự án chốt hướng mới (luồng chính là **nghe chép voice→voice**, hardsub chỉ để
**đối chiếu**) ⇒ bảng bốn dòng của C đo một đường **phụ**, giá trị tụt. Và một làn
phiên khác đã xếp hàng sau `postgres_test` **78 phút**.

Điều phối đặt luật: *"≤ 10 phút thì chạy nốt; **không đo được còn bao lâu ⇒ dừng
ngay**"*. Tôi **không đo được**:

* `qc_ai` vòng 2 đã chạy **14,3 phút**, vượt mốc duy nhất tôi có (lượt B: 11:57 s ≈ 12 ph);
* `asv_stage.outputs` chỉ ghi **lúc kết thúc pha** ⇒ không có tiến độ trong pha.

⇒ Dừng. Đã kill tiến trình **mình khởi động** (lọc theo dòng lệnh), rồi nhả khoá
**tường minh**: `postgres_test` đã tự nhả và về tay phiên `p3` ngay; `may_tao_tieng`
còn một **bản ghi treo của chính tôi** (`cua_so_yen` khai `TREO — tiến trình 24232
không còn chạy`) nên gỡ bằng `nha --ep --tai-nguyen may_tao_tieng` — ⛔ **có
`--tai-nguyen`**, vì `--ep` trống tay gỡ **mọi** khoá trên máy, kể cả của lượt gate
đang chạy. Kiểm lại: làn này giữ **không gì**.

## Thu được — MỘT NỬA bảng bốn dòng

Vòng sửa **đã chạy** trước khi dừng, nên nửa *trước sửa* là số thật:

| | lượt B (giữ hình) | **lượt C (cắt thông minh)** |
|---|---|---|
| `dich_sai` | 60 | **40** |
| `doc_sai` | 10 | **12** |
| `khong_vua` | 15 | **14** |
| **tổng trước sửa** | **85** | **66** |
| **tổng sau sửa** | **85** | ⛔ **KHÔNG CÓ** — dừng trước khi `sua_chua_con_lai` được ghi |

⛔ **Nên C KHÔNG trả lời được câu hỏi 85→85.** Nửa *sau sửa* chỉ được ghi sau khi
`qc_ai` vòng 2 xong, và đó đúng là chỗ đã dừng. Câu hỏi *"vòng sửa có giảm khiếm
khuyết không"* vẫn ở **n = 1** (chỉ lượt B).

⭐ Nửa thu được vẫn nói một điều: cùng phim, cùng cặp ngôn ngữ, **đổi preset** thì
tổng khiếm khuyết trước sửa **85 → 66**. Chưa đủ để kết luận gì, nhưng nó bảo rằng
con số đó **phụ thuộc preset**, tức một phép đo về "bản chất vòng sửa" phải cố định
preset hoặc đo cả hai.

## Các pha đã xong (vòng 1, trước khi vòng sửa chạy)

11/12 `succeeded` ở lần thử 1; `qc_ai` vòng 1 xong và đã đẩy lượt vào vòng sửa.
Card được cấp, `python_tach` ghim venv worker — như A và B.

## ⚠️ Tự soát: khối giữ `postgres_test` CÓ chứa bước CHỜ

**Có.** `qc_ai` phần lớn là **chờ máy B**, và khoá bọc cả quãng đó.

Nhưng nó **không phải K-02 tái diễn**, và lý do đáng ghi lại:

| | `cpu_nhieu` (K-02) | `postgres_test` |
|---|---|---|
| bảo vệ cái gì | **sức tính** | **CSDL không bị `drop_all` dưới chân** |
| trong lúc chờ | tài nguyên **rảnh** ⇒ giữ là phí | CSDL **vẫn đang được ghi** liên tục (mọi `advance`, mọi dòng giai đoạn) |
| tách theo pha | ✅ được | ⛔ **không** — không có pha nào "không cần CSDL" |

⇒ **Không tách được theo pha.** Nhưng nó **bỏ được hoàn toàn**, và đó mới là câu
trả lời hữu ích cho bước sau:

> Khoá tồn tại vì **tên CSDL dùng chung** (`lttplatform_test`), không vì tài nguyên
> tự nó độc quyền. Cho mỗi làn một tên riêng — `lttplatform_test_asvf_nt_v2` — thì
> không còn xung đột, và **không cần khoá nào**.

Và điều đó **hợp lệ**: `tests/pg_scratch.scratch_url()` chỉ đòi tên chứa `"test"`
(kiểm tên, không so với `LTT_DATABASE_URL` — và docstring của nó giải thích vì sao
phép so kia đã bị bỏ). `lttplatform_test_asvf_nt_v2` thoả.

⚠️ Chưa làm — đây là **đề xuất kèm căn cứ**, không phải việc đã xong. Nó cũng đóng
luôn **M-11** (run mồ côi trong CSDL test dùng chung) vì mỗi làn không còn thấy rác
của làn khác.
