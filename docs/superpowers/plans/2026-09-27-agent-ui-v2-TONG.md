# Agent UI V2 — Plan TỔNG (điều phối, làn, gate, sổ tiến độ)

> **For agentic workers:** REQUIRED SUB-SKILL: dùng `superpowers:subagent-driven-development`
> (khuyến nghị) hoặc `superpowers:executing-plans` để thi hành từng plan pha.
> Tệp này KHÔNG có task thi hành — nó là **hợp đồng điều phối** giữa các làn.

**Goal:** Đưa LTT Agent/Automation Studio từ 25,7/100 (có trọng số) lên mức dựng được
workflow thật, bằng nhiều làn agent chạy song song mà **không tạo bug chồng chéo**.

**Architecture:** Hai pha **tuần tự bắt buộc** (UI-0 sửa lỗi cơ khí, UI-3 tách
`CanvasShell`) mở khoá cho các làn song song về sau. Trước UI-3, toàn bộ giao diện
nằm trong **một** hàm 740 dòng — tức một chủ sở hữu, tức **không thể song song**.
Việc tách tệp chính là thứ biến song song hoá thành khả thi, không phải một việc dọn
dẹp làm-cũng-được.

**Tech Stack:** React 19 · `@xyflow/react` 12.11.2 · TypeScript 5.9 · Vite 8 ·
vitest 4 · FastAPI · SQLAlchemy · Playwright (qua `playwright-cli`).

**Spec:** `docs/architecture/agent_ui_v2/` — đọc `00_EXECUTIVE_SUMMARY.md` trước,
rồi `09_TARGET_DESIGN.md` (thiết kế đích) và `10_IMPLEMENTATION_PLAN.md` (lộ trình).

## Global Constraints

Mọi task ở mọi pha đều ngầm mang các ràng buộc này. Chép nguyên văn từ spec.

- ⛔ **KHÔNG chạy gate trong phiên** — không L1, không L2, không L3. Gate chạy **MỘT
  lần ở CUỐI PLAN**, và chỉ **MỘT cấp**. Xong một pha/task/nhánh/lần gộp `main`
  **KHÔNG** phải cuối plan. (CLAUDE.md luật 1, chốt 25/09.)
- Trong phiên: test NHẮM cụm vừa sửa — `python tools\thanh_phan.py --test <tp>` rồi
  `python -m pytest <tệp> -q`.
- Gộp `main`: test nhắm xanh là ĐỦ. Gộp xong chạy `pre-commit run --all-files`.
- Lệnh nặng đi qua `python "C:\Users\Thang Tuong\.claude\ltt\chay_nang.py" --phien <làn> -- <lệnh>`,
  `-n` ≤ 7. ⛔ Không chạy lệnh nặng ngoài khoá. Nhả khoá **ngay khi tính xong**.
- ⛔ **KHÔNG bọc `pytest` trong `chay_nang.py`** khi ≥ 20 tệp test: `conftest` tự xin
  `cpu_nhieu` và không nhận ra `chay_nang.py` là tổ tiên ⇒ tự khoá chính mình.
- Ghi cấu hình KHÔNG BOM · `.ps1` thuần ASCII · ⛔ không viết Python inline qua PowerShell.
- ⛔ KHÔNG deploy từ cây riêng. Deploy xuất HEAD cây chính.
- Đổi CSS/JS tĩnh ⇒ cache-bust (`server/templating.py:ASSET_VER`).
- Đổi giao diện ⇒ kiểm bằng trình duyệt thật (Playwright), ⛔ không đọc mã rồi
  tuyên bố xong. Hai chế độ kiểm bắt buộc — xem **Phần 3b**.
- Frontend giữ **schema-driven**: thêm một app KHÔNG được sửa một dòng nào trong
  `frontend/agent-canvas/src/`.
- ⛔ Không bảng tra tên app/tool/nhãn trong frontend (`test_967` đếm hàng chết).

---

# PHẦN 1 — CrewAI và các nguồn khác nói gì về lộ trình

## 1.1 Phát hiện định hình lộ trình mạnh nhất

CrewAI **có hai sản phẩm, không phải hai giai đoạn của một sản phẩm**:

