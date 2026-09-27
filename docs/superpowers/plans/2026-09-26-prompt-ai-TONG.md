# PROMPT AI — thiết kế lại: PLAN TỔNG

> **Đây là tệp điều khiển.** Nó giữ logic vận hành, thứ tự, và phân làn. Năm tệp pha
> bên dưới giữ **các bước TDD chi tiết** — chúng là phần chi tiết của plan này,
> ⛔ không phải nguồn chân lý song song. Lệch nhau ⇒ tệp này thắng, và phải sửa tệp pha.

**Trạng thái — đo ngày 28/09/2026, ⛔ không phải tự khai.** Năm pha đã viết xong mã;
ba pha đang sống trên production. Đối chứng dùng **migration**, không dùng ô tick:
mỗi pha có đúng một migration, và `git log main -- <tệp migration>` trả lời dứt khoát
*"pha này có trên `main` chưa"* — một ô tick chỉ nói ai đó đã tick.

| Pha | Mã | Trên `main` | Production | Còn nợ |
|---|---|---|---|---|
| 1 · Chỗ nối | ✅ | ✅ `a82786f7` | ✅ `fd565a47` | — |
| 2 · Giao bài | ✅ | ✅ `b4f24329` | ✅ | — |
| 3 · Lõi Studio | ✅ | ✅ `b4f24329` | ✅ (kiểm trên trình duyệt thật) | — |
| 4 · Kho chung | ✅ | ⛔ | ⛔ | gộp `main` · nghiệm thu GUI |
| 5 · Kho tài nguyên | ✅ | ⛔ | ⛔ | gộp `main` · nghiệm thu GUI |
| 6 · Chia lô (Q-16) | ⛔ | — | — | **chưa có plan** ⇒ chặn E5 |

⚠️ **Và đây là một lỗi sổ sách, ghi lại để người sau không tin ô tick.** 397 ô
`- [ ]` trong năm tệp pha ⛔ **chưa bao giờ được tick**, nên một phép đếm máy móc
trả **0/397 = 0%** trong khi 5/6 pha đã xong và 3/6 đã ra khách. Trạng thái được
theo dõi trong hội thoại thay vì trong tệp — đúng thứ luật toàn cục cấm
(*"trạng thái công việc ghi vào tệp plan/sổ lỗi, không chỉ trong hội thoại"*).

⇒ ⛔ **Đừng "sửa" bằng cách tick 397 ô.** Tick một ô mình không kiểm được từng
cái là chế ra bằng chứng. Bảng trên đo **cái đo được** (migration nào trên `main`),
và đó là thứ dùng để phán quyết.

| Tài liệu | Đường |
|---|---|
| **Spec** (thiết kế, nguồn chân lý của hợp đồng) | [`../specs/2026-09-26-prompt-ai-thiet-ke-lai-design.md`](../specs/2026-09-26-prompt-ai-thiet-ke-lai-design.md) |
| 15 quyết định của chủ dự án | [`../../PROMPT_AI/QUYET_DINH_26-09.md`](../../PROMPT_AI/QUYET_DINH_26-09.md) |
| Bảng đối chiếu + bằng chứng đo được | [`../../PROMPT_AI/DOI_CHIEU_PROMPT_SEEDANCE_STUDIO.md`](../../PROMPT_AI/DOI_CHIEU_PROMPT_SEEDANCE_STUDIO.md) |

**Mục tiêu một câu:** biến `apps/prompt_ai_ommi` từ app **đang trả `503` trên production**
thành máy dựng prompt có ba thứ bản gốc chứng minh là dùng thật — **storyboard**,
**vòng lặp iterate**, và **chỗ nối không mất dữ liệu** sang app sinh video.

---

## 1. Năm tệp pha

| Pha | Tệp | Dòng | Task | Step |
|---|---|---|---|---|
| 1 · Chỗ nối đúng | [pha1-cho-noi-dung](2026-09-26-prompt-ai-pha1-cho-noi-dung.md) | 2 427 | 9 | 64 |
| 2 · Giao bài | [pha2-giao-bai](2026-09-26-prompt-ai-pha2-giao-bai.md) | 2 398 | 8 | 58 |
| 3 · Lõi Studio | [pha3-loi-studio](2026-09-26-prompt-ai-pha3-loi-studio.md) | 3 593 | 21 | 111 |
| 4 · Kho chung | [pha4-kho-chung](2026-09-26-prompt-ai-pha4-kho-chung.md) | 2 833 | 15 | 81 |
| 5 · Kho tài nguyên sâu | [pha5-kho-tai-nguyen](2026-09-26-prompt-ai-pha5-kho-tai-nguyen.md) | 3 035 | 12 | 83 |
| | **Tổng** | **14 286** | **65** | **397** |

