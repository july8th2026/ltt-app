# P02 · ADR — KIẾN TRÚC ĐIỀU PHỐI TOOL

*H44 · 2026-09-05 · trạng thái: **ĐỀ XUẤT** · đầu vào: P00 (`00_GAP_MATRIX.md`) +
P01 (`01_PHAN_QUYET.md` PASS).*

## 1. Quyết định

> **Phương án A — ChatLTT tự sở hữu bộ điều phối, đứng trên primitive đã có
> của nền tảng.** Không dựng kernel chung ở `platform_core`, không thêm runtime
> đồ thị ngoài, không fork LibreChat.

Kèm bốn ràng buộc, mỗi cái có ADR/mục riêng:

| | Ràng buộc | Ở đâu |
|---|---|---|
| R1 | mất suất giữa vòng ⇒ `WAITING_SLOT`, không giữ lease cả run | `02_ADR_R1_MOT_SUAT.md` |
| R2 | tiền của **một lượt** tổng hợp theo `run_id`, không dựng sổ thứ hai | §5 |
| R2b | làm tròn C1 trên lượt agentic — **cần chủ dự án chốt** | §6 |
| A5 | bộ hiển thị phải bỏ qua khối lạ | P03 |

## 2. Bốn phương án, chấm theo mười tiêu chí

Thang 0–5. Trọng số không đều — ba tiêu chí đầu là **điều kiện**, không phải sở thích.

| Tiêu chí | **A** ChatLTT tự lo | **B** kernel chung ở `platform_core` | **C** runtime đồ thị ngoài (LangGraph) | **D** fork/dùng backend LibreChat |
|---|:--:|:--:|:--:|:--:|
| **An toàn tiền** (điều kiện) | **5** — dùng thẳng `credit`/`thanh_toan` đã có 19 tệp test ghim | 4 | 2 — checkpointer không biết `credit`, dễ sinh sổ thứ hai | **1** — LibreChat có mô hình billing riêng |
| **Không trùng lặp** (điều kiện) | **5** — `runtime_noi_bo` đã là kernel mỏng (D3) | 3 — thêm một tầng nữa giữa app và facade | 2 | **0** — trùng toàn bộ auth/billing/job |
| **Không chạm lõi** (điều kiện) | **5** | 1 — theo định nghĩa phải sửa `platform_core` | 4 | 3 |
| Độ bền / nối lại | 4 — `chatltt_run` bền + `job_runner` | 4 | **5** — đó là điểm mạnh của LangGraph | 3 |
| Job bất đồng bộ | **5** — `job_runner`+`leases` đã có | 5 | 2 — phải bắc cầu sang job LTT | 2 |
| HITL bền | 4 — `chatltt_approval` mới | 4 | **5** — `interrupt` là primitive sẵn | 4 |
| Tích hợp registry | **5** — `catalog.project_tool` dùng lại được | 4 | 2 | 1 |
| Kiểm thử | **5** — khuôn `test_600`/`test_800` đã có | 4 | 3 | 2 |
| Vận hành | **5** — không thêm tiến trình, không thêm phụ thuộc | 4 | 3 | 1 |
| Tương lai MCP / research | 4 | 4 | 4 | **5** — họ đã có sẵn |
| **Tổng** | **47** | 37 | 32 | 22 |

### Vì sao ba tiêu chí đầu là **điều kiện**, không phải điểm

Một phương án thua ở "tương lai MCP" thì chỉ là làm thêm việc sau. Một phương
án thua ở **an toàn tiền** thì hỏng theo kiểu không sửa được bằng làm thêm: nó
đã thu sai của khách. `docs/AUDIT_MVP_2026-07-31.md` và 19 tệp test quanh
`thanh_toan`/`gia_token` là thứ đã trả giá để đúng.

⇒ **D bị loại ngay ở điều kiện 1 và 2**, không cần cộng điểm: LibreChat là
Node.js với billing/auth riêng, còn LTT là Python/FastAPI với sổ credit đã có
19 tệp test. Fork nó nghĩa là hai runtime, hai sổ tiền, hai đường xác thực —
đúng thứ `CLAUDE.md` gọi là *"mời một sổ tiền thứ hai"*.

### C (LangGraph) — mạnh thật, nhưng mạnh ở chỗ ta đã có

LangGraph thắng ở **độ bền** và **HITL** — hai điểm 5 duy nhất của nó. Nhưng:

