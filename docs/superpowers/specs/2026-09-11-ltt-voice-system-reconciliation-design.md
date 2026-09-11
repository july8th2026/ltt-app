# LTT VOICE — SYSTEM RECONCILIATION DESIGN (RC1)

> Spec thiết kế, khoá ngày **2026-09-11**, phiên `ltt-voice-reconciliation-165a40`.
> Chủ dự án duyệt Decision Lock (D001–D009) và bộ bất biến trong cùng phiên.
>
> ⛔ Tệp này **không** định nghĩa quy trình test/commit/deploy. Quy trình duy nhất
> là `docs/00_LTT_OPERATING_CONTRACT.md`. Nơi nào dưới đây nhắc tới một cấp test
> (L1/L3) hay một cổng, đó là **con trỏ** vào hợp đồng, không phải một luật mới.
>
> ⛔ Tệp này **không** chép giá trị từ mã (giá, trần ký tự, danh sách làn). Con số
> ở mã; ở đây chỉ có con trỏ — theo `docs/LTT_VOICE/NGUON_CHAN_LY.md`.

---

## 1. Current Reality — đo 2026-09-11

### 1.1 Production đang chạy gì

| Câu hỏi | Trả lời | Bằng chứng |
|---|---|---|
| SHA production | **`4a894036`** | `/health/version` loopback **và** `https://app.lttstudios.com` |
| Tệp `.py` khớp commit | 636 tệp · lệch 0 · thiếu 0 · thừa 0 | `tools/nghiem_thu_deploy.py` |
| Tệp KHÔNG phải `.py` (template/JS/CSS) khớp commit | 195 tệp · lệch 0 · thiếu 0 · thừa 0 | so blob git từng tệp (công cụ nghiệm thu chỉ so `.py` — đây là một lỗ đo, xem §10.3) |
| Trunk `admin-mvp-v3` | `3100c317` = `4a894036` + 1 tệp `docs/NHAT_KY.md` | `git diff --stat` |
| Hotfix chỉ có trên production | **không có** | hai dòng trên |

⇒ **VERIFIED CANONICAL BASE = `3100c317`** (code = production).

### 1.2 Năm khái niệm không trùng nhau

| Khái niệm | Giá trị |
|---|---|
| REMOTE HEAD (`origin/HEAD → origin/master`) | `9e73bf1f` (07/09) — **sau trunk 391 commit** |
| TRUNK (`admin-mvp-v3`, local = origin) | `3100c317` |
| WORKTREE HEAD của RC | `3100c317` (nhánh `claude/ltt-voice-reconciliation-165a40`) |
| DEPLOY SOURCE | bản xuất từ commit (`setup: nguon ban giao la BAN XUAT tu commit`) |
| ACTUAL PRODUCTION RUNTIME | `4a894036` |

### 1.3 Branch / Worktree Matrix — vùng Voice

| Nhánh | HEAD | Gốc | Sau/Trước trunk | Tình trạng |
|---|---|---|---|---|
| `claude/ltt-voice-gui-mvp-ed62d6` | `65e099af` | `9d711828` | 19 / 1 | chưa lên trunk |
| `claude/my-voices-enrollment-prod-379a22` | `29ac2300` | `9e73bf1f` | 391 / 2 | chưa lên trunk (worktree detached, sạch) |
| `claude/history-audio-storage-auth-4cffe3` | `dca96e84` | `9e73bf1f` | 391 / 3 | chưa lên trunk |
| `claude/projects-longform-slice-ab2e77` | `ca6a00ce` | `9e73bf1f` | 391 / 1 | chưa lên trunk |
| `claude/ltt-voice-qa-ci-gate-1c85fb` | `a3a2a46e` | `9e73bf1f` | 391 / 1 | chưa lên trunk |
| `claude/studio-voice-picker-ui-6782bb` | `3634412a` | `9e73bf1f` | 391 / 1 | chưa lên trunk |
| `claude/ltt-voice-98-upgrade-9b586f` · `ltt-voice-api-audit-7c8fee` · `ltt-voice-inference-hardening-b1db43` · `voice-language-compatibility-440bfd` | — | — | x / 0 | **đã nằm trọn trong trunk** |
| `phien/asv-v4` · `phien/asv-v6` (chương trình ASV) | `891d93db` | — | — | chạm `apps/ltt_voice` (thêm `duong_cho_app_khac`) |
| `architecture/scheduler-priority-v1` | `ef776aa8` | `3100c317` | 0 / 1 | chạm `job_submit.py`, đổi thứ tự job Voice |

