# GUI_RUNTIME_DIAGNOSIS — LTT Voice (đo 15/09/2026)

> Nhiệm vụ: GUI SUPER PROMPT — Wave 1 (runtime/queue root cause) + chẩn đoán
> lưu trữ cho 25 shared voice. Mọi kết luận đánh dấu
> `PROVEN / LIKELY / PARTIAL / BLOCKED / NOT TESTED`.
>
> Phương pháp đo: truy vấn **chỉ đọc** CSDL production (127.0.0.1, service
> account `ltt_app`), đọc `AppEnvironmentExtra` của dịch vụ nssm
> (`nssm get LTTStudio* AppEnvironmentExtra`), HEAD object R2 từng key.
> Không sửa gì. Không deploy.

## 1. P0-1 — Job bấm "Tạo" nằm "Xếp hàng" mãi mãi — **PROVEN**

### 1.1 Bằng chứng runtime (CSDL production, đọc 15/09)

Hai job **đang kẹt ở `queued`** tại thời điểm đo — cả hai đều **tạo trong
chính ngày 15/09** (vẫn tái hiện live, không phải dữ liệu cũ):

| job_id | created_at (+07) | status | attempts | worker_id | started_at | last_claimed_at | admitted_at | admission_resource |
|---|---|---|---|---|---|---|---|---|
| `1d4fe4b1-3219-4685-82b7-c2bbef9e1340` | 2026-09-15 14:21:23 | queued | 0 | *(rỗng)* | NULL | NULL | NULL | vieneu_gpu |
| `8c4b9945-4b95-43cc-9a78-55844c9673a9` | 2026-09-15 10:16:45 | queued | 0 | *(rỗng)* | NULL | NULL | NULL | vieneu_gpu |

Chuỗi sự kiện của `1d4fe4b1` (bảng `job_events`):

```
submitted     "Đã tiếp nhận yêu cầu."
credit_held   {'credit': 8}
— DỪNG. Không có event nào khác.
```

→ Credit **đã giữ** (8 credit treo trong sổ), job không bao giờ bị claim.

### 1.2 Root cause — PROVEN

Dịch vụ worker production (`LTTStudioWorker`) được cài với

```
LTT_WORKER_POOLS = "api:6, gpu:1"
```

(trong `AppEnvironmentExtra` của nssm — đo trực tiếp 15/09, **không có làn
`voice`**).

Trong khi `apps/ltt_voice/manifest.py` khai:

```python
requires = ("voice",)          # + admission_resource "vieneu_gpu"
```

Luật claim: `jobs.claim()` chỉ nhận job khi
`set(manifest.requires).issubset(capabilities worker)`. Không worker nào có
capability `voice` ⇒ **không worker nào đủ điều kiện, không có lỗi nào được
báo** — job nằm `queued` vĩnh viễn. `/health/ready` vẫn 200 (health không đo
làn worker).

Cái bẫy này **đã được ghi trong chính mã** — tức là bảo vệ đã tồn tại nhưng
đã bị vượt qua ở thời điểm deploy 14/09:

- `apps/ltt_voice/manifest.py:162-171` — chú thích cảnh báo + chỉ đường;
- `setup/4-nghiem-thu.ps1:68-78` — bước nghiệm thu đọc `app.env`, báo `Bad`
  khi pools đặt mà thiếu `voice`;
- `tools/do_sau_khoi_dong.py:246-261` — cảnh báo sau khởi động;
- `tests/test_501_ltt_voice_hong_hoc.py:185` — unit test ghim đúng trap.

### 1.3 Timeline khớp chính xác — PROVEN

| Thời điểm (+07) | Sự kiện | Bằng chứng |
|---|---|---|
| đến 13/09 21:01 | Job synthesize **chạy được** (59 job done trong 30 ngày; job muộn nhất `dadb2399…` xong 13/09 21:01, worker `DESKTOP-H9AGFUQ:24400`, ~11s/job) | bảng `jobs` |
| 14/09 | Bản cấu hình pools **không có làn voice** được nạp vào dịch vụ worker (deploy cấu hình) | `AppEnvironmentExtra` hiện tại; không có job voice done nào sau 13/09 21:01 |
| 15/09 10:16 + 14:21 | Hai job mới tạo → kẹt `queued`, attempts=0, không event sau `credit_held` | bảng `jobs` + `job_events` |

