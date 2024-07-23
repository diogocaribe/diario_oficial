"""adicionando sequancial na chave primaria

Revision ID: 14532f35de43
Revises: 1962557f0efd
Create Date: 2024-07-23 15:52:00.000208

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '14532f35de43'
down_revision: Union[str, None] = '1962557f0efd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
