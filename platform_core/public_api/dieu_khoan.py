"""Điều khoản dịch vụ `/api/v1` — **dữ liệu, sinh từ hằng số thật**.

## Vì sao tệp này tồn tại

Đo 01/09 trên bản đang chạy: `https://lttstudios.com/terms/` có **21.335 ký tự
văn bản** và **không nhắc một chữ nào** tới `API`, `credit`, `hoàn tiền`,
`trách nhiệm`, `SLA`, `khoá` hay `thanh toán`. Đó là trang duy nhất mà chân
trang của `/register` trỏ tới.

⛔ Nghĩa là nền tảng đang **bán một dịch vụ tính tiền theo mức dùng, trả trước
   bằng credit** — và điều khoản khách được trỏ tới không mô tả dịch vụ đó.

Và biểu mẫu đăng ký **không ghi lại việc khách đã đồng ý điều khoản nào**: không
có ô tích, không có cột nào lưu. Luồng VPS thì có (clickwrap + `dong_y_luc`), nên
đây không phải "chưa ai nghĩ tới cơ chế" — chỉ là đường API chưa được nối vào nó.

## Hai luật của tệp này, chép từ tiền lệ đã trả giá

**1. Không con số nào được gõ tay.** `apps/vps/dieu_khoan.py` đã học điều này:

> *"Ở đây con số **không thể lệch**, vì chỉ có một chỗ."*

Nên giá lấy từ `gia_token.bang_gia()` — **chính hàm ra hoá đơn**. Đổi giá trong
`gia_token.py` là điều khoản đổi theo, cùng lúc, không cần ai nhớ.

**2. Điều khoản phải do CHÍNH APP phục vụ.** Cũng từ tiền lệ VPS, và đây là
phần đắt nhất:

> *"bản WordPress **chưa bao giờ được xuất bản** (`/vps-terms/` trả 404 suốt từ
> 25/08), trong khi clickwrap đã trỏ vào đó. Tức khách 'đồng ý' với một trang
> không tồn tại, đúng lúc họ sắp trả tiền."*

Một trang do app phục vụ không thể ở trạng thái đó — nó sống hay chết cùng phần
còn lại của app.

## 🔴 RANH GIỚI: cái gì ở đây là SỰ THẬT ĐO ĐƯỢC, cái gì CHƯA AI QUYẾT

Mọi mục trong `MUC_DA_DO` mô tả **hành vi đã đo trên production ngày 01/09**, và
mỗi mục ghi kèm phép đo. Chúng an toàn vì chúng chỉ nói hệ thống đang làm gì.

`CAN_CHU_SAN_PHAM_QUYET` là chuyện khác hẳn: **giới hạn trách nhiệm, SLA, hoàn
tiền phần credit chưa dùng, chấm dứt tài khoản** — đó là quyết định kinh doanh
và pháp lý. Chúng **không** có trong mã, nên không đo được, nên tệp này **không
bịa ra chúng**. Nó liệt kê chúng thành một danh sách ngắn để chủ sản phẩm điền,
thay vì để một bản nháp nghe-có-vẻ-đúng trôi lên trang bán hàng.

⛔ Đừng "hoàn thiện" tệp này bằng cách viết giúp mấy mục đó. Một điều khoản do
   máy đoán ra, đặt trước một ô tích mà khách bấm, là một lời hứa không ai từng
   đưa ra.
"""
from __future__ import annotations

from platform_core.i18n import N_

#: Phiên bản bản điều khoản. **Đổi nội dung ⇒ đổi nhãn**, không sửa nhãn cũ:
#: bản ghi đồng ý lưu nhãn này, và nếu nhãn được tái sử dụng thì câu hỏi "họ đã
#: đồng ý với cái gì" không còn trả lời được. Cùng luật với `PHIEN_BAN_GIA`.
PHIEN_BAN = "api-2026-09-01"

#: Một credit bằng bao nhiêu đồng. Trang `/gia-api` đã dùng đúng phép nhân này
#: (`credit * 100`); để ở đây một lần thay vì để hai nơi cùng nhân.
DONG_MOI_CREDIT = 100


