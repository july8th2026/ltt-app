# MA TRẬN REUSE / DELETE / BUILD

Luật *"reuse before build"*: một thành phần chỉ được `BUILD` khi **cả bốn** câu
sau đều FAIL.

1. WanGP đã làm chưa?
2. LTT generic đã làm chưa?
3. Gọi trực tiếp được không?
4. Bọc mỏng được không?

---

## A. XOÁ KHỎI KẾ HOẠCH — 9 lớp tôi đã định tạo

Danh sách lớp bị cấm tạo, kèm thứ thay thế:

| Lớp định tạo | Thay bằng | Bằng chứng |
|---|---|---|
| `InputAnalyzer` | `metadata.inputs` + `media_inputs` | `docs/API.md` §Model Metadata |
| `IntentResolver` | `list_model_defs(inputs=, main_output=)` + Deepy Prime | `shared/api.py:31`; `docs/DEEPY.md` |
| `CapabilityResolver` | `get_model_availability` · `list_model_availability` · `get_model_schema` | `shared/api.py:178,192,201` |
| `ModelRegistry` | `list_model_defs` / `get_model_def` (225 tệp `defaults/`) | `shared/api.py:31,70` |
| `VideoTemplateManager` | user settings file + `get_model_settings(model_type, setting_id)` | `shared/api.py:100`; `docs/DEEPY.md` |
| `VideoQueue` *(thực thi)* | hàng đợi nội bộ + `submit_manifest` | `shared/api.py:243` |
| `VideoAgent` | Deepy Zero/Prime | `docs/DEEPY.md`; `wangp-agent/SKILL.md` |
| `VideoPreprocessor` | `preprocessing/` | thư mục tại SHA ghim |
| `VideoPostprocessor` | `submit_media_postprocessing` · `submit_audio_remux` | `shared/api.py:231,235` |

**9/9 đều không chứng minh được gap ⇒ `DELETE FROM PLAN`.**

Thêm ba abstraction nữa bị xoá:
- **media-role schema 8 vai** → `media_inputs` + bảng vai `SKILL.md:55–68`
- **bộ dịch vai → tham số** → `apply_media_flag_defaults()` (`shared/api.py:74`)
- **`duration_s` → số khung** → `apply_video_length_duration()` (`shared/api.py:122`), nhận thẳng `"10s"`

---

## B. ĐƯỢC PHÉP BUILD — 5 thành phần, mỗi cái có chứng minh gap

### B1. `apps/lttvideo/` — GUI + route + job

```
NEW COMPONENT:            App LTT (manifest/routes/jobs/features)
WAN-GP EQUIVALENT:        Gradio trong wgp.py — 1.053 loi goi gr.* nam
                          TRONG chinh tep engine 14.000 dong; khong co
                          frontend/ web/ ui/ static/ templates/ client/
LTT GENERIC EQUIVALENT:   ltt.css, i18n, catalog/nav, server.templating —
                          co KHUNG, khong co trang video
EXACT GAP:                toan bo giao dien tieng Viet + hop dong app
WHY WRAPPER NOT ENOUGH:   khong co gi de boc — UI cua WanGP khong tach roi
                          khoi engine, va nhung no vao san pham co thu tien
                          roi vao giay phep §5.2(d)/(g)
MINIMUM CODE:             manifest.py · routes.py (<900 dong) · jobs.py ·
                          features.py · cost.py · template + JS toi thieu
```

### B2. `platform_core/wangp_client.py` — client gọi C-CLOUD

```
NEW COMPONENT:            WanGP client phia LTT
WAN-GP EQUIVALENT:        shared/api.py — nhung no chay TRONG tien trinh
                          WanGP tren C-CLOUD, khong goi qua mang duoc
LTT GENERIC EQUIVALENT:   platform_core/video_gen/cloud_api.py cua V3 —
                          client RunPod, KHONG phai client WanGP
EXACT GAP:                mot lop HTTP dat giua A-CONTROL va worker
WHY WRAPPER NOT ENOUGH:   day CHINH LA lop boc mong; khong co gi mong hon
MINIMUM CODE:             health · submit · progress · cancel · result ·
                          cleanup — anh xa 1:1 sang API da co
```