Không có stash. Không worktree voice nào bẩn. Không phiên voice nào còn sống.

### 1.4 Gốc rễ — vì sao có sáu nhánh treo

| Gốc | Đo được |
|---|---|
| R1 phiên mới sinh trên nền cũ | 5/6 nhánh mọc từ `origin/master = 9e73bf1f`. **DEFERRED** — chủ dự án xử lý ngoài RC. |
| R2 không có sổ nhận việc | hai phiên cùng viết `POST /giong/{id}/ngon-ngu` |
| R3 "xong" không bao gồm "hạ cánh" | dấu vết duy nhất của nhánh treo nằm trong bộ nhớ phiên |
| R4 chốt cơ học nổ muộn | hai migration cùng cha `f2c48b71e903`; ba số test trùng |
| R5 luật cũ quay lại im lặng | `lan_ngon_ngu.py` tự merge sạch mang chính sách làn thứ hai |

---

## 2. Feature Provenance

| Năng lực | Production (`4a894036`) | Nhánh | Bản dùng trong RC |
|---|---|---|---|
| Chặn lệch làn | Q121: `quyet_dinh`, khai thắng đoán | GUI: chỉ-cảnh-báo khi đoán | **Q121 + D002** (khai chỉ thắt) |
| Làn lúc ghi danh | form chọn sẵn `vi`, giá trị lạ → `"vi"` | My Voices: mặc định `""` | **D003**: bắt khai, giá trị lạ → 400 |
| Nguồn gốc làn của giọng | không có | My Voices: `ngon_ngu_nguon` | My Voices + giá trị `do_asr` (D003) |
| Cửa khai làn | không có | hai bản (GUI, My Voices) | **một route** gộp (D004) |
| Thu hồi / xoá giọng | chỉ `/tat` | My Voices: `/xoa`, `/xoa-nhieu` (4 lỗi) | My Voices + T-07 |
| Trạng thái `loi` khi ghi danh hỏng | không có (treo `dang_ghi_danh`) | hằng số chết | T-07 (worker đặt) |
| Preview kho chung | mất nút im lặng cho người không phải chủ | GUI: `khoa_chung`, `voice/chung/` | GUI + T-08 |
| Nghe thử vs Tạo | bất đối xứng không nói ra | — | **D006** |
| Lịch sử: hết hạn / xoá / đã tải | không có | History | History + **D005** |
| Trạng thái khối/dự án | cột `trang_thai` chết; khối "xong" sau khi tệp hết hạn | Projects: badge suy ra | Projects + **D005** (suy từ tệp thật) |
| `ma_loi` ở Dự án | không có | — | T-10 |
| Chống nộp trùng | chỉ Studio + API | — | T-06 (mọi cửa) |
| Public API: kiểm trước giữ tiền | kiểm trong worker sau khi giữ → hoàn | — | **D007** hook `ToolSpec` |
| Public API: mã lỗi | rơi ở `job_runner` | — | D007 (400 đồng bộ có mã) |
| GUI Studio: bộ lọc bám làn, chip "Kho chung", lý do nút Tạo bị khoá, `<details>` | không có; chữ sai dưới ô Ngôn ngữ | GUI | GUI + T-15 |
| Nút nghe thử: loading / lỗi | reset im lặng khi lỗi | Picker | Picker + T-13 (i18n) |
| Hàng rào QA + E2E mock | không có | QA | QA + T-12 |
| Bộ Playwright vĩnh viễn cho Voice | không có | QA: 3 flow `playwright-cli` | **mở rộng** (§7) |
| Bề mặt cho ASV | `duong_cho_trang` | ASV: `duong_cho_app_khac` | cả hai (T-09) |

---

## 3. Semantic Conflict Map

