"""comentando a coluna autuado_id de auto_infracao

Revision ID: 5d1f8b3e7a42
Revises: 9a3c5e7f2b18
Create Date: 2026-11-19 15:00:00.000000

A FK aponta para a pessoa deduplicada pelo documento; o nome como está em cada auto
continua em ``autuado_nome``.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5d1f8b3e7a42'
down_revision: Union[str, None] = '9a3c5e7f2b18'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COMENTARIO = 'Pessoa autuada, única pelo CPF/CNPJ; sem documento, uma por auto.'


def upgrade() -> None:
    op.alter_column(
        'auto_infracao',
        'autuado_id',
        existing_type=sa.Integer(),
        existing_nullable=False,
        comment=COMENTARIO,
        schema='auto_infracao',
    )


def downgrade() -> None:
    op.alter_column(
        'auto_infracao',
        'autuado_id',
        existing_type=sa.Integer(),
        existing_nullable=False,
        comment=None,
        existing_comment=COMENTARIO,
        schema='auto_infracao',
    )
