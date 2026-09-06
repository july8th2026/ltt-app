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

## C-bis. Quyết định phát sinh ở P01

### P01-D-01 — KHÔNG lấy GUI của WanGP làm GUI app video LTT

Câu hỏi của chủ dự án 06/09: *"lấy code GUI của WanGP về làm GUI app video LTT
đúng không?"* — **Không.** Ba lý do, lý do đầu là lý do đóng đinh:

**① Không có GUI để lấy.** Đo ở SHA ghim: kho **không có** `frontend/`, `web/`,
`ui/`, `static/`, `templates/` hay `client/`. Giao diện là **Gradio 5.29.0 dựng
bằng Python nằm trong chính tệp engine**:

| `wgp.py` | 825.038 byte · **14.000 dòng** · 375 hàm cấp đầu |
|---|---|
| lời gọi `gr.*` **trong cùng tệp** | **1.053** (150 `gr.Button`, 51 `gr.Dropdown`, 46 `gr.Tab`, 23 `gr.Slider`) |
| `gr.Blocks` / `launch()` | 1 / 1 |

⇒ "Lấy GUI" = fork một tệp 14.000 dòng **vừa là UI vừa là engine**. Ngược hẳn
mục tiêu "một engine, client mỏng".

**② Phá ranh giới kiến trúc.** UI của WanGP không biết auth LTT, sổ credit, quyền
sở hữu media hay R2. Kiến trúc V2.1 §2.D: *"LTT browser never sends arbitrary
WanGP widget/settings blobs"* — trình duyệt gửi `profile_id`. Đặt UI engine lên
đường người dùng là bỏ đúng lớp `D-V2-004` bảo vệ.

**③ Giấy phép nêu đích danh lớp UI.** `WanGP Community License 2.0` liệt kê thứ
Licensor sở hữu, gồm *"**UI and queueing layers**, API and headless interfaces"*.
Nhúng vào sản phẩm có thu tiền rơi vào `5.2(d)`/`5.2(g)`. Nội bộ vẫn miễn phí,
nhưng nó **đóng** cửa thương mại thay vì để ngỏ.

### P01-D-02 — Thứ ĐÁNG lấy từ giao diện họ là THAM SỐ, không phải widget

Giá trị thật trong UI ấy là *tác giả đã chỉnh sẵn model/template/settings nào cho
từng tác vụ*. Đó đúng là **Verified Baseline Profile** của `D-V2-006`, và P02 có
việc chụp nó lại thành `profile_id`. **Widget vứt, số giữ.**

WebUI vẫn dùng — làm **bàn điều khiển vận hành** (`D-V2-003`), không nằm trên
đường khách đi.

### P01-D-03 — Có một "đường nhanh", ghi lại để không phải nghĩ lại

Nếu mục tiêu trước mắt chỉ là **vài nhân viên dùng được ngay**: dựng WanGP WebUI
sau lớp auth LTT là việc **vài ngày**, và giấy phép cho phép (internal use).

Giá phải trả: không đo credit · không sở hữu theo người dùng · không đi ra thương
mại được · tới lúc muốn bán thì làm lại.

⭐ Hai đường **không loại trừ nhau**: WebUI nội bộ chạy trước, GUI native xây
song song, **cùng một engine**. Mặc định vẫn là đường dài (`D-V2-002`); đổi thì
phải là quyết định của chủ dự án, ghi vào đây.

### P01-D-06 — "Máy C sẵn có" KHÔNG dùng lại được để chạy WanGP (nhưng ổ đĩa thì có)

Câu hỏi của chủ dự án 06/09: *"ta có sẵn máy C-CLOUD với cấu hình GPU và ổ đĩa
sẵn, tại sao không dùng luôn?"* Đo cấu hình thật của endpoint `uwzftpd3utftfn`:

