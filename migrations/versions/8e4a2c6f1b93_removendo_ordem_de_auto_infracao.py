"""removendo a coluna ordem de auto_infracao

Revision ID: 8e4a2c6f1b93
Revises: 5d1f8b3e7a42
Create Date: 2026-11-19 16:00:00.000000

A posição do auto na resposta do modelo deixa de ser gravada; os autos de um trecho
são lidos na ordem do ``id``. O ``downgrade`` recria a coluna com a ordem do ``id``
dentro de cada trecho.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8e4a2c6f1b93'
down_revision: Union[str, None] = '5d1f8b3e7a42'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ESQUEMA = 'auto_infracao'


def upgrade() -> None:
    op.drop_column('auto_infracao', 'ordem', schema=ESQUEMA)


def downgrade() -> None:
    op.add_column(
        'auto_infracao',
        sa.Column(
            'ordem',
            sa.Integer(),
            nullable=True,
            comment='Posição do auto na resposta do modelo para o trecho.',
        ),
        schema=ESQUEMA,
    )
    op.execute(
        sa.text(
            f"""
            UPDATE {ESQUEMA}.auto_infracao AS a
               SET ordem = n.ordem
              FROM (
                    SELECT id,
                           row_number() OVER (
                               PARTITION BY extracao_trecho_id ORDER BY id
                           ) AS ordem
                      FROM {ESQUEMA}.auto_infracao
                   ) AS n
             WHERE a.id = n.id
            """
        )
    )
    op.alter_column(
        'auto_infracao',
        'ordem',
        existing_type=sa.Integer(),
        nullable=False,
        schema=ESQUEMA,
    )