---

## 2. Dòng thời gian — mỗi pha deploy được riêng

```
Pha 1  CHO NOI DUNG
       bindings + refs that + bat bien o bien + bat ROLLOUT
       => DEPLOY: giao bai sang taovideo khong mat anh
         |
Pha 2  GIAO BAI
       ommi_handoff + prefill form taovideo + canh app->app
       => DEPLOY: khach sua tham so trong taovideo roi tu bam chay
         |
Pha 3  LOI STUDIO
       ommi_brief + ommi_canh + 2-pane + character_lock + Bundle + iterate
       => DEPLOY: PROMPT AI moi thanh hinh; XOA apps/prompt_canh
         |
Pha 4  KHO CHUNG
       chia se bang MA + nhap 12 meta / 21 template / 13 snippet
       => DEPLOY: kho dung duoc, noi dung ban goc da sang
         |
Pha 5  KHO TAI NGUYEN SAU
       dedupe + bulk + ZIP + thumbnail + thung rac + composite + breakdown
       => DEPLOY  ->  GATE (MOT lan, MOT cap)  ->  het plan
```

⛔ **Gate chạy đúng MỘT lần, ở Task cuối của pha 5.** Hết một pha **không phải** cuối
plan (hợp đồng §4, `CLAUDE.md` luật 1). Trong phiên: test **nhắm** cụm vừa sửa.

**Ranh giới mỗi pha:** test nhắm xanh → gộp `main` → `pre-commit run --all-files`
(N-56: merge **không** chạy bánh cóc, nên đây là lưới duy nhất) → deploy nếu cần → báo.

---

## 3. Phân làn — một tệp một chủ

| Làn | Pha | Sở hữu tệp | Dải test |
|---|---|---|---|
| **M**₁ | 1 | tách `tables/`, migration pha 1, `tools/lint_app_contract.py`, `apps/taovideo/__init__.py` | 5100–5109 |
| **A** | 1 | `services/bindings.py`, `routes/bindings.py`, sửa `services/composer.py` | 5110–5129 |
| **B**₁ | 1 | `services/bat_bien.py`, sửa `routes/handoff.py` (vá N-1) | 5130–5133 |
| **B**₂ | 2 | `services/handoff_stage.py`, `apps/taovideo/prefill.py`, sửa `apps/taovideo/routes.py` + template | 5134–5159 |
| **M**₃ | 3 | migration pha 3, `tables/*`, `manifest.py`, `jobs.py`, `routes/__init__.py` | 5300 |
| **C** | 3 | `services/placeholders.py`, `bundle.py`, `briefs.py`, `routes/briefs.py` | 5301–5319 |
| **D** | 3 | `services/iterate.py`, `routes/iterate.py` | 5320–5339 |
| **E** | 3 | `services/nhan_vat.py`, `routes/nhan_vat.py`, `prompts/khoa_nhan_vat.txt`, **xoá `apps/prompt_canh`** | 5340–5369 |
| **M**₄ | 4 | migration pha 4 (`share_level` × 10 bảng + 6 bảng mới) | 5400, 5405 |
| **F** | 4 | `services/chia_se.py`, `routes/chia_se.py`, `tables/chia_se.py` | 5401–5419 |
| **G** | 4 | `services/nhap_mau_goc.py`, `prompts/mau_goc/*.json`, `tables/thu_vien.py`, `library.dat_mac_dinh` | 5420–5449 |
| **M**₅ | 5 | migration pha 5, **Task GATE cuối cùng** | 5500 |
| **H** | 5 | `services/dedupe.py`, `thung_rac.py`, `routes/resources.py`, `jobs.py` | 5501–5529 |
| **I** | 5 | `services/composite.py`, `breakdown.py`, `routes/library.py`, `routes/storyboard.py` | 5530–5559 |
| **J** | 3–5 | **toàn bộ** `frontend/prompt-ai-ommi/src/` | 5560–5579 |