| # | Khái niệm | Hai hiện thực | Loại | Xử lý |
|---|---|---|---|---|
| SC-1 | Chính sách làn | `features._chot_lan`+`quyet_dinh` (trunk) · `_chan_xung_dot_lan`+`xung_dot` (GUI) | CONTRACT CONFLICT | giữ trunk, **bỏ tường minh** bản GUI (tự merge không báo) |
| SC-2 | Cửa khai làn | `khai_ngon_ngu` (JSON, cho `""`) · `dat_ngon_ngu_giong` (form+303) | DUPLICATED SOURCE | gộp một route (D004) |
| SC-3 | Làn mặc định của giọng | `default="vi"` + fallback `"vi"` · `default=""` | BEHAVIOR CONFLICT | D003 |
| SC-4 | Làn của preset | `giong_mau.lan_cua` · `_chan_xung_dot_lan("vi")` gõ cứng · `lui_giong.tu_giong_mau` gõ `"vi"` | DUPLICATED SOURCE | chỉ `giong_mau` (T-16) |
| SC-5 | Danh sách làn hợp lệ | `lan_ngon_ngu.chuan_lan` · gõ lại ở 6+ chỗ | DUPLICATED SOURCE | gom về `lan_ngon_ngu` (T-16) |
| SC-6 | Công thức `PHIEN_BAN` preview | `v2-`+làn (trunk) · `v3-`+vi\|en (GUI) | STALE | giữ trunk |
| SC-7 | Câu nghe thử EN | `CAU_THEO_LAN` (trunk) · `CAU_NGHE_THU_EN` (GUI) | STALE | giữ trunk |
| SC-8 | `doc_lai` ở Lịch sử | trunk có `giai_giong` (hotfix `dc6d9c6b`) · nhánh History bản cũ | **PRODUCTION HOTFIX AT RISK** | giữ trunk; không bao giờ chép nguyên tệp nhánh |
| SC-9 | Migration | hai tệp cùng `down_revision = f2c48b71e903` | CONTRACT CONFLICT (2 head) | nối chuỗi (T-04) |
| SC-10 | Số test | 351×2 · 396 · 398×3 | FILE CONFLICT (không phải git conflict) | cấp lại (§6.4) |
| SC-11 | Trạng thái dự án | cột `trang_thai` · `trang_thai_suy` | DEAD + BRANCH-ONLY | suy ra (D005) |
| SC-12 | Tiền đề "làn rỗng an toàn" | `test_398::…_WS01` xanh vì lý do sai | STALE TEST | viết lại theo Q121 |
| SC-13 | `test_PHEP_DOAN_KHONG_BAO_GIO_DAN_TOI_CHAN` | khẳng định ngược Q121 | STALE TEST | bỏ |
| SC-14 | Docstring migration curation | nói cổng kho chung đọc bảng curation — sai | STALE COMMENT | sửa chú thích (T-17) |
| SC-15 | `du_an.py` docstring `xuat_mot_luot` | nói "tồn tại" — sai | STALE COMMENT | sửa theo Projects |

---

## 4. Locked Decisions

| ID | Quyết định | Chọn |
|---|---|---|
| F-01 | Gốc hợp nhất | `3100c317` (fact, tự xác minh) |
| D001 | Hình dạng hợp nhất | **Một RC, hạ cánh một lần** — commit nguyên tử `Reconciled-from/Dropped`; ff một lần |
| D002 | Ô Ngôn ngữ ở Studio | **Lời khai chỉ THẮT** — chặn khi *khai ≠ làn giọng* HOẶC *đoán chắc ≠ làn giọng*; giữ "Tự động" mặc định |
| D003 | Làn giọng nhân bản | **Giọng mới bắt khai VI/EN; giọng cũ đo ASR** (`do_asr`), đo không chắc ⇒ mời xác nhận, không chặn |
| D004 | Cửa khai làn | **Sửa tự do vi/en trừ khi ngược phép đo ASR chắc chắn**; không về "chưa rõ"; chặn giọng đã thu hồi |
| D005 | Xoá lịch sử khi tệp đang được dùng | **Cho xoá**; hộp xác nhận nêu khối/dự án ảnh hưởng; trạng thái khối suy từ tệp thật |
| D006 | Nghe thử vs Tạo | **Nghe thử hỏi `quyet_dinh` để HIỆN**, không chặn |
| D007 | Public API | **Hook kiểm-trước tuỳ chọn trong `ToolSpec`**; 400 đồng bộ kèm mã; không thêm tham số `ngon_ngu` |
| D008 | Phiên khác chạm vùng Voice | **RC là chủ duy nhất**; yêu cầu vào RC; công cụ đối soát bắt lọt vòng |
| D009 | Nghiệm thu | **Hai tầng**: Tầng 1 `READY_FOR_DEPLOYMENT` · Tầng 2 `RELEASED` chỉ khi chủ dự án ra lệnh deploy |