def bang_gia() -> dict:
    """Bảng giá **của chính hàm ra hoá đơn**, không phải bản chép."""
    from platform_core.llm import gia_token

    return gia_token.bang_gia()


def _tu_ban_khai():
    """Duyệt bản khai của **mọi** app qua registry. Yield `(tool, alias, spec)`.

    🔴 BẢN ĐẦU CỦA TỆP NÀY `import apps.ltt_llm` — VÀ ĐÓ LÀ MỘT LỖI NẶNG.

       `platform_core` **không được** biết app nào tồn tại; registry là đường
       duy nhất. Hai chốt bắt được ngay (`test_147::test_platform_core_never_
       imports_apps`, `test_60::test_platform_never_imports_an_app`).

    ⛔ Và nó không chỉ là một chốt kêu: nền tảng biết tên một app cụ thể nghĩa
       là **gỡ app đó ra sẽ làm nền tảng vỡ**, chứ không phải chỉ mất một app.
       Kho này đã gỡ `socialbot`, `demo`, `kichban`, `mediatools` — đường ấy còn
       dùng nữa.

    ⭐ Cay hơn cả: `test_334::TestBanSaoConLai` viết đúng luật này bằng chữ —
       *"thứ ghép hai đầu lại phải là một **phép kiểm**, không phải một câu
       `import`"* — và tôi đã đọc nó trong cùng phiên, rồi viết `import`.

    ⇒ Đọc từ registry còn **đúng hơn về nội dung**: trang này là điều khoản của
      cả `/api/v1`, không riêng một app. Nay thêm một app là điều khoản tự có
      nó, không cần ai nhớ.
    """
    from platform_core.registry import discover

    for it in discover():
        for tool in it.manifest.tools:
            models = (getattr(tool, "api_contract", None) or {}).get("models") or {}
            for alias, spec in models.items():
                yield tool, alias, dict(spec or {})


def gioi_han_model() -> dict:
    """Giới hạn **công bố** của từng model, đọc từ bản khai của app.

    Chỉ lấy model có khai `context_window`: một model không nói giới hạn của nó
    thì điều khoản không được đoán hộ.
    """
    ra = {}
    for _tool, alias, spec in _tu_ban_khai():
        rb = spec.get("constraints") or {}
        if not rb.get("context_window"):
            continue
        ra[alias] = {"cong_bo": int(rb["context_window"]),
                     "tran_ra": int(rb.get("max_output_tokens") or 0)}
    return ra


def dong_thoi() -> dict:
    """Số lượt cùng lúc của từng tool có giới hạn, đọc từ bản khai.

    `admission_slots = 0` nghĩa là tool đó không khai giới hạn, nên không đưa
    vào điều khoản — nói một con số không ai cưỡng chế là nói sai.
    """
    ra = {}
    for tool, _alias, _spec in _tu_ban_khai():
        suat = int(getattr(tool, "admission_slots", 0) or 0)
        if suat > 0:
            ra[tool.name] = suat
    return ra


