# H43 tiếp — Trạng thái ngữ cảnh + kế hoạch kiểm sâu ChatLTT

*Lập 2026-09-03, sau khi ChatLTT lên production và đạt 18/18 hạng mục GUI.*

Tài liệu này trả lời hai câu hỏi của chủ dự án:

1. **Hộp thoại nhấp nháy** — cộng đồng giải bài này thế nào, và ta làm gì.
2. **Kiểm sâu hơn** — danh sách tình huống nguy cơ rút từ dữ liệu thật, và
   lộ trình triển khai.

---

## PHẦN A — Trạng thái ngữ cảnh khi model đang làm việc

### A1. Vấn đề, đo được chứ không phải cảm giác

Đo trên production `app.lttstudios.com`, một lượt hỏi bình thường:

| Mốc | Người dùng thấy gì |
|---|---|
| t+0,5s | một chấm nhịp nhỏ, không chữ |
| **t+3,7s** | khối "Suy luận" **đột ngột hiện ra**, đẩy mọi thứ xuống |
| t+6,0s | chấm nhịp biến mất, chữ trả lời bắt đầu |

```
CLS (dịch chuyển bố cục tích luỹ) = 0,0791
trong đó MỘT cú nhảy đơn lẻ       = 0,0749
```

Chuẩn Core Web Vitals coi **> 0,1 là kém**. Ta ở 0,079 — chưa "kém", nhưng gần
như toàn bộ nằm ở **một** cú nhảy, và cú nhảy đó rơi đúng vào lúc người dùng
đang nhìn chằm chằm vào hộp trống. Đó là thứ mắt đọc thành "nhấp nháy".

🔴 **Và ba giây rưỡi im lặng mới là vấn đề lớn hơn cú nhảy.** Người dùng không
biết hệ thống đang xếp hàng, đang nạp model, hay đã treo. Một chấm nhịp trả lời
được câu "còn sống không", nhưng không trả lời được câu "đang làm gì".

### A2. Cộng đồng giải thế nào — LibreChat @ `9e74cc0`

Họ có hẳn một họ thành phần cho đúng khoảng thời gian này:
`ProgressText.tsx`, `PendingSkillCall.tsx`, `Summary.tsx`, `Thinking.tsx`.

Chú thích đầu `PendingSkillCall.tsx` nói thẳng ý đồ:

> *Minimal variant of `SkillCall` used for the **interim window between submit
> and the backend's real content part landing** on the message.*
>
> *Strips the expand/collapse affordance… there's nothing to expand during
> priming, and leaving the chevron + cursor-pointer on a non-functional button
> is misleading.*
>
> *Same icon, same shimmer, same localized label strings **so the visual
> language matches the real card it'll be replaced by**.*
>
> *`loaded=false` → "Running X"… `loaded=true` → "Ran X"; driven by
> `ContentParts.hasRealContent`, which flips true **as soon as any streamed
> content part arrives**.*

Rút ra **năm nguyên tắc**, và chúng độc lập với React:

| # | Nguyên tắc | Vì sao |
|---|---|---|
| 1 | **Khoảng chờ luôn có người ở** — không bao giờ để hộp trống | trống = người dùng không phân biệt được "đang chạy" với "đã treo" |
| 2 | **Chỗ giữ chỗ trông GIỐNG thứ sẽ thay nó** | thay một thứ bằng một thứ cùng kích cỡ thì không có gì bị đẩy |
| 3 | **Chiều cao CỐ ĐỊNH, nội dung `absolute`** | `progress-text-wrapper { h-5 }` + `progress-text-content { absolute }` — đổi nhãn bao nhiêu lần cũng CLS = 0 |
| 4 | **Đổi trạng thái theo SỰ KIỆN THẬT**, không theo hẹn giờ | `hasRealContent` lật khi content part đầu tiên tới, không phải sau N giây |
| 5 | **Không bày nút bấm chưa dùng được** | một chevron mở ra chỗ rỗng là một lời nói dối nhỏ |

