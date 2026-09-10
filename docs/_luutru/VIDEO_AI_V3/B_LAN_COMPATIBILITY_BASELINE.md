# MỐC TƯƠNG THÍCH B-LAN — biến D02 thành thứ máy kiểm được

> Sản phẩm của **P01**. Mục đích: `D02` nói *"B-LAN tuyệt đối không thay đổi
> behavior/deployment trước khi C-CLOUD POC chạy độc lập"* — nhưng một lời hứa
> không kiểm được thì không bảo vệ được gì. Tệp này nói **đo bằng cái gì**.
>
> `checklists/B_LAN_PROTECTION.md` của pack liệt kê bảy gạch đầu dòng văn xuôi.
> Dưới đây là bản dịch sang **tên tệp test cụ thể**.

Ngày: **2026-09-04** · cây `...\worktrees\ltt-llm-api-http-guide-a3e123`.

---

## 0. Hai chỗ P00 nói sai, sửa ở đây

P01 xác định tập test bằng **công cụ của kho** (`tools/thanh_phan.py --test`,
ánh xạ suy từ `import` chứ không từ tên tệp) thay vì đọc tên như P00 đã làm.
Kết quả bác lại hai khẳng định:

| P00 nói | Thật ra |
|---|---|
| `tests/test_227_nexus_render.py` là mốc hồi quy B-LAN | ❌ **Sai.** Tệp đó kiểm **kết xuất HTML của Nexus** (`test_trang_danh_sach_render_duoc`, `test_trang_ma_ghep_render_va_hien_ma`). Chữ *"render"* ở đây là *dựng trang*, không phải *cổng render*. Đúng lớp lỗi *"đừng suy từ tên tệp"* mà chính P00 viết ra |
| Bốn tệp là đủ để chốt B-LAN | ❌ **Thiếu.** Cổng ảnh có **4** tệp, cổng LLM có **11** — xem §2 |

🔴 **Và một cái bẫy phải biết trước khi gọi test bằng số:** kho này có **số test
trùng nhau**.

```
test_245_nexus_may_cua_toi.py     test_250_cong_render.py
test_245_render_gateway.py        test_250_llm_gateway.py
                                  test_250_nexus_sso.py
```

⇒ *"chạy test_245"* là một câu **mơ hồ**. Trong tài liệu này mọi phép kiểm gọi
bằng **tên tệp đầy đủ**. (Đây chính là lý do `tools/cay_rieng.py` cấp dải số
riêng cho từng cây — cây này là **700–799**.)

---

## 1. Ranh giới: cái gì là "B-LAN" theo nghĩa D02

| Thuộc B-LAN — ⛔ không đụng | Không thuộc |
|---|---|
| `render_gateway/**` (cổng ảnh, máy B :8199) | `apps/lttvideo/**` (mới) |
| `llm_gateway/**` (cổng LLM, máy B :8299) | `gateway_core/**` (mới) |
| `platform_core/image_gen/**` (client phía A gọi cổng ảnh) | `video_gateway/**` (mới) |
| `platform_core/llm/**` (client phía A gọi cổng LLM) | `platform_core/video_gen/**` (mới) |
| Mục `ltt_image` và `ltt_llm` trong `platform_core/providers.py` | Mục **`ltt_video`** thêm mới vào cùng tệp |

⚠️ **`platform_core/providers.py` là tệp DUY NHẤT vừa chứa thứ phải bảo vệ vừa
chứa thứ phải thêm.** Thêm một mục `ltt_video` **không** phải sửa B-LAN — nhưng
sửa một dòng nào của `ltt_image`/`ltt_llm` **thì là**. Kho đã có sẵn phép kiểm
cho đúng chuyện này: `tests/test_250_cong_render.py::test_them_provider_khong_lam_vo_registry_cu`.

---

## 2. Tập phép kiểm — lấy từ `tools/thanh_phan.py`, không gõ tay

### Cổng ảnh (`gateway:render`) — 4 tệp

```
tests/test_245_render_gateway.py     111 phép kiểm — hợp đồng chính
tests/test_266_tiep_tuc_lo_do.py
tests/test_277_tham_cong_anh.py
tests/test_278_nhuong_card.py        trọng tài card dùng chung
```

### Cổng LLM (`gateway:llm`) — 11 tệp