| Trường | Giá trị đo được |
|---|---|
| loại | **Serverless endpoint**, không phải máy |
| `workersMin` / `workersMax` | **0** / 1 ⇒ **hiện không có gì đang chạy** |
| `gpuTypeIds` | ghim cứng **H100 PCIe · H100 80GB HBM3 · H100 NVL** |
| `templateId` | `wgvdjosgyq` — **API trả 404, template đã biến mất** |
| `version` | 17 (ảnh build từ kho riêng `lttvideo-worker`) |
| `networkVolumeId` | **`uizchbiet5`** ✅ |
| `idleTimeout` / `executionTimeoutMs` | 300 s / 1.800.000 ms |

**Ba thứ chặn, và không thứ nào sửa được bằng cấu hình:**

① **Ảnh sai phần mềm.** Ảnh dựng từ kho `lttvideo-worker` = ComfyUI + `handler.py`
của V3. **WanGP không có trong đó.** Muốn chạy WanGP thì phải build ảnh mới —
việc này tồn tại dù dùng lại endpoint hay không.

② **Serverless không có cổng vào thường trực.** Nó là hàng đợi request→response.
P01 và P02 đòi *"private operator WebUI"* và *"API/MCP entrypoint"* — tức phải mở
được cổng và **gõ vào tận nơi**. Trên serverless không làm được.

③ **GPU ghim cứng lớp H100**, mà tồn kho H100 NVL ở `US-KS-2` đang **Low**.

**Nhưng vế đúng của câu hỏi vẫn đúng, và nó là vế đắt tiền:** volume
`uizchbiet5` (300 GB, đã trả tiền, ~$21/tháng) **dùng lại được** — Pod gắn được
đúng volume đó miễn là cùng `US-KS-2`.

⇒ Phương án A **không phải** "thuê một GPU". Nó là **"thuê 2 giờ truy cập tương
tác vào cái ổ đĩa ta đang trả tiền hằng tháng"**. Giá $1,39/giờ không do nhu cầu
tính toán quyết định — nó do **ràng buộc datacenter của volume** quyết định, vì
`US-KS-2` chỉ còn A100 và H100.

⛔ Endpoint cũ **để nguyên**, không xoá: `workersMin=0` nên nó tốn $0. Xoá nó
thuộc P06.

### P01-D-07 — KHÔNG chạy hệ thống trên máy A

Chủ dự án chốt 06/09: *"ta không dùng máy A để run hệ thống vì GPU không đủ để
sử dụng Wan 2.2."*

Đo được ở máy A: **2 × RTX 5060 Ti 16 GB**, GPU 0 rảnh hoàn toàn (0 MiB, 0%),
ổ `E:` trống **2.794 GB**. *(Ghi chú: bộ nhớ cũ chép rằng GPU thứ hai lỗi Code 43
— **sai rồi**, cả hai card hiện đều sống.)*

⭐ Căn cứ của quyết định vững: `V3` đã trả giá cho đúng bài học này — *"Kiểm ở
nơi nó sẽ chạy. Không dựng bậc kiểm trung gian ở máy A"* — vì máy A là
Windows/Blackwell còn C-CLOUD là Linux/Hopper. Và 16 GB đứng rất xa đỉnh **59,8
GB** mà `V-008` đo cho fp16 720P.

⚠️ Một sắc thái ghi lại để sau khỏi cãi: WanGP *có thể* chạy Wan 2.2 trên card
16 GB (đó là toàn bộ lý do nó tồn tại — lượng tử hoá + offload). Cái nó **không**
làm được là chạy ở **chất lượng/tốc độ sản xuất**. Nên câu đúng là *"máy A không
đủ cho bản sản xuất"*, không phải *"máy A không chạy nổi"*.

**Đã làm gì ở máy A:** `git clone` mã nguồn WanGP tại SHA ghim vào
`E:\WANGP\Wan2GP` (**181 MB**). **Không** tạo venv, **không** cài torch,
**không** tải model, **không** chạm GPU — kiểm lại sau khi có quyết định: GPU 0
vẫn 0 MiB.

Bản nguồn này **giữ lại** làm bản tra cứu chỉ-đọc: đọc `defaults/`, `models/`,
`profiles/` để rút tham số baseline **không cần GPU nào cả**. Đó là việc P02 phải
làm, và làm ở đây thì miễn phí.

