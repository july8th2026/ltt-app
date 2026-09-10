# ADR INDEX — VPS V2

Mỗi quyết định kiến trúc của chương trình VPS V2 có một dòng ở đây. Lý do **luôn**
đi kèm: một quyết định không có lý do là một quyết định sẽ bị lật lại bởi người
không biết vì sao nó có.

| ADR | Pha | Quyết định | Lý do ngắn | Trạng thái |
|---|---|---|---|---|
| [ADR-01](#adr-01) | 01 | Tách trạng thái thành cột riêng, **giữ `trang_thai` làm cột chiếu** | 18 tệp test + 7 template + `nhan.py` đọc nó | ĐÃ CHỐT |
| [ADR-02](#adr-02) | 02 | Bảng `vps_thao_tac` riêng; chạy bằng job, khoá bằng lease sẵn có | `Job` ≠ thao tác; nhưng không dựng khung công việc thứ hai | ĐÃ CHỐT |
| [ADR-03](#adr-03) | 03 | `bat`/`tat`/`khoi_dong_lai`/`khoi_phuc` chuyển sang hàng đợi job | Khởi động lại *thật* vượt trần 100 giây của Cloudflare | ĐÃ CHỐT |
| [ADR-04](#adr-04) | 04 | **Không** chụp "ảnh an toàn" trước khi khôi phục | Cùng pool ⇒ bảo đảm giả; và đĩa là nút thắt của cả sản phẩm | ĐÃ CHỐT |
| [ADR-05](#adr-05) | 05 | Phát hiện của vòng đối chiếu có **năm mức**, mặc định là mức an toàn nhất | Ba loại phát hiện đòi ba hành động khác hẳn nhau | ĐÃ CHỐT |
| [ADR-06](#adr-06) | 09 | VPS **vẫn đóng** ở `/api/v1` | Hợp đồng của API là *một lượt chạy*; máy ảo là một *hợp đồng thuê có thời hạn* | ĐÃ CHỐT |

---

## ADR-01 — Giữ `trang_thai` làm cột chiếu {#adr-01}

**Bối cảnh.** `vps_instance.trang_thai` (`String(16)`) hiện gánh năm khái niệm: vòng đời
nghiệp vụ, điện, treo-vì-tiền, lỗi, đã xoá. `CORE/TARGET_ARCHITECTURE.md` đòi tách.

**Quyết định.** Thêm các cột độc lập, và **giữ nguyên `trang_thai`** như một *projection*
được tính lại từ chúng ở một chỗ duy nhất.

**Vì sao không xoá `trang_thai`.** 18 tệp test, 7 template, `nhan.py` (4 bảng tra), và
phần lớn `routes.py` đọc cột này. Xoá nó biến một pha thành một cuộc viết lại toàn app,
mà **không giảm một rủi ro nào** — rủi ro nằm ở chỗ code *ghi* nó tuỳ tiện, không ở chỗ
code *đọc* nó.

**Hệ quả.** Phải có đúng **một** chỗ tính `trang_thai` từ các cột mới, và mọi lệnh ghi
thẳng `may.trang_thai = "..."` ngoài chỗ đó là bug (Pha 10 sẽ quét).

---

## ADR-02 — Bảng thao tác riêng, không phải bảng job thứ hai {#adr-02}

**Bối cảnh.** Pack đòi một *durable operation* cho mọi mutation dài. Nền tảng đã có
`platform_core/jobs.py` (bền, có progress/retry/`mark_ambiguous`/`reclaim_orphans`) và
`platform_core/leases.py`.

**Quyết định.** Thêm bảng `vps_thao_tac`. Nó **không** thay `Job`: mỗi thao tác dài
được *thi hành* bởi một job, và được *serialize* bởi lease `vps-may:{id}` đã có.

**Vì sao không tái dùng thẳng `Job`.** Hai vòng đời khác nhau. `Job` trả lời *"lượt việc
này của worker đã xong chưa"* — nó có thể thử lại nhiều lần, mỗi lần một `Job` row.
Thao tác trả lời *"cái máy này đang bị làm gì, ai bảo, tới đâu rồi"* — nó sống xuyên qua
nhiều lần thử, và nó là thứ UI hiển thị cho khách.

**Vì sao không dựng hàng đợi mới.** Luật §L của `OPERATING_CONTRACT`: không duplicate
job framework/lease/credit ledger khi nền tảng đã có chủ sở hữu canonical.

---

## ADR-03 — Bốn thao tác điều khiển chuyển sang hàng đợi {#adr-03}

**Bối cảnh.** `services/dieu_khien.py` mở đầu bằng một lập luận: ba thao tác bật/tắt/khởi
động lại *"là một lệnh gọi API rồi trả về ngay… nhét chúng vào hàng đợi là bắt khách chờ
một vòng worker để làm việc mất 200 mili-giây"*.

**Quyết định.** Chuyển cả bốn (`bat`, `tat`, `khoi_dong_lai`, `khoi_phuc`) sang job type
mới `vps.control`. Route trả về **ngay** với id thao tác; UI hiện *"Đang …"*.

**Vì sao lập luận cũ không còn đúng.** Nó đúng với **hành vi hiện tại**, mà hành vi hiện
tại chính là lỗi đang sửa: 200 ms là thời gian để Proxmox *nhận* lệnh, không phải để máy
*tắt xong*. Một lần khởi động lại Windows đúng nghĩa — tắt mềm, chờ STOPPED, bật, chờ
RUNNING — là hàng chục giây tới vài phút. Cloudflare cắt request ở **100 giây**
(`CLAUDE.md` luật 19).

⇒ Giữ nó chạy thẳng thì hoặc là nói dối (như hiện nay), hoặc là timeout ở biên. Không có
đường thứ ba.

**Hệ quả.** `manifest.job_types` + `max_runtime_s` thêm `vps.control`. Docstring đầu
`dieu_khien.py` **phải viết lại** — để nguyên là để lại một lời giải thích sai cho phiên sau.


---

## ADR-04 — Không chụp "ảnh an toàn" trước khi khôi phục {#adr-04}

**Bối cảnh.** Prompt 04 cho phép chụp một điểm an toàn trước khi rollback *"nếu hạ
tầng đỡ được và nó không tạo ra một bảo đảm giả"*.

**Quyết định.** Không chụp.

**Vì sao.** Hai lý do, và lý do thứ hai là lý do thật:

1. ảnh nằm **cùng pool** với đĩa gốc, nên nó không cứu được thứ mà khách sợ nhất
   khi bấm nút này (hỏng phần cứng). Gọi nó là "an toàn" là nói quá — đúng loại
   lời hứa mà cả chương trình này sinh ra để dọn;
2. đĩa là **nút thắt** của cả sản phẩm: 475 GB LVM-thin cho mọi khách. Một ảnh
   thêm cho mỗi lần khôi phục, **nằm ngoài vòng dọn hằng tuần** (vòng đó chỉ dọn
   ảnh mang tiền tố `ltt` theo lịch), là một đường rò dung lượng không ai đóng.

**Thay vào đó.** Đường phá huỷ đã có hai rào của chính nó: gõ đúng tên máy để xác
nhận, và tên ảnh phải khớp chính xác — hỏi lại ngay trước khi rollback.

**Ghim bằng phép kiểm.** `test_554::test_KHONG_chup_anh_an_toan_truoc_khi_khoi_phuc`.
Ai thêm bước ấy vào sau này sẽ làm nó đỏ và đọc được lý do ở đây.

---

## ADR-05 — Phát hiện của vòng đối chiếu có năm mức {#adr-05}

**Bối cảnh.** `doi_chieu.quet` trả về một danh sách phẳng gọi là "mồ côi".

**Quyết định.** Mỗi phát hiện mang một `muc_do` trong năm mức: `TU_CHUA_DUOC`,
`THU_LAI_DUOC`, `CAN_NGUOI`, `NGHI_MO_COI`, `VO_BAT_BIEN`. Mặc định là
`NGHI_MO_COI` — phía an toàn.

**Vì sao.** Ba thứ dưới đây nằm chung một danh sách trong bản cũ, và chúng đòi ba
hành động khác hẳn nhau:

* một **đường NAT không có trong sổ** dẫn gói từ Internet vào mạng riêng — đó là
  lỗ hổng bảo mật, xử ngay;
* một **Reserved IP thừa** là 3 đô-la mỗi tháng — xử khi rảnh;
* một **VM đang được job khác dựng dở** trông y hệt rác — **đừng đụng vào**.

Gộp làm một là mời người đọc xử lý sai, và cái sai đắt nhất là xoá nhầm.

**Hệ quả.** `CAM_TU_XU` là một tập hợp có tên, không phải một danh sách chép tay ở
ba nơi. Ba bản chép tay là ba nơi sẽ lệch nhau, và chỗ lệch đầu tiên xoá một VM
của khách.


---

## ADR-06 — VPS vẫn đóng ở API công khai {#adr-06}

**Bối cảnh.** Prompt 09 §F: *"If the platform already has an API-key/public API
convention, extend it rather than inventing another."* Nền tảng có
`platform_core/public_api/` với hợp đồng **quote → giữ chỗ → quyết toán** cho một
lượt gọi công cụ.

**Quyết định.** Không mở `/api/v1` cho VPS trong chương trình này.

**Vì sao — và đây là một quyết định, không phải một khoảng trống.**

Hợp đồng ấy mô tả **một lượt chạy tính tiền một lần**. Một máy ảo là một **hợp
đồng thuê có thời hạn**: không có "một lượt" nào để báo giá, tiền đi qua
`paid_until` mỗi 30 ngày, và thứ khách mua là *máy còn sống hay không* chứ không
phải *bao nhiêu lượt*. `docs/PUBLIC_API/APP_API_COVERAGE_FINAL.md` đã ghi đúng
điều đó từ trước (`vps` = DEFER, "không có hợp đồng job").

Ép VPS vào khuôn đó là dựng một hợp đồng **nói sai về thứ nó bán** — đắt hơn hẳn
việc chưa có API, vì một hợp đồng công khai rất khó rút lại.

**Cái đã đổi, và nó thu hẹp vật cản.** Trước VPS V2 chưa có **định danh thao
tác**: không có gì để một API trả về sau một lệnh mutating, nên `POST /vps/.../
restart` chỉ có thể trả 200 hoặc nói dối. Giờ `vps_thao_tac.id` tồn tại, bền, và
tra được — tức mảnh khó nhất của một API đúng đã có sẵn.

**Còn thiếu, và nó là việc SẢN PHẨM chứ không phải việc mã:**

1. một hợp đồng giá cho *thuê theo thời gian* trong `public_api/pricing.py`;
2. quyết định phạm vi khoá (`scopes`) cho một tài nguyên khách **sở hữu**, khác
   hẳn một công cụ khách **gọi**;
3. chính sách hạn mức cho các thao tác phá huỷ qua API.

Chủ sản phẩm chốt ba điểm đó thì phần mã còn lại là một tầng mỏng trên
`dieu_khien.xin` và `sao_luu.xin_khoi_phuc` — cả hai đã trả về một thao tác có id.
