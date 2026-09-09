# KẾ HOẠCH TRIỂN KHAI — LTT VPS V2 (mục tiêu >98/100)

> ✅ **ĐÃ THỰC HIỆN XONG — 2026-09-09.** Cả 12 pha đã chạy, commit `5bb3a5a0`,
> đã hoà vào trunk `admin-mvp-v3` và đã deploy lên production.
>
> Tệp này **giữ nguyên dạng tiền-bay** thay vì viết lại thành hồi ký: giá trị của
> nó là ở chỗ nó ghi lại *điều đã dự đoán trước khi làm*, và mục §10 mới ở cuối
> đối chiếu từng dự đoán với kết cục. Một kế hoạch được sửa cho khớp kết quả thì
> không còn nói được nó đã đúng hay sai ở đâu.
>
> Kết quả và bằng chứng: `FINAL_AUDIT.md` · `RELEASE_SCORECARD.md` ·
> `KNOWN_BLOCKERS.md` · `STATE.md`.

---

> **Tài liệu này là bản kế hoạch TIỀN-BAY.** Nó được viết sau khi đọc toàn bộ pack
> `G:\My Drive\AI\A\LTT_VPS_V2_ONE_SESSION_PROMPT_PACK` và **đối chiếu với HEAD thật**
> của kho, trước khi gửi bootstrap prompt.
>
> Nó **không** thay thế `docs/vps_v2/STATE.md` — tệp đó do Prompt 00 của chương trình
> tạo và là SSOT trong lúc chạy. Tệp này trả lời câu hỏi khác: *chương trình đó có
> chạy được trên kho này không, phải chốt gì trước, và thật sự sẽ tốn gì.*

- Nguồn pack: `G:\My Drive\AI\A\LTT_VPS_V2_ONE_SESSION_PROMPT_PACK` (22 tệp, entrypoint `START_HERE.md`)
- Ngày soạn: 09/09/2026
- Cây làm việc: `.claude/worktrees/ltt-vps-v2-deployment-plan-2cfc36`, nhánh `claude/ltt-vps-v2-deployment-plan-2cfc36`
- HEAD lúc soạn: `05464239` · `master`: `9e73bf1f` (HEAD đi trước master **288** commit, master là tổ tiên)

---

## 1. Pack yêu cầu gì — mười dòng

| | |
|---|---|
| Cấu trúc | 12 pha tuần tự `00 → 11`, chạy trong **một phiên**, tự chuyển pha, không hỏi xác nhận giữa các pha |
| Luật cứng | **CODE TRƯỚC, FULL GATE CUỐI** — cấm mọi full gate/pytest toàn kho/commit/push trước Prompt 11 |
| Bộ nhớ | `docs/vps_v2/STATE.md` là SSOT; filesystem là bộ nhớ dài hạn qua compaction; **không** dùng lịch sử chat |
| Phạm vi | `apps/vps/**` + thứ VPS thật sự cần; shared code chỉ khi chứng minh được call path |
| Chấm điểm | Tách **ba** cột: SOFTWARE/CONTROL-PLANE · LIVE INFRA/RESILIENCE · END-TO-END. Không được lấy trung bình để giấu chỗ thiếu bằng chứng |
| Trần cứng | P0 ⇒ ≤60 · P1 ⇒ ≤85 · không có test async failure ⇒ ≤92 · chỉ test thứ tự gọi hàm ⇒ ≤90 · **ảnh chụp cùng kho mà gọi là "chống thảm hoạ" ⇒ ≤50** |
| An toàn | Không `reset --hard`, không `clean -fdx`, không force push, không đè việc phiên khác |
| Live | Chỉ thao tác phá huỷ trên VM thử rõ ràng; thiếu thì ghi `LIVE ACCEPTANCE BLOCKED` và **hạ trần điểm**, không giả PASS |
| Triết lý test | Cấm test kiểu "assert `tat_cung` xuất hiện trước `khoi_phuc_anh`". Phải có fake Proxmox **có trạng thái** chuyển RUNNING → STOPPING → STOPPED |
| Nhãn | Chỉ đổi `lifecycle="development"` → `released` khi bằng chứng thật sự đủ |

---

## 2. Đối chiếu với HEAD THẬT — bảy phát hiện

Pack ghi nó quan sát một snapshot `master` bắt đầu bằng `9e73bf1f...`. **Đo được:**
`master` hiện đúng là `9e73bf1f402c26525f1643761652cd5346359a9c`, và
`git diff 9e73bf1f..HEAD -- apps/vps` **rỗng** — 288 commit của nhánh này không chạm
một dòng nào trong `apps/vps`. Nghĩa là mọi giả thuyết của pack còn nguyên vẹn trên HEAD.

Tôi đã kiểm từng cái bằng mã nguồn, không bằng bảng chép tay:

