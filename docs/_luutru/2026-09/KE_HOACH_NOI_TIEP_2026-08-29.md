> LƯU TRỮ 2026-09-19 — không còn đúng hệ thống hiện tại; thay bằng: `docs/KE_HOACH_TRIEN_KHAI.md`. Chỉ đọc để hiểu lịch sử.

# Kế hoạch nối tiếp — 2026-08-29

> **Đây là danh sách việc đang hiệu lực sau khi Claude tiếp quản từ Codex.**
> Nó **không** thay `docs/KE_HOACH_TRIEN_KHAI.md` (kế hoạch tổng, còn nguyên) và
> **không** cao hơn `docs/QUYET_DINH_NEN_TANG.md`. Nó trả lời đúng một câu hỏi:
> *hạng mục nào còn lại, làm theo thứ tự nào, và cái gì chặn cái gì.*
>
> Hồ sơ Codex đã đóng: `.codex/README.md` là lời nhắn dừng, nội dung dời sang
> `docs/_luutru/codex_2026-08-27/`.

---

## 1. Điểm xuất phát — đã kiểm, không phải giả định

Mọi dòng dưới đây kiểm ngày 2026-08-29, ghi kèm cách kiểm.

| Sự thật | Kiểm bằng |
|---|---|
| `ho_so_he_thong.txt` khớp nguồn | `python tools/build_system_profile.py --check` → **PASS** |
| Máy này **LÀ máy chủ** — `C:\LTTPlatform` tồn tại | `Test-Path C:\LTTPlatform` |
| `secrets/app.env` **không đọc được** bằng quyền thường (ACL H7 đang làm đúng việc) | `grep` → *Permission denied* |
| Production đang phục vụ: catalog ẩn danh trả **HTTP 200**, **10 app**, **6** nhãn *Đang phát triển* | `GET https://app.lttstudios.com/` |
| Nhánh `admin-mvp-v3` đi trước `origin/master` **59 commit**, **chưa push** | `git branch -vv` |
| Có **một phiên khác đang sửa cùng cây** (`lttstudiosapp-7b`) | `ListAgents` + mtime `server/admin.py` 09:30, `tests/test_324_admin_job_gj3.py` 09:32 |

### Kế hoạch Nexus + Qwen của Codex đã ĐÓNG, không dở dang

Đây là điều dễ hiểu nhầm nhất khi tiếp quản, nên nói thẳng: bản
`PLAN_TRIEN_KHAI_NEXUS_QWEN.md` **không còn việc kỹ thuật nào treo**.

| Pha | Trạng thái |
|---|---|
| Q0–Q3 (CPU/DB/mock) | ✅ khóa 2026-08-28 |
| Q4 (cửa sổ GPU, ladder cap) | ✅ chốt cap **65K** (Q116), sau khi 81K không ổn định (Q115) — ⚠️ con số **đã thay** bởi Q120 (03/09): trần dẫn xuất từ `ngan_sach.py`, công bố 88.555 |
| Q6 (canary public + telemetry) | ✅ nghiệm thu 2026-08-29 — 7 arm, queue-age p50 `1,062s` / p95 `1,861s`, 450 mẫu GPU/15 phút, over-cap hoàn credit đúng |
| **Q5** (mở `parallel>1`) | ⏸️ **hoãn có chủ ý** — cần quyết định chủ sản phẩm |
| **P2** (sống qua reboot máy B) | ⏸️ **hoãn có chủ ý** — cần cửa sổ bảo trì được duyệt |
| **P7** (mở public rộng) | ⏸️ chưa mở; giữ `parallel=1`, cap ~~`65000`~~ → theo Q120 (`ngan_sach.CONG_BO_CHO_CLIENT`) |

⇒ Việc còn lại của kho **không nằm** trong plan Codex. Nó nằm ở H41, H35.10 và
các khoản nợ cũ liệt kê ở §4.

---

## 2. Ba ranh giới không đổi

