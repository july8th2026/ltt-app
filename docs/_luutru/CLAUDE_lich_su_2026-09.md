# LỊCH SỬ — mục "Việc còn dở" của CLAUDE.md

> ⛔ **TÀI LIỆU LỊCH SỬ. KHÔNG PHẢI CHỈ DẪN HIỆN HÀNH.**
>
> Chụp nguyên văn từ `CLAUDE.md` ngày **2026-09-02**, 280 dòng, không sửa một chữ.
> Mọi con số ở đây nói về **lúc nó được viết**, không nói về hiện tại.
>
> Muốn biết HIỆN GIỜ cái gì đang sống:
>
> ```
> python tools/api_prod_canary.py trang-thai
> ```

## Vì sao đoạn này bị chuyển ra khỏi CLAUDE.md

Nó chiếm **280/496 dòng (56%)** của tệp chỉ dẫn chính, và nó là **trạng thái**
chứ không phải **luật** — tức nó hết hạn, trong khi phần còn lại của tệp thì
không.

Và nó đã hết hạn thật, **năm lần đã biết**, **cả năm lần đều về phía nguy hiểm**:

| Lần | Nói sai điều gì | Sự thật lúc đó |
|---|---|---|
| 1 | Public API "hạ tầng đã sống, cửa hàng chưa mở" | 2 tool đang mở, đang thu tiền |
| 2 | `/vps` "App vẫn TẮT (`LTT_VPS` chưa đặt)" | `LTT_VPS=1`, `/vps` trả 200 cho khách ẩn danh, biểu mẫu đang thu credit |
| 3 | Public API "hai tool mở" | bốn tool |
| 4 | Public API "còn nợ H35.10" | H35.10 đã đóng, năm tool mở |
| 5 | `ltt_voice` "trần 1.500 ký tự/lượt" | 31/08 đã tách thành **hai** trần (`TRAN_MOI_LUOT_SINH` và `TRAN_KY_TU_CONG_KHAI`); tài liệu chỉ mô tả một |

⭐ Bốn lần đầu được "sửa" bằng cách viết lại bảng. Lần thứ năm vẫn xảy ra — và
nó không được phát hiện bằng cách đọc lại tài liệu, mà bằng cách **đối chiếu
từng giá trị với chủ sở hữu trong mã**.

⇒ Cái sai không nằm ở người viết câu chữ. Nó nằm ở **kiến trúc**: một bảng chép
tay không có cách nào tự biết nó đã cũ. Nên thứ phải đổi là **nơi câu trả lời
đến từ**, không phải câu chữ.

Xem `docs/system_purification/reports/01_truth_rules_docs.md`.

---

## Việc còn dở

