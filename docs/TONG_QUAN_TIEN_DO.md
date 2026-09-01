# Dự án đang đứng ở đâu, và đi tiếp thế nào

**2026-08-24.** Đọc cùng `docs/KE_HOACH_TRIEN_KHAI.md` (ý định) và
`docs/NHAT_KY.md` (sự thật đã xảy ra).

---

## 0. Một câu về con số phần trăm

Không có **một** con số trung thực cho "bao nhiêu % dự án", vì **mẫu số đang di
chuyển**: H37 (ảnh nhà), H38 (LLM nhà) và H39 (bán VPS) đều **chưa tồn tại ba
ngày trước**. Báo "82 %" hôm nay rồi "74 %" tuần sau không phải là lùi tiến độ —
đó là mẫu số vừa to ra.

Nên dưới đây chia theo **ba lớp**, mỗi lớp có mẫu số đứng yên và đếm được.

---

## 1. Ba lớp, ba bức tranh rất khác nhau

### Lớp 1 — Hạ tầng nền tảng: **xong**

21/25 hạng mục trong bảng của `CLAUDE.md` ở trạng thái ✅. Cụ thể là **toàn bộ**
phần hạ tầng: người dùng · hàng đợi job · sổ credit · admin · Cloudflare Tunnel ·
catalog + SSO · APIKEYS hai pha · thanh toán PayOS · R2 · Public API · hồ sơ tự
sinh · củng cố MVP · rà soát bố cục mã nguồn.

⇒ **Không còn hạng mục hạ tầng nào đang mở.** Mọi việc còn lại là **sản phẩm**
xây *trên* nó, hoặc là việc **bán** nó.

### Lớp 2 — Đường từ khách tới tiền: **vừa thông tuyến hôm nay, lần đầu**

Trước hôm nay: Public API đã deploy từ 17/08 nhưng `LTT_PUBLIC_API_TOOLS` **rỗng**
— cửa hàng có nhà, không có hàng. Hôm nay đã đi hết một vòng thật:

```
khoa khach ltt_sk_...  ->  https://app.lttstudios.com/api/v1
  -> giu credit -> may B sinh chu -> quyet toan theo token DA DO -> tru dung tien
```

| Đã chứng minh | Bằng gì |
|---|---|
| Ba cửa cùng chạy | `/jobs` (bất đồng bộ) · `/chat/completions` (đồng bộ) · `/messages` + `/responses` (streaming) |
| Luồng dài không bị Cloudflare cắt | **119,4 giây**, 15.932 sự kiện, không 524 |
| Tiền đúng | số dư 3.042 → 3.037, đối chiếu tay khớp từng credit |
| Một client thật | **Codex CLI** qua địa chỉ công khai, 31 giây |

⚠️ **Nhưng chưa có khách ngoài nào.** Mọi thứ ở trên là ta tự gọi ta. Đó là
khoảng cách lớn nhất còn lại của cả dự án, và nó **không phải khoảng cách kỹ
thuật**.

### Lớp 3 — Danh mục sản phẩm: **đây là chỗ còn việc**

| Sản phẩm | Tiến độ | Trạng thái thật |
|---|---|---|
| Tool ảnh/video di trú từ BOT GEMINI | ✅ | đang chạy, có khách nội bộ |
| **H38 — LLM nhà** | **5/6 đợt** | ✅ **bán được ngay hôm nay** |
| **H39 — bán VPS** | **4/12 phase** (P0a,b,c + P1) | app còn TẮT; còn P2–P9 |
| **H37 — ảnh nhà** | ~6/13 phase | 🔴 so mù **thua Gemini 24–4**; cần quyết định trước khi xây tiếp |
| **Nexus** | LIVE, thu tiền thật | còn hạ tầng C1–C4, macOS, iOS |

---

## 2. Nếu phải chọn một con số

| Lớp | Xong | Ghi chú |
|---|---:|---|
| Hạ tầng nền tảng | **~100 %** | mẫu số đứng yên, và đã cạn |
| Đường khách → tiền | **~85 %** | còn tài liệu bán hàng + **khách thật đầu tiên** |
| Danh mục sản phẩm | **~40 %** | mẫu số còn to ra |

**Nếu buộc phải nói một số cho cả dự án: khoảng 70 %** — và phần 30 % còn lại
**không nằm ở hạ tầng**, nó nằm ở sản phẩm chưa xong và ở việc chưa bán được cho
ai.

---

## 3. Điều đáng lo nhất, nói thẳng

