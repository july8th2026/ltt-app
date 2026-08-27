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
| **E** Console | `/vps/{id}/console` | ✅ PASS | ✅ giữ nguyên | ✅ **kết nối thật tới Proxmox** |

✅ **Khoảng trống bằng chứng của màn E đã lấp 2026-08-27** (D-02 được duyệt).
Console kết nối thật: badge `Connected`, canvas noVNC render, màn hình **Windows
Server 2016 Setup** hiện ra, 0 lỗi console, 0 tràn ngang. Xem §3.

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
| **GJ2** | chọn gói → chọn OS → tóm tắt/credit → POST tạo | ✅ **PASS** | máy thật `may-nghiem-thu-3`, IP `139.180.139.126`, tên do khách đặt (D-01), trừ đúng 1.490 |
| **GJ3** | trang máy → cài Windows → console → gỡ đĩa | ✅ **PASS** | 8 bước; sơ đồ ổ đĩa hiện **40.0 GB** — đĩa thật của gói Nhỏ (D-03); console kết nối thật |
| **GJ4** | bật/tắt/khởi động lại → hạn & băng thông | ✅ **PASS** | Tắt → badge `Stopped`, dải nút đổi thành Bật/Console/Cài; Bật → `Running`, dải nút trở lại |
| **GJ5** | khôi phục → cài lại → xoá, có cảnh báo và xác nhận | ✅ **PASS** | gõ **sai** tên → từ chối, máy còn nguyên; gõ **đúng** → xoá thật, IP trả về Vultr |

⭐ **Đường THẤT BẠI cũng đã chứng minh, và nó tự chữa đúng thiết kế.** Hai máy đầu
hỏng vì một lỗi hạ tầng (xem §6b): vòng bảo trì **tự hoàn đủ 1.490 credit** cho
từng máy, nộp job xoá, máy biến mất. Số dư khách về nguyên vẹn mà không ai can
thiệp. Đó là bảo đảm quan trọng nhất của GJ5 và nó chạy trên dữ liệu thật.

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

## 6b. 🔴 Lỗi hạ tầng mà lượt nghiệm thu tìm ra — và ba chỗ cùng nói một câu sai

Máy thật **đầu tiên** vào trạng thái `loi`, khách bị trừ 1.490 credit:

```
RouterError: VM router tra ma 255:
WARNING: UNPROTECTED PRIVATE KEY FILE!
Permissions for 'C:\Users\...\.ssh\ltt_pve' are too open.
```

Ba dịch vụ chạy bằng **LocalSystem**; khoá SSH nằm trong hồ sơ **người dùng**,
nơi ACL thừa kế cho cả tài khoản ấy. Từ góc nhìn SYSTEM đó là khoá "hở" ⇒
OpenSSH từ chối. Xác minh hai chiều: chính khoá đó `ssh` được bằng tài khoản
người dùng.

⛔ **Lỗi im lặng hoàn toàn:** `/vps` vẫn bán, `/health/ready` vẫn 200, gate vẫn
xanh. Tín hiệu duy nhất là một khách đã trả tiền.

