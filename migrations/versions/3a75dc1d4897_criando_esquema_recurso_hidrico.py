"""criando o esquema recurso_hidrico das outorgas

Tabelas das outorgas de direito de uso de recursos hídricos extraídas dos atos (OUT,
ROUT, AOUT, AMOUT), espelhando ``extracao/modelo_outorga.py``: o trecho extraído, a
outorga, os usos (comum + lançamento e intervenção, herança joined-table), os pontos
(geometria em SIRGAS 2000), os parâmetros do efluente e o endereço da sede do
outorgado. O outorgado fica em ``public.pessoa``.

O endereço é da outorga, mas a FK fica na outorga: o trigger
``after_delete_apagar_endereco_da_outorga`` apaga o endereço quando a outorga é
apagada, inclusive em cascata (reprocessamento do ato ou do trecho). A pessoa
continua (FK RESTRICT), como nos autos de infração.

Revision ID: 3a75dc1d4897
Revises: f2b6d8a4c1e9
Create Date: 2026-11-23 17:26:34.250617

"""

from typing import Sequence, Union

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3a75dc1d4897'
down_revision: Union[str, None] = 'f2b6d8a4c1e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ESQUEMA = 'recurso_hidrico'


def upgrade() -> None:
    op.execute(sa.text('CREATE EXTENSION IF NOT EXISTS postgis'))
    op.execute(sa.text(f'CREATE SCHEMA IF NOT EXISTS {ESQUEMA}'))
    op.create_table(
        'endereco',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('localidade', sa.Text(), nullable=True),
        sa.Column('logradouro', sa.Text(), nullable=True),
        sa.Column('numero', sa.Text(), nullable=True),
        sa.Column('complemento', sa.Text(), nullable=True),
        sa.Column('bairro', sa.Text(), nullable=True),
        sa.Column('rodovia', sa.Text(), nullable=True),
        sa.Column('cep', sa.Text(), nullable=True),
        sa.Column('municipio', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_endereco_id')),
        schema='recurso_hidrico',
    )
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
        sa.Column('trecho', sa.Text(), nullable=False),
        sa.Column(
            'erro',
            sa.Text(),
            nullable=True,
            comment='Erro que impediu a extração do trecho.',
        ),
        sa.Column(
            'preenchido_pelo_modelo',
            postgresql.ARRAY(sa.Text()),
            server_default='{}',
            nullable=False,
            comment='Campos que a regex deixou vazios e o modelo preencheu.',
        ),
        sa.Column(
            'erro_modelo',
            sa.Text(),
            nullable=True,
            comment='Erro do modelo; os campos vazios da regex ficaram vazios.',
        ),
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
        schema='recurso_hidrico',
    )
    op.create_index(
        op.f('ix_extracao_trecho_ato_id'),
        'extracao_trecho',
        ['ato_id'],
        unique=False,
        schema='recurso_hidrico',
    )
    op.create_table(
        'outorga',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('extracao_trecho_id', sa.Integer(), nullable=False),
        sa.Column('natureza', sa.Text(), nullable=False),
        sa.Column(
            'nro_portaria',
            sa.Text(),
            nullable=True,
            comment='Número da portaria sem os pontos.',
        ),
        sa.Column('dt_portaria', sa.Date(), nullable=True),
        sa.Column('nro_processo', sa.Text(), nullable=True),
        sa.Column(
            'nro_processo_relacionado',
            sa.Text(),
            nullable=True,
            comment='Processo da outorga original (alteração e ampliação).',
        ),
        sa.Column(
            'outorgado_pessoa_id',
            sa.Integer(),
            nullable=True,
            comment='Pessoa outorgada, única pelo CPF/CNPJ; sem documento, uma por outorga.',
        ),
        sa.Column(
            'outorgado_nome',
            sa.Text(),
            nullable=True,
            comment='Nome do outorgado como está nesta portaria.',
        ),
        sa.Column(
            'endereco_outorgado_id',
            sa.Integer(),
            nullable=True,
            comment='Endereço da sede do outorgado nesta portaria.',
        ),
        sa.CheckConstraint(
            "natureza IN ('outorga', 'renovacao', 'alteracao', 'ampliacao')",
            name=op.f('ck_outorga_natureza'),
        ),
        sa.ForeignKeyConstraint(
            ['endereco_outorgado_id'],
            ['recurso_hidrico.endereco.id'],
            name=op.f('fk_outorga_endereco_outorgado_id_endereco'),
            ondelete='SET NULL',
        ),
        sa.ForeignKeyConstraint(
            ['extracao_trecho_id'],
            ['recurso_hidrico.extracao_trecho.id'],
            name=op.f('fk_outorga_extracao_trecho_id_extracao_trecho'),
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['outorgado_pessoa_id'],
            ['pessoa.id'],
            name=op.f('fk_outorga_outorgado_pessoa_id_pessoa'),
            ondelete='RESTRICT',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_outorga_id')),
        schema='recurso_hidrico',
    )
    op.create_index(
        op.f('ix_outorga_extracao_trecho_id'),
        'outorga',
        ['extracao_trecho_id'],
        unique=False,
        schema='recurso_hidrico',
    )
    op.create_index(
        op.f('ix_outorga_nro_portaria'),
        'outorga',
        ['nro_portaria'],
        unique=False,
        schema='recurso_hidrico',
    )
    op.create_index(
        op.f('ix_outorga_nro_processo'),
        'outorga',
        ['nro_processo'],
        unique=False,
        schema='recurso_hidrico',
    )
    op.create_index(
        op.f('ix_outorga_outorgado_pessoa_id'),
        'outorga',
        ['outorgado_pessoa_id'],
        unique=False,
        schema='recurso_hidrico',
    )
    op.create_table(
        'uso_recurso_hidrico',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('outorga_id', sa.Integer(), nullable=False),
        sa.Column(
            'tipo_uso',
            sa.Text(),
            nullable=False,
            comment='Especialização (uso_captacao, uso_lancamento...).',
        ),
        sa.Column('modo', sa.Text(), nullable=False),
        sa.Column('prazo_validade_anos', sa.Integer(), nullable=True),
        sa.Column(
            'dt_validade',
            sa.Date(),
            nullable=True,
            comment='Data final, quando o texto diz "válida até".',
        ),
        sa.Column(
            'nro_portaria_prazo',
            sa.Text(),
            nullable=True,
            comment='Portaria cujo prazo vale para este uso.',
        ),
        sa.Column('dt_publicacao_portaria_prazo', sa.Date(), nullable=True),
        sa.Column('bacia_hidrografica', sa.Text(), nullable=True),
        sa.Column('finalidade_texto', sa.Text(), nullable=True),
        sa.Column(
            'finalidades',
            postgresql.ARRAY(sa.Text()),
            server_default='{}',
            nullable=False,
        ),
        sa.Column(
            'metodos_irrigacao',
            postgresql.ARRAY(sa.Text()),
            server_default='{}',
            nullable=False,
        ),
        sa.Column('area_ha', sa.Numeric(), nullable=True),
        sa.Column('localidade', sa.Text(), nullable=True),
        sa.Column(
            'municipios',
            postgresql.ARRAY(sa.Text()),
            server_default='{}',
            nullable=False,
            comment='Municípios da Bahia onde fica o uso (nome oficial do IBGE).',
        ),
        sa.CheckConstraint(
            "finalidades <@ ARRAY['irrigacao', 'abastecimento_humano', 'abastecimento_industrial', 'dessedentacao_animal', 'comercio_servicos', 'aquicultura', 'mineracao', 'aproveitamento_hidreletrico', 'obra_infraestrutura', 'pulverizacao_agricola', 'combate_incendio', 'diluicao_efluente', 'barramento', 'canalizacao', 'dragagem', 'lazer', 'outro']::text[]",
            name=op.f('ck_uso_recurso_hidrico_finalidades'),
        ),
        sa.CheckConstraint(
            "metodos_irrigacao <@ ARRAY['gotejamento', 'microaspersao', 'pivo_central', 'aspersao_convencional', 'aspersao', 'autopropelido', 'caminhao_pipa', 'mangueira', 'superficie']::text[]",
            name=op.f('ck_uso_recurso_hidrico_metodos_irrigacao'),
        ),
        sa.CheckConstraint(
            "modo IN ('captacao_subterranea', 'captacao_superficial', 'lancamento_efluente', 'intervencao')",
            name=op.f('ck_uso_recurso_hidrico_modo'),
        ),
        sa.CheckConstraint(
            "tipo_uso IN ('uso_captacao', 'uso_lancamento', 'uso_intervencao')",
            name=op.f('ck_uso_recurso_hidrico_tipo_uso'),
        ),
        sa.CheckConstraint(
            "(tipo_uso = 'uso_captacao' AND modo IN ('captacao_subterranea', 'captacao_superficial')) OR (tipo_uso = 'uso_lancamento' AND modo = 'lancamento_efluente') OR (tipo_uso = 'uso_intervencao' AND modo = 'intervencao')",
            name=op.f('ck_uso_recurso_hidrico_modo_do_tipo_uso'),
        ),
        sa.ForeignKeyConstraint(
            ['outorga_id'],
            ['recurso_hidrico.outorga.id'],
            name=op.f('fk_uso_recurso_hidrico_outorga_id_outorga'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_uso_recurso_hidrico_id')),
        schema='recurso_hidrico',
    )
    op.create_index(
        op.f('ix_uso_recurso_hidrico_bacia_hidrografica'),
        'uso_recurso_hidrico',
        ['bacia_hidrografica'],
        unique=False,
        schema='recurso_hidrico',
    )
    op.create_index(
        op.f('ix_uso_recurso_hidrico_outorga_id'),
        'uso_recurso_hidrico',
        ['outorga_id'],
        unique=False,
        schema='recurso_hidrico',
    )
    op.create_table(
        'ponto_uso',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uso_recurso_hidrico_id', sa.Integer(), nullable=False),
        sa.Column('identificacao', sa.Text(), nullable=True),
        sa.Column('corpo_hidrico', sa.Text(), nullable=True),
        sa.Column('barramento', sa.Text(), nullable=True),
        sa.Column('barramento_dispensado', sa.Boolean(), nullable=False),
        sa.Column(
            'latitude', sa.Text(), nullable=True, comment='Latitude como está no texto.'
        ),
        sa.Column(
            'longitude',
            sa.Text(),
            nullable=True,
            comment='Longitude como está no texto.',
        ),
        sa.Column(
            'sistema_referencia_espacial',
            sa.Text(),
            nullable=True,
            comment='Datum citado no texto; o ponto está em SIRGAS 2000.',
        ),
        sa.Column('vazao_m3_dia', sa.Numeric(), nullable=True),
        sa.Column('vazao_m3_s', sa.Numeric(), nullable=True),
        sa.Column(
            'captacao_horas_dia',
            sa.Numeric(),
            nullable=True,
            comment='Horas de captação ou lançamento por dia.',
        ),
        sa.Column(
            'ponto',
            geoalchemy2.types.Geometry(
                geometry_type='POINT',
                srid=4674,
                dimension=2,
                spatial_index=False,
                from_text='ST_GeomFromEWKT',
                name='geometry',
            ),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ['uso_recurso_hidrico_id'],
            ['recurso_hidrico.uso_recurso_hidrico.id'],
            name=op.f('fk_ponto_uso_uso_recurso_hidrico_id_uso_recurso_hidrico'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_ponto_uso_id')),
        schema='recurso_hidrico',
    )
    op.create_index(
        'ix_ponto_uso_ponto',
        'ponto_uso',
        ['ponto'],
        unique=False,
        schema='recurso_hidrico',
        postgresql_using='gist',
    )
    op.create_index(
        op.f('ix_ponto_uso_uso_recurso_hidrico_id'),
        'ponto_uso',
        ['uso_recurso_hidrico_id'],
        unique=False,
        schema='recurso_hidrico',
    )
    op.create_table(
        'uso_intervencao',
        sa.Column('uso_recurso_hidrico_id', sa.Integer(), nullable=False),
        sa.Column('tipo_intervencao', sa.Text(), nullable=False),
        sa.Column('volume_maximo_acumulacao_m3', sa.Numeric(), nullable=True),
        sa.Column('altura_maxima_m', sa.Numeric(), nullable=True),
        sa.Column('vazao_minima_jusante_m3_dia', sa.Numeric(), nullable=True),
        sa.Column('vazao_minima_jusante_m3_s', sa.Numeric(), nullable=True),
        sa.Column('descarga_de_fundo', sa.Boolean(), nullable=False),
        sa.Column('vazao_projeto_m3_dia', sa.Numeric(), nullable=True),
        sa.Column('vazao_projeto_m3_s', sa.Numeric(), nullable=True),
        sa.Column('extensao_m', sa.Numeric(), nullable=True),
        sa.Column('largura_m', sa.Numeric(), nullable=True),
        sa.Column('comprimento_m', sa.Numeric(), nullable=True),
        sa.CheckConstraint(
            "tipo_intervencao IN ('regularizacao_barramento', 'construcao_barramento', 'canalizacao', 'travessia', 'aproveitamento_hidreletrico', 'extracao_mineral_dragagem', 'outro')",
            name=op.f('ck_uso_intervencao_tipo_intervencao'),
        ),
        sa.ForeignKeyConstraint(
            ['uso_recurso_hidrico_id'],
            ['recurso_hidrico.uso_recurso_hidrico.id'],
            name=op.f('fk_uso_intervencao_uso_recurso_hidrico_id_uso_recurso_hidrico'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint(
            'uso_recurso_hidrico_id',
            name=op.f('pk_uso_intervencao_uso_recurso_hidrico_id'),
        ),
        schema='recurso_hidrico',
    )
    op.create_table(
        'uso_lancamento',
        sa.Column('uso_recurso_hidrico_id', sa.Integer(), nullable=False),
        sa.Column('vazao_diluicao_m3_dia', sa.Numeric(), nullable=True),
        sa.Column('vazao_diluicao_m3_s', sa.Numeric(), nullable=True),
        sa.ForeignKeyConstraint(
            ['uso_recurso_hidrico_id'],
            ['recurso_hidrico.uso_recurso_hidrico.id'],
            name=op.f('fk_uso_lancamento_uso_recurso_hidrico_id_uso_recurso_hidrico'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint(
            'uso_recurso_hidrico_id',
            name=op.f('pk_uso_lancamento_uso_recurso_hidrico_id'),
        ),
        schema='recurso_hidrico',
    )
    op.create_table(
        'parametro_efluente',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uso_lancamento_id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.Text(), nullable=False),
        sa.Column('valor', sa.Text(), nullable=False, comment='Como no texto.'),
        sa.Column('unidade', sa.Text(), nullable=False),
        sa.Column(
            'valor_numero',
            sa.Numeric(),
            nullable=True,
            comment='O valor como número (1,8 x 10² -> 180).',
        ),
        sa.ForeignKeyConstraint(
            ['uso_lancamento_id'],
            ['recurso_hidrico.uso_lancamento.uso_recurso_hidrico_id'],
            name=op.f('fk_parametro_efluente_uso_lancamento_id_uso_lancamento'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_parametro_efluente_id')),
        schema='recurso_hidrico',
    )
    op.create_index(
        op.f('ix_parametro_efluente_uso_lancamento_id'),
        'parametro_efluente',
        ['uso_lancamento_id'],
        unique=False,
        schema='recurso_hidrico',
    )

    op.execute(
        sa.text(f"""
        CREATE OR REPLACE FUNCTION {ESQUEMA}.apagar_endereco_da_outorga()
        RETURNS TRIGGER AS $$
        BEGIN
            DELETE FROM {ESQUEMA}.endereco e WHERE e.id = OLD.endereco_outorgado_id;
            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql;
    """)
    )
    op.execute(
        sa.text(f"""
        CREATE TRIGGER after_delete_apagar_endereco_da_outorga
        AFTER DELETE ON {ESQUEMA}.outorga
        FOR EACH ROW
        EXECUTE FUNCTION {ESQUEMA}.apagar_endereco_da_outorga();
    """)
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            f'DROP TRIGGER after_delete_apagar_endereco_da_outorga ON {ESQUEMA}.outorga;'
        )
    )
    op.execute(sa.text(f'DROP FUNCTION {ESQUEMA}.apagar_endereco_da_outorga();'))
    op.drop_index(
        op.f('ix_parametro_efluente_uso_lancamento_id'),
        table_name='parametro_efluente',
        schema='recurso_hidrico',
    )
    op.drop_table('parametro_efluente', schema='recurso_hidrico')
    op.drop_table('uso_lancamento', schema='recurso_hidrico')
    op.drop_table('uso_intervencao', schema='recurso_hidrico')
    op.drop_index(
        op.f('ix_ponto_uso_uso_recurso_hidrico_id'),
        table_name='ponto_uso',
        schema='recurso_hidrico',
    )
    op.drop_index(
        'ix_ponto_uso_ponto',
        table_name='ponto_uso',
        schema='recurso_hidrico',
        postgresql_using='gist',
    )
    op.drop_table('ponto_uso', schema='recurso_hidrico')
    op.drop_index(
        op.f('ix_uso_recurso_hidrico_outorga_id'),
        table_name='uso_recurso_hidrico',
        schema='recurso_hidrico',
    )
    op.drop_index(
        op.f('ix_uso_recurso_hidrico_bacia_hidrografica'),
        table_name='uso_recurso_hidrico',
        schema='recurso_hidrico',
    )
    op.drop_table('uso_recurso_hidrico', schema='recurso_hidrico')
    op.drop_index(
        op.f('ix_outorga_outorgado_pessoa_id'),
        table_name='outorga',
        schema='recurso_hidrico',
    )
    op.drop_index(
        op.f('ix_outorga_nro_processo'), table_name='outorga', schema='recurso_hidrico'
    )
    op.drop_index(
        op.f('ix_outorga_nro_portaria'), table_name='outorga', schema='recurso_hidrico'
    )
    op.drop_index(
        op.f('ix_outorga_extracao_trecho_id'),
        table_name='outorga',
        schema='recurso_hidrico',
    )
    op.drop_table('outorga', schema='recurso_hidrico')
    op.drop_index(
        op.f('ix_extracao_trecho_ato_id'),
        table_name='extracao_trecho',
        schema='recurso_hidrico',
    )
    op.drop_table('extracao_trecho', schema='recurso_hidrico')
    op.drop_table('endereco', schema='recurso_hidrico')
    # A extensão PostGIS fica: o esquema auto_infracao também a usa.
    op.execute(sa.text(f'DROP SCHEMA IF EXISTS {ESQUEMA}'))