D002 là một **CHANGE REQUEST với Q121** (`docs/QUYET_DINH_NEN_TANG.md`) — chủ dự án duyệt trong cùng phiên. RC phải cập nhật Q121 cùng commit đổi `quyet_dinh`.

Tự quyết kỹ thuật T-01…T-17 (chủ dự án duyệt cùng baseline):

| ID | Nội dung |
|---|---|
| T-01 | Studio giữ 3 cột |
| T-02 | Preset = `giong_mau_engine.json` (sinh ra); kho chung + nhân bản = DB `voice_profile` |
| T-03 | Bỏ chính sách làn thứ hai của nhánh GUI (SC-1, SC-6, SC-7, SC-13, `data-lan="vi"` gõ cứng) |
| T-04 | Migration một chuỗi: `d15b8c30f7a4 → nguồn gốc làn → voice_lich_su` |
| T-05 | Cấp lại số test (§6.4) |
| T-06 | `dedupe_key` cho ghi danh · đọc lại · khối dự án · phát dần |
| T-07 | Thu hồi: xoá cả tiền tố `voice/{uid}/{pid}/`; chặn khi `dang_ghi_danh`; worker kiểm trạng thái trước khi bật `active`; worker đặt `loi` khi ghi danh hỏng vĩnh viễn |
| T-08 | Preview kho chung; `co_san` trước `nap_ref_b64` |
| T-09 | Giữ `duong_cho_trang`; nhận `duong_cho_app_khac` vào `BE_MAT_CONG_KHAI` |
| T-10 | Cửa Dự án trả `ma_loi` |
| T-11 | Lịch sử xoá thêm khoá cũ `{job_id}.wav` ở tầng app |
| T-12 | Hàng rào QA + mock đủ `/v1/lo-ra-tep`, `/v1/ghep-tep`, `/v1/stream` |
| T-13 | Picker loading/lỗi; chuỗi lỗi qua i18n |
| T-14 | Nâng phiên bản điều khoản cùng commit thu hồi |
| T-15 | Sửa chữ sai dưới ô Ngôn ngữ; `aria-label` `t.ten → d.ten` ở màn Dự án |
| T-16 | Gom danh sách làn về `lan_ngon_ngu`; preset đọc làn từ `giong_mau` |
| T-17 | Sửa docstring migration curation cho khớp hành vi |

---

## 5. System Invariants

| ID | Bất biến | Thẩm quyền | Cưỡng chế |
|---|---|---|---|
| INV-01 | Production chỉ nhận SHA đỉnh RC đã qua Tầng 1; SHA đang chạy = SHA ấy | `/health/version`, `nghiem_thu_deploy` | Tầng 2 |
| INV-02 | Chỉ `lan_ngon_ngu.quyet_dinh` trả phán quyết làn | `lan_ngon_ngu.py` | test AST `test_522` |
| INV-LAN-1 | Không tín hiệu do khách cung cấp nới được luật làn (khai văn bản · khai giọng ngược phép đo) | `quyet_dinh` | `test_355` mở rộng · `test_520` |
| INV-LAN-2 | Không cửa nào gán làn cho giọng mà không có lời khai hoặc phép đo; mọi làn mang nguồn gốc | cột nguồn gốc làn | `test_521` · `test_523` |
| INV-LAN-3 | Mọi cửa có văn bản + giọng HỎI `quyet_dinh`; cửa tiêu tiền CHẶN, cửa miễn phí HIỆN | `quyet_dinh` | `test_356` mở rộng · `test_526` |
| INV-TIEN-1 | Không cửa nào giữ credit trước một phép kiểm làm được ở cửa vào (thứ tự ①–⑥ `CHUAN_VAN_HANH_CUA.md` §3) | hợp đồng cửa | `test_356` · `test_524` |
| INV-TIEN-2 | Mọi cửa nộp việc tiêu tiền đều chống nộp trùng | `job_submit.dedupe_key_for` | `test_356` mở rộng |
| INV-SO-HUU-1 | Đọc được ≠ sửa được; chỉ chủ sở hữu sửa/thu hồi/khai làn | `tham_chieu.tim_profile` / `chi_chu_so_huu` | `test_520` |
| INV-THU-HOI-1 | Giọng đã thu hồi không bao giờ quay lại `active`; thu hồi xoá cả tiền tố lưu trữ | `giong_vong_doi` + kiểm trong worker | `test_520` |
| INV-TRANG-THAI-1 | Trạng thái hiển thị khối/dự án suy từ tệp thật | `du_an` (suy ra) | `test_357` · `test_525` |
| INV-CHU-1 | Mỗi commit vùng Voice chưa lên trunk có đúng một dòng sổ cái | `docs/LTT_VOICE/HOP_NHAT/SO_CAI.json` | `tools/doi_soat_voice.py` · `test_527` |
| INV-NT-1 | `BLOCKED` ≠ `PASS` (0 điểm); `READY_FOR_DEPLOYMENT` ≠ `RELEASED` | bảng chấm §8.3 | báo cáo nghiệm thu |
| INV-BE-MAT-1 | Bề mặt `ltt_voice` mà app khác dùng không bị gỡ nếu chưa báo chương trình phụ thuộc | `apps/ltt_voice/__init__.py::BE_MAT_CONG_KHAI` | test bề mặt công khai |