⭐ Nguyên tắc 3 là thứ thực sự giết cú nhảy 0,0749. Bốn nguyên tắc kia là về
*thông tin*; nguyên tắc 3 là về *hình học*.

### A3. Thiết kế cho ChatLTT

Ta **đã có sẵn** dòng sự kiện cần thiết từ `platform_core/runtime_noi_bo/luong.py`
— không phải thêm hạ tầng, chỉ phải hiển thị thứ đang bị bỏ đi:

| Sự kiện đã có | Nhãn hiển thị | Ghi chú |
|---|---|---|
| *(vừa bấm Gửi)* | **Đang xếp hàng…** | trước `response.started`; đúng lúc đang chờ suất `admission` |
| `response.started` | **Đang chuẩn bị…** | đã có suất, đang mở luồng tới model |
| `reasoning.delta` | **Đang suy nghĩ… (N giây)** | đồng hồ chạy, cập nhật mỗi giây |
| `tool_call.delta` | **Đang gọi công cụ X…** | dành sẵn; hiện chưa app nào dùng |
| `response.delta` đầu tiên | *(trạng thái thu lại)* → **Đã suy nghĩ N giây** | thành nút mở khối suy luận |
| `DangBan` từ máy chủ | **Model đang bận — thử lại sau N giây** | ta ĐÃ biết `thu_lai_sau_s`, đang không nói ra |

⛔ **Không thêm nhãn nào ta không có sự kiện cho nó.** "Đang tìm tài liệu" nghe
hay nhưng ChatLTT không có bước tìm tài liệu; hiển thị nó là bịa một tiến trình
không tồn tại — và ngày nào ta thêm RAG thật, không ai còn tin dòng trạng thái đó
nữa.

**Khuôn hình học** (nguyên tắc 3):

```css
.ltc-trangthai        { height: 1.5rem; position: relative; }  /* chiều cao CỐ ĐỊNH */
.ltc-trangthai__chu   { position: absolute; inset: 0 auto auto 0; white-space: nowrap; }
```

Khối "Suy luận" phải **luôn chiếm chỗ** từ lúc `response.started`, ở trạng thái
thu gọn, thay vì mọc ra ở giây 3,7.

### A4. Các bước làm

| # | Việc | Tệp |
|---|---|---|
| A4.1 | `services/su_kien.py`: ghi `pha` (`xep_hang`/`chuan_bi`/`suy_nghi`/`cong_cu`/`tra_loi`) vào `ChatlttExecution` | `apps/chatltt/services/su_kien.py` |
| A4.2 | Phát `pha` ra SSE để giao diện không phải suy từ thứ khác | `apps/chatltt/routes/_p_luot.py` |
| A4.3 | `<TrangThaiLuot>` — một phần tử, chiều cao cố định, nhãn đổi tại chỗ | `frontend/chatltt/src/TrangThaiLuot.tsx` (mới) |
| A4.4 | Khối Suy luận chiếm chỗ từ `response.started`, không mọc ở giữa chừng | `ThongDiepView.tsx` |
| A4.5 | Nói ra `thu_lai_sau_s` khi model bận | `App.tsx` + `MA_LOI` |
| A4.6 | Phép kiểm: **CLS của một lượt stream < 0,02** | `tools/kiem_chatltt_gui.mjs` |
| A4.7 | Phép kiểm: không bao giờ có khoảng > 1,5s mà trạng thái rỗng | như trên |

⭐ A4.6 là hạng mục quan trọng nhất trong bảng. Nó biến "trông đỡ giật" thành
**một con số có thể đỏ**.

---

## PHẦN B — Kế hoạch kiểm sâu

### B1. Nguồn: 150+ issue `🐛 bug` thật của LibreChat

Không suy đoán. Lọc những loại **áp dụng được cho ChatLTT** (bỏ phần Azure,
Bedrock, MCP, Meilisearch, OAuth doanh nghiệp — ta không có):