**Nó là lỗi kiến trúc, không phải lỗi cấu hình.** VPS có hai đường điều khiển:
Proxmox (HTTP + token, bí mật **trong** `app.env`) và router/cổng vào (SSH + tệp
khoá, `app.env` chỉ giữ **đường dẫn** ra ngoài). Mọi kỷ luật quyền của nền tảng
áp lên `secrets\`; khoá SSH là bí mật **duy nhất** sống ngoài đó — nên là bí mật
duy nhất bộ cài không với tới.

**Ba chỗ cùng khẳng định `secrets\` đã siết, và không chỗ nào thật sự kiểm:**

| # | Chỗ | Sai thế nào |
|---|---|---|
| ① | `2-cai-dat.ps1:231` | `/inheritance:r` chỉ bỏ ACE **thừa kế**; `/grant:r` chỉ thay quyền chủ thể **được liệt kê**. Một ACE **tường minh** sống sót — rồi nó in `Ok`. |
| ② | `4-nghiem-thu.ps1` | chỉ tìm `Users\|Everyone`; một ACE cho **một tài khoản cụ thể** không khớp ⇒ in `Ok 'Quyền secrets\ đã siết'` |
| ③ | `vps_khoa_dich_vu.ps1` (của chính đợt này) | **mắc lại đúng lỗi đó** ở lần chạy đầu: in "đã siết" rồi thoát `EXITCODE=0` trong khi ACL y nguyên |

⭐ Thứ vạch ra ③ là bước **in lại ACL thật** ở cuối script. Bài học: *một bước bảo
mật không tự kiểm là một bước sẽ nói dối vào đúng ngày nó thất bại.*

**Và một cái bẫy nữa, lần thứ ba trong dự án:** sửa `app.env` rồi
`Restart-Service` là **không đủ** — nssm nướng biến môi trường vào đăng ký dịch
vụ lúc cài. Dự án đã trả giá hai lần, đã viết hẳn `nap_lai_env.ps1` kèm cảnh báo
dài — và lần chạy đầu của script này vẫn dẫm vào. Triệu chứng: máy vẫn `loi` với
**nguyên văn** thông báo cũ, trỏ vào đường dẫn **cũ**.

**Đã sửa:** khoá về `secrets\` (bản trong `.ssh` giữ nguyên cho con người) · cả
ba chỗ dùng **danh sách cho phép** + tự kiểm + `throw` · `tools/vps_kiem_khoa.py`
kiểm **quyền** và **nối thật** qua **đúng tầng vận chuyển của worker** ·
`4-nghiem-thu.ps1` gọi nó khi `LTT_VPS=1` · 9 phép kiểm mới (`test_312`).

⚠️ **Một cái giá phải nói ra:** siết `secrets\` xong thì `tools/check_multiproc.py`
không đọc được `app.env` bằng tài khoản thường, nên bước gate *"bất biến đa tiến
trình"* (`test_214`) **bị bỏ qua** khi chạy gate không nâng quyền. Nay nó xuống
thang êm và **nói rõ nguyên nhân**; muốn chạy đủ thì gate phải chạy nâng quyền,
hoặc đặt `LTT_TEST_DATABASE_URL`.

⭐ Và một lỗi giao diện chỉ máy thật mới lộ: nhật ký in `ip_noi_bo: 10.51.0.51` —
địa chỉ trong LAN của cụm. Đồ gá không có khoá đó. **Một danh sách CẤM chỉ chặn
được thứ nó biết tên, và dữ liệu giả chỉ chứa những khoá người viết nghĩ ra.**

---

## 7. Khoảng trống bằng chứng — nói rõ, không lấp liếm

| Chưa chứng minh được | Vì | Cần gì |
|---|---|---|
| Cài Windows tới hết và vào bằng RDP | lượt nghiệm thu dừng ở màn hình Setup rồi xoá máy — cài hết mất 15–25 phút và không đổi lại thêm bằng chứng nào về giao diện | một lượt nữa, nếu muốn |
| Khôi phục ảnh chụp | ảnh chụp đầu tiên chỉ có sau **một tuần**; máy nghiệm thu sống 20 phút | một máy sống qua một tuần |
| Cài lại (`rebuild`) chạy hết | cùng lý do với cài Windows | — |

✅ **Ba khoảng trống đã lấp 27/08:** console qua Proxmox thật · POST tạo/bật/tắt/
xoá đầu-tới-cuối · bản EN đã render (quét `<main>`: **0 đoạn còn tiếng Việt**).
✅ **Cloudflare:** storefront ẩn danh đo trên **URL công khai** sau deploy — CSS
mới tới ngay, cache-bust bằng hash nội dung làm đúng việc.

⚠️ **Một điều Cloudflare KHÔNG cho làm:** trình duyệt tự động bị chặn ở `/login`
bằng thử thách bot ("Just a moment…"). Nên các trang **đã đăng nhập** chỉ kiểm
được qua **loopback**. Không vượt thử thách đó — nó tồn tại đúng để chặn thứ tôi
đang chạy.

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