| Hạng mục | Trạng thái |
|---|---|
| Vỏ nền tảng + hợp đồng app | ✅ xong, có test |
| Mã nguồn trong git | ✅ từ 2026-07-31 |
| PostgreSQL + nhiều người dùng (đăng ký, xác thực email, phân quyền) | ✅ xong (H1) |
| Hàng đợi job + worker tiến trình riêng | ✅ xong (H2) |
| Sổ credit (giữ chỗ → quyết toán → hoàn) | ✅ xong (H3) |
| Trang admin (sqladmin) + tài khoản admin trong CSDL | ✅ xong (H3-admin, Q29) |
| Cloudflare Tunnel LIVE + Turnstile + Resend | ✅ xong (H0.1) |
| Cốt lõi vận hành: catalog công khai + SSO + launcher | ✅ xong (H6/H6.6) |
| Tool thật đầu tiên — thumbnail (Gemini, tính credit) | ✅ xong (H5) |
| App socialbot (FB+TikTok) | 🗑️ **ĐÃ GỠ HẲN 2026-08-25 (Q108, thay Q10)** — xoá `apps/socialbot/`, `core/` (15.046 dòng), `utils/`, `server/services/`, 7 module route (43 route = 62% bề mặt công khai cũ), 10 template, 44 tệp test (~1.017 test). Đo trước khi xoá: **0** job, **0** `app_access`, **0** `app_projects`, và **không có** `tokens.enc` — chưa khách nào từng kết nối. Mã còn trong lịch sử git. ⚠️ Đăng ký Meta App + TikTok app là tài sản **ngoài kho**, chủ sản phẩm quyết |
| App demo · kichban · mediatools | 🗑️ **ĐÃ GỠ HẲN 2026-08-25 (Q109)** — danh mục app **19 → 14**. `demo` được thay bằng **app THỬ tổng hợp** trong `tests/conftest.py::app_thu` (sống trong bộ nhớ một test, không thư mục, không route, không lên catalog). ⚠️ Cái giá đã đo và chủ sản phẩm đã chấp nhận: **4–7 trong 10 workflow Agent đang lưu mất node** — 4 tool `asset.*` của `mediatools` là node **đầu vào** của workflow |
| **Củng cố MVP (Hardening)** — Wave 0+1+2 | ✅ xong 2026-07-31 (H7) |
| Bộ máy APIKEYS (provider + 4 category, mã hoá, allocator) — Pha 1 | ✅ xong 2026-07-31 (H8) |
| APIKEYS Pha 2: telemetry rpm/tpm/token + cascade đa-provider + làm mới model | ✅ xong 2026-08-01 (H8) |
| Giao diện: hệ thống thiết kế + header/avatar + catalog | ✅ xong 2026-07-31 (UX Pha 1+2) |
| Thanh toán / nạp credit (PayOS agnostic, gói bonus %, webhook idempotent) | ✅ xong 2026-08-01 (H9) |
| Lưu file lớn qua R2 + `Storage.url_for()` (presigned, serve thẳng CDN) | ✅ xong 2026-08-01 (H10) |
| Di trú app từ BOT GEMINI: thumbnail(parity)+taoanh+kichban+taovideo(video async) | ✅ đang (A1+A2 P1) |
| **Rà soát hệ điều hành** — bố cục mã nguồn + tầng nghiệp vụ | ✅ 9/12 xong 2026-08-06 (H22) |
| Hồ sơ hệ thống tự sinh (`ho_so_he_thong.txt`) | ✅ xong 2026-08-12 (H34, Q91) |
| **Public API `/api/v1`** cho khách lập trình — 5 tool, cổng dev + admin, chế độ thử | ✅ xong 2026-08-15 (H35, Q92); **ĐÃ DEPLOY 2026-08-17**, tool chưa mở |
| **LTT Nexus** (điều khiển máy từ xa) — nền tảng + wiring + billing | ✅ LIVE; Windows + Android chạy thật, thu credit thật. Vòng sửa lỗi 2026-08-22 đóng hết mục A+B của `docs/nexus/N7_DANH_SACH_VIEC.md`. ⏸️ **Một đợt đã commit nhưng CHƯA DEPLOY — đọc `docs/nexus/N8_CHO_DEPLOY.md` trước khi chạy deploy.** Còn hạ tầng C1–C4, macOS, iOS |
| Củng cố phần thi hành của API — lease, đội hình worker, metrics, vòng đời file | ✅ code xong 2026-08-16 (H36); **còn nợ 4 việc chứng minh** — xem H36.9–12 |
| **Model tạo ảnh NỘI BỘ trên máy B (RTX 3090)** — provider `ltt_image`, không phải app | 🔨 giai đoạn A xong 2026-08-22 (H37, Q102); cổng render đã là dịch vụ trên B; bán ra `/api/v1` qua app `anhnoibo` + tool `image.ltt` — **chưa mở cho khách** (4 cổng còn khoá, D-034). 🔴 **So mù G6b 23/08: Gemini 24 – nhà 4 – hoà 2** (phần có ý nghĩa: **14 – 4**, vì chữ tiếng Việt **ngoài phạm vi** — D-048). Nhà thua vì **giải phẫu, hình học, chất chụp thật**. ⇒ **Đừng định vị nó là "đẹp hơn"; ảnh có chữ thì trả lời Gemini và đó là câu cuối.** ⛔ **Bỏ hẳn đối chứng ngoài** (D-046) — đo từ đây là **HiDream đấu HiDream, một lô một biến**. 🔒 **GIỮ 50 BƯỚC — G4 ĐÓNG 24/08 (D-054), câu cuối.** Lô B2c (seed thứ ba) nâng tổng lên **60 cặp**: 50 bước **33 – 18**, điểm 0,625, KTC [0,507; 0,744] **không chứa 0,5**. 36 bước đã thua **hai lô độc lập** ⇒ không nhận. ⚠️ Nhưng khác biệt **nhỏ hơn khác biệt giữa hai seed** (sàn nhiễu 91% > quyết đoán 85%) — đừng đọc thành "36 bước tệ rõ". Muốn mở lại thì phải là **phép kiểm tương đương**, không phải chạy lại phép cũ. 🔨 **Tiếp quản 24/08 (D-050, D-051):** chấm theo `docs/KHUON_BAN_MODEL_NHA.md` được **18/31**; đã sửa **lỗi tiền đang sống** — xin 4 ảnh, máy B trả 2, khách vẫn bị thu tiền 4 vì handler không báo `credit_cost` (cùng gốc với lỗi H38 đã sửa 23/08). Thêm `/live` + chốt GPU/CPU cho cổng render, giá về `apps/anhnoibo/gia.py` và công bố ở `/gia-api`. 🔓 **24/08 (D-052, D-053): giá hạ một phần ba** (5 → 3 credit/ảnh, tham chiếu 15 → 9), **bốn cổng MỞ trong mã**, **G5 đóng** (trần token 7.506 → 11.412, đo thật 20,1 GB · 239 s). **Máy chấm thay người** (D-052) — đổi lại mỗi phiếu quyết đoán phải viết lý do, `cham_mu.py` từ chối tính nếu thiếu. ⚠️ `render_gateway/deploy/deploy.ps1` có **hai lỗi khiến nó chưa từng deploy thành công lần nào** (đích sai một cấp + `Join-Path` giải ổ đĩa của máy A); đã sửa, nay 29/29 khớp hash. ✅ **G4 + G5 + G9 đều ĐÓNG 24/08.** G9: **100/100 lượt, 0 hỏng**, VRAM dao động 163 MB (0,9 %), nhiệt 69–74 °C, **không trôi gì** qua hơn ba giờ (D-056). ⏳ Còn **hai việc cần chủ sản phẩm**: bật cờ bằng `setup\cong_tac_tool_api.ps1` **rồi mới** deploy — sai thứ tự thì cờ không có tác dụng. ⛔ **D-057 (24/08): DỪNG kế hoạch dùng máy A sinh ảnh.** Không hạ độ chính xác model; `bf16` đỉnh 18.450 MB không vừa card 16.311 MB, và riêng Llama-3.1-8B trong bộ mã hoá đã lấp kín một card. Mở lại cần **phần cứng ≥ 24 GB**, không phải một cách xếp encoder khác. ⇒ Hệ quả: **trọng tài VRAM ở `docs/ANH_NOI_BO/CHIA_GPU_HAI_MODEL.md` nay BẮT BUỘC** — hai model vẫn dùng chung 3090 (18.450 + 19.237 = 37.687 MB / 24.576). **KẾ HOẠCH TIẾP: `docs/KE_HOACH_TIEP_2026-08-24.md`** (một danh sách duy nhất, có thứ tự). Xem D-045…D-057 + `docs/ANH_NOI_BO/` |
| **LLM NỘI BỘ bán qua API** (H38, Q106+Q107) — Qwen3.8-27B trên máy B, bán qua `/api/v1` | ✅ **ĐANG BÁN 2026-08-24.** Ba cửa: `/jobs` · `/chat/completions` (`SYNC_BILLED`) · `/messages` + `/responses` (`STREAM`, cho Codex/Claude Code/Claude Desktop). Đã đo thật qua Cloudflare: luồng **119 giây không bị 524**, Codex CLI chạy đầu-tới-cuối, tiền khớp từng credit. Còn: phiên thật Claude Code/Desktop, xoay khoá, công cụ tự ghi cấu hình. Xem `docs/VLM_NOI_BO/` 🧹 **DỌN THAM SỐ 30/08:** mọi ngân sách token nay có **một nguồn chân lý** — `apps/ltt_llm/ngan_sach.py` (3 số gõ tay: `CUA_SO_MODEL` 131.072 · `TOKEN_RA_TRAN` 32.768 · `LE` 2.048; còn lại **dẫn xuất**: trần vào **96.256**, công bố cho client 88.555, body tối thiểu 433 KB). Mặc định token ra phải **gọi theo tên cửa** `mac_dinh_cho("sync"|"stream"|"job")` — một cái tên chung chung đã khiến cửa stream mượn ngân sách 1.024 của cửa đồng bộ và **mọi câu trả lời dài cụt ở đúng 1.024 token, im lặng**. ⚠️ **Đổi trần token của máy B thì sửa `llm_gateway/deploy/deploy.ps1` rồi deploy** — `C:\ProgramData\LTTLlm\gateway.env` là thứ **thắng tất cả** (nó ghi đè `os.environ`) nhưng do script sinh ra, sửa tay là mất ở lần deploy sau; NSSM env và env máy đều **vô tác dụng**. Sau mỗi lần đổi chạy `pytest tests/test_334_ngan_sach_ltt_llm.py` **có `LTT_LLM_TOKEN`** — 21 phép kiểm đối chiếu ba tầng (ta / mã máy B / máy B đang chạy). Xem `docs/VLM_NOI_BO/RA_SOAT_THAM_SO_LTT_LLM.md` |
| **LTT VOICE** — giọng nói tiếng Việt nhân bản (VieNeu-TTS v3 Turbo), chạy **trên máy A** | 🔨 **V0–V6 xong 2026-08-30** (Q117–Q119). ⭐ Khác `anhnoibo`/`ltt_llm` ở chỗ quan trọng nhất: engine chạy **cùng máy**, sau loopback `127.0.0.1:8120`, dịch vụ NSSM thứ tư `LTTStudioVoice` từ venv cách ly `vieneu-venv`. ⇒ **không provider, không `api_pool`, không sửa `platform_core/` hay `server/` dòng nào.** 📊 **Đo thật trên 5060 Ti:** VRAM đỉnh **641 MB** (reserved 1.288) — nhỏ hơn `upscalevideo` quality 12.000 MB gần 10 lần, nên sống chung thoải mái; RTF **0,121 @3.000 ký tự** / 0,70 @câu ngắn; TTFA **398 ms**; nạp model 19,4 s (10,5 s khi ấm). 🔴 **Ba lỗi upstream đã vá, đừng 'sửa' ngược:** ① gói PyPI `perth` là **thư viện threading**, không phải watermarker — phải `resemble-perth`, và `_init_watermarker` của upstream nuốt `AttributeError` nên **mọi lượt sinh trước đó đều không có dấu** (#191); ② `transformers==4.57.6` đòi `huggingface_hub<1.0` nhưng `vieneu` kéo `1.29` — cài theo thứ tự README là venv hỏng, chỉ lộ ra ở `import transformers`; ③ tải model trên Windows có **cuộc đua blobs→snapshots** (không symlink) ⇒ `max_workers=1` + thử lại. ⛔ **Trần 1.500 ký tự/lượt là trần CHẤT LƯỢNG** (#168 báo trôi giọng từ ~3.000), không phải trần kỹ thuật — 3.000 vẫn sinh được trong 17,6 s. ⛔ **`temperature`/`top_k`/`top_p` KHÔNG ra hợp đồng công khai**: cache CUDA graph khoá theo `(B, temp, top_k, top_p)`. ⚠️ **Bẫy deploy:** `LTTStudioVoice` giữ handle trên `app\` nên `update.ps1` phải dừng nó **đầu tiên**; và nếu production đã đặt `LTT_WORKER_POOLS` mà thiếu làn `voice` thì job nằm `queued` **mãi mãi, không lỗi nào báo** (`4-nghiem-thu.ps1` có chốt). ⚠️ **venv + cache đặt ở `D:\LTTPlatform-runtime`** vì C: chỉ còn 5,6 GB/930 GB. 🖥️ **GIAO DIỆN ĐẦY ĐỦ XONG 2026-08-31** — sáu màn: Tạo tiếng nói · Giọng của tôi · Dự án · Chạy lô · Lịch sử · API. Không tab nào còn `built=False`. Xem `docs/LTT_VOICE/VOICE_UI_EXECUTION_PLAN.md` §14 (nhật ký từng pha, kèm mọi lỗi đã tìm ra). ⛔ **ĐỪNG ĐỌC "Chạy lô đã xong" THÀNH "V9 đã xong".** Màn Chạy lô và màn Dự án nộp **một job cho mỗi dòng/khối** — đúng hình dạng cho MVP (mỗi dòng thử lại và tính tiền độc lập) nhưng **không** dùng `infer_batch` lẫn CUDA graph đã ấm. Tức **bề mặt** của V9 đã có, **phần hiệu năng** thì chưa. 🔴 **Một lỗi vòng đời đã sửa, đáng nhớ vì nó có hạn:** `voice_block.audio_key` sống mãi cùng dự án, còn tệp nó trỏ tới sống **30 ngày** theo hạn của `jobs` — nên sau 30 ngày khách mở dự án cũ sẽ thấy một trình phát 404 không lời giải thích. Nay mọi đường nghe đi qua **một** thẩm quyền `du_an.duong_tieng()` (thay cho năm chỗ tự dựng URL), và khối hết tệp thì **nói ra** thay vì để một ô trống. Còn V7–V10. Xem `docs/LTT_VOICE/` |
| **Bán VPS (máy chủ ảo Windows)** — app `apps/vps/`, Proxmox chạy LỒNG trong VMware trên máy B | 🔴 **ĐANG SỐNG VÀ CÔNG KHAI — SỬA 2026-08-26, TRƯỚC ĐÓ HÀNG NÀY NÓI SAI VỀ PHÍA NGUY HIỂM.** Nó từng viết *"App vẫn **TẮT** (`LTT_VPS` chưa đặt)"*. Đọc production 26/08: `C:\LTTPlatform\secrets\app.env:72` → **`LTT_VPS=1`**, và `GET https://app.lttstudios.com/vps` trả **200 cho khách ẩn danh**. Biểu mẫu tạo máy **đang thu credit thật**. ⛔ Vì sao nguy hiểm chứ không chỉ sai: một phiên sau đọc dòng cũ sẽ sửa `/vps` **như sửa mã chết**. *(Cùng lớp lỗi với hàng Public API, sửa cùng ngày.)* 🔨 **~95% — G1→G10 xong 2026-08-25** (H39, Q103–Q105). Chuỗi đã đo thật đầu-tới-cuối: tạo máy **17 giây** → boot thẳng vào trình cài Windows → console trong trình duyệt → DHCP theo MAC → RDP từ Internet qua **IP riêng của từng máy** → thu tiền → treo → xoá → **trả IP về Vultr**. 🔴 **Cụm không chạy được virtio** — máy phải `sata0`+`e1000`, `agent:0`, `balloon:0` (xem `MO_HINH_CARD` trong `apps/vps/services/mang.py`). 🔴 **Khách TỰ CÀI Windows** (chốt 24/08): nền tảng **không bao giờ biết mật khẩu của khách**, không có template, không sysprep. Danh mục dừng ở **Server 2016, Server 2022, Windows 10 LTSC** — **KHÔNG bán Windows 11** (nhánh UEFI/vTPM đã gỡ khỏi `jobs.py`). ⚠️ Hợp đồng app có thêm `AppManifest.bao_tri` — app khai việc định kỳ, nền tảng chạy nó **dưới lease**; app tự dựng vòng lặp sẽ trừ tiền khách N lần mỗi chu kỳ. ✅ **G8 + G10 xong 25/08**: trang tạo máy hai bước, **trang bán công khai** (`/vps` phục vụ cả khách chưa đăng nhập — thẻ app trong catalog trỏ tới đó, nên đòi đăng nhập là ngõ cụt ngay bước đầu phễu), điều khoản riêng + clickwrap, sao kê thanh toán. `test_298` đối chiếu **từng con số** trong điều khoản với hằng số thật — đổi giá mà quên sửa điều khoản là gate đỏ. ✅ Đã **dọn sạch dấu vết diễn tập**: 0 VM lạ, **0 Reserved IP** bên Vultr, 4 bảng `vps_*` về 0 dòng; tài khoản thử bị **vô hiệu hoá chứ không xoá** (bút toán credit là append-only). ⚠️ Còn **G7b** (cpulimit + cảnh báo CPU) và **G9b** (diễn tập dựng lại cổng vào — **KHÔNG cần mua thêm VPS**: Reserved IP sống sót khi instance chết, nên có đường dựng lại $0; hoãn vì nó là hành động không đảo được trên một máy đang trả tiền). ⚠️ Trước khi mở bán phải chạy `setup\cong_tac_tool_api.ps1` **rồi mới** deploy. ✅ Đã xoá **3 template + 7 ISO chết**; đường `clone` gỡ hẳn, `os_images` chỉ còn Windows. Kho `local` còn **5,1 GB**, đủ cho ba ISO đang dùng. ⚠️ **Có shell root trên node** qua `tools/vps_node_shell.py` (termproxy = shell root; token cũng có `Sys.Modify`) — đừng lặp lại kết luận cũ rằng không có. ⚠️ Hạn ngạch Reserved IP của Vultr tính **cả IP vừa xoá**, nên tạo/xoá liên tục lúc thử sẽ làm lượt sau hỏng ở mốc 92%. Xem `docs/VPS/PHAN_TICH_VPS_PROXMOX.md` và mục G ở `docs/KE_HOACH_TRIEN_KHAI.md` |

**Admin hiện tại là tài khoản trong CSDL** (`tools\create_admin.py`), đăng nhập
bằng email; đường admin-từ-biến-môi-trường đã vô hiệu ở production (Q29).

**H7 (Củng cố MVP) — Wave 0+1+2 ĐÃ XONG 2026-07-31** theo audit
`docs/AUDIT_MVP_2026-07-31.md`: đã bịt các lỗ P0 (double-spend, dedupe, IP thật
sau Tunnel, restore DB, băm token phiên, migration trong update) và P1/P2
(billing thumbnail theo ảnh, handler 500, CSRF admin/logout, khoá theo tài khoản,
ACL backup, validate hợp đồng sớm, log rotation, smoke test). Việc **cố ý hoãn**
sang H9/H10 ghi trong file audit + KE_HOACH (url_for/R2, FK constraints).
Cửa mở khách trả tiền giờ phụ thuộc **H9 (Thanh toán)**.

**H22 (Rà soát hệ điều hành) — 9/12 XONG 2026-08-06** theo audit
`docs/APP_AUDIT/control-plane/2026-08-06/`: chốt nơi đặt logic nghiệp vụ
(`AGENTS.md` mục 8), tách hai file route 1.799 và 1.308 dòng, gom việc dùng
chung về `platform_core`, và **cắt hết phụ thuộc của app vào `core/`**.

Ba việc còn lại, **hai trong đó chờ chủ sản phẩm quyết**:
- **H22.10** ✅ → **VƯỢT QUA 2026-08-25**: 43 route đó không còn nằm sau cờ
  nữa, chúng **đã bị xoá** cùng app socialbot (Q108). Cờ `LTT_SOCIALBOT_ROUTES`
  không còn được đọc ở đâu; để lại trong `secrets/app.env` là một dòng vô nghĩa,
  không phải một lỗi. Bề mặt route công khai giảm đúng 62% như đã dự tính.
- **H22.11** ✅ — đã xoá 2 module `core/` không ai gọi (533 dòng). Ba file
  `__init__.py` giữ lại vì là dấu hiệu package.
- **H22.12** ✅ — `platform_core` sạch hết chỗ nuốt lỗi; 90 chỗ còn lại trong mã
  sống nằm sau **bánh cóc** `tools/check_silent_except.py` (trong gate): không
  cho tăng thêm. `core/` (78 chỗ) loại khỏi phép đo vì đã đóng băng.

**H35 (Public API) — XONG 2026-08-15**, nhánh `public-api-v2`, quyết định nền
Q92. Nó là **adapter/policy layer**, không phải một app trong `apps/`: domain ở
`platform_core/public_api/`, HTTP ở `server/api/`. Dùng lại nguyên
`jobs`/`credit`/`upload_sessions`/`storage` — **đừng dựng hàng đợi, sổ tiền hay
pool thứ hai**.

Ba thứ cần biết trước khi đụng vào:

- **Fail-closed.** `LTT_PUBLIC_API` mặc định TẮT, và `LTT_PUBLIC_API_TOOLS` mặc
  định **rỗng** — bật cờ một mình **không** mở tool nào. `customer_visible` của
  ToolSpec **không** phải cờ public.
- **24 route đóng băng** ở `server/api/inventory.py`, so hai chiều với route
  thật và OpenAPI. Thêm route mà quên khai là gate đỏ, và ngược lại.
- **Thêm/đổi tool đang mở thì phải cập nhật `APP_API_COVERAGE_FINAL.md`** —
  `test_212` đọc bảng đó như dữ liệu và so với registry cả hai chiều.

**H36 (2026-08-16)** sửa ba lỗi P0 mà audit tìm ra, tất cả cùng một gốc: **mọi
vòng nền được viết như thể chỉ có một tiến trình chạy nó**, trong khi số tiến
trình worker mặc định bằng **số GPU**. Hệ quả: webhook gửi trùng, cảnh báo trùng,
việc dọn chạy N lần.

Ba thứ cần biết trước khi đụng vào worker:

- **Việc nền nằm sau một lease** (`platform_core/leases.py`). Thêm một việc nền
  mới thì đặt nó trong `_mot_luot_bao_tri`, đừng tự chạy trong vòng job — vòng
  đó chạy ở **mọi** tiến trình.
- **Đội hình worker khai bằng `LTT_WORKER_POOLS`** (vd `api:8, gpu+ffmpeg:2`).
  Không khai thì giữ nguyên hành vi cũ.
- **`test_214` là bằng chứng đa tiến trình.** Từ H36.9 nó đã vào gate qua
  `tools/check_multiproc.py` (tự tìm/tạo CSDL test). Vẫn nên chạy tay sau khi
  sửa bất cứ thứ gì trong worker hoặc outbox.

Điểm audit trung thực sau H36.9–12: **9,0/10**
(`docs/PUBLIC_API/AUDIT_API_2026-08-15.md` §4c). Việc duy nhất còn nợ của H36 là
chạy `test_221` trên một bucket R2 vứt đi — chặn bởi một quyết định hạ tầng,
không phải bởi code.

**ĐÃ DEPLOY 2026-08-17**, và **TẠM DỪNG có chủ ý** để chuyển sang LTT Nexus.
Đọc `docs/PUBLIC_API/TAM_DUNG_2026-08-17.md` trước khi mở lại — nó ghi mở lại
thì bắt đầu từ đâu và ba cái bẫy đã dính.

🔴 **SỬA 2026-08-26 — ĐOẠN NÀY TRƯỚC ĐÓ NÓI SAI, VÀ NÓI SAI VỀ PHÍA NGUY HIỂM.**

Nó từng viết *"hạ tầng đã sống, **cửa hàng chưa mở**… `LTT_PUBLIC_API_TOOLS`
**rỗng**"*. Đọc production ngày 26/08:

```
LTT_PUBLIC_API=1
LTT_PUBLIC_API_TOOLS=text.chat,image.ltt
```

**Hai tool đang mở và đang thu tiền thật.** Cùng tài liệu này, hàng H38 nói LLM
*"ĐANG BÁN 2026-08-24"* — tức hai câu trong **một** tệp mâu thuẫn nhau suốt hai
ngày.

⛔ Vì sao nó nguy hiểm chứ không chỉ sai: một phiên sau đọc đoạn này sẽ tin
`/api/v1` **không phục vụ ai**, rồi sửa nó **như sửa mã chết**. Nó đang phục vụ
khách trả tiền.

⭐ Và tool đã mở **không phải** `image.thumbnail` như kế hoạch từng ghi — thứ tự
mở cửa đã đổi trên thực tế mà kế hoạch không theo kịp.

🔴 **SỬA LẦN HAI 2026-08-30 — LẠI LỆCH, LẠI VỀ PHÍA NGUY HIỂM.**

Đoạn trên (bản 26/08) ghi *"hai tool mở"* và *"còn nợ H35.10 (tool video)"*.
Hỏi thẳng API đang chạy ngày 30/08 — `GET /api/v1/tools`, khoá thật, qua
Cloudflare — nó trả về **bốn**:

```
image.ltt        ASYNC_JOB
text.chat        ASYNC_JOB
video.subtitle   ASYNC_JOB   <- mo 29/08
video.upscale    ASYNC_JOB   <- mo 29/08
speech.ltt       ASYNC_JOB   <- mo truoc 01/09, hang nay KHONG theo kip
```

Tức **H35.10 đã đóng** và hai tool video đã bán, trong khi hàng này vẫn ghi là
nợ. `docs/PUBLIC_API/APP_API_COVERAGE_FINAL.md` **đã đúng** cả bốn từ 29/08 —
chỉ tệp này trôi.

⛔ Đây là **lần thứ hai** cùng một hàng nói sai theo cùng một hướng. Bài học
không phải "nhớ cập nhật", mà là: **đừng đọc con số ở đây, hỏi máy chủ.** Một
lệnh, mười giây, và nó không bao giờ trôi:

```powershell
Invoke-RestMethod https://app.lttstudios.com/api/v1/tools -Headers @{Authorization="Bearer $env:LTT_API_KEY"; "User-Agent"="ltt/1.0"} | ForEach-Object items | Select-Object name, execution_mode
```

⚠️ **Nhớ đặt `User-Agent` khi gọi bằng `urllib`** — nếu không Cloudflare trả
**403 `error code: 1010`**, trông y như khoá sai.

⭐ Nhưng nói cho đúng, vì bản đầu của cảnh báo này **không tái hiện được** và
một phiên khác đã bắt được điều đó: thứ bị chặn **không phải "thiếu UA"** mà là
**đúng chuỗi `Python-urllib/…` viết hoa chữ P** — tức chuỗi urllib tự điền. Đo
30/08, cùng khoá, cùng đường:

```
UA khong dat  (urllib tu dien "Python-urllib/3.13")  -> 403 CLOUDFLARE
UA "Python-urllib/3.13"  (dat tay, HOA chu P)        -> 403 CLOUDFLARE
UA "Python-urllib/2.7"   (phien ban khac)            -> 403 CLOUDFLARE
UA "python-urllib/3.13"  (thuong p)                  -> 200
UA "PYTHON-URLLIB/3.13"  (in hoa het)                -> 200
UA "Python-Requests/2.0" (client Python khac)        -> 200
UA ""  (chuoi RONG)                                  -> 200
UA "curl/8.0"                                        -> 200
```

⇒ Luật khớp **tiền tố chuỗi `Python-urllib/`, PHÂN BIỆT HOA-THƯỜNG**. Ba dòng
giữa loại đúng ba cách đọc sai: không phải "thiếu UA" (chuỗi rỗng qua), không
phải một phiên bản cụ thể (`2.7` cũng chặn), không phải mọi client Python
(`Python-Requests/` qua).

Đó cũng là lý do hai phiên đo ra kết quả trái ngược **trong cùng một ngày** và
cả hai đều đúng: một bên gõ `python-urllib` chữ thường, tức đo một chuỗi khác.

🔴 **Và đây không chỉ là bẫy cho ta — nó là một lỗ ở phía khách.** `urllib` là
thư viện chuẩn; ai viết mười dòng Python để thử API sẽ dùng nó, rồi nhận **403
của Cloudflare chứ không phải của ta**: không `request_id`, không dòng nào trong
`public_api_requests`, không tra được bằng `/admin/api-trace`. Nhìn y hệt khoá
sai, nên khách đi tạo khoá mới rồi vẫn 403 — **và ta không thấy gì cả.**
`KE_HOACH_TIEP` §1 hạ P3 xuống "nên có" vì đã sửa **ví dụ của ta**; việc đó cứu
người **chép ví dụ**, không cứu người **tự viết**.

⛔ Bài học chung, không riêng chỗ này: **một cảnh báo không tái hiện được sẽ bị
phiên sau bỏ qua — và kéo theo cả những cảnh báo đúng nằm cạnh nó.** Nên viết
lệnh tái hiện, đừng viết kết luận.

🔴 **SỬA LẦN BA 2026-09-01 — VÀ ĐÂY LÀ LẦN THỨ BA CÙNG MỘT HÀNG.**

Hỏi chính máy chủ ngày 01/09 qua Cloudflare bằng khoá thật: **NĂM** tool, không
phải bốn. `speech.ltt` (LTT VOICE) đã mở và hàng này không theo kịp.

⭐ Ba lần trôi, ba lần cùng một hướng, và lần này nó lộ ra **không phải vì ai đó
đọc lại tài liệu** mà vì một canary đi hỏi máy chủ. Đó là lý do lệnh ở trên đáng
giá hơn cả đoạn văn này: **đừng đọc con số ở đây, hỏi máy chủ.**

⚠️ Và con canary ấy suýt nói dối: `tools/api_prod_canary.py` đọc `data`/`tools`
trong khi API trả `items`, nên nó in *“(rỗng — đúng ý muốn khi
`LTT_PUBLIC_API_TOOLS` chưa đặt)”* — **một câu trả lời sai mặc một lời giải
thích nghe hợp lý**. Đã sửa: hình dạng lạ nay phải NÓI RA thay vì lặng lẽ
thành rỗng.

**Trạng thái đúng (đo 01/09):** khu API bật, **năm tool mở** — `text.chat`,
`image.ltt`, `video.upscale`, `video.subtitle`. Fail-closed của Q92 vẫn đúng
việc với mọi tool còn lại. Năm điều kiện §11 đã đóng; còn nợ: **xoay khoá
provider**.

**H37 (bắt đầu 2026-08-21, Q102)** — model tạo ảnh chạy trên **máy B**
(`MAY-B` 192.168.2.66, RTX 3090 24 GB, RAM 192 GB). Nó là **một provider**
(`ltt_image`), **không phải một app**: thêm một dòng vào `platform_core/providers.py`
+ adapter dùng chung `platform_core/image_gen/`. Kế hoạch 13 phase và cổng chấm
điểm ≥ 9/10 ở `docs/ANH_NOI_BO/KE_HOACH_THI_HANH.md`.

Sáu thứ phải biết trước khi đụng vào:

- 🔴 **ĐƯỜNG VÀO MÁY B: đọc `Ket_noi.md` trên Desktop TRƯỚC KHI TÌM CÁCH KHÁC.**
  Kênh chính là **LTT Nexus**, không phải SSH: gọi controller máy A rồi proxy sang
  `https://192.168.2.17:9444/api/v1/nodes/f8b24d88-6e3e-4719-8143-d5e83f68ed82/proxy/api/v1/<đường>`
  kèm `X-Nexus-Protocol: 1` + `Authorization: Bearer <token>`
  (token ở `%USERPROFILE%\.nexus\claude-code.token`). Có `command.run` và
  `file.write`, tức làm được mọi việc SSH làm — agent chạy bằng **LocalSystem**
  nên khởi động lại dịch vụ trên B được luôn.

  ⛔ **`sshd` trên máy B đang `Disabled` có chủ ý** (từ 27/08). Cổng 22 đóng
  **không phải** mạng hỏng. Ngày 31/08 tôi quét 22/2222/22022/8022, thử SMB, thử
  `sc.exe` từ xa rồi kết luận "không vào được máy B" — trong khi câu trả lời nằm
  sẵn trong `Ket_noi.md`, kể cả **lý do** cổng 22 đóng. Cần SSH cho một script
  chỉ chạy được qua nó (vd `llm_gateway/deploy/deploy.ps1`) thì bật tạm **bằng
  Nexus** rồi **đóng lại ngay sau khi xong**.

  ⭐ **`NODE_OFFLINE` ≠ máy tắt.** Ba mức khác nhau, sửa ở ba nơi: máy tắt · máy
  sống nhưng agent Nexus im · agent sống nhưng thiếu capability. Phân biệt bằng
  `ping` → cổng `8199/8299` → `health.state`. Chi tiết ở memory
  `may-b-duong-vao-va-du-phong`.

- ⚠️ **Máy B có thể tự khởi động lại để cập nhật Windows** (Active Hours 07:00 →
  01:00; đã xảy ra 22/08 lúc 01:29, sự kiện `1074`, cuốn theo một lô ở ảnh 21/30).
  ✅ **KHÔNG còn là hạn chót nữa.** Lô đo nay ghi kết quả **sau mỗi ảnh** và **bỏ qua
  ảnh đã xong** khi chạy lại, nên một lần khởi động lại chỉ mất **đúng một ảnh đang
  vẽ** — vài chục giây, không phải cả lô. Bằng chứng: `tests/test_266_tiep_tuc_lo_do.py`.
  ⇒ **Đừng lên lịch quanh mốc 01:00, và đừng nhắc lại nó như một điều kiêng kỵ.**
  Cũng **không cần** đổi `AUOptions` — đó là một thiết lập bảo mật, và cái giá của nó
  (máy tích luỹ bản vá chưa áp) lớn hơn thứ nó cứu.
  *(Tôi đã chẩn đoán nhầm vụ 22/08 thành "cạn VRAM" — xem D-025 để biết vì sao nhầm.)*
- ✅ **VRAM: cảnh báo "97,5 %" ĐÃ LỖI THỜI — đừng lên kế hoạch quanh nó (D-056).**
  Con số 23,9 / 24,6 GB đo **trước** khi ComfyUI chạy với `--reserve-vram 3`. Đo
  lại 24/08 trên cùng card: t2i 50 bước **18,45 GB** (lô 100 lượt, dao động chỉ
  163 MB), `edit` 1 ảnh @4 MP **19,83 GB**, `subject` 2 ảnh @4 MP **20,11 GB** —
  cấu hình **nặng nhất từng đo** nay là 20,1 GB, biên còn **~4,5 GB**.
  ComfyUI trên B **đã** chạy với `--reserve-vram 3` (`test_245` chốt cờ đó khớp
  `VRAM_CHUA_LAI_GB`, mất nó lặng lẽ là sập giữa một lô dài).
  ⚠️ Nhưng **đừng đọc ngược thành "thoải mái"**: 4,5 GB là biên **khi chỉ có ta**.
  Ba hộ vẫn dùng chung card (D-037) — dự án video từng ăn 98,7 %, `llama-server`
  giữ 15,9 GB. Chốt bận của cổng render vẫn là thứ giữ hai hộ không đè nhau.
- 🔴 **CHƯA ĐO THÌ KHÔNG CHẠY.** `render_gateway/ngan_sach.py` từ chối mọi cấu hình
  vượt `TOKEN_DA_DO_TOI_DA` **trước khi chạm GPU**. Trần nay là **11.412** (4.096 →
  7.506 → 11.412, mỗi lần nâng đều có số đo: D-032, D-053). Cả `edit` và `subject`
  ở `ref_mp=4.0` **đã đo xong và đã mở**; bậc kế tiếp (2 ảnh @8 MP = 19.224 token)
  vẫn bị chặn, có test riêng chốt.
  Muốn mở tiếp thì **đo theo bậc, có người canh** rồi ghi số vào `DECISIONS.md`.
  **Đừng hạ `ref_mp` cho lọt chốt** — đó chỉ là chọn một con số khác cũng chưa ai đo.
  ⚠️ Và biết một điều trái trực giác trước khi đọc trần này: **token là proxy rất
  lỏng cho VRAM** — token gấp 2,1 lần mà VRAM chỉ +1,8 % (D-053). Trần vẫn đúng
  việc (từ chối cấu hình chưa đo) nhưng **đừng đọc nó như thước đo mức nguy hiểm**.
- **Máy B KHÔNG giữ bí mật nào của nền tảng.** Không mật khẩu CSDL, không khoá R2,
  không `LTT_TOKEN_ENCRYPTION_KEY`. Ảnh vào bằng presigned GET, ra bằng presigned PUT.
- ⚠️ **ComfyUI trên máy B KHÔNG có xác thực.** Nó chỉ được nghe `127.0.0.1`, vĩnh
  viễn. Chỉ cổng render (:8199, bearer token) nghe LAN, tường lửa chỉ mở cho
  192.168.2.17. **Không bao giờ** đưa ra Cloudflare.
- 🔴 **MÁY B CÓ BA HỘ DÙNG CHUNG GPU, không phải hai** *(đo 22/08 22:27)*:
  ① **video** — `E:\LTT AI`, dùng chung đúng ComfyUI đó; một lượt từng chạy 72,5
  phút và ăn 98,7 % VRAM. ② **LLM** — `H:\LTT_LLM`, dịch vụ `LTTLlamaSwap` +
  `LTTLlmGateway` (cổng 8280/8299); `llama-server.exe` nạp một model 27B giữ
  **15,9 GB** và **ngồi im ở đó**, GPU 0 % tải, tự nhả sau `ttl: 1800`. ③ ta.
  Job ảnh **không xếp hàng sau ai cả** — bận thì cascade sang Gemini.
  ⚠️ Hộ ② **không phải tiến trình python**, và điều đó từng làm chốt dò bận của
  cổng render báo *rảnh* trong khi card chỉ còn 4,6 GB — xem D-037.
- **Bận ≠ hỏng.** Khi B bận, tuyệt đối **không** gọi `api_pool.danh_dau_loi()` cho
  key `ltt_image`: cooldown rồi `disable` sau 5 lần, và một tối chạy video sẽ tự
  tắt vĩnh viễn model nhà.

