"""L-31 (T1b): `--reasoning-budget-message` có mặt, ĐÚNG NGUYÊN VĂN, ở cả hai hồ sơ B.

Cờ này là câu "dừng suy nghĩ" của Qwen3 Technical Report (arXiv 2505.09388, mục
Thinking Budget) mà llama.cpp tiêm trước `</think>` khi budget cạn. Nguồn cộng đồng:
llama.cpp#28182 — không có câu này, budget cắt ngang làm parser lệch và `</think>`
lọt vào content. Đặt ở ENGINE vì `/v1/messages` của llama.cpp bỏ trường
`reasoning_budget_message` trong thân request khi đổi Anthropic→OAI.

⭐ Phép kiểm đọc giá trị như **llama-swap v250 trên Windows** đọc, không bằng
   `str.split()`: cờ mang một đối số có dấu cách và một xuống dòng THẬT ở cuối.
   - llama-swap `internal/config/commands.go::SanitizeCommand` bỏ dòng `#`, thay
     `\\` cuối dòng bằng dấu cách, rồi tách bằng `shlex.Windows` của
     `billziss-gh/golib` (chỉ `"` là ngoặc; `\\` chỉ đặc biệt khi đứng trước `"`).
     `_tach_windows` dưới đây là bản chép từng nhánh của `Dialect.Split` +
     `Windows.Escape/LongEscape`; ca `test_ban_chep_shlex_khop_test_upstream` là
     đúng ca `TestConfig_SanitizeCommand` trong `config_windows_test.go` v250.
   - llama.cpp b10883 `common/arg.cpp:3715` gán MESSAGE nguyên văn, KHÔNG qua
     `string_process_escapes` ⇒ viết `\\n` trong cmd là hai ký tự đi thẳng vào suy
     nghĩ của model. Đối chứng `test_doi_chung_*` giữ cho phép kiểm không xanh với
     cách viết đó.
"""
from __future__ import annotations

import copy
import pathlib

import pytest
import yaml

GOC = pathlib.Path(__file__).resolve().parents[1]
YAML = GOC / "llm_gateway" / "deploy" / "llama-swap.yaml"

HO_SO = ("qwen38-api", "qwen35-api")
CO = "--reasoning-budget-message"
#: Nguyên văn Qwen3 Technical Report, kết bằng MỘT xuống dòng thật (LF).
THONG_DIEP = ("Considering the limited time by the user, I have to give the "
              "solution based on the thinking directly now.\n")


# ── Bản chép bộ tách lệnh của llama-swap v250 (Windows) ────────────────────

_SPACE, _WORD, _DQ = " ", "A", '"'
_EMPTY = object()      # EmptyRune
_NO = object()         # NoEscape


def _escape(s, r, r0):
    if s in (_SPACE, _WORD):
        return r0 if (r == "\\" and r0 == '"') else _NO
    if s == _DQ:
        return r0 if (r in ("\\", '"') and r0 == '"') else _NO
    return _NO


