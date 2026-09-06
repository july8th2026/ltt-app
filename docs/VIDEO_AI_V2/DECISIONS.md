# SỔ QUYẾT ĐỊNH — LTT VIDEO V2.1 (WanGP ONE ENGINE)

Nguồn gốc: pack `LTT_VIDEO_WANGP_ONE_ENGINE_PROMPT_PACK_V2_1`
(`00_ARCHITECTURE/DECISIONS.md`), chép vào kho ở P00 để phiên sau không phụ
thuộc ổ `G:`.

⛔ Đây là **sổ**, không phải bảng tóm tắt. Một quyết định đổi thì sửa **ở đây**,
kèm ngày và lý do; đừng chép giá trị của nó sang tệp khác.

---

## A. Đã CHỐT trong pack V2.1

| # | Nội dung | Trạng thái |
|---|---|---|
| **D-V2-001** | **Một engine.** Sau cutover, engine video = **WanGP**, không còn engine thứ hai. | ✅ CHỐT |
| **D-V2-002** | GUI LTT native là giao diện sản phẩm cho nhân viên. | ✅ CHỐT |
| **D-V2-003** | **WanGP WebUI không nằm trên đường người dùng.** Chỉ operator/debug/benchmark. | ✅ CHỐT |
| **D-V2-004** | **A-CONTROL giữ trạng thái sản phẩm**: auth, user, job, quyền sở hữu media, R2, lịch sử, ngân sách, vòng đời cloud. | ✅ CHỐT |
| **D-V2-005** | **C-CLOUD giữ thực thi**: WanGP + Deepy + model + GPU. | ✅ CHỐT |
| **D-V2-006** | **Hai lớp profile.** `Verified Baseline` (P02) trước, `Optimized Quality` (P07) sau. | ✅ CHỐT |
| **D-V2-007** | **Deepy trước.** Không dựng agent LTT song song trước khi có phép đo Deepy. | ✅ CHỐT |
| **D-V2-008** | **B-LAN được bảo vệ.** Video V2 không dùng, không sửa máy B. | ✅ CHỐT |
| **D-V2-009** | **Xoá legacy sau khi replacement chạy thật E2E.** WanGP tự generate được là chưa đủ. | ✅ CHỐT |
| **D-V2-010** | **Không fallback runtime.** Legacy có thể còn trong Git/source lúc đang xây, nhưng mã V2 **không được** gọi/cascade/fallback sang nó. | ✅ CHỐT |
| **D-V2-011** | **Nội bộ.** Cổng thương mại/công khai **ĐÓNG**. | ✅ CHỐT |

## B. Còn MỞ trong pack

| # | Câu hỏi | Chốt ở đâu |
|---|---|---|
| **O-001** | MCP trực tiếp vs cầu cloud mỏng | sau bằng chứng P02 |
| **O-002** | GPU/vùng cụ thể | P01 |
| **O-003** | Deepy LLM cục bộ hay từ xa | P02/P07 |
| **O-004** | Model nào thắng khi tối ưu | P07 |
| **O-005** | Idle TTL | P08 |

---

## C. Quyết định phát sinh ở P00 (kho này, 2026-09-06)

### P00-D-01 — Trunk là `admin-mvp-v3`, không phải `master`

Đo: `git rev-list --left-right --count master...admin-mvp-v3` → `0 216`.
`master` đứng ở `d225a480` (03/09), tụt sau **216 commit**.

⇒ Nhánh V2 tách từ `admin-mvp-v3`, theo `docs/QUY_TRINH_WORKTREE.md` luật 1.
Tạo từ `master` là tạo ra một cây **ra đời đã cũ** — đúng gốc rễ đã làm treo máy
chín lần trong hai ngày.

**Kiểm lại trước mỗi worktree mới**, đừng tin dòng này:
`git rev-list --count master..admin-mvp-v3` khác 0 ⇒ vẫn dùng `admin-mvp-v3`.

### P00-D-02 — Nhánh V2 là `phien/video-v2-wangp`, worktree riêng

Theo quy ước `phien/<tên>` đang dùng trong kho. Không làm việc trực tiếp trên
trunk vì trunk đang có **phiên khác** sửa (`tools/mobile_quet.js` dirty, và năm
commit W1/W2/W7 hôm nay về ngân sách lõi).

Worktree đã chép `apps/upscalevideo/vendor` (48 MB, bị `.gitignore` loại) theo
luật 1b — thiếu nó thì gate đỏ vì lý do không liên quan đến mã.

### P00-D-03 — "Xoá legacy ở P06" rút lại thành "không merge"

Bằng chứng ở `LEGACY_INVENTORY.md` mục 0: runtime video V3 **không có mặt trên
trunk**; 0 tham chiếu thực thi. Toàn bộ nằm trên nhánh
`claude/ltt-video-ai-v3-p00-3f5713`.

⇒ P06 không phải một lượt `git rm`. P06 là:
① không merge nhánh kia; ② tag phục hồi `video-legacy-final-pre-wangp` (tạo ở
P03); ③ quét lại 7 mẫu ký hiệu để chứng minh vẫn bằng 0.

