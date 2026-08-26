# Báo cáo cuối — MVP giao diện khu VPS

**2026-08-27.** Kết quả Đợt 1→7 của `00_KE_HOACH_GIAO_DIEN.md`, dựng từ bộ
prompt `LTT_VPS_MVP_UI_Prompt_Pack_V2` và năm ảnh tham chiếu.

---

## 1. Năm màn hình — PASS / FAIL

| Màn | Route | Trình bày | Sự thật sản phẩm | Bằng chứng trình duyệt |
|---|---|---|---|---|
| **A** Storefront | `/vps` ẩn danh | ✅ PASS | ✅ giữ nguyên | ✅ 6 bề ngang |
| **B** Nhà của khách + tạo | `/vps` đã đăng nhập | ✅ PASS | ✅ giữ nguyên | ✅ 6 bề ngang, 5 trạng thái máy |
| **C** Trung tâm điều khiển | `/vps/{id}` | ✅ PASS | ✅ giữ nguyên | ✅ 6 bề ngang × 5 trạng thái |
| **D** Cài Windows | `/vps/{id}/cai-dat` | ✅ PASS | ✅ giữ nguyên | ✅ 6 bề ngang × 3 trạng thái |
| **E** Console | `/vps/{id}/console` | ⚠️ **PASS một phần** | ✅ giữ nguyên | ⚠️ bố cục ✅, **giao thức chưa kiểm** |

🔴 **Vì sao màn E chỉ PASS một phần, nói thẳng ở đây để không ai trích dẫn
sai:** bố cục, thanh công cụ, trạng thái ban đầu và bề ngang đều đo được bằng
Chrome thật. Nhưng **bắt tay RFB, gõ phím, chuột, Ctrl+Alt+Del, ngắt–nối lại**
thì cần một máy thật trên Proxmox — tức quyết định **D-02**, còn ở chủ sản phẩm.
Prompt 05 đòi phân biệt E2 với E3/E4, và đây là chỗ phân biệt đó.

---

## 2. Bằng chứng đo được

### Ma trận trình duyệt — Chrome thật

```
14 cảnh × 6 bề ngang (1920·1440·1280·1024·768·390) = 84 tổ hợp
  tràn ngang tài liệu ....... 0
  phần tử tràn ngoài khung ... 0   (không kể thứ cuộn được trong khung của nó)
  lỗi console ................ 0
```

14 cảnh: storefront (còn chỗ · hết chỗ) · điều khoản · nhà của khách (0 máy ·
5 máy) · trang máy ở **5 trạng thái** (`dang_chay` `da_tat` `dang_tao` `bi_treo`
`loi`) · cài Windows ở 3 trạng thái · console.

### Trang bán — so với chính nó trước đợt này

| Đo @ 390×844, ẩn danh | Trước 25/08 | Sau 25/08 | **Sau Đợt 2** |
|---|---|---|---|
| Giá đầu tiên (y) | 1121 🔴 *dưới màn hình đầu 277px* | 524 | **323** ✅ |
| `main h1` | 0 | 1 | 1 |
| Nút trong bảng giá | 0 | 3 | 3 |
| Khối `<style>` trong template VPS | 3 | 3 | **0** |

### Bộ test

```
398 phép kiểm khu VPS xanh
  test_311_vps_giao_dien_mvp.py .... 48 (mới)
  16 tệp test VPS còn lại .......... 350
772 chuỗi chưa bọc `_()` — đúng mốc, không tăng
344 chuỗi thiếu bản EN — đúng mốc, không tăng   (110 chuỗi mới đã dịch)
```

---

## 3. Năm hành trình vàng (Prompt 06 §2)

| # | Hành trình | Kết quả | Bằng chứng |
|---|---|---|---|
| **GJ1** | khám phá → so gói → thấy giá/còn chỗ → đường đăng ký | ✅ PASS | cảnh A (còn chỗ **và** hết chỗ) ở 6 bề ngang |
| **GJ2** | chọn gói → chọn OS → tóm tắt/credit → POST tạo | ⚠️ **một phần** | biểu mẫu + tóm tắt sống + fail-closed ✅; **POST thật chưa chạy** |
| **GJ3** | trang máy → cài Windows → console → gỡ đĩa | ⚠️ **một phần** | ba trang liền mạch, cùng danh tính ✅; **cài thật chưa chạy** |
| **GJ4** | bật/tắt/khởi động lại → console → hạn & băng thông | ⚠️ **một phần** | dải nút theo trạng thái ✅ ở cả 5 trạng thái; **lệnh thật chưa chạy** |
| **GJ5** | khôi phục → cài lại → xoá, có cảnh báo và xác nhận | ⚠️ **một phần** | ba ô gõ tên + thứ tự ít-thiệt-hại-trước ✅; **chưa thi hành thật** |