| ID | Phát hiện | Trên HEAD | Bằng chứng | Mức |
|---|---|---|---|---|
| **V-01** | `khoi_dong_lai()` chỉ **tắt**, không bật lại | ✅ CÒN | `apps/vps/services/dieu_khien.py:91-99` — thân hàm là `return tat(db, may, client, boi=boi)` | **P0** |
| **V-02** | Ghi trạng thái ổn định ngay sau khi Proxmox **nhận** lệnh | ✅ CÒN | `dieu_khien.py:67` — `may.trang_thai = trang_thai_moi` chạy ngay sau `goi()` trả UPID, không chờ tác vụ | **P0** |
| **V-03** | Ảnh chụp: tạo rồi **list/prune ngay**, chưa chờ tác vụ xong | ✅ CÒN | `services/sao_luu.py:122-131` — `chup_anh()` rồi `danh_sach_anh()` + `xoa_anh()` liền; và `bao_tri.py:208-213` ghi `sao_luu_luc` cho một ảnh **chưa xác minh tồn tại** | **P0** |
| **V-04** | Khôi phục: gửi `tat_cung` rồi rollback ngay, chưa chờ máy thật sự STOPPED | ✅ CÒN | `routes.py:620-630` — `client.tat_cung(...)` trong `try/except ProxmoxError: pass` rồi `client.khoi_phuc_anh(...)` dòng kế | **P0** |
| **V-05** | Một chuỗi `trang_thai` gánh cả năm khái niệm | ✅ CÒN | `tables.py:186` — `String(16)`, giá trị trộn lẫn `dang_tao`/`dang_chay`/`da_tat`/`bi_treo`/`loi`/`da_xoa`: vòng đời + điện + treo-vì-tiền cùng một cột | **P1** (kiến trúc) |
| **V-06** | `lifecycle="development"`, Proxmox chạy **lồng** | ✅ CÒN — và **đúng sự thật** | `manifest.py` — `lifecycle="development"`, `notes="Proxmox chạy LỒNG trong VMware trên máy B"` | không phải lỗi |
| **V-07** | 🆕 **Không có trong pack.** Bốn route điều khiển chạy **thẳng**, không đi qua khoá per-instance | ✅ CÒN | `jobs.py:_khoa_may` giữ lease `vps-may:{id}` — nhưng **chỉ bọc handler của job**. `routes.py:462,469,476,586` (`bat`/`tat`/`khoi-dong-lai`/`khoi-phuc`) gọi thẳng service, không xin lease. Khách bấm "Khôi phục" đúng lúc job `vps.rebuild` đang chạy ⇒ hai bên cùng đụng một VM | **P0** |

### Một phát hiện của pack **đã đạt** — đừng "sửa lại"

Pack liệt kê *"ảnh chụp LVM-thin cùng pool được mô tả đúng là quick rollback, không phải
off-host backup"*. Kiểm: `services/sao_luu.py` (docstring đầu tệp) và `proxmox.py:330-343`
đã nói thẳng *"Ảnh chụp KHÔNG phải bản sao lưu… pool hỏng là mất cả hai"*, kèm cả một
phép đo thật ngày 24/08 về giới hạn crash-consistent. **Đây là điểm tốt sẵn có.**
Luật §1 của pack (*"actual HEAD wins"*) áp đúng vào đây: không được sửa ngược theo snapshot.

### Vốn liếng sẵn có — chương trình phải TÁI DÙNG, không dựng lại

| Có sẵn | Ở đâu | Pha nào cần |
|---|---|---|
| Hàng đợi job bền (progress, retry, `mark_ambiguous`, `reclaim_orphans`) | `platform_core/jobs.py` | 02, 03, 04 |
| Lease singleton có TTL + reclaim | `platform_core/leases.py` | 02, 03, 05 |
| Khoá per-instance (đã dùng đúng cách trong job) | `apps/vps/jobs.py:_khoa_may` | 02, 03 |
| Vòng chờ UPID có timeout + kiểm `exitstatus` | `apps/vps/jobs.py:_cho_tac_vu` (dòng 152) — **nhưng chỉ job dùng được** | 02 (nâng thành canonical) |
| Đối chiếu trạng thái | `apps/vps/doi_chieu.py` — `quet()`, `LechLac`, `KetQua` | 05 |
| Quan trắc / đo job | `platform_core/observability.py`, `job_metrics.py`, `job_events.py` | 08 |
| Vé console dùng-một-lần, băm khi lưu | `services/console.py`, `tables.py:VpsConsoleVe` | 07 |
| Ràng buộc duy nhất chống cấp trùng IP/VMID | `tables.py:__table_args__` | 05 |
| 18 tệp test VPS | `tests/test_251,252,279,280,282,286,287,288,289,293,295,296,297,298,304,305,311,312` | 00, 11 |
| 7 template + thư mục static | `server/templates/vps*.html`, `server/static/vps/` | 09 |
| 10 migration VPS đã có | `alembic/versions/20260822..20260824_2500` | 01 |

---

## 3. Năm xung đột giữa pack và hợp đồng vận hành LTT — và cách hoà

Pack tự xếp mình **trên** `CLAUDE.md` trong thứ tự thẩm quyền (§1). Nhưng nó được soạn
mà không biết bốn luật vận hành của máy này. Phải hoà trước, không phải lúc đang chạy.