### 3.1 Sổ đăng ký dùng chung — chủ duy nhất

Đây là chỗ các làn va nhau (bài học `so-dang-ky-dung-chung-la-cho-cac-lan-va-nhau`).

| Sổ | Chủ duy nhất | Luật |
|---|---|---|
| `alembic/versions/` | **làn M của pha đó** | ⛔ Làn nghiệp vụ **không** tạo tệp migration. Khai cột cần, làn M viết. **MỘT head** — head lúc lập plan: `edb8b0fc0ac9` |
| `manifest.py` · `jobs.py` · `routes/__init__.py` | **làn M** | Làn khác gửi yêu cầu, không tự sửa |
| `tables/` | **làn M** | Làn nghiệp vụ sở hữu `services/` + `routes/`, ⛔ không sở hữu model |
| `tools/lint_app_contract.py` · `apps/taovideo/__init__.py` | **làn M₁** | Cạnh app→app phải khai **hai đầu** — xem §5 |
| `frontend/` | **làn J** | Một chủ cho frontend để tránh xung đột CSS/state |
| `tools/check_so_test.moc` | **không ai** | Chỉ giảm. ⛔ Không `--accept` khi còn sửa dở của người khác |
| Dải số test | bảng §3 | ⛔ Không lấy số ngoài dải. Trước khi tạo tệp: `python tools/check_so_test.py --list` |

### 3.2 Cái gì chặn cái gì

```
M1 -> A -> B1 -> [gop main, DEPLOY pha 1]
                   |
                 B2 -> [gop main, DEPLOY pha 2]
                   |
                 M3 -> C1..C6 -> D1 -> C7 -> D2 -> [deploy pha 3]
                        |          
                        +-> E1 -> E2 -> E3 -> E4 -> E5(xoa prompt_canh)
                        |
                        +-> J (theo sau C, D, E)
                   |
                 M4 -> F -> G -> [deploy pha 4]
                   |
                 M5 -> H -> I -> [deploy pha 5] -> GATE
```

**Song song được:** `C ∥ E` · `F ∥ H` (chỉ khi M₄ và M₅ đã xong migration cả hai pha).
**Bắt buộc tuần tự:** `A → B` (cần `ommi_binding`) · `F → G` (cần `share_level`) ·
`D1 → C7` (xem §7 lỗi đã tìm ra) · `E3 → E4 → E5`.

---

## 4. Logic vận hành mới — một chỗ để đối soát

Đây là phần chủ dự án cần đọc kỹ nhất: **khách làm gì, hệ thống làm gì, tiền chạy đi đâu.**

```
1  Khach tao BRIEF (tieu de, noi dung, so canh, thoi luong, ti le)
       -> ommi_brief    [thuc the rieng, KHONG con nhet trong AppProject.payload]

2  Khach chon NHAN VAT / BOI CANH (tuy chon)
       -> POST /api/characters/{id}/lock  => LLM dung `fixed_prompt_block`
       -> khoi chu do CHEN NGUYEN VAN vao prompt MOI canh   [3 credit/lan]

3  Khach gan ANH THAM CHIEU cho canh
       -> ommi_binding: the @IMAGE_k / @VIDEO_k  <->  variant_id
          [day la NGUON CHAN LY cua the — chua con bo N-2]

4  PREFLIGHT   kiem brief du dieu kien chua            MIEN PHI, khong ghi CSDL
5  BUNDLE      render meta-prompt + danh sach asset    MIEN PHI, KHONG goi LLM
                  -> khach copy dem sang LLM rieng cung duoc (Q-6)
6  BAO GIA     tra `credit` + `free_left`              MIEN PHI, authoritative
7  CHAY        luot 1, 2  => credit 0, was_free=true   [bo dem trong CSDL]
                  luot 3+ => thu credit qua submit_with_credit
       -> ommi_iteration ghi tung luot: feedback, credit, job_id
8  PHAN QUYET  kept | rejected      ⛔ rejected KHONG hoan credit
9  ITERATE     gop y -> gui lai brief + gop y -> ve buoc 7

10 STORYBOARD  ve khung hinh tham chieu TRONG PROMPT AI   [Q-12]
                  ⛔ KHONG day sang Seedance Video

11 GIAO BAI    MOT canh MOT lan (Q-13, y nhu ban goc)
       -> POST /api/projects/{id}/handoff/video
          => ommi_handoff: ve dung MOT lan, het han 30 phut
          => payload: prompt (co Camera:/Lighting:/Mood: NGUYEN VAN)
                      + refs (anh da chuan hoa <=8MiB, <=2048px)
                      + tag_map (@IMAGE_k -> @IMG_k)
                      + skipped / skipped_over_limit
          => BAT BIEN O BIEN: prompt nhac @IMG_k ma refs thieu => NEM
       -> dieu huong sang /taovideo/?tu_studio=<ve>
       -> taovideo dien san form; khach SUA roi TU BAM CHAY va tra tien o do
```

