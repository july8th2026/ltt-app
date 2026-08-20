# LTT NEXUS — Kiểm kê OSS và ranh giới giấy phép

> Prompt 03 của `LTT_NEXUS_CLAUDE_BUILD_PACK_V2_ADAPTIVE`, theo
> `references/OSS_BOUNDARY_RULES.md`. Lập 2026-08-17.
>
> **Đây không phải tư vấn pháp lý.** Nó là bản kiểm kê sự thật kỹ thuật và một
> danh sách câu hỏi đủ cụ thể để luật sư trả lời được. Invariant #6 của pack yêu
> cầu legal review bắt buộc trước phát hành thương mại; file này chuẩn bị cho
> buổi đó, không thay thế nó.

---

## 1. Quyết định đang hiệu lực

**D1 (chốt 2026-08-17):** dùng RustDesk AGPL-3.0, giữ **ranh giới tiến trình**.

File này không phản đối quyết định đó. Nó làm rõ **ranh giới ấy phải như thế nào
mới là ranh giới thật**, vì đọc kỹ giấy phép cho thấy một điểm mà bản audit
trước chưa nêu — mục 4.

---

## 2. Kiểm kê — kiểm chứng lại ngày 2026-08-17

Pack yêu cầu ghi **đúng phiên bản/commit**, không dùng ghi chú cũ
(`OSS_BOUNDARY_RULES` rule 2). Số dưới đây lấy trực tiếp từ GitHub API hôm nay.

| Thành phần | Vai trò dự kiến | Giấy phép | Phiên bản | Commit |
|---|---|---|---|---|
| `rustdesk/rustdesk` | engine điều khiển ở hai đầu | **AGPL-3.0** | `1.4.9` (2026-07-06) | `6c578292e8ebbbec708b76986ba8c4bc7c509747` |
| `rustdesk/rustdesk-server` (hbbs/hbbr) | rendezvous + relay tự host | **AGPL-3.0** | `1.1.16` (2026-07-20) | `73523b31cfd25d77dee862e6fc9f5e1fb5e485ef` |
| RustDesk Server Pro | bản thương mại thay thế hbbs/hbbr | độc quyền, trả phí | — | — |

Giấy phép đọc từ chính repo, không từ trí nhớ: cả hai đều khai AGPL-3.0.

**Chưa kiểm kê:** phụ thuộc bắc cầu của RustDesk (crate Rust, thư viện Flutter).
Phải làm trước khi phát hành — một trong số đó có thể mang giấy phép khác. Ghi
là *chưa làm*, không ghi là *không có vấn đề*.

---

## 3. AGPL-3.0 thực sự đòi gì — hai cò súng khác nhau

Đọc từ `LICENCE` trong chính repo RustDesk.

**Cò thứ nhất — §§4–6, khi bạn *conveying* (phân phối binary).** Giao chương
trình cho người khác thì phải kèm Corresponding Source của tác phẩm AGPL đó.
Không phụ thuộc việc có sửa hay không.

**Cò thứ hai — §13, khi bạn *sửa* và người dùng tương tác **qua mạng**.** Nguyên
văn câu đầu:

> "Notwithstanding any other provision of this License, **if you modify the
> Program**, your modified version must prominently offer all users interacting
> with it remotely through a computer network (if your version supports such
> interaction) an opportunity to receive the Corresponding Source of your version…"

Điểm cần đọc kỹ: nghĩa vụ §13 **có điều kiện là "if you modify"**. Chạy một bản
**không sửa** thì §13 không thêm nghĩa vụ nào — điều này khác với hiểu lầm phổ
biến rằng "AGPL nghĩa là cứ chạy trên server là phải mở nguồn".

---

## 4. Chỗ LTT Nexus rơi vào — và cái bẫy

Nghe qua thì có vẻ có đường thoát: chạy `rustdesk-server` **nguyên bản** thì §13
không kích, chỉ còn nghĩa vụ §§4–6 cho phần binary phân phối.