| Loại | Ví dụ thật từ kho họ | ChatLTT có phơi ra không |
|---|---|---|
| **Toàn vẹn luồng SSE** | *Garbled Characters in Chinese Outputs* · *Failed to parse stream* · *JSON.parse: unexpected end of data* · *response flashes blank* | **CÓ** — tiếng Việt nhiều byte, chunk cắt giữa ký tự |
| **Suy luận lẫn vào trả lời** | *o4-mini thinking output mixed with response* · *Think tags still displayed* | **CÓ** — ta có khối suy luận riêng |
| **Trạng thái hội thoại** | *Switching to another conversation and back causes confusion* · *Saved conversation structure collapse* · *New chat has no label until refresh, improper back button* | **CÓ** — ta vừa thêm URL hash, chưa kiểm nút Back |
| **Ngữ cảnh tích luỹ** | *Length exceeded error after repeated use in one conversation* | **CÓ** — trần 88.555 token |
| **Kết xuất Markdown** | *Numbered Lists are cut off (iPad/mobile)* · *Numbers Displayed as "a"* · *Copying in dark mode copies the dark style* | **CÓ** |
| **Đính kèm / vision** | *Images attached don't send* · *inaccessible URL for vision requests* · *multiple upload fails entirely if one exceeds limit* | **CÓ** — vừa xây tuần này |
| **Di động** | *input hidden on firefox mobile* · *virtual keyboard closes then reopens* | **CÓ** |
| **Đổi model** | *Unable to switch endpoints/models* · *chatGptLabel and modelLabel conflict* | **CÓ** |
| **Bản cũ trong cache** | *Users always get the old version of the webpage* | Đã chặn (hash nội dung), **cần một phép kiểm canh** |
| **a11y** | nhãn `♿ a11y` là một loại riêng trong kho họ | **CÓ** — mới kiểm ở mức nhãn |

### B2. Nói thẳng về "triệt tiêu 100% bug"

⛔ **Không đạt được, và một kế hoạch hứa điều đó là một kế hoạch nói dối.**
Không gian đầu vào của một sản phẩm chat là vô hạn: mọi chuỗi ký tự × mọi trạng
thái hội thoại × mọi thời điểm ngắt kết nối.

⭐ Thứ **đạt được** là: triệt tiêu từng **LOẠI** ở trên, mỗi loại bằng một phép
kiểm chạy lại được. Một loại đã có chốt thì nó không quay lại **im lặng** — và
"không quay lại im lặng" mới là thứ giữ được chất lượng qua thời gian, chứ không
phải một lần quét sạch.

⇒ Chỉ tiêu của kế hoạch này: **mỗi dòng trong bảng B1 có ít nhất một hạng mục
chạy trên trình duyệt thật.** Từ 18 hạng mục hiện tại lên khoảng 60.

### B3. Bảy đợt

Xếp theo **rủi ro × khả năng lọt**, không theo độ dễ.

#### Đợt 1 — Toàn vẹn luồng (rủi ro cao nhất)

| # | Hạng mục | Đạt khi |
|---|---|---|
| 1.1 | Tiếng Việt có dấu qua 200 chunk liên tiếp | không một `U+FFFD` nào |
| 1.2 | Emoji + chữ Hán + toán học trong một câu trả lời | hiện đúng, không vỡ |
| 1.3 | Ngắt mạng giữa luồng rồi nối lại | nối lại đúng chỗ, không mất chữ, không nhân đôi |
| 1.4 | Đóng tab giữa luồng, mở lại | lượt vẫn quyết toán đúng, partial được lưu |
| 1.5 | Suy luận **không** lẫn vào trả lời | khối suy luận và khối trả lời tách hẳn |
| 1.6 | Khối mã 5.000 dòng | không treo trình duyệt, cuộn được |
| 1.7 | Model trả về `finish_reason: length` | nói rõ bị cắt, không im lặng |

#### Đợt 2 — Trạng thái hội thoại và cây nhánh