```
tests/test_250_llm_gateway.py     tests/test_363_suat_khong_ro.py
tests/test_254_don_dep_gpu.py     tests/test_368_trong_tai_tai_cua_ta.py
tests/test_258_gioi_han_cong.py   tests/test_373_ssrf_anh_tu_xa.py
tests/test_269_nhip_tim.py        tests/test_374_to_tien_mo_coi.py
tests/test_270_tren_gpu.py        tests/test_379_to_tien_may_a.py
tests/test_278_nhuong_card.py
```

### Phía máy A gọi hai cổng (`core:provider`) — 28 tệp

Không liệt kê hết ở đây (công cụ trả về bất cứ lúc nào); những tệp **trực tiếp**
chốt đường ảnh nội bộ:

```
tests/test_250_cong_render.py     client A→B, và BA LUẬT (429 · không đổi model · job_id)
tests/test_252_dieu_phoi.py       điều phối trọn job + presigned GET/PUT
tests/test_249_prompt_dich.py     dịch prompt trước khi gửi
tests/test_276_gia_anh_that.py    tiền theo ảnh THẬT SỰ sinh ra
tests/test_372_may_b_khong_voi_toi.py    máy B không với tới máy A
```

⭐ `tests/test_278_nhuong_card.py` xuất hiện ở **cả hai** cổng — đúng, vì nó chốt
thứ hai cổng dùng chung: trọng tài một card cho nhiều hộ.

---

## 3. Hợp đồng hành vi của cổng ảnh — đọc từ tên phép kiểm, không từ tài liệu

Đây là bản dịch bảy gạch đầu dòng của `checklists/B_LAN_PROTECTION.md`.

### Xác thực

| Lời hứa | Phép kiểm |
|---|---|
| khoá sai bị chặn | `test_sai_token_bi_chan` |
| `/live` không cần khoá, `/health` thì cần | `test_health_tra_du_thong_tin_van_hanh` |
| đọc token bằng tách chuỗi, không đếm ký tự | `test_kiem_tra_doc_token_bang_split_khong_dem_ky_tu` |

### 429 = BẬN, không phải hỏng — ⭐ luật đắt nhất

| Lời hứa | Phép kiểm |
|---|---|
| bận trả **429**, không bao giờ 5xx | `test_ban_tra_429_va_KHONG_phai_ma_loi_5xx` |
| phía A nâng 429 thành `BanError`, **không** `CongRenderError` | `test_250_cong_render.py::test_429_nem_BanError_chu_KHONG_nem_CongRenderError` |
| không biết bao lâu thì `eta=None`, **không bịa số** | `test_ban_khong_biet_bao_lau_thi_eta_None_chu_khong_bia_so` · `test_eta_chua_co_lich_su_thi_tra_None_chu_khong_doan_bua` |
| mất liên lạc = **bận**, không phải "rảnh" | `test_mat_lien_lac_thi_coi_la_BAN_chu_khong_bao_ranh` |
| ComfyUI chết ⇒ coi là bận, **không nhận việc** | `test_comfy_chet_thi_coi_la_ban_chu_khong_nhan_viec` |
| việc **lạ** trong hàng đợi làm máy bận; việc của ta thì không | `test_viec_la_trong_hang_doi_lam_may_ban` · `test_viec_cua_chinh_ta_khong_lam_may_ban` |
| ngưỡng RAM là **lượng tuyệt đối**, không phải tỉ lệ | `test_ram_thap_lam_may_ban_theo_nguong_TUYET_DOI` |

🔴 Vi phạm nhóm này ⇒ `api_pool` cooldown ⇒ `disable` khoá sau 5 lần ⇒ **model
nhà tự tắt vĩnh viễn** chỉ vì hàng xóm bận. Đây là nhóm phải xanh tuyệt đối.

### Idempotency

| Lời hứa | Phép kiểm |
|---|---|
| gửi lại cùng `job_id` ⇒ trả job cũ, **không vẽ lần hai** | `test_gui_lai_cung_job_id_tra_ve_job_cu` · `test_idempotency_cung_job_id_khong_tao_job_thu_hai` |
| sống sót qua **khởi động lại tiến trình** (hỏi `/history` của ComfyUI) | `test_runner_KHONG_xep_hang_lai_job_da_chay_xong` · `test_chay_lai_cung_job_id_khong_ve_lan_hai` |
| thiếu `job_id` ⇒ từ chối **trước khi gửi đi** | `test_thieu_job_id_thi_TU_CHOI_ngay_khong_gui_di` |
| gửi lại nhận 200 ⇒ **không** coi là lỗi | `test_gui_lai_cung_job_id_tra_200_thi_KHONG_coi_la_loi` |

