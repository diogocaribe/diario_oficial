"""testando...

Revision ID: 65829fb284d8
Revises: 5500522d8e72
Create Date: 2024-08-06 18:21:54.692074

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '65829fb284d8'
down_revision: Union[str, None] = '5500522d8e72'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('diario_oficial_bruto', schema='processing')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('diario_oficial_bruto',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('diario_oficial_json', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=True),
    sa.Column('data', sa.DATE(), autoincrement=False, nullable=True),
    sa.Column('edicao', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('exist', sa.BOOLEAN(), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name='diario_oficial_bruto_pkey'),
    schema='processing'
    )
    # ### end Alembic commands ###
