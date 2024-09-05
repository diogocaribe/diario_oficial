"""iniciando banco

Revision ID: dfae75d03e16
Revises: 
Create Date: 2024-09-02 16:50:48.562355

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'dfae75d03e16'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Adicionando os schemas
    op.execute(sa.text('CREATE SCHEMA IF NOT EXISTS processing'))
    op.execute(sa.text('CREATE SCHEMA IF NOT EXISTS dominio'))
    
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('adm_direta',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('nome', sa.String(), nullable=False),
    sa.Column('sigla', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_adm_direta_id')),
    sa.UniqueConstraint('nome', name=op.f('uq_adm_direta_nome')),
    schema='dominio'
    )
    op.create_index(op.f('ix_adm_direta_id'), 'adm_direta', ['id'], unique=False, schema='dominio')
    op.create_table('adm_indireta',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('nome', sa.String(), nullable=False),
    sa.Column('sigla', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_adm_indireta_id')),
    sa.UniqueConstraint('nome', name=op.f('uq_adm_indireta_nome')),
    schema='dominio'
    )
    op.create_index(op.f('ix_adm_indireta_id'), 'adm_indireta', ['id'], unique=False, schema='dominio')
    op.create_table('divisao_adm_direta',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('nome', sa.String(), nullable=False),
    sa.Column('sigla', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_divisao_adm_direta_id')),
    sa.UniqueConstraint('nome', name=op.f('uq_divisao_adm_direta_nome')),
    schema='dominio'
    )
    op.create_index(op.f('ix_divisao_adm_direta_id'), 'divisao_adm_direta', ['id'], unique=False, schema='dominio')
    op.create_table('poder',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('nome', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_poder_id')),
    sa.UniqueConstraint('nome', name=op.f('uq_poder_nome')),
    schema='dominio'
    )
    op.create_index(op.f('ix_poder_id'), 'poder', ['id'], unique=False, schema='dominio')
    op.create_table('doe_bruto',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('criado_em', sa.DateTime(), server_default=sa.text('now()'), nullable=False, comment='Data e horario da coleta desse registro.'),
    sa.Column('nro_edicao', sa.Integer(), nullable=True, comment='Edição do DOE coletado.'),
    sa.Column('dt_edicao', sa.Date(), nullable=True, comment='Data do DOE coletado.'),
    sa.Column('existe', sa.Boolean(), nullable=False, comment='Se existe ou não publicação do DOE na data solicitada.'),
    sa.Column('doe_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Dados extraídos do DOE em formato json.'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_doe_bruto_id')),
    sa.UniqueConstraint('dt_edicao', name=op.f('uq_doe_bruto_dt_edicao')),
    sa.UniqueConstraint('nro_edicao', name=op.f('uq_doe_bruto_nro_edicao')),
    schema='processing'
    )
    op.create_index(op.f('ix_doe_bruto_id'), 'doe_bruto', ['id'], unique=False, schema='processing')
    op.create_table('publicacao',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('doe_nro_edicao', sa.Integer(), nullable=False),
    sa.Column('poder_id', sa.Integer(), nullable=False),
    sa.Column('adm_direta_id', sa.Integer(), nullable=False),
    sa.Column('adm_indireta_id', sa.Integer(), nullable=False),
    sa.Column('divisao_adm_direta_id', sa.Integer(), nullable=False),
    sa.Column('nome_ato', sa.String(), nullable=False),
    sa.Column('identificador_link', sa.String(), nullable=False),
    sa.Column('link', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['adm_direta_id'], ['dominio.adm_direta.id'], name=op.f('fk_publicacao_adm_direta_id_adm_direta')),
    sa.ForeignKeyConstraint(['adm_indireta_id'], ['dominio.adm_indireta.id'], name=op.f('fk_publicacao_adm_indireta_id_adm_indireta')),
    sa.ForeignKeyConstraint(['divisao_adm_direta_id'], ['dominio.divisao_adm_direta.id'], name=op.f('fk_publicacao_divisao_adm_direta_id_divisao_adm_direta')),
    sa.ForeignKeyConstraint(['doe_nro_edicao'], ['processing.doe_bruto.nro_edicao'], name=op.f('fk_publicacao_doe_nro_edicao_doe_bruto')),
    sa.ForeignKeyConstraint(['poder_id'], ['dominio.poder.id'], name=op.f('fk_publicacao_poder_id_poder')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_publicacao_id')),
    schema='processing'
    )
    op.create_index(op.f('ix_publicacao_id'), 'publicacao', ['id'], unique=False, schema='processing')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_publicacao_id'), table_name='publicacao', schema='processing')
    op.drop_table('publicacao', schema='processing')
    op.drop_index(op.f('ix_doe_bruto_id'), table_name='doe_bruto', schema='processing')
    op.drop_table('doe_bruto', schema='processing')
    op.drop_index(op.f('ix_poder_id'), table_name='poder', schema='dominio')
    op.drop_table('poder', schema='dominio')
    op.drop_index(op.f('ix_divisao_adm_direta_id'), table_name='divisao_adm_direta', schema='dominio')
    op.drop_table('divisao_adm_direta', schema='dominio')
    op.drop_index(op.f('ix_adm_indireta_id'), table_name='adm_indireta', schema='dominio')
    op.drop_table('adm_indireta', schema='dominio')
    op.drop_index(op.f('ix_adm_direta_id'), table_name='adm_direta', schema='dominio')
    op.drop_table('adm_direta', schema='dominio')
    # ### end Alembic commands ###