| | CrewAI-Studio (OSS, MIT) | Crew Studio trong AMP (SaaS đóng) |
|---|---|---|
| Hình dạng | Streamlit, **không canvas**, 8 trang danh sách phẳng | 3 cột: AI Thoughts · canvas node · Resources |
| Soạn | form phẳng 11 trường, một `st.form` | chat + kéo-thả, **chung một state** |
| Phụ thuộc task | **hai ô multiselect** | node nối nhau trên canvas |
| Chạy | `threading.Thread` + `queue` + poll 1 giây | "event timeline" thật |
| Giá | miễn phí | trả tiền |

> **Bài học lớn nhất cho LTT:** form+list và canvas+chat là **hai tầng sản phẩm
> khác nhau**. CrewAI không tiến hoá từ cái này sang cái kia — họ bán hai thứ.

LTT hôm nay đang ở một chỗ kỳ lạ: **có canvas (tầng đắt) nhưng canvas không nối được
dây (chưa bằng tầng rẻ)**. Một form phẳng kiểu CrewAI-Studio, dù thô, vẫn **dựng
được** một automation; canvas của LTT thì không (0/5 luồng).

⇒ **Lộ trình đúng không phải "làm canvas đẹp hơn", mà là "làm canvas đạt mức mà một
form phẳng đã đạt", rồi mới cộng giá trị của canvas lên trên.** Đó chính là thứ tự
UI-0 → UI-3 → UI-4/5/6, và nó xác nhận việc đặt UI-0 lên trước mọi thứ.

## 1.2 Năm điều lấy được từ CrewAI, kèm chỗ chúng vào lộ trình

| # | Quan sát CrewAI | Hệ quả cho lộ trình LTT |
|---|---|---|
| 1 | **Không tầng nào có widget human-in-the-loop** — OSS không, Studio cộng đồng không (issue `#75` mở > 1 năm), **AMP trả tiền cũng chỉ cấp hook `useHumanInTheLoop`, frontend tự dựng UI** | LTT có `core.human` + `NHAN_WAITING_KIND['HUMAN']` **đã chạy ở backend**. Một component duyệt/sửa/từ chối dùng lại được là **lợi thế thật**, không phải đuổi kịp. ⇒ **Nâng UI-8 lên sớm hơn**, và tách "Human approval" thành hạng mục riêng đo được |
| 2 | Hợp đồng `args` / `status` / `respond()` — dừng đúng tại lời gọi tool, phơi nguyên tham số đề xuất, resume bằng một hàm | Đây là hợp đồng cho **core**, không phải UI. LTT nên có một "pause point" chuẩn ở `job_runner.py`/`leases.py` thay vì mỗi tool tự chế ⇒ **một việc backend**, ghi vào sổ chờ, ⛔ không nhét vào plan UI |
| 3 | Studio tách `context_from_async_tasks` / `context_from_sync_tasks` thành **hai** ô — để lộ chi tiết runtime (coroutine chưa resolve) ra tới form | **Bài học NGƯỢC.** LTT đang mắc đúng bệnh này: node hiện `app.video.generate@1`, lỗi hiện `node_khong_ton_tai`, cổng hiện tên kiểu máy. ⇒ UI-4/UI-7 phải có luật *"không rò tên máy ra người dùng cuối"* làm tiêu chí kết thúc |
| 4 | AMP áp thẳng thay đổi AI sinh lên canvas sống, **không diff** — chấp nhận được **chỉ vì** canvas luôn hiện toàn bộ và sửa tay được ngay | LTT **không** ở điều kiện đó: `credit.py`/`jobs.py` có bút toán thật, và `replace` hiện **xoá luôn undo**. ⇒ UI-8 bắt buộc có diff. Xác nhận lại quyết định của spec, không đổi |
| 5 | Nhãn tool tự sinh `"{tên} ({tham số đầu})"` để phân biệt nhiều instance cùng loại | Mẫu nhỏ, rẻ, giải đúng một lỗi LTT sẽ gặp khi một workflow có 3 node `Tạo ảnh AI`. ⇒ gộp vào UI-4 (`nhanNode` hiện chỉ đánh số 1/2/3) |

## 1.3 Đối chiếu với n8n / Activepieces / Langflow

Ba nguồn kia không đổi **thứ tự** lộ trình, chúng đổ đầy **nội dung** từng pha:

- **Activepieces** → UI-5: *"+ Tạo kết nối" là dòng đầu ngay trong dropdown của ô
  auth*, OAuth chạy trong popup để form không mất state. MIT ⇒ **port được**.
