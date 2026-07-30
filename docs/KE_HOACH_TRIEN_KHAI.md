# Kế hoạch triển khai

> Lập 2026-07-31. Đây là **kế hoạch** — nó ghi *ý định*.
> `NHAT_KY.md` ghi *sự thật đã xảy ra*. Khi hai file mâu thuẫn, nhật ký đúng,
> và phải sửa lại kế hoạch cho khớp thực tế.
>
> Quyết định nền: `QUYET_DINH_NEN_TANG.md`. Quy tắc làm việc: `AGENTS.md`.

---

## Cách đọc file này

- **Một hệ đánh số duy nhất: `H0`, `H1`, …** Trước đây dự án có bốn hệ song
  song (P0–P11, PA–PE, W1–W6) và không hệ nào tuyên bố mình đã bị thay thế —
  đó là nguyên nhân chính gây rối. Từ nay chỉ có `H`.
- Mỗi hạng mục có **tiêu chí hoàn thành**. Chưa đạt đủ thì chưa được đánh `[x]`,
  kể cả khi code đã viết xong.
- Ô `[ ]` → chưa làm. `[x]` → xong **và đã chạy test thật**, có ghi ngày.

---

## Bản đồ tổng

```
H0  Dọn nền                        ✅ 2026-07-31
     │
H1  Người dùng + PostgreSQL   ─┐
H2  Hàng đợi job              ─┼─►  H4  Nghiệm thu bằng apps/demo
H3  Sổ credit                 ─┘         │
                                         ▼
                              H5  Tool thật đầu tiên (thumbnail_api)
                                         │
                       ┌─────────────────┼─────────────────┐
                       ▼                 ▼                 ▼
              H6 Thanh toán    H7 File lớn (R2)    H8 Thêm tool
```

H1 → H2 → H3 làm theo thứ tự (job cần chủ sở hữu; credit cần job). Cả ba phải
xong mới nghiệm thu được ở H4.

---

## H0 — Dọn nền ✅ XONG 2026-07-31

**Mục tiêu:** không xây gì lên trên một cái nền có lỗi âm thầm.

- [x] `git init` + commit mốc chuẩn — trước đó ~45.000 dòng không hề có version
      control, trong khi đã có một bản production đang chạy
- [x] Cài `requirements-server.txt` (thiếu `itsdangerous` làm 7 module test
      không nạp được → `pytest` đỏ ngay từ khâu thu thập)
- [x] Chốt cận trên phiên bản cho mọi thư viện (Q17)
- [x] Sửa ranh giới đường dẫn: token store, các CSDL, nhật ký kiểm toán, cache,
      bản dịch, logo audit — tất cả đi qua `core.runtime_paths.data_path()`
- [x] Đổi cổng mặc định 8000 → 8100 ở `setup/`, `deploy/`, `cloudflare/`,
      `server/run.py`, tài liệu (Q4)
- [x] Dọn 19 tài liệu cũ vào `docs/_luutru/` kèm README giải thích (Q8)
- [x] Viết lại `AGENTS.md`, `CLAUDE.md`, `docs/00`, và bộ tài liệu gốc
- [x] Bộ khoá logic `tests/test_62_khoa_logic.py`

**Kết quả test:** `python -m pytest -q` → **1.422 pass, 1 skip, 23 subtests**
(238s) · `python tools/scan_source_secrets.py` → **0 finding**
· `tests/test_62_khoa_logic.py` → 11 pass

Chi tiết và lý do tổng số test đổi từ 1.424 → 1.423: xem `NHAT_KY.md`.

---

## H1 — Người dùng + PostgreSQL

**Mục tiêu:** hệ thống biết "ai đang dùng", và dữ liệu của người này người kia
không thấy được.

### H1.1 — Dựng PostgreSQL và lớp CSDL

- [ ] Cài PostgreSQL trên máy chủ; bổ sung bước này vào `setup/2-cai-dat.ps1`
      (tạo database + user riêng cho ứng dụng, mật khẩu sinh ngẫu nhiên, ghi
      vào `secrets/app.env` không BOM)
- [ ] Thêm `sqlalchemy`, `alembic`, `psycopg` vào `requirements-server.txt`
      **kèm cận trên** (Q17)
- [ ] `platform_core/db.py`: engine + session factory, đọc chuỗi kết nối từ
      biến môi trường `LTT_DATABASE_URL`, không bao giờ viết cứng