### Huỷ · hết giờ · OOM

| Lời hứa | Phép kiểm |
|---|---|
| huỷ gọi `interrupt` với **đúng `prompt_id` của mình** | `test_huy_job_goi_interrupt_dung_prompt_id` · `test_interrupt_bat_buoc_co_prompt_id` |
| hết giờ ⇒ huỷ **đúng prompt của mình** | `test_het_gio_thi_huy_DUNG_prompt_cua_minh` |
| job dài 6 phút **không** bị hết giờ nhầm | `test_job_dai_6_phut_khong_bi_het_gio_nham` |
| OOM ⇒ nhả VRAM rồi thử lại **đúng một lần** | `test_oom_thi_nha_vram_va_thu_lai_DUNG_MOT_lan` · `test_oom_lan_dau_thu_lai_thanh_cong` |
| một cú vấp mạng ≠ máy chủ chết (ba cú thì là) | `test_mot_cu_vap_mang_khong_phai_may_chu_chet` |

### Đầu ra

| Lời hứa | Phép kiểm |
|---|---|
| có **mục lịch sử** ≠ thành công — phải đọc `status_str` | `test_co_muc_lich_su_KHONG_co_nghia_la_thanh_cong` · `test_da_xong_doi_HAI_dieu_kien_khong_phai_mot` |
| "thành công mà không có ảnh" là **thất bại** | `test_thanh_cong_nhung_khong_co_anh_la_that_bai` |
| presigned PUT gửi **đúng `Content-Type` đã ký** | `test_put_gui_dung_content_type_da_ky` |
| không có vé PUT ⇒ lỗi rõ ràng | `test_thieu_ve_put_bi_tu_choi` · `test_khong_co_ve_put_la_loi_ro_rang` |
| bỏ qua ảnh xem trước `temp` | `test_images_of_bo_qua_anh_xem_truoc_temp` |
| `.txt` đổi tên thành `.png` bị chặn (magic byte) | `test_file_txt_doi_ten_thanh_png_bi_chan` |
| ảnh tham chiếu trả **TÊN**, không phải đường dẫn | `test_ref_luu_vao_input_dir_va_tra_ve_TEN_khong_phai_duong_dan` |

### Ngân sách VRAM — chốt an toàn đã ngăn máy B sập

| Lời hứa | Phép kiểm |
|---|---|
| trần là **số ĐÃ ĐO**, không phải số tính ra | `test_tran_la_so_DA_DO_chu_khong_phai_so_tinh_ra` · `test_nguong_lay_tu_so_DO_THAT_chu_khong_phai_so_tron` |
| từ chối **trước khi chạm GPU** | `test_runner_TU_CHOI_truoc_khi_cham_GPU` |
| **mọi** đường gọi ComfyUI đều có chốt (không chỉ `Runner`) | `test_MOI_duong_goi_ComfyUI_deu_co_chot_ngan_sach` |
| cấu hình chưa đo thì bị chặn | `test_BAC_TIEP_THEO_van_BI_CHAN` |

### Triển khai (máy B là Windows)

| Lời hứa | Phép kiểm |
|---|---|
| `.ps1` thuần ASCII, không BOM | `test_ps1_thuan_ascii` · `test_ps1_khong_bom` |
| ghi cấu hình bằng đường **không** chèn BOM | `test_ps1_ghi_cau_hinh_bang_duong_khong_BOM` · `test_ps1_khong_ghi_file_bang_duong_chen_bom` |
| **ComfyUI không bao giờ rời `127.0.0.1`** (Q102) | `test_cai_dat_dich_vu_giu_comfyui_o_loopback` |
| tường lửa chỉ mở cho **một địa chỉ** | `test_tuong_lua_gioi_han_theo_dia_chi_khong_mo_toang` |

### Registry provider — ⭐ phép kiểm quan trọng nhất với V3

| Lời hứa | Phép kiểm |
|---|---|
| **thêm provider mới không làm vỡ registry cũ** | `tests/test_250_cong_render.py::test_them_provider_khong_lam_vo_registry_cu` |
| `base_url` **không** viết cứng địa chỉ LAN | `test_base_url_KHONG_viet_cung_dia_chi_LAN_vao_ma_nguon` |
| bật `is_active` **không đủ** để phục vụ khách (fail-closed) | `test_BAT_is_active_KHONG_du_de_phuc_vu_khach` |
| `capabilities` **chỉ khai thứ đã đo** | `test_capabilities_CHI_khai_thu_DA_DO` |
| giới hạn phải **nói ra**, không giấu sau giao diện | `test_capabilities_NOI_RA_gioi_han_chu_khong_giau` |