**Nhưng cách triển khai RustDesk tự host thông thường là build một client
riêng có sẵn địa chỉ server và khoá công khai của mình.** Việc đó **là sửa
chương trình**. Thêm logo hay tên sản phẩm cũng vậy.

Nói cách khác: **cái làm cho Nexus giống một sản phẩm — client mang thương hiệu
LTT, tự trỏ về hạ tầng LTT — chính là cái kích hoạt §13.** Đường "dùng nguyên
bản nên không sao" và đường "có sản phẩm của riêng mình" gần như loại trừ nhau.

Hệ quả nếu client bị sửa:

- **mã nguồn của bản RustDesk đã sửa phải được công bố** cho người dùng tương
  tác qua mạng với nó;
- câu hỏi thật không còn là "có phải mở nguồn không" mà là **"ranh giới của
  Corresponding Source nằm ở đâu"** — tức là code nào của LTT bị coi là cùng một
  tác phẩm với engine.

Đó chính là câu hỏi mà D1 gọi là "ranh giới tiến trình", và mục 5 làm nó cụ thể.

---

## 5. Ranh giới phải trông như thế nào mới là ranh giới thật

Thiết kế bắt buộc cho endpoint Windows — **hai tiến trình, không phải một**:

```
  Tiến trình A — LTT Nexus Agent            Tiến trình B — engine RustDesk
  (độc quyền, mã LTT)                       (AGPL, có thể đã sửa)
  ─────────────────────────────             ─────────────────────────────
  danh tính thiết bị, khoá riêng            bắt màn hình, nhận phím/chuột,
  enrollment, nhịp tim/presence             thương lượng NAT, truyền dữ liệu
  xin vé phiên từ control plane
  nhật ký kiểm toán, cập nhật
                    │                                     │
                    └──────── IPC cục bộ có hợp đồng ─────┘
                        (không link chung, không import,
                         không chia sẻ tiến trình/địa chỉ)
```

Ba quy tắc suy ra trực tiếp từ mục 3–4, và **phải giữ kể cả khi tiện tay**:

1. **Không copy một dòng mã AGPL nào vào tiến trình A.** Rule 3 của
   `OSS_BOUNDARY_RULES`.
2. **Không link thư viện AGPL vào tiến trình A.** Ranh giới là tiến trình + IPC,
   không phải "gọi hàm cho gọn".
3. **Mọi sửa đổi ở tiến trình B phải là patch theo dõi được** — rule 6 — vì đó
   chính là thứ phải công bố. Một fork tuỳ tiện làm nghĩa vụ công bố thành việc
   không thể thực hiện.

Ranh giới này còn phục vụ **invariant #5** của pack (luồng điều khiển không đi
qua control plane) và **#4** (không có backdoor bí mật): tiến trình A không bao
giờ chạm luồng màn hình, tiến trình B không bao giờ tự quyết uỷ quyền.

---

## 6. Nghĩa vụ phải thực hiện — chưa cái nào làm

| # | Nghĩa vụ | Nguồn | Trạng thái |
|---|---|---|---|
| 1 | `THIRD_PARTY_NOTICES` liệt kê AGPL-3.0 + toàn văn giấy phép | rule 5 | ✅ 2026-08-20 (`/THIRD_PARTY_NOTICES.md`) |
| 2 | Quy trình source-offer: công bố mã của bản RustDesk đã sửa | §13 / §§4–6 | ✅ **N/A theo Q97** — dùng nguyên bản nên không có bản sửa để công bố; Corresponding Source là repo gốc tại commit đã ghim |
| 3 | Theo dõi patch: mọi sửa đổi là commit riêng trên fork có ghi nguồn | rule 6 | ✅ **N/A theo Q97** — không sửa nên không có patch |
| 4 | Kiểm kê phụ thuộc bắc cầu của RustDesk | rule 1 | ⬜ trước phát hành thương mại |
| 5 | Legal review trước phát hành thương mại | invariant #6 | ⬇️ **HẠ cấp bởi Q97** — không sửa nên không kích §13; review xuống thành bước xác nhận tuỳ chọn, **không chặn** |