- **n8n** → UI-6 (Schema là view mặc định, kéo field sinh biểu thức) và UI-7
  (**dirty node** — trạng thái thứ ba "đã chạy nhưng dữ liệu đã cũ"). Sustainable Use
  License ⇒ ⛔ **chỉ học ý tưởng, không chép một dòng**.
- **Langflow** → UI-4 (cổng **màu theo kiểu** + hiện tương thích **trong lúc kéo**).
  LTT đã có 17 kiểu và 180 cặp hợp lệ ở máy chủ — chỉ thiếu lớp thị giác. MIT.

## 1.4 ⭐ Lộ trình được ĐIỀU CHỈNH sau phân tích này

So với `10_IMPLEMENTATION_PLAN.md`, hai thay đổi có lý do:

| Đổi | Từ | Thành | Vì sao |
|---|---|---|---|
| **A** | UI-8 (Agent Designer) ở gần cuối | **UI-8 tách đôi**: `UI-8a Human approval` lên ngay sau UI-7; `UI-8b Agent Designer diff` giữ chỗ cũ | CrewAI cho thấy human-in-the-loop là khoảng trống của **cả ngành**, và backend LTT đã có sẵn. Đây là giá trị rẻ nhất/đắt nhất tỉ lệ |
| **B** | UI-0 sửa `nextNode` + di trú dữ liệu | **UI-0 sửa CỔNG BIÊN DỊCH trước, không di trú** | xem §1.5 — rẻ hơn, an toàn hơn, sửa luôn mọi bản nháp đang có |

## 1.5 🔴 Cách sửa P0-1 TỐT HƠN cách đã ghi trong audit

`10_IMPLEMENTATION_PLAN.md` đề xuất sửa `nextNode()` ghi `type` thật **cộng một lần
di trú dữ liệu production**. Khi lập plan tôi đọc lại `bien_dich._node` và thấy một
đường rẻ hơn và an toàn hơn hẳn:

```python
loai = str(n.get("type", ""))
if loai.startswith(TIEN_TO_LOI):      # ("core.", "trigger.", "ai.", "connector.")
    return _node_loi(n, nid, loai)    # tra nut_loi -> roi dinh_nghia_piece
if loai == "tool":
    ten = data["tool"]; ...
tool = cc.get(ten)                    # SO CONG CU APP
if tool is None:
    raise LoiBienDich("node_khong_ton_tai", ten, nid)   # ← 55/67 node chet O DAY
```

`_node_loi` **đã** có sẵn đúng chuỗi tra ta cần (`nut_loi.tat_ca()` → `dinh_nghia_piece`).
Node do Canvas tạo chỉ khác ở chỗ loại thật nằm ở `data.tool` thay vì `type`, và
`params`/`settings` nằm dưới `data`. Nên sửa đúng là: **khi sổ công cụ app không có,
nâng `data.*` lên mức trên rồi uỷ quyền cho `_node_loi`.**

| | Cách cũ (sửa `nextNode` + di trú) | **Cách mới (cổng biên dịch)** |
|---|---|---|
| Bản nháp đang có trên production | phải di trú, **rủi ro R1 cao** | **tự chạy được ngay**, không đụng dữ liệu |
| Số tệp sửa | 2 frontend + 1 di trú + kiểm dữ liệu | **1 tệp backend** |
| Đảo ngược được không | khó (dữ liệu đã đổi) | **dễ — revert một commit** |
| Hợp với kiến trúc? | có | có — `_node_loi` **vốn đã** tra hai nguồn |

⇒ **UI-0 làm cách mới.** Việc dọn `nextNode` ghi `type` thật vẫn nên làm, nhưng nó
tụt xuống **UI-3** như một việc dọn dẹp **không khẩn cấp và không rủi ro dữ liệu**,
vì lúc đó cổng biên dịch đã nhận **cả hai** hình dạng.

Đây cũng là lý do plan này tồn tại: đọc lại mã ở mức task làm lộ ra thứ mức audit
không thấy.

---

# PHẦN 2 — Kiến trúc làn song song

## 2.1 Luật nền: làn va nhau ở đâu

Bài học đã trả giá: **luật "một tệp một chủ" ngăn xung đột MERGE, nhưng không ngăn
xung đột NGỮ NGHĨA.** Các làn tụ lại va nhau ở chỗ một làn khai một điều về **CẢ HỆ**.

