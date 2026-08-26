"""Nội dung Điều khoản LTT VPS — **dữ liệu, sinh từ hằng số thật**.

## Vì sao nó là một mô-đun Python chứ không phải một trang HTML

Trước 26/08 văn bản này là hai tệp HTML tĩnh ở `docs/lttstudios-website/`, và
mọi con số trong đó **gõ tay**. Một phép kiểm (`test_298`) đối chiếu từng con số
với hằng số thật, nên chúng không trôi được — nhưng cái giá là: đổi giá một gói
thì phải sửa **ba** chỗ (mã, bản VI, bản EN), và phép kiểm chỉ nói cho ta biết
khi ta đã quên.

Ở đây con số **không thể lệch**, vì chỉ có một chỗ:

    from apps.vps.cost import PLANS, CHU_KY_NGAY, ...

Đổi giá trong `cost.py` là điều khoản đổi theo, cùng lúc, không cần ai nhớ.

## Vì sao KHÔNG phải là một bản sao thứ hai của lời hứa pháp lý

`platform_core/public_api/governance.py` có một luật đáng giữ:

> *a second copy of a legal promise is a second promise, and the two will differ*

Luật đó **không** nói văn bản pháp lý phải nằm ở site marketing. Nó nói không
được có **hai** bản. Chủ sản phẩm chốt 26/08: điều khoản là trang con của `/vps`.
Nên bản WordPress đã bị gỡ trong cùng đợt — vẫn đúng một bản, chỉ đổi chỗ ở.

⭐ Và chỗ ở mới tốt hơn theo một cách đo được: bản WordPress **chưa bao giờ được
   xuất bản** (`https://lttstudios.com/vps-terms/` trả 404 suốt từ 25/08), trong
   khi clickwrap đã trỏ vào đó. Tức khách "đồng ý" với một trang không tồn tại,
   đúng lúc họ sắp trả tiền. Một trang do chính app phục vụ thì không thể ở
   trạng thái đó — nó sống hay chết cùng phần còn lại của app.

## Hai quy ước khi sửa tệp này

1. **Mọi chuỗi phải bọc `_()` NGAY LÚC GỌI**, không phải ở cấp mô-đun. Hằng số
   cấp mô-đun bị dịch đúng một lần, bằng ngôn ngữ của request đầu tiên chạm tới
   tiến trình — và sau đó mọi khách đều nhận ngôn ngữ đó. Xem `NOI_DUNG()` là
   một *hàm*, không phải một *danh sách*.

2. **`<strong>` được phép nằm trong chuỗi**, và template render bằng `|safe`.
   An toàn vì nguồn chuỗi là tệp này + catalog dịch của chính ta, không phải dữ
   liệu người dùng. Đổi lại ta giữ được nhấn mạnh ở đúng chỗ quan trọng — mục 4
   (xoá vĩnh viễn) và mục 2 (giấy phép Windows) mất nhấn mạnh là mất tác dụng.
"""
from __future__ import annotations

from typing import Any

from apps.vps.cost import (CHU_KY_NGAY, DIA_THEM_MOI_LO_GB,
                           GIA_MOI_LO_DIA_VND, PLANS, credit_thang)
from apps.vps.services.billing import AN_HAN_TRUOC_KHI_XOA_NGAY
from apps.vps.services.console import HAN_VE_GIAY
from apps.vps.services.sao_luu import GIU, MOI_NGAY
from platform_core.billing_math import VND_PER_CREDIT
from platform_core.i18n import _ as _t

#: Ngày điều khoản có hiệu lực. Đổi nội dung thì đổi cả ngày này — một văn bản
#: pháp lý không ghi ngày là một văn bản không ai biết mình đã đồng ý với bản nào.
HIEU_LUC = "2026-08-26"

#: Báo trước bao nhiêu ngày khi đổi điều khoản theo hướng bất lợi cho khách.
BAO_TRUOC_NGAY = 30

