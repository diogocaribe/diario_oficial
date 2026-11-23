"""renomeando auto_infracao.autuado_id para autuado_pessoa_id

O nome diz para qual tabela a FK aponta (public.pessoa), como endereco_autuado_id.
A FK, o índice e a constraint de NOT NULL são renomeados junto, para seguir a
naming_convention de database/configs/base.py.

Revision ID: e7a3c9d1f4b6
Revises: d5f9b2c7e3a8
Create Date: 2026-11-23 14:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e7a3c9d1f4b6'
down_revision: Union[str, None] = 'd5f9b2c7e3a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABELA = 'auto_infracao.auto_infracao'
# (nome antigo, nome novo)
COLUNA = ('autuado_id', 'autuado_pessoa_id')
CONSTRAINTS = [
    ('fk_auto_infracao_autuado_id_pessoa', 'fk_auto_infracao_autuado_pessoa_id_pessoa'),
    ('auto_infracao_autuado_id_not_null', 'auto_infracao_autuado_pessoa_id_not_null'),
]
INDICE = ('ix_auto_infracao_autuado_id', 'ix_auto_infracao_autuado_pessoa_id')


def _renomear(sentido: int) -> None:
    antiga, nova = COLUNA[::sentido]
    op.execute(sa.text(f'ALTER TABLE {TABELA} RENAME COLUMN {antiga} TO {nova}'))
    for constraint in CONSTRAINTS:
        antiga, nova = constraint[::sentido]
        op.execute(
            sa.text(f'ALTER TABLE {TABELA} RENAME CONSTRAINT {antiga} TO {nova}')
        )
    antiga, nova = INDICE[::sentido]
    op.execute(sa.text(f'ALTER INDEX auto_infracao.{antiga} RENAME TO {nova}'))


def upgrade() -> None:
    _renomear(1)


def downgrade() -> None:
    _renomear(-1)
