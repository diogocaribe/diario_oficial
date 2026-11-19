"""Dados extraídos dos atos com LLM, no esquema ``auto_infracao``.

As tabelas espelham os esquemas Pydantic de ``diario_oficial/extracao/modelo_comum.py``
e ``modelo_auto_infracao.py``: cada campo do JSON tem uma coluna com o mesmo nome,
cada objeto aninhado é uma tabela ligada por FK, cada lista de objetos é uma tabela
filha e cada lista de textos é um ``text[]``. A herança também é a mesma: cada subtipo
(``AutoInterdicao``, ``AutoMulta``, ``AutoEmbargo``...) estende ``AutoInfracao``, em
tabelas ligadas pela chave primária. Quem converte o objeto Pydantic nestas entidades é
``diario_oficial.extracao.gravacao``.

- ``ExtracaoTrecho``: um trecho de ato que foi para o modelo, com o erro, se houve, a
  conferência contra a regex e os campos que a regex preencheu no lugar do modelo.
  Apagar os trechos de um ato apaga, em cascata, tudo o que foi extraído dele.
- ``Pessoa``: uma por CPF/CNPJ (sem documento, uma por auto). O endereço não fica na
  pessoa: é um fato do auto, válido na data do ato.
- ``Endereco``: endereço do autuado ou local da infração, sempre de um auto.
- ``BemProdutoAutuado``: bem apreendido (AIAP) ou produto destruído (AIDP) de um auto.
"""

from datetime import date, datetime, time
from decimal import Decimal

from geoalchemy2 import Geometry
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from diario_oficial.database.configs.base import Base

# processing.ato (alvo da FK de extracao_trecho) e as entidades das relações dele
# precisam estar no metadata quando estas tabelas são usadas fora do Alembic.
from diario_oficial.database.entity import (  # noqa: F401
    ato,
    doe_bruto,
    dominio,
    publicacao,
)

ESQUEMA = 'auto_infracao'
# SIRGAS 2000, o sistema oficial do Brasil: as geometrias são convertidas para ele.
SRID = 4674


class ExtracaoTrecho(Base):
    """Trecho de um ato enviado ao modelo; ``erro`` preenchido se o modelo falhou."""

    __tablename__ = 'extracao_trecho'
    __table_args__ = {'schema': ESQUEMA}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # CASCADE: reprocessar a publicação apaga os atos e, com eles, o que foi extraído
    ato_id: Mapped[int] = mapped_column(
        ForeignKey('processing.ato.id', ondelete='CASCADE'), nullable=False, index=True
    )
    sigla_tipo_ato: Mapped[str] = mapped_column(
        Text, nullable=False, comment='Sigla de dominio.tipo_ato da extração.'
    )
    trecho: Mapped[str] = mapped_column(Text, nullable=False)
    erro: Mapped[str | None] = mapped_column(Text)
    conferencia: Mapped[dict | None] = mapped_column(
        JSONB, comment='Resultado de conferir: a resposta do modelo contra a regex.'
    )
    preenchido_pela_regex: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        server_default='{}',
        comment='Campos que o modelo deixou vazios e a regex preencheu.',
    )
    modelo_llm: Mapped[str | None] = mapped_column(Text)
    extraido_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    autos: Mapped[list['AutoInfracao']] = relationship(
        back_populates='extracao_trecho',
        cascade='all, delete-orphan',
        passive_deletes=True,
        order_by='AutoInfracao.id',
    )