Giữ nguyên từ `AGENTS.md` và bộ nhớ phiên, chép lại đây để khỏi phải tra:

1. **Deploy** — hỏi trước khi bấm. Deploy ở kho này **xoá và thay TOÀN BỘ**
   `app\`, nên chạy `python tools/so_deploy.py` trước mỗi lượt: nếu độ lệch chứa
   việc của phiên khác thì ta vừa phát hành hộ họ.
2. **Bút toán tiền** — mọi thứ chạm `platform_core/credit.py` làm riêng một
   phiên, gate đầy đủ trước và sau, đường lùi viết trước khi sửa.
3. **UAC** — lệnh nâng quyền do chủ sản phẩm bấm; Claude chuẩn bị sẵn tất cả.

Thêm một ranh giới **của riêng phiên này**, vì có phiên khác đang chạy:

4. **Khu admin thuộc phiên `lttstudiosapp-7b`** — `server/admin.py`,
   `server/admin_api.py`, `server/routes/admin/`, `platform_core/admin_console.py`,
   `tests/test_31[7-9]*`, `tests/test_32*`. Không đụng cho tới khi phiên đó xong.
   Hệ quả trực tiếp: **Mục G** (§4-D) bị chặn bởi ranh giới này, không phải bởi
   kỹ thuật.

Quy tắc chạy test: **`docs/00_LTT_OPERATING_CONTRACT.md` §4.**

*(Trước 2026-09-08 chỗ này chép lại khối lệnh của `CLAUDE.md`. Bản chép đó đã
trôi — nó ghi "~5 phút" cho gate đầy đủ, trong khi đo trên 43 lượt thật là
**11,4 phút**. Một cadence chép tay không có cách nào tự biết nó đã cũ.)*

⛔ Một lượt gate chạy trên cây đang bị phiên khác sửa **không phải bằng chứng** —
gate tự nói ra điều đó
(`CAY DA DOI TRONG LUC CHAY`). Cần một cửa sổ cây đứng yên trước khi báo xong.

---

## 3. Đường phụ thuộc — đọc cái này trước bảng việc

Có **một** nút thắt chi phối phần lớn việc kỹ thuật còn lại, và nó không hiện ra
nếu chỉ đọc danh sách phẳng:

```text
H35.10a  đo thời lượng phía máy chủ lúc báo giá
   |     (params["duration_s"] = số đo thật, TRƯỚC khi tính giá,
   |      ở cả POST /quotes và POST /jobs)
   |
   +---> H41.5   mở bề mặt công khai của `upscalevideo`
   |             (cạnh cross-product duy nhất của kho)
   |
   +---> H35.10  mở `video.upscale` + `video.subtitle` trên /api/v1
                 (`video.short_clips` vẫn đóng — chờ H35.10c)
