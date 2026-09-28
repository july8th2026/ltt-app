"""B13 B1 (28/09) — tin hieu AO GIAC ASR thu BA: doan VONG LAI `initial_prompt`.

Ca that: asvr_47327a869a8f4597960048f09064740, seg_0024 (64,27..65,17) mang
`中文普通话句子` — khuc GIUA cua prompt `以下是中文普通话句子。`. Doan nay CO
moc tu (7,8 kt/s) nen hai tin hieu N-39 (a)/(b) khong tin hieu nao cham toi;
tin hieu THU BA nay doi chieu THANG voi dau vao ta tu truyen cho engine.
"""
from __future__ import annotations

from apps.auto_scan_video import ban_ghi

PROMPT_ZH = "以下是中文普通话句子。"


def test_4925_doan_KHUC_GIUA_prompt_bi_GAN_CO():
    """Ca that da do — doan CO moc tu, toc do binh thuong, nhung van la vong
    lai NGUYEN VAN mot khuc 7 ky tu cua prompt."""
    doan = {"ma": "seg_0024", "bat": 64.27, "ket": 65.17,
            "chu": "中文普通话句子",
            "tu": [{"bat": 64.27, "ket": 65.17, "chu": "中"}]}

    co = ban_ghi.nghi_ao_giac(doan, canh_chinh="aligned",
                              initial_prompt=PROMPT_ZH)
    assert co is not None, "khuc giua prompt phai bi gan co"
    assert co["ly_do"] == "vong_lai_initial_prompt"
    assert co["khop_ky_tu"] == 7
    assert co["nguong"] == ban_ghi.NGUONG_KY_TU_VONG_LAI_PROMPT


def test_4925_DOI_CHUNG_AM_khuc_con_RAT_NGAN_KHONG_bi_gan_co():
    """🔴 Doi chung am bat buoc: khong co no thi mot ban va 'gan co moi thu'
    cung xanh. Loi thoai THAT NGAN — chinh xac "中文" (2 ky tu, MOT khuc con
    that su, LIEN TIEP cua prompt) — nhung duoi `NGUONG_KY_TU_VONG_LAI_PROMPT`
    (4) ⇒ ⛔ KHONG duoc gan co, du khop chinh xac va du khong co moc tu."""
    doan_that_ngan = {"ma": "seg_0031", "bat": 10.0, "ket": 10.6,
                      "chu": "中文", "tu": []}

    co = ban_ghi.nghi_ao_giac(doan_that_ngan, canh_chinh="aligned",
                              initial_prompt=PROMPT_ZH)
    assert co is None, "cau thoai that bi an nham vi mot khuc con qua ngan"


def test_4925_khong_truyen_prompt_thi_HANH_VI_CU_GIU_NGUYEN():
    """Doi chung tuong thich nguoc: `initial_prompt` mac dinh rong, va moi
    phep kiem N-39 cu (khong truyen tham so nay) phai chay y het truoc."""
    doan_ao_giac_cu = {"ma": "seg_0083", "bat": 265.0, "ket": 265.034,
                       "chu": "中文字幕志愿者 李宗盛", "tu": []}
    co = ban_ghi.nghi_ao_giac(doan_ao_giac_cu, canh_chinh="aligned")
    assert co is not None and co["ly_do"] == "zero_moc_tu_va_toc_do_bat_kha"


def test_4925_danh_dau_doc_prompt_TU_tham_so_engine_cua_ban_ghi():
    """`danh_dau_nghi_ao_giac` phai tu doc `ban["tham_so_engine"]
    ["initial_prompt"]` — day la cho DUY NHAT ban ghi mang lai chuoi da
    truyen cho engine (xem `whisperx_runner.py`)."""
    ban = {
        "canh_chinh": "aligned",
        "tham_so_engine": {"initial_prompt": PROMPT_ZH},
        "doan": [
            {"ma": "seg_0001", "bat": 0.0, "ket": 2.0, "chu": "好啊我们走吧",
             "tu": [{"bat": 0.0, "ket": 2.0, "chu": "好"}]},
            {"ma": "seg_0024", "bat": 64.27, "ket": 65.17,
             "chu": "中文普通话句子",
             "tu": [{"bat": 64.27, "ket": 65.17, "chu": "中"}]},
        ],
    }
    assert ban_ghi.danh_dau_nghi_ao_giac(ban) == 1
    assert len(ban["doan"]) == 2, "⛔ KHONG duoc xoa doan"
    assert "nghi_ao_giac" not in ban["doan"][0]
    assert ban["doan"][1]["nghi_ao_giac"]["ly_do"] == "vong_lai_initial_prompt"
    assert ban_ghi.tom_tat(ban)["so_doan_nghi_ao_giac"] == 1


def test_4925_log_khong_KeyError_tren_TIN_HIEU_THU_BA():
    """🔴 Bay da sua: dong log cu doc thang `["ky_tu_moi_giay"]`, khoa nay
    KHONG co tren tin hieu vong_lai_initial_prompt. `_canh_bao_ao_giac`
    (giai_doan_chep_loi.py) phai doc an toan bang `.get()`."""
    from apps.auto_scan_video.giai_doan_chep_loi import _canh_bao_ao_giac

    ban = {
        "doan": [
            {"ma": "seg_0024", "nghi_ao_giac": {
                "ly_do": "vong_lai_initial_prompt", "khop_ky_tu": 7,
                "nguong": 4, "khe_s": 0.9, "so_ky_tu": 7}},
            {"ma": "seg_0083", "nghi_ao_giac": {
                "ly_do": "zero_moc_tu_va_toc_do_bat_kha",
                "ky_tu_moi_giay": 294.1, "nguong": 30.0,
                "khe_s": 0.034, "so_ky_tu": 10}},
            {"ma": "seg_0001"},  # khong bi gan co — phai bi bo qua
        ],
    }
    dong = _canh_bao_ao_giac(ban)
    assert dong == [
        ("seg_0024", "vong_lai_initial_prompt", 7),
        ("seg_0083", "zero_moc_tu_va_toc_do_bat_kha", 294.1),
    ]
