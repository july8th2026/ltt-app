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
  Toàn bộ runtime V3 sống trên nhánh `claude/ltt-video-ai-v3-p00-3f5713`.
  Chi tiết + bằng chứng: `LEGACY_INVENTORY.md`.
- **legacy_restore_ref:** *(chưa tạo — P03 tạo `video-legacy-final-pre-wangp`)*
- **integration_transport:** **OPEN** (`O-001`: MCP trực tiếp vs cầu HTTP mỏng)
  — chốt sau bằng chứng P02
- **cloud_resources:** ⚠️ **có tài nguyên trả tiền ĐANG SỐNG, của V3, chưa đụng**
  — xem mục *Cloud* bên dưới
- **baseline_profiles:** *(chưa — sinh ở P02)*
- **max_quality_profiles:** *(chưa — sinh ở P07)*
- **spend_phase:** **$0,00** — P00 không dùng GPU, không gọi API tính tiền
- **tests:** không thêm/sửa test ở P00 (thay đổi chỉ là tài liệu)
- **gates:** xem *Cổng nghiệm thu P00*
- **browser_checks:** **N/A** — P00 không đổi GUI, route hay tài sản tĩnh
- **blockers:** xem *Blockers*
- **decisions:** `DECISIONS.md`
- **exact_next_action:** **P01** — `P01_PIN_VANILLA_WanGP_C_CLOUD_POC.md`,
  trong **chat mới**, từ worktree này.

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

⚠️ Lúc P00 chạy, **một phiên khác đang giữ `cua_so_yen`** (`cpu_nhieu` +
`postgres_test`, pid 7772, `gate --ho-so day-du`). Theo `CLAUDE.md` và
`docs/QUY_TAC_CHAY_LENH_NANG.md`, phiên này **chờ**, không chạy gate chồng lên.

P00 không sửa một dòng mã thực thi nào — thay đổi nằm trọn trong `docs/`. Lượt
gate của phase này phải chạy **trước khi bắt đầu P01**, khi cửa sổ yên rảnh:

```
python tools\cua_so_yen.py trang-thai   # phải trống
python tools\gate.py                    # trong worktree V2
```

⛔ Không được báo `PASS` cho một phase **có sửa mã** mà chưa có `RESULT: PASS`
của gate đầy đủ. Với P00 (chỉ tài liệu) điều kiện là gate **không đỏ thêm** so
với trunk.

## Blockers

| # | Nội dung | Ai gỡ |
|---|---|---|
| **B-1** | **Hai chương trình cùng nhắm một sản phẩm.** Nhánh V3 `claude/ltt-video-ai-v3-p00-3f5713` vẫn có commit **hôm nay 06/09 09:50** (`e21faf6a`). Pack V2.1 xếp đúng nhánh đó vào diện `DELETE_AT_P06`. Nếu V3 tiếp tục được xây thì công sức đó sẽ bị xoá ở P06. | **Chủ dự án** — dừng V3 hay dừng V2.1 |
| **B-2** | `O-001` chưa chốt: MCP trực tiếp vs cầu HTTP mỏng. Không chặn P01. | Bằng chứng P02 |
| **B-3** | Chưa có tài khoản/hạ tầng **C-CLOUD** cho WanGP trong tay. P01 cần biết nhà cung cấp + GPU + vùng. | P01 preflight |

🔴 **B-1 là thứ đắt nhất.** V3 đã đóng 8/8 pha và tiêu tiền thật; V2.1 tuyên bố
nó là legacy. Không ai ngoài chủ dự án quyết được cái nào sống.

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
