# Narration text — 3 Facebook App Review videos

English is used in the generated MP3s (reviewers are international). Vietnamese
is provided as an alternative (`gen_voice.py --lang vi`). For a premium voice,
paste the English into ElevenLabs and overwrite the MP3s with the same filenames.

---

## 🎬 VIDEO 1 — `pages_show_list`  (~38s)

**v1_01_intro** — *EN:* LTTStudios VideoBot. Facebook Graph API integration. This clip demonstrates the pages_show_list permission.
*VI:* LTTStudios VideoBot, tích hợp Facebook Graph API. Clip này minh họa quyền pages_show_list.

**v1_02_connect** — *EN:* The user clicks Connect Facebook Account. The browser opens Facebook's official login and consent screen, where the user grants three permissions: pages_show_list, pages_manage_posts, and pages_read_engagement. The user clicks Continue.
*VI:* User bấm Kết nối tài khoản Facebook. Trình duyệt mở màn đăng nhập và cấp quyền chính thức của Facebook, user cấp 3 quyền: pages_show_list, pages_manage_posts, pages_read_engagement, rồi bấm Continue.

**v1_03_pages_list** — *EN:* The app calls GET /me/accounts and displays the list of Pages the user manages, each with its name and category. The user ticks the Pages to enable for publishing. This is exactly what pages_show_list is used for.
*VI:* App gọi GET /me/accounts và hiển thị danh sách Page user quản lý, kèm tên và category. User tick chọn Page để dùng. Đây chính là công dụng của pages_show_list.

---

## 🎬 VIDEO 2 — `pages_manage_posts`  (~56s)

**v2_01_intro** — *EN:* This clip demonstrates the pages_manage_posts permission — publishing a video to a Facebook Page the user manages.
*VI:* Clip này minh họa quyền pages_manage_posts — đăng một video lên Trang Facebook mà user quản lý.

**v2_02_form** — *EN:* On the Manual FB tab, the user selects the target Page, chooses a local video file, and enters a title and description. Privacy is set to Public.
*VI:* Ở tab Manual FB, user chọn Trang đích, chọn file video trên máy, nhập tiêu đề và mô tả. Quyền riêng tư đặt Công khai.

**v2_03_publish** — *EN:* The user clicks Publish to Facebook. The app calls POST /{page-id}/videos using the resumable upload protocol — start, transfer, and finish phases. The log shows the upload progressing from zero to one hundred percent, then the resulting Facebook video URL.
*VI:* User bấm Đăng Facebook. App gọi POST /{page-id}/videos theo giao thức resumable upload — start, transfer, finish. Log hiển thị tiến trình 0 đến 100%, rồi hiện link video Facebook.

**v2_04_verify** — *EN:* We open the Page in a browser and confirm the video has been published to the Page. This is the core function pages_manage_posts enables.
*VI:* Ta mở Trang trên trình duyệt và xác nhận video đã được đăng lên Trang. Đây là chức năng cốt lõi mà pages_manage_posts cho phép.

---

## 🎬 VIDEO 3 — `pages_read_engagement`  (~24s)

**v3_01_intro** — *EN:* This clip demonstrates the pages_read_engagement permission — reading engagement metrics for the Page's videos.
*VI:* Clip này minh họa quyền pages_read_engagement — đọc số liệu tương tác cho video của Trang.

**v3_02_insights** — *EN:* On the Monitor tab the user clicks Refresh. The app calls GET /{video-id}/video_insights and the reactions, comments and shares fields, then fills a read-only table with views, reach, reactions, comments and shares. This is what pages_read_engagement is used for.
*VI:* Ở tab Monitor user bấm Refresh. App gọi GET /{video-id}/video_insights cùng các trường reactions, comments, shares, rồi điền bảng chỉ-đọc: views, reach, reactions, comments, shares. Đây là công dụng của pages_read_engagement.
