> LƯU TRỮ 2026-09-19 — không còn đúng hệ thống hiện tại; thay bằng: `docs/AGENT_LTT/01_DAC_TA_AGENT.md` (đặc tả đã chốt, app `apps/agent/`). Chỉ đọc để hiểu lịch sử.

# Phân tích PLENX (plenxai.com) + đối chiếu, phương án cho nền tảng ta — 2026-08-01

> Quan sát trực tiếp qua trình duyệt (đã đăng nhập tài khoản người dùng cấp).
> Mục tiêu: rút **CƠ CHẾ** bày trí + hiển thị app + hành vi khi vào app, để
> thiết kế các hạng mục cho nền tảng ta. **Không sao chép danh sách app của họ**
> — app ta tự phát triển; chỉ học cách tổ chức. Ảnh chụp: `plenx-home.png`,
> `plenx-apps.png`, `plenx-tool-nano.png` (thư mục gốc, không commit).

## 1. Bố cục từng trang (quan sát)

### 1.1 Thanh nav trên cùng (mọi trang, dark, dính)
Logo **PlenX** (sao gradient) · các **category** ngang có dropdown: **Ảnh · Video
· Giọng nói · Ứng dụng · Workflow · Khám phá** · bên phải: **Tài nguyên · Bảng
giá · 💎 credit (số) · 🔔 thông báo · avatar + tên + vai trò (User)**.
→ Nav theo **NĂNG LỰC/loại** (không phải liệt kê từng app). Bấm thẳng category =
vào tool mặc định của loại đó (vd bấm "Ảnh" → `/image/nano-banana-pro`).

### 1.2 Trang chủ (landing, `/`) — thiên về marketing/chuyển đổi
- **Hero** gradient: badge "Powered by <models>", tiêu đề lớn "AI Creative
  Studio", chip giá trị "Tạo ảnh MIỄN PHÍ | Tạo video chỉ 200đ/video", CTA:
  giới thiệu nhận hoa hồng (referral), khám phá model mới, khám phá Workflow.
- **Thẻ use-case nổi bật** (filter Tất cả/Video/Ảnh): "AI Dance Video", "AI
  Review Sản phẩm", "AI Video Thời trang"… — mỗi thẻ có **video/ảnh preview** +
  mô tả + CTA "Tạo ngay". Đây là **kịch bản dùng** (template), không phải tool thô.
- **"AI Models hàng đầu"**: hàng chip model chia 2 nhóm (Image / Video), mỗi chip
  = icon + tên + loại + **badge** (Popular/NEW/Premium/Fast/HD).
- **"Công cụ AI chuyên biệt"** (One-click tools): lưới thẻ tool (Interior Design,
  Skin Enhancer, Upscale, Product Creator, Storyboard, Food Creator, App Builder…)
  — icon + tên + mô tả ngắn. "Xem tất cả công cụ →".
- **"Tại sao chọn"**: lưới 6 điểm mạnh (Text-to-Image, Video Gen, Workflow, Tốc
  độ, Bảo mật, Cộng đồng).
- **Dải CTA** gradient "Sẵn sàng sáng tạo? → Bắt đầu miễn phí". **Footer** 5 cột.

### 1.3 Trang `/apps` — CÁCH HIỂN THỊ APP (cốt lõi)
- Hero nhỏ "CHÀO MỪNG ĐẾN VỚI PLENX APPS" + mô tả.
- **Search + filter tabs** (Tất cả / Phổ biến nhất / Mới).
- **Lưới thẻ app 5 cột**, chia **section theo curation**: *Phổ biến nhất* → *Mới*
  → *Fast Apps (chạy trên ComfyUI Workflow)* → *Ứng dụng cộng đồng*. Section tải
  lười (lazy, có spinner).
- **Thẻ app** = **ẢNH BÌA riêng (art thiết kế, không phải emoji)** + **badge góc**
  (HOT đỏ / NEW xanh / PRO hồng) + **tên** + **mô tả 2 dòng** + nút **"▷ Dùng
  ngay"** (full-width). App chưa ra: nút **"Sắp ra mắt"** (disabled).

### 1.4 Vào một app = WORKSPACE (khác hẳn ta)
Bấm "Dùng ngay" → mở trang tool (vd `/image/nano-banana-pro`):
- **Khu kết quả (gallery)** lớn chiếm phần lớn màn — hiện các ảnh/video đã tạo
  ("Đã hiển thị tất cả 3 ảnh"), có zoom.
- **Thanh COMPOSER nổi ở đáy** (luôn hiện): nút **+ Thêm** (ảnh tham chiếu) ·
  ô **"Mô tả ảnh bạn muốn tạo…"** (prompt) · hàng tham số: **chọn model** (Nano
  Banana Pro ▾) · **tỉ lệ** (1:1) · **số lượng** (stepper 1/4) · **độ phân giải**
  (1K) · **tier** (VIP 01) · **Free** (toggle) · nút **Tạo ảnh**.