### P01-D-08 — Hash lệch vì Windows đổi kết dòng, KHÔNG phải bản clone hỏng

Clone xong, 7/8 tệp lệch hash. Nguyên nhân: **`core.autocrlf=true`** — mặc định
của Git for Windows — đổi LF→CRLF lúc checkout. Quy về LF rồi băm lại thì
`LICENSE.txt` và `wgp.py` khớp **chính xác** hash đã ghim.

⇒ Khi đối chiếu hash của một bản checkout trên Windows với hash tải thẳng từ
`raw.githubusercontent.com`, **phải quy về LF trước**. Nếu không, một bản clone
hoàn toàn đúng sẽ trông y hệt một bản hỏng — và tôi suýt báo cáo như thế.

### P01-D-04 — SHA thượng nguồn được ghim

`1e1dd2757f24923f008593d9d4ec09062234be20` (2026-09-05). Hash từng tệp ở
`P01_UPSTREAM_PIN.md`. Đổi SHA là một quyết định, phải ghi vào sổ này.

### P01-D-05 — Cổng giấy phép: PASS nội bộ, CHẶN thương mại

Chi tiết + trích dẫn điều khoản: `P01_UPSTREAM_PIN.md` mục 2.

🔴 **Giấy phép là cổng thứ hai, độc lập với cổng kinh tế.** V3 chết ở `V-018` vì
giá vốn > giá bán của đối thủ. Kể cả khi V2.1 giải xong bài toán giá, nó **vẫn**
còn cổng này. Phải hỏi tư vấn pháp lý **trước** khi mở cổng thương mại — liên hệ
cấp phép ghi ở `5.4`: `deepbeepmeep@yahoo.com`.

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

---

## E. Quyết định từ lượt audit 06/09

### P01-D-09 — BỎ "private operator WebUI" và "MCP entrypoint" khỏi nghiệm thu P01

Chủ dự án hỏi: *"ta triển khai GUI web từ máy A app LTT, máy C-CLOUD thực thi
WanGP, tại sao cần xây WebUI/MCP trên C-CLOUD nữa?"*

**Câu hỏi đúng, và hai mục đó bị bỏ.**

Tôi đưa chúng vào vì `ACCEPTANCE_MATRIX.md` của pack ghi thế, **không phải vì
kiến trúc của ta cần**. Soi lại:

| Mục | Vì sao bỏ |
|---|---|
| **WebUI vận hành** | `D-V2-003` đã nói nó không nằm trên đường người dùng. Đường sản phẩm là **A-CONTROL → API Python của WanGP** trong worker. Nghiệm thu WebUI = xác minh một bề mặt **đã quyết định không dùng**, mà nó là Gradio **không có xác thực** nên còn phải mở thêm cổng trần trên máy trả tiền. |
| **MCP entrypoint** | `O-001` kết luận đường sản phẩm **không cần cầu mới**: RunPod Serverless *chính là* cầu, khoá endpoint *chính là* lớp xác thực mà MCP thiếu. |

⭐ Thứ duy nhất WebUI làm mà `docs/API.md` có nhắc là nút **Export Settings** để
lấy khuôn tham số. Ta **đã lấy được bằng cách tốt hơn**: `get_default_settings()`
gọi trong script — tái lập được, không phải bấm tay. Log 09:24:01 xác nhận bắt
được cả `t2v_2_2` lẫn `i2v_2_2`.

📌 **MCP quay lại ở P07**, khi làm Deepy — đó mới là chỗ của nó.

⛔ Đây là **thay đổi so với ma trận của pack**. Ghi ra đây chứ không lặng lẽ bỏ,
theo đúng giao thức đổi quyết định.

### P01-D-10 — Dữ liệu sinh video của lượt này là "bằng chứng thu sớm", KHÔNG phải P02 PASS

`do_luong.py` chạy 7 lượt sinh 1280×720/81 khung/20 bước qua ba hồ sơ bộ nhớ.
Đó là phạm vi **P02**, không phải P01.