---

## 6. Target Architecture

### 6.1 Luật làn — một thẩm quyền, bốn đầu vào

```
                 ┌───────────────── lan_ngon_ngu.quyet_dinh ─────────────────┐
  văn bản ──────►│  lan_t_khai  = chuan_lan(khai_bao)            (nếu có)    │
  khai_bao ─────►│  lan_t_doan  = doan_ngon_ngu(text)            (nếu chắc)  │
  lan_giong ────►│  lan_g       = chuan_lan(lan_giong)                        │
                 │                                                            │
                 │  lan_g rỗng                         → CHẶN  unknown        │
                 │  lan_t_khai có và ≠ lan_g           → CHẶN  mismatch       │
                 │  lan_t_doan có và ≠ lan_g           → CHẶN  mismatch  (D002)│
                 │  còn lại                            → CHO                  │
                 └────────────────────────────────────────────────────────────┘
  gọi bởi:  features._chot_lan (Studio · Dự án · Lịch sử · phát dần · worker)
            hook kiểm-trước của speech.ltt (D007)
            cửa nghe thử — chỉ HIỆN (D006)
            bộ chọn giọng — chỉ HIỆN
```

`PhanQuyet.nguon` phân biệt `khai_bao` / `doan` / `theo_giong` như hiện nay; ô mới
chặn với `nguon = doan` khi khách đã khai, để câu hỗ trợ *"sao bị chặn"* còn trả lời được.

### 6.2 Làn của giọng — ba nguồn gốc

Cột mới trên `voice_profile`: **`ngon_ngu_nguon`** (`String(16)`, mặc định `""`), giá trị
`khai_bao` · `do_asr` · `mac_dinh_cu`. Hằng số + phép chuyển hợp lệ ở
`apps/ltt_voice/giong_vong_doi.py` (thẩm quyền duy nhất; lấy từ nhánh My Voices).

| Nguồn | Sinh ra bởi | Cửa khai làn (D004) |
|---|---|---|
| `khai_bao` | ghi danh (bắt buộc khai) · cửa khai làn | đổi tự do vi ↔ en |
| `do_asr` | công cụ di trú ASR, **chỉ** khi độ tin ≥ ngưỡng (D003) | chỉ nhận lời khai **trùng** số đo; ngược ⇒ 400 `voice_language_measured` |
| `mac_dinh_cu` | migration đánh dấu mọi giọng cũ; ASR đo không chắc thì giữ nguyên | đổi tự do ⇒ thành `khai_bao` |

Migration **không** đổi `ngon_ngu` của dòng cũ. Công cụ di trú ASR là thứ duy nhất
được đổi, và chỉ khi độ tin ≥ ngưỡng (ngưỡng là hằng số trong mã công cụ, mượn từ
`tools/soi_kho_giong_cu.py`). Giọng `mac_dinh_cu` hiện lời mời "Xác nhận ngôn ngữ"
trên thẻ giọng, không chặn.

### 6.3 Vòng đời giọng

```
dang_ghi_danh ──worker OK──► active ──/tat──► disabled
      │                        │
      │worker hỏng vĩnh viễn   └──/xoa──► revoked   (xoá voice/{uid}/{pid}/*, giữ profile+consent+lịch sử)
      ▼
     loi
```
Thu hồi khi `dang_ghi_danh` bị từ chối. Worker kiểm `trang_thai` trước khi bật `active`.

### 6.4 Cấp phát số test

