# LTT VIDEO V2.1 — PROJECT STATE

> Khuôn: `PROJECT_STATE_TEMPLATE.md` của pack
> `LTT_VIDEO_WANGP_ONE_ENGINE_PROMPT_PACK_V2_1` (G:\My Drive\AI\A LTT AII\).
> **Tệp này là bộ nhớ giữa các phase.** Chat mới đọc tệp này trước, không đọc
> lại lịch sử chat cũ.
>
> ⛔ Đừng chép số hiệu commit, giá tiền hay tham số vào đây bằng tay nếu nó có
> một nguồn sống ở nơi khác — ghi **con trỏ** tới nguồn đó. Chương trình V3
> trước đã mất hai ngày vì một bảng chép tay không tự biết nó đã cũ.

## Trạng thái

- **phase:** `P00` — Recover + Audit Legacy + Fresh V2 Baseline
- **status:** **PASS** (xem mục *Cổng nghiệm thu P00*)
- **branch:** `phien/video-v2-wangp`
- **worktree:** `D:\LTTSTUDIOSAPP\.claude\worktrees\video-v2-wangp`
- **base_commit (trunk lúc tách):** `06017841` trên `admin-mvp-v3`
- **head:** ⚙️ hỏi `git -C <worktree> log -1 --format=%h`, đừng chép vào đây
- **trunk thật:** **`admin-mvp-v3`**, **không** phải `master`
  — đo được: `git rev-list --left-right --count master...admin-mvp-v3` → `0 216`.
  `master` đứng ở `d225a480` (03/09), tụt sau trunk **216 commit**.
  ⇒ Worktree V2 tạo từ `admin-mvp-v3` theo `docs/QUY_TRINH_WORKTREE.md` luật 1.
- **wangp_upstream_sha:** *(chưa — P01 ghim)*
- **wangp_patch_sha:** *(chưa — P01/P03)*
- **video_engine_target:** **WanGP** (D-V2-001)
- **new_v2_runtime_fallback_to_legacy:** **FORBIDDEN** (D-V2-010)
- **commercial_gate:** **CLOSED** (D-V2-011) — nội bộ, `public=False`,
  `api_exposed=False`
- **b_lan:** **UNTOUCHED** (D-V2-008) — P00 không đọc, không ghi, không ping máy B
- **legacy_runtime_source:** **PRESENT — nhưng KHÔNG nằm trên trunk.**
  Toàn bộ runtime V3 sống trên nhánh `claude/ltt-video-ai-v3-p00-3f5713`, và
  nhánh đó **đã dừng phát triển 06/09** (`P00-D-07`). Loại bỏ ở **P06**, sau khi
  P05 PASS. Chi tiết + bằng chứng: `LEGACY_INVENTORY.md`.
- **legacy_restore_ref:** *(chưa tạo — P03 tạo `video-legacy-final-pre-wangp`)*
- **integration_transport:** **OPEN** (`O-001`: MCP trực tiếp vs cầu HTTP mỏng)
  — chốt sau bằng chứng P02
- **cloud_resources:** ⚠️ **có tài nguyên trả tiền ĐANG SỐNG, của V3, chưa đụng**
  — xem mục *Cloud* bên dưới
- **baseline_profiles:** *(chưa — sinh ở P02)*
- **max_quality_profiles:** *(chưa — sinh ở P07)*
- **spend_phase:** **$0,00** — P00 không dùng GPU, không gọi API tính tiền
- **tests:** không thêm/sửa test ở P00 (thay đổi chỉ là tài liệu)
- **gates:** `gate.py` đầy đủ trong worktree V2 → **`FAIL (3/26)`**, nhưng **cả
  ba bước đỏ đỏ y hệt trên trunk** khi không có nhánh này (đối chứng đã chạy).
  Nhánh V2 thêm 0 lỗi. Chi tiết + lệnh tái hiện: *Cổng chất lượng kho*.
