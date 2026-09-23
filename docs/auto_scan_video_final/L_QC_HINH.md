# Làn `qc-hinh` — M-02 (lớp QC hình không ai gọi) và F-10 (vân tay cảnh)

Nhánh `phien/asv-final-qc-hinh`, từ `d8a39091`. Tệp này là **bảng đo + quyết định**,
không phải quy trình. Luật vận hành ở `docs/00_LTT_OPERATING_CONTRACT.md`.

> Bốn video nghiệm thu thật (Douyin, tiếng Trung, 576p, chỉ đọc):
> v1 烤牛肠 265 s · v2 暴雨露营 190 s · v3 跳伞 107 s · v4 气枪 275 s.

---

## 1. M-02 là gì, và vì sao nó không lộ ra

`LOI_TONG.md` M-02: *"QC liên tục cảnh bằng VLM định nghĩa nhưng **không ai gọi**"*.

Ba mảnh đã nằm sẵn từ pha 19, **đều có test xanh**:

| mảnh | nó làm gì | ai gọi (trước 23/09) |
|---|---|---|
| `qc_ai.loi_nhac_hinh` | hỏi VLM về hai khung hai bên một chỗ nối | — |
| `qc_ai.doc_hinh` | đọc phán quyết | — |
| `sua_chua.tu_qc_hinh` | biến phán quyết thành khiếm khuyết `cat_sai` | — |

⇒ Cột *"QC thị giác"* của sản phẩm **rỗng**, và nó rỗng theo kiểu không ai thấy:
mọi phép kiểm của ba mảnh đều xanh. Đây là lần thứ **sáu** kho này gặp đúng hình
dạng đó (kiểm toán pha 26 đếm được năm lần trước).

## 2. Đã nối gì (mã)

| Trước | Sau | Tệp |
|---|---|---|
| `giai_doan_qc_ai` chỉ soát NGỮ NGHĨA | + vòng **hình**: mọi chỗ nối của tệp **ĐÃ RENDER**, trên **trục bản ra** | `giai_doan_qc_ai._soat_hinh` |
| (không có) | `qc_ai.cac_cho_noi` — đổi ngược chỗ nối → **các cảnh bị bỏ tại đó** | `qc_ai.py` |
| `doc_hinh(goi: dict, ...)` (người gọi tự bóc `noi_dung`) | `doc_hinh(kq, ...)` đi qua `ai.doc_ket_qua` (giữ `finish_reason`/`suy_nghi`) | `qc_ai.py` |
| `bool(goi.get("dat", True))` — thiếu trường ⇒ **ĐẠT** | `chuan_dat` + `QC_HINH.truong_bat_buoc` ⇒ thiếu/lạ thì **NỔ** | `qc_ai.py`, `ai.py` |
| lời nhắc kể tên khoá | **khung JSON** + cấm mảng + cấm bọc lớp | `qc_ai.loi_nhac_hinh` |
| (không có) | `jobs._qc_hinh` → `sua_chua.lap_ke_hoach(qc_hinh=)` | `jobs.py` |
| `rut_khung` viết riêng trong `edit_plan` | `canh.rut_khung` — **một bản sao** cho cả hai người gọi | `canh.py` |
| `PHIEN_BAN_QC_AI = 1` | `= 2` (vào vân tay giai đoạn qua `thi_hanh.phien_ban_engine`) | `qc_ai.py` |

⛔ Không có `old`/`new` song song: `qc_ai.tom_tat` (đếm lại đúng những con số
giai đoạn tự đếm, **chưa từng có người gọi**) đã **xoá hẳn**.

### 2.1 Vì sao hỏi trên tệp ĐÃ RENDER, không trên nguồn

Câu hỏi là *"chỗ nối này, **như khách sẽ nhìn thấy**, có đứt mạch không"*. Hỏi nó
trên tệp nguồn là hỏi về hai cảnh **trước** khi che logo, dán chữ, dán phụ đề,
đổi tốc độ và mã hoá lại — tức trả lời về một bản dựng không ai nhận được. Và nó
không phải khác biệt lý thuyết: một chỗ nối có thể đứt mạch **vì** một lớp phủ
bắc qua nó.

### 2.2 Trục thời gian: hai bước, không một

`BanDoThoiGian.ra` (nguồn → biên tập) rồi `bien_tap.moc_ban_ra` (biên tập → bản
ra, chia cho `toc_do`). Rút khung ở giây của trục biên tập trên một tệp đã đổi
tốc độ là rút **nhầm khung**, và càng về cuối phim càng lệch xa.

### 2.3 Đổi ngược chỗ nối → cảnh: thứ biến một phán đoán thành một VIỆC

