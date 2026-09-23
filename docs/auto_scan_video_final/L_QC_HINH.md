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

### 4.1 Bộ đo có hai vế, và một vế có đáp án biết trước

| vế | dựng thế nào | đáp án |
|---|---|---|
| `cat_canh` | nối hai cảnh THẬT không liền nhau (bỏ mọi cảnh thứ 3) | **chưa biết** → người đo xem hai khung rồi gắn nhãn tay |
| `nhay_hinh` | cắt mất 1,5 s ở **giữa** một cảnh dài liên tục rồi nối lại | **BIẾT TRƯỚC: hỏng** (jump cut) |

⭐ Vế `nhay_hinh` là **đối chứng dương**. Nếu bộ đo không bắt được loại này thì
mọi con số ở vế kia đều vô nghĩa — ta chưa chứng minh phép đo NỔ được.

Khung hình của vế đó đã **kiểm bằng mắt**: cặp khung hai bên một `nhay_hinh`
trên v3 cho thấy đúng một jump cut — cùng phòng, cùng nhân vật, nhưng bộ đếm HUD
nhảy (95 → 94), phụ đề đổi giữa câu, nhân vật đã xoay. Chân lý nền của vế này là
**thật**, không phải một nhãn tự gán.

⚠️ **Giới hạn phải nói ra — trùng giới hạn làn `ky-thuat` đã ghi:** v3/v4 là cảnh
game; camera trong game cắt liên tục nên mắt người không phân biệt được "cắt
dựng" với "chuyển camera". `L_KY_THUAT.md` §3 đã loại v3/v4 khỏi chân lý nền cắt
cảnh vì đúng lý do đó, và lý do đó áp y nguyên cho việc gắn nhãn tay ở đây.
⇒ Chấm điểm trên **v1 + v2** (cảnh đời thật, gắn nhãn được); v3/v4 chỉ đo CHI PHÍ.

### 4.2 SO_DO_KET_QUA

<!-- KET_QUA -->

### 4.3 Chi phí

<!-- CHI_PHI -->

---

## 5. Quyết định: lớp này **TƯ VẤN**, chưa gate

`sua_chua.QC_HINH_LA_TU_VAN = True` — phán quyết đi vào báo cáo, `stage.outputs`
và bề mặt vận hành, nhưng **không sinh việc sửa**.

**(a) Độ chính xác đo được là quá thấp để tiêu tiền.** Người đo mở **cả hai
khung** của từng chỗ nối bị chấm `dat=false` rồi trả lời đúng câu mà model được
hỏi: **8/8 cái đã soi là báo động giả** (`bang_chung/qc_hinh/NHAN_TAY.md`).

Và chúng không phải những cái model lưỡng lự: **9/10** cái bị chấm mang
`do_tin` ≥ 0,70, tức **vượt** `DO_TIN_TOI_THIEU` và sẽ sinh việc sửa thật nếu
bật cổng.

⇒ Không phải "chưa chắc chắn". Là **sai, và sai một cách tự tin**.

**(b) `cat_sai` là vòng sửa ĐẮT NHẤT của hệ, độc lập với độ chính xác.**
`edit_plan` là giai đoạn **sớm nhất** của chuỗi, nên đặt lại nó kéo theo
`content_process` + `voice_synthesis` + `timing_align` + `compose` + `render` +
cả ba lớp QC. Làn `fix-toc-do` đo được `voice_synthesis` = **~190 s** cho một
phim 107 s *sau khi đã tối ưu 5×* (943 s trước đó). Tức một báo động giả ở đây
không phải "một lần hỏi lại" — nó gần bằng **một lần chạy lại cả chuỗi**.

⇒ Cái giá hai chiều **không bằng nhau**. Bỏ sót một chỗ nối hỏng: khách nhận một
bản dựng có một chỗ giật — thấy được, khiếu nại được, và `qc` tất định vẫn gác
mọi lỗi kỹ thuật. Báo động giả: một hoá đơn gần bằng cả lần chạy, trên một lần
chạy không ai bảo là sai.

⭐ Nhưng **dây đã nối đủ**, không phải nối một nửa: `jobs._qc_hinh` →
`sua_chua.lap_ke_hoach(qc_hinh=)` → `cat_sai` → `edit_plan` với **một đơn vị cho
mỗi cảnh bị bỏ**, và `test_2120` §4 chốt cả hai chiều của cờ. Bật nó là **đổi một
hằng số**, không phải viết thêm một tầng. Đó là khác biệt giữa cái này và M-02
(một năng lực định nghĩa xong rồi không ai gọi).

### 5.1 Vòng sửa có DỪNG không — có, bằng cơ học

Một chỗ nối hỏng **có thể không sửa được**: hai cảnh hai bên vốn là hai cảnh khác
nhau, và không cảnh bị bỏ nào là cầu nối. Khi đó mọi vòng sửa đều cho ra đúng
phán quyết cũ.

