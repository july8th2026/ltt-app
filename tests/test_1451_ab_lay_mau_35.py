"""test_1451 — bộ đề cố định + luật A/B của `tools/ab_lay_mau_35.py` (Task 12). Thuần, không mạng.

Kiểm cả BỘ ĐỀ: mỗi bài có một lời giải tham chiếu mà bộ chấm phải cho ĐẠT, và một câu sai phải TRƯỢT —
không thì phép A/B đo bộ chấm chứ không đo model.
"""
from __future__ import annotations

import json

import pytest

from tools import ab_lay_mau_35 as T

GIAI = {
    "c01": "def roman_to_int(s):\n    v={'I':1,'V':5,'X':10,'L':50,'C':100,'D':500,'M':1000}\n    t=0\n"
           "    for i,ch in enumerate(s):\n        if i+1<len(s) and v[ch]<v[s[i+1]]: t-=v[ch]\n        else: t+=v[ch]\n"
           "    return t",
    "c02": "def merge_intervals(xs):\n    out=[]\n    for a,b in sorted(xs):\n        if out and a<=out[-1][1]: "
           "out[-1][1]=max(out[-1][1],b)\n        else: out.append([a,b])\n    return out",
    "c03": "import re\ndef parse_duration(s):\n    m=re.fullmatch(r'(?:(\\d+)h)?(?:(\\d+)m)?(?:(\\d+)s)?',s)\n"
           "    h,mi,se=(int(x or 0) for x in m.groups())\n    return h*3600+mi*60+se",
    "c04": "import heapq\ndef topo_sort(n,edges):\n    g=[[] for _ in range(n)];d=[0]*n\n    for u,v in edges: "
           "g[u].append(v);d[v]+=1\n    h=[i for i in range(n) if d[i]==0];heapq.heapify(h);o=[]\n    while h:\n"
           "        u=heapq.heappop(h);o.append(u)\n        for v in g[u]:\n            d[v]-=1\n"
           "            if d[v]==0: heapq.heappush(h,v)\n    return o if len(o)==n else None",
    "c05": "def tim(xs,x):\n    lo,hi=0,len(xs)\n    while lo<hi:\n        mid=(lo+hi)//2\n        if xs[mid]==x: return mid\n"
           "        if xs[mid]<x: lo=mid+1\n        else: hi=mid\n    return -1",
    "c06": "import re\nfrom collections import Counter\ndef top_words(text,k):\n"
           "    c=Counter(re.findall('[a-z]+',text.lower()))\n    return sorted(c.items(),key=lambda x:(-x[1],x[0]))[:k]",
    "c07": "def spiral(m):\n    o=[]\n    while m:\n        o+=m.pop(0)\n        m=[list(r) for r in zip(*m)][::-1]\n    return o",
    "c08": "def calc(e):\n    t=e.replace(' ','');i=0\n    def num():\n        nonlocal i\n        if t[i]=='(':\n"
           "            i+=1;v=add();i+=1;return v\n        j=i\n        while i<len(t) and t[i].isdigit(): i+=1\n"
           "        return float(t[j:i])\n    def mul():\n        nonlocal i\n        v=num()\n"
           "        while i<len(t) and t[i] in '*/':\n            o=t[i];i+=1;w=num();v=v*w if o=='*' else v/w\n"
           "        return v\n    def add():\n        nonlocal i\n        v=mul()\n        while i<len(t) and t[i] in '+-':\n"
           "            o=t[i];i+=1;w=mul();v=v+w if o=='+' else v-w\n        return v\n    return add()",
    "c09": "from collections import OrderedDict\nclass LRU:\n    def __init__(self,cap): self.c=cap;self.d=OrderedDict()\n"
           "    def get(self,k):\n        if k not in self.d: return -1\n        self.d.move_to_end(k);return self.d[k]\n"
           "    def put(self,k,v):\n        self.d[k]=v;self.d.move_to_end(k)\n"
           "        if len(self.d)>self.c: self.d.popitem(last=False)",
    "c10": "def doc_so(n):\n    cs='không một hai ba bốn năm sáu bảy tám chín'.split()\n    if n==0: return 'không'\n"
           "    tr,ch,dv=n//100,n//10%10,n%10;o=[]\n    if tr: o+=[cs[tr],'trăm']\n    if ch==0:\n"
           "        if dv and tr: o.append('linh')\n    elif ch==1: o.append('mười')\n    else: o+=[cs[ch],'mươi']\n"
           "    if dv:\n        if dv==1 and ch>1: o.append('mốt')\n        elif dv==5 and ch>0: o.append('lăm')\n"
           "        else: o.append(cs[dv])\n    return ' '.join(o)",
}