| Số | Tệp | Nguồn |
|---|---|---|
| 351 | `test_351_ltt_voice_lifecycle_authz.py` | History |
| 357 | `test_357_ltt_voice_du_an_trang_thai.py` | Projects |
| 358 | `test_358_ban_doc_dai_ranh_gioi.py` | Projects |
| 520 | `test_520_ltt_voice_so_huu.py` | My Voices |
| 521 | `test_521_ltt_voice_ghi_danh_ngon_ngu.py` | My Voices |
| 522 | `test_522_mot_tham_quyen_lan.py` | mới (INV-02) |
| 523 | `test_523_di_tru_lan_asr.py` | mới (D003) |
| 524 | `test_524_public_api_kiem_truoc.py` | mới (D007) |
| 525 | `test_525_lich_su_xoa_trang_thai_suy.py` | mới (D005) |
| 526 | `test_526_nghe_thu_phan_quyet.py` | mới (D006) |
| 527 | `test_527_doi_soat_voice.py` | mới (INV-CHU-1) |
| 528 | `test_528_kho_chung_nghe_thu.py` | mới (T-08) |
| 529–549 | dự trữ cho RC1 | — |

Đo trên **mọi nhánh** ngày 11/09: 357–359 và 520–549 trống.

### 6.5 Sổ cái hợp nhất + công cụ đối soát

- `docs/LTT_VOICE/HOP_NHAT/SO_CAI.json` — dữ liệu máy đọc:
  `vung` (đường dẫn thuộc vùng Voice) · `nguon[]` (mỗi commit nguồn: sha, nhánh,
  hạng mục, `KEEP|DROP|FIX`, lý do/D-id, RC sha, test chứng minh) · `yeu_cau[]`
  (yêu cầu từ phiên khác, D008) · `cap_phat_test`.
- `tools/doi_soat_voice.py` — **chỉ đọc**. Liệt kê mọi commit trên mọi nhánh cục bộ
  chạm `vung` mà chưa có trong trunk; thoát ≠ 0 nếu commit nào không có dòng
  trong `nguon[]`. **Không** là bước gate (gate chạy ở mọi cây; không được đỏ vì
  nhánh người khác). Thời điểm chạy: đầu phiên, trước ff, trước deploy.
- `docs/LTT_VOICE/NGUON_CHAN_LY.md` thêm một dòng trỏ tới sổ cái + spec này, và
  mục *"khẳng định không còn đúng ⑥"*: chính sách chỉ-cảnh-báo của nhánh GUI.

### 6.6 Hook kiểm-trước của Public API

`ToolSpec` nhận thuộc tính tuỳ chọn **`kiem_truoc: str = ""`** — tham chiếu dotted
`module:callable` do app sở hữu, cùng khuôn `sync_executor` / `tuy_chon_dong` (nền
tảng resolve lúc cần, không import app lúc nạp). Callable có chữ ký
`(db, user_id, params) -> None` và ném `LoiNguoiGoi` mang mã. Với `speech.ltt`:
`apps.ltt_voice.kiem_truoc_api:kiem` (gọi `features.chuan_hoa` + `giai_giong`).
`invocation.py` gọi nó **sau**
phép kiểm hình dạng tham số và **trước** `submit_with_credit`; lỗi đi ra phong bì lỗi
sẵn có với mã lấy từ ngoại lệ; mã mới đăng ký trong `contract.py`. Tool không khai
hook ⇒ hành vi không đổi. Worker vẫn kiểm (phòng thủ nhiều lớp).

⚠️ Luật 20 (`CLAUDE.md`): đây là sửa `platform_core`. Lý do: hợp đồng app **thiếu**
một điểm kiểm trước khi giữ tiền — không app nào tự làm được điều đó từ thư mục của nó.

---

## 7. Reconciliation Strategy

```
6 NHÁNH NGUỒN ── đóng băng, không viết lại lịch sử
   │ đọc diff theo HÀNH VI · không merge · không cherry-pick nguyên commit
   ▼
RC  claude/ltt-voice-reconciliation-165a40  @ 3100c317
   commit nguyên tử theo thứ tự phụ thuộc, mỗi commit:
     Reconciled-from: <sha> (phần nào)   Dropped: <gì> (vì sao, D/T-id)
   ▼
admin-mvp-v3 (fast-forward, một lần)
```

Thứ tự phụ thuộc bắt buộc (sự thật đã đo, không phải sở thích):

