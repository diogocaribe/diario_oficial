"""criando as tabelas dos subtipos de auto de infração

Revision ID: 03079842dad8
Revises: c8f2a61d4e09
Create Date: 2026-11-19 10:41:24.292651

Uma tabela por subtipo (multa, advertência, apreensão, embargo, demolição, destruição
de fornos e de produtos), com as colunas próprias do subtipo e a PK igual à de
``auto_infracao`` (herança joined-table, como ``auto_interdicao``). Os bens apreendidos
(AIAP) e os produtos destruídos (AIDP) ficam em ``bem_produto_autuado``, ligados ao auto.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '03079842dad8'
down_revision: Union[str, None] = 'c8f2a61d4e09'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'auto_advertencia',
        sa.Column('auto_infracao_id', sa.Integer(), nullable=False),
        sa.Column('exigencia', sa.Text(), nullable=True),
        sa.Column('prazo_atendimento_dias', sa.Integer(), nullable=True),
        sa.Column('nro_notificacao', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ['auto_infracao_id'],
            ['dado_estruturado.auto_infracao.id'],
            name=op.f('fk_auto_advertencia_auto_infracao_id_auto_infracao'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint(
            'auto_infracao_id', name=op.f('pk_auto_advertencia_auto_infracao_id')
        ),
        schema='dado_estruturado',
    )
    op.create_table(
        'auto_apreensao',
        sa.Column('auto_infracao_id', sa.Integer(), nullable=False),
        sa.Column('fiel_depositario', sa.Text(), nullable=True),
        sa.Column('destinacao', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ['auto_infracao_id'],
            ['dado_estruturado.auto_infracao.id'],
            name=op.f('fk_auto_apreensao_auto_infracao_id_auto_infracao'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint(
            'auto_infracao_id', name=op.f('pk_auto_apreensao_auto_infracao_id')
        ),
        schema='dado_estruturado',
    )
    op.create_table(
        'auto_demolicao',
        sa.Column('auto_infracao_id', sa.Integer(), nullable=False),
        sa.Column(
            'obra_demolida',
            postgresql.ARRAY(sa.Text()),
            server_default='{}',
            nullable=False,
        ),
        sa.Column('area_restricao_legal_uso', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ['auto_infracao_id'],
            ['dado_estruturado.auto_infracao.id'],
            name=op.f('fk_auto_demolicao_auto_infracao_id_auto_infracao'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint(
            'auto_infracao_id', name=op.f('pk_auto_demolicao_auto_infracao_id')
        ),
        schema='dado_estruturado',
    )
    op.create_table(
        'auto_destruicao_fornos',
        sa.Column('auto_infracao_id', sa.Integer(), nullable=False),
        sa.Column('qtd_fornos', sa.Integer(), nullable=True),
        sa.Column('tipo_forno', sa.Text(), nullable=True),
        sa.Column('capacidade_por_forno', sa.Numeric(), nullable=True),
        sa.Column('situacao_forno', sa.Text(), nullable=True),
        sa.CheckConstraint(
            "situacao_forno IN ('ativo', 'inativo')",
            name=op.f('ck_auto_destruicao_fornos_situacao_forno'),
        ),
        sa.ForeignKeyConstraint(
            ['auto_infracao_id'],
            ['dado_estruturado.auto_infracao.id'],
            name=op.f('fk_auto_destruicao_fornos_auto_infracao_id_auto_infracao'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint(
            'auto_infracao_id', name=op.f('pk_auto_destruicao_fornos_auto_infracao_id')
        ),
        schema='dado_estruturado',
    )
    op.create_table(
        'auto_destruicao_produtos',
        sa.Column('auto_infracao_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['auto_infracao_id'],
            ['dado_estruturado.auto_infracao.id'],
            name=op.f('fk_auto_destruicao_produtos_auto_infracao_id_auto_infracao'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint(
            'auto_infracao_id',
            name=op.f('pk_auto_destruicao_produtos_auto_infracao_id'),
        ),
        schema='dado_estruturado',
    )
    op.create_table(
        'auto_embargo',
        sa.Column('auto_infracao_id', sa.Integer(), nullable=False),
        sa.Column('modalidade', sa.Text(), nullable=True),
        sa.Column('objeto_embargado', sa.Text(), nullable=True),
        sa.Column('area_restricao_legal_uso', sa.Text(), nullable=True),
        sa.CheckConstraint(
            "modalidade IN ('temporario', 'definitivo')",
            name=op.f('ck_auto_embargo_modalidade'),
        ),
        sa.ForeignKeyConstraint(
            ['auto_infracao_id'],
            ['dado_estruturado.auto_infracao.id'],
            name=op.f('fk_auto_embargo_auto_infracao_id_auto_infracao'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint(
            'auto_infracao_id', name=op.f('pk_auto_embargo_auto_infracao_id')
        ),
        schema='dado_estruturado',
    )
    op.create_table(
        'auto_multa',
        sa.Column('auto_infracao_id', sa.Integer(), nullable=False),
        sa.Column('valor_multa', sa.Numeric(), nullable=True),
        sa.Column('tipo_multa', sa.Text(), nullable=True),
        sa.Column('reincidente', sa.Boolean(), nullable=False),
        sa.Column('percentual_desconto', sa.Numeric(), nullable=True),
        sa.Column('nro_notificacao', sa.Text(), nullable=True),
        sa.CheckConstraint(
            "tipo_multa IN ('simples', 'diaria')", name=op.f('ck_auto_multa_tipo_multa')
        ),
        sa.ForeignKeyConstraint(
            ['auto_infracao_id'],
            ['dado_estruturado.auto_infracao.id'],
            name=op.f('fk_auto_multa_auto_infracao_id_auto_infracao'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint(
            'auto_infracao_id', name=op.f('pk_auto_multa_auto_infracao_id')
        ),
        schema='dado_estruturado',
    )
    op.create_table(
        'bem_produto_autuado',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('auto_infracao_id', sa.Integer(), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=False),
        sa.Column('quantidade', sa.Numeric(), nullable=True),
        sa.Column('unidade', sa.Text(), nullable=True),
        sa.Column('valor_avaliado', sa.Numeric(), nullable=True),
        sa.Column('identificacao', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ['auto_infracao_id'],
            ['dado_estruturado.auto_infracao.id'],
            name=op.f('fk_bem_produto_autuado_auto_infracao_id_auto_infracao'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_bem_produto_autuado_id')),
        schema='dado_estruturado',
    )
    op.create_index(
        op.f('ix_bem_produto_autuado_auto_infracao_id'),
        'bem_produto_autuado',
        ['auto_infracao_id'],
        unique=False,
        schema='dado_estruturado',
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_bem_produto_autuado_auto_infracao_id'),
        table_name='bem_produto_autuado',
        schema='dado_estruturado',
    )
    op.drop_table('bem_produto_autuado', schema='dado_estruturado')
    op.drop_table('auto_multa', schema='dado_estruturado')
    op.drop_table('auto_embargo', schema='dado_estruturado')
    op.drop_table('auto_destruicao_produtos', schema='dado_estruturado')
    op.drop_table('auto_destruicao_fornos', schema='dado_estruturado')
    op.drop_table('auto_demolicao', schema='dado_estruturado')
    op.drop_table('auto_apreensao', schema='dado_estruturado')
    op.drop_table('auto_advertencia', schema='dado_estruturado')
