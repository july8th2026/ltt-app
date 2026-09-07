# P07 — memory · projects · agents · skills

> Viết **sau khi P06 đóng** và **sau khi đo kho**, theo đúng luật kế hoạch tổng:
> *"viết bây giờ là viết trên một kiến trúc chưa tồn tại"*.
>
> Đo ngày 06/09/2026. Mọi con số dưới đây lấy từ **CSDL production**, không từ
> mã nguồn và không từ trí nhớ.

---

## §1 — Bốn hạng mục, và ba trong bốn VA vào thứ đã có

Kế hoạch tổng ghi phạm vi P07 là *"memory/projects/agents/skills"*. Đo kho thì
chỉ **một** trong bốn là đất trống:

| Hạng mục | Thứ đã tồn tại | Trạng thái |
|---|---|---|
| **memory** | không có gì (`grep` `bo_nho`/`memory` chỉ trúng VRAM và bộ nhớ card) | 🟢 đất trống |
| **projects** | `app_projects` — bảng **dùng chung của nền tảng**, phân theo `app_slug`, `payload` JSON do app tự sở hữu | 🟡 dùng lại |
| **agents** | **`apps/agent` đang `enabled=True, public=True`** + `platform_core/agent/` (12 module: tool discovery, validate plan, budget) | 🔴 va chạm sản phẩm |
| **skills** | không có (`skills` chỉ xuất hiện ở `sdk/` và `tools/cam_cli.py`, không phải khái niệm nền tảng) | 🟢 đất trống |

### Số đo trên production

```
chatltt_conversation   220 hang     <- KHACH THAT dang dung
app_projects             9 hang     agent.preferences(2) prompt_ai_ommi(1) autosubvideo(6)
agent_runs               4 hang     <- san pham agent gan nhu khong ai dung
```

⭐ Hai con số cuối đứng cạnh nhau là dữ kiện quan trọng nhất của cả tệp này.
**ChatLTT có 220 hội thoại thật; LTT Agent AI có 4 lượt chạy.** Cùng một nền
tảng, cùng một tập khách. Xây một hệ agent **thứ hai** bên trong ChatLTT trong
khi hệ thứ nhất gần như không ai dùng là một quyết định cần lý do, không phải
một mục trong danh sách.

🔴 Và `chatltt_conversation` có **220 hàng thật** nghĩa là P07 **không còn là
đất trống về mặt di trú**: mọi cột thêm vào bảng ấy chạm dữ liệu khách đang
sống. Add-only + nullable là bắt buộc, không phải tuỳ chọn.

---

## §2 — Một cái bẫy tôi suýt dính, ghi lại vì nó rẻ để lặp

`git grep AppProject` trúng `apps/chatltt/services/hoi_thoai.py:135`. Đọc lướt
thì kết luận *"ChatLTT đã dùng `app_projects`"*. Đọc thật thì đó là một **chú
thích** mượn con số 30 ngày:

> *"30 ngay la cua so ma `AppProject` cua nen tang da chon cho dung viec do
> (Q89), nen dung lai no thay vi phat minh mot con so thu hai."*

⇒ ChatLTT **chưa** dùng `app_projects` một lần nào. Cùng hình dạng với hai lần
đã dính hôm nay: `grep` trúng **thứ đại diện** cho một khái niệm, không phải
**chỗ dùng** nó.

---

## §3 — Ba quyết định phải chấm TRƯỚC khi viết mã

### D1. `projects` dùng `app_projects`, nhưng liên kết **không** nằm trong `payload`

`app_projects.payload` là JSON do app sở hữu — hợp cho *cấu hình* của một
project (tên, chỉ dẫn, tool cho phép). Nhưng *"project gom chat/tệp"* nghĩa là
`chatltt_conversation` và `chatltt_tep` phải **thuộc về** một project, và một
danh sách id trong JSON không có ràng buộc, không có chỉ số, không xoá theo
tầng được.

⇒ **Cấu hình ở `app_projects.payload`; liên kết ở một cột `project_id` trên
chính bảng nội dung.** Đó là cùng một phép chia đã dùng ở P06 bước 2: byte ở
`storage`, liên kết ở `chatltt_tep`.

⚠️ Cột ấy phải **nullable**: 220 hội thoại đang sống không thuộc project nào, và
sẽ tiếp tục không thuộc project nào. Project là **tuỳ chọn**, không phải một
tầng bắt buộc mọc thêm trên đầu mọi người.

### D2. `agents` — chưa làm, và lý do là một PHÉP ĐO chứ không phải một linh cảm

`apps/agent` đã hứa đúng thứ P07 định hứa: *"biến mục tiêu thành kế hoạch nhiều
bước, báo giá trước và chạy có kiểm soát"*. Nó có `platform_core/agent/budget`
(quote/approve/settle), `validator.validate_plan`, `tools.discover_tools`.