**Đã xây gần hai tháng, chưa có một khách bên ngoài nào trả tiền.**

Mọi hạng mục ✅ ở trên đều đúng, đều có test, đều đo được. Nhưng chúng chứng minh
**hệ thống chạy**, không chứng minh **có người muốn mua**. Và đó là hai câu hỏi
khác nhau — câu thứ hai chưa được đặt ra lần nào.

⇒ Kế hoạch dưới đây xếp **việc bán** lên trước việc xây thêm, cho tới khi có ít
nhất một khách thật. Không phải vì việc xây kém quan trọng, mà vì mỗi sản phẩm
xây thêm mà chưa ai mua là **thêm một canh bạc trên cùng một giả định chưa kiểm**.

---

## 4. Kế hoạch — năm giai đoạn

### Giai đoạn 1 — Đóng nốt H38 (1,5 ngày) 🔜 **ngay**

Đây là sản phẩm **duy nhất** có toàn tuyến trả tiền đã chứng minh. Đóng nó lại
thành thứ bán được.

| # | Việc | Đạt khi |
|---|---|---|
| 1.1 | Claude Code CLI + Claude Desktop, phiên thật có gọi tool | cần chủ sản phẩm — máy này không có hai công cụ đó |
| 1.2 | **C13** xoay bearer token cổng VLM | token cũ hết hiệu lực |
| 1.3 | **C15** công cụ tự ghi cấu hình cho ba client | copy–dán không còn cần thiết |
| 1.4 | **C16** thu tường lửa máy B về một IP | `Set-NetFirewallRule ... -RemoteAddress 192.168.2.17` |
| 1.5 | Chạy `gate.py` **đầy đủ** một lần trọn vẹn | chưa lần nào xong — hai lần bị deploy giết |

### Giai đoạn 2 — Bán thật (2 ngày) 🔴 **việc chưa từng làm**

| # | Việc | Vì sao |
|---|---|---|
| 2.1 | Trang giá công khai cho API + ví dụ chi phí thật | khách phải biết giá **trước** khi đăng ký |
| 2.2 | Điều khoản sử dụng + giới hạn trách nhiệm cho API | bán dịch vụ tính tiền mà không có điều khoản là rủi ro pháp lý |
| 2.3 | Đường đăng ký → nhận khoá → gọi lần đầu, **đi thử bằng một tài khoản mới toanh** | ta chưa bao giờ đi con đường đó bằng mắt người lạ |
| 2.4 | **Một khách thật** (dù là người quen) gọi API và trả tiền | 🔴 mốc quan trọng nhất của cả dự án |
| 2.5 | Giám sát lưu lượng thật: cảnh báo hết credit, lỗi 5xx, tồn đọng hàng đợi | hôm nay ta chỉ giám sát máy, chưa giám sát **khách** |

### Giai đoạn 3 — H39 bán VPS (P2–P9, ~8 phase) 

Khối xây lớn nhất còn lại, và là dòng doanh thu **định kỳ** duy nhất (thuê tháng)
— khác hẳn API bán theo lượt.

| Phase | Nội dung |
|---|---|
| P2 | vòng đời bật/tắt/rebuild/xoá + console noVNC |
| P3 | tiền: 3 gói, trừ credit 30 ngày, treo → xoá +7 ngày |
| P4 | chống lạm dụng: cpulimit, giới hạn băng thông, chặn cổng 25/587 |
| P5–P6 | template Windows Server 2022 · Windows 10/11 |
| P7 | cổng thứ hai + chọn vùng |
| P8 | backup snapshot tuần + **khôi phục thật** |
| P9 | trang bán + cảnh báo bắt buộc + điều khoản |

⚠️ P3 và P4 là chỗ mất tiền nếu làm ẩu: P3 sai thì thu nhầm hoặc quên thu; P4
thiếu thì một khách chạy 100 % CPU làm hỏng trải nghiệm của mọi khách còn lại.

### Giai đoạn 4 — H37 ảnh nhà: **cần một quyết định trước khi xây tiếp** 🔴

So mù G6b ngày 23/08: **Gemini 24 – nhà 4 – hoà 2**. Nhà **0 thắng / 16** ở
photoreal, chân dung, đông người, thumbnail và chữ.

⇒ Xây tiếp 7 phase còn lại **chỉ hợp lý nếu** trả lời được: bán nó vì **giá vốn**
(không phụ thuộc hạn mức Gemini, không lộ dữ liệu ra ngoài) hay vì **chất lượng**?
Nếu là giá vốn thì phần lớn G7–G11 vẫn cần; nếu định vị là "đẹp hơn" thì **dừng
lại**, vì số đo đã bác bỏ.

