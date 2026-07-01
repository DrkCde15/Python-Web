"""add respostas_cache table

Revision ID: df67217e0195
Revises: 4bb7ac6401b9
Create Date: 2026-07-01 09:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'df67217e0195'
down_revision: Union[str, Sequence[str], None] = '4bb7ac6401b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('respostas_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=64), nullable=False),
        sa.Column('pergunta', sa.Text(), nullable=False),
        sa.Column('resposta', sa.Text(), nullable=False),
        sa.Column('model', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('hits', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_respostas_cache_key'), 'respostas_cache', ['key'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_respostas_cache_key'), table_name='respostas_cache')
    op.drop_table('respostas_cache')