Trong chương trình này, có đúng **sáu sổ đăng ký dùng chung**. Mỗi sổ phải có
**đúng một làn chủ**:

| # | Sổ dùng chung | Chủ | Làn khác muốn đổi thì |
|---|---|---|---|
| S1 | `frontend/agent-canvas/src/canvas.css` (+ `styles/`) | **UI-2** | mở phiếu cho UI-2, ⛔ không tự sửa |
| S2 | `CanvasShell.tsx` / `features/editor/EditorShell.tsx` | **UI-3** | như trên |
| S3 | `editorState.ts` (reducer + action) | **UI-3** | như trên |
| S4 | `workflowApi.ts` (hình dạng lưu trữ) | **UI-0** rồi **UI-7** | như trên |
| S5 | Bảng định tuyến máy chủ (`apps/agent/routes/`) | **UI-1** | như trên |
| S6 | `tools/thanh_phan.toml` (khai thành phần) | **UI-3** | như trên |

Dải số test **không** nằm trong bảng này vì công cụ đã giải:
`python tools/cay_rieng.py tao <làn>` **tự in dải số riêng** cho cây đó. Mỗi làn đặt
tệp test mới **trong dải của mình** thì không va chạm.

## 2.2 Vì sao KHÔNG song song được ngay từ đầu

```
Hôm nay:  CanvasShell.tsx = 959 dòng, Editor() = 740 dòng, 33 useState, 11 khu vực JSX
       ⇒ MỌI pha UI đều phải sửa tệp này
       ⇒ một chủ sở hữu
       ⇒ song song hoá = xung đột merge liên tục
```

⇒ **UI-3 (tách `CanvasShell`) không phải việc dọn dẹp — nó là ĐIỀU KIỆN của song song
hoá.** Sau UI-3, mỗi thư mục `features/editor/*` có một chủ và các làn chạy thật sự
độc lập.

## 2.3 Sơ đồ làn

```text
  ── TUẦN TỰ (không song song được) ──────────────────────────────

  UI-0  Lỗi P0 cơ khí          ~1 ngày   1 agent
        ↓  (gộp main, deploy độc lập)
  UI-3  Tách CanvasShell       ~2 ngày   1 agent     ← MỞ KHOÁ SONG SONG
        ↓  (gộp main)

  ── SONG SONG ĐỢT 1 (3 làn, không giao tệp) ─────────────────────

  Làn A  UI-2  Design system + theme sáng     chủ S1
  Làn B  UI-1  Automation Studio (IA)         chủ S5      ⚠️ cần Q1
  Làn C  UI-4  Node UX V2                     features/editor/nodes/
        ↓  (gộp lần lượt: A → B → C, mỗi lần pre-commit --all-files)

  ── SONG SONG ĐỢT 2 (3 làn) ─────────────────────────────────────

  Làn D  UI-5  Inspector + Connections        ⚠️ CHẶN bởi Q4 (OAuth)
  Làn E  UI-7  Execution UX + Runs            chủ S4 (đợt này)
  Làn F  UI-8a Human approval  ⭐ mới          features/editor/human/
        ↓

  ── SONG SONG ĐỢT 3 (3 làn) ─────────────────────────────────────

  Làn G  UI-6  Data picker + mapping          cần UI-5 xong
  Làn H  UI-8b Agent Designer + diff
  Làn I  UI-9  Templates + onboarding         cần UI-1 xong
        ↓

  ── TUẦN TỰ CUỐI ────────────────────────────────────────────────

  UI-10 i18n + trợ năng + mobile   (chạm MỌI tệp ⇒ ⛔ không song song)
  UI-11 Nghiệm thu UX + hồi quy
        ↓
  ⭐ GATE — MỘT lần, MỘT cấp, CUỐI PLAN
```

⚠️ **UI-10 không được song song hoá.** Bỏ chuỗi cứng và sửa trợ năng chạm **mọi** tệp
— đó đúng là hình dạng "một làn khai một điều về cả hệ" ở §2.1.

## 2.4 Quy tắc bắt buộc cho mọi làn

1. **Một làn = một cây = một nhánh.** `python tools/cay_rieng.py tao ui4` →
   nhánh `phien/agent-ui-v2-ui4`. ⛔ Không hai làn cùng một cây.
