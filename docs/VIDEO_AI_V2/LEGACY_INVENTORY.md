# P00 — INVENTORY LEGACY VIDEO

Đo 2026-09-06 trên `D:\LTTSTUDIOSAPP`.
Trunk `admin-mvp-v3` @ `06017841`. Nhánh legacy `claude/ltt-video-ai-v3-p00-3f5713`
@ `e21faf6a`.

---

## 0. Phát hiện chính — legacy **không nằm trên trunk**

Đây là thứ đổi hình dạng của cả kế hoạch xoá ở P06.

```
git ls-tree -r --name-only admin-mvp-v3 -- apps/lttvideo        -> 0 tệp
git ls-tree -r --name-only admin-mvp-v3 -- platform_core/video_gen -> 0 tệp
git ls-tree -r --name-only admin-mvp-v3 -- video_gateway        -> 0 tệp

git ls-tree -r --name-only claude/ltt-video-ai-v3-p00-3f5713 -- apps/lttvideo        -> 4 tệp
git ls-tree -r --name-only claude/ltt-video-ai-v3-p00-3f5713 -- platform_core/video_gen -> 5 tệp
git ls-tree -r --name-only claude/ltt-video-ai-v3-p00-3f5713 -- video_gateway        -> 12 tệp
```

Quét ký hiệu trên trunk (`git grep -l -I -E <mẫu> admin-mvp-v3`):

| Mẫu | Số tệp trên trunk | Loại tệp trúng |
|---|---:|---|
| `lttvideo` | 1 | `docs/CHATLTT_V3/00_SOURCE_TRUTH.md` — chỉ nhắc tên |
| `ltt_video` | 0 | — |
| `video\.ltt` | 0 | — |
| `video_gateway` | 0 | — |
| `lttv-` | 0 | — |
| `video_gen` | 2 | `docs/CHATLTT_V3/STATE.md`; `tests/test_188` — **dương tính giả**, trúng tên hàm `test_video_generate_...` |
| `VIDEO_AI` | 2 | `docs/CHATLTT_V3/STATE.md`, `docs/NHAT_KY.md` — nhắc lịch sử |

⇒ **Trên trunk, số tham chiếu thực thi tới runtime video legacy là 0.**

### Hệ quả cho P06

`LEGACY_DELETE_POLICY.md` giả định phải *xoá* legacy khỏi cây sản xuất. Ở kho
này, việc đó **đã tự đúng**: không có gì để xoá trên trunk. P06 rút lại thành:

1. **Không merge** `claude/ltt-video-ai-v3-p00-3f5713` vào trunk;
2. gắn tag phục hồi `video-legacy-final-pre-wangp` lên `e21faf6a` (P03);
3. quét lại 7 mẫu trên để chứng minh vẫn 0.

⚠️ **Đừng đọc điều này thành "legacy vô hại".** Nó vô hại **chừng nào không ai
merge nhánh kia**. Xem mục 3: nhánh kia đụng vào chính hạ tầng dùng chung mà
trunk cũng vừa sửa.

### `docs/VIDEO_AI/` trên cây chính là thư mục RỖNG

`ls -la docs/VIDEO_AI` → không tệp nào; `git ls-files docs/VIDEO_AI` → 0.
Nội dung thật (33 tệp) nằm ở worktree của nhánh V3. Thư mục rỗng ở cây chính là
vỏ còn sót — không phải nguồn.

---

## 1. DELETE_AT_P06 — runtime legacy (39 tệp, chỉ trên nhánh V3)

Không tệp nào trong nhóm này tồn tại trên trunk. "Xoá" = **không mang sang**.

### 1a. App `lttvideo` — 4 tệp, 339 dòng

| Tệp | Dòng |
|---|---:|
| `apps/lttvideo/gia.py` | 131 |
| `apps/lttvideo/manifest.py` | 113 |
| `apps/lttvideo/jobs.py` | 94 |
| `apps/lttvideo/__init__.py` | 1 |

### 1b. Adapter nền tảng `platform_core/video_gen/` — 5 tệp, 1.109 dòng

| Tệp | Dòng |
|---|---:|
| `ngan_sach.py` | 451 |
| `cloud_api.py` | 254 |
| `cau_hinh_san_xuat.py` | 216 |
| `dieu_phoi.py` | 160 |
| `__init__.py` | 28 |

