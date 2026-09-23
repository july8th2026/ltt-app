# video_crawler — văn bản pháp lý (NHÁP — chủ dự án duyệt)

> **NHÁP — chủ dự án duyệt (quyết định Q2, PLAN_MVP §B).** Chưa phải tư vấn pháp lý; nên cho luật sư đọc trước khi
> mở bán thật. Mọi con số/hằng số trong app lấy từ `apps/video_crawler/features.py` (một nguồn) — sửa văn bản ở đây
> thì sửa cả hằng ở đó và tăng `PHIEN_BAN_CAM_KET`.

## 0. Nguồn

| # | Nguồn | Dùng cho |
|---|---|---|
| N1 | Điều khoản YouTube (youtube.com/t/terms); YouTube API Developer Policies III.E.1 | Các nền cấm tải tự động ⇒ trách nhiệm quyền thuộc khách, app chỉ là công cụ |
| N2 | OpusClip Terms of Service (opus.pro/terms-of-service); OpusClip copyright policy (help.opus.pro) | Khuôn: khách cam kết quyền, bảo đảm + bồi hoàn, kênh gỡ, khoá người tái phạm, nhật ký |
| N3a | Nghị định 17/2023/NĐ-CP, Điều 114 (hethongphapluat.com/…/dieu-114) | Trung gian gỡ/chặn tạm trong **72 giờ** kể từ yêu cầu của chủ thể quyền; không làm ⇒ mất miễn trừ, liên đới bồi thường |
| N3b | Luật Sở hữu trí tuệ sửa đổi 2022 (07/2022/QH15) | Biện pháp buộc ngừng và gỡ nội dung xâm phạm trên mạng |
| N3c | Luật Bảo vệ dữ liệu cá nhân 91/2025/QH15 (hiệu lực 01/01/2026) | Cookie khách tải lên là dữ liệu cá nhân: cần đồng ý, xoá theo yêu cầu, cấm bán |
| N7 | yt-dlp wiki (tần suất an toàn khi tải) | Trần tải theo tài khoản 60 video/giờ, 300 video/ngày |

Ghi chép nghiên cứu gốc: `DANH_GIA_MVP.md` §2 và `NC_B_nen_tang.md` §4 (thư mục scratchpad phiên 22/09/2026).
Chưa xác minh: phạm vi chính xác của NĐ 147/2024 (gỡ 24 h theo yêu cầu nhà nước) và thời hạn lưu bắt buộc với tệp
tải về — không dựa vào hai điểm này.

## 1. Câu cam kết (hiện trên MỌI lượt tải — phiên bản `2026-09-22`)

> Tôi cam kết có quyền tải và sử dụng các video này (tôi là chủ sở hữu, được chủ sở hữu cho phép, hoặc thuộc trường
> hợp pháp luật cho phép) và tự chịu trách nhiệm theo Điều khoản sử dụng.

Cơ chế (đã làm, `features.chuan_bi_tai`): ô tick bắt buộc ở "Cào hết" và "Tải các video đã chọn"; thiếu ⇒ không tạo
job, không giữ credit. Job lưu `params.cam_ket = {"phien_ban", "luc" (UTC)}` làm **bằng chứng** ai đồng ý câu nào lúc
nào. Xem trước không cần cam kết (không tải tệp).

## 2. Điều khoản bảo đảm và bồi hoàn (đề xuất bổ sung vào trang Điều khoản sử dụng)

**Điều X. Công cụ Cào video nguồn**

1. Công cụ chỉ thực hiện thao tác kỹ thuật theo yêu cầu của bạn. LTT Studios không chọn, không kiểm duyệt trước và
   không sở hữu nội dung bạn tải.
2. Mỗi lần tải, bạn **bảo đảm** rằng: (a) bạn là chủ sở hữu hoặc được chủ sở hữu cho phép, hoặc việc sử dụng thuộc
   trường hợp ngoại lệ pháp luật cho phép; (b) việc tải không vi phạm điều khoản của nền tảng nguồn mà bạn đã chấp
   nhận; (c) bạn chỉ dùng nội dung trong phạm vi quyền đó.
3. Bạn **bồi hoàn** cho LTT Studios mọi thiệt hại, chi phí hợp lý (kể cả phí luật sư) và khoản phải trả cho bên thứ ba
   phát sinh từ việc bạn vi phạm cam kết ở khoản 2.
4. LTT Studios có quyền gỡ tệp, huỷ job, khoá tính năng hoặc tài khoản khi nhận yêu cầu hợp lệ từ chủ thể quyền hoặc
   cơ quan nhà nước; credit đã dùng cho nội dung vi phạm **không hoàn**.