Còn "custom agent" của P07 là một thứ **khác**: một **cấu hình lưu lại** (model
nào, tool nào, trần chi tiêu bao nhiêu, chỉ dẫn gì) gắn vào hội thoại — không
phải một cỗ máy lập kế hoạch.

🔴 Hai thứ khác nhau, nhưng chúng **trông giống nhau với người dùng**, và một
sản phẩm có hai thứ tên "agent" là một sản phẩm khó giải thích.

⇒ **Hoãn `agents` sang cuối P07**, sau memory và projects. Và điều kiện để làm
nó không phải "tới lượt" mà là: **trả lời được vì sao khách sẽ dùng nó trong
khi họ không dùng `apps/agent`**. Nếu câu trả lời là "vì nó nằm trong ChatLTT"
thì thứ cần làm là **đưa `apps/agent` vào ChatLTT**, không phải viết lại nó.

⛔ Ghi là **CHƯA CHẤM**, không phải DEFERRED — DEFERRED là thứ đã quyết không
làm (`04_ACCEPTANCE_SCORECARD.md`); đây là thứ chưa đủ dữ kiện để quyết.

### D3. `memory` — cửa nguy hiểm nhất của cả làn B

Kế hoạch tổng đòi: *"ba tầng memory tách bạch, người dùng **thấy và sửa được**,
không âm thầm lưu mọi thứ"*.

⭐ Vế cuối là vế chịu lực. Một hệ memory ghi âm thầm là một hệ mà **người dùng
không biết mình đã nói gì cho nó** — và ngày họ phát hiện, thứ họ mất không phải
một tính năng mà là niềm tin. Nên thứ tự phải là: **hiện ra và xoá được TRƯỚC,
tự động ghi SAU**. Ngược lại là dựng một cái hộp đen rồi mới lắp cửa sổ.

---

## §4 — Thứ tự làm

| # | Việc | Vì sao trước/sau |
|---|---|---|
| 1 | **Bảng memory + cửa quyền + xem/sửa/xoá** (chưa tự ghi) | Cửa xem phải có trước nội dung để xem; xem §3 D3 |
| 2 | **Ghi memory CÓ CHỦ Ý** — người dùng bấm "nhớ điều này" | Một đường ghi mà người dùng khởi xướng thì không có gì để giấu |
| 3 | **Ba tầng tách bạch** + thứ tự ưu tiên chỉ dẫn | Cần 1–2 tồn tại mới đo được ưu tiên |
| 4 | **`project_id` trên `chatltt_conversation`/`chatltt_tep`** (nullable) | Chạm 220 hàng thật ⇒ add-only, và sau khi memory ổn |
| 5 | **Cấu hình project** ở `app_projects.payload` + phạm vi tìm kiếm theo project | Cần 4 |
| 6 | **Mở cho model** (đọc memory / tìm trong project) | **Bước cuối**, đúng luật P05/P06 |
| — | `agents`, `skills` | **CHƯA CHẤM** — xem D2; xét lại sau bước 6 |

⛔ **Tự động ghi memory KHÔNG nằm trong sáu bước trên.** Nó là thứ đổi quan hệ
giữa sản phẩm và người dùng, và nó chỉ được xét sau khi cửa xem/sửa/xoá đã chạy
thật với dữ liệu thật.

---

## §5 — Ràng buộc chép sang từ P06, vì chúng đã trả giá

1. **Bề mặt quyền mới ⇒ test ACL trước, không sau.** Bốn hạng mục P07 đều là bề
   mặt quyền mới; kế hoạch tổng nói thẳng điều đó.
2. **Lớp mới không được vay bất biến của lớp dưới.** P06 bước 5 có một phép kiểm
   *không thể đỏ* đúng vì tôi vay — cảnh phân biệt được phải là cảnh **chéo**.
3. **Phạm vi không được là tham số của model.** `boi_canh` của `thi_hanh()` đã
   có từ P06 bước 6; memory và project dùng lại đường ấy, không mở đường mới.
4. **Governance CONTENT, không OPERATIONAL.** Lần thứ tư của cùng một ca. Memory
   là tri thức khách gửi ta; một bảng tự già đi sẽ xoá nó trong im lặng.

---

## §6 — Điều kiện dừng của P07

- Người dùng **xem, sửa, xoá** được mọi mục memory của mình — có phép kiểm.
- Không một đường nào ghi memory mà người dùng không khởi xướng — có phép kiểm
  quét, không phải một dòng ghi chú.
- Project là **tuỳ chọn**: 220 hội thoại không thuộc project nào vẫn chạy đúng.
- `agents`/`skills` được **chấm hoặc ghi rõ vì sao chưa chấm**, không im lặng.
- Gate đầy đủ PASS, `cay_da_doi_giua_chung = False`.