1. Sổ cái + đối soát + hàng rào QA **trước** mọi thay đổi hành vi.
2. Luật làn (`quyet_dinh`, D002) **trước** giao diện làn.
3. Cửa khai làn (D004) **trước hoặc cùng** thứ sinh ra giọng thiếu làn tường minh.
4. Migration nguồn gốc làn **trước** migration `voice_lich_su`.
5. Sửa worker (T-07) **cùng** commit thu hồi.
6. Trạng thái khối suy ra (D005) **cùng hoặc trước** nút Xoá lịch sử.

Quy tắc đối chiếu một hạng mục: đọc ý định → diff với production → giữ hành vi
tốt → bỏ hành vi cũ (ghi `Dropped`) → viết lại trên RC → test.

Đồng bộ trunk: ngay trước lượt cổng cuối và ngay trước ff, theo
`docs/16_CAP_NHAT_VA_DEPLOY.md`. Nếu trunk đã đi, hoà trunk vào RC (merge, không
rebase), chạy lại cổng cuối.

---

## 8. Testing Strategy

### 8.1 Cấp test

Theo `docs/00_LTT_OPERATING_CONTRACT.md` §4 và §7 — **không định nghĩa lại ở đây**.
Áp cho RC1: mỗi commit checkpoint dùng cấp của hợp đồng cho checkpoint; RC1 chạm
migration + `platform_core` + worker nên cổng đầy đủ bắt buộc ở đỉnh RC trước ff.
Mọi lệnh nặng tuân `docs/QUY_TAC_CHAY_LENH_NANG.md` và trần worker ở `CLAUDE.md`
toàn cục.

### 8.2 Ma trận nghiệm thu Voice (Tầng 1)

| Nhóm | Ca bắt buộc |
|---|---|
| Studio | VI+VI PASS · EN+EN PASS · VI+EN CHẶN · EN+VI CHẶN · trộn có dấu ⇒ vi · khai VI + văn bản EN chắc ⇒ CHẶN (D002) |
| Giọng | ghi danh bắt khai · consent · làn · active · preview · tắt · thu hồi · `loi` · khai làn · khai ngược `do_asr` ⇒ CHẶN · chủ sở hữu |
| Kho chung | danh mục · lọc VI · lọc EN · preview cho người không phải chủ · license · đọc được · sửa bị từ chối |
| Dự án | tạo · khối · giọng/khối · tạo một · tạo tất cả · an toàn làn + `ma_loi` · tệp hết hạn ⇒ "cần tạo lại" |
| Lịch sử | danh sách · lọc · phát · tải · đọc lại (hotfix giữ) · giọng ôi · lệch làn · xoá (hộp xác nhận nêu khối) · đã tải |
| API | xác thực · kiểm-trước 400 có mã · không giữ tiền khi bị từ chối · job · poll · artifact · hết hạn |
| Runtime | queued · running · done · failed · retry · sidecar bận · không có worker |
| Credit | báo giá · giữ · quyết toán · hoàn · thất bại · thử lại · nộp trùng ở MỌI cửa |
| Lưu trữ | cô lập chủ sở hữu · kho chung · nguồn · preview · output · Range · MP3 |

Tổng hợp **thật** VI và EN qua pipeline đầy đủ, gọi sidecar máy A — cần quyền đọc
`LTT_VOICE_SIDECAR_TOKEN` đúng thời điểm. Giọng EN dựng bằng ghi danh một clip
tiếng Anh trên CSDL dev. Không có quyền ⇒ `BLOCKED`, không `PASS`.

### 8.3 Bảng chấm

Theo khung 100 điểm của yêu cầu gốc (Architecture 10 · Studio 10 · Language 10 ·
Catalog 8 · My Voices 8 · Projects 8 · History 6 · API 6 · Jobs 8 · Credit 8 ·
Storage 6 · GUI 6 · Tests/Browser/CI 4 · Deploy/Rollback 2). Mục `BLOCKED` = 0
điểm của mục ấy. ≥98 chỉ công nhận khi không còn `BLOCKED` ở Language, Credit,
Studio, Jobs.

---

## 9. Browser QA

- Bộ vĩnh viễn ở `tests/browser/ltt_voice_*.js`, chạy bằng Playwright, Chrome thật
  (`channel: "chrome"`, có đầu khi QA tương tác) vào máy chủ RC loopback + sidecar
  giả cho luồng tất định; một luồng riêng dùng sidecar thật cho VI/EN.
- Mỗi luồng bắt: `console.error` · `pageerror` · `requestfailed` · HTTP ≥ 400 không
  mong đợi · spinner quá hạn · tràn bố cục · bàn phím · modal · audio · tải xuống.