- Kết quả **stream vào gallery ngay trên trang** — KHÔNG chuyển sang trang tiến
  độ riêng. (Lịch sử tổng vẫn có ở chỗ khác.)

### 1.5 Tài khoản thu gọn trong AVATAR (không có sidebar)
Bấm avatar (góc phải) mở dropdown chứa TOÀN BỘ phần tài khoản:
- Danh tính: tên + email + badge **User** + **☆ Free**.
- **My Workspace** (bộ chuyển workspace, có tick).
- Mục: **Hồ sơ · Tài khoản · Workflows của tôi · Bảng điều khiển người bán ·
  Lịch sử mua · Lịch sử sử dụng · Giới thiệu bạn bè · Team của Bạn**.
- Khối **Credits** (số + thanh) + nút **Nạp thêm Credits**.
- **Ngôn ngữ**: VI/EN/TH/JA. · **Đăng xuất** (đỏ).
→ Xác nhận: **KHÔNG cần sidebar trái** — mọi thứ nằm ở **header + dropdown
avatar**. Đây là điểm mấu chốt về bố cục.

## 2. Cơ chế rút ra (đáng học)

1. **Hai tầng "app":** (a) **Model** thô (chọn trong composer, có badge) ·
   (b) **Tool/App** = gói một mục đích trên nền model (thẻ ở /apps) · (c)
   **Use-case template** (thẻ landing). Ta hiện chỉ có tầng (b) sơ khai.
2. **Hiển thị app bằng ẢNH BÌA + badge + mô tả + "Dùng ngay"**, chia **section
   curation** (Phổ biến/Mới/Cộng đồng) + **search/filter**. (Ta: emoji-in-box,
   lưới phẳng.)
3. **Vào app = workspace** (gallery kết quả + composer đáy, stream tại chỗ), KHÔNG
   phải form → redirect → trang tiến độ. **Đây là khác biệt UX lớn nhất.**
4. **Composer khai tham số động** (prompt, model, tỉ lệ, số lượng, độ phân giải,
   tier) + **hiện giá/credit + toggle Free** ngay trước khi tạo.
5. **Chọn model trong composer** — gắn thẳng với registry model/provider (ta ĐÃ
   có Provider Registry ở H8 — rất khớp).
6. **Credit/giá nổi bật**: badge 💎 ở nav, trang Bảng giá, giá mỗi lần tạo, tier
   VIP, **referral (hoa hồng)**.
7. **Cộng đồng/Khám phá**: gallery tác phẩm + app do cộng đồng tạo.
8. **Nav theo category** + click category = vào tool mặc định.

## 3. Đối chiếu ta ↔ PLENX (khoảng cách)

| Hạng mục | PLENX | Nền tảng ta hiện tại | Khoảng cách |
|---|---|---|---|
| Thẻ app | ảnh bìa + badge + mô tả + Dùng ngay, chia section, search | emoji-in-box, lưới phẳng | **Lớn** (thẩm mĩ + curation) |
| Vào app | **workspace + composer + gallery, stream tại chỗ** | form → 303 → `/jobs/{id}` tiến độ | **Rất lớn** (mô hình tương tác) |
| Tham số tạo | composer động (model/tỉ lệ/số lượng/độ phân giải/tier) | form cứng mỗi app tự viết | **Lớn** (nên có schema chung) |
| Chọn model | dropdown trong composer, có badge | ẩn (app tự chọn) | Vừa (đã có registry, chưa lộ UI) |
| Giá/credit | giá mỗi lần + tier + Free toggle + referral | có sổ credit + badge; chưa hiện giá/tier | Vừa (thiếu hiển thị + pricing) |
| Nav | top-nav theo category | sidebar app-launcher | Vừa (khác mô hình, cân nhắc) |
| Landing | hero + use-case + model catalog + tools + why + CTA | hero ngắn + thẻ app | Vừa (Pha marketing) |
| Cộng đồng/Khám phá | gallery + community apps | chưa có | Nhỏ (tương lai) |

## 4. PHẠM VI (chốt theo người dùng 2026-08-01)

**CHỈ audit + triển khai BỐ CỤC/ĐIỀU HƯỚNG (chrome).** KHÔNG động vào xây tính
năng bên trong app, KHÔNG xây "vỏ workspace/composer", KHÔNG đụng logic app. Nội
dung từng app do người dùng phát triển sau. Ở đây chỉ định nghĩa **khung điều
hướng + cách bày trí trang**.