Đếm 30 ngày (bảng `jobs`, `app_slug='ltt_voice'`):

| job_type | done | error | queued | cancelled |
|---|---|---|---|---|
| synthesize | 59 | 15 (muộn nhất 04/09) | 2 (chính 2 job trên) | 1 |
| enroll | 29 (31/08 → 12/09 05:58) | — | 0 | 0 |

Ví dụ error thật (cho mục 5 — phân loại lỗi): job `16931066…` 04/09,
attempts=1: `LoiGiongNoi: Không tìm thấy giọng này trong tài khoản của bạn.`
→ đây là lỗi **voice not owned/unavailable**, không phải lỗi worker.

### 1.4 Toàn bộ chuỗi đã kiểm (theo §3 prompt)

```
POST /ltt-voice/tao   → job tạo được        ✔ PROVEN (job tồn tại, events có)
DB job status         → 'queued'            ✔ PROVEN
worker claim          → KHÔNG BAO GIỜ       ✔ PROVEN (attempts=0, last_claimed NULL)
capability matching   → SAI: thiếu làn      ✔ PROVEN (env + manifest)
GPU admission         → chưa tới lượt       — (admitted_at NULL vì chưa claim)
sidecar/model/artifact→ không chạy được     — (systemic: không có job nào đến đây)
poll/player           → GUI kẹt "xếp hàng"  ✔ (triệu chứng người dùng)
```

Phần `sidecar → model → artifact` **NOT TESTED ở production** (không job nào
đi đủ đường). Sẽ được kiểm bằng E2E thật trong Wave 9 (app worktree + worker
địa phương có làn `voice` — xem `GUI_MASTER_PLAN.md` §Wave 9).

### 1.5 Xử lý theo §28 (không deploy)

1. **Thay đổi production (chỉ chủ dự án, ĐÃ GHI NHẬN, chưa thực thi):**
   thêm làn `voice:1` vào `LTT_WORKER_POOLS` của `LTTStudioWorker`
   (ví dụ `api:6, gpu:1, voice:1`) rồi restart dịch vụ. Đây là thao tác cấu
   hình máy chủ — ngoài phạm vi mã nguồn, không tự rollout.
2. **Source/guard trong repo (Wave 10):**
   - `do_sau_khoi_dong.py` đã cảnh báo — bổ sung kiểm **theo từng app có
     `requires`**: liệt kê app bị "vô hình" (requires không khớp pools hiện
     đặt) thay vì chỉ cảnh báo chung cho voice.
   - Worker: khi một job `queued` vượt ngưỡng tuổi mà không có worker claim,
     ghi `job_events` mức warning (hiện trạng: không event nào — đây là lỗ
     quan sát, §20).
   - Test L1/L2 ghim: pools đặt + thiếu lane ⇒ claim bị từ chối **và** có tín
     hiệu phát hiện (mở rộng `test_501`).
3. **Credit bị giữ của 2 job kẹt** sẽ tự chạy khi làn được thêm — không xoá sổ.

## 2. P0-2 — 25 shared voice mất tệp lưu trữ — **PROVEN** (mất tệp) / **LIKELY** (cơ chế xoá)

### 2.1 Đo trực tiếp R2 (15/09, HEAD từng key)

Toàn bộ 29 hồ sơ giọng có 58 key (`voice_repr.storage_key` +
`voice_ref.storage_key` từng profile). Kết quả `head_object` trên bucket thật:

```
TONG: co=2  khong=56  tong=58   (~0.1 MB còn lại)
```

Chỉ MỘT hồ sơ còn đủ hai tệp:

```
voice/a5d15080-…/vc_d60a3c21…/
  repr-a55339a6….npz   0.001 MB
  source.wav                                  0.102 MB
```

Đó là hồ sơ ghi danh **12/09** (`RC1 ghi danh EN 1789167530688`) — trẻ nhất,
chưa đủ tuổi để bị xoá. **28/29 hồ sơ còn lại: cả hai key đều KHONG tồn
tại.** → 25 shared voice **không voice nào usable** ở production hiện tại
(ngay cả hồ sơ "intact" là hồ sơ owned của tài khoản thử, không thuộc 25).