| chặn | ở đâu | cơ học |
|---|---|---|
| **1 vòng cho một lần chạy** | `sua_chua.VONG_SUA_TOI_DA = 1` | đếm bằng **số dòng sổ cái** (`UNIQUE(run_id, ma_dispatch)`), không bằng một biến trong bộ nhớ — bền qua worker chết, không bị hai lượt `advance` cùng tăng |
| hết vòng ⇒ **giao hàng, không giết lần chạy** | `jobs._sua_chua_neu_can` | ghi `sua_chua_con_lai` vào sổ cái rồi đi tiếp; `qc` (tất định) vẫn là cổng phát hành |
| vòng sửa phải hỏi một câu **KHÁC** | `hieu_canh.van_tay_canh(muoi=)` + `loi_nhac_canh(phan_hoi_qc=)` | không muối thì cache trả về đúng phán đoán vừa bị báo sai (M-07) — tức một vòng sửa **không thể** sửa được gì mà vẫn tính tiền |

`test_2120::test_VONG_SUA_CO_TRAN_nen_mot_cho_noi_KHONG_SUA_DUOC_se_DUNG` chốt
chặn thứ nhất; `test_vong_sua_MUOI_van_tay_canh_...` chốt chặn thứ ba.

### 5.2 Điều kiện để bật gate

1. Vế `nhay_hinh` (đối chứng dương) phải **bắt được gần hết** — bộ đo chưa nổ
   được thì chưa đo được gì.
2. Gắn nhãn tay **cả hai phía**: mọi chỗ nối bị chấm `dat=false` **và** một mẫu
   đối chứng các chỗ nối được chấm `dat=true`. ⛔ Chỉ xem cái bị chấm hỏng thì
   không đo được recall — *"không đối chứng thì số không không phải phát hiện"*.
3. Chỉ khi độ chính xác của `dat=false` đủ cao so với cái giá ở (b) mới đổi cờ —
   và đổi **kèm** bảng số ở §4, không đổi một mình.

---

## 6. Phép kiểm

| Tệp | Bài | Hỏi gì |
|---|---|---|
| `tests/test_2120_asv_qc_hinh.py` | 49 | §1 đổi ngược chỗ nối → cảnh (kể cả trục tốc độ, kể cả khi thiếu chỉ mục) · §2 `chuan_dat` nhận/không-nuốt-rác, thiếu `dat`/`do_tin` thì NỔ, `doc_hinh` nhận CẢ kết quả · §3 lời nhắc mang khung JSON + thứ tự hai ảnh · §4 chính sách tư vấn, trần vòng sửa, muối vân tay · §5 F-10 hai chiều · §6 một bản sao `rut_khung` |
| `tests/test_2121_asv_qc_hinh_cho_noi.py` | 6 | **CHỖ NỐI**: chạy HẾT chuỗi với `LTT_ASV_QC_AI=1`; preset cắt phải có phán quyết THẬT cho MỌI chỗ nối; preset giữ hình 0 chỗ nối **kèm lý do**; phán quyết tới `stage.outputs`; một chỗ nối hỏng KHÔNG giết lần chạy; thiếu một khung ⇒ **không hỏi** thay vì hỏi bằng một ảnh; và **vòng sửa** nhắm đúng `edit_plan` + có trần + hỏi lại THẬT (bút toán `:sua1`) |

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

<!-- CON_LAI_DO -->
* **Lệnh đo cần quyền Administrator** — nó đọc `C:\LTTPlatform\secrets\app.env`
  (ACL đúng, ⛔ đừng nới) để lấy `LTT_DATABASE_URL` + `LTT_TOKEN_ENCRYPTION_KEY`
  cho `api_pool` chọn khoá gọi máy B. Đây là khuôn `setup\do_on_dinh.ps1` mà các
  làn `ngan-sach` / `do-giong` / `fix-toc-do` đều đi qua. Chạy ⛔ **KHÔNG** qua
  `chay_nang.py` (xem §7):

  ```
  python tools\nang_quyen.py --cho 5400 --log <tep.log> --lenh ^
    "powershell -NoProfile -ExecutionPolicy Bypass -File ^
     D:\LTTSTUDIOSAPP-asvf-qc-hinh\setup\do_on_dinh.ps1 -Do qc-hinh ^
     -Phim v1,v2 -ThuMucKhung <thu-muc-khung> -Ra <ket-qua.json>"
  ```

  ⛔ `-Phim` phải là **bí danh ASCII** (`v1|v2|v3|v4`). Tên tệp là tiếng Trung và
  `nang_quyen` sinh `.ps1` thuần ASCII, nên `-Phim 廉价` tới nơi thành `--phim ??`
  — lượt đo 23/09 chạy thật với đúng bộ lọc đó, không khớp phim nào, in `BO QUA`
  rồi **thoát 0**: một lượt đo *thành công mà không đo gì*, nhìn từ ngoài giống
  hệt một lượt đang chạy. Nay nó trả `2` và in rõ (`BI_DANH` trong `do_qc_hinh.py`).

* **Chưa đo trên preset có `toc_do` ≠ 1** — phép đổi trục đã có test
  (`test_2120::..._truc_BAN_RA_khi_co_doi_TOC_DO`) nhưng chưa lượt thật nào đi qua.
* **Chưa đo video dọc / ≥ 1080p**, giống hạn chế của làn `ky-thuat`.
* `KHUNG_MOI_CHO_NOI = 2` và `LECH_KHUNG_GIAY = 0,4` **thừa hưởng từ pha 19, chưa
  ai đo**. 0,4 s có thể quá gần chỗ nối (bắt phải khung đang chuyển) hoặc quá xa
  (bỏ sót chính khoảnh khắc nối). Đây là tham số đo được — cùng bộ đo ở §4, chỉ
  đổi một số.