| LangGraph cho | LTT đã có | Ai thắng |
|---|---|---|
| checkpointer | `chatltt_execution` (ghi partial 1 s/200 ký tự) + `job_runner` | hoà, và LTT biết `credit` |
| `interrupt`/resume | `chatltt_approval` (chưa xây) + `leases` | LangGraph, nhưng chênh nhỏ |
| đồ thị nhiều nhánh | máy trạng thái **10 trạng thái** (§`02_STATE_MACHINE.md`) | LTT — đồ thị này quá nhỏ để cần một thư viện |

⛔ Và cái giá thật: checkpointer của LangGraph **không biết** `admission`,
`credit`, `job_runner`. Mọi lần nối lại phải tự bắc cầu sang ba thứ đó — tức
viết đúng phần khó, cộng thêm một thư viện phải nuôi. Gói prompt nói thẳng:
*"Do not add dependency unless P02 proves it reduces duplication."* P02 không
chứng minh được điều đó.

### B (kernel chung) — đúng về sau, sai về bây giờ

Lập luận cho B: ngày mai một app khác cũng muốn điều phối tool. Đúng — nhưng:

1. Hôm nay **chưa có app thứ hai** nào cần nó.
2. `platform_core/runtime_noi_bo/` **đã là** kernel mỏng (D3 của H43). Thêm một
   tầng điều phối nữa là thêm tầng thứ ba giữa app và facade.
3. B **theo định nghĩa** phải sửa `platform_core` — nơi có 20 tệp test ghim và
   nằm trong `00_DO_NOT_REWRITE.md`.

⭐ Đường nâng cấp có sẵn và rẻ: xây trong `apps/chatltt/services/` với **ranh
giới sạch** (không import ngược lên `server/`, không biết id model), rồi khi có
app thứ hai thật thì **nhấc nguyên khối** lên `platform_core`. Nhấc một khối đã
chạy được thì dễ; đoán trước hình dạng của nó thì không.

## 3. Kiến trúc chốt

```
apps/chatltt/services/
  dieu_phoi.py     may trang thai cua MOT run: vong model -> tool -> vong model
  chieu_tool.py    registry (da duyet) -> JSON schema OpenAI; dung lai
                   public_api.catalog.project_tool, KHONG viet phep chieu thu hai
  thi_hanh.py      chay mot tool: validate -> chinh sach -> (duyet) -> goi
                   runtime_noi_bo.job HOAC ham noi bo -> ket qua CO CAU TRUC
  duyet.py         chatltt_approval: ghi/doc quyet dinh, ben qua restart
  gop_manh.py      gop tool_call.delta bi cat manh  (test_800 da ghim: runtime
                   KHONG gop, do la viec cua tang nay)
```

Bốn điểm cắt của `00_CALL_GRAPH.md` §4 giữ nguyên, không thêm điểm thứ năm.

**Bất biến giữ nguyên, không đàm phán:**

- `mo_luong` vẫn là cửa **duy nhất** tới model. Điều phối gọi nó **N lần**,
  không tự dựng HTTP.
- ChatLTT vẫn **không biết** id model, URL máy B, giá.
- Tiền vẫn đi qua `credit`/`thanh_toan`. `chatltt_run` chỉ **tổng hợp**.
- `chinh_sach.py` vẫn là cổng thứ ba, fail-closed.

## 4. Ranh giới tin cậy — nay có **quan sát**, không chỉ nguyên tắc

| Mệnh đề | Trạng thái | Bằng chứng |
|---|---|---|
| Model là planner **không tin được** | nguyên tắc | — |
| Model **không nghe mệnh lệnh** trong kết quả tool | ✅ **đã đo** | N10: 0/30 vượt rào, và model **gọi tên** được prompt injection |
| Model **tin tuyệt đối dữ liệu** tool | 🔴 **đã đo** | G0-4: 5/5 lặp lại một con số **sai** của tool, không nghi ngờ |
| Duyệt không giả mạo được bằng prompt | thiết kế | duyệt là một hàng CSDL do route có phiên + CSRF ghi |
| Chính sách không đổi được bằng prompt | thiết kế | `chinh_sach.CONG_CU_CHO_PHEP` là hằng số trong mã |

⛔ **Dòng ba lật ngược ưu tiên phòng vệ.** Bề mặt lộ lớn hơn **không phải** lệnh
tiêm — model chống lệnh tốt. Nó là **dữ liệu sai**: một API hỏng, một trang web
lỗi thời, một kết quả RAG lệch đều đi thẳng vào câu trả lời cho khách, không
gặp một lớp hoài nghi nào.

⇒ Kernel phải kiểm **tính đúng** của kết quả tool ở chỗ kiểm được (schema,
khoảng giá trị, đối chiếu nguồn), không chỉ lọc lệnh tiêm. Đặt niềm tin vào
*"model sẽ thấy nó vô lý"* là đặt vào một thứ **vừa được đo là không tồn tại**.