| # | Hạng mục | Đạt khi |
|---|---|---|
| 2.1 | Nút **Back** của trình duyệt giữa các hội thoại | về đúng hội thoại trước |
| 2.2 | Chuyển hội thoại A→B→A giữa lúc A đang stream | A không mất chữ, B không nhận nhầm |
| 2.3 | Sửa-gửi-lại ở **lượt đầu tiên** (`parent_id = null`) | tạo anh em ở gốc, không tạo hội thoại mới |
| 2.4 | 50 nhánh trên cùng một nút | điều hướng `‹ n/50 ›` đúng, không chậm |
| 2.5 | Xoá hội thoại đang stream | lượt bị huỷ, tiền quyết toán, không hàng mồ côi |
| 2.6 | Tiêu đề hội thoại sinh ra sau lượt đầu | có tiêu đề mà **không** cần F5 |
| 2.7 | Hash trỏ tới hội thoại của người khác | 404 + thoát ra được (đã có, cần canh) |

#### Đợt 3 — Kết xuất Markdown

| # | Hạng mục | Đạt khi |
|---|---|---|
| 3.1 | Xuống dòng đơn | ✅ đã sửa (`remark-breaks`) — giữ chốt |
| 3.2 | Danh sách đánh số lồng nhau, ở 390 px | không bị cắt |
| 3.3 | Bảng rộng hơn màn hình | cuộn ngang **trong bảng**, không cuộn cả trang |
| 3.4 | Sao chép khối mã ở chế độ tối | dán ra chỉ có chữ, không kèm kiểu |
| 3.5 | Markdown chưa đóng thẻ giữa luồng (` ``` ` chưa đóng) | không vỡ bố cục trong lúc đang stream |
| 3.6 | HTML thô | vẫn escape thành chữ (đã chốt, giữ) |

#### Đợt 4 — Đính kèm và vision

| # | Hạng mục | Đạt khi |
|---|---|---|
| 4.1 | Ảnh 8 MB (sát trần) | lên được hoặc từ chối **có nói lý do** |
| 4.2 | Chọn 4 tệp trong đó 1 tệp quá cỡ | 3 tệp kia **vẫn lên** (lỗi LibreChat từng dính: hỏng cả lô) |
| 4.3 | Tệp không phải ảnh đổi đuôi thành `.png` | từ chối theo **byte**, không theo tên |
| 4.4 | Ảnh trong hội thoại sau khi F5 | vẫn hiện, vẫn đúng chủ |
| 4.5 | Gửi ảnh rồi đổi sang model không đọc ảnh | nói rõ, không gửi lặng lẽ |
| 4.6 | 4 ảnh trong một lượt + hội thoại dài | không vượt trần ngữ cảnh bất ngờ |

#### Đợt 5 — Di động và bàn phím ảo

| # | Hạng mục | Đạt khi |
|---|---|---|
| 5.1 | 390 px: ô soạn khi bàn phím ảo mở | không bị che |
| 5.2 | Gõ tiếng Việt Telex trên di động | không cắt từ (IME đã chốt ở vitest, cần kiểm thật) |
| 5.3 | Xoay ngang giữa lúc stream | không mất chỗ đang đọc |
| 5.4 | Cuộn khi model đang viết | **không** kéo người dùng xuống nếu họ đang đọc lên trên |

#### Đợt 6 — Đổi model và ngữ cảnh tích luỹ

| # | Hạng mục | Đạt khi |
|---|---|---|
| 6.1 | Đổi model giữa hội thoại | lượt sau dùng model mới, lượt cũ giữ nhãn cũ |
| 6.2 | Hội thoại chạm trần 88.555 token | báo `qua_dai` rõ ràng, gợi ý mở hội thoại mới |
| 6.3 | Đổi sang vision rồi quay lại | ô đính ảnh hiện/ẩn đúng, ảnh cũ không mất |

#### Đợt 7 — Tiền và đồng thời, nhìn từ GUI

| # | Hạng mục | Đạt khi |
|---|---|---|
| 7.1 | Bấm Gửi hai lần thật nhanh | **một** lượt, giữ tiền **một** lần |
| 7.2 | Hai tab cùng gửi trong một hội thoại | hai lượt tách bạch, sổ tiền đúng |
| 7.3 | Hết credit giữa chừng | dừng sạch, hoàn phần chưa dùng, nói rõ |
| 7.4 | Số dư trên thanh app cập nhật ngay | không cần F5 (nợ đã ghi) |

### B4. Thứ tự và chi phí

| Đợt | Cỡ | Vì sao ở vị trí này |
|---|---|---|
| **A** (trạng thái) | M | chủ dự án nhìn thấy mỗi ngày; và A4.6 cho một con số canh gác |
| **1** Luồng | **L** | rủi ro cao nhất, và tiếng Việt làm ta phơi ra nhiều hơn LibreChat |
| **2** Hội thoại | **L** | URL hash vừa thêm tuần này, chưa ai kiểm nút Back |
| **4** Vision | M | vừa xây, mã mới nhất = mã ít mắt nhìn nhất |
| **3** Markdown | M | vừa tìm ra một lỗi thật ở đây, khả năng còn nữa |
| **5** Tạo ảnh | M | đường tiêu tiền theo job, trước đó không hạng mục nào chạm |
| **6** Tạo giọng | M | như trên, cộng dữ liệu sinh trắc |
| **7** Tiền/đồng thời | M | đã có `test_627` ở tầng dịch vụ; đây là tầng GUI |
| **8** Di động | M | cần thiết bị/emulator, chậm hơn |
| **9** Model | S | |

⚠️ **Số hiệu đợt trong bảng này đã đổi ngày 04/09.** Bản đầu đặt 5 = Di động,
6 = Model. Khi chủ dự án yêu cầu kiểm tạo ảnh và tạo giọng, hai đợt đó chiếm
số 5 và 6 **trong mã** (`tools/kiem_chatltt/dot5_*.mjs`, `dot6_*.mjs`), còn tài
liệu vẫn giữ nghĩa cũ trong một thời gian.

⛔ Đó đúng là cơ chế đã làm bảng "app nào đang bật" trong `CLAUDE.md` nói sai
**năm lần**: một con số chép ở hai nơi, rồi một nơi đổi. Ở đây nguồn chân lý là
**tên tệp trong `tools/kiem_chatltt/`**, không phải bảng này.

### B5. Hai luật cho mọi hạng mục mới

Rút từ **ba lần bộ kiểm vu khống sản phẩm** trong ngày 03/09:

**① Đọc dấu hiệu của sản phẩm, đừng đoán bằng độ dài chuỗi.**
`xong()` từng đợi "không còn nút Dừng" — nhưng `dangChay` có một khoảng `false`
ngay sau khi bấm Gửi. Và điều kiện phụ "chữ dài hơn 15 ký tự" được thoả bởi
chính nhãn vai (`ChatLTT` + `▸ Đang suy nghĩ…` = 24 ký tự, không một chữ trả lời
nào). Hệ quả: hạng mục hỏi "thủ đô Pháp" đọc phải câu trả lời của **lượt trước**
rồi báo "model trả lời sai". Chạy tay: **"Paris"**.

**② "Không quan sát được" ≠ "hỏng".**
Lượt kết thúc trước khi kịp bấm Dừng thì mệnh đề **chưa được kiểm**, không phải
bị vi phạm. Báo `BO QUA` kèm lý do. Báo `HONG` là vu khống; báo `DAT` là nói dối.

---

## Phụ lục — quyết định sản phẩm đã chốt

**Model tự xưng là Qwen là hành vi MONG MUỐN** (chủ dự án chốt 03/09). Khi được
chào, nó trả lời "tôi không phải ChatLTT, tôi là Qwen". Giấu điều đó cần một
system prompt dạy model nói sai về chính nó — đổi một sự thật lấy một câu quảng
cáo.

⛔ Thứ **vẫn cấm** lộ: `qwen38` (id nội bộ, khác tên thường gọi), cổng LAN của
máy B (`8299`/`8199`/`8120`), tiền tố khoá API `ltt_sk_`, dải IP `192.168.`.
Đó là những thứ cho ai đó **đi tiếp một bước**; một cái tên model thì không.
Chốt ở `tools/kiem_chatltt_gui.mjs::khong-lo-id-noi-bo`.

## Đợt 5–6 (media) — bốn phép kiểm sai, không phải bốn lỗi sản phẩm

Đo 04/09 trên production. Lượt chạy đầu báo **4 HỎNG**; điều tra xong thì **cả
bốn đều là phép kiểm sai**, và mỗi cái sai một kiểu khác nhau — đáng ghi lại vì
chúng là bốn cách khác nhau để một bộ kiểm nói dối.

| Báo | Sự thật | Loại sai |
|---|---|---|
| 6.1/6.2 "nút media không sẵn sàng" | model chưa nạp trên máy B | **suy từ giao diện** thay vì hỏi máy chủ |
| 6.3 "máy chủ nhận `voice_id` của người khác" | đúng thiết kế; job `failed`, hoàn đủ | đo **chi tiết cài đặt** thay vì bất biến |
| 6.4 "bấm Đọc to không gửi gì" | đúng thiết kế: phải qua ô xác nhận giá | đòi sản phẩm **bỏ một chốt an toàn** |
| 6.4 lần hai, `manh_doi_chieu:""` | mảnh đối chiếu rỗng ⇒ nửa mệnh đề tự tắt | **xanh mà không chứng minh gì** |

🔴 **Cái nguy nhất trong bảng này là dòng cuối, không phải dòng nào đỏ.** Ba
dòng trên đều đỏ, nên chúng được điều tra. Dòng cuối **xanh** — nó đóng hồ sơ
lại. Nếu không đọc kỹ `manh_doi_chieu:""` thì hạng mục đó vĩnh viễn là một dòng
`DAT` không kiểm gì cả.

⛔ Và 6.3 suýt gây thiệt hại thật. Nếu "sửa" sản phẩm cho khớp phép kiểm, ta
thêm một chỗ kiểm sở hữu **thứ hai** ở route — đúng thứ `tim_profile` cảnh báo,
và chỗ kiểm ở route sẽ **không thấy kho giọng chung** nên chặn nhầm giọng hợp
lệ. Một phép kiểm sai kéo theo một lỗ hổng thật.

⭐ Ba luật rút ra, đã cưỡng chế bằng mã trong `tools/kiem_chatltt/`:

1. **Trạng thái năng lực hỏi máy chủ**, không suy từ nút — `nangLuc(p, ten)`,
   và mọi lần `bo_qua` phải kèm con số máy chủ trả về.
2. **Đo bất biến, đừng đo cách cài đặt.** 6.3 giờ chấp nhận cả hai đường (chặn
   lúc nộp *hoặc* nhận rồi hỏng + hoàn đủ) và chỉ đỏ khi **ra tiếng** hoặc
   **mất tiền**.
3. **Nguồn đối chiếu phải độc lập với thứ đang đo.** 6.4 đặt sẵn dấu hiệu
   `CANHCUT DOCTO 4471` thay vì bốc chữ từ màn hình; bốc từ màn hình đã lấy
   nhầm khối *Suy luận*.

### Bộ kiểm tự tạo ra điều kiện làm chính nó đỏ

⛔ Đợt 1–4 gửi hàng chục lượt chữ, giữ LLM trên GPU (TTL 1800s), nên `image.ltt`
và `speech.ltt` **không còn chỗ nạp**. Rồi đợt 5–6 báo "model chưa sẵn sàng".

⭐ Nên chạy media **trước** hoặc **riêng**: `--dot 5,6` trên một GPU rảnh. Và
"máy bận" phải là `BOQUA` kèm bằng chứng (`job` vẫn `queued`, `thu=0`), không
bao giờ là `HONG` — một hàng đợi dài không phải một bất biến bị vi phạm.