class Pessoa(Base):
    """Pessoa física ou jurídica autuada, única pelo documento quando ele existe."""

    __tablename__ = 'pessoa'
    __table_args__ = (
        CheckConstraint(
            "tipo_documento IN ('CPF', 'CNPJ', 'RG')", name='tipo_documento'
        ),
        Index(
            'uq_pessoa_documento',
            'tipo_documento',
            'nro_documento',
            unique=True,
            postgresql_where=text('nro_documento IS NOT NULL'),
        ),
        {'schema': ESQUEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(
        Text, nullable=False, comment='Nome da primeira vez em que a pessoa apareceu.'
    )
    tipo_documento: Mapped[str | None] = mapped_column(Text)
    nro_documento: Mapped[str | None] = mapped_column(
        Text, comment='Só os dígitos, para CPF e CNPJ.'
    )


class Endereco(Base):
    """Lugar citado num auto: endereço urbano ou localidade rural."""

    __tablename__ = 'endereco'
    __table_args__ = {'schema': ESQUEMA}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    localidade: Mapped[str | None] = mapped_column(Text)
    logradouro: Mapped[str | None] = mapped_column(Text)
    numero: Mapped[str | None] = mapped_column(Text)
    complemento: Mapped[str | None] = mapped_column(Text)
    bairro: Mapped[str | None] = mapped_column(Text)
    rodovia: Mapped[str | None] = mapped_column(Text)
    cep: Mapped[str | None] = mapped_column(Text)
    municipio: Mapped[str | None] = mapped_column(Text)


class AutoInfracao(Base):
    """Atributos comuns a qualquer auto de infração; o tipo fica em ``tipo_auto``."""

    __tablename__ = 'auto_infracao'
    __table_args__ = (
        CheckConstraint(
            "natureza IN ('homologacao', 'recurso', 'termo_de_compromisso', "
            "'sustacao', 'outro')",
            name='natureza',
        ),
        CheckConstraint(
            "resultado_recurso IN ('deferido', 'indeferido')", name='resultado_recurso'
        ),
        CheckConstraint(
            "gravidade IN ('leve', 'grave', 'gravissima')", name='gravidade'
        ),
        Index('ix_auto_infracao_ponto', 'ponto', postgresql_using='gist'),
        Index('ix_auto_infracao_poligono', 'poligono', postgresql_using='gist'),
        {'schema': ESQUEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    extracao_trecho_id: Mapped[int] = mapped_column(
        ForeignKey(f'{ESQUEMA}.extracao_trecho.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    tipo_auto: Mapped[str] = mapped_column(
        Text, nullable=False, comment='Tabela da especialização (ex.: auto_interdicao).'
    )
    nro_processo: Mapped[str | None] = mapped_column(Text, index=True)
    natureza: Mapped[str] = mapped_column(Text, nullable=False)
    resultado_recurso: Mapped[str | None] = mapped_column(Text)
    nro_ato_decisorio: Mapped[str | None] = mapped_column(Text)
    dt_homologacao: Mapped[date | None]
    conduta: Mapped[str | None] = mapped_column(Text)
    local_infracao_id: Mapped[int | None] = mapped_column(
        ForeignKey(f'{ESQUEMA}.endereco.id', ondelete='SET NULL')
    )
    dt_constatacao: Mapped[date | None]
    hr_constatacao: Mapped[time | None]
    sistema_referencia_espacial: Mapped[str | None] = mapped_column(
        Text, comment='Datum citado no texto; as geometrias estão em SIRGAS 2000.'
    )
    area_hectare: Mapped[Decimal | None] = mapped_column(Numeric)
    gravidade: Mapped[str | None] = mapped_column(Text)
    nro_lacre: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default='{}'
    )
    especie_citada: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default='{}'
    )
    # RESTRICT: a pessoa pode estar em vários autos; não some com um deles
    autuado_id: Mapped[int] = mapped_column(
        ForeignKey(f'{ESQUEMA}.pessoa.id', ondelete='RESTRICT'),
        nullable=False,
        index=True,
        comment='Pessoa autuada, única pelo CPF/CNPJ; sem documento, uma por auto.',
    )
    autuado_nome: Mapped[str] = mapped_column(
        Text, nullable=False, comment='Nome do autuado como está neste auto.'
    )
    endereco_autuado_id: Mapped[int | None] = mapped_column(
        ForeignKey(f'{ESQUEMA}.endereco.id', ondelete='SET NULL')
    )
    ponto = mapped_column(Geometry('POINT', srid=SRID, spatial_index=False))
    poligono = mapped_column(Geometry('POLYGON', srid=SRID, spatial_index=False))

    extracao_trecho: Mapped[ExtracaoTrecho] = relationship(back_populates='autos')
    autuado: Mapped[Pessoa] = relationship()
    local_infracao: Mapped[Endereco | None] = relationship(
        foreign_keys=[local_infracao_id]
    )
    endereco_autuado: Mapped[Endereco | None] = relationship(
        foreign_keys=[endereco_autuado_id]
    )
    coordenada: Mapped[list['CoordenadaExtraidaTrecho']] = relationship(
        cascade='all, delete-orphan',
        passive_deletes=True,
        order_by='CoordenadaExtraidaTrecho.id',
    )

    __mapper_args__ = {
        'polymorphic_on': 'tipo_auto',
        'polymorphic_identity': 'auto_infracao',
    }


class AutoInterdicao(AutoInfracao):
    """Auto de infração de interdição (AIIN)."""

    __tablename__ = 'auto_interdicao'
    __table_args__ = (
        CheckConstraint(
            "modalidade IN ('temporaria', 'definitiva')", name='modalidade'
        ),
        {'schema': ESQUEMA},
    )

    auto_infracao_id: Mapped[int] = mapped_column(
        ForeignKey(f'{ESQUEMA}.auto_infracao.id', ondelete='CASCADE'), primary_key=True
    )
    modalidade: Mapped[str | None] = mapped_column(Text)
    atividade_interditada: Mapped[str | None] = mapped_column(Text)
    excecao_interdicao: Mapped[str | None] = mapped_column(Text)
    condicao: Mapped[str | None] = mapped_column(Text)

    __mapper_args__ = {'polymorphic_identity': 'auto_interdicao'}


def _chave_do_auto() -> Mapped[int]:
    """PK da especialização: a mesma do ``auto_infracao`` (herança joined-table)."""
    return mapped_column(
        ForeignKey(f'{ESQUEMA}.auto_infracao.id', ondelete='CASCADE'), primary_key=True
    )


def _bens_do_auto() -> Mapped[list['BemProdutoAutuado']]:
    return relationship(
        cascade='all, delete-orphan',
        passive_deletes=True,
        order_by='BemProdutoAutuado.id',
    )


class AutoMulta(AutoInfracao):
    """Auto de infração de multa (AIMU)."""

    __tablename__ = 'auto_multa'
    __table_args__ = (
        CheckConstraint("tipo_multa IN ('simples', 'diaria')", name='tipo_multa'),
        {'schema': ESQUEMA},
    )

    auto_infracao_id: Mapped[int] = _chave_do_auto()
    valor_multa: Mapped[Decimal | None] = mapped_column(Numeric)
    tipo_multa: Mapped[str | None] = mapped_column(Text)
    reincidente: Mapped[bool] = mapped_column(nullable=False)
    percentual_desconto: Mapped[Decimal | None] = mapped_column(Numeric)
    nro_notificacao: Mapped[str | None] = mapped_column(Text)

    __mapper_args__ = {'polymorphic_identity': 'auto_multa'}


class AutoAdvertencia(AutoInfracao):
    """Auto de infração de advertência (AIAD)."""

    __tablename__ = 'auto_advertencia'
    __table_args__ = {'schema': ESQUEMA}

    auto_infracao_id: Mapped[int] = _chave_do_auto()
    exigencia: Mapped[str | None] = mapped_column(Text)
    prazo_atendimento_dias: Mapped[int | None]
    nro_notificacao: Mapped[str | None] = mapped_column(Text)

    __mapper_args__ = {'polymorphic_identity': 'auto_advertencia'}


class AutoApreensao(AutoInfracao):
    """Auto de infração de apreensão (AIAP)."""

    __tablename__ = 'auto_apreensao'
    __table_args__ = {'schema': ESQUEMA}

    auto_infracao_id: Mapped[int] = _chave_do_auto()
    fiel_depositario: Mapped[str | None] = mapped_column(Text)
    destinacao: Mapped[str | None] = mapped_column(Text)

    bem_apreendido: Mapped[list['BemProdutoAutuado']] = _bens_do_auto()

    __mapper_args__ = {'polymorphic_identity': 'auto_apreensao'}


class AutoEmbargo(AutoInfracao):
    """Auto de infração de embargo (AIEM)."""

    __tablename__ = 'auto_embargo'
    __table_args__ = (
        CheckConstraint(
            "modalidade IN ('temporario', 'definitivo')", name='modalidade'
        ),
        {'schema': ESQUEMA},
    )

    auto_infracao_id: Mapped[int] = _chave_do_auto()
    modalidade: Mapped[str | None] = mapped_column(Text)
    objeto_embargado: Mapped[str | None] = mapped_column(Text)
    area_restricao_legal_uso: Mapped[str | None] = mapped_column(Text)

    __mapper_args__ = {'polymorphic_identity': 'auto_embargo'}


class AutoDemolicao(AutoInfracao):
    """Auto de infração de demolição (AIDM)."""

    __tablename__ = 'auto_demolicao'
    __table_args__ = {'schema': ESQUEMA}

    auto_infracao_id: Mapped[int] = _chave_do_auto()
    obra_demolida: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default='{}'
    )
    area_restricao_legal_uso: Mapped[str | None] = mapped_column(Text)

    __mapper_args__ = {'polymorphic_identity': 'auto_demolicao'}


class AutoDestruicaoFornos(AutoInfracao):
    """Auto de destruição de fornos para produção de carvão vegetal (AIDF)."""

    __tablename__ = 'auto_destruicao_fornos'
    __table_args__ = (
        CheckConstraint(
            "situacao_forno IN ('ativo', 'inativo')", name='situacao_forno'
        ),
        {'schema': ESQUEMA},
    )

    auto_infracao_id: Mapped[int] = _chave_do_auto()
    qtd_fornos: Mapped[int | None]
    tipo_forno: Mapped[str | None] = mapped_column(Text)
    capacidade_por_forno: Mapped[Decimal | None] = mapped_column(Numeric)
    situacao_forno: Mapped[str | None] = mapped_column(Text)

    __mapper_args__ = {'polymorphic_identity': 'auto_destruicao_fornos'}


class AutoDestruicaoProdutos(AutoInfracao):
    """Auto de destruição ou inutilização de produtos (AIDP)."""

    __tablename__ = 'auto_destruicao_produtos'
    __table_args__ = {'schema': ESQUEMA}

    auto_infracao_id: Mapped[int] = _chave_do_auto()

    produto_destruido: Mapped[list['BemProdutoAutuado']] = _bens_do_auto()

    __mapper_args__ = {'polymorphic_identity': 'auto_destruicao_produtos'}


class BemProdutoAutuado(Base):
    """Bem ou produto de um auto: apreendido (AIAP) ou destruído (AIDP)."""

    __tablename__ = 'bem_produto_autuado'
    __table_args__ = {'schema': ESQUEMA}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    auto_infracao_id: Mapped[int] = mapped_column(
        ForeignKey(f'{ESQUEMA}.auto_infracao.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    quantidade: Mapped[Decimal | None] = mapped_column(Numeric)
    unidade: Mapped[str | None] = mapped_column(Text)
    valor_avaliado: Mapped[Decimal | None] = mapped_column(Numeric)
    identificacao: Mapped[str | None] = mapped_column(Text)


class CoordenadaExtraidaTrecho(Base):
    """Par de coordenadas de um auto, como está no texto."""

    __tablename__ = 'coordenada_extraida_trecho'
    __table_args__ = (
        CheckConstraint("tipo IN ('ponto', 'vertice')", name='tipo'),
        {'schema': ESQUEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    auto_infracao_id: Mapped[int] = mapped_column(
        ForeignKey(f'{ESQUEMA}.auto_infracao.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    latitude: Mapped[str] = mapped_column(Text, nullable=False)
    longitude: Mapped[str] = mapped_column(Text, nullable=False)
    fuso_utm: Mapped[str | None] = mapped_column(Text)
    tipo: Mapped[str] = mapped_column(Text, nullable=False)