| # | Pack nói | Kho nói | Hoà thế nào |
|---|---|---|---|
| **X-1** | Cấm **mọi** gate trước Prompt 11 | `docs/00_LTT_OPERATING_CONTRACT.md` §4.1: vòng lặp mặc định là **L1 `gate --doi`** | **Không mâu thuẫn thật.** Pack cấm *full repository gate* (= L3). L1 chạy test **chạm tới thứ vừa sửa**, đúng nghĩa "targeted" mà pack cho phép. ⇒ **Mỗi pha đóng bằng một lượt L1**; L3 **chỉ** ở Prompt 11. Ghi rõ điều này vào STATE để pha sau không hiểu ngược |
| **X-2** | Một commit duy nhất, ở cuối, sau khi L3 xanh | Hợp đồng §7 + kinh nghiệm: **compaction sẽ xảy ra nhiều lần** trong 12 pha | Nhánh này là **nhánh riêng**, không phải `master` ⇒ commit theo pha ở đây **không** "xuất bản" gì cho ai. Khuyến nghị **D-2**: commit sau mỗi pha trên nhánh riêng (bảo hiểm chống mất việc), squash lúc merge. Giữ đúng chữ của pack = chấp nhận rủi ro mất 10 pha việc vì một sự cố |
| **X-3** | Không biết máy chỉ có **10 lõi vật lý** dùng chung nhiều phiên | `CLAUDE.md` toàn cục: trước mọi lệnh nặng phải `python tools\cua_so_yen.py trang-thai`, trần `-n 6` | Prompt 11 (L3, trung vị **11,4 phút**) và mọi lượt L1 lớn phải xin cửa sổ yên **trước**, và kiểm cây tiến trình chứ không chỉ tin `cua_so_yen`. Thêm bước này vào checklist P11 |
| **X-4** | Không cấp dải số test | Kho có luật cấp dải cho từng chương trình | Đo được: **550–599 và 650–699 hoàn toàn trống** (554 tệp test hiện có). Khuyến nghị **D-3**: cấp **550–599** cho VPS V2. Test VPS cũ nằm rải ở 251/252/279–312 — **giữ nguyên**, không đánh số lại |
| **X-5** | — | `CLAUDE.md`: *"chưa có khách ở lớp Agent/Canvas ⇒ sửa thẳng"* | ⛔ **Quyền đó KHÔNG áp cho VPS.** VPS có hạ tầng thật, IP Vultr trả tiền thật (17 instance, ~$210/tháng), `credit_entries` thật. Ở đây lý do cẩn thận là **tính đúng của sổ sách** và **tài nguyên trả tiền**, đúng như chính `CLAUDE.md` đã tự giới hạn |

---

## 4. Sáu quyết định phải chốt TRƯỚC khi bấm nút

Năm trong sáu cái này **quyết định trần điểm cuối cùng**. Chốt sau là chốt muộn.

| ID | Câu hỏi | Khuyến nghị | Hệ quả nếu chọn khác |
|---|---|---|---|
| **D-1** | Đặt pack ở đâu? README bảo giải nén vào `<repo>/prompt_packs/` | **Để NGUYÊN ngoài kho**, bootstrap trỏ đường dẫn tuyệt đối `G:\My Drive\...` | Thêm 22 tệp `.md` vào kho làm động các bánh cóc đếm nội dung/tài liệu và `test_147_layering`; và pack là *instruction*, không phải mã sản phẩm |
| **D-2** | Commit theo pha, hay một commit cuối? | **Theo pha, trên nhánh riêng**; squash khi merge | Đúng chữ pack = 12 pha việc sống trong một cây chưa commit qua nhiều lần compaction |
| **D-3** | Dải test cho VPS V2 | **550–599** | Đè lên dải của chương trình khác ⇒ va chạm khi hai nhánh hoà |
| **D-4** | **Có VM thử để nghiệm thu live không?** | Phải trả lời trước P00 | Không có ⇒ mục 6 của Prompt 11 = `LIVE ACCEPTANCE BLOCKED` **ngay từ đầu**, và điểm END-TO-END bị chặn trần. Lưu ý máy B chỉ có **một suất đồng thời** (`DONG_THOI_MAY_B=1`) |
| **D-5** | **Có PBS / kho sao lưu độc lập không?** | Nhiều khả năng **KHÔNG** | Không có ⇒ Prompt 06 chỉ ra được *CODE READY / INFRA BLOCKED*, và theo chính scorecard: **Backup/DR ≤ 50**. Đây là trần **không thể** gỡ bằng mã |
| **D-6** | Có CA/fingerprint cho Proxmox không? | Chuẩn bị **trước** P07 | P07 đòi production **fail-closed** thay cho `verify=False` (`proxmox.py:87-99`). Bật fail-closed mà chưa có CA = **VPS ngừng hoạt động ngay**. Phải: (a) sinh/ghim CA trước, hoặc (b) cờ dev tường minh + readiness check đỏ ở production |

---

## 5. Kế hoạch từng pha

Ký hiệu cấp gate: **L0** `--quick` · **L1** `--doi` · **L2** `--pham-vi` · **L3** đầy đủ.
Ước lượng là *thời gian làm việc của mô hình*, không phải giờ đồng hồ của người.

