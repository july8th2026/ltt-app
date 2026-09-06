# ĐỐI CHIẾU WanGP ↔ LTT V2.1 — 30 subsystem

Nguồn: `WANGP_ARCHITECTURE_EXTRACTION.md` · `DEEPY_UNKNOWN_GAPS.md` ·
`P01_KET_QUA_DO.md` · hợp đồng app LTT (`AGENTS.md` §8) · kiến trúc V2.1.

Sáu quyết định được phép: `REUSE_WANGP_DIRECTLY` · `WRAP_WANGP_THINLY` ·
`REUSE_LTT_GENERIC` · `BUILD_LTT_MINIMAL` · `DELETE_FROM_PLAN` · `NEEDS_LIVE_TEST`

---

| # | Subsystem | LTT V2.1 định xây | WanGP đã có | LTT generic đã có | Gap thật | Quyết định |
|---|---|---|---|---|---|---|
| 1 | **Unified input** | schema phẳng riêng | `metadata.inputs: [text,image,video,audio]` từng model | — | chỉ còn **hình dạng form** cho người Việt | `WRAP_WANGP_THINLY` |
| 2 | **Media handling** | tầng nhận/kiểm media | gallery + `wangp_io` | `platform_core.image_input.validate_reference` | không | `REUSE_LTT_GENERIC` (kiểm) + `REUSE_WANGP_DIRECTLY` (nhận) |
| 3 | **Media roles** | 8 vai tự định nghĩa | `media_inputs` + bảng vai trong `SKILL.md` | — | **không** | `DELETE_FROM_PLAN` |
| 4 | **Intent understanding** | rule router tự viết | truy vấn năng lực + Deepy Prime | — | chất lượng suy luận chưa đo | `NEEDS_LIVE_TEST` |
| 5 | **Model discovery** | ModelRegistry | `list_model_defs` / `list_model_metadata` | — | **không** | `DELETE_FROM_PLAN` |
| 6 | **Capability discovery** | CapabilityResolver | `capabilities` + `get_model_schema` + `get_model_availability` | — | **không** *(trừ allowlist, xem #27)* | `DELETE_FROM_PLAN` |
| 7 | **Settings / defaults** | bộ tham số riêng | `get_default_settings` · `merge_settings_with_defaults` | — | **không** | `REUSE_WANGP_DIRECTLY` |
| 8 | **Templates** | VideoTemplateManager | user settings file + Deepy tool template | — | **không** | `DELETE_FROM_PLAN` |
| 9 | **Profiles** | định dạng profile mới | tệp settings JSON | — | **nguồn gốc**: tệp nào được duyệt, phiên bản trong git | `BUILD_LTT_MINIMAL` (sổ đăng ký, không phải định dạng) |
| 10 | **Deepy** | VideoAgent | Deepy Zero/Prime | — | chưa đo | `NEEDS_LIVE_TEST` — và `D-V2-007` khoá: sau benchmark |
| 11 | **Queue (thực thi)** | VideoQueue | hàng đợi nội bộ + `submit_manifest` | — | **không** | `REUSE_WANGP_DIRECTLY` |
| 12 | **Queue (sản phẩm)** | — | ❌ không có | `platform_core.job_runner` + `leases` | **là nguồn chân lý** (§2.A) | `REUSE_LTT_GENERIC` |
| 13 | **Progress** | tầng tiến độ riêng | `SessionStream` · `ProgressUpdate` · **786 sự kiện/lượt đo được** | SSE/poll của nền tảng | chỉ còn **chuyển tiếp** | `WRAP_WANGP_THINLY` |
| 14 | **Preview** | — | `PreviewUpdate` — **20 ảnh/lượt đo được** | — | chỉ còn hiển thị | `WRAP_WANGP_THINLY` |
| 15 | **Cancel** | cơ chế huỷ riêng | `job.cancel()` · `session.cancel()` — **đã kiểm ĐẠT** | huỷ job của nền tảng | chỉ còn **lan truyền** | `WRAP_WANGP_THINLY` |
| 16 | **Error handling** | — | `GenerationError` · `result.errors` · `.cancelled` | xử lỗi job của nền tảng | chỉ còn **dịch sang ngôn ngữ sản phẩm** | `WRAP_WANGP_THINLY` |
| 17 | **API** | client riêng | `shared/api.py` — 25 phương thức | — | client HTTP phía LTT | `BUILD_LTT_MINIMAL` |
| 18 | **MCP** | — | 20+ công cụ, streamable-http | — | ⚠️ **không có xác thực** | `DELETE_FROM_PLAN` cho đường sản phẩm; giữ cho Deepy sau |
| 19 | **Gallery** | kho media riêng | gallery + upload/download **dùng-một-lần, ngắn hạn** | R2 | gallery là **tạm**, R2 là **bền** | `REUSE_WANGP_DIRECTLY` (chuyển) + `REUSE_LTT_GENERIC` (lưu) |
| 20 | **Preprocessing** | VideoPreprocessor | `preprocessing/` (pose/depth/edge/mask) | — | **không** | `DELETE_FROM_PLAN` |
| 21 | **Postprocessing** | VideoPostprocessor | `submit_media_postprocessing` · `audio_remux` · cùng hàng đợi | — | **không** | `DELETE_FROM_PLAN` |
| 22 | **Model switching** | — | nạp theo yêu cầu, tự gỡ model cũ | — | ⚠️ `init()` **một lần/tiến trình** (`P01-D-13`) | `REUSE_WANGP_DIRECTLY` + ràng buộc một-cấu-hình-một-worker |
| 23 | **VRAM management** | — | `mmgp` 3.7.14, 5 hồ sơ | — | **không** — đã chốt `profile 3` | `REUSE_WANGP_DIRECTLY` |
| 24 | **History** | — | ❌ Gallery cục bộ, mất theo máy | lịch sử job của nền tảng | **bền + theo người dùng** | `REUSE_LTT_GENERIC` |
| 25 | **Storage** | — | ❌ | `platform_core.storage` (R2) | **không** | `REUSE_LTT_GENERIC` |
| 26 | **Auth** | — | ❌ không có khái niệm người dùng | `server.auth.session.require_login` | **không** | `REUSE_LTT_GENERIC` |
| 27 | **User ownership** | — | ❌ | sở hữu media của nền tảng | **allowlist năng lực theo hạng khách** | `REUSE_LTT_GENERIC` + `BUILD_LTT_MINIMAL` (allowlist) |
| 28 | **Credits** | — | ❌ không có khái niệm tiền | `platform_core.credit` · `billing` | **quy giây GPU → credit** | `REUSE_LTT_GENERIC` + `BUILD_LTT_MINIMAL` (`cost.py`) |
| 29 | **Budget / cloud lifecycle** | — | ❌ | `video_gen/ngan_sach.py` · `cloud_api.py` · `video_cloud.py` **(nhánh V3)** | lấy từng tệp, không merge cả nhánh | `REUSE_LTT_GENERIC` *(qua `git checkout <nhánh> -- <tệp>`, `P00-D-04`)* |
| 30 | **GUI** | Unified Flat Composer | Gradio trong `wgp.py` — **không tách được** | `ltt.css` · i18n · catalog/nav · hợp đồng app | **toàn bộ giao diện** | `BUILD_LTT_MINIMAL` |

---

## Tổng kết quyết định

| Quyết định | Số subsystem |
|---|---:|
| `DELETE_FROM_PLAN` | **8** |
| `REUSE_WANGP_DIRECTLY` | 7 |
| `REUSE_LTT_GENERIC` | 8 |
| `WRAP_WANGP_THINLY` | 5 |
| `BUILD_LTT_MINIMAL` | **5** |
| `NEEDS_LIVE_TEST` | 2 |

*(Tổng > 30 vì một số subsystem mang hai quyết định cho hai vế khác nhau.)*

⭐ **Chỉ 5/30 subsystem cần LTT viết mã mới**, và không cái nào là "engine".

## Hai chỗ dễ hiểu nhầm, ghi rõ

**#11 so với #12 — hai hàng đợi, đừng gộp.** WanGP có hàng đợi **thực thi cục bộ**
trên C-CLOUD; LTT có hàng đợi **sản phẩm**. Kiến trúc V2.1 §2.A đã chốt: hàng đợi
LTT là nguồn chân lý. Bỏ một trong hai đều sai: bỏ của LTT thì mất ai-xếp-hàng /
ai-trả-tiền / ai-được-huỷ; bỏ của WanGP thì phải tự viết lại điều phối GPU.

**#19 — Gallery là TẠM, R2 là BỀN.** Gallery của WanGP nằm trên máy sẽ bị xoá.
Nó là **phương tiện chuyển**, không phải nơi lưu. Job chỉ `done` khi tệp đã nằm
trong R2 của LTT (kiến trúc §4).
