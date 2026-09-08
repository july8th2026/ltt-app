"""Fixture dùng chung: tạm coi MỌI provider là còn sống, cho các phép kiểm CƠ CHẾ.

## Vấn đề nó giải

Pha 04 (AI CLEAN REBUILD V2) retire `gemini` · `apiai` · `cheapkeyai`. Nhưng
nhiều tệp test không chốt *provider nào đang sống* — chúng chốt **cơ chế**:

    test_251  khuon day + anh xa loi cua dong co Gemini (429 -> ban, 401, 400…)
    test_255  cascade cua `dieu_phoi` (ban -> di tiep, danh dau loi, thu tu)
    test_71   handler `thumbnail`: khuon request, luu storage, gia credit
    test_117  `taoanh`: quyen rieng tu anh tham chieu, phan giai id model cu
    test_88   hop dong ToolSpec: tham so min/max, gia, output
    test_130  `prompt_ai_ommi`: chuan hoa anh truoc khi submit
    test_98   Canvas chay het bay ToolSpec that

Mệnh đề chúng canh phải **BẤT BIẾN VỚI TẬP HỢP PROVIDER**. Nếu không, mỗi lần
nền tảng retire một provider thì một phép kiểm về *cơ chế* lại đỏ, và người ta
sẽ sửa nó bằng cách **hạ kỳ vọng** — tức làm mất luôn thứ nó canh.

## ⛔ Nó KHÔNG che sự thật production

Chốt production-thật (ba họ đã ngừng, cổng fail-closed, enum rỗng thì từ chối)
nằm ở **`tests/test_1000_chan_provider_da_ngung.py`**, và tệp đó **không** dùng
fixture này. Mỗi tệp chốt một thứ.

## ⏭️ HẠN DÙNG — module này PHẢI BIẾN MẤT ở pha 06

Khi `taoanh`/`thumbnail`/`prompt_ai_ommi` chuyển sang `LTT_IMAGE`/`LTT_LLM`,
enum `model_ref` của chúng không còn rỗng và các tệp trên được viết lại quanh
động cơ mới ⇒ không tệp nào còn cần fixture này.

🔴 Một lớp che "tạm thời" **không có ngày hết hạn viết ra** sẽ sống mãi — và nó
che đúng thứ chiến dịch này sinh ra để phơi bày. Ngày hết hạn của nó là pha 06,
và cách kiểm là: `grep -rl rao_provider_retire tests/` phải trả về **rỗng**.
"""
from __future__ import annotations

import dataclasses

import pytest


@pytest.fixture(autouse=True)
def moi_provider_deu_song(monkeypatch):
    """Patch `providers.REGISTRY` sao cho mọi provider đều `is_active=True`.

    Đọc thẳng `REGISTRY` chứ không patch `providers.get()`, vì cổng
    `providers.da_ngung()` cố ý đọc `REGISTRY` — patch nhầm chỗ thì fixture
    không có tác dụng và ta sẽ đi tìm lý do ở nơi khác.
    """
    from platform_core import providers

    monkeypatch.setattr(
        providers, "REGISTRY",
        {pid: dataclasses.replace(p, is_active=True)
         for pid, p in providers.REGISTRY.items()},
        raising=False)