**Đây là câu hỏi kinh doanh, không phải kỹ thuật, và tôi không tự trả lời.**

### Giai đoạn 5 — Nexus C1–C4 + macOS + iOS

Đang LIVE và thu tiền thật, nên đây là **mở rộng**, không phải hoàn thiện. Xếp
sau vì nó đã có doanh thu còn ba việc trên thì chưa.

---

## 5. Nợ kỹ thuật xuyên suốt — không thuộc giai đoạn nào

| # | Nợ | Mức |
|---|---|---|
| N1 | `test_221` trên một bucket R2 vứt đi (H36) | chặn bởi quyết định hạ tầng, không phải mã |
| ~~N2~~ | ~~`gate.py` đầy đủ chưa chạy trọn lần nào~~ | ✅ **ĐÓNG 01/09** — `RESULT: PASS`, 5,3 phút, cây đứng yên. Cần một **cửa sổ yên** thoả thuận với phiên kia; ba lượt trước đó bị vô hiệu vì cây đổi giữa chừng |
| N3 | Cảnh báo mới `ltt_llm:tren_cpu` chưa được thử bằng một sự cố thật | chỉ mới thử trên sự cố tình cờ hôm 23/08 |
| ~~N4~~ | ~~`AUOptions` máy B ⇒ mốc 01:00~~ | 🗑️ **KHÔNG CÒN LÀ VIỆC** — `CLAUDE.md:420` chốt **không cần** đổi `AUOptions` (nó là thiết lập bảo mật, cái giá lớn hơn thứ nó cứu), và lô đo nay ghi kết quả sau mỗi ảnh nên một lần khởi động lại chỉ mất **đúng một ảnh**. Dòng này mâu thuẫn với quyết định hiện hành |
| **N7** | **Diễn tập reboot máy A** — F05 mới suy từ cấu hình, chưa quan sát một lần reboot thật | máy A vừa là production vừa chạy phiên làm việc; cần một cửa sổ chủ dự án chọn |
| **N9** | **Đọc nhật ký khởi động Windows sau khi reboot máy A** — đối chiếu thứ tự dịch vụ lên, thời gian tới lúc `/health/ready` xanh, và có dịch vụ nào phải nhờ `FAILURE_ACTIONS` mới lên không | làm **cùng lượt** với N7; một mình nó không đáng một lần reboot |
| **N8** | `setup/bat_tu_dung_day.ps1` **chưa chạy** — 5 dịch vụ máy A vẫn không có `FAILURE_ACTIONS` | một lệnh, **cần Administrator**. Chỉ đặt chính sách cho lần hỏng sau, không khởi động lại gì |
| N5 | Codex báo *"Model metadata for `ltt_llm` not found"* | không chặn, nhưng làm ước chi phí của nó sai |
| N6 | Số test trùng giữa hai phiên — nay **ba lần** (371, 01/09) | ⚠️ Mốc "≥ 274" đã **lỗi thời**: cao nhất hiện là **377**. Và bài học không phải một con số — `ls tests/` là **ảnh chụp** của một cây có hai người ghi. Chạy `tools/check_so_test.py` **ngay trước** khi đặt tên |

---

## 6. Thứ tự tôi đề xuất, và vì sao

1. **Giai đoạn 1** — vì H38 đang ở mức "gần xong", và một sản phẩm gần xong để
   đấy sẽ phải học lại từ đầu ở phiên sau.
2. **Giai đoạn 2** — vì nó trả lời câu hỏi mà **mọi** việc còn lại đang giả định
   là đã có câu trả lời.
3. **Giai đoạn 4 (quyết định H37)** — trước giai đoạn 3, vì nó **rẻ**: một cuộc
   trò chuyện, không phải một tuần code. Trả lời xong có thể xoá luôn 7 phase.
4. **Giai đoạn 3** — khối lớn nhất, làm khi đã biết chắc mô hình bán được.
5. **Giai đoạn 5** — mở rộng thứ đã có doanh thu.

⚠️ Nếu chỉ làm được **một** việc trong tuần này, làm **2.4**: một khách thật gọi
API và trả tiền. Nó rẻ hơn mọi thứ khác trong danh sách và nó là thứ duy nhất
kiểm chứng được giả định mà cả dự án đang đứng lên.
