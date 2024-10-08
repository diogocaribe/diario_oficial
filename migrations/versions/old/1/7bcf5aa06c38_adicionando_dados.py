"""Adicionando dados

Revision ID: 7bcf5aa06c38
Revises: 9745a934e2fc
Create Date: 2024-09-01 11:09:32.236383

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from diario_oficial.database.configs.connection import DBConnectionHandler
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '7bcf5aa06c38'
down_revision: Union[str, None] = '9745a934e2fc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(text('CREATE SCHEMA IF NOT EXISTS dominio'))

    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        'poder',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('nome', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_poder_id')),
        sa.UniqueConstraint('nome', name=op.f('uq_poder_nome')),
        schema='dominio',
    )
    op.create_index(op.f('ix_poder_id'), 'poder', ['id'], unique=False, schema='dominio')
    op.add_column(
        'publicacao', sa.Column('poder_id', sa.Integer(), nullable=False), schema='processing'
    )
    op.create_foreign_key(
        op.f('fk_publicacao_poder_id_poder'),
        'publicacao',
        'poder',
        ['poder_id'],
        ['id'],
        source_schema='processing',
        referent_schema='dominio',
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(
        op.f('fk_publicacao_poder_id_poder'), 'publicacao', schema='processing', type_='foreignkey'
    )
    op.drop_column('publicacao', 'poder_id', schema='processing')
    op.drop_index(op.f('ix_poder_id'), table_name='poder', schema='dominio')
    op.drop_table('poder', schema='dominio')
    # ### end Alembic commands ###
