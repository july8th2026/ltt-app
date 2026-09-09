# 00 — TIẾN ĐỘ & KẾ HOẠCH KHẢO SÁT WORKFLOW V2

> Bảng theo dõi. Phiên nào tiếp nhận chương trình này **đọc tệp này trước**.
>
> **Cập nhật:** 2026-09-07 · ✅ **TOÀN BỘ 8 PHA ĐÃ XONG.** Chờ phê duyệt trước khi viết mã.

---

## 1. TÌNH TRẠNG

| Pha | Nội dung | Tài liệu | TT |
|---|---|---|:--:|
| **A** | Đo LTT thật | `01` `02` | ✅ |
| **B** | Thu thập OSS | `03` | ✅ |
| **C** | Đọc mã 7 kho | `04` `05` `06` `07_08` `09` `10` | ✅ |
| **D** | So sánh ngang | `12_19` | ✅ |
| **E** | Chấm điểm · khoảng trống · ma trận | `12_19 §20` · `21_22` | ✅ |
| **F** | Thiết kế đích | `23_24` `25_26` | ✅ |
| **G** | Đường đi | `27_29` | ✅ |
| **H** | Quyết định | `30` (gồm ADR-WF-001) · `00_EXECUTIVE_SUMMARY` | ✅ |

```
A ████████████  B ████████████  C ████████████
D ████████████  E ████████████  F ████████████
G ████████████  H ████████████   ← HOÀN TẤT
```

**Gộp tài liệu:** 31 tài liệu của đề bài → **11 tệp**. Gộp khi nội dung tổng hợp
từ cùng nguồn (`12_19`, `21_22`, `07_08`); **không** gộp khi khác nguồn bằng chứng.

---

## 2. KẾT QUẢ CỐT LÕI TỪNG TÀI LIỆU