- **browser_checks:** **N/A** — P00 không đổi GUI, route hay tài sản tĩnh
- **blockers:** xem *Blockers*
- **decisions:** `DECISIONS.md`
- **exact_next_action:** **P01** — `P01_PIN_VANILLA_WanGP_C_CLOUD_POC.md`,
  trong **chat mới**, từ worktree này.
  ➕ **Việc phụ bắt buộc của P01:** chốt giữ hay bỏ volume RunPod `uizchbiet5`
  (~$21/tháng, của V3 đã dừng) — quyết được ngay khi biết BOM model của WanGP.
  Xem `DECISIONS.md` `P00-D-07`.

## Cloud — tài nguyên trả tiền đang sống (thừa kế từ V3)

⛔ **P00 không tạo, không xoá, không đụng gì.** Ghi lại vì `COST_AND_SAFETY.md`
đòi kiểm kê **trước** khi có compute trả tiền, và vì hai tài nguyên này đang
tính tiền trong lúc chương trình V2.1 khởi động.

| Tài nguyên | ID | Trạng thái | Tiền |
|---|---|---|---|
| Network volume RunPod | `uizchbiet5` (`lttvideo-models-v1`) | 300 GB standard, `US-KS-2` | ~**$21/tháng**, cố định |
| Endpoint Serverless | `uwzftpd3utftfn` (`lttvideo-worker`) | `workersMin=0` | ~$0 khi rảnh |

- Số dư RunPod và mức chi **không chép vào đây** — hỏi
  `python tools\video_theo_doi.py tom-tat` **trên nhánh V3** (công cụ chỉ tồn
  tại ở đó), và chỉ tin dòng `Hoa don`.
- 🔴 **Sàn credit:** số dư RunPod về $0 thì volume bị **xoá không khôi phục
  được**. Quyết định giữ hay bỏ volume 300 GB là một quyết định **của chủ dự
  án**, thuộc P06 (cutover), không phải của P00.

## Cổng nghiệm thu P00

Yêu cầu của prompt: *"Fresh V2 branch sạch; inventory path-level có bằng chứng;
runtime không đổi."*

| Điều kiện | Kết quả | Bằng chứng |
|---|---|---|
| Xác định trunk thật | ✅ `admin-mvp-v3` | `rev-list --left-right --count master...admin-mvp-v3` = `0 216` |
| Branch/worktree V2 sạch, tạo từ trunk | ✅ | `git worktree list`; `rev-parse` khớp `06017841` |
| Inventory legacy path-level, có bằng chứng | ✅ | `LEGACY_INVENTORY.md` — 39 tệp runtime + 13 tệp hạ tầng dùng chung, kèm số dòng và lệnh đo |
| Không merge legacy | ✅ | 0 tệp legacy trên `phien/video-v2-wangp` |
| Runtime không đổi | ✅ | thay đổi duy nhất của P00 là `docs/VIDEO_AI_V2/**` |
| Không chạm B-LAN | ✅ | không lệnh nào ra khỏi máy A |
| Không secret vào docs | ✅ | tệp này ghi **ID tài nguyên**, không ghi khoá |

### Cổng chất lượng kho

Đã chạy `python tools\gate.py` trong worktree V2 sau khi cửa sổ yên rảnh
(phiên khác giữ khoá lúc 11:44 đã xong).

**`RESULT: FAIL (3/26)`** — sổ: `test-results/gates/20260906T061946Z-6764.json`,
489 giây.

🔴 **Cả ba bước đỏ đều đỏ y hệt trên trunk `admin-mvp-v3` khi KHÔNG có nhánh
này.** Nhánh V2 thêm **0** lỗi. Đối chứng đã chạy, không suy luận:

| Bước đỏ | Trên nhánh V2 | Đối chứng trên trunk |
|---|---|---|
| `bo qua im lang` | 15 chỗ / mốc 14 | **15 / mốc 14** — y hệt |
| `nuot loi lang le` | 64 chỗ / mốc 62 | **64 / mốc 62** — y hệt |
| `test_306::test_bo_qua_hien_tai_dat_moc` | FAIL | **FAIL** — y hệt |

