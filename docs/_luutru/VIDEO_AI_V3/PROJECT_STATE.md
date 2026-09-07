# VIDEO AI PROJECT STATE

> 🔴 **CHƯƠNG TRÌNH NÀY ĐÃ DỪNG PHÁT TRIỂN — 2026-09-06.**
>
> Chủ dự án chốt: *"V3 đã dừng phát triển, ta đang tập trung vào V2.1.
> Loại bỏ V3 sau khi V2.1 chính thức khởi động."*
>
> Đường đang sống là **LTT VIDEO V2.1 — WanGP One Engine**: nhánh
> `phien/video-v2-wangp`, tài liệu `docs/VIDEO_AI_V2/`.
> **Đọc `docs/VIDEO_AI_V2/PROJECT_STATE.md` trước khi làm bất cứ gì ở đây.**
>
> ⛔ Đừng xây tiếp nhánh này, và đừng `git merge` nó vào trunk — nó sửa 13 tệp
> hạ tầng dùng chung, bốn trong đó là cơ chế ngân sách lõi mà trunk cũng đã sửa
> nhiều hơn. Cần lấy lại một tệp thì `git checkout <nhánh> -- <đường dẫn>`.
>
> ⭐ Mọi thứ dưới đây vẫn **đúng tại thời điểm nó được ghi** và vẫn đáng đọc lại
> — phép đo ở đây đã trả bằng tiền thật. Nó chỉ không còn là kế hoạch.
>
> ⚠️ Tài nguyên trả tiền của chương trình này **vẫn đang tính tiền**: volume
> RunPod `uizchbiet5` (300 GB, ~$21/tháng). Dừng phát triển **không** làm nó
> ngừng — nó tính theo dung lượng, không theo việc dùng. Giữ hay bỏ sẽ chốt ở
> **P01 của V2.1**.

---

> Khuôn: `templates/PROJECT_STATE_TEMPLATE.md` của pack V3, cộng hai trường P00 đề
> xuất thêm (`phase_budget_envelope`, `blan_regression_status`).
> **Cập nhật sau MỖI pha.** Tệp này là nơi phiên sau đọc đầu tiên.

- **phase:** **8/8 pha đã đóng** (P00–P07, P09, P10, P15). `P14a`: đỏ cho việc
  **bán ra ngoài**, **xanh** cho việc **dùng nội bộ** — xem `V-018`, đã CHỐT.