### Pha 00 — Bootstrap & baseline đóng băng · không sửa mã

- **Làm:** xác nhận branch/HEAD/status; kiểm 7 phát hiện ở §2 **lại một lần nữa trên cây đang đứng**; lập bản đồ 28 tệp `apps/vps` + 7 template + 18 tệp test + 10 migration; truy vết 12 luồng (tạo → bật → tắt → khởi động lại → chụp → khôi phục → cài lại → xoá → treo/gia hạn/xoá quá hạn → mạng/DHCP/NAT/IP công khai → console → đối chiếu).
- **Ra:** `docs/vps_v2/STATE.md`, `BASELINE.md`, `ADR_INDEX.md`.
- **Gate:** không chạy gì. Chỉ lệnh đọc.
- **Bẫy:** đừng đọc cả kho — `docs/` có 872 tệp `.md`. Đi theo bản đồ ở §2, không quét mù.

### Pha 01 — Mô hình trạng thái & schema

- **Làm:** tách `trang_thai` (một chuỗi 16 ký tự) thành các khái niệm độc lập: vòng đời nghiệp vụ · điện **mong muốn** · điện **quan sát được** · tác vụ đang chạy · sức khoẻ/độ tươi (`quan_sat_luc`).
- **Bắt buộc biểu diễn được:** *nghiệp vụ đang hoạt động · mong muốn = tắt · quan sát = đang chạy · tác vụ = đang tắt* — bốn thứ cùng lúc, không mâu thuẫn.
- **Tương thích:** `trang_thai` **giữ nguyên** làm cột chiếu (projection) — 18 tệp test, 7 template và `routes.py` đang đọc nó. Đây là ADR-01, không phải nợ kỹ thuật.
- **Chạm:** `apps/vps/tables.py`, migration mới (sau head `20260908_1600_voice_license_va_curate`), `services/*` đủ để mạch cũ không gãy.
- **Test:** 550–553 — hàng cũ `dang_chay`/`da_tat` nâng cấp đúng; hàng `bi_treo` giữ nguyên nghĩa **tài chính**; hàng `da_xoa` không bao giờ hiện "đang chạy"; quan sát **unknown** **không** được biến thành `stopped`.
- **Gate:** L1. Migration ⇒ bán kính **NGHIÊM TRỌNG** ⇒ thêm L2 ở cuối pha.
- **Bẫy:** `bi_treo` là trạng thái **TIỀN**, không phải trạng thái điện. Gộp nhầm hai thứ này là tái tạo đúng lỗi đang sửa.

### Pha 02 — Động cơ thao tác & bộ theo dõi tác vụ Proxmox

- **Phần A — bản ghi thao tác bền.** Bảng `vps_thao_tac`: id · instance · loại · người yêu cầu · khoá idempotency · trạng thái (`cho`/`dang_chay`/`xong`/`hong`/`qua_han`/`huy`) · UPID · số lần thử · mốc thời gian + hạn chót · lỗi có cấu trúc · bước con.
  **Vì sao không tái dùng `Job`:** `Job` là *một lượt việc của worker*; thao tác là *một mutation trên một máy*, có thể do route khởi xướng. Hai vòng đời khác nhau. Nhưng thao tác **chạy bằng** job và **khoá bằng** lease — không dựng khung công việc thứ hai (ADR-02).
- **Phần B — bộ chờ UPID canonical.** Nâng `jobs.py:_cho_tac_vu` (dòng 152) thành `apps/vps/services/tac_vu.py`: chờ có chặn thời gian, phát hiện terminal, kiểm `exitstatus == OK`, **và xác minh trạng thái VM thật sự đạt kỳ vọng**. Chỉ thử lại GET, **không bao giờ** thử lại POST.
- **Phần C — đồng thời.** Kéo lease `vps-may:{id}` lên **trước** route (sửa **V-07**), không chỉ trong job.
- **Test:** 554–559, dùng **fake Proxmox có trạng thái** — task chạy→OK · task lỗi · timeout · endpoint status hỏng tạm thời · request trùng · tiến trình khởi động lại giữa chừng · **task báo OK nhưng VM không tới trạng thái kỳ vọng**.
- **Gate:** L1 + L2.

### Pha 03 — Vòng đời đúng sự thật · **pha nặng nhất**

