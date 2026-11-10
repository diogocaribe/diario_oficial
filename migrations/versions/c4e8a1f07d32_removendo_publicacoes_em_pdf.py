"""removendo publicacoes em pdf

PDFs ficam fora do pipeline: o texto salvo era o binário do arquivo. Apaga as publicações
com conteudo_link em PDF, seus atos e suas linhas de log_erro. As edições em doe_bruto e
as demais publicações delas continuam.

O downgrade não restaura os registros: a remoção é definitiva.

Revision ID: c4e8a1f07d32
Revises: 7d3f1c9a2b64
Create Date: 2026-11-10 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4e8a1f07d32'
down_revision: Union[str, None] = '7d3f1c9a2b64'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PUBLICACOES_PDF = r"""
    SELECT id FROM processing.publicacao WHERE conteudo_link ~ '^\s*%PDF'
"""


def upgrade() -> None:
    # Nessa ordem: a FK de log_erro para publicacao é RESTRICT
    op.execute(sa.text(
        f'DELETE FROM processing.ato WHERE publicacao_id IN ({PUBLICACOES_PDF})'
    ))
    op.execute(sa.text(
        f'DELETE FROM processing.log_erro WHERE publicacao_id IN ({PUBLICACOES_PDF})'
    ))
    op.execute(sa.text(
        f'DELETE FROM processing.publicacao WHERE id IN ({PUBLICACOES_PDF})'
    ))


def downgrade() -> None:
    pass