#: Hai con số MẠNG mà điều khoản hứa. Chúng được **thi hành trong
#: `tools/vps_gateway/cai-dat-router.sh`**, không phải trong Python.
#:
#: 🔴 VÌ SAO CHÉP SANG ĐÂY THAY VÌ ĐỌC THẲNG TỆP ĐÓ
#:
#:    Bản đầu của tệp này neo tới kịch bản bằng `Path(__file__).parents[2]`, và
#:    `test_148` bắt ngay — đúng như `CLAUDE.md` đã dặn: đếm cấp thư mục gãy
#:    ngay khi tệp đổi chỗ, và nó gãy **lặng lẽ**.
#:
#:    Sâu hơn thế: một app **không được với ra ngoài thư mục của chính nó**.
#:    Kịch bản router là hạ tầng, không phải tài sản của app; hôm nay nó ở
#:    `tools/`, mai nó có thể ở một kho khác.
#:
#: ⭐ Nên app giữ con số của app, và **một phép kiểm** giữ hai bên khớp nhau:
#:    `test_298::test_toc_do_khi_bi_ham_khop_KICH_BAN_ROUTER`. Test được phép
#:    đọc cả kho; mã chạy thì không. Sửa router mà quên chỗ này là gate đỏ.
TOC_KHI_HAM_MB = 1
CONG_RA_BI_CHAN: tuple[str, ...] = ("25", "465", "587")


def _tien(vnd: int) -> str:
    """`149000` → `149.000đ`. Một chỗ duy nhất định dạng tiền trong tệp này."""
    return f"{vnd:,}".replace(",", ".") + "đ"