- **Sửa V-01:** khởi động lại thật = tắt mềm → chờ tác vụ → **xác minh STOPPED** → bật → chờ → **xác minh RUNNING**. Hết hạn chờ ⇒ trả trạng thái hỏng/suy giảm **có hành động tiếp theo**, tuyệt đối không nói "đã khởi động lại".
- **Sửa V-02:** DB chỉ ghi kết quả ổn định **sau** xác minh; trong lúc chạy chỉ có `tac_vu` + `dien_mong_muon`.
- **⚠️ Hệ quả kiến trúc — thứ đắt nhất của cả chương trình.** Chú thích đầu `dieu_khien.py` nói ba thao tác này *"không đi qua hàng đợi job"* vì chỉ tốn 200 ms. Điều đó **đúng với hành vi sai hiện tại** (bắn rồi quên). Một lần khởi động lại **thật** của Windows là hàng chục giây tới vài phút, mà Cloudflare cắt ở **100 giây** (`CLAUDE.md` luật 19). ⇒ `bat`/`tat`/`khoi_dong_lai`/`khoi_phuc` **phải** chuyển sang hàng đợi job. Thêm `vps.control` vào `manifest.job_types` + `max_runtime_s`. Route trả về **ngay** với id thao tác, UI hiện "Đang khởi động lại…". Chú thích cũ phải viết lại — nếu không nó sẽ nói dối phiên sau.
- **Cài lại / Xoá:** truy vết dọn dẹp — VM · NAT/DHCP trên router · IP công khai Vultr · sổ sách. Dọn dẹp hỏng một phần ⇒ ghi **nợ dọn dẹp có thể thử lại**, không xoá bằng chứng.
- **Test:** 560–569 — bật/tắt trễ, thành công và thất bại; khởi động lại **kết thúc ở RUNNING**; khởi động lại **không bao giờ** gọi start trước khi quan sát được STOPPED; bấm hai lần; cài lại gặp sự cố rồi thử lại; xoá dọn dẹp nửa chừng; máy `bi_treo` không tự bật được; máy `dang_tao` không nhận lệnh xung đột.
- **Gate:** L1 mỗi changeset nguyên tử + L2 cuối pha.

### Pha 04 — Ảnh chụp & khôi phục

- **Sửa V-03:** chụp → lưu UPID → **chờ terminal OK** → **xác minh ảnh tồn tại đúng tên** → ghi `sao_luu_luc` → **rồi mới** dọn ảnh cũ. Dọn hỏng = cảnh báo dọn dẹp, **không** phải chụp hỏng. Chụp hỏng **không bao giờ** được xoá bản tốt trước đó. Giữ nguyên luật "chỉ dọn ảnh mang tiền tố `ltt`" (`sao_luu.py:cua_ta`) — nó đã đúng.
- **Sửa V-04:** khôi phục → kiểm quyền sở hữu + đúng tên ảnh → xác nhận phá huỷ → khoá độc quyền → ghi lại trạng thái điện trước đó → tắt → **chờ + xác minh STOPPED** → rollback → **chờ UPID** → xác minh → chỉ khi đó mới ghi thành công. Bỏ `except ProxmoxError: pass` ở `routes.py:626` — nuốt lỗi tắt máy rồi rollback là đường ngắn nhất tới hỏng đĩa.
- **Phục hồi khi hỏng:** định nghĩa hành vi cho tắt-xong-rollback-hỏng · rollback-xong-bật-hỏng · task timeout **rồi sau đó thành công** · tiến trình chết sau khi Proxmox xong nhưng trước khi commit DB · ảnh biến mất.
- **Giữ nguyên:** cách mô tả "ảnh chụp ≠ sao lưu" ở docstring và trang bán — đã đúng.
- **Test:** 570–579, chuyển trạng thái **bất đồng bộ** trong fake. Test so sánh thứ tự gọi hàm **không được tính**.
- **Gate:** L1 + L2.

### Pha 05 — Đối chiếu · mạng · sổ sách

- **Đối chiếu V2:** nâng `doi_chieu.py` để so DB ↔ Proxmox ↔ router (DHCP/NAT/hãm tốc) ↔ gateway ↔ IP Vultr ↔ treo/ân hạn, và **phân loại** thành `SAFE_AUTO_HEAL` / `RETRYABLE_OPERATION` / `OPERATOR_REQUIRED` / `ORPHAN_SUSPECTED` / `FATAL_INVARIANT`. ⛔ Không bao giờ tự xoá một "mồ côi" mơ hồ chỉ để DB khớp.
- **Mạng:** cấp IP riêng duy nhất dưới đồng thời (ràng buộc `uq_vps_instance_ip` đã có — thêm test chứng minh) · router khởi động lại dựng lại được runtime set · IP công khai đặt chỗ xong mà DB hỏng ⇒ phải dọn ở nhà cung cấp.
- **Sổ sách:** thu đúng một lần mỗi chu kỳ · `paid_until` đơn điệu · thiếu credit ⇒ treo · ân hạn ⇒ xoá · thử lại **không** trừ/hoàn hai lần · băng thông chụp mốc rồi reset đúng thứ tự (`bang_thong.py` đã xử số âm khi router reboot — giữ).
- **Test:** 580–589, tiêm lỗi: DB commit hỏng sau khi nhà cung cấp đã cấp IP · hai vòng bảo trì chạy song song · hai job cấp phát song song · máy đang chạy thật trong khi sổ sách ghi treo.
- **Gate:** L1 + L2 (chạm tiền ⇒ bán kính NGHIÊM TRỌNG).

### Pha 06 — Sao lưu & thảm hoạ · **gần như chắc chắn INFRA BLOCKED**

