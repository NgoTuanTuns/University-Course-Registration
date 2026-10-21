"""Lớp Base dùng chung cho mọi model.

naming_convention giúp tên khóa chính / khóa ngoại / unique ổn định, để migration và
`alembic downgrade` không bị lệch tên. Riêng CHECK: mọi CHECK đều phải tự đặt tên đầy đủ
(ví dụ `ck_offerings_schedule_array`), convention chỉ giữ nguyên tên đó.
"""
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