#: Những điều **đã đo trên production**, mỗi điều kèm phép đo sinh ra nó.
#: Đây là phần an toàn của điều khoản: nó chỉ mô tả hệ thống đang làm gì.
MUC_DA_DO = (
    {
        "khoa": "giu_va_quyet_toan",
        "tieu_de": N_("Giữ chỗ trước, tính tiền theo mức dùng thật"),
        "noi_dung": N_(
            "Mỗi lời gọi giữ trước một khoản credit theo ước tính cao, rồi quyết "
            "toán lại theo số token thật sự đã dùng. Phần giữ dư được hoàn ngay "
            "trong cùng lượt gọi."),
        # Do song 01/09: giu tran uoc cao, thu theo token that sinh ra.
        "do_bang": "test_272 test_259 P08/L3",
    },
    {
        "khoa": "khong_do_duoc",
        "tieu_de": N_("Không đo được mức dùng thì không thu tiền"),
        "noi_dung": N_(
            "Nếu hệ thống không đọc được số token của một lượt gọi, toàn bộ khoản "
            "giữ chỗ được hoàn và lượt đó tính 0 credit. Hệ thống không ước lượng "
            "để tính tiền."),
        "do_bang": "gia_token.KhongDoDuocError test_252 INV-009",
    },
    {
        "khoa": "ban_thi_khong_thu",
        "tieu_de": N_("Bận thì không thu tiền"),
        "noi_dung": N_(
            "Khi tài nguyên đang bận, lời gọi bị từ chối với mã 429 kèm header "
            "Retry-After, và không bị tính credit."),
        # Do song 01/09: 3 luot dong thoi -> 2x429, so du giam dung 1.
        "do_bang": "INV-003 P08/L3",
    },
    {
        "khoa": "ngat_ket_noi",
        "tieu_de": N_("Ngắt kết nối giữa chừng vẫn tính phần đã sinh"),
        "noi_dung": N_(
            "Nếu khách đóng kết nối khi câu trả lời đang được sinh, phần đã sinh "
            "ra vẫn được tính. Phần chưa sinh thì không."),
        # Do song 01/09: doc 15.872 byte roi dong socket -> thu 1 credit.
        "do_bang": "P08/L3 B17",
    },
    {
        "khoa": "goi_lai",
        "tieu_de": N_("Gọi lại cùng một khoá idempotency không bị tính tiền hai lần"),
        "noi_dung": N_(
            "Gửi lại một yêu cầu với cùng Idempotency-Key trả về đúng kết quả cũ "
            "và không tạo lượt tính tiền mới."),
        # Do song qua Cloudflare: cung job id, tru 0 credit.
        "do_bang": "B14 B15",
    },
    {
        "khoa": "lam_tron",
        "tieu_de": N_("Mỗi lượt gọi làm tròn lên credit nguyên"),
        "noi_dung": N_(
            "Một lượt gọi rất nhỏ vẫn tính tối thiểu 1 credit. Với lượt gọi nhỏ, "
            "số tiền thực trả cao hơn giá niêm yết trên một triệu token."),
        "do_bang": "gia_token.bang_gia toi_thieu_moi_luot_credit",
    },
    {
        "khoa": "dong_thoi",
        "tieu_de": N_("Mỗi tài khoản được phục vụ một lượt tại một thời điểm"),
        "noi_dung": N_(
            "Model chạy trên phần cứng của chính LTT Studios và phục vụ một lượt "
            "tại một thời điểm. Lượt vượt quá nhận 429 kèm Retry-After."),
        # Do song: 429 tra ve trong duoi 1,4 giay -- khong xep hang an.
        "do_bang": "INV-014 P08/L3",
    },
    {
        "khoa": "tran_ngu_canh",
        "tieu_de": N_("Trần ngữ cảnh khác nhau giữa các model"),
        "noi_dung": N_(
            "Mỗi model có trần đầu vào riêng và trần này được công bố ở "
            "/api/v1/models. Yêu cầu vượt trần bị từ chối bằng mã 413 kèm con số "
            "trần thật, không bị cắt bớt âm thầm."),
        # Do song 01/09: 413 kem limit_value dung cua tung model.
        "do_bang": "P08/F-02 P08/L3",
    },
)