5. Giới hạn sử dụng: tối đa 60 video/giờ và 300 video/ngày mỗi tài khoản. Việc lách giới hạn (nhiều tài khoản, tự
   động hoá) là vi phạm điều khoản.
6. Nền tảng nguồn có thể chặn, hạn chế hoặc khoá tài khoản của bạn (nhất là khi dùng phiên đăng nhập); LTT Studios
   không chịu trách nhiệm về việc đó.

## 3. Quy trình gỡ ≤ 72 giờ (NĐ 17/2023 Đ.114)

Kênh tiếp nhận (hiện trên form tải): trang **Báo cáo lạm dụng** `https://lttstudios.com/bao-cao-lam-dung/` và email
`support@lttstudios.com`.

| Bước | Hạn | Việc |
|---|---|---|
| 1. Tiếp nhận | ngay | Ghi sổ: thời điểm nhận (mốc tính 72 h), người yêu cầu, tác phẩm, link gốc/mã video, bằng chứng quyền |
| 2. Kiểm tối thiểu | ≤ 24 h | Yêu cầu đủ thông tin nhận diện chưa; thiếu ⇒ hỏi lại (mốc 72 h tính từ khi đủ) |
| 3. Gỡ/chặn tạm | ≤ 72 h | Tìm job theo mã video trong `jobs.result.muc[].id` → xoá tệp `video_crawler/<owner>/<job>/<id>.*` khỏi kho; ghi `job_id`, `owner_id`, `params.cam_ket` vào sổ |
| 4. Báo khách | cùng lúc | Báo người tải: nội dung đã gỡ, lý do, quyền phản hồi (kèm bằng chứng quyền) trong 10 ngày |
| 5. Khép | — | Phản hồi của khách có căn cứ ⇒ cân nhắc khôi phục; không ⇒ giữ gỡ, tính một "lần vi phạm" |

**Chỗ trống cần làm (chưa có mã):** công cụ admin "tìm và gỡ theo mã video" + sổ yêu cầu gỡ. Hiện gỡ bằng tay; tệp
tự xoá sau 30 ngày (spec §13), nên nhiều yêu cầu sẽ gặp tệp đã tự hết hạn — vẫn phải ghi sổ.

## 4. Người vi phạm lặp lại

- Lần 1: gỡ + cảnh báo qua email.
- Lần 2 trong 12 tháng: gỡ + khoá tính năng Cào video nguồn 30 ngày.
- Lần 3 trong 12 tháng: khoá vĩnh viễn tính năng; xem xét khoá tài khoản.
- Căn cứ đếm: sổ yêu cầu gỡ (bước 5 ở §3). **Cần làm:** cờ khoá tính năng theo tài khoản (chưa có mã).

## 5. Dữ liệu phiên đăng nhập (cookie) — Luật 91/2025/QH15

Đã có trong mã (`apps/video_crawler/phien.py`, trang "Đăng nhập nền tảng"):

- Chỉ giữ cookie của đúng tên miền nền đó; lưu **mã hoá**; không bao giờ trả giá trị cookie về trình duyệt.
- Chỉ dùng cho job cào của chính khách; đi qua tệp tạm quyền 600 trong thư mục job, không vào params/result/nhật ký.
- Khách **xoá được bất cứ lúc nào** (nút "Xoá phiên").

Văn bản đồng ý đề xuất (hiện cạnh ô nhập cookie):

> Tôi đồng ý để LTT Studios lưu mã hoá phiên đăng nhập này và chỉ dùng nó để thực hiện các lượt cào tôi yêu cầu.
> Tôi hiểu nền tảng nguồn có thể hạn chế hoặc khoá tài khoản của tôi. Tôi có thể xoá phiên bất cứ lúc nào.

Cam kết: không chia sẻ, không bán, không dùng cho mục đích khác; xoá theo yêu cầu qua `support@lttstudios.com` trong
72 giờ (khách cũng tự xoá được ngay trên trang).

## 6. Việc chủ dự án cần quyết

1. Duyệt câu cam kết §1 (đổi chữ ⇒ tăng `PHIEN_BAN_CAM_KET`).
2. Đưa Điều X (§2) vào trang `https://lttstudios.com/dieu-khoan-su-dung/`.
3. Xác nhận hộp thư `support@lttstudios.com` **đang nhận thư thật** (sổ nội dung cấm admin
   `docs/admin_mvp_v3/06b_SO_DANG_KY_NOI_DUNG_CAM.md` ghi "không có hộp thư hỗ trợ công bố"); nếu không, đổi
   `EMAIL_HO_TRO` và chỉ để trang Báo cáo lạm dụng.
4. Ai trực quy trình gỡ 72 h và sổ ghi ở đâu.
5. Duyệt văn bản đồng ý §5 — sau khi duyệt mới thêm ô tick vào form phiên (`templates/video_crawler.html`).