### B3. `apps/lttvideo/kha_nang.py` — allowlist năng lực

```
NEW COMPONENT:            Allowlist nang luc theo hang khach
WAN-GP EQUIVALENT:        capabilities/media_inputs tra loi "MODEL lam duoc
                          gi" — KHONG tra loi "KHACH NAY duoc dung gi"
LTT GENERIC EQUIVALENT:   surface/public/api_exposed cua manifest — muc APP,
                          khong phai muc nang luc
EXACT GAP:                chinh sach san pham, khong the suy tu engine
WHY WRAPPER NOT ENOUGH:   day la QUYET DINH KINH DOANH, khong phai du lieu
MINIMUM CODE:             mot bang hang so + mot ham kiem
```

⚠️ Đây **không phải** `CapabilityResolver`. Resolver hỏi *"làm được không"* —
WanGP trả lời. Allowlist hỏi *"được phép không"* — chỉ LTT trả lời được.

### B4. `apps/lttvideo/ho_so.py` — sổ đăng ký profile

```
NEW COMPONENT:            So dang ky profile
WAN-GP EQUIVALENT:        user settings file — DINH DANG da co, nhung khong
                          co khai niem "ban nao duoc duyet"
LTT GENERIC EQUIVALENT:   khong co
EXACT GAP:                NGUON GOC: tep nao duoc duyet, phien ban trong git,
                          neo vao SHA WanGP nao, ai doi va vi sao
WHY WRAPPER NOT ENOUGH:   day la quan tri cau hinh, khong phai doc tep
MINIMUM CODE:             thu muc ho_so/*.json (settings that cua WanGP) +
                          mot bang profile_id -> (tep, SHA WanGP)
```

🔴 **Phát hiện của lượt audit:** `profile_id` phải neo vào **cặp (tệp settings,
SHA WanGP)** — tham số chỉ có nghĩa với đúng phiên bản engine sinh ra chúng.

### B5. `apps/lttvideo/cost.py` — quy giây GPU thành credit

```
NEW COMPONENT:            Mo hinh gia
WAN-GP EQUIVALENT:        KHONG CO khai niem tien nao
LTT GENERIC EQUIVALENT:   platform_core.credit / billing — SO CAI, khong
                          phai cong thuc cua app nay
EXACT GAP:                giay GPU + gia may -> credit, giu cho truoc va
                          quyet toan sau
WHY WRAPPER NOT ENOUGH:   khong co gi de boc
MINIMUM CODE:             mot ham uoc tinh + mot ham quyet toan
```

---

## C. DÙNG LẠI NGUYÊN — không viết dòng nào

**Từ WanGP:** khám phá model · schema · sẵn sàng · tham số mặc định · chuẩn hoá
job · hàng đợi thực thi · tiến độ/preview · huỷ · gallery upload/download ·
tiền/hậu xử lý · đổi model · quản lý VRAM · MCP.

**Từ LTT generic:** `server.auth.session.require_login` · `server.auth.csrf` ·
`server.deps` · `server.templating` · `platform_core.job_runner` + `leases` ·
`platform_core.credit` + `billing` · `platform_core.storage` (R2) ·
`platform_core.image_input.validate_reference` ·
`platform_core.frontend_bundle` · `platform_core.i18n`.

⛔ Hợp đồng app cho phép **đúng bốn** module của `server` — không hơn
(`AGENTS.md` §8.2b). Chạm sâu hơn là **gate ĐỎ**.

**Từ nhánh V3 — lấy TỪNG TỆP, không merge cả nhánh (`P00-D-04`):**
`platform_core/video_gen/cloud_api.py` · `ngan_sach.py` ·
`tools/video_cloud.py` · `tools/video_theo_doi.py`.

---

## D. Đếm cuối

| | |
|---|---:|
| Thành phần **xoá khỏi kế hoạch** | **12** (9 lớp + 3 abstraction) |
| Thành phần **được phép build** | **5** |
| Subsystem **dùng lại nguyên** | **15** |
| Còn **cần chạy thật mới biết** | **2** (chất lượng suy luận Deepy; tổ hợp reference+control) |