## 5. Tiền: tổng hợp, không dựng sổ thứ hai

`chatltt_run` thêm ba cột **dẫn xuất**: `credit_giu_tong`, `credit_thu_tong`,
`credit_hoan_tong` — cộng từ các `chatltt_execution` con, mỗi cái vẫn ứng với
đúng một `request_id` trong `credit_entries`.

⛔ Không có bút toán nào ghi ở tầng `run`. Đối soát vẫn là: một `request_id` ↔
một dòng sổ. `run` chỉ trả lời câu *"lượt này tốn bao nhiêu"* mà hôm nay không
ai trả lời được.

## 6. 🔴 Câu duy nhất cần chủ dự án — làm tròn C1

`thanh_toan.py` làm tròn **LÊN credit nguyên mỗi lượt gọi**, tối thiểu 1. Một
lượt agentic 8 vòng: **2,3 credit thật → thu 8 credit** (gấp 3,5 lần).

| PA | Nội dung | Được | Mất |
|---|---|---|---|
| **a** | C2 cho mọi lượt (sổ tích luỹ phần lẻ) | đúng nhất; sửa cả cửa API | đụng `thanh_toan.py` — module tiền |
| **b** | C2 **trong phạm vi một run** (làm tròn một lần ở cuối) | hẹp, đủ giải bài của V3 | hai luật làm tròn cùng tồn tại |
| **c** | giữ C1, **nói thẳng chi phí trên thẻ duyệt** | không đụng tiền | khách trả gấp 3,5 lần và biết điều đó |

⭐ Đề xuất **b**. Lý do: `thanh_toan.py` **tự để ngỏ** C2 và ghi rõ *"nó chỉ đụng
module này, không đụng `gia_token.py`"* — ranh giới đã vẽ sẵn. Và (b) thu hẹp
thay đổi vào đúng dạng tải mới (một run nhiều vòng) mà không đổi cách tính của
lượt đơn lẻ đang chạy production.

⛔ **Không được chọn (c) mà im lặng.** Giữ C1 thì phải nói ra — đó chính là điều
`thanh_toan.py` đã làm khi khai `toi_thieu_moi_luot_credit = 1` ra API công khai.

**Tôi đi tiếp với giả định (b)** và thiết kế `chatltt_run` sao cho cả ba phương
án đều lắp được: ba cột tổng là dẫn xuất, nên đổi luật làm tròn **không đổi
schema**.

### 6b. 🔴 Nhưng (b) KHÔNG nằm trọn trong `apps/chatltt/` — đo được, không suy

Phiên điều phối chốt (b) và dặn: *"`platform_core/llm/thanh_toan.py` không nằm
trong ranh giới của bạn — nếu (b) buộc phải sửa tệp này, báo trước."* Tôi đã
truy đường quyết toán, và **nó buộc thật**:

```
mo_luong()  ->  _phat()  ->  finally:
                              luong.py:381  thanh_toan.quyet_toan_hoac_hoan(...)
                                              -> gia_token.tinh()
                                              -> tong_credit_lam_tron_len   <- C1 o DAY
```

Mỗi lời gọi `mo_luong` **tự quyết toán và tự làm tròn**, ngay trong `finally`.
Một run 8 vòng ⇒ 8 lần làm tròn lên, xong trước khi ChatLTT kịp cộng gì.

**Bốn đường, và ba đường đầu đều vướng:**

| Đường | Vướng ở đâu |
|---|---|
| Sửa `thanh_toan.py` thêm cửa "cộng dồn, chưa làm tròn" | **ngoài ranh giới** của tôi (điều phối đã dặn báo trước) |
| Hoãn quyết toán tới lúc đóng run | ⛔ phá bất biến `00_DO_NOT_REWRITE.md` §2: *"quyết toán trong `finally`, không phải sau vòng lặp — khách đóng kết nối thì `GeneratorExit` ném ngay chỗ `yield`"*. Run chết ⇒ **không thu, không hoàn**, tiền treo |
| Hoàn bù ở cuối run | tạo **đường bút toán thứ hai** — đúng thứ §5 cấm |
| Dùng **một `request_id` cho cả run** (giữ một lần, quyết toán một lần) | 🟢 khả thi: chỉ cần `chuan_bi` nhận `request_id` sẵn có — `luong.py` **nằm trong** ranh giới của tôi. Nhưng phải giải: `_phat().finally` chạy N lần trên **cùng** một `request_id`, mà `credit.quyet_toan` không thiết kế cho việc đó |

