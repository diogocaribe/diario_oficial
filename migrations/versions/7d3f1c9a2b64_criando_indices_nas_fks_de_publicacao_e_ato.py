"""criando indices nas fks de publicacao e ato

As consultas por edição (publicacao.doe_bruto_id) e por publicação (ato.publicacao_id),
usadas em todas as etapas do pipeline e no trigger de reprocessamento, varriam a tabela
inteira.

Revision ID: 7d3f1c9a2b64
Revises: bcd56ebfe8e3
Create Date: 2026-11-09 18:10:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '7d3f1c9a2b64'
down_revision: Union[str, None] = 'bcd56ebfe8e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(op.f('ix_publicacao_doe_bruto_id'), 'publicacao', ['doe_bruto_id'], unique=False, schema='processing')
    op.create_index(op.f('ix_ato_publicacao_id'), 'ato', ['publicacao_id'], unique=False, schema='processing')


def downgrade() -> None:
    op.drop_index(op.f('ix_ato_publicacao_id'), table_name='ato', schema='processing')
    op.drop_index(op.f('ix_publicacao_doe_bruto_id'), table_name='publicacao', schema='processing')
