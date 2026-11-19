"""renomeando o esquema dado_estruturado para auto_infracao

Revision ID: 9a3c5e7f2b18
Revises: 4b7e2d9c1a36
Create Date: 2026-11-19 13:00:00.000000

O esquema guarda os autos de infração extraídos dos atos e passa a ter o nome deles.
Tabelas, sequências, índices, constraints e dados vão junto com o esquema. O PostGIS
fica em ``public`` e não é afetado.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a3c5e7f2b18'
down_revision: Union[str, None] = '4b7e2d9c1a36'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text('ALTER SCHEMA dado_estruturado RENAME TO auto_infracao'))


def downgrade() -> None:
    op.execute(sa.text('ALTER SCHEMA auto_infracao RENAME TO dado_estruturado'))