### 2.2 Cơ chế xoá — LIKELY (hành vi PROVEN, cấu hình chưa đọc được)

Từ `docs/LTT_VOICE/HOP_NHAT/MAT_TEP_KHO_R2.md` (điều tra 12/09) + phép đo
này:

- **PROVEN (hành vi):** bucket `fb-video-storage` không giữ object nào già hơn
  ~7 ngày (12/09: 46 key, cũ nhất 05/09; tiền tố `thumbnail/` mất 14 key → 0
  trong 4 giờ, không app nào chạm); 0 đường xoá trong mã ứng dụng giải thích
  được (đã loại trừ từng đường: `expire_content`, `RETENTION_DAYS` (sinh ra
  đã là 30), `upload_sessions` (bảng rỗng), đường xoá của `ltt_voice`
  (chỉ chạy với hồ sơ revoked/loi/disabled — cả 29 đều `active`)).
- **LIKELY (cơ chế):** bucket có **lifecycle rule ~7 ngày** ở dashboard
  Cloudflare — khoá S3 của app bị `AccessDenied` ở
  `GetBucketLifecycleConfiguration`, không đọc trực tiếp được. Vật mốc
  `chan_doan/moc-vong-doi-*.txt` đã đặt để đo ngưỡng chính xác khi nó biến
  mất.
- ⚠️ Mã khai retention **30 ngày** (`RETENTION_DAYS`) nhưng kho làm **~7
  ngày** — hai tầng nói hai điều khác nhau; **tầng thật thắng**. Hậu quả mở
  rộng ra **mọi** app trong bucket (ảnh, video, thumbnail), không chỉ voice.

### 2.3 Vì sao 25 shared voice lại nằm trên R2 — và R2 có bắt buộc không

**Đáp: không bắt buộc. Việc chúng nằm trên R2 là hệ quả của biến môi trường
production, không phải quyết định kiến trúc.** PROVEN:

1. `platform_core/storage.py:407-422` — `get_storage()` trả `R2Storage` khi
   `LTT_STORAGE=r2` + đủ `LTT_R2_*`; không thì `LocalStorage`
   (`C:\LTTPlatform\data\files`). Production đặt `LTT_STORAGE=r2` ⇒ **mọi**
   ghi/đọc file của **mọi** app đi R2.
2. 25 shared voice được tạo bằng đúng luồng **ghi danh (enroll) của user**:
   job enroll lưu `source.wav` + `repr.npz` dưới prefix **của owner**
   `voice/{owner_uuid}/{vc_…}/` (`tham_chieu.py::luu_bieu_dien`,
   `jobs.py::_ghi_danh`). Không có khái niệm "tài sản hệ thống" trong mã —
   chúng được lưu như nội dung người dùng, ở đúng prefix nội dung người dùng.
3. Đọc lúc chạy cũng đi một seam duy nhất:
   `nap_ref_b64()` → `get_storage().open(bieu_dien.storage_key)`
   (`tham_chieu.py:333-340`) cho cả synthesize lẫn preview.

**Thiết kế sai thực sự:** tài sản **hệ thống** (25 giọng dùng chung cho mọi
khách — tính chất như mã nguồn, bắt buộc để app hoạt động, kích thước nhỏ)
đặt trong **prefix nội dung người dùng**, dưới **lifecycle xoá theo tuổi đã
chứng minh là phá huỷ**, không có bản sao bền, không có version.

### 2.4 Phương án — quyết định: **C (repo là nguồn chân lý + seed + tự chữa)**

| | Phương án | Kết luận |
|---|---|---|
| A | Code đọc thẳng file trong repo (`open()`), bỏ qua `get_storage()` | ❌ Phá seam storage duy nhất; route preview/URL giả định storage key; `local_path()` trả None trên R2; sinh ra 2 đường đọc ⇒ lệch |
| B | Giữ trên R2, "bảo vệ" prefix (dashboard/policy) | ❌ (đứng riêng) Phụ thuộc trạng thái bên ngoài đã chứng minh phá huỷ; không version; không tự hồi phục; chính prefix `voice/{owner}/` hiện tại KHÔNG hề được bảo vệ (56/58 đã mất) |
| **C** | **Repo = nguồn chân lý bền; storage = bộ nhớ chạy; seed + tự chữa + guard** | ✅ **CHỌN** |

