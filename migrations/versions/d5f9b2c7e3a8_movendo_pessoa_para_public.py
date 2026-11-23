"""movendo pessoa do esquema auto_infracao para public

A pessoa é comum a todas as extrações: a mesma pessoa pode aparecer em atos de
tipos diferentes, e outro tipo de ato não deve apontar para auto_infracao.pessoa.
SET SCHEMA move a tabela com os dados, os ids, a sequência do id, o índice
uq_pessoa_documento e as constraints. A FK auto_infracao.autuado_id continua
apontando para a mesma tabela.

Revision ID: d5f9b2c7e3a8
Revises: c4e8a1d6f2b7
Create Date: 2026-11-23 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd5f9b2c7e3a8'
down_revision: Union[str, None] = 'c4e8a1d6f2b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text('ALTER TABLE auto_infracao.pessoa SET SCHEMA public'))


def downgrade() -> None:
    op.execute(sa.text('ALTER TABLE public.pessoa SET SCHEMA auto_infracao'))
