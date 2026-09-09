# VPS V2 — VẬT CẢN CÒN LẠI

> Ba loại, và trộn chúng vào nhau là cách để không sửa được cái nào:
>
> | Loại | Ai gỡ được | Có gỡ bằng mã không |
> |---|---|---|
> | **HẠ TẦNG** | mua/dựng | ❌ không, dòng nào cũng vô ích |
> | **VẬN HÀNH** | một thao tác trước khi deploy | ❌ nhưng mã đã chuẩn bị sẵn chỗ |
> | **SẢN PHẨM** | chủ sản phẩm chốt | ❌ chờ một quyết định, không chờ mã |

Cập nhật: 2026-09-09, cuối Prompt 11.

---

## ⛔ B-01 · HẠ TẦNG — không có lớp sao lưu độc lập

**Trạng thái:** `CODE READY / INFRA BLOCKED`.

Sản phẩm hiện chỉ có **một** lớp bảo vệ dữ liệu: ảnh chụp LVM-thin, **cùng pool**
với đĩa gốc. Hỏng đĩa, hỏng pool, hỏng node ⇒ **mất cả hai**.

Không phải khiếm khuyết của mã: `apps/vps/sao_luu_doc_lap.py` khai đủ hợp đồng
năng lực và trả `sao_luu_doc_lap=False` đúng sự thật; giao diện nói ra; runbook
có mục riêng. Thiếu là **đích sao lưu**, và đó là thứ phải mua/dựng.

**Trần điểm mà nó áp** — theo chính `CORE/QUALITY_SCORECARD.md`:

> *snapshot on same storage only ⇒ "hardware backup/disaster protection" ≤ 50
> regardless of code quality*

⇒ Backup/DR **≤ 50**. Không dòng mã nào gỡ được.

**Điều kiện để câu này đổi** (cả bốn, thiếu một là chưa):

1. một đích có **failure domain độc lập** (PBS, hoặc tương đương);
2. khai `LTT_VPS_PBS_URL` / `_DATASTORE` / `_USER`;
3. một job sao lưu theo lịch **và** một job xác minh chạy sau nó;
4. một lần **diễn tập khôi phục** thật, có ghi kết quả.

⚠️ Điền biến môi trường mà không chạy job là dựng đúng cái nhãn xanh giả mà cả
chương trình này sinh ra để dọn. `nang_luc()` sẽ trả `True` — và nó sẽ nói dối.

---

## ⛔ B-02 · HẠ TẦNG — một node PVE, chạy lồng, không HA

`manifest.notes`: *"Proxmox chạy LỒNG trong VMware trên máy B"*. Một node, không
cụm, không quorum, không UPS đã xác nhận.

Mã không biến một host lồng thành HA, và `START_HERE.md` §12 nói thẳng điều đó.

⇒ Điểm **LIVE INFRA / RESILIENCE** không thể ≥ 98 hôm nay, và nó phải được báo
**tách riêng** thay vì trung bình vào điểm phần mềm.

---

## 🟡 B-03 · VẬN HÀNH — production cần CA của Proxmox *(đã deploy, chưa đặt CA)*