**Cập nhật 2026-08-20 (Q97):** chủ sản phẩm chọn **Rổ 1** — dùng RustDesk nguyên
bản, thương hiệu LTT chỉ ở Agent/web/tray. Vì không *modify*, §13 không kích, nên
nghĩa vụ #2/#3/#5 tan biến hoặc hạ cấp; chỉ còn #1 (đã làm) và #4 (kiểm kê phụ
thuộc, trước khi bán). **N3.2 hết bị chặn.**

**Không cái nào chặn N2** (danh tính thiết bị, enrollment, presence, broker) — N2
không chạm một dòng mã AGPL nào. Sau Q97, **N3 cũng không còn bị chặn** bởi giấy
phép; ranh giới hai tiến trình vẫn giữ vì nó phục vụ cả bảo mật (invariant #4/#5),
không chỉ giấy phép.

---

## 7. Câu hỏi cho luật sư — đủ cụ thể để trả lời được

Viết dạng câu hỏi đóng, kèm bối cảnh, để buổi tư vấn không mất thời gian giải
thích lại:

1. LTT build một client RustDesk có sẵn địa chỉ server và thương hiệu LTT. Đó
   **có** là "modify the Program" theo §13 không? *(Giả định làm việc của chúng
   tôi: có.)*
2. Nếu có: Corresponding Source phải công bố gồm những gì — chỉ bản RustDesk đã
   sửa, hay cả **LTT Nexus Agent** chạy ở tiến trình riêng và nói chuyện qua IPC?
3. Ranh giới **tiến trình + IPC** như mục 5 có đủ để Agent không bị coi là một
   phần của cùng tác phẩm không? Nếu chưa đủ, cần thêm điều kiện gì?
4. Control plane (`app.lttstudios.com`, mã độc quyền, **không** chứa mã AGPL, chỉ
   cấp vé uỷ quyền) có bị kéo vào nghĩa vụ nào không?
5. Nếu mua **RustDesk Server Pro**: nó phủ tới đâu? Cụ thể, nó **có** cấp quyền
   phân phối một *client* đóng nguồn không, hay client vẫn nằm dưới AGPL?
6. Nghĩa vụ khi khách tự tải client về máy họ (conveying) khác gì so với khi LTT
   chạy dịch vụ (§13)?

Câu 5 quan trọng hơn vẻ ngoài của nó: nếu Pro chỉ phủ phần server thì mua Pro
**không** gỡ được nghĩa vụ của client — mà client mới là thứ khách cài.

---

## 8. Trạng thái

**Status: PASS-WITH-RISK.**

PASS: đã kiểm kê đúng phiên bản/commit, đã đọc giấy phép từ nguồn gốc thay vì
trí nhớ, đã xác định hai cò súng khác nhau của AGPL, và đã chuyển ranh giới từ
một khẩu hiệu ("ranh giới tiến trình") thành một thiết kế kiểm chứng được.

RISK, và nó không nhỏ: **cái làm cho Nexus thành sản phẩm chính là cái kích hoạt
§13.** Rủi ro này thuộc loại **không đóng được bằng kỹ thuật** — chỉ luật sư
đóng được. Cho tới lúc đó, mọi công việc chạm mã AGPL đều mang rủi ro phải công
bố rộng hơn dự tính.

Vì vậy thứ tự trong `EXECUTION_PLAN.md` giữ nguyên và nay có thêm một lý do:
**N2 trước, N3 sau.** N2 không chạm AGPL, nên nó là công việc duy nhất tiến được
mà không đặt cược vào một câu trả lời pháp lý chưa có.