def _long_escape(s, r, line):
    """Windows: n dấu `\\` không đứng trước `"` ⇒ giữ nguyên n dấu."""
    if r != "\\":
        return None
    n = 0
    while True:
        r1 = line[n] if n < len(line) else None
        n += 1
        if r1 is None or r1 != "\\":
            break
    if n < 2:
        return None
    if r1 != '"':
        return ("\\" * (n - 1), line[n - 1:], r1)
    if n % 2 == 0:
        return ("\\" * (n // 2 - 1), line[n - 1:], '"')
    return ("\\" * (n // 2 - 1), line[n - 2:], "\\")


def _tach_windows(line: str) -> list[str]:
    """`shlex.Windows.Split` (golib) — chép từng nhánh."""
    tokens: list[str] = []
    token: list[str] | None = None
    state = [_SPACE]
    r = line[0] if line else None
    line = line[1:]
    while r is not None:
        r0 = line[0] if line else None
        s = state[-1]
        e = _escape(s, r, r0 if r0 is not None else _EMPTY)
        if e is not _NO:
            if r0 is not None:
                line = line[1:]
                r0 = line[0] if line else None
            if e is _EMPTY:
                r = r0
                line = line[1:] if r0 is not None else line
                continue
        if s == _SPACE:
            if e is not _NO:
                state.append(_WORD)
                token = (token or []) + [e]
            elif r == '"':
                state += [_WORD, r]
                token = []
            elif r not in " \t\r\n":
                state.append(_WORD)
                token = (token or []) + [r]
        elif s == _WORD:
            if e is not _NO:
                token.append(e)
            elif r == '"':
                state.append(r)
            elif r in " \t\r\n":
                state.pop()
                tokens.append("".join(token))
                token = None
            else:
                token.append(r)
        else:
            if e is not _NO:
                token.append(e)
            elif r == s:
                state.pop()
            else:
                token.append(r)
        if e is _NO:
            le = _long_escape(s, r, line)
            if le is not None:
                them, line, r0 = le
                token.extend(them)
                line = line[1:] if r0 is not None else line
                r = r0
                continue
        r = r0
        line = line[1:] if r0 is not None else line
    if token is not None:
        tokens.append("".join(token))
    return tokens


def _sanitize(cmd: str) -> list[str]:
    """`SanitizeCommand` v250: bỏ dòng `#`, `\\` cuối dòng ⇒ dấu cách, rồi tách."""
    dong = []
    for x in cmd.split("\n"):
        t = x.strip()
        if t.startswith("#"):
            continue
        dong.append(t[:-1] + " " if t.endswith("\\") else x)
    return _tach_windows("\n".join(dong))


def _argv(cfg: dict, ten: str) -> list[str]:
    cmd = str(cfg["models"][ten]["cmd"])
    for khoa, gt in (cfg.get("macros") or {}).items():
        cmd = cmd.replace("${%s}" % khoa, str(gt))
    return _sanitize(cmd)


def ho_so_sai_thong_diep(cfg: dict) -> list[str]:
    """Hàm phán xử — đối chứng gọi ĐÚNG hàm này. Trả hồ sơ thiếu/sai cờ."""
    sai = []
    for ten in HO_SO:
        a = _argv(cfg, ten)
        if a.count(CO) != 1 or a.index(CO) + 1 >= len(a) or a[a.index(CO) + 1] != THONG_DIEP:
            sai.append(ten)
    return sai


@pytest.fixture(scope="module")
def cfg() -> dict:
    return yaml.safe_load(YAML.read_text(encoding="utf-8"))


# ── Bản chép bộ tách phải khớp test của chính llama-swap ─────────────────────

def test_ban_chep_shlex_khop_test_upstream():
    cmd = ('python model1.py \\\n\n\t-a "double quotes" \\\n\t-s\n\t--arg3 123 \\\n\n'
           '\t   # comment 2\n\t--arg4 \'"string in string"\'\n\n\n\n'
           '\t# this will get stripped out as well as the white space above\n'
           '\t-c "\'single quoted\'"\n\t')
    assert _sanitize(cmd) == ["python", "model1.py", "-a", "double quotes", "-s",
                              "--arg3", "123", "--arg4", "'string in string'",
                              "-c", "'single quoted'"]


def test_ban_chep_shlex_quy_tac_gach_nguoc_windows():
    assert _tach_windows(r'a\nb') == [r"a\nb"]            # \ không trước " = nguyên văn
    assert _tach_windows(r'"x\"y"') == ['x"y']
    assert _tach_windows('"hai\ndong"') == ["hai\ndong"]  # xuống dòng thật trong ngoặc


# ── Phép kiểm ──────────────────────────────────────────────────────────────

def test_ca_hai_ho_so_co_thong_diep_dung_nguyen_van(cfg):
    assert ho_so_sai_thong_diep(cfg) == []


def test_thong_diep_la_mot_doi_so_va_co_sau_van_nguyen(cfg):
    """Chuỗi trong ngoặc không nuốt cờ kế tiếp; budget vẫn là co của hồ sơ."""
    for ten in HO_SO:
        a = _argv(cfg, ten)
        i = a.index(CO)
        assert a[i + 2].startswith("-"), a[i + 2]
        assert "--reasoning-budget" in a and "--temp" in a
        assert a[-2:] == ["--port", "${PORT}"]


def test_khong_dat_trong_macro_chung(cfg):
    assert CO not in str((cfg.get("macros") or {}).get("CHUNG") or "")


# ── Đối chứng: phép kiểm phải ĐỎ với các cách viết sai ─────────────────────

def _thay_cmd(cfg: dict, ten: str, cu: str, moi: str) -> dict:
    lech = copy.deepcopy(cfg)
    goc = str(lech["models"][ten]["cmd"])
    assert cu in goc
    lech["models"][ten]["cmd"] = goc.replace(cu, moi)
    return lech


def test_doi_chung_viet_gach_n_mot_dong_bi_bat(cfg):
    """`"...now.\\n"` trên một dòng = hai ký tự `\\`+`n` (llama.cpp không giải escape)."""
    lech = _thay_cmd(cfg, "qwen35-api", 'directly now.\n"', 'directly now.\\n"')
    assert "qwen35-api" in ho_so_sai_thong_diep(lech)
    a = _argv(lech, "qwen35-api")
    assert a[a.index(CO) + 1].endswith("now.\\n")


def test_doi_chung_nhay_don_bi_bat(cfg):
    """Trên Windows `'` không phải ngoặc ⇒ câu vỡ thành nhiều đối số."""
    goc = str(cfg["models"]["qwen38-api"]["cmd"])
    i = goc.index(CO) + len(CO) + 1
    j = goc.index('"', i + 1)
    lech = copy.deepcopy(cfg)
    lech["models"]["qwen38-api"]["cmd"] = goc[:i] + "'" + goc[i + 1:j] + "'" + goc[j + 1:]
    assert "qwen38-api" in ho_so_sai_thong_diep(lech)


def test_doi_chung_thieu_co_bi_bat(cfg):
    lech = copy.deepcopy(cfg)
    goc = str(lech["models"]["qwen38-api"]["cmd"])
    i = goc.index(CO)
    j = goc.index('"', goc.index('"', i) + 1) + 1
    lech["models"]["qwen38-api"]["cmd"] = goc[:i] + goc[j:]
    assert ho_so_sai_thong_diep(lech) == ["qwen38-api"]