- **Sự thật hạ tầng:** kho `dir` duy nhất trên node (`local`) còn **2,2 GiB** — không đủ cho `vzdump` một máy. Chưa có PBS (chờ **D-5**).
- **Vẫn làm được, và vẫn có giá trị:** hợp đồng năng lực (`local_snapshot` / `independent_backup` / sức khoẻ đích / lần sao lưu cuối / retention / lần xác minh cuối) · ranh giới adapter + cấu hình · **UI nói đúng sự thật**: tính năng **disabled**, không phải một cái nhãn xanh giả.
- **Kết luận bắt buộc:** `CODE READY / INFRA BLOCKED`. Theo chính scorecard của pack, **Backup/DR ≤ 50** chừng nào chỉ có ảnh chụp cùng pool. Không có dòng mã nào gỡ được trần này.
- **Test:** 590–594 — thiếu cấu hình PBS thì **fail closed** · bí mật không lọt vào log/sự kiện · ảnh chụp vẫn dùng được độc lập với cờ tính năng sao lưu.
- **Gate:** L1.

### Pha 07 — Bảo mật · lạm dụng · TLS

- **TLS quản trị:** `proxmox.py:87-99` hiện trả `verify=False` kèm một cảnh báo. Production phải **fail-closed** + kiểm tra sẵn sàng. ⚠️ Xem **D-6** — bật cái này mà chưa có CA là **tự tắt dịch vụ VPS**.
- **Giữ và kiểm lại** (đang tốt): kiểm quyền sở hữu ở route · phản hồi không liệt kê tài nguyên người khác · CSRF · vé console dùng-một-lần băm khi lưu, tiêu thụ nguyên tử · xác nhận gõ tên máy cho thao tác phá huỷ.
- **Thêm:** chặn SMTP/25 ra ngoài theo mặc định (quyết định kinh doanh — hỏi trước khi bật) · trạng thái **cách ly** tách khỏi **xoá** + đường gỡ cách ly cho vận hành · chống giả mạo MAC/IP ở mức PVE/router **thật sự cưỡng chế được** (không vẽ nút cho luật không tồn tại).
- **Test:** 595–599 — IDOR · CSRF · phát lại vé · vé hết hạn · tiêu thụ đồng thời · lọc bí mật · thiếu CA ⇒ readiness đỏ.
- **Gate:** L1 + L2.

### Pha 08 — Quan trắc · cảnh báo · sức khoẻ

- Tái dùng `platform_core/observability.py` + `job_metrics.py` — **không** dựng vũ trụ đo lường thứ hai (luật §L của pack).
- Phân biệt **healthy / degraded / unreachable / stale-unknown** theo `quan_sat_luc`. ⛔ Không tái dùng `da_tat` để nghĩa "không liên lạc được" — đó chính là **V-05** đội lốt mới.
- Cảnh báo có khử trùng lặp: PVE không tới được · kho đầy · sao lưu quá hạn · task timeout · rò IP · bảo trì thu tiền hỏng · đối chiếu router hỏng.
- **Test:** 600–604 (dải 600–649 đã có 31 tệp — dùng số còn trống trong 550–599 nếu va chạm).
- **Gate:** L1.

### Pha 09 — Sản phẩm · GUI · API

- 7 template + `server/static/vps/` phải phản ánh mô hình mới: *đang bật / đang tắt / đang khởi động lại / đang khôi phục*, trạng thái **không rõ**, lỗi **có việc để làm tiếp**, lịch sử thao tác.
- ⛔ **Không vẽ năng lực không có**: PBS, IPv6, rDNS, HA — cờ năng lực + trạng thái "chưa hỗ trợ", không phải huy hiệu giả.
- API công khai: mở rộng quy ước sẵn có (`platform_core/public_api/`), **không** đẻ quy ước thứ hai. Thao tác mutating trả **id thao tác + trạng thái**, không trả "thành công" giả.
- **⚠️ Bắt buộc theo `CLAUDE.md` luật 17 + chính sách trình duyệt toàn cục:** kiểm bằng trình duyệt thật sau mỗi thay đổi giao diện, và chốt trên **URL công khai** `https://app.lttstudios.com`, không chỉ `127.0.0.1:8100`. Nối vào Chrome thật (`--cdp`) — Playwright tự mở Chrome sẽ dính CAPTCHA của Cloudflare.
- **Cache-bust:** đổi CSS/JS phải đính `?v={{ asset_ver }}` (`server/templating.py:ASSET_VER`), luật 18.
- **Gate:** L1 + kiểm trình duyệt cục bộ. Đây **chưa** phải nghiệm thu trình duyệt cuối.

### Pha 10 — Quét khuyết tật tích hợp · vẫn chưa full gate

- Đọc lại STATE (không quét mù cả kho), truy vết **17 mạch** mà pack liệt kê xuyên qua mọi thay đổi của pha 01–09.
- Săn bốn khuôn hỏng: ghi DB thành công ngay sau POST · `sleep()` dùng thay cho tính đúng · nuốt ngoại lệ che lỗi tiền/dữ liệu · test so thứ tự gọi hàm giả vờ chứng minh hành vi bất đồng bộ.
- Rà lại ranh giới giao dịch: bên ngoài thành công → DB hỏng · DB đặt chỗ → bên ngoài hỏng · worker khởi động lại · bấm hai lần.
- **Ra:** `IMPLEMENTATION_COMPLETE = YES` trong STATE, kèm danh sách chưa xong và **tách riêng** thứ nào là chặn hạ tầng thật.
- **Gate:** chỉ test hẹp.

