# 06 — Decision Gate trước khi viết code

Các lựa chọn mặc định dưới đây là khuyến nghị kỹ thuật. Dev có thể trả lời theo
dạng `1A, 2A...`; nếu chủ sản phẩm yêu cầu tự triển khai theo khuyến nghị thì
dùng toàn bộ phương án **A**.

1. Phạm vi parity?
   - **A — ≥90% user-value parity, thay hạ tầng (khuyến nghị).**
   - B — MVP brief→prompt trước, hoãn storyboard/library.
   - C — Copy gần nguyên module.

2. Đơn vị trải nghiệm chính?
   - **A — Project production: Brief→Director→Scenes→Storyboard→Export.**
   - B — Chat prompt đơn lẻ.
   - C — Canvas node tự do.

3. Thư viện LTT/team?
   - **A — Admin publish/version; user read và clone về bản riêng.**
   - B — Mọi user sửa chung.
   - C — Chỉ private, không catalog LTT.

4. Tạo ảnh/video trong PROMPT AI OMMI?
   - **A — Gọi job/ToolSpec của app LTT hiện có, quote/confirm riêng.**
   - B — Copy provider/handler sang app mới.
   - C — Chỉ export prompt, không handoff.

5. Dữ liệu BOT GEMINI hiện hữu?
   - **A — Không nhập tự động; chỉ importer package đã dry-run/validate.**
   - B — Bulk import toàn bộ SQLite.
   - C — Dùng chung DB nguồn.

6. Model/provider?
   - **A — Dynamic từ LTT provider registry; admin quản key/model.**
   - B — User tự nhập API key.
   - C — Hardcode Gemini duy nhất.

7. UI?
   - **A — Carbon Red immersive, rail icon + progressive disclosure.**
   - B — Giữ nguyên 14 tab Alpine của nguồn.
   - C — Form Jinja một cột tối giản.

8. Rollout?
   - **A — off→admin→allowlist→public sau LTT-AQA G0–G8.**
   - B — public ngay khi code xong.
   - C — internal vĩnh viễn.

9. Tên kỹ thuật?
   - **A — folder/slug `prompt_ai_ommi`, URL `/prompt-ai-ommi`, display
     `PROMPT AI OMMI`.**
   - B — `promptommi` / `/promptommi`.
   - C — giữ tên `seedance`.

10. Collaboration v1?
    - **A — private-by-default; published catalog clone-only; chưa realtime.**
    - B — shared edit tất cả project.
    - C — realtime multi-user ngay P1.

## Khóa mặc định khuyến nghị

`1A · 2A · 3A · 4A · 5A · 6A · 7A · 8A · 9A · 10A`.

Lý do chung: giữ chiều sâu sản phẩm của nguồn, tận dụng toàn bộ nội tại LTT,
loại bỏ shared-write/SQLite/runtime thứ hai và không hứa collaboration/provider
mà hệ thống chưa chứng minh.

