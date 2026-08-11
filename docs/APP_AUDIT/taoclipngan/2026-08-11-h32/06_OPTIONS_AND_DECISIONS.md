# H32.4 — Phương án và quyết định

## O1 — Giữ generator hiện tại, chỉ vá lỗi

- Điểm khả thi 5/5; giá trị thị trường 2/5; rủi ro 2/5.
- Không đủ vì khách vẫn phải sang editor ngoài để sửa caption/crop.

## O2 — Generator hai bước + editor tối giản theo transcript (khuyến nghị)

- Điểm khả thi 4/5; giá trị 5/5; rủi ro 3/5.
- Step 1 Generate chỉ giữ source, goal, count, length, ratio và quality.
- Step 2 Review/Edit có transcript-linked trim, crop/reframe, caption/brand,
  rerender revision, compare và handoff Publish Bot.
- Tái sử dụng job/credit/storage/AppProject; không tạo runtime thứ hai.

## O3 — Sao chép full editor đa lớp như CapCut/Descript ngay

- Điểm khả thi 2/5; giá trị 5/5; rủi ro 5/5.
- Phạm vi vượt MVP, dễ biến Clip Studio thành app video editor thứ hai và kéo
  chậm các tool còn lại.

**Chọn O2.** P0 trước là cancel/storage/quality matrix; sau đó dựng editor theo
vertical slice trim → transcript → reframe → caption → rerender. Publishing gọi
workflow của Publish Bot, không chép logic OAuth/scheduler vào app này.
