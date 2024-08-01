"""diorio_oficial_json nullable=true

Revision ID: 7aa9a8934b04
Revises: f7c28b13095d
Create Date: 2024-07-24 18:49:16.645823

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7aa9a8934b04'
down_revision: Union[str, None] = 'f7c28b13095d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('diario_oficial_bruto', 'diario_oficial_json',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               nullable=True,
               schema='processing')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('diario_oficial_bruto', 'diario_oficial_json',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               nullable=False,
               schema='processing')
    # ### end Alembic commands ###