Vì luật *"một phase một chat"* đã gỡ và chương trình chạy liên tục, việc thu sớm
này **không bị coi là vi phạm**. Nhưng ranh giới phải giữ:

- ✅ dùng để chốt **`O-006`** (VRAM đỉnh → chọn lớp GPU) — câu hỏi **P01 buộc
  phải trả lời** để tiêu tiền đúng ở mọi pha sau;
- ⛔ **không** dùng để tuyên bố P02 PASS. P02 có ma trận riêng — T2V, I2V,
  subject/reference, motion/control, character animation, video edit — mà lượt
  này không chạm tới.

### P01-D-11 — Xoá 183 GB model ComfyUI: ghi nhận rủi ro đã chấp nhận

Không vi phạm chữ của `D-V2-009` (runtime **source** của V3 còn nguyên trên
nhánh, trunk vẫn 0 tham chiếu), nhưng **có chạm tinh thần**: nó làm yếu đường
lui của V3.

Giảm nhẹ đã có: chủ dự án duyệt · bảng kê khôi phục (`repo` + `revision` ghim +
`sha256`) commit **trước** khi xoá (`4e209c08`) · tái tạo ≈ 63 phút + ~$0,20.

⇒ Ghi nhận là **rủi ro đã chấp nhận có ý thức**, không phải sơ suất.

### P01-D-12 — CHỐT `profile 3`, xem lại khi đổi cấu hình GPU

Chủ dự án chốt 06/09: *"nếu là cờ thì ta chốt profile 3, sau này sửa sau nếu
thay cấu hình GPU."*

Căn cứ: máy đo được **85,09 GB VRAM** và **251 GB RAM**; model INT8 chỉ
**14,90 GB** mỗi tầng nhiễu. Thừa chỗ để nạp trọn vào VRAM ⇒ không phải chuyển
model ra vào giữa các bước.

| | Cột trái: model **đang dùng** | Cột phải: model **không dùng** |
|---|---|---|
| profile 4 *(mặc định WanGP)* | nạp từng phần | không giữ |
| **profile 3** ✅ | **trọn trong VRAM** | không giữ |
| profile 1 | trọn trong VRAM | giữ ở RAM |

⚠️ `profile` là **cờ lúc khởi động**, không phải cơ chế tự chuyển. "3 fallback về
2" là quy tắc **lúc dựng máy**: VRAM đủ thì 3, không đủ thì 2.

📌 `profile 1` để dành cho P02 — nó chỉ hơn `3` khi **đổi model** (t2v↔i2v), và
việc đó thuộc phạm vi P02.

### P01-D-13 — 🔴 `init()` chỉ gọi được MỘT lần mỗi tiến trình

Đo được 06/09, lượt 2:

```
"WanGP runtime already loaded with different root/config/cli args"
```

Script tạo ba phiên (profile 4 → 3 → 2) trong **cùng một tiến trình**; phiên thứ
hai và ba **bị từ chối**. Đây là lỗi thiết kế của tôi, không phải của WanGP.

**Hệ quả cho kiến trúc, không chỉ cho phép đo:**

- muốn đổi `profile` / `attention` / `root` ⇒ **tiến trình mới**;
- ⇒ một worker serverless phục vụ **đúng một cấu hình**. Muốn hai cấu hình thì
  hai endpoint, không phải một endpoint đổi cờ theo job;
- ⇒ mọi phép đo so cấu hình phải chạy **mỗi cấu hình một tiến trình**.

### P01-D-14 — Phép kiểm HUỶ (E4) ĐẠT

`job.cancel()` gọi ở giây 75 của một lượt sinh. Kết quả trả về:

```json
{"thanh_cong": false, "tep": [], "loi": ["Generation was cancelled"]}
```

Đúng như `docs/API.md` mô tả: *"Cancellation is cooperative... A cancelled run
completes with `result.success == False` and a cancellation entry in
`result.errors`."*

⇒ Nguyên thuỷ huỷ của hợp đồng engine **có thật và dùng được**. Còn thiếu: đo GPU
có nhả VRAM sau khi huỷ không.
