"""removendo a coluna ordem de extracao_trecho e coordenada_extraida_trecho

Revision ID: b2d7f4a9c1e6
Revises: 8e4a2c6f1b93
Create Date: 2026-11-19 16:30:00.000000

A posição do trecho no ato e a do par de coordenadas no auto deixam de ser gravadas;
as linhas são lidas na ordem do ``id``. A unique (ato_id, sigla_tipo_ato, ordem) de
``extracao_trecho`` sai junto, porque um ato tem vários trechos. O ``downgrade``
recria as colunas numerando pela ordem do ``id``.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2d7f4a9c1e6'
down_revision: Union[str, None] = '8e4a2c6f1b93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ESQUEMA = 'auto_infracao'

# tabela e coluna que agrupa a numeração
TABELAS = {
    'extracao_trecho': 'ato_id, sigla_tipo_ato',
    'coordenada_extraida_trecho': 'auto_infracao_id',
}


def upgrade() -> None:
    op.drop_constraint(
        'uq_extracao_trecho_ato_id', 'extracao_trecho', type_='unique', schema=ESQUEMA
    )
    for tabela in TABELAS:
        op.drop_column(tabela, 'ordem', schema=ESQUEMA)


def downgrade() -> None:
    for tabela, grupo in TABELAS.items():
        op.add_column(
            tabela, sa.Column('ordem', sa.Integer(), nullable=True), schema=ESQUEMA
        )
        op.execute(
            sa.text(
                f"""
                UPDATE {ESQUEMA}.{tabela} AS t
                   SET ordem = n.ordem
                  FROM (
                        SELECT id,
                               row_number() OVER (
                                   PARTITION BY {grupo} ORDER BY id
                               ) AS ordem
                          FROM {ESQUEMA}.{tabela}
                       ) AS n
                 WHERE t.id = n.id
                """
            )
        )
        op.alter_column(
            tabela, 'ordem', existing_type=sa.Integer(), nullable=False, schema=ESQUEMA
        )
    op.create_unique_constraint(
        'uq_extracao_trecho_ato_id',
        'extracao_trecho',
        ['ato_id', 'sigla_tipo_ato', 'ordem'],
        schema=ESQUEMA,
    )