2. **Khai tệp TRƯỚC khi sửa.** Mỗi làn mở phiếu ở `00_SO_TIEN_DO.md` (§4.2) liệt kê
   tệp mình sẽ chạm. Điều phối từ chối nếu trùng chủ sở hữu.
3. **Đụng sổ dùng chung ⇒ DỪNG và báo điều phối.** ⛔ Không tự sửa rồi "để merge lo".
4. **Test mới đặt trong dải số của cây mình** (công cụ in ra lúc tạo cây).
5. **Bất biến mới (invariant) phải báo điều phối trước.** Đây là thứ dễ đụng làn khác
   nhất và nó **xanh riêng, đỏ khi gộp**.
6. **Gộp `main` theo thứ tự điều phối chỉ định**, không tự gộp khi thích.
   Gộp xong chạy `pre-commit run --all-files` — merge KHÔNG chạy bánh cóc.
7. ⛔ **Không chạy gate.** Xem Phần 3.
8. **Báo cáo ≤ 250 từ.** Trạng thái ghi vào sổ tiến độ, không chỉ trong hội thoại.
9. Agent việc cơ học ⇒ `model: "sonnet"`. Opus chỉ cho gỡ lỗi khó/thiết kế.

## 2.5 Ba nguy cơ chồng chéo đã lường, kèm cách chặn

| Nguy cơ | Vì sao nó xảy ra | Chặn thế nào |
|---|---|---|
| UI-2 token hoá CSS trong lúc UI-4 đổi cấu trúc node | cả hai cần `.node-*` | UI-2 chủ S1; **UI-4 gửi danh sách lớp cần cho UI-2 trước khi bắt đầu**, UI-2 tạo sẵn lớp rỗng |
| UI-7 đổi `workflowApi.ts` trong lúc UI-0 vừa đổi cùng tệp | S4 hai chủ theo thời gian | UI-0 **xong và gộp `main`** rồi UI-7 mới mở. ⛔ Không chồng thời gian |
| Hai làn cùng thêm route `/agent/...` | S5 | UI-1 là chủ duy nhất của bảng định tuyến trong cả chương trình |

---

# PHẦN 3 — Luật gate (chốt 25/09, ⛔ không diễn giải lại)

```
TRONG PHIÊN     test NHẮM cụm vừa sửa:
                python tools\thanh_phan.py --test <tp>
                python -m pytest <tệp> -q
                ⛔ KHÔNG chạy gate — không L1, không L2, không L3

GẶP LỖI         sửa TẠI CHỖ -> chạy lại ĐÚNG phép đã đỏ -> đi tiếp

GỘP main        test nhắm xanh là ĐỦ. ⛔ Không gate để gộp.
                Gộp xong -> pre-commit run --all-files

XONG MỘT PHA    test nhắm xanh -> gộp main -> pha kế
                ⛔ KHÔNG gate để "đóng pha"

CUỐI PLAN       MỘT lần, MỘT cấp:
                python tools\gate.py --doi          (L1)
                HOẶC python tools\gate.py --pham-vi <tp>   (L2)
                ⛔ MỘT GATE MỖI NHÁNH — không chạy lần hai, kể cả sau lượt XANH

GATE ĐỎ         sửa tại chỗ -> chạy lại đúng phép đỏ (gate in sẵn lệnh)
                -> KHÉP: python tools\gate.py --doi --tu <sha của lượt gate>
```

**Ba điều dễ làm sai, ghi ra để không ai làm:**

1. 🔴 **"Xong UI-4" KHÔNG phải cuối plan.** Hết một pha/task/nhánh/lần gộp `main`
   đều **không** phải cuối plan. Cuối plan = **hết mọi pha trong tệp này**.
2. 🔴 **Deploy giữa plan phải HỎI chủ dự án.** Deploy cần gate XANH trên đúng SHA
   deploy; gate nay chỉ có ở cuối plan. UI-0 muốn deploy độc lập (và nó **nên**, vì
   B4 đang tiêu tiền thật) ⇒ **đó là một câu hỏi cho chủ dự án**, ⛔ không tự quyết.
3. **Gate chạy ở cây RIÊNG**: `python tools/cay_gate.py chay`. ⛔ Không chạy gate
   trong cây làm việc — một phiên khác gộp giữa lượt sẽ làm bẩn phán quyết.

