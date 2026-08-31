"""
routes/ — bề mặt web của LTT VOICE, tách theo màn (`AGENTS.md` mục 8).

Nền tảng chỉ cần biến `router`. Import từng mảnh ở đây để handler của chúng
được đăng ký vào router **trước khi** nền tảng gắn vào FastAPI.

    _chung.py       router + helper dùng chung (`_uid`, `_db`, `_het_phien`)
    _p_tao.py       Tạo tiếng nói: dựng trang · xem trước cách đọc · nộp · kết quả
    _p_giong.py     Giọng: lưới giọng · ghi danh · tắt
    _p_du_an.py     Dự án: danh sách · khối · sinh · xuất
    _p_lich_su.py   Lịch sử: lọc và liệt kê
    _p_api.py       API: mã giọng để dán vào mã nguồn + trạng thái cửa thật
    _p_audio.py     Phục vụ tệp tiếng — cửa duy nhất đọc kho của khách

⭐ TỪ P8 KHÔNG CÒN MẢNH GIỮ CHỖ. `_p_chua_xay.py` đã gỡ cùng màn cuối được xây.
   Nó từng phải nằm **sau** mọi mảnh khác vì FastAPI khớp theo thứ tự đăng ký,
   nên một placeholder đăng ký trước sẽ **nuốt** đường thật — và triệu chứng là
   một màn hoàn chỉnh hiện ra trang "đang xây", không lỗi nào báo. Cái bẫy đó đi
   cùng tệp; ghi lại ở đây phòng khi ai dựng lại cơ chế ấy.
"""
from apps.ltt_voice.routes._chung import router
from apps.ltt_voice.routes import (  # noqa: F401  (import để đăng ký route)
    _p_tao, _p_giong, _p_du_an, _p_lich_su, _p_api, _p_audio)

__all__ = ["router"]