#: 🔴 CHƯA AI QUYẾT — và tệp này **cố ý để trống**.
#:
#: Mỗi mục dưới đây là một quyết định kinh doanh/pháp lý, không phải một tính
#: chất của mã. Không đo được thì không viết ra. Danh sách này tồn tại để chủ
#: sản phẩm điền một lần, chứ không để một bản nháp nghe-hợp-lý trôi lên trang
#: bán hàng và trở thành lời hứa.
CAN_CHU_SAN_PHAM_QUYET = (
    {
        "khoa": "credit_het_han",
        "cau_hoi": N_("Credit đã nạp có hạn sử dụng không?"),
        "hien_trang": N_(
            "Mã nguồn không cài đặt hạn dùng nào cho credit. Nhưng 'không có mã' "
            "không phải một lời hứa — cần một câu trả lời rõ ràng."),
    },
    {
        "khoa": "hoan_tien_chua_dung",
        "cau_hoi": N_("Credit chưa dùng có hoàn lại được tiền không?"),
        "hien_trang": N_(
            "Sổ credit là append-only và có đường hoàn, nhưng không có quy trình "
            "hoàn tiền mặt nào trong mã."),
    },
    {
        "khoa": "sla",
        "cau_hoi": N_("Có cam kết mức độ sẵn sàng (SLA) không, và bồi thường ra sao?"),
        "hien_trang": N_(
            "Không có SLA nào trong mã nguồn. Model chạy trên phần cứng dùng "
            "chung, và đã có lần ngừng dịch vụ nhiều giờ."),
    },
    {
        "khoa": "gioi_han_trach_nhiem",
        "cau_hoi": N_("Giới hạn trách nhiệm tối đa là bao nhiêu?"),
        "hien_trang": N_("Không có điều khoản nào về việc này ở bất kỳ đâu."),
    },
    {
        "khoa": "cham_dut",
        "cau_hoi": N_("Khi nào LTT Studios được dừng tài khoản, và credit còn lại xử lý thế nào?"),
        "hien_trang": N_(
            "Tài khoản có cờ vô hiệu hoá và bút toán credit không bị xoá, nhưng "
            "không có điều khoản mô tả khi nào việc đó xảy ra."),
    },
    {
        "khoa": "noi_dung_cam",
        "cau_hoi": N_("Nội dung nào bị cấm gửi qua API, và hậu quả là gì?"),
        "hien_trang": N_("Không có chính sách sử dụng chấp nhận được nào được công bố."),
    },
)


def du_lieu_luu_gi() -> list:
    """Dữ liệu khách bị giữ lại những gì, **đọc từ đăng ký thật**.

    ⛔ KHÔNG chép danh sách bảng vào đây. `governance.py` đã là nguồn chân lý và
       nó tự nhắc: *"a second copy of a legal promise is a second promise, and
       the two will differ"*. Hàm này chỉ **đọc** nó.
    """
    from platform_core.public_api import governance

    ra = []
    for s in getattr(governance, "STORES", ()) or ():
        ra.append({"bang": s.table,
                   "lop": getattr(s, "klass", ""),
                   "giu_ngay": s.retention_days})
    return ra


class ChuaDuDeRangBuoc(RuntimeError):
    """Có người định lấy chữ ký của khách vào một bản điều khoản chưa xong."""


def san_sang() -> bool:
    """Điều khoản đã đủ để **ràng buộc** khách chưa.

    ⭐ Trả `False` chừng nào còn mục trong `CAN_CHU_SAN_PHAM_QUYET`. Đây không
       phải một cái cờ trang trí: nó là thứ giữ cho ô tích "tôi đồng ý" không
       xuất hiện trước khi có gì thật để đồng ý.
    """
    return not CAN_CHU_SAN_PHAM_QUYET


def can_dieu_khoan_san_sang() -> None:
    """Gọi ở **mọi** chỗ sắp ghi nhận một chữ ký của khách. Ném nếu chưa đủ.

    🔴 VÌ SAO LÀ MỘT HÀM NÉM, KHÔNG PHẢI MỘT CỜ ĐỂ ĐỌC.

       `san_sang()` một mình không có răng: nó chỉ trả về một giá trị, và một
       giá trị không ai đọc thì không chặn được gì. Phép kiểm cho nó cũng dễ
       thành tautology — bản đầu của `test_390` đúng là như vậy, và chỉ lộ ra
       khi bị đột biến.

    ⭐ Hàm này thì khác: nó **ném**, nên chỗ nào quên gọi sẽ hiện ra ở đường thi
       hành chứ không hiện ra trong một dòng log. Và một phép kiểm cho nó có thể
       đỏ thật — chỉ cần bỏ danh sách chưa-quyết đi là nó thôi ném.
    """
    if not san_sang():
        con = ", ".join(m["khoa"] for m in CAN_CHU_SAN_PHAM_QUYET)
        raise ChuaDuDeRangBuoc(
            "Dieu khoan API chua du de rang buoc khach: con "
            f"{len(CAN_CHU_SAN_PHAM_QUYET)} cau hoi chua ai tra loi ({con}). "
            "Xem CAN_CHU_SAN_PHAM_QUYET trong platform_core/public_api/"
            "dieu_khoan.py — moi muc co san cau hoi va hien trang.")