⭐ Ba dòng cuối là **hợp đồng mà mục `ltt_video` sắp thêm phải tuân**, không chỉ là
thứ phải giữ nguyên: khai `capabilities` cho Wan2.2 **chỉ được ghi số đã đo ở P07**,
và phải nói ra giới hạn.

---

## 4. Cách chạy mốc

⚠️ Trước mọi lượt: `python tools\cua_so_yen.py trang-thai`. Trần `-n 6`.

```powershell
# Mốc hẹp — sau mỗi lần sửa, vài chục giây
python tools\thanh_phan.py --test gateway:render
python tools\thanh_phan.py --test gateway:llm

# Mốc đúng nghĩa — trước khi báo xong một pha
python tools\gate.py --pham-vi gateway:render,gateway:llm,core:provider

# Phán quyết — trước khi báo xong toàn bộ
python tools\gate.py
```

⛔ `--vong-lap` và `--quick` **không phải bằng chứng** — chính dòng `RESULT` của
chúng nói vậy.

---

## 5. Gate **G-B** — định nghĩa chính xác

Gate này do P00 thêm. Nay viết thành thứ chạy được:

```bash
git diff --stat -- render_gateway llm_gateway platform_core/image_gen platform_core/llm
# PHẢI RỖNG
```

Cộng thêm **một** ngoại lệ được phép, và chỉ một:

```bash
git diff -- platform_core/providers.py
# CHỈ được chứa phần THÊM mục `ltt_video`.
# Một dòng đổi trong `ltt_image` hoặc `ltt_llm` là ĐỎ.
```

**Trạng thái hôm nay:** ✅ xanh — `git diff` trên bốn đường đầu **rỗng**, và
`providers.py` chưa bị chạm.

---

## 6. Characterization test cần viết **trước** giai đoạn 2

Giai đoạn 2 của ADR-3 (trỏ `render_gateway` sang `gateway_core/` rồi xoá bản sao)
là lần **duy nhất** được phép sửa B-LAN, và chỉ khi hai điều kiện D02/D04 đã đủ.

⭐ **Tin tốt: 111 phép kiểm của `test_245_render_gateway.py` ĐÃ LÀ bộ
characterization test** — không phải viết mới. Điều kiện là chúng xanh **mà không
sửa một dòng test nào**; sửa test để nó xanh là xoá đúng thứ đang bảo vệ.

Ba chỗ bộ hiện có **chưa** phủ, phải bổ sung trước giai đoạn 2 (dải **700–799**):

1. **Cổng ảnh chạy được khi nhập từ `gateway_core`** — hôm nay không có phép kiểm
   nào chốt *chỗ* mã nằm, vì chưa cần.
2. **`videos_of()` không làm hỏng `images_of()`.** Node ComfyUI lõi đặt video dưới
   khoá `"images"` (`comfy_api/latest/_ui.py:437`) ⇒ hai đường đọc **cùng một khoá**.
   Phải có phép kiểm chốt cổng ảnh **không** nhận nhầm một tệp `.mp4`.
3. **Bánh cóc chống trôi bản sao**: `tools/check_song_sinh.moc` ghim băm các tệp
   `render_gateway` có bản song sinh trong `gateway_core` (§4 của ADR-3).

---

## 7. Điều kiện đóng của P01

| Yêu cầu của `P01_CURRENT_SYSTEM_AND_ADR.md` | Trạng thái |
|---|---|
| Ma trận generic / image-only / Windows-only / LAN-only | ✅ `ADR_REMOTE_VIDEO_COMPUTE.md` §3b |
| Đặc tả hợp đồng B-LAN (auth · 429 · idempotency · cancel · timeout · OOM · output · health) | ✅ §3 tệp này |
| Audit mô hình provider của A-CONTROL | ✅ ADR §2 + `CURRENT_SYSTEM_MAP.md` §3.1 |
| So sánh 4 phương án A/B/C/D | ✅ `ARCHITECTURE_SCORECARD.csv` (A 168 · B 210 · C 277) |
| Scorecard 14 tiêu chí | ✅ như trên |
| ADR + migration path | ✅ **APPROVED** 2026-09-04 → `Q121` |
| Định nghĩa "B-LAN untouched" bằng test/behavior snapshot | ✅ §3 + §5 tệp này |
| Danh sách characterization test cần trước implementation | ✅ §6 |
