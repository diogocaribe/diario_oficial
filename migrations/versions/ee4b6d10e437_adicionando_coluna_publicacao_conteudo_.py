"""adicionando coluna publicacao.conteudo_link

Revision ID: ee4b6d10e437
Revises: 7ece6d16d3bc
Create Date: 2024-09-09 13:24:23.496378

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ee4b6d10e437'
down_revision: Union[str, None] = '7ece6d16d3bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('publicacao', sa.Column('conteudo_link', sa.String(), nullable=True), schema='processing')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('publicacao', 'conteudo_link', schema='processing')
    # ### end Alembic commands ###