Một chỗ nối *"ở giây 74 của bản ra"* **không sửa được**: không giai đoạn nào nhận
"giây 74" làm đơn vị việc. Cái sửa được là *"`canh_0011` và `canh_0012` bị bỏ ở
đây"*, và `edit_plan` nhận đúng đơn vị đó.

`cac_cho_noi` đổi ngược từ **khoảng bị cắt trên trục nguồn** (`giu[j-1][1]` →
`giu[j][0]`), không đoán từ số thứ tự cảnh. Khoảng đó trùng nhiều cảnh ⇒ **nhiều**
đơn vị sửa: chọn một cảnh "đại diện" là đoán xem cảnh nào trong hai cảnh đó là cầu
nối cần thiết, và chỉ một lần hỏi lại mới biết.

⚠️ Không có chỉ mục cảnh ⇒ `ma_cat: []` ⇒ phán quyết vẫn **ghi**, việc sửa thì
không. ⛔ Không bịa một mã cảnh để có việc làm.

### 2.4 Một LÁT CẮT, hai vòng lặp

Lô ngữ nghĩa chiếm vị trí `0..so_lo-1` của con trỏ; chỗ nối hình chiếm `so_lo..`.
Hai con trỏ sẽ bắt lượt sau **đoán** xem nửa nào đã xong, và "đoán" ở đây nghĩa là
hỏi (và trả tiền) lại. `du_phong_s` lấy `max` của hai loại đơn vị: đơn vị hình tốn
thêm hai lệnh ffmpeg rút khung trước khi gọi model.

### 2.5 Dùng lại đường đọc đã được làm cứng của làn `fix-toc-do`

`L_FIX_TOC_DO.md` R-05 đo 18 cảnh với lời nhắc cũ: **8/18 hỏng, và mọi lượt hỏng
đều là phản hồi HTTP THÀNH CÔNG có hình dạng sai** — 5 lần `"giữ"` có dấu, 2 lần
trả về một MẢNG, 1 lần bọc `{"objects": [...]}`. **Không lượt nào là model từ chối.**

⇒ Lớp hình ra đời SAU phép đo đó nên nó mang sẵn cả ba bản vá, và **không viết
đường đọc thứ hai**:

* lời nhắc đưa **khung JSON** tường minh, cấm mảng, cấm bọc lớp;
* `qc_ai.chuan_dat` gọi **đúng** `hieu_canh.chuan_ma` (bỏ dấu NFD + `đ`→`d`) —
  `"đạt"` / `"không đạt"` / `"true"` / `1` đều nhận diện được;
* ⛔ nhưng **không nuốt rác**: `"có lẽ"`, `0.5` ra `None` ⇒ `QcAiError`;
* hỏi lại **một lần** và **chỉ** với lỗi hình dạng (`LuocDoSai`/`QcAiError`);
  `AiMoHo` không hỏi lại (không biết model đã chạy chưa), `AiError` trần không
  hỏi lại (đó là câu trả lời về TÌNH TRẠNG, không phải phản hồi rác).

---

## 3. F-10 — vân tay cảnh khoá theo `ma_canh`

`canh_0003` là một **số thứ tự**, không phải một danh tính. Đổi bộ tách cảnh
(làn `ky-thuat`: `select=gt(scene,0.4)` → `ContentDetector(35)`) sinh ra một
`canh_0003` ở **một khoảng thời gian khác hẳn**, và ba trường còn lại của vân tay
đều có thể trùng:

* `ngu_canh` trùng khi cả hai cảnh đều không có thoại (chuỗi rỗng);
* `so_khung` trùng vì `canh.khung` lấy một số khung cố định mỗi cảnh;
* `nguong` là hằng số chính sách, không đổi theo bộ tách.

⇒ Điểm chốt cũ khớp, `_doc_cac_canh` đọc lại `outputs` cũ, và lần chạy dùng một
phán đoán VLM **về một đoạn phim khác**. Không lỗi nào báo.

**Đã sửa:** `van_tay_canh(..., bat=, ket=, muoi=)`.

* mốc **làm tròn mili giây** — mốc cảnh là số thực từ PySceneDetect, hai lần tính
  có thể lệch ở chữ số thứ 15; một vân tay nhảy theo nhiễu dấu chấm động là một
  cache không bao giờ khớp, tức hỏi (và trả tiền) lại mỗi lượt lát cắt;
* `muoi` = số vòng sửa đã đẩy cảnh này về `edit_plan`, kèm lý do QC. Đây là
  **M-07 của đường GIỌNG** áp cho đường HÌNH: cùng vân tay = cùng khoá = cùng kết
  quả cache, nên không muối thì một "vòng sửa" trả về **đúng phán đoán vừa bị báo
  là sai** — một hoá đơn không có sản phẩm.