### 4.1 Tiền chạy đi đâu — bảng duy nhất

| Việc | Credit | Ghi chú |
|---|---|---|
| Preflight | **0** | Không gọi LLM, không ghi CSDL |
| **Bundle** | **0** | Q-6 — chủ dự án chốt mở miễn phí |
| Báo giá | **0** | `authoritative: true`, frontend ⛔ không tự tính lại |
| Dựng kịch bản — lượt **1, 2** mỗi brief | **0** | Bộ đếm `ommi_brief.free_iterations_used` nằm **trong CSDL** |
| Dựng kịch bản — lượt **3+** | `max(3, min(9, ⌈director/2⌉))` | Qua `submit_with_credit` (giữ chỗ → quyết toán → hoàn) |
| Khoá nhân vật / bối cảnh | **3** | Không phụ thuộc số cảnh |
| Render khung hình storyboard | giá của `taoanh.generate` | Job của app khác |
| Giao bài sang video | **0** ở PROMPT AI | Khách trả tiền **trong `taovideo`** khi tự bấm chạy |

⚠️ **Hai rủi ro tiền đã biết, ghi ra chứ không giấu:**
1. **Nhân bản brief** đặt lại bộ đếm về 0 ⇒ khách nhân bản liên tục để có 2 lượt miễn phí nữa.
   Plan chọn `0` (bản sao là kịch bản mới). Đo được lạm dụng ⇒ sửa **một dòng** trong
   `briefs.nhan_ban`, và ghi `docs/NHAT_KY.md`.
2. **`rejected` không hoàn credit.** Nếu sau này ai đó "sửa cho khách dễ chịu" bằng cách
   hoàn, app thành LLM miễn phí vô hạn. Đã có bánh cóc đọc mã chặn (`test_5321`).

---

## 5. Bốn chỗ chết người — nếu bỏ sót thì pha đó vô nghĩa

| # | Chỗ | Vì sao chết người | Ai làm |
|---|---|---|---|
| **K-1** | `refs` không được rỗng khi prompt nhắc `@IMG_k` | Đây **là** con bọ N-1: khách trả credit dựng prompt khoá nhân vật rồi nhận video **không có nhân vật của mình**. Bất biến ở biên (B-1…B-5) là thuốc | B₁ (`test_5131`) |
| **K-2** | Khai cạnh app→app phải **HAI ĐẦU** | `tools/lint_app_contract.py:381-398` đối chiếu hai chiều. `apps/taovideo/__init__.py` **đang RỖNG** ⇒ thêm cạnh mà quên `BE_MAT_CONG_KHAI` là gate **ĐỎ**. Và bản khai phải là **tuple literal** — bọc `frozenset(...)` làm linter đọc bằng `ast.literal_eval` không ra, hàng rào **im lặng** như chưa khai gì | M₁ (`test_5102`) |
| **K-3** | Chi tiết `camera`/`lighting`/`mood` phải vào **prompt**, enum chỉ là gợi ý | `taovideo` khai ba trường đó là **enum ĐÓNG** (`manifest.py:196-198`). Ai "sửa N-1" bằng cách khớp enum rồi **bỏ** chữ gốc thì **vứt trường im lặng lần thứ hai**. Thêm nữa: `camera` nằm trong `idempotency.key_fields` ⇒ hàm suy ra enum phải **tất định** | C (`test_5309`), B₂ (`test_5137`) |
| **K-4** | `ommi_canh.id` phải **tái dùng** id cảnh cũ | Sinh id mới ⇒ **mọi** binding pha 1 trỏ vào hư không, ảnh tham chiếu mất sạch, và **không ai báo lỗi** vì chẳng ai xem lại prompt cũ | C (`test_5305`, `test_5308`) |