### 1c. Worker RunPod/ComfyUI `video_gateway/` — 12 tệp, 10.550 dòng

| Tệp | Dòng |
|---|---:|
| `workflows/video_wan2_2_14B_i2v.json` | 3.108 |
| `workflows/video_wan2_2_14B_t2v.json` | 2.944 |
| `workflows/video_wan2_2_14B_fun_control.json` | 2.908 |
| `handler.py` | 626 |
| `lam_phang.py` | 462 |
| `ap_cau_hinh.py` | 254 |
| `Dockerfile` | 113 |
| `README.md` | 59 |
| `cau_hinh.json` | 56 |
| `extra_model_paths.yaml` | 13 |
| `requirements.txt` | 3 |
| `.gitignore` | 3 |

### 1d. Công cụ `tools/video_*.py` — 9 tệp, 2.266 dòng

`video_ra_soat.py` (575) · `video_nap_model.py` (380) · `video_theo_doi.py` (336) ·
`video_goi.py` (279) · `video_do_idle.py` (167) · `video_cau_hinh_json.py` (165) ·
`video_kiem_tep.py` (132) · `video_cloud.py` (131) · `video_bang_ke.py` (131)

⚠️ `video_theo_doi.py` là công cụ **duy nhất** đọc được hoá đơn RunPod của các
tài nguyên đang sống ở mục *Cloud* trong `PROJECT_STATE.md`. Đừng vứt nó trước
khi tài nguyên kia được xử lý.

### 1e. Test dải 710–718 — 9 tệp, 2.180 dòng

`test_710_ngan_sach_video` · `test_711_cloud_api_video` · `test_712_cau_hinh_san_xuat` ·
`test_713_nap_model` · `test_714_lam_phang` · `test_715_ap_cau_hinh` ·
`test_716_anh_worker` · `test_717_app_lttvideo` · `test_718_dieu_phoi_video`

⛔ `tests/test_71_thumbnail.py` **không** thuộc nhóm này. Nó trúng khi lọc bằng
tiền tố chuỗi `tests/test_71` và nó là test của app `thumbnail`. Ghi ra đây vì
đó đúng là kiểu bẫy làm một lượt xoá "theo mẫu" giết nhầm thứ đang phục vụ khách.

---

## 2. ARCHIVE_DOC_ONLY — tài liệu V3 (33 tệp `docs/VIDEO_AI/`)

Giữ trong lịch sử Git, không mang sang trunk. Đáng đọc **một lần** ở P01/P02 vì
chứa phép đo thật đã trả bằng tiền:

| Tệp | Vì sao còn giá trị cho V2.1 |
|---|---|
| `PROJECT_STATE.md` | trạng thái đóng của V3, ID tài nguyên cloud, giá đo được |
| `NGHIEN_CUU_CLOUD_GPU.md`, `CLOUD_RESOURCE_PLAN.md` | khảo sát 11 datacenter × 8 GPU — dữ liệu chọn vùng cho C-CLOUD |
| `KE_HOACH_DO_LUONG.md` | phương pháp chấm chất lượng bằng **VBench** — dùng lại được ở P07 |
| `CLOUD_SAFETY_PLAN.md`, `COST_LEDGER.csv` | khuôn sổ chi + luật an toàn đã trả giá |
| `DECISIONS.md` | 18 quyết định V-001…V-018, gồm `V-018` (giá vốn) |
| `B_LAN_COMPATIBILITY_BASELINE.md` | mốc chứng minh không chạm B-LAN |

---

## 3. ⚠️ Hạ tầng dùng chung nhánh V3 đã sửa — 13 tệp, phải diff thủ công

Đây là phần nguy hiểm thật, và nó **không** nằm trong danh sách "candidate areas"
của pack. Nhánh V3 sửa các tệp trunk cũng đang sửa. Đo bằng
`git diff --numstat <merge-base> <nhánh>`; merge-base là `d225a480` (= `master`).