```

**Vì sao nó là một nút thắt chứ không phải một việc trong danh sách.** Giá của
`video.upscale` phụ thuộc `duration_s` **do người gọi khai**, và worker *nâng
giữ chỗ* khi đo được thời lượng thật (`_dam_bao_giu_cho`). Với giao diện thì ổn —
có người chọn file họ nhìn thấy. Với **máy gọi máy** thì nó phá lời hứa của một
báo giá đã ký. Đây chính là Q84, sự cố Seedance *giữ 29 thu 78*. Chẩn đoán đã
nằm sẵn trong `apps/upscalevideo/manifest.py:94-101` từ lâu — cái thiếu là người
làm, không phải người phát hiện.

Công cụ để làm **đã có sẵn, không phải viết mới**:
- `platform_core.media.duration_seconds` (`platform_core/media.py:126`)
- `storage.try_url_for()` (`platform_core/storage.py:129`) — R2 thì ffprobe đọc
  thẳng presigned URL, **không tải cả 2 GB về**; local thì `storage.open()`
- file đã ở `staging/` từ lúc upload (Q85) và đã qua kiểm magic-byte
- `create_job` đã có sẵn phép so `price_changed`, nên hai route tự khớp nhau

⇒ **H35.10a là hạng mục nên làm trước tiên trong nhóm kỹ thuật.** Rủi ro thấp
(không chạm sổ credit), và nó mở khoá hai việc khác.

⚠️ Nhưng đừng nhầm H35.10a với H35.10b. H35.10a làm quote **đúng**; nó **không**
làm quote *không thể sai* — `_dam_bao_giu_cho` vẫn còn đó và vẫn nâng nếu worker
tính ra số khác. Dựa vào *"hai số này chắc bằng nhau"* **chính là** kiểu lập luận
đã đẻ ra Q84. H35.10b (trần cứng ở tầng credit) mới biến Q84 thành bảo đảm cấu
trúc — và nó chạm `credit.py`, tức ranh giới 2.

---

## 4. Bản đồ hạng mục còn lại

### A. Chờ chủ sản phẩm quyết — không phải việc kỹ thuật

Bốn quyết định. Mỗi mục ghi **đánh đổi thật** để quyết được ngay, không cần
điều tra thêm.

| ID | Quyết định | Đánh đổi |
|---|---|---|
| **H41.7** | 6/10 app khách ẩn danh thấy mang nhãn *Đang phát triển*. Giữ, hay ẩn bớt? | Bề mặt hôm nay là **mặc định manifest cộng lại**, không do ai chọn. Giữ = khách thấy một cửa hàng nửa hoàn thiện. Ẩn = catalog gọn nhưng mất đường vào của app đang có người dùng thật. **Số đo hôm nay:** agent · autosubvideo · chataistudio · taoanh · taoclipngan · vps là 6 mục `development`; nexus · prompt_ai_ommi · taovideo · upscalevideo là 4 mục `released`. |
| **H41.8** | Đổi mặc định `AppManifest.public` → `False`? | Đây là **gốc** của H41.7: viết một app mới mà không khai gì thì nó **tự lên catalog công khai**. Đổi = an toàn mặc định, nhưng phải rà lại 14 manifest và sẽ có app biến mất nếu quên khai. Không đổi = lỗi này còn tái diễn ở app thứ 15. |
| **H41.3** | `hold_expires_at` + tự hoàn giữ chỗ treo | Hôm nay INV-5 chỉ được **quan sát** (máy dò `giu_cho_treo` kêu chuông `HOLD_STRANDED`), chưa được **bảo đảm** — hệ thống báo chứ không tự hoàn. Làm = INV-5 thành bảo đảm cấu trúc; nhưng **đụng schema và đường tiền** cùng lúc (ranh giới 2). Không làm = mỗi khoản treo cần một người xử tay. |
| **Q5** | Mở `parallel>1` trên RTX 3090? | `parallel=1` đã có p50/p95 đo thật và không OOM. Mở = throughput tổng có thể tăng; nhưng 3090 đang **ba hộ dùng chung** (video `E:\LTT AI`, LLM `H:\LTT_LLM`, ta) và p95 có thể xấu đi mà chỉ thấy sau canary. Q5 hiện **DEFER** theo Q112/Q116. |
| **Mục J** | `overview()["jobs"]` đếm job **toàn nền tảng** trong bảng điều khiển API | Lô C5–C8 xử lý bằng cách **nói ra** (nhãn "toàn nền tảng" + dẫn sang đúng phạm vi) — trung thực nhưng vẫn lạ trên trang tên *"API — Tổng quan"*. Sửa đúng là thêm `params._api.tool IS NOT NULL`; nhưng nó **đổi ý nghĩa một con số chủ sản phẩm có thể đang theo dõi**, nên là quyết định chứ không phải sửa lỗi. |

### B. Làm được ngay — không cần quyết định gì thêm

| ID | Việc | Rủi ro | Chặn bởi |
|---|---|---|---|
| **H35.10a** | Đo thời lượng phía máy chủ lúc báo giá | **Thấp** — không chạm sổ credit | — |
| **H41.5** | Khai bề mặt công khai `upscalevideo` | Thấp sau khi có H35.10a | H35.10a |
| **H35.10** | Mở `video.upscale` + `video.subtitle` trên `/api/v1` | Trung bình — đổi tool đang mở ⇒ phải cập nhật `APP_API_COVERAGE_FINAL.md` (`test_212` đọc bảng đó như dữ liệu, so hai chiều) | H35.10a |
| **Vệ sinh** | 5 việc ở §6 | Thấp | phần lớn: cây đứng yên |

### C. Làm được nhưng nên đợi — ranh giới hoặc cửa sổ

| ID | Việc | Chặn bởi |
|---|---|---|
| **Mục G** | Gỡ cầu tạm `server/admin.py:_KHOA_CU` (dịch khoá `active` cũ sang khoá mới) | **Ranh giới 4** — phiên `lttstudiosapp-7b` đang giữ file đó |
| **Mục A** | Chuyển ~1.880 dòng f-string HTML của 4 miền API sang Jinja | Ranh giới 4 + **đã tự hạ ưu tiên**: giá trị vận hành lấy được rồi mà không cần viết lại thân (xem `24_DEFERRED_POST_MVP.md` §A) |
| **H35.10b** | Trần cứng cho việc nâng giữ chỗ của job đến từ API | **Ranh giới 2** — chạm `credit.py`, làm riêng một phiên |
| **H35.10c** | Trần đồng thời GPU cho `video.short_clips` | Chưa chốt được trần; cần một cửa sổ GPU |
| **P2** | Máy B sống qua reboot | Cửa sổ bảo trì được duyệt |
| **test_221** | Chạy trên R2 thật | Cần **một bucket vứt đi** — bucket hiện tại dùng chung với BOT GEMINI, `CLAUDE.md` cấm ghi vào đó. Quyết định hạ tầng, không phải code. |
| **G9b** | Diễn tập dựng lại cổng vào VPS | Hành động không đảo được trên một máy đang trả tiền. **Không cần mua thêm VPS** — Reserved IP sống sót khi instance chết. |
| **Xoay khoá provider** | 6 khoá / 5 nhà | Chủ sản phẩm — phải lấy credential mới từ từng nhà, xoay sai thì job của khách chết |

### D. Nợ dài hạn, không thuộc đợt này

`H13` (R4–R10) · `H15.S15` · `H19.10` · `H21.8` · `H31.3`–`H31.6` (Quality Lab) ·
`H33.R1b`–`H33.R6` (release hardening) · `H37 G11/G12` · `B/D` của
`24_DEFERRED_POST_MVP.md` (omnibox, nút thu gọn thanh bên) · bản sao secrets còn
**cùng ổ** với bản dữ liệu (off-site là việc giai đoạn thương mại).

---

## 5. Thứ tự triển khai đề xuất

Bốn đợt. Mỗi đợt là **một lát cắt kết thúc được** — chạy full gate, ghi nhật ký,
rồi mới sang đợt sau. Không gộp hai đợt vào một lượt gate.

### Đợt 0 — vệ sinh và làm sạch mốc *(30–60 phút, không rủi ro)*

Làm trước để mọi phép đo sau đó có mốc sạch. Chi tiết ở §6.

**Nghiệm thu:** `git status` sạch phần tracked · `gate.py` **PASS** trên cây
đứng yên · nhật ký ghi số thật.

### ✅ Đợt 1 — H35.10a: đo thời lượng phía máy chủ — **XONG 2026-08-29**

`python tools/gate.py` → **PASS 23/23** trên cây đứng yên. `test_325` 20 phép
kiểm, bánh cóc đã kiểm **có răng**. Chi tiết ở mục `2026-08-29 — H35.10a` của
`NHAT_KY.md`. ⇒ **Đợt 2 hết chặn.**

⚠️ Đọc kỹ giới hạn trước khi tưởng Q84 đã đóng: H35.10a làm quote **đúng**, chưa
làm nó **không thể sai** — `_dam_bao_giu_cho` vẫn nâng giữ chỗ. Đó là H35.10b.

<details><summary>Kế hoạch gốc của Đợt 1 (giữ để truy vết)</summary>

**Làm gì.** Ở cả `POST /quotes` và `POST /jobs` (`server/api/jobs.py:216` và
`:281`), đặt `params["duration_s"]` bằng số đo thật **trước** khi gọi
`price()` → `credit_for()` → `_cost()`.

**Đụng file:** `server/api/jobs.py` (+ test mới). **Không** chạm
`platform_core/credit.py`. **Không** viết lại ffprobe — dùng
`platform_core.media.duration_seconds`.

**Nghiệm thu (viết test TRƯỚC khi sửa):**
1. `/quotes` và `/jobs` cho **cùng một** `duration_s` với cùng asset;
2. `duration_s` khách khai **sai** (thiếu, thừa, âm, chữ) → giá vẫn theo số đo;
3. Storage là R2 → dùng `try_url_for()`, **không** tải cả file về
   *(kiểm bằng cách đếm lời gọi, không bằng cách đọc mã)*;
4. Asset không đo được thời lượng → lỗi rõ ràng, **không** rơi về số khách khai;
5. `price_changed` của `create_job` vẫn bắt được lệch.

**Đường lùi:** revert đúng một commit; không migration, không chạm sổ tiền.

</details>

### Đợt 2 — H41.5 + H35.10 *(Đo lại 07/09: **H35.10 ĐÃ XONG**)*

⛔ **H35.10 không còn là việc cần làm.** Đo trên production 07/09:

```
LTT_PUBLIC_API_TOOLS = text.chat,image.ltt,video.subtitle,video.upscale,speech.ltt
```

`video.upscale` và `video.subtitle` **đã mở từ 29/08** — cùng ngày tài liệu này
được viết, nên nó ghi là còn treo. `APP_API_COVERAGE_FINAL.md` dòng 70 và 72 đã
ghi **EXPOSE_V1 — MỞ 29/08** cho cả hai.

⭐ Luật của kho: *khi kế hoạch và nhật ký mâu thuẫn, **nhật ký đúng***. Ai
   đọc hàng này mà đi "mở" hai tool ấy là đang đụng vào một bề mặt **đang thu
   tiền thật**.

### H41.5 — hình dạng thật, đo 07/09

Cạnh `apps/taovideo/routes.py:549,578` **vẫn còn**, và nó không phải cẩu thả:
docstring của `submit_upscale_job` ghi rõ *"dùng bởi route /queue **VÀ** bởi
taovideo — **KHÔNG nhân đôi code engine**"*.

⚠️ Gỡ nó **không phải xóa hai dòng import.** Nền tảng có đường chung
   (`public_api/invocation.py`: `validate_public_input` → `build_job_params` →
   `apply_server_measurements` → `price` → `submit`), nhưng nó mang **hình
   dạng API-key**: `submit()` nhận `principal` và ghi `key_id` + ngân sách
   project. Cuộc gọi của `taovideo` là **phiên web**; bịa một principal để dùng
   nó là ghi sai sổ.

⇒ Phần còn lại của H41.5 là **một tính năng nền tảng** (một đường gọi tool
  dùng chung cho cả phiên web lẫn khoá API), và nó chạm `submit_with_credit`
  — tức **đường tiền. Theo chính tiêu chí của tài liệu này, việc đó thuộc
  Đợt 3 — mỗi việc một phiên riêng**, không phải Đợt 2.

<details><summary>Nội dung Đợt 2 như viết ban đầu (giữ để truy vết)</summary>

⏳ **Cần chủ sản phẩm gật trước**, vì đợt này chạm hai ranh giới: nó **mở bề mặt
công khai** cho khách trả tiền, và bước bật cờ + deploy nằm ngoài quyền phiên.

1. **H41.5** — khai bề mặt công khai `upscalevideo`, gỡ cạnh cross-product ở
   `apps/taovideo/routes.py:548,577`.
2. **H35.10** — mở `video.upscale` + `video.subtitle` trên `/api/v1`.
   `video.short_clips` **vẫn đóng** (chờ H35.10c).

⚠️ **Hai bẫy đã biết của khu API, cả hai là gate đỏ nếu quên:**
- `LTT_PUBLIC_API_TOOLS` là **fail-closed** — bật cờ một mình không mở tool nào.
  Mở tool phải chạy `setup\cong_tac_tool_api.ps1` **rồi mới** deploy; sai thứ tự
  thì cờ không có tác dụng.
- Đổi tool đang mở thì **phải** cập nhật `docs/PUBLIC_API/APP_API_COVERAGE_FINAL.md`
  — `test_212` đọc bảng đó **như dữ liệu** và so với registry **cả hai chiều**.
- 24 route đóng băng ở `server/api/inventory.py`: thêm route mà quên khai là gate
  đỏ, và ngược lại.

**Nghiệm thu:** canary một khoá, request thật, **vượt cap trả 413 chứ không 503**,
sổ credit đóng đúng vòng `hold → settle`, và kiểm trên **URL công khai** (quy tắc
5b), không chỉ loopback.

</details>

### Đợt 3 — hai việc rủi ro cao, mỗi việc một phiên riêng

Không làm chung, không làm chung với bất cứ thứ gì khác.

- **H35.10b** — trần cứng cho việc nâng giữ chỗ. Chạm `credit.py`. Gate đầy đủ
  trước **và** sau; đường lùi viết trước khi sửa dòng đầu tiên.
- **H41.3** — `hold_expires_at` + tự hoàn (nếu chủ sản phẩm duyệt ở §4-A).
  Chạm schema **và** đường tiền. Migration phải chạy transactional.

### Đợt 4 — sau khi phiên `lttstudiosapp-7b` nhả khu admin

- **Mục G** — gỡ `_KHOA_CU` khi trang cuối cùng chuyển sang khoá mới.
  ⛔ Đừng **thêm** dòng vào nó; trang mới khai thẳng khoá mới ở `SECTIONS`.
- **Mục A** — Jinja hoá 4 miền API, chỉ khi có người sửa cùng lúc ≥ 2 trang
  trong đó, hoặc một trang cần khối UI mà f-string không dựng nổi.

---

## 6. Việc vệ sinh — phát hiện lúc tiếp quản

Năm khoản, không khoản nào là việc lớn, nhưng bỏ qua thì các phép đo sau đứng
trên nền bẩn.

**V1. `docs/PUBLIC_API/CONTRACT_BASELINE.json` đang bẩn.**
```diff
       "tool"