DUNG_VI = {
    "v01": "305.000", "v02": "Giá cuối là 748000", "v03": "Thứ Sáu", "v04": "Dũng", "v05": "240",
    "v06": "120", "v07": json.dumps({"ho_ten": "Nguyễn Thị Lan", "tuoi": 34, "thanh_pho": "Đà Nẵng",
                                     "so_dien_thoai": "0905 123 456"}, ensure_ascii=False),
    "v08": "Hà Nội là thủ đô của Việt Nam. Thành phố có nhiều hồ nước và phố cổ. Người dân ở đây rất hiếu khách.",
    "v09": "Ánh sáng mặt trời bị tán xạ bởi các phân tử khí trong không khí. Ánh sáng xanh có bước sóng ngắn nên "
           "tán xạ mạnh hơn, khiến bầu trời có màu xanh.",
    "v10": "10",
}


def _tc(ten, **args):
    return {"function": {"name": ten, "arguments": json.dumps(args, ensure_ascii=False)}}


@pytest.mark.parametrize("bai", T.DE_CODE, ids=lambda b: b["ma"])
def test_moi_bai_code_co_loi_giai_dat_va_cau_rong_truot(bai):
    assert T.cham_code(bai, "```python\n" + GIAI[bai["ma"]] + "\n```")
    assert not T.cham_code(bai, "```python\ndef khong_lien_quan():\n    return 0\n```")
    assert not T.cham_code(bai, "")


def test_cham_code_lay_khoi_dai_nhat_khi_co_nhieu_khoi():
    bai = T.DE_CODE[0]
    text = "Ví dụ:\n```python\nroman_to_int('X')\n```\nLời giải:\n```python\n" + GIAI["c01"] + "\n```"
    assert T.cham_code(bai, text)


@pytest.mark.parametrize("bai", T.DE_VI, ids=lambda b: b["ma"])
def test_moi_bai_vi_dat_voi_cau_dung_va_truot_voi_cau_sai(bai):
    assert T.cham_vi(bai, DUNG_VI[bai["ma"]])
    assert not T.cham_vi(bai, "")
    assert not T.cham_vi(bai, "Tôi không biết 1")


def test_vi_so_lay_so_cuoi_va_chap_nhan_dau_phan_nghin():
    bai = next(b for b in T.DE_VI if b["ma"] == "v01")
    assert T.cham_vi(bai, "135.000 + 60.000 = 195.000, thối 305 000")
    assert not T.cham_vi(bai, "305000 - không, đáp án là 295000")


def test_vi_ba_cau_bat_chu_cam_va_sai_so_cau():
    bai = next(b for b in T.DE_VI if b["ma"] == "v08")
    assert not T.cham_vi(bai, DUNG_VI["v08"].replace("hiếu khách", "đẹp"))
    assert not T.cham_vi(bai, DUNG_VI["v08"] + " Thêm một câu nữa.")


def test_tool_dung_ten_va_tham_so():
    t = {b["ma"]: b for b in T.DE_TOOL}
    assert T.cham_tool(t["t01"], "", [_tc("tra_thoi_tiet", thanh_pho="Đà Nẵng")])
    assert not T.cham_tool(t["t01"], "", [_tc("tinh_tien", so_luong=1, don_gia=1)])
    assert T.cham_tool(t["t02"], "", [_tc("tinh_tien", so_luong=3, don_gia=12500)])
    assert not T.cham_tool(t["t02"], "", [_tc("tinh_tien", so_luong=3, don_gia=37500)])
    assert T.cham_tool(t["t03"], "", [_tc("gui_email", den="lan@ltt.vn", noi_dung="Họp dời sang 3 giờ chiều")])
    assert T.cham_tool(t["t05"], "", [_tc("tra_thoi_tiet", thanh_pho="Hà Nội"), _tc("tra_thoi_tiet", thanh_pho="Huế")])
    assert not T.cham_tool(t["t05"], "", [_tc("tra_thoi_tiet", thanh_pho="Huế")])
    assert T.cham_tool(t["t06"], "", [_tc("tinh_tien", so_luong=7, don_gia=15000)])


