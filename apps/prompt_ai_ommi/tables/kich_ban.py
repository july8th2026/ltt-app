"""tables/kich_ban.py — storyboard + canh + phien ban canh.

Tach tu apps/prompt_ai_ommi/tables.py (2026-09-26). Ba lop nay khong nam
trong danh sach 7 tep con spec liet ke rieng cho pha 1-4 (binding/brief/
iteration/nhan_vat/chia_se/tai_nguyen/thu_vien) vi chung la mo hinh CU da co
tu truoc spec nay (khong doi trong pha 1) — dat rieng mot tep de khong lan
voi `binding.py` (quyet dinh D-1, xem dau plan).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from platform_core.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class OmmiStoryboard(Base):
    """Một storyboard thuộc về một project.

    Project vẫn là `AppProject` của nền tảng; storyboard chỉ tham chiếu bằng
    `project_id`. Không dựng bảng project thứ hai — nền tảng đã có một cái và
    hai nguồn sự thật về "project là gì" là cách chắc chắn để chúng lệch nhau.
    """

    __tablename__ = "ommi_storyboard"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    # Meta prompt và phong cách dùng cho cả storyboard; để trống thì mỗi cảnh tự lo.
    meta_prompt_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    style_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    aspect_ratio: Mapped[str] = mapped_column(String(12), default="16:9", nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class OmmiScene(Base):
    """Một KHUNG HÌNH storyboard — ⛔ KHÔNG phải "cảnh kịch bản" (spec §4.3 S-2).

    ⚠️ Hai thứ trong app này cùng mang chữ "cảnh", và trộn chúng là một con bọ
    thật đã được phán quyết ở spec §4.3:

      · **cảnh kịch bản** — `ommi_canh`, do AI Director sinh, giữ `prompt` đi ra
        ngoài (giao bài sang app video). Đó là NGUỒN CHÂN LÝ.
      · **khung hình** — bảng này, có `storyboard_id`/`position`/`image_key`.
        `prompt`/`camera` ở đây chỉ là bản SAO phục vụ việc sinh ảnh.

    `image_key` trỏ thẳng tới Storage thay vì tới `ommi_resource_variant`: ảnh
    của cảnh do job sinh ra và nằm trong namespace của app Tạo ảnh, không phải
    tài nguyên tái sử dụng của người dùng.
    """

    __tablename__ = "ommi_scene"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    storyboard_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    # Khung hinh nay ve cho CANH KICH BAN nao (spec §4.3 S-2).
    #
    # `nullable` vi hai ca THAT: khung hinh tao truoc pha 3 khong biet canh nao,
    # va khach duoc ve mot khung roi moi gan vao canh.
    #
    # ⛔ Dung doi thanh `nullable=False`: `services/storyboard.py` tao khung hinh
    #    ma chua biet canh, va mot cot NOT NULL o day se lam vo duong do.
    canh_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    title: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    camera: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    continuity: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # Tài nguyên tham chiếu cho cảnh này — giữ nhất quán nhân vật giữa các cảnh.
    resource_ids: Mapped[dict] = mapped_column(JSON, default=list, nullable=False)
    image_key: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        Index("ix_ommi_scene_board_position", "storyboard_id", "position"),
    )


class OmmiSceneVersion(Base):
    """Ảnh và prompt của một cảnh ở lần chạy trước.

    Có bảng này thì chạy lại MỘT cảnh không mất bản cũ, và so được hai lần.
    Nguồn giữ việc này ở `storyboard_scene_versions`; ta giữ đúng ý đó.
    """

    __tablename__ = "ommi_scene_version"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    scene_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    image_key: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    job_id: Mapped[str] = mapped_column(String(36), default="", nullable=False)
    # Câu góp ý người dùng gõ khi bấm "Chạy lại" (H19.5). Lưu vào chính bản
    # được sinh RA từ nó, nên lịch sử trả lời được câu "vì sao bản này khác
    # bản trước" — không có nó thì người dùng thấy 5 bản na ná nhau mà không
    # nhớ mình đã yêu cầu gì.
    feedback: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("scene_id", "version", name="uq_ommi_scene_version"),
    )