> **Cập nhật 2026-09-09 sau khi deploy.** Đã deploy `5bb3a5a0` lên production mà
> **chưa** đặt `LTT_VPS_PROXMOX_CA`. Không phải sơ suất: chủ sản phẩm xác nhận
> *"chưa có VPS nào chạy thật trên production, chưa có khách"* — với **0 máy**
> đang chạy thì fail-closed không cắt dịch vụ của ai.
>
> Nên vật cản **hạ từ 🔴 xuống 🟡**: nó không còn chặn deploy, nhưng nó **vẫn
> chặn việc bán máy đầu tiên**. Ngày có máy thật đầu tiên, mọi đường chạm
> Proxmox (tạo máy, console, bật/tắt, chụp ảnh, đối chiếu) sẽ hỏng cho tới khi
> CA có mặt.
>
> 🔴 **Và một sự thật đo được lúc deploy, ghi lại vì nó ngược với tài liệu:**
> `C:\LTTPlatform\secrets\app.env` **không đọc được từ phiên thường** (ACL — cố
> ý), và lượt kiểm nâng quyền trả `EXITCODE=2` nghĩa là **tệp không tồn tại ở
> đường dẫn đó**. Env của dịch vụ do `nssm` nướng lúc cài (log deploy: *"Da nap
> bi mat vao moi truong dich vu"*). ⇒ Đừng đi tìm `app.env` để sửa; đường đúng
> là `setup/dat_bien_env.ps1` / `nap_lai_env.ps1` rồi cài lại cấu hình dịch vụ.

**Nếu deploy khi ĐÃ có máy khách thật thì đây là vật cản chặn dịch vụ.**

Pha 07 đóng lỗ `verify=False`: từ nay `LTT_ENV=production` **và** không có
`LTT_VPS_PROXMOX_CA` ⇒ `doc_cau_hinh` ném `ChuaCauHinh`, tức app VPS **không nối
được Proxmox**.

Đó là hành vi đúng — `verify=False` trên đường quản trị nghĩa là ai chen được vào
đường đi cũng đọc và sửa được lệnh, kể cả lệnh xoá đĩa. Nhưng nó là một **thay
đổi phá vỡ** với `secrets/app.env` hiện tại.

### Việc phải làm trước khi deploy

```bash
python tools/vps_kiem_cau_hinh.py
```

Mục **TLS QUAN TRI** phải in `[x] cau hinh TLS phat hanh duoc`. Nếu không:

1. lấy CA của Proxmox (`/etc/pve/pve-root-ca.pem` trên node) đặt lên máy chủ;
2. thêm `LTT_VPS_PROXMOX_CA=<đường dẫn>` vào `C:\LTTPlatform\secrets\app.env`;
3. **chạy `setup/nap_lai_env.ps1`** — `nssm` nướng biến môi trường lúc **CÀI**,
   nên sửa `app.env` rồi `Restart-Service` là **không đủ**. Đã dính ba lần.

⚠️ Đường thoát `LTT_VPS_PROXMOX_TLS_BO_QUA=1` **không** mở ở production — cố ý.
Mở được thì hàng rào chỉ còn là một quy ước, và quy ước thua một lần sao chép
`app.env` từ máy dev sang máy chủ.

---

## 🟡 B-04 · VẬN HÀNH — chưa có VM thử, nên chưa nghiệm thu live

`LIVE ACCEPTANCE BLOCKED`.

Prompt 11 §6 mô tả một mạch nghiệm thu đầy đủ: tạo → cài → console → tắt → bật →
khởi động lại → chụp → khôi phục → cài lại → xoá, rồi kiểm VM/IP/NAT/DHCP đã dọn.
Nó **chưa chạy**, vì chưa có tài nguyên thử nào được xác nhận là của chương trình
này.

⛔ Không chạy nó trên máy khách. `START_HERE.md` §9 cấm, và nó đúng: một mạch
nghiệm thu có bước "xoá vĩnh viễn".

Thiếu thêm một ràng buộc vật lý: **máy B chỉ có một suất đồng thời**
(`DONG_THOI_MAY_B=1`), nên một lượt nghiệm thu live loại trừ mọi việc khác dùng
máy đó.

⇒ Điểm **END-TO-END PRODUCT** bị chặn trần cho tới khi mạch này chạy thật.

---

## 🟡 B-05 · SẢN PHẨM — chặn SMTP/25 ra ngoài chưa được chốt

Prompt 07 §C đề nghị chặn cổng 25 ra ngoài **theo mặc định** *"unless business
decision explicitly says otherwise"*.

**Chưa làm, và cố ý chưa làm.** Đó là một thay đổi chính sách mạng nhìn thấy
được với khách trên một sản phẩm đang chạy, không phải một bản vá kỹ thuật. Chủ
sản phẩm chốt thì nó là vài dòng trên router (`services/router.py` đã có đường
gọi `nft`).

**Cái đã làm thay vào đó:** `services/cach_ly.py` — nút cắt mạng cho **một** máy,
có lý do bắt buộc, có đường gỡ, có nhật ký. Đó là công cụ mà người vận hành thật
sự cần khi một máy đang phát tán thư rác, và nó không đụng tới khách khác.

⛔ Không có vòng lặp nào tự gọi `cach_ly()` — `test_557` ghim điều đó. Một tín
hiệu heuristic tự cắt mạng là cắt mạng của một khách đang chạy việc hợp lệ, đúng
lúc họ cần nó nhất.

---

## 🟡 B-06 · SẢN PHẨM — `/api/v1` vẫn đóng cho VPS

Xem `ADR_INDEX.md` ADR-06. Tóm tắt: hợp đồng của API công khai là *quote → giữ
chỗ → quyết toán* cho **một lượt chạy**; một máy ảo là một **hợp đồng thuê có
thời hạn**. Ép vào khuôn đó là dựng một hợp đồng nói sai về thứ nó bán.

Mảnh khó nhất đã có: `vps_thao_tac.id` — một định danh thao tác bền, tra được,
tức thứ một API đúng sẽ trả về sau mỗi lệnh mutating. Còn thiếu là ba quyết định
sản phẩm (giá theo thời gian, phạm vi khoá cho tài nguyên khách **sở hữu**, hạn
mức cho thao tác phá huỷ).

---

## 🟢 B-07 · Nhãn `lifecycle` vẫn là `development`

Giữ nguyên, và đó là kết luận chứ không phải quên.

`START_HERE.md` §12 và `QUALITY_SCORECARD.md` đòi bằng chứng live trước khi đổi
nhãn. B-04 chưa gỡ ⇒ chưa có bằng chứng ⇒ nhãn không đổi. Q73 của kho này cũng
cấm dùng nhãn marketing để giả trạng thái.

Đổi được khi: B-03 xong (deploy được), B-04 xong (mạch live chạy), và gate cuối
xanh trên cây đã deploy.
