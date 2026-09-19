# 06 — Kiểm bằng trình duyệt

**Chromium thật qua `playwright-cli`**, không phải phép kiểm template.
16 trang × 6 khung nhìn = **56 ảnh mỗi lượt** (khung trung gian chỉ chụp 6 trang
tiêu biểu — đủ để bắt vỡ vỏ, không sinh 96 ảnh phải xem bằng mắt).

Chạy lại: `tools/qa/dev_portal_qa.js` · số đo: `evidence/{before,sau}/do_dac.json`

## Môi trường

`tools/dev_portal_harness.py --port 8101` — một bản `/developers` **có dữ liệu**
trên CSDL SQLite tạm.

⚠️ **KHÔNG chạy trên production.** Máy này *là* máy chủ (`C:\LTTPlatform` tồn
tại) và `/api/v1` đang phục vụ khách trả tiền (`text.chat`, `image.ltt`). Bộ
kiểm này **tạo và thu hồi khóa**, và thu hồi thì không đảo ngược được.

Dữ liệu gieo — cố ý gồm cả trạng thái xấu, vì trang chỉ lộ ra khi có gì đó sai:
2 project · 4 khóa (một **đã thu hồi**, một **test**, một có IP/CIDR + hạn) ·
10 dòng nhật ký gồm **402 · 429 · 404 · 422 · 500** · 1 webhook với **3 lần giao
hỏng** · 1 ngân sách.

## Kết quả theo khung nhìn

`main` = bề rộng thật của `.app-main` · `tràn` = số trang làm **tài liệu** cuộn ngang

| Khung | main trước | main sau | tràn trước | tràn sau |
|---|---|---|---|---|
| 1920 | 898 px | **1318 px** | 0 | **0** |
| 1440 | 898 px | **1166 px** | 0 | **0** |
| 1280 | 898 px | **1010 px** | 0 | **0** |
| 1024 | 742 px | **761 px** | 1 | **0** |
| 768 | 720 px | **744 px** | 1 | **0** |
| 390 | 342 px | **366 px** | **6** | **0** |

⭐ Ở 1440 và 1280 bề rộng cũng tăng — `.page--standard` 1180px **cắt cả hai
khung đó**, không riêng 1920. Triệu chứng "nhiều khoảng trắng" chủ sản phẩm nêu
không phải chuyện của riêng màn hình lớn.

## Năm chốt đo được

| Chốt | trước | sau |
|---|---|---|
| ô nhập bị trình duyệt vẽ (viền `inset`) | **42** *(7 ô × 6 khung)* | **0** |
| `fieldset` viền `groove` | **18** *(3 × 6)* | **0** |
| tài liệu tràn ngang | **8** | **0** |
| lỗi console | 0 | **0** |
| phản hồi ≥ 400 | 0 | **0** |

Kiểu so được đo **bằng `getComputedStyle`**, không bằng mắt:

```
truoc  input#key-name   bg rgb(59,59,19)   2px INSET rgb(133,133,133)  radius 0   pad 1/2px
sau    input#key-name   bg rgb(27,20,19)   1px solid rgb(56,36,34)     radius 6px pad 9/10px
       select#key-project  ← giống hệt, và trước đây hai ô này nằm cạnh nhau
```

## Hồi quy ngoài khu API

`_kieu_chung.html` chạm **mọi trang của nền tảng**, nên quét 18 đường ngoài
`/developers`. 14 trả 200 (4 route tắt bằng cờ ở bản chạy cục bộ):

`/` · `/gia-api` · `/huong-dan` · `/huong-dan/cong-cu` · `/nap` · `/taoanh` ·
`/thumbnail` · `/chataistudio` · `/taovideo` · `/taoclipngan` · `/upscalevideo` ·
`/autosubvideo`

Kết quả: **0 trang vỡ**, 0 ô nhập viền `inset` còn sót, 0 `fieldset` groove.

⚠️ **Một cảnh báo thật, đã bắt được và đã rút lại.** Lượt quét thấy
`/autosubvideo` có chín nút cao 93px, `display:grid`, là các thẻ mẫu chữ tự vẽ.
Chúng **không** phải hồi quy — chúng vốn thế. Nhưng `white-space:nowrap` tôi vừa
thêm vào `.btn` **sẽ** kế thừa vào chữ mẫu bên trong chúng. Không nguyên nhân
gốc nào đòi thuộc tính đó ⇒ đã bỏ. *(Nếu chỉ nhìn ảnh chụp `/developers` thì
không bao giờ thấy.)*

⚠️ **Một tồn tại ngoài phạm vi, không phải của tôi:** `/huong-dan/cong-cu` tràn
ngang ở 390px (tài liệu 420 > 390, thủ phạm là một phần tử `code` rộng 462px).
Có **trước** mọi thay đổi trong lượt này. Trang công khai, thuộc phạm vi
`docs/ui_stabilization/` (nay lưu trữ ở `docs/_luutru/2026-09/ui_stabilization/`) của phiên khác.

## Ảnh chụp

`evidence/before/<khung>/<trang>.png` và `evidence/sau/<khung>/<trang>.png`
— cùng tên tệp, xem cạnh nhau được.

`evidence/b1 · b2 · b3 · b4 · b6` là ảnh của từng đợt, giữ lại làm dấu vết.
⚠️ Bảy thư mục × ~8 MB = **~59 MB**. Xoá năm thư mục giữa đi trước khi commit:

```bash
rm -rf docs/developer_portal_mvp_ui/evidence/b{1,2,3,4,6}
```

## Trạng thái đã soi tận mắt

| | |
|---|---|
| có dữ liệu | bảng khóa 4 hàng, nhật ký 10 dòng có 5 lỗi, webhook 3 lần hỏng |
| rỗng | nhật ký lọc không khớp · project · job · thông báo · ngân sách |
| bí mật | khối hiện-một-lần sau khi tạo **và** sau khi đổi |
| lỗi | 401/403/429/422/500 trong bảng nhật ký, mỗi mã một màu ngữ nghĩa |
| chữ dài | `key_id` 32 ký tự · URL webhook · 6 scope trong một ô · 2 dải CIDR |
| di động | 390px: thanh bên thành dải cuộn ngang, form xếp dọc, bảng cuộn **trong** vỏ |