---

# PHẦN 3b — Kiểm bằng trình duyệt thật (bắt buộc cho MỌI pha)

⛔ **Không pha nào được đánh dấu xong nếu chỉ chạy test và đọc mã.** Ba trong bốn
lỗi P0 của UI-0 **chỉ lộ ra trên layout thật** — jsdom không tính layout nên một
phép so toạ độ trong vitest sẽ **XANH GIẢ**.

## 3b.1 Hai chế độ, dùng ở hai thời điểm khác nhau

| | **Chế độ A — máy chủ cô lập** | **Chế độ B — web thật** |
|---|---|---|
| Khi nào | **trong lúc làm**, mã chưa deploy | **sau khi deploy**, chốt lần cuối |
| Đâu | `http://127.0.0.1:8198` (sqlite riêng) | `https://app.lttstudios.com` |
| Đăng nhập | tài khoản fixture của chính máy chủ đó | `tai_khoan_thu.py --cookie` |
| Chứng minh được gì | mã mới chạy đúng | **thứ khách thật sự thấy** chạy đúng |
| Rủi ro | không có | ghi vào CSDL production dưới tài khoản `.local` |

🔴 **Cả hai đều cần.** Chế độ A không chứng minh được bản deploy; chế độ B không
chạy được trước khi deploy. ⛔ Không thay cái này bằng cái kia.

⚠️ CLAUDE.md luật 7: chốt trên `https://app.lttstudios.com`, **không** chốt trên
loopback — loopback bỏ qua Cloudflare, và Cloudflare đã từng là thủ phạm thật
(asset thử thách chỉ có AAAA, máy không IPv6).

## 3b.2 Chế độ B — công thức chính xác

Nguồn: `docs/TAI_KHOAN_THU.md`. ⛔ **Không gõ mật khẩu vào form** — công cụ đăng
nhập bằng HTTP và chỉ trả cookie phiên.

**Bước 1 — lấy cookie.** Đọc `C:\LTTPlatform\secrets\app.env` cần Administrator,
nên đi qua `nang_quyen.py` (nâng quyền im lặng, ⛔ không phải điểm dừng):

```bash
python tools\nang_quyen.py --lenh "C:\LTTPlatform\venv\Scripts\python.exe tools\tai_khoan_thu.py --app-env C:\LTTPlatform\secrets\app.env --cookie khach1.thu@lttstudios.local"
#   -> session=<giá trị>
```

⚠️ Nếu tài khoản chưa có hoặc hết credit:

```bash
python tools\nang_quyen.py --lenh "C:\LTTPlatform\venv\Scripts\python.exe tools\tai_khoan_thu.py --app-env C:\LTTPlatform\secrets\app.env --tao-bo --nap-den 20000"
```

**Bước 2 — mở Chrome qua Playwright, đặt cookie, vào thẳng trang.**
Mỗi làn dùng **profile riêng** (`-s=<tên làn>`), ⛔ không dùng Chrome thật của chủ
dự án:

```js
// tests/browser/<ten>.js  — chay bang: playwright-cli -s=ui0 run-code --filename=...
async page => {
  const COOKIE = process.env.LTT_COOKIE_THU;   // dat tu Buoc 1
  await page.context().addCookies([{ name: 'session', value: COOKIE,
    domain: 'app.lttstudios.com', path: '/', secure: true, httpOnly: true }]);
  await page.goto('https://app.lttstudios.com/agent/canvas');
  // ... phep do cua pha
}
```

**Bước 3 — luôn thu bốn thứ này, mọi pha:**

```js
const pageErrors = [], consoleErrors = [], failedRequests = [], serverErrors = [];
page.on('pageerror',     e => pageErrors.push(e.message));
page.on('console',       m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
page.on('requestfailed', r => failedRequests.push({url: r.url(), err: r.failure()?.errorText}));
page.on('response',      r => { if (r.status() >= 500) serverErrors.push({url: r.url(), status: r.status()}); });
```

## 3b.3 Ba luật cứng

1. ⛔ **Tài khoản thử chỉ có đuôi `.local`.** Công cụ tự từ chối email khác, và
   ⛔ **không** nâng `role=admin` — nó phải nhìn đúng bề mặt khách hàng.
