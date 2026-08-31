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


def test_ho_so_ghep_NOI_RA_moc_tung_doan():
    """🔴 Không có mốc thì người đo lại phải CHIA ĐỀU, và chia đều sai luỹ tiến.

    `ghep()` biết chính xác từng đoạn nằm ở đâu trong bản đã ghép — nó vừa xếp
    chúng. Trước 01/09/2026 nó không nói ra, nên bất cứ ai muốn đo lại **từng
    đoạn** đều phải chia đều mà đoán.

    ⛔ Cái sai đó không hiền. Mỗi mối nối chèn thêm `nghi` giây, nên phép chia
       đều lệch **luỹ tiến theo chỉ số đoạn** — tức nó tự sinh ra một **xu hướng
       đơn điệu**.

    ⭐ Và nó đã sinh ra một cái thật. Lượt đo trôi tông đầu tiên (01/09) đọc ra
       *"−5,05 Hz mỗi đoạn, có hướng, vượt sàn nhiễu"* — một kết luận nghe rất
       chắc về đúng hiện tượng đang đi tìm, và hoàn toàn có thể là hiện vật của
       phép cắt chứ không phải của model. Một dụng cụ hỏng cho ra thứ đọc lên y
       hệt một phát hiện.

    Nay `moc_s` có `so_doan + 1` phần tử, phần tử cuối là hết bản — cùng khuôn
    với một mảng ranh giới, để cắt `[moc[i], moc[i+1]]` mà không phải cộng độ
    dài lấy từ nơi khác.
    """
    import numpy as np

    from voice_sidecar import noi_dai

    sr = 24_000
    ds = [(np.sin(np.linspace(0, 200, sr)) * 0.3).astype(np.float32)
          for _ in range(4)]
    ra, hs = noi_dai.ghep(ds, sr, so_cau=[1] * 4)

    moc = hs.get("moc_s")
    assert moc, "ho so ghep khong noi moc — xem docstring"
    assert len(moc) == hs["so_doan"] + 1, (
        f"{len(moc)} moc cho {hs['so_doan']} doan; can {hs['so_doan'] + 1}")
    assert moc == sorted(moc), "moc phai tang dan"
    assert abs(moc[-1] - len(ra) / sr) < 1e-3, (
        f"moc cuoi {moc[-1]} khong khop do dai that {len(ra) / sr}")
    # ⛔ Và phải KHÁC chia đều — nếu bằng nhau thì hoặc không có nghỉ nào được
    #    chèn, hoặc ai đó đã "sửa" `moc_s` thành chính phép chia đều mà nó thay.
    deu = [i * len(ra) / sr / hs["so_doan"] for i in range(hs["so_doan"] + 1)]
    assert any(abs(a - b) > 1e-3 for a, b in zip(moc, deu)), (
        "moc trung khop chia deu — phep cat khong con bao ve duoc gi")


def test_bai_dai_KHONG_bi_chan_boi_kich_thuoc_lo_ben_trong():
    """🔴 Một con số của vòng lặp bên trong đi lạc ra thành hợp đồng của khách.

    `/v1/speech-dai` gọi `ngan_sach.kiem_mot_lo`, và hàm ấy áp
    `TRAN_SO_VAN_BAN_BATCH = 8` — một hằng số **tự khai là tạm**: *"giữ thấp hơn
    cho tới khi đo được VRAM thật của từng bậc batch"*.

    Đo thật 01/09/2026: một bài đọc mười hai đoạn nhận
    `413 "Lo 12 van ban, vuot tran 8"`. Không ai chọn giới hạn ấy cho khách cả —
    nó là kích thước một lượt gộp lô, tức **chuyện xếp việc cho GPU**, và nó rò
    ra tới tận thông báo lỗi người dùng đọc.

    ⭐ Cách sửa không phải nâng con số 8 lên. Nâng nó chỉ dời cái vách ra xa hơn
       và giữ nguyên chuyện *khách phải biết engine gộp lô mấy đoạn một lượt*.
       Cửa văn bản dài **tự chia nhóm**, và phép ghép vẫn chạy MỘT LẦN trên toàn
       bộ đoạn — nên nhịp nghỉ và phép cân mức vẫn tính trên cả bài, y như cũ.

    ⛔ Trần thật của một bài dài là **tổng số ký tự**, và nó thuộc tầng app
       (`TRAN_KY_TU_CONG_KHAI`). Cổng giọng chỉ chốt từng đoạn.
    """
    from voice_sidecar import ngan_sach, tham_so

    n = tham_so.TRAN_SO_VAN_BAN_BATCH
    bai = [f"Day la doan thu {i + 1} cua mot bai doc dai." for i in range(n * 2)]

    ra = ngan_sach.kiem_bai_dai(bai)          # KHÔNG được ném
    assert len(ra) == len(bai)

    # Còn `kiem_mot_lo` thì vẫn phải giữ trần — nó nói về MỘT lượt gộp lô thật.
    with pytest.raises(ngan_sach.VuotNganSach):
        ngan_sach.kiem_mot_lo(bai)


def test_cua_van_ban_dai_CHIA_NHOM_chu_khong_goi_mot_lan():
    """Chốt rằng cửa dài thật sự chia nhóm, không phải chỉ bỏ phép kiểm.

    Bỏ trần mà vẫn gọi `noi_lo` một lần cho tất cả sẽ đẩy lỗi xuống sâu hơn —
    lúc ấy nó thành một lỗi CUDA giữa chừng thay vì một `413` sạch sẽ, tức tệ
    hơn chỗ xuất phát.
    """
    import ast
    import inspect

    from voice_sidecar import server

    src = inspect.getsource(server.create_app)
    cay = ast.parse(src.lstrip())
    ham = [n for n in ast.walk(cay)
           if isinstance(n, ast.FunctionDef) and n.name == "speech_dai"]
    assert ham, "khong tim thay handler `speech_dai`"

    goi = [n for n in ast.walk(ham[0])
           if isinstance(n, ast.Call)
           and isinstance(n.func, ast.Attribute) and n.func.attr == "noi_lo"]
    assert goi, "`speech_dai` khong goi `noi_lo` nua?"
    trong_vong = any(
        any(g is c for c in ast.walk(v))
        for v in ast.walk(ham[0]) if isinstance(v, (ast.For, ast.While))
        for g in goi)
    assert trong_vong, (
        "`noi_lo` khong nam trong vong lap — cua dai dang goi mot lan cho ca "
        "bai, tuc chi bo phep kiem chu khong chia nhom")