| # | Tệp | Kết quả quyết định |
|---|---|---|
| 01 | `CURRENT_LTT_ARCHITECTURE` | 🔴 **0 job `agent.advance` / 28 ngày** — engine **chưa từng chạy production**. `31+N` câu SQL/tick · trần cứng 4 step · chỉ page đang mở được chạy · edge không mang dữ liệu. Phụ lục A: log thật |
| 02 | `LTT_WORKFLOW_V2_REQUIREMENTS` | **41 yêu cầu có ID** · 33 MUST · **10 ngưỡng nghiệm thu bằng số** (`M1`–`M10`) · 4 ranh giới bất khả xâm phạm |
| 03 | `REPOSITORY_MANIFEST` | 7 kho ghim tag+SHA · 1,0 GB · `D:\LTT_ARCHITECTURE_LAB\` · cảnh báo AGPL/Sustainable Use |
| 04 | `ACTIVEPIECES` ⭐5 | **Waitpoint + `BarrierPolicy` + `sealed` + `NOT_DISPATCHED`**. 🔴 cây không phải đồ thị; tuần tự tuyệt đối |
| 05 | `N8N` ⭐6 | **`binary-data` id `<mode>:<fileId>`**; **cạnh có kiểu** → loại thứ ba `RESOURCE`. 🔴 trạng thái một cột `text`, phải đẩy ra `fs/s3/az` |
| 06 | `NODE_RED` ⭐3 | **6 hook trên đường định tuyến cạnh**; kho đầu tiên đan xen thật. 🔴 **không lưu byte trạng thái nào**. 📐 canvas tự viết **10.203** vs LTT **2.061** |
| 07_08 | `KESTRA_WINDMILL` ⭐4/⭐9 | **`Concurrency{limit, behavior}`** · **`finally`** · **`parallel`/`parallelism` theo NODE (biểu thức)** · **`mock` trong lược đồ** · 11 gói trigger |
| 09 | `TRIGGER_DEV` ⭐7 | **Chuỗi ảnh chụp BẤT BIẾN** (mô hình C) · **lọc hàng đợi hết sức chứa trước khi chọn** · waitpoint 3 bảng nhiều-nhiều |
| 10 | `TEMPORAL` ⭐11 | **Cách VIẾT bảo đảm** (*at least once **or** at most once* = hợp đồng với mã người dùng) · máy chủ chỉ **ĐẾM** vi phạm tất định ⇒ **không chọn replay** |
| 12_19 | `TONG_HOP_SO_SANH` | Chốt **`Q1` `Q3` `Q5` `Q7`** · bảng điểm 7 kho · ma trận giấy phép |
| 21_22 | `GAP_VA_MA_TRAN` | **47 khoảng trống** có mã `G01`–`G47` · ma trận **KEEP 13 · ADAPT 14 · REWRITE 4 · IGNORE 8 · ADOPT 0** · thứ tự thi hành 5 đợt |

---

## 3. BẢY CÂU HỎI ĐÃ CHỐT · MỘT CÒN MỞ

| # | Câu hỏi | Chốt | Mức | Ở đâu |
|---|---|---|---|---|
| `Q1` | Điều kiện: cạnh hay node Router? | **trên CẠNH** + `skip_if` cấp node | `HIGH` | `12_19 §13.2` |
| `Q3` | Trạng thái: bảng sửa được hay event log? | **mô hình C — ảnh chụp bất biến** | `HIGH` | `12_19 §16.2` |
| `Q5` | Ngôn ngữ biểu thức? | **tập toán tử cố định**; ngoại lệ `parallelism` | `HIGH` | `12_19 §13.3` |
| `Q7` | Giữ React Flow? | **GIỮ** (đối chứng 5× Node-RED) | `CONFIRMED` | `12_19 §14` |
| `Q2` | JSONB / bảng chuẩn hoá / lai? | **LAI** — JSONB là chân lý, bảng là chỉ mục dẫn xuất | `HIGH` | `23_24 §2` |
| `Q4` | LISTEN/NOTIFY hay bảng đánh thức? | **bảng `wakeup`** là chân lý; NOTIFY chỉ gia tốc | `HIGH` | `23_24 §3` |
| `Q6` | Bỏ hẳn Plan v1? | ⬜ **chờ số đếm production** — nhưng **không chặn**: hình dạng đã rõ (không lớp tương thích; nếu có bản nháp thì một script chuyển một lần) | | tài liệu 27 |
| `Q8` | Nhận `AiTransform`? | **KHÔNG** dạng Windmill; **CÓ** dạng `ai_choice` bị chặn 3 ràng buộc | `HIGH` | `25_26 §3` |

---

## 4. SỔ NỢ — hoãn CÓ CHỦ Ý

⛔ Không phải danh sách việc quên. Mỗi dòng kèm **cái giá của việc hoãn**.

### N1 — Nhánh "đồ thị node media" (ComfyUI) — **HOÃN 2026-09-07**

**Quyết định:** người dùng — *"tạm chưa dựng node dựng video, tập trung các hạng
mục khác"*.
**Hệ quả:** không clone ComfyUI; tài liệu `11` thu hẹp, ưu tiên thấp.

🔴 **Giá phải trả.** Bảy kho đã đọc **không kho nào** có bài toán *"một node =
20 phút GPU, output 2 GB"*. Ba yêu cầu sau **không có đối chứng ngành**:

- `WF-202` lập lịch quanh **một** suất tài nguyên khan hiếm (`F2`: 92 %)
- `WF-403/404` khai VRAM · thời lượng ước tính là đầu vào lập lịch
- `WF-601/602` artifact hàng GB qua nhiều bước

⇒ Ở tài liệu 23 ba mục này phải mang nhãn **`INFERRED — không có đối chứng
OSS`**, không được trình bày như đã được ngành kiểm chứng.

⚠️ **Không bị hoãn:** `F4` (*"LTT không phải Zapier"*) vẫn nguyên hiệu lực — nó
đo từ **log production của chính LTT**, không phải từ ComfyUI.

**Gỡ nợ khi:** trước khi thiết kế node media/GPU thật của V2.

### N2 — Nguyên mẫu chạy thật (đề bài §9) — **CHƯA LÊN LỊCH**

Đã làm **tĩnh** (đọc mã) cho cả 7 kho. **Chưa chạy** thí nghiệm nào: giết worker
giữa chừng · đo ForEach song song · soi trạng thái CSDL · sửa workflow khi đang
chạy.

**Giá:** các nhãn `UNKNOWN` còn lại tập trung ở đúng chỗ quan trọng — *"thử lại
một phần tử ForEach"*, *"tiếp tục bộ sưu tập dở sau crash"*, *"hiệu quả thật của
lọc sức chứa"*.

**Nếu làm:** chỉ 2 hệ — **Trigger.dev + Temporal**. Cần Docker+Postgres+Redis,
vài GB mỗi kho. ⚠️ **Ổ D: còn 41 GB/466 GB (92 %)** ⇒ chuyển lab sang **ổ C:**
(459 GB) trước.

---

## 5. MỘT VIỆC CẦN NGƯỜI DÙNG

| # | Việc | Vì sao | Ảnh hưởng |
|---|---|---|---|
| **D2** | Đếm `AgentWorkflow`/`AgentRun` trong CSDL production | `LTT_DATABASE_URL` ở `secrets/` — ACL chặn **cố ý** (W1.5) | `Q6`: nếu **0** ⇒ bỏ hẳn Plan v1, di trú thành bài toán rỗng |

⛔ **Không phải việc cần quyết:** thư mục cũ trên
`C:\LTTPlatform\app\docs\architecture\`. Bị chặn bởi luật `deny` **do chính
người dùng viết** (`Edit/Write(//C:/LTTPlatform/app/**)` + `Bash(rm -rf:*)`), và
cả hai luật **đúng** (`CLAUDE.md`: *"Đừng bao giờ sửa file trực tiếp trong
`app\`"*). Khuyến nghị **giữ nguyên luật**; deploy sau sẽ chép đè.

---

## 6. 21 SỬA ĐÃ TÍCH LUỸ CHO TÀI LIỆU 02

Đọc mã người khác đã sửa yêu cầu của chính ta **21 lần**. Danh sách đầy đủ ở
`12_19 §22`. Hai yêu cầu **mới** (`WF-209` `finally` · `mock` trong lược đồ) và
một câu hỏi **mới** (`Q8`).

⚠️ Tài liệu 02 **chưa được sửa tại chỗ** — 21 sửa đang nằm ở `12_19 §22` và sẽ
được hợp nhất khi viết tài liệu 23/24/25. *(Cố ý: sửa 02 giữa chừng sẽ làm mất
dấu vết "yêu cầu ban đầu của ta là gì trước khi nhìn ai khác" — thứ đề bài §3
yêu cầu giữ.)*

---

## 7. RÀNG BUỘC ĐANG THI HÀNH

- ⛔ **Không sửa mã sản phẩm LTT.** Chỉ ghi vào `docs/architecture/workflow_v2_audit/`.
- ⛔ **Không commit, không ff, không deploy.**
- ⛔ **Không chép mã** n8n (Sustainable Use) hay Windmill (AGPL).
- ⛔ **Không đọc** tệp `.ee.` của n8n, `packages/ee/` của Activepieces.
- ⛔ **Điểm dừng: hết tài liệu 30.** Không viết mã sản phẩm cho tới khi được duyệt.
- ✅ Mọi kết luận gắn **kho + SHA + tệp + hàm**, có nhãn
  `CONFIRMED`/`HIGH`/`INFERRED`/`UNKNOWN`.
- ⚠️ **Kho nhiều phiên** — chỉ đụng thư mục của mình; một dòng `??` lạ là phiên
  khác đang làm việc.
- ⚠️ **Trước mọi lệnh nặng:** `python tools\cua_so_yen.py trang-thai` **và** kiểm
  tải CPU.

---

## 8. CÒN LẠI

| Pha | Tài liệu | Ước lượng |
|---|---:|---:|
| G — đường đi | `27` `28` `29` | 1–2 lượt |
| H — quyết định | `30` · ADR · `00_EXEC` | 1–2 lượt |
| **Còn lại** | **6** | **2–4 lượt** |

*(Ước lượng ban đầu 18–22 lượt; đã dùng ~8 nhờ gộp tài liệu.)*

**Đã xong 13 tệp / 6.709 → 7.059 dòng.** Pha G thu hẹp mạnh so với kế hoạch gốc:
`27_MIGRATION` gần như rỗng vì **không có runtime nào để di trú** (0 run/28 ngày),
và `28_ROADMAP` đã có sẵn 5 đợt suy ra ở `21_22 §22.4`.