Chi tiết phương án C:

1. **Tệp hệ thống trong repo:** `apps/ltt_voice/data/voices/`
   - `manifest.json` — 25 mục: `public_id`, tên, ngôn ngữ, giới, license,
     tên tệp, `sha256` từng tệp;
   - `voices/<public_id>/source.wav` + `repr.npz`.
   - Kích thước đo được (hồ sơ intact): source ~0.1 MB + npz ~0.001 MB/giọng
     ⇒ **~3 MB cho cả 25** — không cần git LFS.
2. **Seed khi khởi động/deploy:** với mỗi mục manifest,
   `get_storage().put()` vào prefix hệ thống **`voice/he_thong/<public_id>/…`**
   — **idempotent** (bỏ qua nếu key tồn tại + sha khớp), **backend-agnostic**
   (đúng với cả R2 lẫn LocalStorage).
3. **Tự chữa (self-heal) khi khởi động:** key hệ thống nào thiếu → seed lại
   từ cây repo + ghi log diagnostic. Hệ quả: **ngay cả khi luật ~7 ngày vẫn
   còn**, bucket chỉ còn là cache — bản bền nằm trong repo, và mỗi lần khởi
   động web service tự kéo lại. Điều này giải quyết an toàn cảnh báo
   "đừng dựng lại vào kho vẫn đang xoá" của `MAT_TEP_KHO_R2.md` §7: bản dựng
   lại không phụ thuộc vào kho.
4. **DB migration:** 25 hồ sơ `voice_profile` (và `voice_repr`/`voice_ref`)
   trỏ lại key sang prefix `voice/he_thong/<public_id>/…`.
5. **Guard cơ học:**
   - L1: mọi profile `dung_chung=True` phải có repr key bắt đầu bằng prefix
     hệ thống **và** tồn tại trong storage; manifest bao phủ đủ 25; sha256 khớp;
   - Khởi động: log liệt kê giọng hệ thống thiếu (diagnostic, không crash).
6. **Sửa luật lifecycle bucket — riêng, P0, chỉ chủ dự án:** mở dashboard
   Cloudflare R2 → `fb-video-storage` → Object lifecycle rules; đọc luật thật
   (vật mốc §2.2 cho ngưỡng chính xác); hoặc nới luật, hoặc hạ hằng số trong
   mã — vì **toàn bộ nội dung user** trong bucket bị ảnh hưởng, không chỉ
   voice. Việc này **không chờ** phương án C (C sống được cả khi luật chưa
   sửa).

### 2.5 Điều chặn (BLOCKED) — cần người dùng

**25 clip nguồn gốc đã MẤT khỏi mọi nơi có thể đo được:** R2 (56/58 key
mất), đĩa máy chủ (0 tệp `source.wav`/`repr*.npz` — đã đo), repo (0 `.wav`/
`.npz` — Glob toàn kho). Mã không thể "tìm lại" được clip không còn tồn tại.

→ **Cần chủ dự án cung cấp 25 clip nguồn** (từ nơi lưu bản gốc/bản ghi âm
gốc) hoặc vị trí của chúng. Có clip thì seed + tự chữa + migration chạy được;
trước đó 25 giọng chỉ hiển thị được ở Library **kèm lý do chính xác từng
giọng** ("tệp gốc đã mất — chờ cung cấp lại"), đúng yêu cầu §6/V03.
(npz có thể tái tạo từ clip qua sidecar enroll — đã chứng minh khả thi: job
enroll 12/09 chạy được.)

## 3. Bảng audit 25 shared + 4 owned (yêu cầu §6) — đo 15/09

Nguồn: bảng `voice_profile`/`voice_repr`/`voice_ref` + HEAD R2 từng key
(phiên trên). **Tất cả 29 hồ sơ:** owner `a5d15080-21ba-4187-abe1-4ed97feed589`
(tài khoản thử `thu.giongnoi@lttstudios.local`), `license_status=cho_soat`,
`trang_thai=active`, `voice_repr.trang_thai=dang_dung`, cột `gioi` **rỗng
toàn bộ** (metadata thiếu — ảnh hưởng bộ lọc giới, D004).

