"""criando tipo_ato e ato_tipo_ato

Revision ID: 4e8a2f6b1c37
Revises: c4e8a1f07d32
Create Date: 2026-11-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e8a2f6b1c37'
down_revision: Union[str, None] = 'c4e8a1f07d32'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# A sigla não é única: a lista de origem repete PPV/AA e RPPN em nomes diferentes.
TIPOS_ATO = [
    ('Outorga de Direito de Uso de Recurso Hídrico', 'OUT'),
    ('Licença de Operação', 'LO'),
    ('Alteração de Licenciamentos', None),
    ('Transferência de Titularidade', 'TLA'),
    ('Renovação de Outorga de Direito de Uso de Recurso Hídrico', 'ROUT'),
    ('Licença Unificada', 'LU'),
    ('Autorização de Supressão de Vegetação Nativa', 'ASV'),
    ('Autorização Ambiental', 'AA'),
    ('Alteração de Outorga de Direito de Uso de Recurso Hídrico', 'AOUT'),
    ('Licença Prévia', 'LP'),
    ('Licença de Instalação', 'LI'),
    ('Cancelamento de Outorga', 'COUT'),
    ('Aprovação da Exploração ou Corte de Florestas Plantadas', 'ACFP'),
    ('Alteração de Razão Social', 'ALRS'),
    ('Renovação de Licença de Operação', 'RLO'),
    ('Prorrogação do Prazo de Validade de Licença de Instalação', 'PPV/LI'),
    ('Criação de Reserva Particular do Patrimônio Natural', 'RPPN'),
    ('Reconhecimento de Reserva Particular do Patrimônio Natural', 'RPPN'),
    ('Autorização para Realização de Atividade Didática', 'AAD'),
    ('Suspensão de Ato Autorizativo', None),
    (
        'Prorrogação do Prazo de Validade de Autorização para Realização de Pesquisa '
        'Científica',
        'PPV/ARPC',
    ),
    ('Cancelamento de Outros Atos', None),
    (
        'Prorrogação do Prazo de Validade de Autorização de Supressão de Vegetação '
        'Nativa',
        'PPV/ASV',
    ),
    ('Aproveitamento de Material Lenhoso', 'AML'),
    ('Revisão de Condicionante', 'RC'),
    ('Licença Prévia Concomitantemente com Licença de Instalação', None),
    ('Renovação de Licença Prévia', 'RLP'),
    ('Anuência Prévia', 'AP'),
    ('Licença de Regularização', 'LR'),
    ('Renovação de Licença Unificada', 'RLU'),
    ('Prorrogação do Prazo de Validade de Licença de Alteração', 'PPV/LA'),
    ('Cancelamento, Revogação ou Suspensão de Portarias', None),
    ('Autorização para Realização de Pesquisa Científica', 'ARPC'),
    (
        'Aprovação da Execução das Etapas do Plano de Manejo Florestal Sustentável',
        'EPMF',
    ),
    ('Aprovação do Termo de Referência', 'ATR'),
    ('Prorrogação do Prazo de Validade de Autorização Ambiental', 'PPV/AA'),
    ('Exclusão de Condicionante', 'EC'),
    ('Renovação de Licenciamentos', None),
    ('Transferência de Crédito de Volume Florestal', 'TCVF'),
    ('Renovação ou Alteração de Outorga', None),
    ('Autorização de Manejo de Fauna', 'AMF'),
    ('Reconhecimento de Volume Florestal Remanescente', 'RVFR'),
    ('Prorrogação do Prazo de Validade de Licença Prévia', 'PPV/LP'),
    ('Ampliação de Outorga de Direito de Uso de Recurso Hídrico', 'AMOUT'),
    ('Emissão de Crédito de Volume Florestal', 'ECVF'),
    (
        'Prorrogação do Prazo de Validade de Aprovação da Execução das Etapas do '
        'Plano de Manejo Florestal Sustentável',
        'PPV/EPMF',
    ),
    ('Prorrogação do Prazo de Validade de Licença de Localização', 'PPV/LLO'),
    ('Licença de Alteração', 'LA'),
    ('Prorrogação do Prazo de Validade de Licença Unificada', 'PPV/LU'),
    ('Transferência de Crédito de Reposição Florestal', 'TCRF'),
    ('Outorga Preventiva de Uso de Recurso Hídrico', 'OUTP'),
    ('Licença Simplificada', 'LS'),
    ('Aprovação de Plano de Manejo Florestal Sustentável', 'APMF'),
    ('Prorrogação do Prazo de Validade de Licença de Implantação', 'PPV/LIP'),
    ('Prorrogação do Prazo de Validade de Autorização', 'PPV/AA'),
    ('Licença Prévia de Operação', 'LPO'),
    ('Autorização de Manejo da Cabruca', None),
    ('Prorrogação do Prazo de Validade de Outorga', 'PPV/OUT'),
    ('Prorrogação do Prazo de Validade de Licença Simplificada', 'PPV/LS'),
    ('Cancelamento do Reconhecimento de Crédito de Volume Florestal', None),
    ('Renovação da Ampliação de Outorga de Direito de Uso de Recurso Hídrico', 'RAOUT'),
    ('Licença de Operação de Alteração', 'LOA'),
    ('Cancelamento da Autorização de Supressão de Vegetação', 'CASV'),
    (
        'Prorrogação do Prazo de Validade de Autorização de Corte de Floresta '
        'Plantada',
        'PPV',
    ),
    ('Prorrogação da Aprovação de Localização de Servidão Florestal', 'PPV/APLF'),
    ('Prorrogação do Prazo de Validade para Atendimento a Condicionante', 'PPV/RC'),
    # Autos de infração, notificações, fiscalização e termos: nomes lidos nos atos a
    # partir da sigla do número do processo (ex.: 2023-001073/TEC/AIMU-0081).
    ('Auto de Infração de Multa', 'AIMU'),
    ('Auto de Infração de Advertência', 'AIAD'),
    ('Auto de Infração de Interdição', 'AIIN'),
    ('Auto de Infração de Apreensão', 'AIAP'),
    ('Auto de Infração de Embargo', 'AIEM'),
    ('Auto de Infração de Demolição', 'AIDM'),
    (
        'Auto de Infração de Destruição de Fornos para Produção de Carvão Vegetal',
        'AIDF',
    ),
    ('Auto de Infração de Destruição ou Inutilização de Produtos', 'AIDP'),
    ('Notificação', 'NOT'),
    ('Notificação de Comunicação', 'NOTC'),
    ('Notificação de Homologação', 'NOTH'),
    ('Denúncia', 'DEN'),
    ('Emergência Ambiental', 'EMER'),
    ('Termo de Compromisso', 'TC'),
    ('Termo de Compromisso de Responsabilidade Ambiental', 'TCRA'),
]


def upgrade() -> None:
    op.create_table(
        'tipo_ato',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('nome', sa.String(), nullable=False),
        sa.Column('sigla', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_tipo_ato_id')),
        sa.UniqueConstraint('nome', name=op.f('uq_tipo_ato_nome')),
        schema='dominio',
    )
    op.create_table(
        'ato_tipo_ato',
        sa.Column('ato_id', sa.Integer(), nullable=False),
        sa.Column('tipo_ato_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['ato_id'],
            ['processing.ato.id'],
            name=op.f('fk_ato_tipo_ato_ato_id_ato'),
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['tipo_ato_id'],
            ['dominio.tipo_ato.id'],
            name=op.f('fk_ato_tipo_ato_tipo_ato_id_tipo_ato'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint(
            'ato_id', 'tipo_ato_id', name=op.f('pk_ato_tipo_ato_ato_id')
        ),
        schema='processing',
    )
    op.create_index(
        op.f('ix_ato_tipo_ato_tipo_ato_id'),
        'ato_tipo_ato',
        ['tipo_ato_id'],
        unique=False,
        schema='processing',
    )
    for nome, sigla in TIPOS_ATO:
        op.execute(
            sa.text(
                'INSERT INTO dominio.tipo_ato (nome, sigla) VALUES (:nome, :sigla)'
            ).bindparams(
                sa.bindparam('nome', nome, type_=sa.String()),
                sa.bindparam('sigla', sigla, type_=sa.String()),
            )
        )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_ato_tipo_ato_tipo_ato_id'),
        table_name='ato_tipo_ato',
        schema='processing',
    )
    op.drop_table('ato_tipo_ato', schema='processing')
    op.drop_table('tipo_ato', schema='dominio')