+      "ghost_field"
```
Đúng rác fixture `test_209` mà nhật ký 2026-08-29 đã cảnh báo — **lần thứ hai**.
Sửa bằng `git checkout` file đó.
⛔ **Tuyệt đối không chạy `check_api_compat.py --accept` để cho qua** — nó nuốt
mất một thay đổi phá vỡ tương thích thật nếu có.
⭐ Nó tái diễn hai lần trong ba ngày ⇒ đáng cân nhắc cho `test_209` dọn sau
mình (fixture ghi vào tệp trong cây mà không hoàn nguyên khi bị ngắt).

**V2. Bảng H41 trong kế hoạch tổng lệch nhật ký.** `KE_HOACH_TRIEN_KHAI.md` còn
ghi **H41.2 treo**, trong khi nhật ký 2026-08-26 đã có E3 cho GJ-1/2/6 trên URL
công khai và chốt GJ-3 **giữ E2 có lý do** (đòi giao dịch tiền thật). Quy tắc của
chính `NHAT_KY.md`: *"khi kế hoạch và nhật ký mâu thuẫn, **nhật ký đúng** và phải
sửa lại kế hoạch cho khớp."*

**V3. H41.7 đang mang số của máy dev.** Kế hoạch ghi *"5/8 app"*; đo trên
`https://app.lttstudios.com` hôm nay là **6/10** (máy dev thiếu cờ `LTT_VPS` và
`LTT_NEXUS` nên đếm hụt hai app). Số dùng để quyết phải là số của production.