### P00-D-04 — Không bao giờ `git merge` cả nhánh V3

Nhánh V3 sửa **13 tệp hạ tầng dùng chung**, trong đó bốn tệp
(`tools/gate.py`, `tools/test_nhanh.py`, `tests/test_361_cua_so_yen.py`,
`tests/test_431_ngan_sach_loi.py`) là **cơ chế ngân sách lõi** mà trunk cũng vừa
sửa nhiều hơn. Và nó mang theo `ho_so_he_thong.txt` (+6912 dòng) — tệp đã bị gỡ
khỏi trunk có chủ đích ngày 04/09.

⇒ Cần lấy lại thứ gì thì lấy **từng tệp** bằng `git checkout <nhánh> -- <đường dẫn>`.

### P00-D-05 — Không đụng tài nguyên cloud của V3 ở P00

Volume `uizchbiet5` (300 GB, ~$21/tháng) và endpoint `uwzftpd3utftfn` đang sống.
P00 chỉ **ghi nhận**. Giữ hay bỏ là quyết định của chủ dự án ở P06, và nó có mặt
trái không hoàn tác được: số dư RunPod về $0 ⇒ volume bị xoá vĩnh viễn.

### P00-D-06 — Bốn app video trên trunk **không** phải legacy

`taovideo`, `autosubvideo`, `upscalevideo`, `taoclipngan` là sản phẩm khác, đang
phục vụ khách. Phân loại `KEEP_GENERIC`. Ghi rõ vì một lượt dọn "theo mẫu tên"
rất dễ giết nhầm — cùng loại bẫy đã suýt cho `tests/test_71_thumbnail.py` vào
danh sách xoá chỉ vì nó khớp tiền tố chuỗi `tests/test_71`.

---

## D. Xung đột B-1 — ĐÃ GỠ

### P00-D-07 — V3 dừng phát triển; V2.1 là đường duy nhất đi tiếp

**Chủ dự án chốt 2026-09-06:** *"V3 đã dừng phát triển, ta đang tập trung vào
V2.1. Loại bỏ V3 sau khi V2.1 chính thức khởi động."*

Ba vế, đừng trộn chúng vào nhau:

| Vế | Hiệu lực | Ghi ở đâu |
|---|---|---|
| **V3 dừng phát triển** | **ngay lập tức** | banner đầu `docs/VIDEO_AI/PROJECT_STATE.md` trên nhánh V3 |
| **V2.1 là đường duy nhất** | ngay lập tức | chính sổ này |
| **Loại bỏ V3** | **sau khi V2.1 chạy thật** | mục dưới |

### "Sau khi V2.1 chính thức khởi động" nghĩa là ĐIỂM NÀO

Câu chốt của chủ dự án khớp đúng `D-V2-009` của pack, nên lấy luôn mốc của pack
làm định nghĩa vận hành — **không diễn giải rộng ra**:

```
P05 REAL LTT<->WanGP + R2 + cancel PASS
        |
P06 cutover  ->  luc nay moi loai bo V3
```

⛔ **Không** loại bỏ ở P01/P02 chỉ vì WanGP đã tự chạy được. `D-V2-009` tồn tại
đúng để chặn cách đọc đó: engine chạy được **chưa** chứng minh auth/R2/cancel/hợp
đồng job của LTT chạy thật.

⛔ Và "loại bỏ" ở kho này **không phải một lượt `git rm`** — xem `P00-D-03`:
runtime V3 chưa bao giờ lên trunk. Loại bỏ = không merge + tag phục hồi
`video-legacy-final-pre-wangp` (tạo ở P03) + quét lại chứng minh vẫn 0.

### 🔴 Việc KHÔNG chờ tới P06 được: tiền cloud

V3 dừng, nhưng **tài nguyên của nó vẫn tính tiền**:

| Tài nguyên | Tiền | Dừng phát triển có làm nó ngừng tính tiền không |
|---|---|---|
| Volume `uizchbiet5`, 300 GB | **~$21/tháng** | ❌ **không** — tính tiền theo dung lượng, không theo việc dùng |
| Endpoint `uwzftpd3utftfn` | ~$0 khi rảnh (`workersMin=0`) | ✅ có |

Từ nay tới P06 là **nhiều tuần**. Giữ nguyên volume = trả tiền cho 170,51 GB
model của một chương trình đã dừng.

Nhưng **đừng vội xoá**, vì ba lý do đo được:
① volume **thu nhỏ được thì không** — xoá là mất hẳn, tải lại mất 62,8 phút;
② P01/P02 chưa biết WanGP cần model nào — có thể trùng một phần với 8 tệp đã có;
③ số dư RunPod về $0 ⇒ RunPod **tự xoá volume**, không khôi phục được, nên
"để đó cho rẻ" cũng có mặt trái.

⇒ **Chốt việc này ở P01**, khi đã biết BOM model của WanGP — không sớm hơn, và
không muộn hơn. Ghi thành `exact_next_action` phụ của P01.
