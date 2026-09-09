# 2026-09-09 — `chuyen_loi_thoai` hỏng vì **trần token ra 4.096**, không vì máy B

**Loại tệp: ĐÓNG BĂNG.** Đây là ảnh chụp một lô đo cụ thể, không phải tệp cuộn.
Không lượt chạy nào ghi đè nó. Xem `README.md` cùng thư mục để biết vì sao hai
loại tệp ấy phải phân biệt được từ cái tên.

---

## Câu hỏi

Lượt nghiệm thu 09/09 (`nghiem_thu_hien_hanh.json`, `ghi_luc 12:31:14`): preset
`giu_hinh` chết ở `content_process` **ba lần liên tiếp**, mỗi lần một dòng:

```
chuyen_loi_thoai: model tra ve rong
```

Preset `cat_thong_minh` nhận **đúng cùng bản ghi ASR** (6 câu, giống hệt từng
chữ), cùng giọng `Minh Đức`, cùng model — và xong ngay lần đầu.

**Bốn phiên liên tiếp** đọc dòng ấy thành *"máy B hỏng"*.

## Máy B không hỏng — đo được

Bước ①, 30 lượt gọi thật, có đối chứng xen kẽ:

| | kết quả |
|---|---|
| `chuyen_loi_thoai` (nghi ngờ) | **0/15 hỏng**, p50 19,7 s |
| `rut_ngan_cho_vua` (đối chứng) | **0/15 hỏng**, p50 19,9 s |

⇒ Máy B phục vụ bình thường. Lỗi cũng **không ngẫu nhiên**.

## Nguyên nhân: `TOKEN_RA_MAC_DINH["job"] = 4.096`

`ai.tran_token_ra()` đọc `apps/ltt_llm/ngan_sach.py`, cửa **`job`** = **4.096**.

Bước ②, 6 vòng, **cùng một lời nhắc**, đối chứng nằm **trong cùng lượt đo** —
biến số duy nhất là trần:

| trần | hỏng | `finish_reason` | `token_ra` |
|---|---|---|---|
| **4.096** (đang chạy thật) | **6/6 = 100 %** | `length` × 6 | 4.096 × 6 (chạm trần) |
| **12.288** (đối chứng) | **0/6 = 0 %** | `stop` × 6 | 5.868 · 7.526 · 6.422 · 6.406 · 5.201 · **4.517** |
| 4.096, đầu vào ngắn (đối chứng) | 0/6 | `stop` × 6 | ~1.000–1.150 |

Cả **ba** hình dạng lỗi của 09/09 đều dựng lại được từ **một** biến số:

| `noi_dung` | thông điệp sinh ra |
|---|---|
| 0 ký tự | `model tra ve rong` ← nguyên văn 09/09 |
| 154 ký tự | `phan hoi khong chua doi tuong JSON nao` |
| 561 ký tự | `JSON hong (Expecting ...)` ← nguyên văn 09/09 |

Thứ tự sinh là **suy nghĩ trước, nội dung sau** (cổng chạy
`--reasoning-format deepseek`), nên mỗi lần chạm trần đều cắt vào đúng phần
mang ý nghĩa. Khối `<think>` chiếm **~93 %** token ra.

### ⛔ Không phải "xui" — trần nằm **dưới sàn** nhu cầu

Lần **nhẹ nhất** trong 6 mẫu vẫn cần **4.517** token ra, tức trên 4.096.

### ⚠️ Một con số ở bản nháp tệp này đã SAI, và nó từng là tiêu đề

Bản nháp viết: *"lượt production xanh tiêu 3.985 token — 97,3 % trần 4.096"*.

**So sai đơn vị.** `so_luong` trong sổ kê là `token_vao + token_ra`
(`ai.py:505`), còn `max_tokens` đi thẳng vào thân OpenAI (`cong_vlm.py:208`) nên
nó chặn **completion tokens** — chỉ đầu ra. Một tổng không so được với một trần
chỉ chặn một nửa của tổng ấy.

Và phần tách **không đo lại được**: `_ghi` có ghi `token_vao`/`token_ra` riêng
vào `ghi_chu`, nhưng tệp chứng cứ chỉ mang `so_luong`, còn CSDL của lượt nghiệm
thu là SQLite dùng-một-lần đã biến mất cùng thư mục tạm. Nên câu đúng duy nhất
nói được về lượt production ấy là: **tổng 3.985, phần tách không biết.**

⇒ Kết luận **không đổi**, vì nó không dựa vào con số ấy: 6/6 mẫu `token_ra` đo
  trực tiếp đều vượt 4.096, thấp nhất 4.517. Nhưng một con số sai đứng ở vị trí
  tiêu đề thì lần sau sẽ có người trích nó.

