"""mudando o nome da coluna

Revision ID: ef8d543771cb
Revises: 7f0fcc2b350b
Create Date: 2024-09-02 14:27:15.194356

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ef8d543771cb'
down_revision: Union[str, None] = '7f0fcc2b350b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        'publicacao',
        sa.Column('divisao_adm_direta_id', sa.Integer(), nullable=False),
        schema='processing',
    )
    op.drop_constraint(
        'fk_publicacao_orgao_adm_indireta_id_orgao_adm_indireta',
        'publicacao',
        schema='processing',
        type_='foreignkey',
    )
    op.create_foreign_key(
        op.f('fk_publicacao_divisao_adm_direta_id_orgao_adm_indireta'),
        'publicacao',
        'orgao_adm_indireta',
        ['divisao_adm_direta_id'],
        ['id'],
        source_schema='processing',
        referent_schema='dominio',
    )
    op.drop_column('publicacao', 'orgao_adm_indireta_id', schema='processing')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        'publicacao',
        sa.Column('orgao_adm_indireta_id', sa.INTEGER(), autoincrement=False, nullable=False),
        schema='processing',
    )
    op.drop_constraint(
        op.f('fk_publicacao_divisao_adm_direta_id_orgao_adm_indireta'),
        'publicacao',
        schema='processing',
        type_='foreignkey',
    )
    op.create_foreign_key(
        'fk_publicacao_orgao_adm_indireta_id_orgao_adm_indireta',
        'publicacao',
        'orgao_adm_indireta',
        ['orgao_adm_indireta_id'],
        ['id'],
        source_schema='processing',
        referent_schema='dominio',
    )
    op.drop_column('publicacao', 'divisao_adm_direta_id', schema='processing')
    # ### end Alembic commands ###