## 5. TIÊU CHÍ BỐ CỤC CẦN TRIỂN KHAI (đối chiếu PLENX)

**Mô hình mục tiêu: điều hướng bằng HEADER NGANG, BỎ sidebar trái.** Hiện nền
tảng ta dùng **sidebar trái** (app-launcher hai tầng, H6.6) + topbar mỏng. PLENX
KHÔNG có sidebar: mọi điều hướng ở **header ngang**, tài khoản thu gọn trong
**avatar dropdown**, và **vào app thì full-width, không sidebar**.

### T1 — Header ngang toàn cục (thay sidebar)
- Trái: **logo** (bấm về trang chủ).
- Giữa: **điều hướng app theo NHÓM** dạng menu ngang (PLENX: Ảnh/Video/Giọng
  nói/Ứng dụng/Workflow/Khám phá). Với ta: nhóm theo loại app (hoặc mục "Ứng
  dụng" mở ra catalog). Mỗi mục có thể là dropdown liệt kê app trong nhóm.
- Phải (cụm tiện ích, thu gọn): **Bảng giá** · **badge Credit (💎 số)** ·
  **🔔 thông báo** · **avatar** (ảnh + tên + vai trò).
- Header **dính (sticky)**, nền panel, viền dưới mảnh — như hiện tại nhưng chuyển
  toàn bộ vai trò điều hướng từ sidebar sang đây.

### T2 — Tài khoản THU GỌN trong avatar dropdown (bỏ khối sidebar)
Bấm avatar mở dropdown chứa: danh tính (tên/email/badge vai trò+gói) · **Hồ sơ ·
Tài khoản · Lịch sử mua · Lịch sử sử dụng · (Giới thiệu) ·** khối **Credits + Nạp
thêm** · **ngôn ngữ** · **Đăng xuất**. → Bỏ nút "Đăng xuất" + badge credit rời ở
sidebar/topbar hiện tại; gom hết vào đây.

### T3 — VÀO APP = FULL-WIDTH, KHÔNG sidebar
- Khi mở một app, **không còn sidebar trái**; nội dung app chiếm toàn bộ chiều
  ngang dưới header. (PLENX: vào tool là thấy ngay chức năng.)
- Điều hướng **giữa các app** vẫn qua header (luôn hiện). Điều hướng **trong một
  app** (nếu app nhiều trang, vd socialbot 8 trang) là việc **nội bộ của app**
  (tab/menu riêng trong vùng nội dung), KHÔNG phải sidebar toàn cục.

### T4 — Trang chủ / Catalog
- Trang chủ: hero gọn + lối vào các nhóm app. Trang **danh sách app** (như
  `/apps` của PLENX): lưới thẻ + **search + filter tabs (Tất cả/Phổ biến/Mới)** +
  **section curation**. (Chi tiết THẨM MĨ thẻ — ảnh bìa/badge — là phần bố cục,
  có thể làm; KHÔNG gồm chức năng bên trong app.)

### T5 — Responsive
- Header ngang co gọn trên mobile (menu app gộp vào nút ☰; cụm phải gộp vào
  avatar). Không có sidebar nên mobile đơn giản hơn hẳn mô hình hiện tại.

### T6 — Nhất quán hệ thị giác
- Dùng lại `ltt.css` (đã có ở UX Pha 1) cho header/avatar-menu/catalog — token
  dark thống nhất. Trang quản trị (/admin) giữ vỏ riêng (đã dark), KHÔNG lẫn với
  header khách.

## 6. Đối chiếu nhanh: ta ĐANG có gì vs CẦN đổi (chỉ bố cục)

| Thành phần | Hiện tại (ta) | Cần đổi theo PLENX |
|---|---|---|
| Điều hướng chính | **sidebar trái** (app-launcher 2 tầng) | **header ngang** (nhóm app) |
| Tài khoản | nút Đăng xuất ở chân sidebar + badge credit ở topbar | **avatar dropdown** gom hết |
| Khi vào app | vẫn còn sidebar trái | **full-width, bỏ sidebar** |
| Sub-nav trong app | sidebar bung trang con (socialbot) | **nội bộ app** (tab trong nội dung) |
| Catalog | thẻ emoji, lưới phẳng | lưới + search/filter + section (thẩm mĩ nâng sau) |

## 7. Ghi chú
- Chỉ mượn **cơ chế điều hướng + bố cục**, KHÔNG lấy app/nội dung PLENX.

## 8. PLAN TRIỂN KHAI — UX Pha 2: bố cục HEADER (bỏ sidebar) ✅ XONG 2026-08-01

> **Đã build + audit trực quan sạch (Chrome loopback).** Header ngang thay sidebar;
> nav app dropdown theo NHÓM (Ảnh/Đăng bài/Khác); tài khoản gom trong avatar-menu;
> vào app FULL-WIDTH; app nhiều trang (socialbot) có TAB nội bộ; app 1 trang không
> tab; /admin giữ vỏ riêng. Catalog thẻ cover+badge+search+filter. Full suite 1586
> pass, scan 0. Chụp đối chiếu: catalog/login/home/avatar/app-socialbot/app-thumbnail/
> admin — tất cả khớp tiêu chí + cơ chế PLENX, không lỗi bố cục.


**Chốt người dùng 2026-08-01:** header ngang thay sidebar; nav app = **dropdown
theo NHÓM**; tài khoản gom vào avatar; vào app **full-width**. Chỉ đổi BỐ CỤC mặt
KHÁCH; **/admin giữ vỏ riêng**. Không đụng tính năng/logic app.

### L1 — Nhóm app cho header (data-only)
- `AppManifest` thêm `group: str = "Ứng dụng"` (nhãn nhóm ở header). Gán:
  thumbnail→"Ảnh", socialbot→"Đăng bài", demo→"Khác". (Chỉ metadata bố cục;
  không hardcode slug ở nền tảng — nền đọc `group` từ manifest.)

### L2 — templating (dữ liệu cho header)
- Global `nav_groups(request)` → `{group: [LoadedApp...]}` đã lọc quyền (thay vai
  trò `nav_apps` hai tầng ở sidebar). Giữ `active_app`, `is_admin`, `so_du_credit`.
- Global `tai_khoan(request)` → dict cho avatar-menu: {email/tên, vai trò, credit,
  is_admin}. (Không lộ gì nhạy cảm.)

### L3 — Partial `_header.html` (dùng chung)
- Trái: logo (→ `/`). Giữa: mỗi **nhóm** = 1 dropdown liệt kê app trong nhóm
  (bấm app → route_prefix). Phải: **Bảng giá** (placeholder→H9) · **badge Credit
  💎** · **🔔** (placeholder) · **avatar dropdown**.
- **Avatar dropdown** = tài khoản thu gọn: tên/email/vai trò · Hồ sơ (→/settings)
  · **Credits + Nạp thêm** (→H9) · (Quản trị nếu admin →/admin) · **Đăng xuất**
  (form POST + CSRF `phien_csrf`). Ngôn ngữ: để sau.
- CSS header/avatar-menu/app-tabs thêm vào `ltt.css`.

### L4 — `base.html` (vỏ khách đã đăng nhập) — bỏ sidebar
- Thay `<aside class="sidebar">` bằng `{% include "_header.html" %}`; vùng nội
  dung **full-width** dưới header.
- App nhiều trang (socialbot): khi `active_app==slug` và >1 nav_entries → render
  **thanh tab nội bộ app** ở ĐẦU vùng nội dung (không sidebar). App 1 trang: không tab.
- Bỏ topbar cũ (credit/đăng xuất) — đã chuyển lên header/avatar. Giữ block
  `content`; block `topbar_title/right` → gộp thành 1 dải tiêu đề mảnh trong nội
  dung (tuỳ trang), hoặc bỏ.

### L5 — `base_public.html` (khách chưa đăng nhập)
- Dùng `_header.html` phiên bản anon: logo + (tuỳ) nhóm app công khai + **Đăng
  nhập/Đăng ký** (thay avatar). Giữ hero/catalog hiện có.

### L6 — Responsive
- ≤820px: nhóm app gộp vào nút **☰** (menu xổ); cụm phải gộp vào avatar. Không
  sidebar nên mobile gọn.

### L7 — Cập nhật test (đổi assertion sidebar → header)
- test_72 (launcher/sub-nav/link admin/logout/credit), test_64 (logout form +
  "Việc của tôi"), test_66 (demo hiện/ẩn), test_37, test_41 (credit badge). Đổi:
  "sidebar có X" → "header/nhóm có X"; "Việc của tôi" (mục sidebar) → mục tương
  ứng trong header/avatar; logout form vẫn CSRF. Giữ nguyên bất biến bảo mật
  (phân quyền tầng route KHÔNG đổi — chỉ chrome đổi).

### L8 — Nghiệm thu
- Full `pytest -q` xanh + scan 0 + kiểm trình duyệt (từ máy khác do IPv6 máy chủ):
  header điều hướng đúng, avatar-menu đủ mục, **vào app full-width không sidebar**,
  socialbot có tab nội bộ, mobile ☰. Deploy + commit.

**Ngoài phạm vi (không làm):** workspace/composer, params_schema, logic app, đổi
/admin. Thẩm mĩ thẻ catalog (ảnh bìa/badge) có thể làm kèm hoặc tách — hỏi khi
chốt.
