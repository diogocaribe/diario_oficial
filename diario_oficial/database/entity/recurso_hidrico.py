"""Outorgas de direito de uso de recursos hídricos, no esquema ``recurso_hidrico``.

As tabelas espelham os esquemas Pydantic de ``diario_oficial/extracao/modelo_outorga.py``
(e ``modelo_comum.py``): cada campo tem uma coluna com o mesmo nome, cada objeto
aninhado é uma tabela ligada por FK, cada lista de objetos é uma tabela filha e cada
lista de textos é um ``text[]``.

- ``ExtracaoTrecho``: um trecho de ato lido pela regex, com os campos que o modelo de
  linguagem preencheu e o erro dele. Apagar os trechos de um ato apaga, em cascata, tudo
  o que foi extraído dele.
- ``Outorga``: uma portaria. O outorgado fica em ``public.pessoa`` (``entity/pessoa.py``),
  comum a todas as extrações; o endereço da sede fica em ``Endereco`` e é um fato da
  outorga, válido na data do ato. Apagar a outorga apaga o endereço (trigger
  ``after_delete_apagar_endereco_da_outorga``).
- ``UsoRecursoHidrico``: um uso autorizado pela portaria. A herança é joined-table como
  nos autos, mas só lançamento (``UsoLancamento``) e intervenção (``UsoIntervencao``)
  têm tabela própria; a captação (``UsoCaptacao``) não tem atributo além dos comuns e
  fica só na tabela do uso. ``tipo_uso`` diz a especialização e ``modo`` o modo do
  texto (a captação tem dois: subterrânea e superficial).
- ``PontoUso``: os pontos de cada uso, com o par de coordenadas como está no texto e o
  ``ponto`` em SIRGAS 2000.
- ``ParametroEfluente``: as concentrações autorizadas num lançamento.
"""

from datetime import date, datetime
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
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from diario_oficial.database.configs.base import Base
from diario_oficial.database.entity.pessoa import Pessoa

# processing.ato (alvo da FK de extracao_trecho) e as entidades das relações dele
# precisam estar no metadata quando estas tabelas são usadas fora do Alembic.
from diario_oficial.database.entity import (  # noqa: F401
    ato,
    doe_bruto,
    dominio,
    publicacao,
)
from diario_oficial.extracao.modelo_outorga import (
    FINALIDADES,
    METODOS_IRRIGACAO,
    TIPOS_INTERVENCAO,
)

ESQUEMA = 'recurso_hidrico'
# SIRGAS 2000, o sistema oficial do Brasil: as geometrias são convertidas para ele.
SRID = 4674

MODOS = (
    'captacao_subterranea',
    'captacao_superficial',
    'lancamento_efluente',
    'intervencao',
)


MODO_DO_TIPO_USO = (
    "(tipo_uso = 'uso_captacao' "
    "AND modo IN ('captacao_subterranea', 'captacao_superficial')) "
    "OR (tipo_uso = 'uso_lancamento' AND modo = 'lancamento_efluente') "
    "OR (tipo_uso = 'uso_intervencao' AND modo = 'intervencao')"
)


def _em(coluna: str, valores: tuple[str, ...]) -> str:
    """Condição ``coluna IN (...)`` para um ``CheckConstraint``."""
    return f'{coluna} IN ({", ".join(repr(valor) for valor in valores)})'


def _contido_em(coluna: str, valores: tuple[str, ...]) -> str:
    """Condição de que todo item do ``text[]`` está em ``valores``."""
    lista = ', '.join(repr(valor) for valor in valores)
    return f'{coluna} <@ ARRAY[{lista}]::text[]'


class ExtracaoTrecho(Base):
    """Trecho de um ato lido pela regex; o modelo só preenche os campos vazios."""

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
    erro: Mapped[str | None] = mapped_column(
        Text, comment='Erro que impediu a extração do trecho.'
    )
    preenchido_pelo_modelo: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        server_default='{}',
        comment='Campos que a regex deixou vazios e o modelo preencheu.',
    )
    erro_modelo: Mapped[str | None] = mapped_column(
        Text, comment='Erro do modelo; os campos vazios da regex ficaram vazios.'
    )
    modelo_llm: Mapped[str | None] = mapped_column(Text)
    extraido_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    outorgas: Mapped[list['Outorga']] = relationship(
        back_populates='extracao_trecho',
        cascade='all, delete-orphan',
        passive_deletes=True,
        order_by='Outorga.id',
    )


class Endereco(Base):
    """Endereço da sede do outorgado, como está na portaria."""

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