def _so(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _p(text: str) -> tuple[str, Any]:
    return ("p", text)


def _ul(items: list[str]) -> tuple[str, Any]:
    return ("ul", items)


def _ol(items: list[str]) -> tuple[str, Any]:
    return ("ol", items)


def _bang_gia() -> list[str]:
    """Một dòng cho mỗi gói, dựng từ `PLANS`. Thêm gói = tự có dòng."""
    dong = []
    for p in PLANS:
        dong.append(
            _t("%(ten)s — %(vcpu)s vCPU · %(ram)s GB RAM · %(dia)s GB đĩa · "
               "%(bt)s GB băng thông — <strong>%(gia)s</strong> "
               "(%(credit)s credit)")
            % {"ten": _t(p.ten), "vcpu": p.vcpu, "ram": p.ram_mb // 1024,
               "dia": p.disk_gb, "bt": _so(p.bang_thong_gb),
               "gia": _tien(p.gia_thang_vnd), "credit": _so(credit_thang(p.id))})
    dong.append(
        _t("Đĩa thêm: mỗi <strong>%(lo)s GB</strong> — %(gia)s/chu kỳ")
        % {"lo": DIA_THEM_MOI_LO_GB, "gia": _tien(GIA_MOI_LO_DIA_VND)})
    return dong


def NOI_DUNG() -> list[dict]:
    """Toàn bộ điều khoản, đã dịch theo ngôn ngữ của request hiện tại.

    Là **hàm** chứ không phải hằng số cấp mô-đun: gettext tra theo ngôn ngữ đang
    hoạt động, và một hằng số cấp mô-đun sẽ đóng băng ngôn ngữ của request đầu
    tiên chạm tới tiến trình cho mọi khách sau đó.
    """
    return [
        {"so": "1", "tieu_de": _t("Máy được giao như thế nào"), "khoi": [
            _p(_t("Máy giao cho bạn là một <strong>máy trống đã gắn sẵn đĩa cài "
                  "Windows</strong>. Bạn tự chạy trình cài đặt qua console trong "
                  "trình duyệt và <strong>tự đặt tài khoản và mật khẩu của chính "
                  "mình</strong>.")),
            _ul([
                _t("Chúng tôi <strong>không biết mật khẩu của bạn</strong> và "
                   "<strong>không đặt lại được</strong> nó. Không giữ thì không "
                   "làm lộ được."),
                _t("Mất mật khẩu đồng nghĩa với phải cài lại máy, tức "
                   "<strong>mất toàn bộ dữ liệu</strong> trên đó."),
                _t("Bạn tự chịu trách nhiệm về mọi thứ chạy bên trong máy: bản "
                   "vá, tường lửa, phần mềm, và ai được vào."),
            ]),
        ]},
        {"so": "2", "tieu_de": _t("Giấy phép Windows — đọc kỹ mục này"), "khoi": [
            _p(_t("<strong>Giá dịch vụ KHÔNG bao gồm giấy phép Windows.</strong> "
                  "Chúng tôi cung cấp <em>đĩa cài đặt</em>, không cung cấp "
                  "<em>giấy phép</em>.")),
            _ul([
                _t("Đĩa cài Windows Server 2016 và Windows Server 2022 là "
                   "<strong>bản Evaluation của Microsoft</strong> — bản dùng "
                   "thử, thời hạn 180 ngày."),
                _t("Windows 10 LTSC cần giấy phép khối lượng riêng."),
                _t("Khi bạn chạy trình cài đặt, <strong>bạn</strong> là người "
                   "chấp nhận thoả thuận sử dụng của Microsoft, và "
                   "<strong>bạn</strong> chịu trách nhiệm về việc sử dụng đúng "
                   "giấy phép cho mục đích của mình."),
            ]),
            _p(_t("Nếu bạn cần Windows có giấy phép cho mục đích thương mại, hãy "
                  "tự mua giấy phép phù hợp hoặc dùng khoá của chính bạn. Chúng "
                  "tôi không bán lại giấy phép Microsoft.")),
        ]},
        {"so": "3", "tieu_de": _t("Thanh toán và chu kỳ"), "khoi": [
            _ul([
                _t("Chu kỳ là <strong>%(n)s ngày</strong>, <strong>trả "
                   "trước</strong> bằng credit.") % {"n": CHU_KY_NGAY},
                _t("<strong>1 credit = %(n)s đồng.</strong>") % {"n": VND_PER_CREDIT},
            ]),
            _p(_t("Giá hiện hành mỗi chu kỳ:")),
            _ul(_bang_gia()),
            _ul([
                _t("Đến kỳ, hệ thống tự trừ credit cho chu kỳ tiếp theo. Bạn "
                   "không phải thao tác gì."),
                _t("Sao kê từng lần thu nằm trong trang máy của bạn."),
            ]),
        ]},
        {"so": "4", "tieu_de": _t("Hết hạn, tạm dừng, và xoá"), "khoi": [
            _p(_t("Đây là mục quan trọng nhất của trang này. Chúng tôi viết nó "
                  "thẳng vì hậu quả không hoàn tác được.")),
            _ol([
                _t("Đến kỳ mà số dư credit <strong>không đủ</strong>: máy bị "
                   "<strong>tạm dừng ngay</strong> — máy tắt, nhưng <strong>dữ "
                   "liệu còn nguyên</strong>."),
                _t("Bạn có <strong>%(n)s ngày</strong> kể từ lúc tạm dừng để nạp "
                   "credit và dùng tiếp.") % {"n": AN_HAN_TRUOC_KHI_XOA_NGAY},
                _t("Quá %(n)s ngày: máy bị <strong>xoá vĩnh viễn</strong> — đĩa "
                   "và mọi ảnh chụp bị huỷ. <strong>Chúng tôi không khôi phục "
                   "được</strong>, kể cả khi bạn trả tiền sau đó.")
                % {"n": AN_HAN_TRUOC_KHI_XOA_NGAY},
            ]),
            _p(_t("Địa chỉ IP riêng được trả lại kho khi máy bị xoá. Máy mới của "
                  "bạn sẽ nhận một địa chỉ khác.")),
        ]},
        {"so": "5", "tieu_de": _t("Tài nguyên và hạn mức"), "khoi": [
            _ul([
                _t("<strong>RAM là tài nguyên cấp riêng.</strong> Bạn mua bao "
                   "nhiêu thì giữ chỗ thật bấy nhiêu."),
                _t("<strong>Dung lượng đĩa là hạn mức trên kho lưu trữ dùng "
                   "chung</strong>, không phải một ổ cứng cấp riêng. Bạn dùng "
                   "tới đâu chiếm tới đó."),
                _t("<strong>CPU là tài nguyên chia sẻ.</strong> Máy của bạn có "
                   "thể chậm hơn khi các máy khác trên cùng máy chủ đang bận."),
                _t("<strong>Băng thông có hạn mức theo gói.</strong> Vượt hạn "
                   "mức thì tốc độ bị giảm còn <strong>%(toc)s MB/giây</strong> "
                   "cho tới hết chu kỳ. Chúng tôi <strong>không tính thêm "
                   "tiền</strong> và không cắt mạng của bạn.") % {"toc": TOC_KHI_HAM_MB},
            ]),
        ]},
        {"so": "6", "tieu_de": _t("Ảnh chụp — không phải bản sao lưu"), "khoi": [
            _p(_t("Chúng tôi chụp ảnh máy của bạn <strong>mỗi %(nhip)s "
                  "ngày</strong> và giữ <strong>%(giu)s bản</strong>. Bạn khôi "
                  "phục về ảnh chụp gần nhất bằng một nút trong trang máy.")
               % {"nhip": MOI_NGAY, "giu": GIU}),
            _p(_t("Nhưng hãy hiểu đúng thứ bạn nhận được:")),
            _ul([
                _t("Ảnh chụp nằm <strong>trên cùng kho lưu trữ</strong> với máy "
                   "của bạn. Kho hỏng thì mất cả hai. Nó <strong>không thay thế "
                   "bản sao lưu của riêng bạn</strong>."),
                _t("Ảnh chụp được lấy khi máy đang chạy, giống như rút điện rồi "
                   "bật lại. Nó giữ những gì <strong>đã ghi xuống đĩa</strong>, "
                   "không phải mọi thứ tại đúng thời điểm chụp. Dữ liệu vừa ghi "
                   "trong vài giây trước đó có thể không có trong ảnh."),
                _t("Khôi phục làm <strong>mất mọi thay đổi</strong> sau thời "
                   "điểm chụp, và không hoàn tác được."),
            ]),
            _p(_t("Dữ liệu quan trọng, bạn nên tự sao lưu ra ngoài.")),
        ]},
        {"so": "7", "tieu_de": _t("Sử dụng chấp nhận được"), "khoi": [
            _p(_t("Những việc sau bị cấm, và vi phạm dẫn tới <strong>tạm dừng "
                  "ngay lập tức không báo trước</strong>:")),
            _ul([
                _t("Gửi thư rác, hoặc tiếp tay cho việc gửi thư rác dưới bất kỳ "
                   "hình thức nào."),
                _t("Quét cổng, dò mật khẩu, tấn công từ chối dịch vụ, hoặc bất "
                   "kỳ hành vi tấn công nào nhắm vào hệ thống của người khác."),
                _t("Lưu trữ hoặc phát tán nội dung vi phạm pháp luật Việt Nam, "
                   "hoặc vi phạm quyền sở hữu trí tuệ của người khác."),
                _t("Đào tiền mã hoá. CPU là tài nguyên chia sẻ, và một máy chạy "
                   "hết công suất liên tục làm chậm máy của mọi khách khác."),
                _t("Bán lại hoặc chia sẻ lại dịch vụ cho bên thứ ba."),
            ]),
            _p(_t("<strong>Các cổng ra %(cong)s bị chặn ở tầng mạng</strong> cho "
                  "mọi máy. Đây là biện pháp kỹ thuật, không phải chính sách có "
                  "thể xin miễn: một máy gửi thư rác làm địa chỉ của toàn hệ "
                  "thống vào danh sách đen, và khi đó mọi khách cùng chịu. Nếu "
                  "bạn cần gửi thư từ ứng dụng, hãy dùng API của một dịch vụ gửi "
                  "thư qua HTTPS.")
               % {"cong": ", ".join(CONG_RA_BI_CHAN[:-1]) + _t(" và ")
                     + CONG_RA_BI_CHAN[-1]}),
        ]},
        {"so": "8", "tieu_de": _t("Mức độ sẵn sàng"), "khoi": [
            _p(_t("Dịch vụ chạy theo chế độ <strong>best effort</strong>. Chúng "
                  "tôi <strong>không cam kết thời gian hoạt động</strong> và "
                  "không có SLA.")),
            _ul([
                _t("Máy chủ có thể khởi động lại để bảo trì hoặc cập nhật."),
                _t("Đường vào Internet đi qua một máy chủ trung gian; máy đó gặp "
                   "sự cố thì bạn tạm thời không vào được máy của mình, dù máy "
                   "vẫn chạy."),
            ]),
            _p(_t("Nếu công việc của bạn không chịu được gián đoạn, dịch vụ này "
                  "chưa phù hợp. Chúng tôi nói trước còn hơn để bạn phát hiện "
                  "vào lúc không mong muốn.")),
        ]},
        {"so": "9", "tieu_de": _t("Hoàn tiền"), "khoi": [
            _p(_t("Chu kỳ <strong>đã bắt đầu thì không hoàn</strong>: tài nguyên "
                  "(RAM, đĩa, địa chỉ IP) đã được giữ chỗ thật cho bạn ngay từ "
                  "đầu chu kỳ, và không dùng lại được cho người khác.")),
            _p(_t("Bạn có thể xoá máy bất cứ lúc nào; việc xoá dừng các chu kỳ "
                  "<em>tiếp theo</em>, không hoàn lại chu kỳ đang dùng.")),
            _p(_t("Nếu dịch vụ không sử dụng được vì lỗi từ phía chúng tôi, hãy "
                  "liên hệ <a href=\"mailto:support@lttstudios.com\">"
                  "support@lttstudios.com</a>; chúng tôi xem xét từng trường hợp.")),
        ]},
        {"so": "10", "tieu_de": _t("Dữ liệu của bạn"), "khoi": [
            _ul([
                _t("Chúng tôi <strong>không truy cập</strong> vào bên trong máy "
                   "của bạn. Chúng tôi không có mật khẩu của bạn."),
                _t("Console trong trình duyệt hiển thị màn hình máy bạn. Nó chỉ "
                   "mở được từ tài khoản của chính bạn, bằng vé dùng một lần, "
                   "hết hạn sau %(n)s giây.") % {"n": HAN_VE_GIAY},
                _t("Xoá máy là xoá đĩa và mọi ảnh chụp. Không khôi phục được."),
                _t("Chúng tôi giữ nhật ký vòng đời máy (tạo, bật, tắt, tạm dừng, "
                   "xoá) và bút toán thanh toán, để trả lời được các câu hỏi về "
                   "vận hành và đối soát."),
            ]),
        ]},
        {"so": "11", "tieu_de": _t("Thay đổi điều khoản"), "khoi": [
            _p(_t("Chúng tôi có thể sửa trang này. Với thay đổi <strong>bất lợi "
                  "cho bạn</strong> (tăng giá, giảm hạn mức, thêm hạn chế), "
                  "chúng tôi báo trước <strong>%(n)s ngày</strong> qua email. "
                  "Bạn không đồng ý thì có quyền xoá máy trước khi thay đổi có "
                  "hiệu lực.") % {"n": BAO_TRUOC_NGAY}),
        ]},
        {"so": "12", "tieu_de": _t("Luật áp dụng"), "khoi": [
            _p(_t("Điều khoản này áp dụng pháp luật Việt Nam. Tranh chấp không "
                  "giải quyết được bằng thương lượng sẽ đưa ra toà án có thẩm "
                  "quyền tại Việt Nam.")),
        ]},
        {"so": "", "tieu_de": _t("Liên hệ"), "khoi": [
            _p(_t("<a href=\"mailto:support@lttstudios.com\">"
                  "support@lttstudios.com</a>")),
        ]},
    ]


def mo_dau() -> list[tuple[str, Any]]:
    """Hai đoạn mở đầu — đứng ngoài danh sách mục vì chúng không có số."""
    return [
        _p(_t("Trang này là điều khoản <strong>riêng cho dịch vụ LTT "
              "VPS</strong>. Điều khoản dịch vụ chung của LTT Studios vẫn áp "
              "dụng; chỗ nào hai bên khác nhau thì trang này thắng, vì nó nói "
              "về chính dịch vụ bạn đang dùng.")),
        _p(_t("Mọi con số trong trang này là con số <strong>hệ thống thật sự thi "
              "hành</strong>, không phải mục tiêu — chúng được dựng thẳng từ "
              "chính hằng số mà phần mềm dùng, nên chúng không thể lệch.")),
    ]