Đây đúng hình dạng *"phanh luôn ăn tệ hơn không có phanh"*: một trần đặt **dưới**
nhu cầu bình thường biến thất bại thành **mặc định**. Và ba lần thử lại ở cùng
một trần chỉ là ba lần tung lại đúng đồng xu ấy — `LuocDoSai` được `loi.py` xếp
`TAM_THOI` với lý do *"model là ngẫu nhiên, nên một lần sinh hỏng thường hết ở
lần sau"*. Lý do ấy **đúng cho một dao động, sai cho một trần**.

## 🔴 Vì sao bốn phiên đi nhầm chỗ

`platform_core/llm/cong_vlm.KetQuaChat` **đã** bóc sẵn `finish_reason` và
`suy_nghi`. `apps/auto_scan_video/ai.goi` **vứt cả hai đi** khi đóng gói lại
thành dict, và mỗi người gọi viết `ai.doc_json(kq.get("noi_dung") or "", ...)`.

⇒ Dấu vết tồn tại ở tầng dưới; nó chỉ không đi qua được cửa ấy. Một thông điệp
lỗi không nói được `finish_reason` bắt người đọc đi đo lại thứ hệ thống **đã** đo.

Và chú thích ở đầu công cụ đo bước ① từng ghi: *"`max_tokens` = 32.768 nên TRẦN
không phải nguyên nhân"*. 32.768 là trần cửa **`stream`**; ASV đi cửa **`job`**.
Một giả định không đo, viết ra như một sự thật, đã loại đúng nguyên nhân thật
khỏi tầm nhìn.

## 🔴 Rào **thứ hai**, và nó nguy hiểm hơn rào thứ nhất

Sáu lượt thành công ở trần 12.288, sắp theo token:

| giây | `token_ra` |
|---|---|
| 65,8 | 4.517 |
| 75,3 | 5.201 |
| 84,6 | 5.868 |
| 94,4 | 6.406 |
| 94,9 | 6.422 |
| **107,7** | **7.526** |

Tuyến tính sạch, ~70 token/giây. Và `platform_core/llm/dieu_phoi.goi` có
`timeout_s: float = 120.0`; `ai.goi` **không truyền** tham số này.

⇒ Lượt chậm nhất cách trần thời gian **10 %** — với một lô **6** đoạn, trong khi
`long_tieng.DOAN_MOI_LO = 12`.

**Nâng `max_tokens` một mình sẽ làm mọi thứ tệ hơn:**

| hỏng vì | ngoại lệ | `loi.phan_loai` | hậu quả |
|---|---|---|---|
| hết token | `LuocDoSai` | `TAM_THOI` | thử lại được |
| hết thời gian | `AmbiguousProviderError` | **`MO_HO`** | **dừng lần chạy, chờ người** |

Tiền đã tiêu ở cả hai, nhưng ở cái thứ hai còn không ai biết model đã chạy chưa.

⇒ Đây là *"hai rào bị gộp làm một"*: gỡ một rào rồi để nguyên rào kia mà không
kiểm. Bản sửa phải mở **cả hai**, và cả hai đều phải lấy số từ đo.

### ⛔ BẤT BIẾN — ghim lại

> **Không bao giờ giao trần token mà không giao trần timeout cùng lượt.**

Vì hệ quả không phải "sửa được ít hơn" mà là **sửa xong hệ tệ đi**: hỏng ít lần
hơn, nhưng mỗi lần hỏng đắt hơn nhiều và cần người can thiệp — `AiMoHo` dừng
lần chạy và chờ quyết định, trong khi `LuocDoSai` chỉ thử lại.

Dạng tổng quát, đáng nhớ hơn ca cụ thể:

> Một trần nới ra làm **lộ trần kế tiếp**. Nếu trần kế tiếp có **hạng lỗi nặng
> hơn**, thì thứ tự giao hàng không còn là chuyện tiện tay.

### ⚠️ Hai rào KHÔNG độc lập — mỗi phép đo phải khai cấu hình của rào kia

Token cao hơn ⇒ thời gian dài hơn (đo được: ~70 token/giây, tuyến tính). Nên
mọi con số ở tệp này đều **đo với cả hai rào đã nới** (`--tran`, `--timeout`).
Chúng nói model **cần** bao nhiêu; chúng **không** nói gì về hệ khi một trong
hai rào vẫn ở giá trị cũ. Mỗi lô đo ghi kèm cấu hình của rào kia, ngay trong
dòng cuối bản ghi.

## Cùng cái bẫy còn ở đâu

| nơi | cỡ lô | đã hỏng chưa |
|---|---|---|
| `long_tieng.DOAN_MOI_LO = 12` → `chuyen_loi_thoai` | 12 | **rồi** (đo ở trên, và mới chỉ đo lô 6) |
| `qc_ai.DOAN_MOI_LO = 10` → `qc_ngu_nghia` | 10 | chưa — vì **chưa lần nào chạy với model thật** |
| `hieu_canh` → `doc_canh` | 1 cảnh | chưa — 1.258 token/lượt trung bình |
| `dich_thuat.DOAN_MOI_LO = 20` | 20 | đường v2, đã chết từ pha 14 |

