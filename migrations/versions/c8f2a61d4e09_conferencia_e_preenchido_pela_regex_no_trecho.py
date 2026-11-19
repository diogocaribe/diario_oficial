"""gravando a conferência e os campos preenchidos pela regex em extracao_trecho

Revision ID: c8f2a61d4e09
Revises: e36ed117ea37
Create Date: 2026-11-18 18:00:00.000000

``conferencia`` guarda o resultado de ``conferir`` (a resposta do modelo contra a
regex) e ``preenchido_pela_regex`` os campos que o modelo deixou vazios e a regex
preencheu. Os trechos já gravados ficam com ``conferencia`` NULL e lista vazia: para
preencher, extraia de novo com ``--save-db``.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c8f2a61d4e09'
down_revision: Union[str, None] = 'e36ed117ea37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ESQUEMA = 'dado_estruturado'


def upgrade() -> None:
    op.add_column(
        'extracao_trecho',
        sa.Column(
            'conferencia',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='Resultado de conferir: a resposta do modelo contra a regex.',
        ),
        schema=ESQUEMA,
    )
    op.add_column(
        'extracao_trecho',
        sa.Column(
            'preenchido_pela_regex',
            postgresql.ARRAY(sa.Text()),
            server_default='{}',
            nullable=False,
            comment='Campos que o modelo deixou vazios e a regex preencheu.',
        ),
        schema=ESQUEMA,
    )


def downgrade() -> None:
    op.drop_column('extracao_trecho', 'preenchido_pela_regex', schema=ESQUEMA)
    op.drop_column('extracao_trecho', 'conferencia', schema=ESQUEMA)