| Tệp | V3 đổi (+/−) | Trunk đổi (+/−) | Rủi ro |
|---|---|---|---|
| `ho_so_he_thong.txt` | +6912 / −192 | **đã XOÁ khỏi trunk 04/09** | merge sẽ **hồi sinh** một tệp bị gỡ có chủ đích |
| `tools/gate.py` | +21 / −5 | +123 / −23 | cả hai sửa **ngân sách lõi** — đúng cơ chế đã làm treo máy 9 lần |
| `tools/test_nhanh.py` | +162 / 0 | +249 / 0 | như trên |
| `tests/test_361_cua_so_yen.py` | +246 / −2 | +417 / −2 | như trên |
| `tests/test_431_ngan_sach_loi.py` | +75 / −3 | +72 / −5 | như trên |
| `platform_core/providers.py` | +61 / 0 | +7 / −4 | V3 thêm provider `ltt_video` |
| `platform_core/gia_von.json` | +157 / −153 | — | giá vốn của model V3 |
| `tests/test_145_gate_covers_everything.py` | +47 / 0 | — | bánh cóc phủ tệp mới của V3 |
| `tests/test_190_public_api_coverage.py` | +11 / 0 | — | khai app `lttvideo` là đóng |
| `tests/test_88_agent_toolspec_apps.py` | +14 / 0 | — | như trên |
| `tests/test_61_setup_scripts.py` | +58 / −3 | — | |
| `tests/test_394_nen_da_phien.py` | +65 / −3 | — | |
| `locale/en/LC_MESSAGES/messages.po` (+`.mo`) | +54 / 0 | — | chuỗi dịch của app `lttvideo` |

🔴 **Luật rút ra:** nếu có ngày ai đó merge nhánh V3 (để lấy lại một công cụ, ví
dụ `video_theo_doi.py`), **không được merge cả nhánh**. Lấy từng tệp bằng
`git checkout <nhánh> -- <đường dẫn>` và đọc diff của bốn tệp ngân sách lõi bằng
mắt. Một lượt `git merge` ở đây là một lượt đánh nhau đúng chỗ đã làm sập máy.

---

## 4. KEEP_GENERIC — có trên trunk, **không** phải legacy video V3

Bốn app video này là **sản phẩm khác**, đang phục vụ khách, dùng API ngoài hoặc
engine cục bộ. Chúng không liên quan gì tới chương trình GPU cloud.

| Đường dẫn | Là gì | Xử lý |
|---|---|---|
| `apps/taovideo/` (23 tệp) | tạo video qua **API ngoài** (ModelArk/Seedance) | **KEEP** — không đụng |
| `apps/autosubvideo/` | phụ đề tự động | **KEEP** |
| `apps/upscalevideo/` | nâng cấp video, engine vendor cục bộ | **KEEP** |
| `apps/taoclipngan/` | cắt clip ngắn, whisper+YOLO GPU cục bộ | **KEEP** |
| `tools/3video/`, `tools/qualitylab_upscale_video_cli.py` | công cụ của các app trên | **KEEP** |

Hạ tầng chung V2.1 sẽ **gọi lại chứ không chép lại** (`REUSE_CONCEPT`):

`platform_core/storage.py` (R2/lưu trữ) · `platform_core/job_runner.py` +
`leases.py` (hàng đợi, lease) · `platform_core/credit.py` + `billing.py` (sổ
credit) · `platform_core/api_pool.py` + `providers.py` (khoá/provider) ·
`platform_core/image_input.py` · `platform_core/frontend_bundle.py`.

⛔ `render_gateway/**` và `llm_gateway/**`: **không đụng** (D02 + gate G-B của
chương trình cũ vẫn còn hiệu lực).

---

## 5. Bảng phân loại tóm tắt

| Lớp | Số tệp | Ở đâu | Hành động |
|---|---:|---|---|
| `DELETE_AT_P06` | 39 | chỉ nhánh V3 | không merge; tag phục hồi ở P03 |
| `ARCHIVE_DOC_ONLY` | 33 | chỉ nhánh V3 (`docs/VIDEO_AI/`) | giữ trong Git, đọc một lần |
| ⚠️ diff thủ công | 13 | cả hai nhánh | không bao giờ `git merge` cả nhánh |
| `KEEP_GENERIC` | 4 app + hạ tầng `platform_core` | trunk | không đụng |

## 6. Lệnh tái hiện toàn bộ số trên

```bash
git rev-list --left-right --count master...admin-mvp-v3
git rev-list --left-right --count admin-mvp-v3...claude/ltt-video-ai-v3-p00-3f5713
git diff --name-status $(git merge-base admin-mvp-v3 claude/ltt-video-ai-v3-p00-3f5713) \
    claude/ltt-video-ai-v3-p00-3f5713
git grep -l -I -E 'lttvideo|ltt_video|video_gateway|lttv-|video_gen' admin-mvp-v3
```