def test_tool_khong_can_goi_thi_phai_tra_loi_chu():
    t04 = next(b for b in T.DE_TOOL if b["ma"] == "t04")
    assert T.cham_tool(t04, "Tôi khoẻ, cảm ơn bạn!", [])
    assert not T.cham_tool(t04, "", [_tc("tra_thoi_tiet", thanh_pho="Huế")])
    assert not T.cham_tool(t04, "", [])


def test_mcnemar():
    assert T.mcnemar_p(0, 0) == 1.0
    assert T.mcnemar_p(5, 5) == 1.0
    assert T.mcnemar_p(10, 0) == pytest.approx(2 / 1024)
    assert T.mcnemar_p(0, 10) == T.mcnemar_p(10, 0)


def test_bien_the_A_khong_gui_gi_va_moi_phep_chi_mot_bien():
    assert T.BIEN_THE["A"] == {}
    for phep, (b, _nhom) in T.PHEP.items():
        assert len(T.BIEN_THE[b]) == 1, phep


def test_viec_xen_ke_A_va_B_dung_nhom():
    viec = T.viec_can_chay(1)
    theo = {}
    for bai, _i, bt in viec:
        theo.setdefault(bt, set()).add(bai["nhom"])
    assert theo["A"] == {"code", "vi", "tool", "agent"}
    assert theo["t06"] == {"code"}
    assert theo["pt_false"] == {"agent"}
    assert theo["codex"] == {"code", "tool", "agent"}
    # mỗi B ngay sau A của cùng bài (cùng tải máy)
    assert all(viec[k][2] == "A" or viec[k][0]["ma"] == viec[k - 1][0]["ma"] for k in range(1, len(viec)))


def _dong(ma, nhom, lan, bt, dung, **kw):
    return {"ma": ma, "nhom": nhom, "lan": lan, "bien_the": bt, "dung": dung, **kw}


def test_phan_quyet_thang_ro_va_khong_tut():
    dong = []
    for i in range(12):
        dong += [_dong(f"c{i}", "code", 0, "A", False), _dong(f"c{i}", "code", 0, "t06", True)]
    kq = T.phan_quyet(dong, "temp_code")
    assert kq["chi_B_dung"] == 12 and kq["chi_A_dung"] == 0
    assert kq["B_thang_ro"] and kq["B_khong_tut"]


def test_phan_quyet_bang_nhau_khong_thang_ro_nhung_khong_tut():
    dong = []
    for i in range(10):
        dong += [_dong(f"v{i}", "vi", 0, "A", True), _dong(f"v{i}", "vi", 0, "pp15", True)]
    kq = T.phan_quyet(dong, "presence")
    assert not kq["B_thang_ro"] and kq["B_khong_tut"]


def test_phan_quyet_bo_qua_luot_khong_do_duoc_va_cap_thieu():
    dong = [_dong("c1", "code", 0, "A", True), _dong("c1", "code", 0, "t06", None),
            _dong("c2", "code", 0, "A", True)]
    assert T.phan_quyet(dong, "temp_code")["cap"] == 0


def test_phan_quyet_tut_mot_nhom_thi_khong_thang_ro():
    dong = []
    for i in range(14):  # code: B thắng 14-0
        dong += [_dong(f"c{i}", "code", 0, "A", False), _dong(f"c{i}", "code", 0, "rb4096", True)]
    for i in range(10):  # vi: B tụt 10 → 0
        dong += [_dong(f"v{i}", "vi", 0, "A", True), _dong(f"v{i}", "vi", 0, "rb4096", False)]
    kq = T.phan_quyet(dong, "budget")
    assert kq["nhom"]["vi"]["tut_duoi_wilson_A"]
    assert not kq["B_thang_ro"]


def test_ti_le_cache_trong_phan_phu():
    dong = [_dong("a00", "agent", 0, "A", True, prompt_n=1000, cache_n=800),
            _dong("a00", "agent", 0, "pt_false", True, prompt_n=900, cache_n=300)]
    kq = T.phan_quyet(dong, "preserve")
    assert kq["phu_A"]["ti_le_cache"] == 0.8
    assert kq["phu_pt_false"]["ti_le_cache"] == pytest.approx(0.333, abs=1e-3)