⇒ **Đường thứ tư là đường duy nhất đi được**, và nó vẫn cần một quyết định
thiết kế thật ở P04: quyết toán một lần cho cả run **mà không** đánh mất tính
chất *"khách ngắt giữa chừng vẫn thu đúng phần đã sinh"*.

⭐ Nghĩa là (b) **rẻ hơn (a)** nhưng **không miễn phí** như phán quyết giả định.
Nó không phải một hằng số đổi chỗ; nó là một thay đổi ở tầng quyết toán, chỉ
nhỏ hơn (a) ở chỗ nó **không chạm cửa `/api/v1`**.

### 6c. 🟢 Trần tôi tưởng có — nó KHÔNG tồn tại. Đã chứng minh và đã ghim.

Bản trên nêu một lo: phần thu mỗi vòng của C2-tích-luỹ có thể vượt phần giữ chỗ
của chính vòng đó, đụng `charged = min(provider_actual, held)` (`credit.py:408`)
và **thu thiếu trong im lặng**. Ba đường vá được liệt kê.

**Cả ba đều thừa.** Với `E_k` = chi phí chính xác tích luỹ, `C_k = max(1, ceil(E_k))`,
`c1_k = max(1, ceil(cost_k))`:

> **Δ_k = C_k − C_(k−1) ≤ c1_k với mọi k**, vì `ceil(a+b) ≤ ceil(a) + ceil(b)`.

⇒ **Hold đủ cho C1 hôm nay thì đủ cho C2 ngày mai** — cùng một hold, không nới.
Và phát biểu mạnh hơn: đường mới **đi vào trần nhẹ hơn** đường hiện tại, không
bao giờ nặng hơn.

**Đã kiểm, không chỉ chứng minh:** `tests/test_803_c2_tich_luy_bat_bien.py`
quét 100.000 dãy `cost` ngẫu nhiên trong **miền số nguyên milli-credit** (đúng
miền mã thật chạy, không phải số thực) — 0 vi phạm. Số học thuần, không import
`thanh_toan`/`credit`, nên nó không đỏ vì một phiên khác đang sửa CSDL.

⛔ **Chỗ định lý GÃY**, và nó là quyết định thiết kế chứ không phải chi tiết:
neo vào `C_(k−1)` **dự định**, KHÔNG neo vào `A_(k−1)` **đã thu thật**. Neo vào
số đã thu thì một vòng bị kẹp sẽ khiến vòng sau **đòi bù**, Δ vượt c1, định lý
gãy. Và nó sai cả hợp đồng: `credit.quyet_toan` viết rõ *"phần vượt là variance
**nội bộ của nền tảng**"* — đòi bù là chuyển variance của nhà sang khách.

⭐ Một chỗ phát biểu gốc chưa khớp, ghim luôn: với `cost_1 = 0` thì
**Δ_1 = 0 < c1_1 = 1**, không "bằng nhau". Lệch về phía an toàn, nên định lý
vẫn đứng — nhưng nó là **một quyết định sản phẩm đội lốt chi tiết số học**:
một vòng không tốn gì thì C2 thu 0, C1 thu 1. ⇒ P04 phải trả lời riêng: run có
tổng chi phí 0 thì thu 0 hay sàn 1? Sàn là **luật ở tầng run**, không phải hệ
quả của phép làm tròn.

Tôi vẫn đi tiếp với (b) như điều phối chốt. Việc thiết kế quyết toán thuộc
**P04**, không phải P03 — nên nó không chặn kernel.

## 7. Đường lùi

| Tầng | Cách lùi | Mất gì |
|---|---|---|
| Cờ `LTT_CHATLTT_V3_TOOLS=0` | `params` không mang `tools` | V3 tắt, V1 nguyên vẹn — **không** cần rollback CSDL |
| Cờ `LTT_CHATLTT_V3_PAID_TOOLS=0` | tool có phí không được chiếu | tool miễn phí vẫn chạy |
| Migration | ba bảng mới **chỉ thêm**, không sửa bảng cũ | hạ migration = mất `run`/`step`/`approval`, hội thoại cũ **không đổi** |
| Mã | `git revert` phạm vi `apps/chatltt/` | — |

⭐ Điều kiện làm đường lùi này thật: **`chatltt_message.blocks` không đổi hình
dạng**. Khối mới là phần tử mới trong mảng cũ, nên một bản V1 đọc dữ liệu V3
vẫn vẽ được phần nó hiểu và bỏ qua phần lạ — với điều kiện A5 (bộ hiển thị bỏ
qua khối lạ) được chốt bằng test ở P03.