- [ ] Khởi tạo Alembic; migration đầu tiên tạo bảng rỗng
- [ ] Thêm bước sao lưu CSDL vào `deploy/windows/backup.ps1` (`pg_dump`) — sao
      lưu file như trước sẽ **không** bắt được dữ liệu Postgres

**Tiêu chí hoàn thành**
- `alembic upgrade head` chạy sạch trên một CSDL trống
- `alembic downgrade -1` rồi `upgrade` lại vẫn sạch (lùi được thì mới dám tiến)
- `/health/ready` báo `not_ready` khi CSDL không kết nối được, **kèm lý do**
- `backup.ps1` tạo ra file `pg_dump` khôi phục lại được — **đã thử khôi phục
  thật**, không chỉ tạo file

**Rủi ro:** mật khẩu CSDL lọt vào log hoặc thông báo lỗi. Test phải khẳng định
chuỗi kết nối không xuất hiện trong bất kỳ thông báo lỗi nào.

### H1.2 — Bảng người dùng và đăng nhập

- [ ] Bảng `users`: id, email, hash mật khẩu, vai trò (`admin`/`user`), trạng
      thái, thời điểm tạo, lần đăng nhập cuối
- [ ] Đưa `fastapi-users` vào (Q14) — **dựng song song**, chưa gỡ gì
- [ ] Phiên đăng nhập lưu phía máy chủ (hiện tại là cookie đã ký, không thu
      hồi được — nghĩa là không thể "đăng xuất khỏi mọi thiết bị")
- [ ] Giữ `admin` từ biến môi trường hoạt động song song trong lúc chuyển, để
      luôn còn một đường vào khi phần mới hỏng
- [ ] Chỉ khi đường mới đã xanh: gỡ `server/auth/session.py` cũ, cập nhật test

**Tiêu chí hoàn thành**
- Đăng ký → đăng nhập → đăng xuất → không vào lại được bằng cookie cũ
- Đổi mật khẩu làm **mọi phiên khác** hết hiệu lực
- Toàn bộ test cũ về CSRF, giới hạn tần suất, cookie an toàn vẫn xanh
- Không route nào trả dữ liệu khi chưa đăng nhập (có test quét mọi route)

**Ghi chú về cái giá đã biết:** `server/auth/` hiện có 4 file đã test và đang
chạy production. Thứ tự **dựng song song → chứng minh xanh → mới gỡ cũ** là bắt
buộc. Gỡ trước rồi thay là cách chắc chắn nhất để mất đường đăng nhập.

### H1.3 — Đăng ký, xác thực email, chống lạm dụng

Đây là hệ quả trực tiếp của Q7 (tự đăng ký + credit dùng thử). Không có phần
này thì credit dùng thử **sẽ** bị hút cạn bằng tài khoản ảo.

- [ ] Luồng đăng ký + gửi mã xác thực email (token dùng một lần, có hạn)
- [ ] **Chỉ cấp credit dùng thử SAU KHI xác thực email thành công**
- [ ] Chặn danh sách tên miền mail dùng-một-lần
- [ ] Giới hạn số tài khoản mới trên mỗi IP mỗi ngày
- [ ] Giới hạn tần suất cho chính route đăng ký (đã có sẵn bộ giới hạn, tái dùng)
- [ ] Quên mật khẩu / đặt lại mật khẩu

**Tiêu chí hoàn thành**
- Token xác thực: dùng lần thứ hai bị từ chối; quá hạn bị từ chối; token của
  người này không dùng cho người khác được — **có test cho cả ba**
- Tài khoản chưa xác thực có **0 credit** và không tạo được job
- Đăng ký lần thứ N+1 từ cùng một IP trong ngày bị từ chối
- Không có phản hồi nào tiết lộ "email này đã tồn tại" (lộ danh sách khách hàng)

### H1.4 — Phân quyền app cho từng người dùng

- [ ] Bảng phân quyền: mỗi (user × app) → `mở` / `khoá` / `ẩn`
- [ ] Trang chủ chỉ hiện app mà người đó được phép thấy
- [ ] Chặn ở tầng route, **không chỉ ẩn trên giao diện** — ẩn nút không phải là
      phân quyền

**Tiêu chí hoàn thành**
- Người dùng gọi thẳng URL của app bị khoá → bị từ chối, có test
- Admin thấy hết

---

## H2 — Hàng đợi job

**Mục tiêu:** việc dài chạy được ngoài vòng đời một request, sống sót qua khởi
động lại, và không bao giờ bị hai worker làm hai lần.

