"""criando o esquema dado_estruturado com os autos de interdição extraídos

Revision ID: e36ed117ea37
Revises: 7b3d9e5a2c18
Create Date: 2026-11-18 12:00:00.000000

Precisa do PostGIS instalado no servidor (imagem postgis/postgis). O downgrade apaga o
esquema e deixa a extensão, que pode estar em uso por outras tabelas.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e36ed117ea37'
down_revision: Union[str, None] = '7b3d9e5a2c18'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ESQUEMA = 'dado_estruturado'
SRID = 4674


def upgrade() -> None:
    op.execute(sa.text('CREATE EXTENSION IF NOT EXISTS postgis'))
    op.execute(sa.text(f'CREATE SCHEMA IF NOT EXISTS {ESQUEMA}'))

    op.create_table(
        'extracao_trecho',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('ato_id', sa.Integer(), nullable=False),
        sa.Column(
            'sigla_tipo_ato',
            sa.Text(),
            nullable=False,
            comment='Sigla de dominio.tipo_ato da extração.',
        ),
        sa.Column('ordem', sa.Integer(), nullable=False),
        sa.Column('trecho', sa.Text(), nullable=False),
        sa.Column('erro', sa.Text(), nullable=True),
        sa.Column('modelo_llm', sa.Text(), nullable=True),
        sa.Column(
            'extraido_em',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['ato_id'],
            ['processing.ato.id'],
            name=op.f('fk_extracao_trecho_ato_id_ato'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_extracao_trecho_id')),
        sa.UniqueConstraint(
            'ato_id',
            'sigla_tipo_ato',
            'ordem',
            name=op.f('uq_extracao_trecho_ato_id'),
        ),
        schema=ESQUEMA,
    )
    op.create_index(
        op.f('ix_extracao_trecho_ato_id'),
        'extracao_trecho',
        ['ato_id'],
        schema=ESQUEMA,
    )

    op.create_table(
        'pessoa',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            'nome',
            sa.Text(),
            nullable=False,
            comment='Nome da primeira vez em que a pessoa apareceu.',
        ),
        sa.Column('tipo_documento', sa.Text(), nullable=True),
        sa.Column(
            'nro_documento',
            sa.Text(),
            nullable=True,
            comment='Só os dígitos, para CPF e CNPJ.',
        ),
        sa.CheckConstraint(
            "tipo_documento IN ('CPF', 'CNPJ', 'RG')",
            name=op.f('ck_pessoa_tipo_documento'),
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_pessoa_id')),
        schema=ESQUEMA,
    )
    op.create_index(
        'uq_pessoa_documento',
        'pessoa',
        ['tipo_documento', 'nro_documento'],
        unique=True,
        schema=ESQUEMA,
        postgresql_where=sa.text('nro_documento IS NOT NULL'),
    )

    op.create_table(
        'endereco',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        *[
            sa.Column(campo, sa.Text(), nullable=True)
            for campo in (
                'localidade',
                'logradouro',
                'numero',
                'complemento',
                'bairro',
                'rodovia',
                'cep',
                'municipio',
            )
        ],
        sa.PrimaryKeyConstraint('id', name=op.f('pk_endereco_id')),
        schema=ESQUEMA,
    )

    op.create_table(
        'auto_infracao',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('extracao_trecho_id', sa.Integer(), nullable=False),
        sa.Column(
            'ordem',
            sa.Integer(),
            nullable=False,
            comment='Posição do auto na resposta do modelo para o trecho.',
        ),
        sa.Column(
            'tipo_auto',
            sa.Text(),
            nullable=False,
            comment='Tabela da especialização (ex.: auto_interdicao).',
        ),
        sa.Column('nro_processo', sa.Text(), nullable=True),
        sa.Column('natureza', sa.Text(), nullable=False),
        sa.Column('resultado_recurso', sa.Text(), nullable=True),
        sa.Column('nro_ato_decisorio', sa.Text(), nullable=True),
        sa.Column('dt_homologacao', sa.Date(), nullable=True),
        sa.Column('conduta', sa.Text(), nullable=True),
        sa.Column('local_infracao_id', sa.Integer(), nullable=True),
        sa.Column('dt_constatacao', sa.Date(), nullable=True),
        sa.Column('hr_constatacao', sa.Time(), nullable=True),
        sa.Column(
            'sistema_referencia_espacial',
            sa.Text(),
            nullable=True,
            comment='Datum citado no texto; as geometrias estão em SIRGAS 2000.',
        ),
        sa.Column('area_hectare', sa.Numeric(), nullable=True),
        sa.Column('gravidade', sa.Text(), nullable=True),
        sa.Column(
            'nro_lacre',
            postgresql.ARRAY(sa.Text()),
            server_default='{}',
            nullable=False,
        ),
        sa.Column(
            'especie_citada',
            postgresql.ARRAY(sa.Text()),
            server_default='{}',
            nullable=False,
        ),
        sa.Column('autuado_id', sa.Integer(), nullable=False),
        sa.Column(
            'autuado_nome',
            sa.Text(),
            nullable=False,
            comment='Nome do autuado como está neste auto.',
        ),
        sa.Column('endereco_autuado_id', sa.Integer(), nullable=True),
        sa.Column(
            'ponto',
            Geometry('POINT', srid=SRID, spatial_index=False),
            nullable=True,
        ),
        sa.Column(
            'poligono',
            Geometry('POLYGON', srid=SRID, spatial_index=False),
            nullable=True,
        ),
        sa.CheckConstraint(
            "natureza IN ('homologacao', 'recurso', 'termo_de_compromisso', "
            "'sustacao', 'outro')",
            name=op.f('ck_auto_infracao_natureza'),
        ),
        sa.CheckConstraint(
            "resultado_recurso IN ('deferido', 'indeferido')",
            name=op.f('ck_auto_infracao_resultado_recurso'),
        ),
        sa.CheckConstraint(
            "gravidade IN ('leve', 'grave', 'gravissima')",
            name=op.f('ck_auto_infracao_gravidade'),
        ),
        sa.ForeignKeyConstraint(
            ['extracao_trecho_id'],
            [f'{ESQUEMA}.extracao_trecho.id'],
            name=op.f('fk_auto_infracao_extracao_trecho_id_extracao_trecho'),
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['local_infracao_id'],
            [f'{ESQUEMA}.endereco.id'],
            name=op.f('fk_auto_infracao_local_infracao_id_endereco'),
            ondelete='SET NULL',
        ),
        sa.ForeignKeyConstraint(
            ['endereco_autuado_id'],
            [f'{ESQUEMA}.endereco.id'],
            name=op.f('fk_auto_infracao_endereco_autuado_id_endereco'),
            ondelete='SET NULL',
        ),
        sa.ForeignKeyConstraint(
            ['autuado_id'],
            [f'{ESQUEMA}.pessoa.id'],
            name=op.f('fk_auto_infracao_autuado_id_pessoa'),
            ondelete='RESTRICT',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_auto_infracao_id')),
        schema=ESQUEMA,
    )
    for coluna in ('extracao_trecho_id', 'nro_processo', 'autuado_id'):
        op.create_index(
            op.f(f'ix_auto_infracao_{coluna}'),
            'auto_infracao',
            [coluna],
            schema=ESQUEMA,
        )
    for coluna in ('ponto', 'poligono'):
        op.create_index(
            f'ix_auto_infracao_{coluna}',
            'auto_infracao',
            [coluna],
            schema=ESQUEMA,
            postgresql_using='gist',
        )

    op.create_table(
        'auto_interdicao',
        sa.Column('auto_infracao_id', sa.Integer(), nullable=False),
        sa.Column('modalidade', sa.Text(), nullable=True),
        sa.Column('atividade_interditada', sa.Text(), nullable=True),
        sa.Column('excecao_interdicao', sa.Text(), nullable=True),
        sa.Column('condicao', sa.Text(), nullable=True),
        sa.CheckConstraint(
            "modalidade IN ('temporaria', 'definitiva')",
            name=op.f('ck_auto_interdicao_modalidade'),
        ),
        sa.ForeignKeyConstraint(
            ['auto_infracao_id'],
            [f'{ESQUEMA}.auto_infracao.id'],
            name=op.f('fk_auto_interdicao_auto_infracao_id_auto_infracao'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint(
            'auto_infracao_id', name=op.f('pk_auto_interdicao_auto_infracao_id')
        ),
        schema=ESQUEMA,
    )

    op.create_table(
        'coordenada',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('auto_infracao_id', sa.Integer(), nullable=False),
        sa.Column('ordem', sa.Integer(), nullable=False),
        sa.Column('latitude', sa.Text(), nullable=False),
        sa.Column('longitude', sa.Text(), nullable=False),
        sa.Column('fuso_utm', sa.Text(), nullable=True),
        sa.Column('tipo', sa.Text(), nullable=False),
        sa.CheckConstraint(
            "tipo IN ('ponto', 'vertice')", name=op.f('ck_coordenada_tipo')
        ),
        sa.ForeignKeyConstraint(
            ['auto_infracao_id'],
            [f'{ESQUEMA}.auto_infracao.id'],
            name=op.f('fk_coordenada_auto_infracao_id_auto_infracao'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_coordenada_id')),
        schema=ESQUEMA,
    )
    op.create_index(
        op.f('ix_coordenada_auto_infracao_id'),
        'coordenada',
        ['auto_infracao_id'],
        schema=ESQUEMA,
    )


def downgrade() -> None:
    op.execute(sa.text(f'DROP SCHEMA IF EXISTS {ESQUEMA} CASCADE'))