🔴 **Bốn "một phần" đều dừng ở cùng một chỗ, và đó không phải chỗ giao diện:**
mọi thứ **nhìn thấy được** đã kiểm; mọi thứ **chạy thật** cần một máy thật —
quyết định **D-02**. Đợt 1→7 cố ý được thiết kế để chạy đủ mà không cần nó.

Phần **âm** của GJ2 (hết sức chứa · gói hết chỗ · không đọc được sức chứa) thì
kiểm được và **đã kiểm**: cảnh `A_storefront_het_suc_chua` cho thấy fail-closed
đúng — bảng giá còn, `<form>` không dựng, mỗi gói nói **đi đâu** thay vì dừng ở
hai chữ "hết chỗ".

---

## 4. Hồi quy an ninh — không thay đổi hành vi nào

| Hợp đồng | Kết quả |
|---|---|
| Cờ tắt ⇒ 404, cổng cờ trước `require_login` | ✅ không đổi |
| Khách ẩn danh: không vỏ điều khiển, không thấy máy của ai, không `<form>` | ✅ không đổi |
| Máy người khác ⇒ 404 | ✅ không đổi |
| CSRF trên mọi POST | ✅ không đổi (+1 route mới: `doi-ten`) |
| Ba việc phá huỷ đòi gõ đúng tên máy | ✅ không đổi — và **mạnh lên** (D-01) |
| Vé console 60 giây, một lần, không vào URL | ✅ không đổi |
| `resizeSession=false`, không tự nối lại bằng vé đã tiêu | ✅ không đổi |
| Fail-closed sức chứa · không khoá nút khi thiếu credit | ✅ không đổi |

⭐ **D-01 làm rào chắn phá huỷ MẠNH LÊN, không phải yếu đi.** Trước đợt này cột
`ten` luôn rỗng, nên nhánh thật đang chạy là `may.id[:8]` — để xoá máy, khách
phải chép tay `a3f9c1d0`. Khuôn "gõ đúng tên" của GitHub hiệu quả vì cái tên
**có nghĩa với người gõ**; chép–dán không có khoảnh khắc dừng lại đó. Rào chắn
đang chạy ở dạng tệ nhất của nó, và giờ thì không.

**Một hành vi backend đổi, có chủ ý:** `billing.thu_mot_chu_ky` nay chụp
`bang_thong_byte` vào sự kiện `thu_phi` **trước** khi đặt lại (D-04a). Không
bảng mới, không route mới, không đổi gì khách nhìn thấy. Lý do: mỗi chu kỳ trôi
qua mà không chụp là một chu kỳ **mất vĩnh viễn**.

---

## 5. Soát phình phạm vi (Prompt 06 §5)

Mọi thứ thêm vào trong Đợt 2–6, và nó phục vụ hành trình nào:

| Thêm | Vì | Giữ? |
|---|---|---|
| Ô "Tên máy" + `POST /doi-ten` | GJ5 — rào chắn phá huỷ đang chạy ở dạng tệ nhất | ✅ giữ (D-01) |
| Bốn ô chỉ số ở màn B | GJ4 — quét trạng thái đội máy trong một tầm mắt | ✅ giữ |
| Sơ đồ hộp thoại ổ đĩa | GJ3 — bước chọn nhầm thì phải cài lại từ đầu | ✅ giữ (D-03) |
| Nút "Toàn màn hình" ở console | GJ3 — cài Windows trong một khung 74vh | ✅ giữ (API trình duyệt, ~8 dòng) |
| Chụp `bang_thong_byte` | dữ liệu không chụp là dữ liệu mất | ✅ giữ (D-04a) |
| ~~Dải nav mỏ neo trên storefront~~ | không hành trình nào cần | ❌ **bỏ** — trang cao 1282px ở 1440, một mục lục là nhiễu |
| ~~Sắp xếp / chuyển lưới-danh sách~~ | ảnh có, không hành trình nào cần | ❌ **bỏ** |
| ~~Gửi phím tắt ở console~~ | noVNC đỡ được, nhưng chưa test thật được | ⏸️ **hoãn** tới D-02 |
| ~~Trang Ảnh chụp / Băng thông~~ | không có dữ liệu để trang đó nói gì | ❌ **bỏ** (D-04) |

**Không thêm:** telemetry · tiến độ giả · SLA/hỗ trợ · quản lý mật khẩu ·
firewall/DNS/volume/SSH · framework mới · bất kỳ trạng thái lưu nào cho hướng dẫn.

---

## 6. Ba lỗi tự gây ra, và cả ba chỉ thấy được bằng trình duyệt