- [ ] Đưa `procrastinate` vào (Q13), tạo bảng của nó bằng migration
- [ ] Bảng `jobs` của ứng dụng: id, chủ sở hữu, app, loại job, tham số, trạng
      thái, tiến độ, kết quả, lỗi, thời điểm — **tách khỏi bảng nội bộ của
      procrastinate** để đổi thư viện sau này không phải đổi mô hình nghiệp vụ
- [ ] Dịch vụ Windows `LTTWorker` riêng (Q6), đăng ký bằng NSSM như `LTTWeb`
- [ ] Worker khai báo năng lực (`api` / `ffmpeg` / `gpu`); job chỉ vào worker
      có đủ năng lực — khớp với trường `requires` đã có sẵn trong hợp đồng app
- [ ] Thử lại luỹ thừa; phân biệt lỗi tạm thời (nên thử lại) và lỗi vĩnh viễn
      (đừng thử lại — thử lại một lỗi tham số chỉ tốn tiền API)
- [ ] Cửa sổ chống trùng: cùng một người gửi cùng tham số trong N giây → nhận
      lại job cũ, không tạo job mới
- [ ] Đẩy tiến độ về trình duyệt
- [ ] Job "mồ côi" (worker chết giữa chừng) phải được nhận ra và xử lý

**Tiêu chí hoàn thành**
- Tắt worker giữa lúc chạy → bật lại → job được nhận lại hoặc báo lỗi rõ ràng,
  **không nằm im mãi ở trạng thái "đang chạy"**
- Hai worker cùng chạy → không job nào bị làm hai lần (có test)
- Khởi động lại máy → job đang chờ vẫn còn
- Người dùng A không đọc được job của người dùng B (có test ở tầng route)
- `LTTWeb` restart **không** giết job đang chạy

**Rủi ro lớn nhất:** job bị làm hai lần trên một API tính tiền. Test phải chứng
minh điều này, không được suy luận.

---

## H3 — Sổ credit

**Mục tiêu:** tiền không bao giờ sai. Đây là phần ít code nhất nhưng ít được
phép sai nhất.

- [ ] Bảng sổ **chỉ ghi thêm** (append-only): mọi biến động là một dòng mới.
      Số dư = tổng của sổ, **không bao giờ là một ô được sửa đè**
- [ ] Ba thao tác, tất cả trong **một giao dịch CSDL** cùng với việc tạo job:
      - **giữ chỗ** — khi nhận job, trừ tạm theo giá ước tính
      - **quyết toán** — khi xong, chốt theo giá thật
      - **hoàn lại** — khi lỗi, trả đủ phần đã giữ
- [ ] Từ chối job khi không đủ credit, **trước khi** gọi API tính tiền
- [ ] Chặn mọi đường lách: nút "Tạo lại", gửi lại form, F5 — đều phải qua đúng
      cổng kiểm tra như lần đầu
- [ ] Trang quản trị bằng `sqladmin` (Q15): xem sổ, cấp credit tay, xem lịch sử
- [ ] Admin cấp credit cũng phải ghi vào sổ, kèm ai cấp và vì sao

**Tiêu chí hoàn thành**
- Số dư tính từ sổ **luôn** khớp với tổng các dòng — có test chạy nhiều thao
  tác đồng thời rồi đối chiếu
- Job lỗi → credit được hoàn **đủ**, không thiếu không thừa
- Job chạy hai lần (do thử lại) → **chỉ trừ tiền một lần**
- Không đủ credit → job bị từ chối và **không có lệnh gọi API nào được phát ra**
- Hai request đồng thời của cùng một người không tạo ra số dư âm

**Tham khảo có sẵn:** `app/modules/seedance_video/cost.py` bên `D:\BOT GEMINI`
đã có mô hình giá theo token thật + markup + quy đổi VND + `reserve_check`.
Đọc để học, **viết lại** theo hợp đồng app của dự án này (Q3).

**Lỗi đã có tiền lệ:** BOT GEMINI từng để nút "Tạo lại" đi vòng qua cổng kiểm
tra, cho phép chạy job không mất tiền và xếp hàng vô hạn. Họ đã phải vá
(`P0-5`). Đừng lặp lại — viết test cho đúng đường đó ngay từ đầu.

---

## H4 — Nghiệm thu bằng `apps/demo`

**Mục tiêu:** chứng minh cả chuỗi thông suốt **trước khi** cắm một tool tốn
tiền API vào.

