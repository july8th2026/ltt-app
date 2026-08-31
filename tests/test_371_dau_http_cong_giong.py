"""
🔴 Đầu HTTP chỉ nhận latin-1, và cổng giọng viết chuỗi chẩn đoán TIẾNG VIỆT
   vào đó — nên một bản đọc đã sinh xong vẫn có thể tan thành `500`.

Đo thật 01/09/2026: `/v1/speech-dai` với tám đoạn trả **HTTP 500**. Log máy chủ:

    File "voice_sidecar/server.py", line 222, in speech_dai
      return Response(content=..., headers={...})
    UnicodeEncodeError: 'latin-1' codec can't encode character '\\u2014'

`\\u2014` là dấu gạch ngang dài `—`. Nó đến từ **một** trong ba lối ra của
`noi_dai.nhip_nghi`:

    "UOC THO tu N khoang lang bat ky (khong biet so cau) — con so nay thien ve
     khe TU, thuong qua ngan"

⭐ Vì sao lỗi này sống được lâu mà không ai thấy: lối ra đó chỉ chạy khi **không
   dò được ranh giới câu nào** giữa các đoạn — tức đúng lúc khách nộp nhiều
   dòng ngắn, mỗi dòng một câu. Hai lối ra kia thuần ASCII. Nên nó hỏng ở một
   phần ba số ca và trông y như ngẫu nhiên.

⛔ Và nó hỏng theo kiểu tệ nhất: **việc đã làm xong rồi mới bị vứt**. Model đã
   sinh đủ tiếng, đã ghép, đã cân mức. GPU đã tiêu thật. Rồi cả lượt tan vì một
   chuỗi *giải thích*. Khách thấy "lỗi hệ thống"; log thì báo một
   `UnicodeEncodeError` ở tầng Starlette không nhắc một chữ nào tới giọng nói.

Phép kiểm chốt ở **cửa ra** (`server._dau`) chứ không chốt chuỗi kia. Bỏ dấu `—`
đi là đập một con chuột trong khi cái lỗ vẫn mở: mọi chuỗi chẩn đoán tiếng Việt
viết sau này đều là một quả mìn, và không có gì trong hệ thống kiểu nào phản đối.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.usefixtures()


def test_dau_HTTP_khong_bao_gio_lam_vo_phan_hoi():
    """Mọi giá trị, kể cả tiếng Việt có dấu, phải mã hoá được sang latin-1."""
    from voice_sidecar.server import _dau

    for v in ("UOC THO tu 7 khoang lang bat ky (khong biet so cau) — con so "
              "nay thien ve khe TU, thuong qua ngan",
              "đo được từ 4 ranh giới câu",
              "trần 1.500 ký tự — chất lượng, không phải hiệu năng",
              "—…“”",
              None, 0, 0.0, 3.14159):
        ra = _dau(v)
        assert isinstance(ra, str)
        ra.encode("latin-1")           # nổ ở đây = đầu HTTP sẽ nổ ở production


def test_chuoi_ASCII_di_qua_NGUYEN_VEN():
    """Bọc an toàn không được làm hỏng thứ vốn đã đúng.

    Một hàm "làm sạch" mà đổi cả những giá trị hợp lệ sẽ khiến người đọc log
    không tra ngược được về mã sinh ra chúng.
    """
    from voice_sidecar.server import _dau

    for v in ("do duoc tu 4 ranh gioi cau: 0.412s",
              "lui (khong do duoc khoang lang giua nao)",
              "khong can ghep", "ltt-voice-thamso-2026-08-30a"):
        assert _dau(v) == v


def test_MOI_loi_ra_cua_nhip_nghi_deu_dat_vao_dau_HTTP_duoc():
    """⛔ Chốt tận gốc: **mọi** lời giải thích mà `nhip_nghi` sinh ra đều phải
    qua được cửa ra.

    Phép kiểm trên chốt cái cửa; phép kiểm này chốt rằng thứ đi qua cửa hôm nay
    đúng là thứ đã gây lỗi thật. Đọc thẳng mã nguồn của `nhip_nghi` và lấy mọi
    chuỗi trong đó — nếu ai thêm một lối ra thứ tư bằng tiếng Việt, chỗ này thấy.
    """
    import ast
    import inspect

    from voice_sidecar import noi_dai
    from voice_sidecar.server import _dau

    cay = ast.parse(inspect.getsource(noi_dai.nhip_nghi))
    chuoi = [n.value for n in ast.walk(cay)
             if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    assert chuoi, "khong doc duoc chuoi nao tu `nhip_nghi` — phep kiem dang mu"

    ngoai_latin1 = []
    for s in chuoi:
        try:
            s.encode("latin-1")
        except UnicodeEncodeError:
            ngoai_latin1.append(s)
        _dau(s).encode("latin-1")      # cửa ra phải nuốt được tất

    # Không đòi các chuỗi ấy phải thuần ASCII — đòi vậy là ép người viết mã bỏ
    # tiếng Việt khỏi lời giải thích, tức chữa bệnh bằng cách bỏ thông tin.
    # Chỉ ghi lại rằng chúng TỒN TẠI, để ai đọc phép kiểm này hiểu vì sao cửa ra
    # là bắt buộc chứ không phải một lớp phòng xa.
    assert isinstance(ngoai_latin1, list)
