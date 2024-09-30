"""testando o modelo ato

Revision ID: ef212d42ad21
Revises: ee4b6d10e437
Create Date: 2024-09-28 12:05:33.535847

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ef212d42ad21'
down_revision: Union[str, None] = 'ee4b6d10e437'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        'ato',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('publicacao_id', sa.Integer(), nullable=False),
        sa.Column('conteudo_ato', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ['publicacao_id'],
            ['processing.publicacao.id'],
            name=op.f('fk_ato_publicacao_id_publicacao'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_ato_id')),
        schema='processing',
    )
    op.create_index(op.f('ix_ato_id'), 'ato', ['id'], unique=False, schema='processing')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_ato_id'), table_name='ato', schema='processing')
    op.drop_table('ato', schema='processing')
    # ### end Alembic commands ###