- **status:** **`P15` ĐÓNG** — gate đầy đủ `RESULT: PASS` (26/27, một bước tự
  bỏ qua). **`V-018` ĐÃ CHỐT — đường A**, chủ dự án duyệt 05/09 (*"theo đề
  xuất"*). Không còn việc nào của chương trình này chờ quyết định.
- **source_branch:** `claude/ltt-video-ai-v3-p00-3f5713`
- **worktree:** `D:\LTTSTUDIOSAPP\.claude\worktrees\ltt-llm-api-http-guide-a3e123`
- **base_commit:** `d225a480564de1f6298a9b8bf04c3cfca8a9c05a` (`d225a48`)
- **current_commit:** ⚙️ hỏi `git log -1 --format=%h`, đừng chép vào đây —
  một số hiệu commit gõ tay là một số hiệu sẽ sai từ lần commit kế tiếp.
- **environment:** máy vừa là dev vừa là **production** (`C:\LTTPlatform` tồn tại;
  `https://app.lttstudios.com` trả 200 lúc 2026-09-04 17:50). Làm việc ở cây `D:\`,
  **không** chạm `C:\LTTPlatform\app\`.

> ⛔ **Hai dòng trên là thứ trôi nhanh nhất trong tệp này.** Ngày 05/09 chúng
> còn ghi `P05` trong khi cuối tệp đã ghi 7/8 pha — cùng cơ chế đã gỡ bảng 280
> dòng khỏi `CLAUDE.md`. Nếu chúng nói khác mục **Bàn giao**, tin mục Bàn giao.

## 🔑 ĐỌC HAI THỨ NÀY TRƯỚC — mọi tệp khác là hồ sơ đường đi

| Hỏi gì | Ở đâu |
|---|---|
| **Kế hoạch đang sống** | `docs/VIDEO_AI/KE_HOACH_XAY_DUNG.md` — **7 pha, một nguồn** (`V-014`) |
| **Tham số sản xuất** (bước, cfg, shift, kích thước, GPU, BOM) | `platform_core/video_gen/cau_hinh_san_xuat.py` — `test_712` canh |

⛔ Sáu tệp kế hoạch cũ đã đóng băng và mang banner *"HỒ SƠ ĐƯỜNG ĐI"*:
`EXECUTION_PLAN_REBASED` · `CHUOI_MODEL_VA_VAN_HANH` · `CLOUD_RESOURCE_PLAN` ·
`OSS_PIPELINE_CATALOG` · `COST_BUDGET_LEDGER` · `NGHIEN_CUU_CLOUD_GPU` ·
`THAM_SO_VA_THOI_GIAN` · `MODEL_BOM_{PLANNED,FINAL}.csv`.
Chỗ nào chúng nói khác hai nguồn trên, **chúng sai**.

🔴 **Vì sao phải làm thế:** trong hai ngày cấu hình sản xuất đổi **ba lần**
(bf16 40 bước → fp8 4 bước → fp16 40 bước) và mỗi lần được chép tay vào tài liệu.
Quét 05/09 tìm được **14 tệp** còn mang giả định cũ. Cùng cơ chế `CLAUDE.md` đã
gỡ bảng *"cái gì đang sống"* 280 dòng: **một bảng chép tay không tự biết nó đã cũ**.

### Chuỗi xây dựng — 7 pha, ba luật đáng nhớ

```
P05 nap model (0 GPU)  ->  P06 image+endpoint+luot khoi (~$0,05)
->  P07 DO MOT LAN (~0,5h)  ->  P14a CONG THUONG MAI (0 GPU)
->  P09 provider  ->  P10 app  ->  P15 cong khai
```

- ⛔ **Không pha nào so sánh nhiều lựa chọn** (`V-014`). `P08` đã bị lập rồi giết
  **ba lần** dưới ba cái tên khác nhau; luật này là thứ ngăn nó quay lại lần thứ tư.
- 🔴 **`P14a` là cổng DỪNG và đứng TRƯỚC `P09`/`P10`** — chốt giá **trước** khi
  xây app. Giá vốn × 2 không cạnh tranh được ⇒ dừng, trình chủ dự án.
- **Kiểm ở nơi nó sẽ chạy.** Không dựng bậc kiểm trung gian ở máy A: máy A là
  Windows/WSL2 + RTX 5060 Ti (Blackwell), worker là Linux + Hopper/Ampere. Lượt
  khói trên cloud vừa chứng minh worker dựng được vừa bắt bẫy subgraph (`V-009`),
  vì ComfyUI validate đồ thị **trước** khi đụng GPU.

## ✅ P05 ĐÓNG — nạp model **trong datacenter**, máy A ~0 byte

| | |
|---|---|
| Kết quả | **8/8 tệp · 170,515 GB · 0 lỗi · 62,8 phút** · đối chiếu độc lập từ máy A: **đủ và đúng byte** |
| Pod | `b33f664mr7dtpu` · 4 vCPU · US-KS-2 · sống 71 phút · **ĐÃ XOÁ** (HTTP 204) |
| Chi phí thật | **$0,20** (số dư $49,88 → $49,68). Máy A truyền ~0 byte. |
| Tốc độ | 39–91 MB/s (HuggingFace tiết lưu, không phải RunPod) |
| Ảnh | `python:3.11-slim` — chỉ thư viện chuẩn, **không `pip install`** |
| Nguồn | HuggingFace, revision đã ghim, sha256 đối chiếu `lfs.sha256` thượng nguồn |
| Đích | `/workspace` = volume `uizchbiet5` |
| Bảng kê | `BANG_KE_MONG_DOI.json` — 8 tệp, 170,515 GB |
| Công cụ | `tools/video_nap_model.py` · `tools/video_bang_ke.py` · `test_713` |

🔴 **Vì sao KHÔNG nạp từ máy A** — hai thứ tôi bỏ sót, phiên điều phối chỉ ra:
① `cloudflared` **đang chạy trên máy A** (`sc query` → RUNNING; app trả 200 trong
0,72 s) ⇒ 340 GB sẽ bão hoà đúng uplink khách thật đang dùng;
② `D:` chỉ còn 53 GB, dùng chung với hai worktree khác và `D:\LTTBackups`.

⭐ Nhưng cái sai gốc cũ hơn, và chủ dự án bác nó bằng một câu hỏi: *"Máy cloud
không tự tải model về được à mà cần chuyển model qua s3 từ máy A?"* — Nó tự tải
được. Tôi chép **luồng nạp volume RunPod ghi trong tài liệu**, mà luồng ấy mặc
định *dữ liệu nằm trên máy bạn*. Dữ liệu của ta nằm trên HuggingFace, tức **đã ở
trên Internet rồi**. Lần thứ ba của cùng một lỗi `V-011` trong hai ngày.

⛔ **POD TÍNH TIỀN LIÊN TỤC** — khác serverless. Ba lớp chặn: tên mang tiền tố
`lttvideo-` (⇒ `kiem_ke` thấy), mốc `_NAP_XONG.json` để biết lúc xoá, và ghi
`COST_LEDGER.csv` **lúc tạo**.

🔴 **Và lớp thứ ba đã suýt hỏng ngay lần đầu:** lượt `tao` tạo pod **thành công**
rồi chết ở dòng `print` kế tiếp vì stdout Windows là cp1252 ⇒ `ghi_so()` (nằm
**sau** print đó) không bao giờ chạy ⇒ một pod đang tính tiền mà **không có
trong sổ**. Đã vá hai lớp và `test_713` chốt bất biến: **câu lệnh ngay sau khi
có `pid` phải là `ghi_so`** — không cho phép bất cứ thứ gì có thể ném chen vào.

## Cloud

- **active_cloud_resources:** network volume `uizchbiet5` **+ endpoint
  Serverless `uwzftpd3utftfn`** (`lttvideo-worker`, `workersMin=0` nên **về
  không khi rảnh**). Ảnh build từ kho riêng `lttvideo-worker` qua GitHub
  integration — đẩy `main` là RunPod tự build, `version` của endpoint tăng.
  Sổ: `COST_LEDGER.csv`.
- **⛔ ĐỌC TRƯỚC KHI CHẠY BẤT CỨ GÌ TỐN TIỀN:**
  `python tools\video_theo_doi.py tom-tat` — dòng **`Hoa don`** mới là sự thật;
  dòng `Muc chi` là **chỉ báo tức thời và nó MÙ trong lúc worker khởi động**,
  tức mù đúng giai đoạn đắt nhất (`V-017`).
- **persistent_storage:** ✅ **`uizchbiet5`** · `lttvideo-models-v1` · **300 GB**
  standard · **`US-KS-2`** · tạo 04/09/2026 16:20 (+07). ⛔ `dataCenterId`
  **không sửa được**; `size` nới được bằng `PATCH`, thu lại thì không.
- **runpod_account:** số dư **$47,26** (05/09 cuối ngày; đã tiêu **$1,32** cho
  990 giây tính tiền) · **Auto-Pay TẮT** · trần RunPod $80/giờ ·
  khoá API `lttvideo-platform` (phạm vi `graphql` R/W) ở `secrets/app.env`.
- **live_hourly_price:** 🔴 **SỬA 05/09 (`V-017`).** Giá đang dùng là
  **$0,00133/giây = $4,79/giờ** — `NVIDIA H100 NVL`, **đo được** lúc worker
  chạy (`currentSpendPerHr` $4,8190 trừ $0,0290 ổ đĩa).
  ⛔ Giá cũ $0,00076 là giá **A100**, và `V-013` đã bỏ A100 từ lâu — nguồn đúng,
  trích đúng, và **sai** vì thứ nó mô tả bị thay mà không ai quay lại gỡ.
  ⚠️ $4,79 **cao hơn cả ba giá bảng** (`securePrice` $2,89–3,49) vì `securePrice`
  là giá **Pod**; Serverless Flex tính khác. ⇒ **Bảng giá không phải nguồn chân
  lý cho Serverless — phép đo mới là.** Network volume standard **$0,07/GB/tháng**.
  🔴 **Khoản P03 bỏ sót:** container disk **~$0,10/GB/tháng** (mặc định 50 GB;
  ta đặt **20**).
- **datacenter:** **`US-KS-2`** — chọn bằng phép đo 11 DC × 8 GPU, không đoán.
  Là DC **duy nhất** vừa có S3 API, vừa host Serverless, vừa có `A100 80GB PCIe`.
  Đường lui trong cùng DC: `H100 NVL` 94 GB. Ba DC trong danh sách 11
  (`EUR-NO-1`, `US-IL-1`, `US-WA-1`) **không có GPU ≥ 80 GB nào**.
- **month_spend_estimate:** **$21,00** (volume, cố định) — compute vẫn **$0,00**
- **month_budget_remaining:** **$129,00 / $150,00** *(đã trừ volume)*
- **phân bổ:** volume **300 GB** **$21,00** + **sàn credit $31,50** + compute
  **$97,50** = **$150,00**. 🔴 Sàn credit là khoản **KHÔNG ĐƯỢC TIÊU**: số dư về
  $0 thì RunPod **xoá volume, không khôi phục được** (`billing.md`).
- **volume:** **300 GB, tạo một lần, không chia đợt** (chủ dự án chốt 04/09).
  BOM thật **170,51 GB** ⇒ còn trống 129,5 GB cho mode Character và tệp tạm.
  ⚠️ Nới được, **thu lại thì không**.
  🔴 **Rút lại đề xuất hạ xuống 150 GB** (tôi nêu 05/09 khi còn tưởng chạy fp8):
  **300 GB đúng**. Lần thứ hai con số chủ dự án chốt đúng hơn con số tôi tính —
  lần đầu là 275 vs 300.

- **thuê hay mua:** **THUÊ** (`V-005②`) — mua card không khả thi

- **phase_budget_envelope:** ⚙️ sống trong `ngan_sach.ENVELOPE_PHA_GIO`;
  `test_710` cưỡng chế **tổng ≤ envelope thật** và **P06 + P07 ≤ giờ mua được
  bằng số dư hiện có**. ⛔ Đừng chép bảng đó ra đây.

- 🔴 **HẠN MỨC ≠ TIỀN THẬT:** hạn mức tháng **35,6 giờ** (giả định nạp đủ $150)
  so với **6,8 giờ** mua được bằng số dư thật $50 (đã trừ sàn credit $31,50).
  `ngan_sach.gio_compute_kha_dung()` trả con số thật; `tools\video_cloud.py
  trang-thai` in cả hai cạnh nhau. Cầu dao **đang cảnh báo** — $50 ≤ 2 × sàn.
  ✅ Sau `V-012`, P06 + P07 = **4,2 giờ** — vừa trong 6,8.

- **Cấu hình sản xuất:** ⚙️ **`cau_hinh_san_xuat.py`** là nguồn duy nhất.
  Tóm tắt để định hướng (đừng trích dẫn lại ở nơi khác): **một đường duy nhất**,
  fp16 · **1280×720** · 81 khung/16 fps = **5,06 s** · **20 bước** (nhánh chất
  lượng của chính ComfyUI, `V-013`) · shift lấy của **tác giả model** (T2V
  **12,0**, không phải 5,0 của template) · **không LoRA** ·
  **H100 NVL 94GB trước, A100 80GB làm đường lui**.
  **Độ dài tối đa là 81 khung** (`wan_shared_cfg.frame_num`) — dài hơn thì **nối
  đoạn**, đúng cách template `animate` làm.
  Ước **~8,7 phút · ~$0,60** mỗi video 5 s ⇒ $18,50 ≈ **30 video**;
  video 10 s = nối hai đoạn ≈ 17,4 phút.
  ⛔ Là **ước tính** từ bảng đo chính chủ; `Đ2` thay được.

- ⭐ **Mở rộng prompt — tác giả model KHUYẾN NGHỊ**, đưa vào V1, **0 giây GPU
  thuê**: đi qua `api_pool` theo đúng khuôn `image_gen/prompt_dich` + `dich_gemini`
  (`D-027`). ⛔ Không dùng `apps/ltt_llm` trên máy B — `P00` cấm V1 chạm B-LAN.

- ✅ **`V-008` (A100 80GB) đứng vững; giả thuyết L40 48GB CHẾT** — fp16 ở 720P
  đỉnh VRAM **59,8 GB**, không vừa 48 GB. ⛔ `V-012`: **không tra cứu card VRAM
  thấp nữa**, đã gỡ khỏi kế hoạch.

- ✅ **Kế hoạch đo chốt bằng bộ đo CỘNG ĐỒNG** (`KE_HOACH_DO_LUONG.md`):
  chất lượng dùng **VBench** (Apache-2.0, CVPR24 Highlight, `pip install vbench`,
  `--mode=custom_input`), 7/16 chiều nội tại video. ⭐ **Chấm điểm chạy trên
  A-CONTROL, không tốn GPU thuê** — video là tệp mp4, chấm nó không cần A100.
  Vận hành đọc từ ComfyUI `/history` + RunPod `/billing`, không cài thêm gì.
  Bốn phép đo; GPU thuê **~2,3 giờ** (envelope `P07` = 3,0 kể cả biên).
  ⭐ Bỏ hai bậc thấp làm phép đo **đắt lên**, không rẻ đi: ít hạng mục hơn
  nhưng mỗi hạng mục nặng gấp ~30 lần đường chưng cất.
  ⚠️ `vbench` phải cài **venv riêng ngoài cây kho** — nó đòi CUDA ≤ 12.1 còn máy
  A chạy cu128; cài chồng là hỏng `taoclipngan` và `render_gateway`.

- ⛔ ~~Giả thuyết L40 48GB rẻ hơn 1,43 lần~~ — **đã chết ở `V-010`**. Nó đứng
  trên giả định chạy fp8 ở 640×640; sản xuất chạy fp16 tới 720P, đỉnh 59,8 GB.
  ⭐ Giữ lại vì cách nó chết đáng nhớ: giả thuyết **khớp quá vừa** (rẻ hơn, giải
  luôn bài toán thiếu tiền, có một con số đo hậu thuẫn). Câu *"chưa đổi `V-008`,
  phải đo"* là thứ duy nhất giữ nó không thành một quyết định sai.

- 🔴 **Hai khoản P03 bỏ sót:** container disk ~$0,10/GB/tháng (mặc định 50 GB ⇒
  $5/tháng thừa; đặt **20**) và `idleTimeout` (chốt **60 giây**, phép tính ở
  `VAN_HANH_MAY_C.md` §3).

## Quyết định — trạng thái hiện tại

Sổ đầy đủ: `DECISIONS.md`. Tóm tắt để phiên sau không phải mở nhiều tệp:

| | Nội dung | Trạng thái |
|---|---|---|
| **V-001** | Vì sao C-CLOUD: **nội bộ trước, bán phần dư**; tối giản chi phí dài hạn | ✅ **CHỐT** (đáp ADR-0) |
| **V-002** | App mới **`lttvideo`** · prefix `/lttvideo` · tool **`video.ltt`** · `requires=("api",)` | ✅ **CHỐT** (đáp ADR-1) |
| **V-003** | Giá bán = **2 × giá vốn theo giây**, giá vốn chuẩn là hằng **đã đo, có phiên bản** | ✅ **CHỐT** (đáp ADR-2) |
| **V-004** | Mở **bề mặt nội bộ trước** (`surface="admin"`), bán sau. **P13 hoãn cả pha** | ✅ **CHỐT** |
| **V-005** | ② **thuê, không mua** (máy B max tải, mua card không khả thi) — C-CLOUD là **vĩnh viễn** | ✅ **CHỐT** ② · ⏳ ① lớp GPU nào: **CHỜ ĐO** (P03) |
| **V-006** | ADR-3 do Claude đề xuất | ✅ **CHỐT** |
| **V-007** | C-CLOUD **được** giữ credential R2 (temporary, giới hạn tiền tố, có TTL). **Máy B không đụng** | ✅ **CHỐT** |
| **V-008** | **GPU = A100 80GB**, chốt, không tra cứu thêm — Wan2.2 A14B đòi ≥80GB **ngay cả khi đã offload** | ✅ **CHỐT** |
| **ADR-3 v4** ✅ **APPROVED** → `Q121` | **Phương án C** — cổng mới, KHÔNG sửa `render_gateway`: `gateway_core/` + `video_gateway/` (**một lõi, hai cửa vào**) + provider `ltt_video` + `platform_core/video_gen/`. **C-CLOUD = serverless endpoint**, không phải Pod tự quản. Chấm **277/300** | ✅ **APPROVED** 2026-09-04 |
| **Nghiên cứu** | `NGHIEN_CUU_CLOUD_GPU.md` — **RunPod Serverless** ($2,72/hr A100 · **$1,22/hr 48GB**) vs Modal/Replicate/fal; ba câu hỏi mở của ADR **đã có đáp án**; **P14 phần lớn bị xoá** | ✅ xong 2026-09-04 |
| **Q121** | Đặt LTT Video AI trong kiến trúc (khuôn Q102) | ✅ **ĐÃ GHI** vào `docs/QUYET_DINH_NEN_TANG.md` |

**Không sửa `USER_DECISIONS.md`.** D01–D12 nguyên vẹn — đối chiếu từng dòng ở
`EXECUTION_PLAN_REBASED.md` §8.

## Kết quả P00 · P01 · P02 · P03

- **evidence:**
  - `CURRENT_SYSTEM_MAP.md` · `PROMPT_PACK_V3_REVIEW.md` ·
    `EXECUTION_PLAN_REBASED.md` (§8 đối chiếu D01–D12, §9 tự rà soát) ·
    `DECISIONS.md` · `ADR_REMOTE_VIDEO_COMPUTE.md` (**APPROVED**) ·
    `ARCHITECTURE_SCORECARD.csv` · `NGHIEN_CUU_CLOUD_GPU.md`
  - **P01:** `B_LAN_COMPATIBILITY_BASELINE.md` — tập phép kiểm lấy từ
    `tools/thanh_phan.py --test` (không suy từ tên tệp); hợp đồng hành vi cổng
    ảnh dịch sang tên ca kiểm; gate **G-B** viết thành lệnh chạy được
  - `docs/QUYET_DINH_NEN_TANG.md` → **Q121** (đặt LTT Video AI trong kiến trúc)
  - **P02:** `OSS_PIPELINE_CATALOG.md` · `MODEL_BOM_PLANNED.csv` ·
    `UPSTREAM_REVISIONS.lock` — cả 4 mode có baseline, **0 NO-GO**
  - **P03:** `CLOUD_RESOURCE_PLAN.md` · `COST_BUDGET_LEDGER.md` ·
    `MODEL_BOM_FINAL.csv` · `CLOUD_SAFETY_PLAN.md` — giá hỏi **hai lần**, trùng
  - **P03b:** `CHUOI_MODEL_VA_VAN_HANH.md` — **220,812 GB chính xác**, không còn
    ô `CHƯA_XÁC_ĐỊNH`; cách tính tiền ổ đĩa (**theo giờ**); sàn credit
  - **P04 (kế hoạch):** `KE_HOACH_DUNG_MAY_C.md` — ranh giới người/máy, API-first,
    Docker image tự dựng (⛔ không dùng worker-comfyui vì **AGPL**), công cụ vận hành
  - **P04 (đã chạy):** `VAN_HANH_MAY_C.md` (OS + cấu hình chỉ-trả-khi-dùng) ·
    `COST_LEDGER.csv` · `platform_core/video_gen/` · `tests/test_70{0,1}_*` ·
    `tools/video_cloud.py`
  - **P04b:** `THAM_SO_VA_THOI_GIAN.md` · `MODEL_BOM_V1.csv` ·
    `KE_HOACH_DO_LUONG.md` · `V-009` — trích tham số thật từ template đã ghim

## ⚠️ Hai chuyện liên phiên phải biết

- **Dải test 700–799 là của chương trình này.** Phiên H44 (ChatLTT V3) ban đầu
  cũng ghi 700–799, đã tự dời sang **800–899** ngày 05/09 khi cả hai bên còn
  **0 tệp** trong dải — đổi lúc đó tốn 0 đồng, đổi sau khi mỗi bên có 30 tệp thì
  không. Số cao nhất đang dùng trong `tests/` trước đó là 637.

- 🔴 **`ho_so_he_thong.txt` — cây này KHÁC các cây khác, đừng "sửa" cho giống.**
  Nhánh `admin-mvp-v3` và `claude/chatltt-v3-agentic` đã **gỡ** tệp này
  (`e85020eb`, quyết định của chủ dự án). Nhánh này (`claude/ltt-video-ai-v3-p00-*`,
  gốc `d225a48`) **chưa có commit đó**, nên ở đây:
  · `CLAUDE.md:12` vẫn kê `ho_so_he_thong.txt` là nguồn để định vị mã;
  · `tools/gate.py` vẫn có bước **`system profile`**, và nó **FAIL khi tệp cũ**.
  ⇒ Việc sinh lại tệp ở cây này **không phải dựng lại thứ đã gỡ** — nó là điều
  kiện để gate xanh trên chính nhánh này. ⛔ Đừng xoá tệp ở đây để "khớp" nhánh
  kia: gate sẽ đỏ và không ai hiểu vì sao. Việc đúng là **hợp nhất `e85020eb`
  vào nhánh này một cách có chủ đích** — đổi cả `CLAUDE.md` lẫn `gate.py` cùng
  lúc — và đó là việc của chủ dự án quyết, đã trình.
  - `tools/api_prod_canary.py trang-thai` (17:50) — production sống
  - `GET /gia-api` — nav công khai có `🎬 Tạo Video Seedance`
  - đọc mã: `render_gateway/*` · `platform_core/*` · `platform_core/image_gen/*` ·
    `apps/{taovideo,anhnoibo,qualitylab}/*` · `server/api/inventory.py` ·
    `docs/QUYET_DINH_NEN_TANG.md` · `AGENTS.md`
- **tests:** **không chạy** ở P00, có chủ ý — không sửa một dòng mã nào, và ba
  phiên khác đang chia 10 lõi vật lý. Đã chạy ba phép kiểm tĩnh rẻ:
  `check_xuong_dong` **PASS** · `check_ky_tu_dieu_khien` **PASS** ·
  `scan_source_secrets` **PASS** (0 finding / 2.328 tệp).
- **files_changed:** **không sửa/xoá một dòng mã nào** qua cả ba pha.
  ```
  + docs/VIDEO_AI/*.md, *.csv, *.lock   (11 tệp)
  M docs/NHAT_KY.md                     (các mục mới lên đầu)
  M docs/QUYET_DINH_NEN_TANG.md         (thêm Q121, không sửa đè dòng cũ)
  ```
  ⚠️ `ho_so_he_thong.txt` (dẫn xuất) chưa sinh lại — để lượt cuối.
- **risks:** R1 xây trùng `taovideo` (**đã giải** bởi V-002: app mới, không đụng) ·
  R2 chưa rõ vì sao cần C-CLOUD (**đã giải** bởi V-001) · R3 ngân sách chưa chia
  theo pha (**còn**, P03) · R4 hai cây/hai nhánh cùng làm V3 (**đã đóng** — nhánh biến mất) · R5 chưa có
  mô hình giá vốn theo giây-GPU (**đã có khuôn** ở V-003, còn thiếu số) · R6
  A-CONTROL cũng chạy GPU cho khách · R7 CPU 10 lõi dùng chung · R8 mã ghi "video
  là hộ thứ tư của máy B" · R9 hồ sơ dẫn xuất cũ.
- **blockers:** **không còn blocker nào.**
  - ✅ ADR-3 duyệt 2026-09-04 → D01 thoả → code tích hợp được phép từ **P10**.
  - ✅ V-004 chốt → P12 co lại, **P13 hoãn cả pha**.
  - ✅ Hai nhánh `claude/ltt-video-ai-v3-audit-*` và cây bẩn của chúng **đã biến
    mất** (phiên khác dọn trước; P01 xác nhận bằng `git worktree list`).
  - ⏳ **P04 trở đi cần bàn giao người**: đăng nhập / thanh toán Runpod.
- **rollback:** `Remove-Item -Recurse docs\VIDEO_AI` + hoàn tác mục nhật ký. Không
  đụng `platform_core/`, `server/`, `apps/`, `render_gateway/`, `llm_gateway/`;
  không chạm production; không tạo tài nguyên cloud nào.
- **blan_regression_status:** **KHÔNG ÁP DỤNG** — gate **G-B xanh**: `git diff`
  rỗng trên `render_gateway`, `llm_gateway`, `platform_core/image_gen`,
  `platform_core/llm`; `providers.py` chưa chạm.
  ⚠️ Mốc hồi quy đầy đủ nay ở **`B_LAN_COMPATIBILITY_BASELINE.md`** (lấy từ
  `tools/thanh_phan.py --test`, không suy từ tên tệp). P00 từng liệt kê
  `test_227_nexus_render.py` — **sai**, tệp đó kiểm kết xuất HTML của Nexus.
- **next_gate:** **P04 — ĐANG CHẠY.** Kế hoạch dựng chi tiết (P04→P06):
  **`KE_HOACH_DUNG_MAY_C.md`**.
  ✅ **RunPod có REST API đầy đủ** (`rest.runpod.io/v1/endpoints`,
  `/networkvolumes`) ⇒ sau khi nạp tiền, dựng và vận hành **bằng API**, không bấm tay.
  ✅ **Chủ dự án đã xong phần người:** tài khoản tạo, thẻ liên kết, **nạp $50**
  (số dư xác nhận `$50.00`), Auto-Pay giữ **Disabled**.
  ✅ **`RUNPOD_API_KEY` đã tạo và cất** vào `secrets/app.env` (gitignored) — tên
  console `lttvideo-platform`, quyền **Restricted**: `graphql` Read/Write,
  `api.runpod.ai` **None**. Giá trị khoá **chưa từng đi qua chat hay ngữ cảnh**.
  ⭐ **Đã kiểm bằng lời gọi thật:** khoá chỉ có quyền `graphql` **vẫn gọi được**
  `rest.runpod.io/v1` — `GET /billing/networkvolumes`, `/networkvolumes`,
  `/endpoints` đều **HTTP 200**. Giữ được quyền tối thiểu.
  ⏭️ **Tiếp theo (không cần chủ dự án):** P04-a hỏi giá live + chọn DC trong 11 DC
  → P04-b tạo volume 300 GB → P04-c ba phép thử cầu dao.

## Ghi chú vận hành cho phiên sau

- Dải số test của cây này: **700–799** (số cao nhất đang dùng trên mọi cây: 633).
- Tên đã chốt — **đừng đặt lại**: app slug `lttvideo` (KHÔNG gạch dưới), provider
  `ltt_video` (CÓ gạch dưới), tool `video.ltt`, cổng `video_gateway/`, lõi chung
  `gateway_core/`, adapter `platform_core/video_gen/`. Lý do slug không được có gạch dưới: nó sẽ trùng id
  provider trong `platform_core/` và bắt `test_60` phải cấp miễn trừ thứ tư —
  đúng cái bẫy `apps/ltt_llm` đã sập (`tests/test_60_app_registry.py:396`).
- Trước mọi lệnh nặng: `python tools\cua_so_yen.py trang-thai`. Trần `-n 6`.
- Trước khi báo xong bất cứ pha nào có sửa mã: `python tools\gate.py` **đầy đủ**.
- Cuối mỗi phiên: cập nhật tệp này **và** `docs/NHAT_KY.md`.

---

## Bàn giao 05/09/2026 — đọc mục này trước

### Đang ở đâu

**`P06` ĐÓNG.** Video thật đầu tiên đã về tới máy A:
`ComfyUI_00001_.mp4` · 12.445 byte · `ftypisom` · `status_str="success"`.
Môi trường đo được: **H100 NVL 93,1 GB · torch 2.11.0+cu128 · fp16_mo_rong=True
· attention=sage · ComfyUI 0.34.0**.

**`P07` đã dựng xong công cụ, CHƯA chạy.** Lệnh:

```
python tools\video_goi.py do --thu --so-lan 2 --tran 1500   # chay khan truoc
python tools\video_goi.py do --so-lan 2 --tran 1500         # ~$0,74
```

Nó chạy **cấu hình sản xuất** hai lượt trong **một** worker để tách
`nap+ham nong ≈ luot1 − luot2` khỏi `khuech tan ≈ luot2`, và lấy VRAM kèm.

### 🔴 VIỆC ĐANG TREO — kiểm trước tiên

**Build `version 16` chưa lên sau 25 phút** (các build trước chỉ mất ~6 phút).

```
commit worker cuoi : 83e4db7   (da len remote, da xac nhan bang ls-remote)
endpoint version   : 15        (= commit 827598f)
```

⇒ Build cho `83e4db7` **đang treo hoặc đã hỏng**. Vào
`console.runpod.io/serverless/user/endpoint/uwzftpd3utftfn?tab=builds` xem build
log. (Thử đọc bằng `playwright-cli` không ra kết quả — có thể phiên console đã
hết hạn, cần đăng nhập lại.)

⛔ **Đừng chạy `video_goi.py do` khi version < 16.** Worker cũ không biết
`so_lan`, nên nó sẽ chạy **một lượt cấu hình sản xuất** — vẫn tốn ~$0,48 mà
**không tách được** nạp model khỏi khuếch tán, tức trả tiền mà không có đúng con
số cần. Kiểm bằng:

```
python -c "import sys;sys.path.insert(0,'.');import httpx;
env={k.strip():v.strip() for k,v in (l.split('=',1) for l in
open('secrets/app.env',encoding='utf-8-sig') if '=' in l and not l.startswith('#'))};
print(httpx.get(f\"https://rest.runpod.io/v1/endpoints/{env['RUNPOD_ENDPOINT_ID']}\",
headers={'Authorization':f\"Bearer {env['RUNPOD_API_KEY']}\"},timeout=30).json()['version'])"
```

### Ba việc phải làm trước khi chạy

1. `python tools\video_ra_soat.py cham` — phải **35/35**, exit 0. Nó **chặn**.
2. Kiểm build đã lên: `version` của endpoint phải ≥ **16**
   (commit worker cuối: `83e4db7`).
3. Luôn `--thu` trước. ⛔ `--tran` **không phải phanh** — nó giới hạn thời gian
   *chờ*, không giới hạn việc *gửi*. Đã một lần gõ `kiem --tran 1` và nó gửi
   một job thật.

### Quy tắc đã trả giá bằng tiền

- ⛔ Dòng `Muc chi` trong `tom-tat` **mù trong lúc worker khởi động** — đúng
  giai đoạn đắt nhất. Chỉ tin dòng **`Hoa don`**.
- ⛔ Bộ chấm nói `35/35` nghĩa là *"35 câu tôi biết cách hỏi đều ổn"*, **không**
  nghĩa là an toàn. Hai lỗi lớn nhất trong ngày đều lọt qua nó lúc nó xanh.
- ⭐ Bốn tầng lỗi ghép widget đều cùng một gốc: **dựng một mô hình về dữ liệu
  rồi tin mô hình đó, trong khi dữ liệu tự nó đã nói.** Bản sửa cuối bỏ hẳn việc
  mô hình hoá — `n["inputs"]` khai cổng nào là socket, đọc thẳng từ đó.

### ⚠️ Kho worker lệch kho chính — RỦI RO TIỀM ẨN, **không** phải lỗi sống

**Đo 06/09/2026.** `diff` **toàn bộ** `cau_hinh.json` giữa `<scratchpad>/wrepo`
và `video_gateway/`: đúng **một** dòng khác nhau.

```
 "tran_giay_mot_job": 751     <- kho worker (RunPod build tu day)
 "tran_giay_mot_job": 1052    <- kho chinh
```

Hai tệp `.py` khác lệch **chú thích** (số hiệu test 704→714); `handler.py` và
`Dockerfile` giống hệt.

#### 🔴 ĐÍNH CHÍNH — bản đầu của mục này viết SAI

Tôi đã ghi *"mọi job nguội vẫn hỏng"*. **Không đúng.** Đọc tiếp một dòng nữa thì
thấy:

```
handler.py:500   tran = int(vao.get("timeout_s") or CAU_HINH.get("tran_giay_mot_job") or 751)
dieu_phoi.py:91  than = {"input": {..., "timeout_s": tran}}      tran = 1052
video_goi.py:212 than = {"input": {..., "timeout_s": tran_giay}}
```

⇒ **Giá trị máy A gửi xuống THẮNG.** `751` chỉ là **giá trị dự phòng** cho
trường hợp không ai gửi `timeout_s` — và **cả hai** đường gọi hiện có đều gửi.

⭐ Cái sai không phải đọc thiếu mà là **dừng điều tra khi giả thuyết khớp quá
vừa**: tìm thấy hai kho lệch nhau, con số lệch **đúng bằng** con số của một lỗi
vừa chữa xong ⇒ kết luận ngay. Một giải thích khớp hoàn hảo là lúc phải đo
**thêm**, không phải lúc dừng. Xem [[gia-thuyet-khop-qua-vua-ket-thuc-dieu-tra]].

#### Vậy nó còn là vấn đề gì

**Rủi ro tiềm ẩn, không phải thiệt hại đang xảy ra.** Giá trị dự phòng sai thì
đường gọi **thứ ba** nào quên gửi `timeout_s` sẽ nhận trần **751 < 814,6** — và
nó hỏng **im lặng**, vì không có gì so hai kho với nhau.

⇒ Không đủ lý do để kích hoạt một lượt RunPod build lại ảnh **chỉ vì nó**. Nên
gộp vào lần đẩy worker kế tiếp, và kèm **một bánh cóc so hai kho** — vì cơ chế
để lọt là *không có ai đứng giữa đối chiếu*, thứ đã lặp ba lần trong một đêm
(hai cây · hai tệp · hai kho).

### Kho worker (riêng tư)

`giaitritruyenthongltt-spec/lttvideo-worker`, bản sao làm việc ở
`<scratchpad>/wrepo`. Đẩy `main` ⇒ RunPod tự build. **Không có** trong cây này.

---

### Cập nhật cuối 05/09 — sau `P09` + `P10`

**Tiến độ 8/8 pha.** `P14a` đỏ cho việc **bán**, xanh cho việc **dùng nội bộ**
(`V-018` đã chốt đường A); `P15` đã đóng.

| Pha | | Bằng chứng |
|---|---|---|
| P04 Volume + cầu dao | ✅ | `lttv-models-v1` @ US-KS-2 · 300 GB |
| P05 Nạp model | ✅ | 8/8 tệp, sha256 khớp thượng nguồn |
| P06 Image + endpoint + khói | ✅ | video 1,1 MB về máy A, `status_str=success` |
| P07 Đo | ✅ | `DO_LUONG_KET_QUA.csv` 15 dòng |
| **P14a Cổng thương mại** | ✅ | **`V-018` CHỐT đường A** · ngưỡng đảo chiều **193 video/ngày** |
| P09 Provider | ✅ | `ltt_video` trong `providers.py` |
| P10 App | ✅ | `apps/lttvideo/`, bốn cổng đóng |
| P15 Công khai | ✅ | gate đầy đủ `RESULT: PASS` · 26/27 · 5.974+ phép kiểm xanh |

#### ⚠️ TỆP NÀY ĐÃ TRÔI VỀ `V-018` — đọc `DECISIONS.md`, đừng đọc đây

🔴 Tới 06/09 tệp này vẫn ghi *"chờ chủ dự án quyết"* ở **bốn** chỗ, trong khi
`DECISIONS.md` đã ghi **✅ CHỐT đường A** từ **05/09** — chủ dự án trả lời *"theo
đề xuất"*. Hệ quả: tôi đã trình lại một quyết định **đã có**, và tiêu mất sự chú ý
của chủ dự án cho một câu hỏi không còn mở.

⭐ Đúng cơ chế đã gỡ bảng 280 dòng khỏi `CLAUDE.md`: **một bản chép tay không tự
biết nó đã cũ**. Quyết định sống ở `DECISIONS.md`; tệp này chỉ là hồ sơ đường đi.

#### 🔴 `V-018` là thứ chặn, và nó KHÔNG phải lỗi kỹ thuật

```
gia von cua ta (worker am)  $0,90   video 5,06 giay 720P
fal.ai BAN cung model       $0,41   Wan2.2 A14B, 16 fps, giong het ta
=> lo 2,2 lan ke ca khi ban NGANG GIA ho
```

⭐ Gốc là **giá thuê GPU**, không phải cấu hình: RunPod Serverless Flex
**$4,79/giờ** so với **$1,89/giờ** fal.ai bán — đắt gấp **2,53 lần**, khớp gần
đúng khoảng cách 2,2 lần. **Ba đường** ở `V-018`; đường **C** (đổi sang Pod)
không đụng `V-012` một chút nào nhưng đổi mô hình chi phí ($2 081/tháng chạy
24/7), nên đó là quyết định thương mại.

⇒ Khuyến nghị đã ghi: giai đoạn nội bộ **giữ đường A** (trả đắt mỗi video, không
trả gì khi rảnh). Câu hỏi giá chỉ thành thật khi có lưu lượng thật.

#### Đổi tên tài nguyên cloud: `lttvideo-` → `lttv-`

Bánh cóc `test_no_app_slug_is_hardcoded_in_the_platform` bắt được rằng
`platform_core/video_gen/cloud_api.py` chứa `"lttvideo-"` — tức `platform_core`
biết tên một app, đúng thứ `V-002` đã viết là không được xảy ra.

⭐ Sửa bằng **đổi tiền tố**, không bằng nới phép kiểm. Tên thật trên RunPod đã
đổi theo (`PATCH` 200): volume `lttv-models-v1`, endpoint `lttv-worker`.

⛔ `lttvideo-worker` (kho GitHub riêng tư) **giữ nguyên** — đó là tên kho, không
phải tên tài nguyên cloud.

#### Việc còn lại, theo thứ tự

1. ~~Gate đầy đủ xanh ⇒ đóng `P15`~~ — **XONG**.
2. **`V-018`** — chủ dự án chọn A/B/C. Không ai khác chọn được.
3. Nếu chọn C: `KE_HOACH_GO_COLD_START.md` mới có nghĩa trở lại (hiện nó **đúng
   về kỹ thuật nhưng sai về ưu tiên** — $0,40 tiết kiệm không lấp nổi 2,2 lần).

#### 🔴 Sau khi `P15` đóng, tìm thêm MỘT LỖI SỐNG — trần cắt mọi job nguội

Một phiên khác hỏi một câu tưởng đơn giản: *"một video **điển hình** thật sự tốn
bao nhiêu"* — khác câu *"đơn giá GPU là bao nhiêu"*. Câu ấy lôi ra chuỗi sau.

**Gốc là một phép cộng sai trong `DECISIONS.md`:**

```
"20 buoc ~ 520 s, cong ~300 s nap model  =>  du kien ~363 s, bien 2,07 lan"
                                                        ^^^^^
                          520 + 300 = 820, KHONG phai 363
```

Mọi thứ phái sinh từ dòng ấy đều sai **theo hướng an toàn giả**:

| | Ghi | Thật |
|---|---|---|
| `GIAY_DU_KIEN_MOT_JOB` | `363` | **675** (ấm) · **815** (nguội, `executionTime`) |
| biên của trần `751` giây | `2,07 lần` | **0,92 lần** — trần nằm **DƯỚI** nhu cầu |
| cửa sổ chờ của `dieu_phoi` | `tran + 120` | `120` < `delayTime` đo được **155** |

⛔ **Hệ quả nếu không sửa:** `dieu_phoi` gửi `timeout_s=751` xuống worker; một
lượt cold start cần **814,6 giây** trong handler ⇒ **mọi** job nguội bị cắt
trước khi ra sản phẩm, sau khi đã đốt gần trọn trần. Với `workersMax=1` +
scale-to-zero thì lượt nguội là **mặc định**, không phải ngoại lệ. Lượt đo `P07`
chạy được chỉ vì công cụ truyền tay `--tran 1500`.

⭐ **Một cái phanh luôn ăn thì tệ hơn không có phanh** — nó biến "job thất bại"
thành trạng thái mặc định, và tiền vẫn mất.

🔑 **Vì sao nó sống sót:** docstring của `tran_giay_mot_job` **đã tự tính đúng**
(*"dự kiến ~820 giây"*) và **đã ghi số đo đúng** (*"đo được 814 giây. Khớp."*),
nằm cách hằng số sai vài dòng. Không gì so hai con số ấy với nhau. Cùng cơ chế
với `V-017`: nguồn đúng, trích đúng, và sai vì thứ nó mô tả bị thay.

**Đã sửa:**

- Tách **ba đại lượng** trước đây bị gộp: `executionTime` 814,6 s (thứ
  `timeout_s` chặn được) · `delayTime` 154,7 s (xảy ra **trước** handler) ·
  `billed` 969,3 s (thứ sinh ra $1,29). So trần với cột thứ ba là so **sai đại
  lượng** — tôi đã viết một phép kiểm như thế và nó đỏ vì lý do sai trước.
- `TRAN_USD_MOT_JOB` **$1,00 → $1,40** ⇒ 1.052 giây, biên **1,29 lần** trên một
  phép đo duy nhất. ⚠️ Đây là **một con số tiền**.
- `apps/lttvideo/gia.py` **phái sinh** giá vốn từ hằng số giây của
  `platform_core` thay vì gõ `0.90`/`1.29`. Chiều phụ thuộc `apps` →
  `platform_core`, không ngược (`V-002`). Giá credit **không đổi**: 234 / 336.
- Cửa sổ chờ của `dieu_phoi` phái sinh từ `GIAY_KHOI_DONG_NGUOI`.
- `video_gateway/cau_hinh.json` sinh lại (751 → 1.052) — bánh cóc bắt được.
- Ba phép kiểm mới ở `test_710`, **kèm self-test hai chiều** chứng minh trần cũ
  **không** qua được. Một phép kiểm chưa chứng minh nó đỏ được thì chưa phải
  phép kiểm.

#### Gate lượt 6 — `RESULT: PASS`, và một con số đáng giữ

```
RESULT: PASS   [1 BUOC TU BO QUA, KHONG PHAI BANG CHUNG: frontend chatltt]
  [PASS] bo test (song song)   613,6s     <- 5.974+ phep kiem
  [PASS] system profile          7,0s
  26/27 PASS · 1 BOQUA · 0 FAIL
  test-results/gates/20260905T171624Z-14740.json
```

⭐ **613 giây, so với 490 giây khi chạy một mình.** Lượt này chạy trong lúc có
**ba** gate song song trên máy (của phiên này, ASV V4, và Mobile V1), CPU chạm
98 %. Ép CPU làm lượt chạy **chậm 25 %** và **không làm nó sai** — đó là dữ kiện
phân biệt tình huống này với sự cố 03/09, vốn chết vì 12 tiến trình `demucs` mỗi
cái 460–984 % CPU, tức một cơ chế khác hẳn.

⚠️ `frontend chatltt` **tự khai bỏ qua**, và gate in thẳng rằng đó *không phải
bằng chứng*. Nó tự bỏ qua ở cả ba lượt gate đầy đủ gần nhất (`0d509f94`,
`b946e065`, và lượt này) vì bundle của app ấy không được dựng trong cây này —
trạng thái ổn định, không phải mới hỏng.

🔴 **Ngưỡng tự dừng đặt TRƯỚC khi biết kết quả:** RAM trống < 6 GiB thì dừng
gate, không chờ ai đồng ý. Đáy đo được là 9,6 GiB nên nó không bao giờ bị chạm —
nhưng một ngưỡng đặt *sau* khi nhìn số là một ngưỡng sẽ trôi theo điều mình muốn.

#### ⚠️ `RESULT: PASS` chứng nhận NHÁNH NÀY, không chứng nhận bản hợp nhất

Đo 06/09 00:40:

```
nhanh: claude/ltt-video-ai-v3-p00-3f5713
  vs admin-mvp-v3 : sau 125 | truoc 38      <- MOC THAT
  vs master       : sau   0 | truoc 38      <- DUNG, va VO NGHIA
```

⛔ **Đừng đọc dòng `master` rồi yên tâm.** `master` là **tổ tiên thuần** của
`admin-mvp-v3` và đi sau nó đúng **125** — cùng con số của nhánh này. Nên
*"sau 0 so với `master`"* không nói ta mới; nó nói **ta và `master` cũ như
nhau**. Đo được 06/09:

```
master la to tien thuan cua admin-mvp-v3 : CO
master lech admin-mvp-v3 : sau 125 | truoc 0
master dang o d225a480

commit dang chay PRODUCTION (1320e9d1):
    trong master        KHONG
    trong admin-mvp-v3  CO
```

🔑 **Bản đang phục vụ khách hàng không nằm trên `master`.** Nhánh chuẩn của kho
là `admin-mvp-v3`; `master` là một cái tên vẫn còn đó và **vẫn trả lời khi bị
hỏi**. `git rev-list ... master` trả lời thành thật cho câu hỏi hẹp của nó
(*"tôi lệch bao nhiêu so với con trỏ tên `master`"*), không trả lời câu rộng hơn
(*"tôi lệch bao nhiêu so với thứ đang chạy"*).

⭐ Đúng hình dạng của `cua_so_yen` báo RẢNH khi máy bận — chỉ đổi trục: ở kia là
cái khoá, ở đây là **cái tên nhánh**. Mốc phải là **thứ đang chạy**, không phải
tên mặc định.

Trong **125** commit đi trước có `platform_core/phat_media.py` — thứ **mọi route
media của 7 app** đi qua — và luật `@media(pointer:coarse)` mới trong `ltt.css`.

⇒ **Lượt gate quyết định là lượt SAU khi merge**, không phải lượt này. Một phiên
khác vừa tự vấp đúng chỗ đó: chạy gate đầy đủ ở worktree, merge trunk vào, rồi
phải chạy **lại** ở cây chính vì nội dung đã khác.

⛔ Tôi **không** ff ngay, có lý do:

1. Trunk đang **di chuyển** (`c43d7880` vừa đẩy lúc 00:35). Merge một mục tiêu
   đang chạy là đổi một lượt gate đã xanh lấy một lượt phải chạy lại.
2. Merge mà không chạy lại gate thì chỉ có **cảm giác** an toàn, không có bằng
   chứng — và lúc 00:45 có ba phiên đang dùng chung 10 lõi.

🔑 Và một câu đáng thay câu cũ của tôi: tôi viết *"gate tự khai bước ấy không
phải bằng chứng"*; phiên Mobile V1 nói thẳng hơn — **`PASS` kèm ngoặc vuông
không phải `PASS`**. Ở cây này `frontend chatltt` tự bỏ qua vì thiếu bundle;
"ổn định" không có nghĩa là "đã kiểm".

#### Tiến trình mồ côi — đã tự chết, và bài học không nằm ở chỗ đó

Tám PID được ghi lại (`22096` `14456` `15800` `20644` `7836` `28140` `29112`
`11756`) **đều đã biến mất** khi đo lại sáng 05/09. Không cần `taskkill`.

🔴 Bài học thật là chuyện xảy ra **trước** đó: lượt gate thứ 4 chết vì `timeout
900` khi đang ở bước 22/27, và lý do là **hai gate chạy chồng** — một trong hai
là của tôi. Lúc phóng nó tôi đã gõ `cua_so_yen.py trang-thai`, thấy `RẢNH`, và
chạy tiếp.

⛔ `cua_so_yen` **không phải bằng chứng máy rảnh.** Nó chỉ biết ai đã *xin* khoá.
Một gate chạy mà không giữ khoá thì nó không thấy — và cả hai gate hôm đó đều
không giữ. Câu đúng phải hỏi là *"có tiến trình nào đang chạy không"*, tức đọc
**cây tiến trình**:

```powershell
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -match 'gate\.py|test_nhanh|pytest' }
```

⭐ Và phải là **một lệnh riêng, chạy trước** — không ghép `kiểm && chạy` vào cùng
một dòng. Ghép lại thì cái kiểm chỉ còn là nghi thức: nó không đổi được gì nữa,
vì lệnh chạy đã nằm trong cùng lượt gửi.