---

## 6. Ba phép không được thiếu (spec §10.2)

| # | Phép | Ở đâu |
|---|---|---|
| **T-1** | **Tiêm lỗi cũ**: cảnh có 2 ảnh, ép `refs=[]` ⇒ `bat_bien_giao_bai` **phải** ném | pha 1 `test_5131` |
| **T-2** | **Cả tập, không mẫu đại diện**: `kiem_placeholder` trên **cả 12** meta prompt | pha 3 `test_5303` (bộ placeholder) → pha 4 `test_5440` (nội dung thật) |
| **T-3** | **Bộ đếm trong CSDL**: 2 lượt free, lượt 3 thu tiền, **đóng rồi mở lại session** vẫn thu | pha 3 `test_5320` |

⚠️ **Phạm vi T-2 phải nói đúng** (bài học `pham-vi-phep-do-hep-hon-loi-tuyen-bo`):
pha 3 đo **bộ placeholder**; pha 4 đo **nội dung thật đã nhập**. Và 21 image template dùng
bộ placeholder **khác** (`{SUBJECT}`, `{STYLE}`, `{EXTRA}`, `{EQUIPMENT}`) mà nguồn giá trị
ở **pha 5** ⇒ pha 4 chỉ đo được **tính nhất quán cú pháp**. ⛔ Đừng báo "đã kiểm 21 template".

---

## 7. Điều phối đã tự soát — và tìm ra 14 lỗi trong chính spec của mình

Chạy ba phép tự soát của skill `writing-plans` trên **cả năm** tệp plan cùng lúc.

### 7.1 Lỗi liên pha đã vá

| # | Lỗi | Đã vá |
|---|---|---|
| 1 | `test_5132`, `test_5133` — pha 1 và pha 2 **cùng số, khác tên** ⇒ bánh cóc `check_so_test.py` sẽ đỏ | Pha 2 đổi sang `5138`/`5139` |
| 2 | `test_5100_tables_package_re_export` có ở **cả** pha 1 và pha 4 | Pha 4 đổi sang `test_5405_tables_package_pha4` |
| 3 | ⭐ **Tên hàm `bindings` lệch hoàn toàn**: pha 1 cài `list_bindings`/`replace_bindings`/`delete_binding`/`binding_lines` (keyword-only, có `BindingError`/`BindingNotFound`); spec §5.1 và pha 3 gọi `doc_bindings`/`dat_bindings`/`co_binding` | **Pha 1 thắng** (có mã thật, bộ tên tốt hơn). Đã sửa spec §5.1 **và** 13 chỗ trong pha 3. ⚠️ **Không có `co_binding`** — `has_binding` suy ra bằng `bool(list_bindings(...))` |
| 4 | Vá #2 **tạo ra** xung đột mới: `test_5401` trùng với `test_5401_chia_se_sinh_thu_hoi` của pha 4 | Đổi tiếp sang `5405` |

**Sau khi vá:** 82 số test, **0 số trùng** trên cả 5 plan.

### 7.2 Lỗi trong spec do các làn bắt được

