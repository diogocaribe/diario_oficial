"""adicionando a coluna divisao_adm_indireta

Revision ID: 59887b3ae575
Revises: 9e09149daa8d
Create Date: 2024-11-28 17:22:28.144032

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '59887b3ae575'
down_revision: Union[str, None] = '9e09149daa8d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('publicacao', sa.Column('divisao_adm_indireta_id', sa.Integer(), nullable=True), schema='processing')
    op.create_foreign_key(op.f('fk_publicacao_divisao_adm_indireta_id_divisao_adm_indireta'), 'publicacao', 'divisao_adm_indireta', ['divisao_adm_indireta_id'], ['id'], source_schema='processing', referent_schema='dominio')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(op.f('fk_publicacao_divisao_adm_indireta_id_divisao_adm_indireta'), 'publicacao', schema='processing', type_='foreignkey')
    op.drop_column('publicacao', 'divisao_adm_indireta_id', schema='processing')
    # ### end Alembic commands ###
