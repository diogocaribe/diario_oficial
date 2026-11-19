"""renomeando a tabela coordenada para coordenada_extraida_trecho

Revision ID: 4b7e2d9c1a36
Revises: 03079842dad8
Create Date: 2026-11-19 12:00:00.000000

O nome deixa claro que os pares são os copiados do trecho do auto, como estão no
texto, e não a geometria convertida (``auto_infracao.ponto`` e ``poligono``). A
sequência, o índice e as constraints são renomeados junto, para seguir a
``naming_convention`` do ``Base``.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4b7e2d9c1a36'
down_revision: Union[str, None] = '03079842dad8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ESQUEMA = 'dado_estruturado'

NOMES = [
    ('TABLE', 'coordenada', 'coordenada_extraida_trecho'),
    ('SEQUENCE', 'coordenada_id_seq', 'coordenada_extraida_trecho_id_seq'),
    (
        'INDEX',
        'ix_coordenada_auto_infracao_id',
        'ix_coordenada_extraida_trecho_auto_infracao_id',
    ),
]

CONSTRAINTS = [
    ('pk_coordenada_id', 'pk_coordenada_extraida_trecho_id'),
    (
        'fk_coordenada_auto_infracao_id_auto_infracao',
        'fk_coordenada_extraida_trecho_auto_infracao_id_auto_infracao',
    ),
    ('ck_coordenada_tipo', 'ck_coordenada_extraida_trecho_tipo'),
]


def _renomear(tabela: str, nomes: list, constraints: list) -> None:
    for tipo, antigo, novo in nomes:
        op.execute(sa.text(f'ALTER {tipo} {ESQUEMA}.{antigo} RENAME TO {novo}'))
    for antigo, novo in constraints:
        op.execute(
            sa.text(
                f'ALTER TABLE {ESQUEMA}.{tabela} RENAME CONSTRAINT {antigo} TO {novo}'
            )
        )


def upgrade() -> None:
    _renomear('coordenada_extraida_trecho', NOMES, CONSTRAINTS)


def downgrade() -> None:
    _renomear(
        'coordenada',
        [(tipo, novo, antigo) for tipo, antigo, novo in NOMES],
        [(novo, antigo) for antigo, novo in CONSTRAINTS],
    )
