"""`core.code` — chạy mã JS người soạn tự viết, trong vỏ RIÊNG (P-D mục 3).

⭐ Lan `wfd` (P-D mục 1–2) đã dựng và ĐO cái vỏ hai lớp
   (`platform_core/workflow/code_sandbox.py` + `connector_runner/src/
   code_sandbox.js`) nhưng CỐ Ý không đăng ký node — prompt gốc §33: *"không
   đưa Code Node vào early phase khi sandbox chưa hoàn thành"*. Bảy đường
   thoát D1–D7 (`tests/test_4231_wf_code_dien_tap_thoat_vo.py`) đều đã có
   phép "PHẢI THẤT BẠI" + phép TIÊM LỖI xanh trên `main`, nên điều kiện đó
   nay đã đạt. Tệp này CHỈ đăng ký — ⛔ không sửa `code_sandbox.js`/`.py`.

## Vì sao một `job_type` THỨ BA (`nut.JOB_TYPE_CODE`), không dùng lại hai cái cũ

`piece.*` (`JOB_TYPE_PIECE`) chạy qua `connector.chay()` — vỏ
`ltt-connector-runner`, **luôn mở** `proxy_egress` (spec §9.4). `core.code`
thì ngược lại: `code_sandbox.chay()` KHÔNG mở proxy (không domain nào được
phép cho mã tuỳ ý) và dùng vỏ KHÁC (`ltt-code-runner`, ACL/loopback riêng).
Nộp job của `core.code` qua nhánh xử lý của `piece.*`
(`apps/connector_runner/jobs.py::_chay_piece`) sẽ gọi `_connector.chay(...,
piece=meta["piece"], ...)` — node này không có `piece`/`op`/`ten_action`,
nên đó là một nhánh SAI, không phải một nhánh thiếu tham số. `JOB_TYPE_CONNECTOR`
(youtube) càng không khớp: nó chạy TRỰC TIẾP trong tiến trình worker bằng
`httpx`, không qua AppContainer nào cả. Ba mô hình thi hành khác nhau ⇒ ba
hằng — đúng dự liệu của `nut.JOB_TYPE_KHONG_TOOLSPEC`: *"một bộ thi hành THỨ
BA xuất hiện mà không khai gì sẽ ném ở `__post_init__`"*.

## Đi qua ĐÚNG cửa `bao_gia._gia_node` — nhánh GIÁ CỐ ĐỊNH

`_dinh_nghia_gia_co_dinh()` (gộp `wfp`+`wfg`, 25/09) trả `NodeDefinition` của
một node khi `job_type` nằm trong `JOB_TYPE_KHONG_TOOLSPEC` — `core.code` đi
đúng nhánh đó (KHÔNG bọc ToolSpec nên KHÔNG thể đi nhánh `cc.get(ten_cong_cu)`
phía dưới, và thứ tự hai nhánh trong `_gia_node` "có nghĩa, đừng đảo" đã chốt
25/09).

⚠️ `gia=Gia.co_dinh(1)` — ⛔ KHÔNG `0` như `core.http`/`connector.youtube.upload`,
   và đó là một lựa chọn có chủ ý, khác hai node kia: cả hai node đó bị chặn
   bởi một hạn mức KHÁC nền tảng không kiểm soát được (thời gian phản hồi của
   một API ngoài); `core.code` thì không — trần của nó (isolate 128 MB/8 s +
   Job Object 512 MB) là một hạn mức của CHÍNH nền tảng, và một job giá 0 CPU
   trên một lane chỉ có 2 suất admission (`TAI_NGUYEN_CONNECTOR`, spec §11.2)
   là một lời mời spam job miễn phí để chiếm hết lane. 1 credit là mức phí
   DANH NGHĨA — không mô phỏng chi phí điện thật (bảng giá hôm nay tính theo
   giây GPU/lệnh API trả tiền, không cái nào áp dụng cho CPU nội bộ có trần
   cứng) — chỉ để lượt chạy này có một cái giá GHI ĐƯỢC vào `bang_gia`/
   `gia_tran` thay vì biến mất vào nhóm "miễn phí" cùng những node không có
   trần nào ngoài nền tảng kiểm soát. `INFERRED`, cùng lời cảnh báo ở đầu tệp
   `bao_gia.py`: chưa có đối chứng ngành, phải đo lại bằng `actual_cost` thật
   ngay khi có lượt chạy đầu tiên.

## `side_effect="none"` — lý do, không phải mặc định lười

Mã người soạn CHẠY TUỲ Ý, nhưng chính cái vỏ này (P-D mục 4, bảy đường D1–D7)
tồn tại để đảm bảo nó **không chạm được** gì ngoài `inputs`/giá trị trả về:
không mạng (D3/D4), không đọc/ghi tệp ngoài vỏ (D1/D2), không sinh tiến trình
con (D5), không đọc biến môi trường bí mật (D6). Với ranh giới đó GIỮ ĐÚNG,
một lượt chạy `core.code` không để lại dấu vết nào ngoài `WorkflowRun` của
chính nó — đúng định nghĩa `side_effect="none"` (`cau_noi.py` dùng nó để
đơn giản hoá khoá idempotency, §`_khoa_idem`). ⛔ KHÔNG suy ra "external" cho
chắc: nếu ranh giới ấy từng bị vượt qua, đó là một lỗ hổng bảo mật mà bảy
phép D1–D7 phải bắt được — không phải một thứ `side_effect` sửa được bằng
cách khai bảo thủ hơn. `idempotency_key_fields=()` theo đúng nhánh
`side_effect == "none"` của `cau_noi._khoa_idem` (khoá theo
`[run.id, đường thi hành, attempt]`, không cần trường nào của tham số).

## `quyen=frozenset()` — không xin quyền nào

`QUYEN` (`network`, `credential`, `gpu`, `filesystem`, `subprocess`) mô tả
node này CẦN nền tảng cấp gì. `core.code` không gọi credential nào (không có
`credential_ref`), và bốn quyền còn lại đúng là bốn thứ vỏ chặn — khai bất kỳ
quyền nào trong số đó là khai sai về những gì node THẬT SỰ có thể làm.

## `resource`/timeout — dùng lại trần ĐÃ CÓ, không đặt số mới

`code_sandbox.chay()` tự áp `HAN_ISOLATE_MAC_DINH_MS` (8 s, đo bởi V8) +
`BO_NHO_ISOLATE_MAC_DINH_MB` (128 MB, trần isolate) bên trong hạn giờ TRÔI +
Job Object (`job_object.BO_NHO_MAC_DINH_MB` = 512 MB) đã có của
`vo_boc.chay`. Node KHÔNG khai `timeout_expr` (chuỗi rỗng, giống mọi node
`piece.*`/`connector.*` khác — trường đó chỉ phục vụ node bọc ToolSpec, xem
`nut.tu_toolspec`) và KHÔNG cho tham số tuỳ chỉnh `han_isolate_ms`/
`bo_nho_isolate_mb`: mở một khe cấu hình mới ở `tham_so` là mời người soạn tự
đặt số, đúng thứ dòng luật của lan này cấm.
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.workflow import he_kieu, nut
from platform_core.workflow.nut import Gia, NodeDefinition
from platform_core.workflow.nut_loi import dang_ky

#: Mã lỗi node công bố — ĐÚNG bốn mã `runner.js::MA` phát ra cho `op ==
#: "run_code"` (`provider_loi`/`dau_vao_sai`/`het_gio`/`loi_he_thong`), cộng
#: `vuot_tran_bao_gia` mà MỌI job connector có thể nhận từ
#: `cau_noi._nop_job_connector` trước khi job kịp nộp. Khai TỪ nguồn thật
#: (`connector_runner/src/runner.js::MA`), không đoán theo `nut.MA_LOI_APP`
#: (bảng đó là của node `app.*`, mang `ket_qua_mo_ho`/`bi_huy`/
#: `cong_cu_khong_con` — ba mã `core.code` không bao giờ phát ra: nó không có
#: `hau_kiem`, không phải node `irreversible`, và không bọc ToolSpec nào để
#: "gỡ mất").
MA_LOI_CODE = ("provider_loi", "dau_vao_sai", "het_gio", "loi_he_thong",
               "vuot_tran_bao_gia")

THAM_SO = {
    "type": "object",
    "properties": {
        "code": {
            "type": "string", "x-ltt-control": "code-js",
            "description": N_(
                "Module CJS: `module.exports.code = function(inputs) {...}`."
                " Chay trong isolated-vm — khong `require`, khong mang, "
                "khong doc/ghi tep, khong sinh tien trinh con."),
        },
        "inputs": {
            "type": "object", "x-ltt-control": "code-json",
            "description": N_(
                "Object truyen vao tham so `inputs` cua ham `code`. Gia tri "
                "thuong la tham chieu {{ }} toi dau ra cua node khac."),
        },
    },
    "required": ["code"],
    "additionalProperties": False,
}


CORE_CODE = NodeDefinition(
    type="core.code", type_version=1, kind="data", category="DATA",
    title=N_("Code"),
    description=N_("Chay mot doan JavaScript tuy y trong vo cach ly hai lop "
                   "(AppContainer + isolated-vm). Khong mang, khong tep, "
                   "khong tien trinh con."),
    icon="🧩",
    cong_vao=(
        ("inputs", he_kieu.Cong(type="any", required=False, nhan="inputs")),
    ),
    cong_ra=(
        ("output", he_kieu.Cong(type="any", required=True, nhan="output")),
    ),
    tham_so=THAM_SO,
    thi_hanh="job", job_type=nut.JOB_TYPE_CODE,
    side_effect="none", idempotency_key_fields=(),
    resource={"class": "cpu", "slots": 1},
    retry_mac_dinh={"max": 0, "backoff_s": 30},
    gia=Gia.co_dinh(1),
    credential=(), quyen=frozenset(),
    cho=("JOB",), ma_loi=MA_LOI_CODE,
    publish_duoc=True)

DINH_NGHIA = ((CORE_CODE, None),)

dang_ky(CORE_CODE)

__all__ = ["CORE_CODE", "DINH_NGHIA", "MA_LOI_CODE"]