Ký hiệu cột: Shared=T/F; Usable=Đ/K; GUI visible ghi theo màn (kết quả xác
minh chính thức ở Wave 3/9 — đây là suy ra từ dữ liệu + template, đánh dấu
tương ứng).

### 3.1 Kho chung — 25 shared (17 EN + 8 VI)

| Voice (public_id) | Shared | License | Status | Ngôn ngữ | Repr (R2) | Preview | GUI visible | Usable |
|---|---|---|---|---|---|---|---|---|
| Aaron — nam, phiêu lưu (`vc_aec13571…`) | T | cho_soat | active | en | **KHÔNG** (mất key) | KHÔNG | Library `/giong` có (nhóm sai — Wave 3 xác minh); Studio picker có; màn chỉ preset **KHÔNG** | K |
| Adrian — nam, thuyết minh (`vc_b24b1aee…`) | T | cho_soat | active | en | KHÔNG | KHÔNG | như trên | K |
| Clara — nữ, thuyết minh (`vc_a55b2ad1…`) | T | cho_soat | active | en | KHÔNG | KHÔNG | như trên | K |
| Douglas — nam, thuyết minh (`vc_1b65a9e6…`) | T | cho_soat | active | en | KHÔNG | KHÔNG | như trên | K |
| Ethan — nam, giảng bài (`vc_77d04fc5…`) | T | cho_soat | active | en | KHÔNG | KHÔNG | như trên | K |
| Ivy — nữ, thuyết minh (`vc_62bedaf9…`) | T | cho_soat | active | en | KHÔNG | KHÔNG | như trên | K |
| Julian — nam, thuyết minh (`vc_27af9b75…`) | T | cho_soat | active | en | KHÔNG | KHÔNG | như trên | K |
| Lulu — nữ, hoạt hình (`vc_67071577…`) | T | cho_soat | active | en | KHÔNG | KHÔNG | như trên | K |
| Marcus — nam, thuyết minh (`vc_f0a3c379…`) | T | cho_soat | active | en | KHÔNG | KHÔNG | như trên | K |
| Miles — nam, mạng xã hội (`vc_633fcf57…`) | T | cho_soat | active | en | KHÔNG | KHÔNG | như trên | K |
| Nathan — nam, hội thoại (`vc_ad277664…`) | T | cho_soat | active | en | KHÔNG | KHÔNG | như trên | K |
| Nova — nữ, hoạt hình (`vc_704b9d21…`) | T | cho_soat | active | en | KHÔNG | KHÔNG | như trên | K |
| Owen — nam, kể chuyện (`vc_526cb3ff…`) | T | cho_soat | active | en | KHÔNG | KHÔNG | như trên | K |
| Peter — nam, hội thoại (`vc_d2a0e1da…`) | T | cho_soat | active | en | KHÔNG | KHÔNG | như trên | K |
| Robin — giải trí, biến hoá giọng (`vc_b6679551…`) | T | cho_soat | active | en | KHÔNG | KHÔNG | như trên | K |
| Simon — nam, trang nghiêm (`vc_8a9ba87e…`) | T | cho_soat | active | en | KHÔNG | KHÔNG | như trên | K |
| Victor — nam, kể chuyện (`vc_c06352ee…`) | T | cho_soat | active | en | KHÔNG | KHÔNG | như trên | K |
| An Nhiên — nữ, kể chuyện thiền (`vc_fceeabc6…`) | T | cho_soat | active | vi | KHÔNG | KHÔNG | như trên | K |
| Bảo Lâm — nam, kể chuyện (`vc_24d7f103…`) | T | cho_soat | active | vi | KHÔNG | KHÔNG | như trên | K |
| Diễm Chi — nữ, kể chuyện ngôn tình (`vc_ea505b37…`) | T | cho_soat | active | vi | KHÔNG | KHÔNG | như trên | K |
| Duy Khang — nam, tự nhiên (`vc_8dc2abfc…`) | T | cho_soat | active | vi | KHÔNG | KHÔNG | như trên | K |
| Gia Huy — nam, bản tin kinh tế (`vc_133e1577…`) | T | cho_soat | active | vi | KHÔNG | KHÔNG | như trên | K |
| Hạ Vy — nữ, tự nhiên (`vc_e4e173ae…`) | T | cho_soat | active | vi | KHÔNG | KHÔNG | như trên | K |
| Thanh Nhã — nữ, tự nhiên (`vc_54b096aa…`) | T | cho_soat | active | vi | KHÔNG | KHÔNG | như trên | K |
| Trọng Nghĩa — nam, kể chuyện lịch sử (`vc_be77e368…`) | T | cho_soat | active | vi | KHÔNG | KHÔNG | như trên | K |