class Outorga(Base):
    """Uma portaria de outorga (OUT, ROUT, AOUT ou AMOUT)."""

    __tablename__ = 'outorga'
    __table_args__ = (
        CheckConstraint(
            _em('natureza', ('outorga', 'renovacao', 'alteracao', 'ampliacao')),
            name='natureza',
        ),
        {'schema': ESQUEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    extracao_trecho_id: Mapped[int] = mapped_column(
        ForeignKey(f'{ESQUEMA}.extracao_trecho.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    natureza: Mapped[str] = mapped_column(Text, nullable=False)
    nro_portaria: Mapped[str | None] = mapped_column(
        Text, index=True, comment='Número da portaria sem os pontos.'
    )
    dt_portaria: Mapped[date | None]
    nro_processo: Mapped[str | None] = mapped_column(Text, index=True)
    nro_processo_relacionado: Mapped[str | None] = mapped_column(
        Text, comment='Processo da outorga original (alteração e ampliação).'
    )
    # RESTRICT: a pessoa pode estar em várias outorgas e autos; não some com uma delas.
    # Nulo quando nem a regex nem o modelo acharam o outorgado.
    outorgado_pessoa_id: Mapped[int | None] = mapped_column(
        ForeignKey('pessoa.id', ondelete='RESTRICT'),
        index=True,
        comment='Pessoa outorgada, única pelo CPF/CNPJ; sem documento, uma por outorga.',
    )
    outorgado_nome: Mapped[str | None] = mapped_column(
        Text, comment='Nome do outorgado como está nesta portaria.'
    )
    endereco_outorgado_id: Mapped[int | None] = mapped_column(
        ForeignKey(f'{ESQUEMA}.endereco.id', ondelete='SET NULL'),
        comment='Endereço da sede do outorgado nesta portaria.',
    )

    extracao_trecho: Mapped[ExtracaoTrecho] = relationship(back_populates='outorgas')
    outorgado: Mapped[Pessoa | None] = relationship()
    endereco_outorgado: Mapped[Endereco | None] = relationship()
    usos: Mapped[list['UsoRecursoHidrico']] = relationship(
        back_populates='outorga',
        cascade='all, delete-orphan',
        passive_deletes=True,
        order_by='UsoRecursoHidrico.id',
    )


class UsoRecursoHidrico(Base):
    """Atributos comuns a qualquer uso; a especialização fica em ``tipo_uso``."""

    __tablename__ = 'uso_recurso_hidrico'
    __table_args__ = (
        CheckConstraint(_em('modo', MODOS), name='modo'),
        CheckConstraint(
            _em('tipo_uso', ('uso_captacao', 'uso_lancamento', 'uso_intervencao')),
            name='tipo_uso',
        ),
        # A especialização tem de bater com o modo: captação não grava como lançamento.
        CheckConstraint(MODO_DO_TIPO_USO, name='modo_do_tipo_uso'),
        CheckConstraint(_contido_em('finalidades', FINALIDADES), name='finalidades'),
        CheckConstraint(
            _contido_em('metodos_irrigacao', METODOS_IRRIGACAO),
            name='metodos_irrigacao',
        ),
        {'schema': ESQUEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    outorga_id: Mapped[int] = mapped_column(
        ForeignKey(f'{ESQUEMA}.outorga.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    tipo_uso: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment='Especialização (uso_captacao, uso_lancamento...).',
    )
    modo: Mapped[str] = mapped_column(Text, nullable=False)
    prazo_validade_anos: Mapped[int | None]
    dt_validade: Mapped[date | None] = mapped_column(
        comment='Data final, quando o texto diz "válida até".'
    )
    nro_portaria_prazo: Mapped[str | None] = mapped_column(
        Text, comment='Portaria cujo prazo vale para este uso.'
    )
    dt_publicacao_portaria_prazo: Mapped[date | None]
    bacia_hidrografica: Mapped[str | None] = mapped_column(Text, index=True)
    finalidade_texto: Mapped[str | None] = mapped_column(Text)
    finalidades: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default='{}'
    )
    metodos_irrigacao: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default='{}'
    )
    area_ha: Mapped[Decimal | None] = mapped_column(Numeric)
    localidade: Mapped[str | None] = mapped_column(Text)
    municipios: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        server_default='{}',
        comment='Municípios da Bahia onde fica o uso (nome oficial do IBGE).',
    )

    outorga: Mapped[Outorga] = relationship(back_populates='usos')
    pontos: Mapped[list['PontoUso']] = relationship(
        back_populates='uso',
        cascade='all, delete-orphan',
        passive_deletes=True,
        order_by='PontoUso.id',
    )

    __mapper_args__ = {'polymorphic_on': 'tipo_uso'}


class UsoCaptacao(UsoRecursoHidrico):
    """Captação subterrânea ou superficial: só os atributos comuns, sem tabela própria."""

    __mapper_args__ = {'polymorphic_identity': 'uso_captacao'}


def _chave_do_uso() -> Mapped[int]:
    """PK da especialização: a mesma do ``uso_recurso_hidrico`` (joined-table)."""
    return mapped_column(
        ForeignKey(f'{ESQUEMA}.uso_recurso_hidrico.id', ondelete='CASCADE'),
        primary_key=True,
    )


class UsoLancamento(UsoRecursoHidrico):
    """Lançamento de efluente para diluição."""

    __tablename__ = 'uso_lancamento'
    __table_args__ = {'schema': ESQUEMA}

    uso_recurso_hidrico_id: Mapped[int] = _chave_do_uso()
    vazao_diluicao_m3_dia: Mapped[Decimal | None] = mapped_column(Numeric)
    vazao_diluicao_m3_s: Mapped[Decimal | None] = mapped_column(Numeric)

    parametros: Mapped[list['ParametroEfluente']] = relationship(
        cascade='all, delete-orphan',
        passive_deletes=True,
        order_by='ParametroEfluente.id',
    )

    __mapper_args__ = {'polymorphic_identity': 'uso_lancamento'}


class UsoIntervencao(UsoRecursoHidrico):
    """Obra no corpo hídrico: barramento, canalização, ponte, hidrelétrica, dragagem."""

    __tablename__ = 'uso_intervencao'
    __table_args__ = (
        CheckConstraint(
            _em('tipo_intervencao', TIPOS_INTERVENCAO), name='tipo_intervencao'
        ),
        {'schema': ESQUEMA},
    )

    uso_recurso_hidrico_id: Mapped[int] = _chave_do_uso()
    tipo_intervencao: Mapped[str] = mapped_column(Text, nullable=False)
    volume_maximo_acumulacao_m3: Mapped[Decimal | None] = mapped_column(Numeric)
    altura_maxima_m: Mapped[Decimal | None] = mapped_column(Numeric)
    vazao_minima_jusante_m3_dia: Mapped[Decimal | None] = mapped_column(Numeric)
    vazao_minima_jusante_m3_s: Mapped[Decimal | None] = mapped_column(Numeric)
    descarga_de_fundo: Mapped[bool] = mapped_column(nullable=False)
    vazao_projeto_m3_dia: Mapped[Decimal | None] = mapped_column(Numeric)
    vazao_projeto_m3_s: Mapped[Decimal | None] = mapped_column(Numeric)
    extensao_m: Mapped[Decimal | None] = mapped_column(Numeric)
    largura_m: Mapped[Decimal | None] = mapped_column(Numeric)
    comprimento_m: Mapped[Decimal | None] = mapped_column(Numeric)

    __mapper_args__ = {'polymorphic_identity': 'uso_intervencao'}


class PontoUso(Base):
    """Ponto de captação, lançamento ou intervenção de um uso."""

    __tablename__ = 'ponto_uso'
    __table_args__ = (
        Index('ix_ponto_uso_ponto', 'ponto', postgresql_using='gist'),
        {'schema': ESQUEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uso_recurso_hidrico_id: Mapped[int] = mapped_column(
        ForeignKey(f'{ESQUEMA}.uso_recurso_hidrico.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    identificacao: Mapped[str | None] = mapped_column(Text)
    corpo_hidrico: Mapped[str | None] = mapped_column(Text)
    barramento: Mapped[str | None] = mapped_column(Text)
    barramento_dispensado: Mapped[bool] = mapped_column(nullable=False)
    latitude: Mapped[str | None] = mapped_column(
        Text, comment='Latitude como está no texto.'
    )
    longitude: Mapped[str | None] = mapped_column(
        Text, comment='Longitude como está no texto.'
    )
    sistema_referencia_espacial: Mapped[str | None] = mapped_column(
        Text, comment='Datum citado no texto; o ponto está em SIRGAS 2000.'
    )
    vazao_m3_dia: Mapped[Decimal | None] = mapped_column(Numeric)
    vazao_m3_s: Mapped[Decimal | None] = mapped_column(Numeric)
    captacao_horas_dia: Mapped[Decimal | None] = mapped_column(
        Numeric, comment='Horas de captação ou lançamento por dia.'
    )
    ponto = mapped_column(Geometry('POINT', srid=SRID, spatial_index=False))

    uso: Mapped[UsoRecursoHidrico] = relationship(back_populates='pontos')


class ParametroEfluente(Base):
    """Concentração autorizada de um parâmetro do efluente (DBO, coliformes...)."""

    __tablename__ = 'parametro_efluente'
    __table_args__ = {'schema': ESQUEMA}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uso_lancamento_id: Mapped[int] = mapped_column(
        ForeignKey(
            f'{ESQUEMA}.uso_lancamento.uso_recurso_hidrico_id', ondelete='CASCADE'
        ),
        nullable=False,
        index=True,
    )
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    valor: Mapped[str] = mapped_column(Text, nullable=False, comment='Como no texto.')
    unidade: Mapped[str] = mapped_column(Text, nullable=False)
    valor_numero: Mapped[Decimal | None] = mapped_column(
        Numeric, comment='O valor como número (1,8 x 10² -> 180).'
    )