## Lô **12** — kích thước lô thật của sản phẩm — vượt **cả hai** rào

`long_tieng.DOAN_MOI_LO = 12`. Bộ nghiệm thu chỉ dựng video **6 câu**, tức
**nửa lô**, nên nó chưa bao giờ chạm tới bức tường thật.

Đo với **cả hai rào đã nới** (trần token 24.576, timeout 900 s), 3 vòng, tất cả
`finish_reason = stop`, 0 hỏng:

| cỡ lô | `token_ra` | giây |
|---|---|---|
| 6 | 5.039 · 5.278 · **7.915** | 75,7 · 78,8 · 117,3 |
| **12** | **10.248** · 9.642 · 6.948 | **151,0** · 142,6 · 102,3 |

| rào | đang chạy thật | lớn nhất quan sát | |
|---|---|---|---|
| `max_tokens` | 4.096 | **10.248** | vượt **2,5 ×** |
| `timeout_s` | 120 s | **151,0 s** | vượt **1,26 ×** |

### ⛔ Đường thẳng theo cỡ lô **không vững** — đừng dùng nó

Bản nháp tệp này (và commit `3eae396d`) ghi `ra(n) ≈ 310 + 828·n`, khớp từ **2**
vòng đầu. Vòng 3 lật nó: lô 6 nhảy lên 7.915 còn lô 12 tụt xuống 6.948.

⇒ Hai phân bố **chồng lên nhau**: `max(n=6) = 7.915` **>** `min(n=12) = 6.948`.
Với n=3 mỗi điểm, độ dốc theo cỡ lô không tách được khỏi nhiễu, và khớp hai điểm
trên hai giá trị **max** cho ra một đường đổi hẳn hình dạng khi thêm một mẫu —
dấu hiệu kinh điển của việc khớp vào nhiễu.

Kết luận đúng và chắc hơn một độ dốc: **nhu cầu bị chi phối bởi khối suy nghĩ,
lớn và biến động mạnh, chứ không bởi cỡ lô.** Nên trần phải vượt **giá trị lớn
nhất quan sát được** kèm biên, không đặt theo một công thức tuyến tính chưa đủ
mẫu. Muốn dùng công thức thì phải đo lại với n đủ lớn ở mỗi điểm (≥ 10 mẫu).

### 🔑 Đây là thứ giải thích vì sao lỗi **trông như** xác suất

Ở **nửa lô** (6 đoạn) nhu cầu ~5.000 nằm sát ngay trên trần 4.096 — kết quả
trông ngẫu nhiên, và ba lần thử lại trông như xui.

Ở **lô đầy** (12 đoạn) nhu cầu 10.248 trên trần 4.096: không ngẫu nhiên gì cả.
Đó là một bức tường. Bộ nghiệm thu không thấy nó vì đầu vào của nó quá ngắn.

## ⚠️ Thứ KHÔNG làm trong lượt này, và vì sao

Khối `<think>` chiếm **~93 %** token ra. Cổng chạy `--reasoning-format deepseek`
với template mặc định `reasoning_effort = medium`, và
`platform_core/llm/cong_vlm.chat` **đã** nhận tham số `reasoning_effort` —
`ai.goi` chỉ chưa mở đường.

Hạ nó xuống `low` cho một phép biến đổi JSON cơ học nghe rất hợp lý, và nó sẽ
cắt phần lớn cả token lẫn thời gian — tức sửa **cả hai** rào cùng lúc, rẻ hơn
nhiều so với nới chúng ra.

⛔ **Nhưng đó là một thay đổi CHẤT LƯỢNG đầu ra, và chưa ai đo.** Gộp nó vào một
bản vá lỗi sẽ làm hai thứ không tách được: nếu bản lồng tiếng xấu đi, không ai
biết là vì trần mới hay vì suy nghĩ ít đi.

⇒ Phép đo riêng cần làm sau: cùng một lô, `medium` so `low`, chấm **chất lượng
  bản lồng tiếng** (đủ đoạn, đúng bảng từ vựng `CAM_XUC`/`KIEU_NOI`, độ dài đọc
  vừa `thoi_luong_giay`) chứ không chỉ chấm "có parse được JSON không". Chỉ đổi
  khi chất lượng không giảm.

## Cách dựng lại

```
powershell -ExecutionPolicy Bypass -File .\setup\do_on_dinh_nang_quyen.ps1 -Vong 6
powershell -ExecutionPolicy Bypass -File .\setup\do_on_dinh_nang_quyen.ps1 -Vong 3 -Do ngan-sach
```

Cần quyền Administrator (đọc `secrets\app.env`, ACL của nó là **đúng**, đừng nới
lỏng) và cần **suất máy B** — `DONG_THOI_MAY_B = 1`.

Nhật ký gốc: `C:\LTTPlatform\logs\do_on_dinh-20260909-140327.out.log`.