**V4. Ô đánh dấu của H37 và H40 đã lỗi thời.** `KE_HOACH_TRIEN_KHAI.md` còn 55 ô
`- [ ]`, trong đó H37 `G4/G5/G9` và H40.5/H40.6 **đã đóng** theo `CLAUDE.md` và
nhật ký. Đây không phải việc còn lại — đây là kế hoạch chưa được cập nhật.
⚠️ Rà cả 55 ô là một hạng mục riêng, **đừng làm lẫn vào một đợt khác**: sửa ô
đánh dấu bằng phỏng đoán còn tệ hơn để nó lỗi thời.

**V5. Nhánh `admin-mvp-v3` đi trước `origin/master` 59 commit, chưa push.**
Kho off-site đã có. Đây là rủi ro mất việc, không phải rủi ro mã.
Push/merge là việc cần chủ sản phẩm gật.

---

## 7. Không làm, và vì sao

Ghi ra để phiên sau khỏi tưởng là bỏ sót.

| Không làm | Vì sao |
|---|---|
| Xoá hẳn thư mục `.codex/` | Ba tệp trong đó là **bằng chứng đo** (bảng arm Q4/Q115/Q116 có `job_id`, VRAM, nhiệt; 4 harness `.ps1` đã chạy thật trên B, một tệp có SHA-256 ghi trong nhật ký). Đã lưu trữ + để lại lời nhắn dừng. Xoá tài liệu thì được; xoá số đo thì không — số đo không dựng lại bằng cách viết lại tài liệu. |
| Mở `parallel>1` | Q5 DEFER theo Q112/Q116. `parallel=1` là mặc định an toàn và đã có số đo. |
| Reboot máy B | Ngoài phạm vi; cần cửa sổ bảo trì được duyệt. |
| Chạy `gate.py` để **dò lỗi** | Gate là công cụ ra **phán quyết**, không phải chẩn đoán. Ngày 27/08 nó bị chạy sáu lần chỉ để dò, bốn lượt đỏ vì thứ mà một bước con lẻ trả lời trong nửa giây. |
| Sửa `server/admin.py` | Ranh giới 4 — phiên khác đang giữ. |
| Tin lượt `gate.py --vong-lap` lúc 09:34 | Cây đổi giữa lượt chạy (gate tự báo). 10 test đỏ đúng nhóm hay tranh tài nguyên (`test_150`/`test_151` GPU lease, `test_263` apikeys, `test_145` dấu thời gian). **Chưa kết luận gì** cho tới khi chạy lại trên cây đứng yên. |

---

## 8. Câu hỏi cần chủ sản phẩm trả lời để mở khoá

Xếp theo mức chặn:

1. **H41.7 + H41.8** — chặn bề mặt MVP công khai. Hai câu hỏi này đi cùng nhau:
   H41.8 là gốc, H41.7 là hiện tượng.
2. **Đồng ý cho làm Đợt 1 (H35.10a) không?** — nếu có, đây là việc kỹ thuật
   đáng làm nhất còn lại, và nó mở khoá hai việc khác.
3. **H41.3** — có nâng INV-5 từ *quan sát* lên *bảo đảm* trong đợt này không?
4. **Mục J** — có thu hẹp `overview()["jobs"]` về đúng job của API không?
5. **V5** — push `admin-mvp-v3` lên `origin` chứ?
