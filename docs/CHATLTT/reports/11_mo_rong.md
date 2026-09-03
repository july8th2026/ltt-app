# Phase 11 — Chứng minh kiến trúc mở rộng (bằng fixture, không bằng lời)

> Gói viết: *"Prove architecture, do not merely claim it."* Nên phase này không
> thêm tính năng nào — nó **thử phá** lời hứa của các phase trước.

## Source
- worktree/branch: như Phase 02 · base: `f2b58a5`
- canonical rules read: kế hoạch §6 (hàng H43.11), báo cáo Phase 01 §6 (phản đề
  `visionModels[]` hardcode của LibreChat), `docs/CHATLTT/11_THEM_MODEL_MOI.md`

## Ba fixture, ba câu hỏi khác nhau

| # | Fixture | Câu hỏi | Kết quả |
|---|---|---|---|
| 1 | Thêm alias text **thứ ba** (`ltt_llm_dai`, ngữ cảnh 200K, `reads_images`, `experimental`) | Có hiện ra **mà không sửa UI** không? | **Có.** Alias vào catalog, `stability` và `constraints` đi theo; `reads_images` chỉ bật ở alias khai nó; **id nội bộ không rời nền tảng** |
| 2 | Alias ảnh với `suc_khoe` trả `chua_san_sang`, rồi hook **ném** / trả giá trị lạ / trả `None` | Trạng thái nói đúng chưa, và có fail-closed không? | **Cả bốn** ra `chua_san_sang`. Giao diện tắt nút theo đúng trường đó — chốt bằng chính mã `TaoMedia.tsx` |
| 3 | Năng lực `video.tuong_lai` — phương thức bộ hiển thị **không vẽ được** | Fail-closed hay hiện một ô trống? | **Không hiện**. Và `LOAI_KHOI` là danh sách **đóng**: khối `video`/`html` bị từ chối ngay lúc ghi |

## Hai phép kiểm TĨNH — thứ giữ cho ba điều trên còn đúng ở phiên sau

| Phép kiểm | Chốt gì |
|---|---|
| `test_khong_re_nhanh_theo_ten_model_o_bat_cu_dau` | Không dòng mã chạy được nào trong `apps/chatltt` hay `frontend/chatltt/src` nhắc `qwen38`, `hidream`, `noi-bo-`, `ltt_llm_vision`, `vieneu`. **Đây là phản đề trực tiếp** của `visionModels[]` + `model.includes()` trong LibreChat (`config.ts:2024-2086`) |
| `test_chatltt_khong_import_app_khac_hay_provider` | `apps/chatltt` không import `apps.*` khác, `platform_core.{providers,api_pool,image_gen,llm}`, `render_gateway`, `llm_gateway`, `voice_sidecar`. Thêm model mới **không được** đòi ChatLTT biết ai cung cấp nó |
| `test_them_model_moi_can_sua_dung_nhung_dau_da_ghi_ra` | Tài liệu `11_THEM_MODEL_MOI.md` nêu **đủ** tên tệp và tên trường hợp đồng. Một tài liệu tiếp quản thiếu tên trường là một tài liệu bắt người sau đi dò mã |

## Tài liệu giao nộp — `docs/CHATLTT/11_THEM_MODEL_MOI.md`

Nói **cả hai chiều**, và chiều thứ hai mới là lời hứa:

- **Không phải sửa**: `frontend/chatltt/` không một dòng; `apps/chatltt/` chỉ một
  dòng khi thêm một *năng lực* (không phải khi thêm một *alias*);
  `platform_core/runtime_noi_bo/` không bao giờ.
- **Phải sửa**, theo bốn tình huống: alias text · model ảnh · engine giọng ·
  **phương thức mới** (việc lớn nhất, 5 bước, cố ý lớn).
- Một mục riêng cho "model không khả dụng" — vì đó là **đường chạy bình thường**,
  không phải trường hợp riêng, và vì phân biệt *chưa sẵn sàng* (trạng thái của
  cổng) với *bận* (trạng thái của một lượt gọi) là chỗ dễ nhầm nhất.

## Decisions made autonomously

| Decision | Chosen | Why |
|---|---|---|
| Allowlist sản phẩm và khả năng **vẽ** là một cổng hay hai? | **Hai** | `kiem_cho_phep` vẫn cho `video.tuong_lai` qua (nó nằm trong allowlist), nhưng `danh_muc` lọc nó ra vì không vẽ được. Gộp làm một thì thêm một phương thức sẽ **im lặng** hiện một ô trống thay vì buộc người thêm nó phải khai chỗ vẽ |
| Tài liệu mở rộng để ở đâu | `docs/CHATLTT/11_THEM_MODEL_MOI.md`, **có test đọc nó** | Một tài liệu không ai kiểm là một tài liệu sẽ trôi — đúng cơ chế đã hỏng năm lần với bảng trạng thái trong `CLAUDE.md` |

## Tests
| Command | Result |
|---|---|
| `pytest test_626 -n 0` | **8 passed** |

## Failures found and repaired
- Không có lỗi sản phẩm. Một phép kiểm tài liệu ban đầu đòi chuỗi
  `apps/<slug>/manifest.py` trong khi tài liệu viết đường dẫn **cụ thể** — sửa
  phép kiểm để nó đòi thứ thật sự quan trọng (tên tệp + tên trường hợp đồng),
  không phải một cách viết.

## External unknown/blocker
- Không.

## Verdict
**PASS** — ba fixture chứng minh, hai phép kiểm tĩnh giữ, một tài liệu có test canh.

## Next
Autocontinue to phase: **12** (torture: đồng thời · tiền · bảo mật · dữ liệu · hiệu năng).