| Làn | Lỗi/lỗ trong spec | Đã xử |
|---|---|---|
| 1 | Chữ ký `bat_bien_giao_bai` **không đủ tham số để cài đặt chính điều kiện B-5** | Thêm `has_binding` keyword-only |
| 1 | `taovideo` khai `camera`/`motion`/`visual_style` là **enum ĐÓNG** | §6.2b: chi tiết vào `prompt`, enum là gợi ý thô, không khớp thì `""`, hàm phải **tất định** |
| 2 | `services/bindings.py` không có hàm đọc nào được đặt tên | Khai chữ ký công khai trong §5.1 |
| 2 | Enum `taovideo` buộc phải **chép literal** (G-3b cấm import `manifest`) ⇒ hai chỗ khai một điều | §10.3: bánh cóc `test_5156` đặt **ngoài cả hai app** |
| 2 | `ommi_handoff.scene_id` trỏ cảnh nào — mơ hồ | §4.3 phán quyết |
| 4 | **Lỗi đếm của điều phối**: 21 template là **7/7/7**, không phải 7/8/9 | Đã sửa bảng đối chiếu |
| 4 | 21 image template dùng bộ placeholder **khác**, và `ommi_image_template` **thiếu cột `placeholders`** | Thêm cột + §7.2, nói rõ phạm vi T-2 |
| 4 | `library.dat_mac_dinh()` được §4.2 dùng mà **không làn nào sở hữu** | Giao làn G |
| 4 | Không endpoint nào đặt `share_level` | Thêm `POST /api/library/{kind}/{id}/share-level`, `catalog` chỉ admin |
| 5 | §6.7 có endpoint mà **không ai sở hữu tệp route** | `routes/resources.py`+`jobs.py` → H; `routes/library.py`+`routes/storyboard.py` → I |
| 5 | Dải số làn M **cắn vào** dải làn nghiệp vụ ở pha 4/5 | Tách số riêng cho làn M từng pha |
| 3 | `LUOT_MIEN_PHI = 2` khai ở làn D, mà `routes/briefs.py::quote` của làn C **gõ lại số `2`** | `quote` phải dùng `con_mien_phi()`; và **đổi thứ tự** thành `D1 → C7` |

### 7.3 Phán quyết nặng nhất: HAI thứ cùng tên "cảnh"

Không phải lỗi của spec — là lỗi **có sẵn trong app**. Đo được:

| | `AppProject.payload["scenes"]` | bảng `ommi_scene` |
|---|---|---|
| Thực chất | **Cảnh kịch bản** (AI Director sinh) | **Khung hình storyboard** |
| Có `prompt` · `camera` · `continuity` | ✅ ✅ ✅ | ✅ ✅ ✅ |
| Ai đọc | `jobs.py:15`, `project_schema.py:128`, `routes/handoff.py:73`, `routes/projects.py:299`, `routes/assets_catalog.py:90` | `services/storyboard.py`, `services/retention.py:76` |
| Khoá liên kết sang bên kia | **KHÔNG CÓ** | **KHÔNG CÓ** |

Đúng dạng `hai-cho-khai-cung-mot-dieu-khong-ai-bat-khop`. Phán quyết (spec §4.3):
cảnh kịch bản là **nguồn chân lý duy nhất** của prompt đi ra ngoài (`ommi_canh` mới);
`ommi_scene` là **khung hình**, thêm `canh_id`; và `ommi_canh.id` **tái dùng đúng id cũ**
để binding pha 1 **sống sót** qua pha 3 không cần di trú.

### 7.4 Còn lại, nói thẳng

| Chỗ | Trạng thái |
|---|---|
| `down_revision` của migration pha 2–5 | **Cố ý không có giá trị cứng** — head thật chỉ biết lúc thi hành. Mỗi chỗ kèm lệnh `python -m alembic heads` + luật MỘT head |
| Tên biến cục bộ trong `composer.director_prompt` (pha 3 E3) | Cố ý không đoán — kèm lệnh `grep` để đọc mã đang có |
| `ommi_face_embedding` | Pha 3 **chỉ tạo bảng**, không service/route (spec §6.5 không có endpoint). Người ghi đầu tiên là `services/composite.py` pha 5. ⛔ Không viết mã phòng thủ |
| Fixture `db_factory` (pha 3 T-3) | Nếu repo chưa có, tạo **cục bộ trong tệp test**. ⛔ Không sửa `tests/conftest.py` gốc — tệp dùng chung của mọi phiên |
| Số zip-bomb / thumbnail (pha 5) | Làn 5 **tự chọn** vì spec không cho: 300 mục · 20 MiB/mục · 500 MiB tổng · tỉ lệ nén 100× · thumbnail 320×320 JPEG q82. Chủ dự án xem lại nếu muốn số khác |

---

## 8. Rủi ro — và cái giá nếu quyết định sai