- Khung hình: 1280×720 · 1366×768 · 1440×900 · 1920×1080 · 390×844 · 768×1024.
- Hàng rào tĩnh `tools/check_voice_qa.py` (bước gate, chỉ đọc) ghim các luồng này
  không bị rút ruột.
- Tầng 2: cùng bộ, chạy trên `https://app.lttstudios.com` bằng tài khoản test vận
  hành (không dùng admin), nối Chrome thật qua CDP.

---

## 10. Deployment Strategy

### 10.1 Không deploy trong RC

Deploy chỉ khi chủ dự án ra lệnh. Quy trình: `docs/16_CAP_NHAT_VA_DEPLOY.md`.

### 10.2 Tầng 2 — `RELEASED`

1. SHA tested = SHA ff = SHA deploy (ghi vào sổ cái).
2. `/health/version` = SHA ấy.
3. `tools/nghiem_thu_deploy.py` 0/0/0 **và** phép so tệp không `.py` 0/0/0.
4. `alembic upgrade head` một head.
5. Chạy công cụ di trú ASR trên production (D003) — ghi số giọng đã đo/đổi/không chắc.
6. Bộ Playwright trên URL công khai.
7. Public API live bằng khoá đọc (`api_prod_canary --token-file`); không có ⇒ `BLOCKED`.

### 10.3 Lỗ đo đã phát hiện

`nghiem_thu_deploy.py` chỉ so `.py` — một bản deploy chỉ lệch JS hiện nay trả `DAT`.
RC1 mở rộng chính công cụ ấy so **mọi tệp được theo dõi** trong `GOI` (bỏ `__pycache__`),
giữ nguyên dòng kết luận và mã thoát.

---

## 11. Rollback Strategy

| Tầng | Cách lui | Vì sao an toàn |
|---|---|---|
| Code | `C:\LTTPlatform\app.previous` (đường lui của bộ cài) | bản trước giữ nguyên |
| Schema | hai migration chỉ **thêm** (một cột, một bảng) | code cũ bỏ qua cột/bảng lạ; không cần downgrade để chạy lại bản cũ |
| Dữ liệu ASR | công cụ ghi giá trị cũ + nguồn gốc cũ trước khi đổi | đảo được bằng chính công cụ (`--dao`) |
| Tệp đã xoá (thu hồi, xoá lịch sử) | **không đảo được** — đúng ý nghĩa của xoá | có hộp xác nhận; không chạy trên dữ liệu thật trong RC |
| Public API | hook tuỳ chọn; gỡ khai báo trên `ToolSpec` ⇒ hành vi cũ | không đổi hợp đồng cũ, chỉ thêm mã lỗi |

---

## 12. Definition of Done

`READY_FOR_DEPLOYMENT` (Tầng 1) chỉ khi **tất cả**:

- một cây hợp nhất (RC) · 0 xung đột ngữ nghĩa chưa xử lý (§3 mọi dòng có kết cục)
- `tools/doi_soat_voice.py` = 0 commit chưa đối soát
- 0 bất biến bị nhân đôi thẩm quyền (§5)
- cổng đầy đủ xanh trên SHA đỉnh RC
- bộ Chrome thật xanh (§9)
- tổng hợp thật VI xanh · EN xanh (hoặc `BLOCKED` ghi rõ ⇒ **NOT READY**)
- vòng đời credit xanh ở mọi cửa
- di trú chạy khô trên bản restore-drill xanh
- điểm ≥ 98 theo §8.3

Thiếu một ⇒ báo **NOT READY** kèm danh sách chặn.

---

## 13. Explicit Non-goals

- Scheduler ưu tiên (`architecture/scheduler-priority-v1`) — chỉ nghiệm thu lại thứ tự job Voice nếu nó lên trunk trước.
- Ba công thức ước giá (giữ tiền · xem trước · phát dần) — thẩm quyền nhân đôi thật, chạm tiền ⇒ hạng mục riêng, đo trước.
- Bộ đếm nghe thử trong bộ nhớ tiến trình — đo số tiến trình trước.
- Tên suất GPU gõ cứng; ghi danh và dựng preview không xin suất.
- Gốc R1 (`origin/master` cũ) — DEFERRED.
- Tham số `ngon_ngu` công khai cho `speech.ltt`.
- Refactor app khác, `platform_core` ngoài hook D007.
- Deploy (chỉ khi chủ dự án ra lệnh).
