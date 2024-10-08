"""adicionando tipo_publicacao

Revision ID: 7d3010a8ea8c
Revises: 36e27a825a91
Create Date: 2024-09-04 10:30:20.991410

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7d3010a8ea8c'
down_revision: Union[str, None] = '36e27a825a91'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        'tipo_publicacao',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('nome', sa.String(), nullable=True),
        sa.Column('sigla', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_tipo_publicacao_id')),
        sa.UniqueConstraint('nome', name=op.f('uq_tipo_publicacao_nome')),
        schema='dominio',
    )
    op.create_index(
        op.f('ix_tipo_publicacao_id'), 'tipo_publicacao', ['id'], unique=False, schema='dominio'
    )
    op.drop_index('ix_ato_id', table_name='ato', schema='dominio')
    op.drop_table('ato', schema='dominio')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        'ato',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('nome', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('sigla', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint('id', name='pk_ato_id'),
        sa.UniqueConstraint('nome', name='uq_ato_nome'),
        schema='dominio',
    )
    op.create_index('ix_ato_id', 'ato', ['id'], unique=False, schema='dominio')
    op.drop_index(op.f('ix_tipo_publicacao_id'), table_name='tipo_publicacao', schema='dominio')
    op.drop_table('tipo_publicacao', schema='dominio')
    # ### end Alembic commands ###