Gốc của cả ba là **hai** thay đổi của phiên khác trên trunk hôm nay:
① commit `ae1c23f5` thêm một chỗ `skip` mới trong `tests/test_361_cua_so_yen.py`
(`test_may_ban_KHONG_dem_chinh_no_va_chuoi_cha`) mà chưa `--accept` bánh cóc;
② +2 chỗ `except Exception` nuốt lỗi.

⇒ Việc gỡ ba bước này thuộc **phiên đang làm trên trunk**, không thuộc P00.
P00 chỉ thêm `docs/`, không chạm `apps/ platform_core/ server/ tools/ tests/`.

⛔ Ghi rõ để phiên sau không đọc nhầm: đây **không** phải một lượt `RESULT: PASS`.
Tiêu chuẩn của P00 (phase chỉ có tài liệu) là **không đỏ thêm so với trunk**, và
tiêu chuẩn đó đạt bằng đối chứng ở trên. **P01 trở đi có sửa mã ⇒ phải có
`RESULT: PASS` thật**, nên trunk cần xanh lại trước khi P01 báo xong.

Lệnh tái hiện đối chứng:

```
cd D:\LTTSTUDIOSAPP && python tools\check_bo_qua.py
cd D:\LTTSTUDIOSAPP && python tools\check_silent_except.py
cd D:\LTTSTUDIOSAPP && python -m pytest tests\test_306_banh_coc_bo_qua_va_dich.py -q
```

## Blockers

| # | Nội dung | Ai gỡ |
|---|---|---|
| ~~**B-1**~~ | ✅ **ĐÃ GỠ 06/09.** Chủ dự án chốt: **V3 dừng phát triển**, V2.1 là đường duy nhất, **loại bỏ V3 sau khi V2.1 chạy thật** (= P06, sau P05 PASS — xem `P00-D-07`). | — |
| **B-2** | `O-001` chưa chốt: MCP trực tiếp vs cầu HTTP mỏng. Không chặn P01. | Bằng chứng P02 |
| **B-3** | Chưa có tài khoản/hạ tầng **C-CLOUD** cho WanGP trong tay. P01 cần biết nhà cung cấp + GPU + vùng. | P01 preflight |
| **B-4** | **Trunk đang đỏ 3/26 bước gate** vì việc đang dở của phiên khác (chỗ `skip` mới chưa `--accept`, +2 chỗ nuốt lỗi). Không chặn P00; **chặn P01 báo xong**, vì P01 có sửa mã nên cần `RESULT: PASS` thật. | phiên đang làm trên `admin-mvp-v3` |

🔴 **Việc còn lại của B-1 không phải kỹ thuật mà là tiền.** V3 dừng rồi, nhưng
volume `uizchbiet5` **vẫn tính ~$21/tháng** vì nó tính theo dung lượng chứ không
theo việc dùng — dừng phát triển không làm nó ngừng. Từ nay tới P06 là nhiều
tuần.

⇒ **Chốt giữ hay bỏ volume ở P01**, khi đã biết BOM model của WanGP. Sớm hơn thì
chưa đủ dữ liệu; muộn hơn là trả tiền cho một quyết định đã trì hoãn. Ba ràng
buộc + lý do ở `DECISIONS.md` `P00-D-07`.

## Ghi chú vận hành cho phiên sau

- Worktree này **đã chép** tài sản bị `.gitignore` loại (`apps/upscalevideo/vendor`,
  48 MB) theo `docs/QUY_TRINH_WORKTREE.md` luật 1b. Thiếu nó thì
  `test_82::test_vendor_engine_co_mat` đỏ và cái đỏ đó vô nghĩa.
- `tools/gate.py` ở worktree này **có** `loi_cho_bo_test` ⇒ trần 6 worker, đúng
  ngân sách lõi. Không cần gộp trunk trước khi chạy gate.
- `tests/rao_chan_nang.py` **không có** trên trunk (chỉ ở `phien/asv-v4`). Test
  nào nạp model thật phải tự chặn bằng `LTT_TEST_NANG` gõ tay.

---

*P00 đóng. Không chạy P01 trong chat này.*