### Pha 11 — Full gate · red team · phán quyết phát hành

Đây là pha **duy nhất** được chạy L3.

1. **Trước gate:** kiểm `git status` — dòng `??` lạ là **phiên khác đang làm việc**, không phải rác. `ListAgents` + hỏi trước.
2. **Xin cửa sổ yên:** `python tools\cua_so_yen.py trang-thai`, **và** nhìn cây tiến trình. Trần `-n 6`.
3. **L3:** `python tools\gate.py` (trung vị ~11,4 phút). Mỗi lỗi: phân loại có-sẵn / do-mình-gây; **không miễn trừ** lỗi do mình; ⛔ không xoá/làm yếu test để gate xanh.
4. **Red team** theo danh sách mục 4 của Prompt 11.
5. **Nghiệm thu trình duyệt** trên URL công khai, desktop + mobile, VI + EN.
6. **Nghiệm thu live** — chỉ trên VM thử (xem **D-4**). Thiếu ⇒ `LIVE ACCEPTANCE BLOCKED` kèm đúng thứ còn thiếu.
7. **Chấm điểm ba cột** + `FINAL_AUDIT.md`, `RELEASE_SCORECARD.md`, `KNOWN_BLOCKERS.md`.
8. **Commit + push** nhánh riêng. Không force push. Push hỏng ⇒ ghi `PUSH BLOCKED`, không giả thành công.

---

## 6. Trần điểm dự kiến — nói trước cho thật thà

Đây là ước lượng **theo chính scorecard của pack**, để không ai chờ ba con 98.

| Cột | Dự kiến | Vì sao |
|---|---:|---|
| **SOFTWARE / CONTROL PLANE** | **92 – 97** khả thi | Đạt >98 đòi *"integrated gate green"* **và** đủ bằng chứng E2E. Bảy phát hiện đều sửa được bằng mã; phần bị chặn là bằng chứng, không phải mã |
| **LIVE INFRA / RESILIENCE** | **40 – 60** | Một host PVE **lồng trong VMware**, không cụm, không HA, không PBS, kho `local` còn 2,2 GiB. Mã không biến một host lồng thành HA — pack nói thẳng điều đó |
| **END-TO-END PRODUCT** | **không thể > 98** với hạ tầng hôm nay | Bị kéo xuống bởi Backup/DR ≤ 50 và LIVE ACCEPTANCE nếu bị chặn |

Muốn cột hai và ba lên: đó là việc **mua và dựng** (đích sao lưu độc lập, host thứ hai, UPS), không phải việc viết mã. Nên tách bạch từ đầu.

---

## 7. Điểm dừng bắt buộc — chương trình phải hỏi người, không tự quyết

Pack nói "không hỏi xác nhận cho technical decision thông thường". Bốn thứ dưới đây
**không** phải technical decision thông thường:

1. **Bật fail-closed TLS ở production** (D-6) — có thể làm VPS ngừng phục vụ ngay.
2. **Chặn SMTP/25 mặc định** — quyết định kinh doanh, không phải kỹ thuật.
3. **Bất kỳ thao tác phá huỷ nào chạm VM/IP/snapshot** không chứng minh được là tài nguyên thử của chương trình.
4. **Deploy** — deploy chép **cả cây**, không tách được phần của một phiên (`CLAUDE.md` luật 15).

Và một điều kiện cơ học: mọi lệnh cần UAC vẫn cần người bấm chuột.

---

## 8. Lệnh khởi động

Sau khi chốt xong D-1 → D-6, gửi đúng một câu (giả định D-1 = để pack ngoài kho):

```bash
echo 'Doc day du G:\My Drive\AI\A\LTT_VPS_V2_ONE_SESSION_PROMPT_PACK\START_HERE.md va thuc hien CHINH XAC toan bo quy trinh trong do. Doc them docs/vps_v2/KE_HOACH_TRIEN_KHAI.md truoc Prompt 00.'
```

Trong đó `docs/vps_v2/KE_HOACH_TRIEN_KHAI.md` (tệp này) mang sáu quyết định đã chốt và
bảy phát hiện đã kiểm — nhờ đó Prompt 00 **xác minh lại** thay vì khám phá từ số 0.

---

## 9. Việc tệp này KHÔNG trả lời

- **Nó chưa chạy một dòng mã nào.** Bảy phát hiện ở §2 được kiểm bằng **đọc mã**, không bằng thi hành. Prompt 00 vẫn phải kiểm lại theo cách của nó.
- **Nó không biết trạng thái hạ tầng live hôm nay.** D-4/D-5/D-6 là câu hỏi cho máy chủ và cho chủ dự án, không phải cho kho mã. `python tools\api_prod_canary.py trang-thai` trả lời được phần *đang sống*; PBS/CA/VM thử thì phải hỏi người.
- **Ước lượng điểm ở §6 là ước lượng.** Con số thật do Prompt 11 chấm với bằng chứng thật.

---

## 10. Đối chiếu: kế hoạch đã dự đoán gì, và thực tế ra sao

