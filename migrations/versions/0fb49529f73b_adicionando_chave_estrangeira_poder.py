"""adicionando chave estrangeira poder

Revision ID: 0fb49529f73b
Revises: 6bdd57e019e5
Create Date: 2024-08-07 16:21:58.425771

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0fb49529f73b'
down_revision: Union[str, None] = '6bdd57e019e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('ato_bruto', sa.Column('poder_id', sa.Integer(), nullable=False), schema='processing')
    op.create_foreign_key(None, 'ato_bruto', 'poder', ['poder_id'], ['id'], source_schema='processing', referent_schema='dominio')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'ato_bruto', schema='processing', type_='foreignkey')
    op.drop_column('ato_bruto', 'poder_id', schema='processing')
    # ### end Alembic commands ###