| # | Rủi ro | Giảm thiểu / cái giá |
|---|---|---|
| R-1 | 8 tính năng đo được là **0 dòng ở bản gốc** vẫn xây theo Q-14 (Profiles, `characters`/`outfits`/`poses`/`backgrounds`, `face_embeddings`, kế thừa style, budget cap) | Điều phối đã nêu bằng chứng và khuyến nghị bỏ; chủ dự án chốt xây. Đặt cuối pha 3/4 ⇒ **cắt phạm vi thì cắt ở đây trước** |
| R-2 | Cạnh `("prompt_ai_ommi","taovideo")` mở tiền lệ; app thứ ba muốn nhận ảnh phải khai cạnh nữa, dần thành lưới | Cạnh giới hạn ở **đúng một module** `apps.taovideo.refs`, 5 tên. ⛔ Không import `routes`/`jobs`/`cost`/`manifest`. Có test AST chặn (pha 2 `test_5155`) |
| R-3 | Nhập 12 mẫu gốc làm hỏng catalog đang có | Endpoint **idempotent** theo `(target_format, name)`; chạy trên tài khoản thử trước |
| R-4 | Tách `tables.py` thành package làm vỡ import cũ | `tables/__init__.py` re-export **đủ mọi** tên lớp cũ; `test_5100` khẳng định |
| R-5 | Bật `ROLLOUT=public` ở pha 1, nhưng pha 3 **đổi hẳn lối vào** ⇒ khách vừa quen lại phải học lại | Chủ dự án chốt bật luôn (Q-11), và đã xác nhận **chưa có khách thật** — đo được 26/09: `LTT_PROMPT_AI_OMMI_ROLLOUT` chưa đặt trên cả `LTTStudioWeb` và `LTTStudioWorker` |
| R-6 | Xoá `apps/prompt_canh` làm đỏ **10 tệp test, 26 chỗ** — trong đó 5 tệp liên-app dùng chung của mọi phiên | Pha 3 E5 có bảng từng tệp, sửa **tối thiểu**. Và **đo lại trước khi xoá** (`grep -rc`) vì phiên khác có thể vừa thêm tham chiếu |
| R-7 | Khách **nhân bản brief** để lấy thêm 2 lượt miễn phí | Ghi rõ ở §4.1. Sửa là **một dòng**, có test nói rõ đây là quyết định |

---

## 9. ⛔ Điều plan này CỐ Ý không làm

| Không làm | Vì |
|---|---|
| Kho asset/media dùng chung ở `platform_core` | Q-1 chọn đường A: kho trong app, mở qua ToolSpec |
| Bổ sung hình dạng tham chiếu thứ ba vào `server/api/uploads.py` | Đã hỏi; chủ dự án chọn đường D (khai cạnh app→app) |
| Đẩy storyboard sang Seedance Video | Q-12: storyboard chỉ để tham chiếu trong PROMPT AI |
| Hàng đợi nhiều bài ở `taovideo` | Q-13: một bài một lần, y bản gốc |
| Trang "kho công khai" + kiểm duyệt nội dung | Q-10: chia sẻ bằng mã/link ⇒ nghĩa vụ kiểm duyệt nhỏ nhất |
| Quét thư mục đĩa máy chủ (862 LOC của bản gốc) | SaaS: khách không có đĩa trên máy chủ. Thay bằng upload + ZIP |
| Khách nhập API key riêng | Nền tảng dùng `platform_core/api_pool.py` |
| Kế thừa style nhiều tầng | Chỉ **một** tầng cha–con; `parent_id` trỏ tới bản ghi **không có** `parent_id` |
| Di trú brief cũ trong `AppProject.payload` | Q-11: chưa có khách thật. `/classic` vẫn đọc payload cũ; có test khẳng định app **không vỡ** |

---

## 10. Sau khi chủ dự án chốt

Hai đường thi hành, chọn một:

| | Cách | Phù hợp khi |
|---|---|---|
| **1** | **Agent theo từng Task** (`superpowers:subagent-driven-development`) — một agent mới mỗi Task, điều phối soát giữa các Task | Muốn nhanh và có chốt kiểm giữa từng Task. ⚠️ Mỗi agent phải qua `chay_nang.py` cho lệnh nặng, và **một lượt nặng một lúc trên toàn máy** |
| **2** | **Thi hành trong phiên** (`superpowers:executing-plans`) — chạy theo lô, dừng ở mốc | Muốn điều phối giữ toàn bộ bối cảnh, ít lượt hơn |

⛔ Dù chọn cách nào: **không** chạy gate trong phiên, **không** deploy giữa plan mà không
hỏi, và **báo** khi gộp `main` chứ không xin duyệt (hợp đồng §6, §10).