**(a) Nút vận hành đổi sang MÀU ĐỎ.** `_kieu_chung.html` là khối `<style>` nội
tuyến trong `<head>` **đứng sau** `<link>` tới `ltt.css`, khai
`button, .btn { background: var(--accent) }`. Cùng độ đặc hiệu nhưng đến sau ⇒
thắng. Đo được `rgb(239,55,49)`. Đó cũng chính là lý do bản cũ đặt luật đó trong
`<style>` của template — chuyển sang `ltt.css` mà giữ nguyên độ đặc hiệu là làm
sống lại đúng lỗi mà đợt 25/08 vừa sửa. Sửa bằng `.btn.btn-goi`.

**(b) Tràn ngang 7px ở 390px.** `grid-template-columns:1fr` mặc định là
`minmax(auto,1fr)` — **sàn của nó là min-content**. Phải là `minmax(0,1fr)`.
Trang vẫn render bình thường, chỉ là cuộn ngang.

**(c) Công cụ kiểm mới dính đúng quy tắc 6.** Sửa `ltt.css`, dựng lại, đo lại —
Chrome vẫn trả **màu cũ** vì URL không đổi. Suýt kết luận *"luật mới thua độ đặc
hiệu"* trong khi luật mới **còn chưa tới trình duyệt**. Nay công cụ đính hash
nội dung vào URL tệp tĩnh, đúng như production làm.

**Và ba lần phép kiểm khớp vào chính chú thích của tôi**, gồm một biến thể mới:
cắt lát CSS từ **chính cái mốc** thay vì từ `/*` **mở khối chứa mốc** — lát cắt
bắt đầu giữa một chú thích đang mở, nên bộ bóc ghép lệch một nhịp và **bóc mã,
giữ chú thích**. `_khoi_mo_dau()` nay khẳng định lát cắt không rỗng trước khi
trả về: một lát cắt rỗng làm mọi `assert ... not in` **xanh giả**.

---

## 7. Khoảng trống bằng chứng — nói rõ, không lấp liếm

| Chưa chứng minh được | Vì | Cần gì |
|---|---|---|
| Bắt tay RFB, gõ phím, chuột, Ctrl+Alt+Del, ngắt–nối lại | route console mở phiên VNC **thật** trên Proxmox trước khi render | **D-02** |
| POST tạo/bật/tắt/cài lại/khôi phục/xoá chạy đầu-tới-cuối | cần một máy thật | **D-02** |
| Hành vi thật của job trong worker | như trên | **D-02** |
| Mọi thứ đi qua Cloudflare (cache, CSP biên, minify) | cảnh dựng ở loopback | **deploy** — quy tắc 5b |
| Bản EN **render** của năm trang | mới chốt bằng `.po` + `test_305` | một lượt soi bằng mắt trên `/en/vps` |

⚠️ `tools/vps_dung_mau.py` chứng minh **bố cục, tràn ngang, tương phản, reflow,
và trạng thái nào hiện ra cái gì** — đúng phần mà đọc mã không trả lời được, và
**không hơn**. Docstring của chính nó ghi giới hạn đó.

---

## 8. Còn lại

| Việc | Ai | Ghi chú |
|---|---|---|
| **D-02** · một máy thật cho GJ2–GJ5 | ⏳ chủ sản phẩm | trừ credit thật + Reserved IP; Đợt 1–7 chạy đủ mà không cần |
| Deploy | ⏳ chủ sản phẩm | `/vps` **đang bán hàng thật** — xem §9 |
| Soi bản EN đã render | sau deploy | `test_305` chốt `.po`, không chốt trang |
| `tools/gui/ltt.css` + `ho_so_he_thong.txt` | người commit sau cùng | tệp **dẫn xuất từ cả cây**; một phiên Claude khác đang sửa khu `/developers` trong cùng cây |

---

## 9. ⚠️ Trước khi deploy

1. `/vps` **đang sống và công khai** (`LTT_VPS=1`, GET trả 200 cho khách ẩn
   danh). Đây là thay đổi trên trang **đang bán hàng**, không phải trên bản nháp.
2. Deploy chép **cả cây** `app\` — không tách được phần của một phiên. Kiểm
   `git status`, `alembic head`, và hỏi các phiên Claude khác trước.
3. Sinh lại hai tệp dẫn xuất **ngay trước** khi commit.
4. Kiểm lại trên **URL công khai**, không chỉ loopback: loopback bỏ qua
   Cloudflare (cache, CSP biên, minify) — quy tắc 5b.
5. `tools\gate.py` hiện đỏ ở **2 phép kiểm không thuộc đợt này**
   (`docs/PUBLIC_API/CONTRACT_BASELINE.json` có một mục `image.ghost` với
   `contract_hash` toàn số 0, từ phiên đang làm khu `/developers`). Đã báo phiên
   đó. Mọi bước gate mà đợt này chạm đều PASS.