⚠️ `canh.PHIEN_BAN_CANH` đã vào vân tay GIAI ĐOẠN nên đổi bộ tách làm cả giai đoạn
chạy lại. Nhưng điểm chốt theo ĐƠN VỊ thì không ai vô hiệu — hai tầng khác nhau,
và chỉ tầng dưới trả lời được câu *"`canh_0003` này có phải `canh_0003` kia không"*.

---

## 4. Số đo trên phim thật

<!-- PLACEHOLDER_SO_DO -->

---

## 5. Quyết định: lớp này **TƯ VẤN**, chưa gate

<!-- PLACEHOLDER_QUYET_DINH -->

---

## 6. Phép kiểm

| Tệp | Bài | Hỏi gì |
|---|---|---|
| `tests/test_2120_asv_qc_hinh.py` | 49 | §1 đổi ngược chỗ nối → cảnh (kể cả trục tốc độ, kể cả khi thiếu chỉ mục) · §2 `chuan_dat` nhận/không-nuốt-rác, thiếu `dat`/`do_tin` thì NỔ, `doc_hinh` nhận CẢ kết quả · §3 lời nhắc mang khung JSON + thứ tự hai ảnh · §4 chính sách tư vấn, trần vòng sửa, muối vân tay · §5 F-10 hai chiều · §6 một bản sao `rut_khung` |
| `tests/test_2121_asv_qc_hinh_cho_noi.py` | 4 | **CHỖ NỐI**: chạy HẾT chuỗi với `LTT_ASV_QC_AI=1`; preset cắt phải có phán quyết THẬT cho MỌI chỗ nối; preset giữ hình 0 chỗ nối **kèm lý do**; phán quyết tới `stage.outputs`; một chỗ nối hỏng KHÔNG giết lần chạy |

**Đối chứng cho `test_2121`** (một phép kiểm chỗ nối phải chứng minh được là nó
bắt): bỏ lời gọi `_soat_hinh` khỏi `giai_doan_qc_ai.chay` ⇒ **3/4 bài đỏ**. Một bộ
kiểm xanh cả khi mã bị gỡ là một bộ kiểm không đo gì.

Tệp cũ phải đổi theo — không tệp nào bị nới lỏng mệnh đề của nó:

* `test_2025::test_luot_thu_lai_DUNG_ma_dispatch_KHAC` — khoá chuyển từ một chuỗi
  `f"{c.ma}:lai{lan}"` viết tại chỗ sang `_ma_don_vi_goi(...)` vì nó nay mang
  **chiều thứ hai** (số vòng sửa: hai lượt gọi thật ở hai vòng khác nhau mà trùng
  `ma_dispatch` thì bút toán của lượt sau bị `UNIQUE(run_id, ma_dispatch)` nuốt).
  Chốt bằng **hành vi** của hàm đó thay vì bằng một chuỗi con — mạnh hơn, và chốt
  được cả chiều mới.
* `test_445::test_moi_don_vi_chi_xuat_hien_MOT_lan_trong_ke_hoach_gon` — mệnh đề
  của nó là ĐỊNH TUYẾN (`cat_sai` → `edit_plan`), không phải chính sách tư vấn.
  Tắt `QC_HINH_LA_TU_VAN` bằng `monkeypatch` **cho riêng bài đó**, không hạ cờ ở
  sản phẩm (khuôn của `L_FIX_TOC_DO.md` §Phép kiểm).
* `tests/fixtures/asv_media.phan_hoi_ngoai_dich` — thêm nhánh `QC_HINH` (mặc định
  ĐẠT). Đây đúng là chỗ docstring của nó nói: *"Thêm một thao tác AI mới thì chỉ
  phải sửa MỘT chỗ."*

---

## 7. Công cụ đo

`tools/do_qc_hinh.py` (mới), gọi qua `setup\do_on_dinh.ps1 -Do qc-hinh` (tập đóng
tên công cụ nằm TRONG mã — script đó cố ý không nhận một đường dẫn tuỳ ý, vì nó
nạp `app.env`).

Nó chạy **đúng đường sản phẩm**: `canh.phan_tich` (PySceneDetect ContentDetector
35) → ffmpeg `trim`+`concat` crf23 (hình dạng của `CAT_MA_HOA_LAI`) →
`qc_ai.cac_cho_noi` → `canh.rut_khung` → `ai.goi(QC_HINH)` → `qc_ai.doc_hinh`.

`--khong-model` chạy hết bộ đo mà **không tiêu một token nào** — một bộ đo chưa tự
chạy được trên đường khô thì mọi con số của nó đều là một giả thuyết.

---

## 8. Việc còn lại

<!-- PLACEHOLDER_CON_LAI -->