**Lý do chính xác (V03):** 25/25 KHÔNG usable vì `voice_repr.storage_key` +
`voice_ref.storage_key` **không còn tồn tại trên R2** (xoá theo tuổi ~7 ngày
của bucket — §2.2); DB vẫn giữ hồ sơ `active` + `dang_dung` nên Library
**liệt kê được** nhưng **không preview được, không synthesize được** cho tới
khi clip được cung cấp lại + seed (phương án C, §2.4).

### 3.2 Giọng của tôi — 4 owned (cùng owner tài khoản thử)

| Voice (public_id) | Shared | License | Status | Ngôn ngữ | Repr (R2) | Preview | GUI visible | Usable |
|---|---|---|---|---|---|---|---|---|
| Clip 30s kiem thang cham (`vc_f5d83434…`) | F | cho_soat | active | vi | **KHÔNG** | KHÔNG | `/giong` (nhóm đúng: của tôi) | K |
| Giọng mẫu nam trầm (`vc_8b9d3307…`) | F | cho_soat | active | vi | **KHÔNG** | KHÔNG | `/giong` | K |
| HF_HOME (`vc_3312d5e8…`) | F | cho_soat | active | vi | **KHÔNG** | KHÔNG | `/giong` — **tên là biến môi trường HF_HOME: lỗi ghi tên ở luồng enroll 31/08** | K |
| RC1 ghi danh EN 1789167530688 (`vc_d60a3c21…`) | F | cho_soat | active | en (nguồn `khai_bao`) | **CÒN** (0.001 MB) | **CÒN** (0.102 MB) | `/giong` | **Đ** (duy nhất) |

### 3.3 Bất thường dữ liệu (chạy sang GUI_AUDIT_MATRIX)

1. **Dedupe lỗi:** 2 hồ sơ (`vc_f5d83434` + `vc_3312d5e8`) trỏ cùng key
   `repr-f42de3bf….npz` — hai hồ sơ, một tệp biểu diễn.
2. **Tên `HF_HOME`** — biến môi trường bị ghi thành tên hồ sơ.
3. **Cột `gioi` rỗng 29/29** — bộ lọc "giới" không có dữ liệu thật để lọc
   (liên quan D004: bộ lọc phải khai đúng điều này).
4. **25 giọng `dung_chung=True` mà `owner` là tài khoản thử** — "shared" đang
   được biểu diễn bằng cờ + prefix owner, không phải prefix hệ thống (chính
   là lỗi thiết kế §2.3; phương án C sửa bằng migration).
5. `ngon_ngu_nguon`: 28/29 `mac_dinh_cu`, 1/29 `khai_bao` — chỉ 1 hồ sơ khai
   ngôn ngữ nguồn thật.

## 4. Quan sát hàng đợi (§20) — hiện trạng

Hỏi §20 với dữ liệu thật: job_id ✔ · created ✔ · status ✔ · age (tính được
từ `created_at`) ✔ · attempt ✔ · worker claimed? ✔ (`worker_id`,
`last_claimed_at`) · capability requirement ✔ (`manifest.requires`) ·
**matching worker exists? — KHÔNG trực tiếp** (phải đọc env của dịch vụ —
`tools/do_sau_khoi_dong.py:246-261` làm việc này) · admission resource ✔
(`admission_resource`) · lease state ✔ (bảng lease) · latest event ✔
(`job_events`).

**Lỗ:** khi không có matching worker, **không có event nào** được ghi —
support chỉ phát hiện được bằng cách đọc env dịch vụ đối chiếu. Sửa trong
Wave 10 (worker ghi event warning khi job quá tuổi mà chưa được claim — mục
1.5/2).

GUI user chỉ nhận câu an toàn theo tuổi hàng đợi (D005) — không lộ thông tin
server.