2. ⛔ **Không chạy `--dat-lai-mat-khau`** trừ khi thật cần: nó thu hồi **mọi** phiên
   cũ của tài khoản đó ⇒ đá văng phiên khác đang dùng cookie.
3. ⛔ **Không dùng dữ liệu production của khách thật.** Tài khoản thử tự dựng dữ
   liệu của nó.

## 3b.4 Mỗi pha phải nộp gì

```
□ Kịch bản `tests/browser/agent_ui_v2_<pha>_nghiem_thu.js` trả {status:'PASS'|'FAIL', so_lieu:{…}}
□ Chạy XANH ở chế độ A (8198) trước khi xin gộp `main`
□ Chạy XANH ở chế độ B (app.lttstudios.com) sau khi deploy — nếu pha được deploy
□ 0 pageerror · 0 console error · 0 request hỏng · 0 phản hồi 5xx
□ Ảnh chụp trước/sau trong docs/architecture/agent_ui_v2/bang_chung/
```

---

# PHẦN 4 — Sổ tiến độ và báo cáo

## 4.1 Ba tệp, ba vai — ⛔ không ba nguồn sự thật

| Tệp | Ai ghi | Chứa gì |
|---|---|---|
| `docs/superpowers/plans/2026-09-27-agent-ui-v2-TONG.md` | điều phối | plan này. **Bất biến** sau khi duyệt |
| `docs/architecture/agent_ui_v2/00_SO_TIEN_DO.md` | **mọi làn** | trạng thái, phiếu tệp, chặn, quyết định |
| `docs/architecture/agent_ui_v2/00_SO_LOI.md` | mọi làn | sổ lỗi hợp nhất + bảng độ phủ |

⛔ **Trạng thái công việc ghi vào TỆP, không chỉ trong hội thoại.** Một phiên bị
`/compact` mất hội thoại; tệp thì còn.

## 4.2 Khuôn sổ tiến độ

`00_SO_TIEN_DO.md` phải bắt đầu bằng đúng bảng này:

```markdown
# Sổ tiến độ — Agent UI V2

Cập nhật lần cuối: <ngày giờ> bởi <làn>

## Bảng pha

| Pha | Làn | Trạng thái | Nhánh | Tệp SỞ HỮU | Gộp main | Ghi chú |
|-----|-----|-----------|-------|-----------|----------|---------|
| UI-0  | —  | CHƯA MỞ | — | — | — | |
| UI-3  | —  | CHƯA MỞ | — | — | — | chặn bởi UI-0 |
| UI-2  | —  | CHƯA MỞ | — | — | — | chặn bởi UI-3 |
...

Trạng thái hợp lệ (⛔ không tự chế thêm):
CHƯA MỞ · ĐANG LÀM · CHỜ DUYỆT · ĐÃ GỘP · CHẶN

## Phiếu tệp đang giữ

| Làn | Tệp | Từ lúc | Sổ dùng chung? |
|-----|-----|--------|----------------|

## Bảng độ phủ nghiệm thu

| Luồng | Dựng được? | Kịch bản Playwright | Pha mở khoá |
|-------|-----------|---------------------|-------------|
| UX-1 Schedule→Sheets→…→YouTube | ❌ | — | UI-5 + backend trigger |
| UX-2 Webhook→… | ❌ | — | backend (chưa có node) |
| UX-3 Manual→Image→Video→Voice | ❌ | — | UI-0 |
| UX-4 Sheets→AI Router→nhánh | ❌ | — | UI-5 + Q11 |
| UX-5 Parent→Subworkflow→Wait→Human | ❌ | — | UI-0 + UI-8a |

## Quyết định đã chốt

| # | Câu | Chốt | Ngày | Ai |
|---|-----|------|------|-----|
| Q1 | Kiến trúc thông tin | CHƯA | | |
| Q4 | Tầng OAuth | CHƯA | | |
| Q11 | Trigger | CHƯA | | |

## Nhật ký (mới nhất ở trên)

- `<ngày giờ>` `<làn>` — <một dòng: đã làm gì, số đo gì>
```

## 4.3 Nhịp báo cáo