- [ ] Chạy đủ chuỗi: đăng ký → xác thực email → nhận credit dùng thử → tạo job
      → worker nhận → xử lý → trả kết quả → trừ credit đúng → xem lịch sử
- [ ] Hỏng có chủ ý: giết worker giữa chừng → credit phải được hoàn
- [ ] Hỏng có chủ ý: tắt CSDL → giao diện báo lỗi rõ ràng, không trắng trang
- [ ] Hai người dùng chạy song song → không ai thấy dữ liệu của ai
- [ ] Kiểm tra thật bằng trình duyệt, không chỉ bằng test

**Tiêu chí hoàn thành:** cả năm mục trên đã chạy thật và ghi kết quả vào
`NHAT_KY.md`. **Chưa xanh thì không sang H5** — cắm một tool tính tiền vào một
đường ống chưa chứng minh được là cách đắt nhất để phát hiện lỗi.

---

## H5 — Tool thật đầu tiên: `thumbnail_api`

**Mục tiêu:** một tool có người trả tiền, đi qua đúng hợp đồng app.

- [ ] Copy `app/modules/thumbnail_api/` từ `D:\BOT GEMINI` sang — theo danh
      sách "phải mang theo" ở `KHAO_SAT_BOT_GEMINI.md` mục 3
- [ ] Dựng lại thành `apps/thumbnail/` theo hợp đồng app
- [ ] Viết `credit_cost` cho nó
- [ ] Khoá API của nhà cung cấp nằm phía máy chủ, **không bao giờ xuống trình
      duyệt**

**Tiêu chí hoàn thành**
- **Không sửa một dòng nào** trong `platform_core/` hay `server/`. Nếu buộc
  phải sửa → dừng, ghi lại vì sao, bổ sung vào hợp đồng app (đây chính là phép
  thử thật của hợp đồng)
- App tự hiện trên trang chủ và sidebar
- Chạy thật một job, trừ đúng credit
- Quét bí mật 0 finding

---

## H6 — Thanh toán *(chưa chốt cách làm)*

Chỉ bắt đầu khi H5 đã có người dùng thật. Cần chốt trước: cổng thanh toán nào
(VNPAY / MoMo / chuyển khoản có webhook), hoá đơn, hoàn tiền.

Nguyên tắc bắt buộc từ bây giờ: **mọi thứ liên quan tiền đi qua sổ credit ở
H3**, không bao giờ có đường tắt riêng cho thanh toán.

---

## H7 — File lớn (R2) *(chưa chốt)*

Bắt buộc trước khi làm bất kỳ tool nào thuộc nhóm FFmpeg hoặc GPU
(`auto_sub_video`, `concat_pro`, `cut_clip_short`, `video_upscale`).

- Trình duyệt upload **thẳng** lên R2, không đi qua máy chủ — trần 100 MB của
  Cloudflare nằm ở đường qua máy chủ
- Thêm backend R2 vào `platform_core/storage.py`, **không sửa app nào**
- Kiểm duyệt file người lạ tải lên trước khi đưa vào FFmpeg — file media dị
  dạng là đường thực thi mã có thật

---

## H8 — Thêm tool

Theo thứ tự khuyến nghị trong `KHAO_SAT_BOT_GEMINI.md`:

1. `youtube_script` (139 dòng — rẻ nhất để kiểm chứng lại hợp đồng app)
2. `seedance_video` (5.508 dòng — giá trị thương mại cao nhất; cần H7)
3. `plenx` (2.731 dòng — cùng cấu trúc, port chung một lượt)
4. Nhóm FFmpeg / GPU (cần H7)

**Không đưa lên nền tảng:** mọi module dùng cookie hoặc trình duyệt
(`whisk_nano` và 16 module đã archive). Lý do đầy đủ ở `KHAO_SAT_BOT_GEMINI.md`
nhóm D.

---

## Việc phải làm ngay ở phiên tiếp theo

1. **H1.1** — dựng PostgreSQL + SQLAlchemy + Alembic, migration đầu tiên.
2. Bổ sung bước cài Postgres vào `setup/2-cai-dat.ps1` và bước `pg_dump` vào
   `backup.ps1` **trong cùng lần đó** — thêm CSDL mà quên sao lưu là một sự cố
   đang chờ xảy ra.
3. Dựng Cloudflare Tunnel trên máy này (`setup/3-cloudflare.ps1`) — việc này
   độc lập với H1, làm lúc nào cũng được, nhưng cần người dùng đăng nhập
   Cloudflare bằng trình duyệt.