Viết 09/09/2026 sau khi chạy xong. Mục này **không sửa** chín mục trên — giá trị
của một kế hoạch nằm ở chỗ nó nói trước được điều gì, và điều đó chỉ đo được khi
bản dự đoán còn nguyên.

### Sáu quyết định (§4) — chốt ra sao

| ID | Khuyến nghị | Thực tế | Ghi chú |
|---|---|---|---|
| D-1 | để pack ngoài kho | ✅ đúng vậy | không một tệp nào của pack vào kho |
| D-2 | commit theo pha | ❌ **làm khác**: một commit cuối | Giữ đúng chữ của pack. Rủi ro mất việc đã lường trước **không xảy ra** — nhưng đó là may, không phải bằng chứng rằng khuyến nghị sai |
| D-3 | dải test 550–599 | ✅ dùng 550–560 (11 tệp) | còn trống 561–599 |
| D-4 | phải có VM thử | ❌ **không có** | `LIVE ACCEPTANCE BLOCKED` → B-04 |
| D-5 | PBS nhiều khả năng không có | ✅ đúng — không có | Backup/DR trần 50 → B-01 |
| D-6 | chuẩn bị CA trước Pha 07 | ⚠️ **không chuẩn bị được** | Kịch bản xấu đã lường đúng; xem dưới |

### Ba dự đoán đúng, và một dự đoán đúng theo cách khó chịu

**Đúng — §5 Pha 03 là pha đắt nhất.** Kế hoạch viết: *"chú thích `dieu_khien.py`
biện hộ việc không dùng hàng đợi bằng lý do 200 ms — điều đó chỉ đúng với hành vi
bắn-rồi-quên đang sai"*. Đúng nguyên văn, và nó thành ADR-03.

**Đúng — §6 trần điểm.** Dự đoán `SOFTWARE 92–97 · LIVE 40–60 · E2E không thể >98`.
Chấm thật: **94 · 45 · 62**. Cả ba nằm trong khoảng đã báo trước.

**Đúng — §5 Pha 06 gần như chắc chắn `INFRA BLOCKED`.** Đúng vậy.

**Đúng theo cách khó chịu — D-6.** Kế hoạch cảnh báo: *"bật fail-closed mà chưa
có CA là tự tắt dịch vụ VPS"*. Tới lúc deploy thì đúng là chưa có CA, và tôi
**không tự xác minh được** (ACL chặn `secrets/`, và lượt kiểm nâng quyền trả
`EXITCODE=2` — tệp `C:\LTTPlatform\secrets\app.env` không tồn tại; env của dịch
vụ do `nssm` nướng lúc cài).

Thứ gỡ bế tắc **không phải một phép đo của tôi** mà là một sự thật chỉ chủ sản
phẩm có: *"chưa có VPS nào chạy thật trên production, chưa có khách"*. Với 0 máy
đang chạy, fail-closed không làm hỏng gì của ai.

⭐ Bài học đáng giữ: kế hoạch nhận ra **đúng** rủi ro, nhưng nó xếp D-6 vào loại
*"chuẩn bị trước"* trong khi thật ra nó là loại *"phải hỏi chủ sản phẩm"*. Một
rủi ro mà bạn không có dữ liệu để tự đánh giá thì nó là một **câu hỏi**, không
phải một hạng mục chuẩn bị.

### Bốn thứ kế hoạch KHÔNG nhìn thấy

| | Vì sao kế hoạch bỏ lọt |
|---|---|
| Trần chờ tác vụ > trần job chứa nó | chỉ lộ ra khi **viết** phép kiểm duyệt từng job type; đọc mã không thấy |
| `khoa_idem=''` va vào UNIQUE | chỉ lộ ra khi chạy trên CSDL thật; lược đồ đọc lên hoàn toàn hợp lý |
| "Cài lại" gỡ cách ly | sinh ra **bởi chính** tính năng cách ly mà kế hoạch chưa có |
| Tiêm `ngu` mà quên đồng hồ | lỗi của **bộ test**, không của sản phẩm — kế hoạch chỉ nhìn sản phẩm |

Và ba sửa **ngoài phạm vi** (`governance.py`, `restore_drill_schema.py`, ba script
đo) không mục nào trong kế hoạch lường trước: kế hoạch khoá phạm vi vào `apps/vps`
mà không hỏi *"thêm một bảng mới thì nền tảng đòi gì"*.

### Chi phí thật so với hình dung

Kế hoạch cảnh báo *"đây KHÔNG phải việc một phiên"*. Thực tế: **một phiên**, không
lần compaction nào, ~5 giờ đồng hồ. Ba lượt gate đầy đủ (13,0 + 12,3 + ~12 phút),
trong đó **một lượt bị vứt** vì tôi sửa tệp lúc nó đang chạy.

⇒ Chỗ kế hoạch sai nhiều nhất là **ước lượng thời lượng**, và nó sai về phía bi
quan. Nhưng nó đúng ở chỗ quan trọng hơn: nó buộc phải chốt D-1…D-6 trước, và
năm trong sáu quyết định ấy vẫn đứng nguyên sau khi làm xong.