| Khi nào | Ai | Gì |
|---|---|---|
| Mở làn | làn | thêm hàng vào *Phiếu tệp*, đổi trạng thái → ĐANG LÀM |
| Xong mỗi task | làn | tick checkbox trong plan pha + một dòng *Nhật ký* |
| Xong pha | làn | test nhắm xanh + **ảnh chụp trình duyệt** + đổi → CHỜ DUYỆT |
| Điều phối duyệt | điều phối | gộp `main` → `pre-commit run --all-files` → ĐÃ GỘP, **trả phiếu tệp** |
| Bị chặn > 30 phút | làn | đổi → CHẶN, ghi rõ **chặn bởi AI/CÁI GÌ và NGÀY** |
| Mỗi lần đo | làn | ghi số vào *Bảng độ phủ*, ⛔ không ghi "đã xong" mà không có số |

🔴 **"Chặn bởi X" phải ghi AI đo và NGÀY.** Một cớ hoãn không có phép đo sau lưng sẽ
biểu hiện thành **sự vắng mặt của công việc**, và không bảng độ phủ nào bắt được vì
không có gì để đếm.

## 4.4 Tiêu chí "xong" của một pha — ⛔ không dùng "trông ổn rồi"

```
□ Test nhắm của cụm vừa sửa XANH (dán lệnh + đuôi kết quả vào sổ)
□ Kịch bản Playwright của pha XANH (nếu pha có mặt giao diện)
□ Ảnh chụp trình duyệt trước/sau trong docs/architecture/agent_ui_v2/bang_chung/
□ Số đo của pha ghi vào Bảng độ phủ (CÓ SỐ, không phải câu mô tả)
□ Không tệp mới nào > 250 dòng
□ Đã trả phiếu tệp
□ ⛔ KHÔNG chạy gate
```

---

# PHẦN 5 — Danh sách pha và plan con

| Pha | Plan chi tiết | Trạng thái plan | Chặn bởi |
|---|---|---|---|
| **UI-0** | `2026-09-27-agent-ui-v2-pha0-p0-co-khi.md` | ✅ **đã viết, sẵn sàng thi hành** | — |
| UI-3 | `…-pha3-tach-canvasshell.md` | ⏳ viết sau khi UI-0 gộp | UI-0 |
| UI-2 | `…-pha2-design-system.md` | ⏳ | UI-3 |
| UI-1 | `…-pha1-automation-studio.md` | ⏳ | **Q1** |
| UI-4 | `…-pha4-node-ux.md` | ⏳ | UI-3 |
| UI-5 | `…-pha5-inspector-connections.md` | ⏳ | **Q4** |
| UI-7 | `…-pha7-execution-runs.md` | ⏳ | UI-3 |
| UI-8a | `…-pha8a-human-approval.md` ⭐ | ⏳ | UI-7 |
| UI-6 | `…-pha6-data-picker.md` | ⏳ | UI-5 |
| UI-8b | `…-pha8b-agent-designer-diff.md` | ⏳ | UI-3 |
| UI-9 | `…-pha9-templates.md` | ⏳ | UI-1 |
| UI-10 | `…-pha10-i18n-tro-nang-mobile.md` | ⏳ | tất cả |
| UI-11 | `…-pha11-nghiem-thu.md` | ⏳ | tất cả |

⚠️ **Cố ý chỉ viết chi tiết UI-0 lúc này.** Viết task-level cho 12 pha bây giờ là
viết ra thứ sẽ sai: UI-1 phụ thuộc **Q1**, UI-5 phụ thuộc **Q4**, và UI-3 sẽ đổi
hình dạng tệp mà UI-2/4/7 phải trỏ vào. Mỗi plan con viết **ngay trước khi mở pha**,
khi đã biết hình dạng thật.

## 5.1 Ba câu chặn, cần chủ dự án

| # | Câu | Chặn pha | Không có thì |
|---|-----|---------|--------------|
| **Q1** | Canvas-centric hay Automation Studio? (khuyến nghị **B**, độ tin CAO) | UI-1, UI-9 | vẫn chạy được UI-0/2/3/4/7/8a |
| **Q4** | Tầng OAuth: LTT quản lý / khách tự mang / cả hai? (khuyến nghị **C**, độ tin **THẤP**) | UI-5 → UI-6 | 33 node vẫn chết |
| **Q11** | Mở `publish_duoc` cho `trigger.manual`? schedule/webhook khi nào? | UX-1, UX-2, UX-4 | không tự động hoá được |

⭐ **UI-0 không chặn bởi câu nào — mở được ngay.**
