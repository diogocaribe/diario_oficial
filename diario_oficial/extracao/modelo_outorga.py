"""Esquemas Pydantic da extração das outorgas de direito de uso de recursos hídricos.

Uma portaria (``Outorga``) autoriza um ou mais usos (``UsoCaptacao``,
``UsoLancamento``, ``UsoIntervencao``), cada um com os seus pontos (``PontoUso``). O
uso é o conjunto de pontos com o mesmo modo, a mesma finalidade e o mesmo prazo: no
texto, um parágrafo (§) do Art. 1º ou o bloco que termina em "para fins de ...".

A extração principal é a regex de ``outorga``; o modelo de linguagem só preenche o que
ela deixou vazio. Por isso as descrições dos campos também servem ao modelo.

Toda vazão tem as duas unidades, ``_m3_dia`` e ``_m3_s``: a que o texto traz é copiada
e a outra é calculada (1 m³/s = 86.400 m³/dia). Se o texto traz as duas, nenhuma é
calculada.
"""

import re
from typing import Annotated, Literal

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator

from diario_oficial.extracao.modelo_comum import CoordenadaGeografica, Pessoa
from diario_oficial.extracao.normalizacao import (
    normalizar_data,
    normalizar_municipio,
    normalizar_sistema_referencia,
)

SEGUNDOS_POR_DIA = 86_400

FINALIDADES = (
    'irrigacao',
    'abastecimento_humano',
    'abastecimento_industrial',
    'dessedentacao_animal',
    'comercio_servicos',
    'aquicultura',
    'mineracao',
    'aproveitamento_hidreletrico',
    'obra_infraestrutura',
    'pulverizacao_agricola',
    'combate_incendio',
    'diluicao_efluente',
    'barramento',
    'canalizacao',
    'dragagem',
    'lazer',
    'outro',
)
Finalidade = Literal[FINALIDADES]

METODOS_IRRIGACAO = (
    'gotejamento',
    'microaspersao',
    'pivo_central',
    'aspersao_convencional',
    'aspersao',
    'autopropelido',
    'caminhao_pipa',
    'mangueira',
    'superficie',
)
MetodoIrrigacao = Literal[METODOS_IRRIGACAO]

TIPOS_INTERVENCAO = (
    'regularizacao_barramento',
    'construcao_barramento',
    'canalizacao',
    'travessia',
    'aproveitamento_hidreletrico',
    'extracao_mineral_dragagem',
    'outro',
)
TipoIntervencao = Literal[TIPOS_INTERVENCAO]

EXPOENTE = str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹', '0123456789')
NOTACAO_CIENTIFICA = re.compile(
    r'(?P<base>\d+(?:[.,]\d+)?)?\s*[xX×]\s*10\s*\^?\s*(?P<expoente>[⁰¹²³⁴⁵⁶⁷⁸⁹\d]+)'
)


def vazao_nas_duas_unidades(
    por_dia: float | None, por_segundo: float | None
) -> tuple[float | None, float | None]:
    """A vazão em m³/dia e em m³/s, calculando só a que faltar."""
    if por_dia is None and por_segundo is not None:
        por_dia = round(por_segundo * SEGUNDOS_POR_DIA, 3)
    elif por_segundo is None and por_dia is not None:
        por_segundo = round(por_dia / SEGUNDOS_POR_DIA, 6)
    return por_dia, por_segundo


class PontoUso(BaseModel):
    """Um ponto de captação, lançamento ou intervenção."""

    identificacao: str | None = Field(
        description='Nome do ponto no texto (ex.: "poço 1", "Ponto P2", "B1").'
    )
    corpo_hidrico: str | None = Field(
        description=(
            'Rio, córrego, riacho, lagoa ou afluente onde fica o ponto, como no texto '
            '(ex.: "Rio do Meio", "afluente sem nome do Rio Surubim"). Não é a bacia. '
            'Null na captação subterrânea.'
        )
    )
    barramento: str | None = Field(
        description=(
            'Barramento ou barragem onde fica a captação, como no texto (ex.: '
            '"barramento existente B1"). Null se não houver.'
        )
    )
    barramento_dispensado: bool = Field(
        description='true se o texto diz que o barramento foi dispensado de outorga.'
    )
    coordenada: CoordenadaGeografica | None = Field(
        description='Par de coordenadas do ponto, como no texto.'
    )
    sistema_referencia_espacial: str | None = Field(
        description='Datum do par (ex.: SIRGAS 2000, SAD 69). Null se o texto não diz.'
    )
    vazao_m3_dia: float | None = Field(
        description=(
            'Vazão captada ou lançada no ponto, em m³/dia. Null se o texto só der m³/s.'
        )
    )
    vazao_m3_s: float | None = Field(
        description='A mesma vazão, se o texto a der em m³/s. Null se só der m³/dia.'
    )
    captacao_horas_dia: float | None = Field(
        description='Horas de captação ou lançamento por dia (ex.: "20 h/d" -> 20).'
    )

    @field_validator('sistema_referencia_espacial')
    @classmethod
    def _sistema_no_padrao(cls, valor: str | None) -> str | None:
        return normalizar_sistema_referencia(valor)

    @model_validator(mode='after')
    def _vazao_nas_duas_unidades(self) -> 'PontoUso':
        self.vazao_m3_dia, self.vazao_m3_s = vazao_nas_duas_unidades(
            self.vazao_m3_dia, self.vazao_m3_s
        )
        return self

    @computed_field
    @property
    def ponto(self) -> str | None:
        """WKT ``POINT(lon lat)`` no datum do texto (a gravação converte para 4674)."""
        if self.coordenada is None or (par := self.coordenada.lon_lat()) is None:
            return None
        return f'POINT({par[0]} {par[1]})'


class UsoRecursoHidrico(BaseModel):
    """Atributos comuns a qualquer uso autorizado pela portaria.

    ``modo`` é declarado aqui só para ser o primeiro campo do esquema: o modelo gera as
    propriedades na ordem do esquema e, se a resposta for cortada no ``num_predict``, o
    discriminador já saiu. Cada especialização o restringe ao seu ``Literal``, e o
    Pydantic mantém o campo redefinido na posição da classe base.
    """

    modo: str
    prazo_validade_anos: int | None = Field(
        description='Prazo de validade em anos (ex.: "04 (quatro) anos" -> 4).'
    )
    dt_validade: str | None = Field(
        description='Data final, se o texto diz "válida até DD/MM/AAAA" (AAAA-MM-DD).'
    )
    nro_portaria_prazo: str | None = Field(
        description=(
            'Número da portaria cujo prazo vale para este uso ("válida pelo prazo da '
            'Portaria nº 205" -> 205). Null nos demais casos.'
        )
    )
    dt_publicacao_portaria_prazo: str | None = Field(
        description='Data de publicação dessa portaria no DOE, em AAAA-MM-DD.'
    )
    bacia_hidrografica: str | None = Field(
        description='Bacia hidrográfica, sem "Bacia Hidrográfica do" (ex.: Rio Grande).'
    )
    finalidade_texto: str | None = Field(
        description='O que vem depois de "para fins de", como no texto.'
    )
    # O limite vira ``maxItems`` na gramática do Ollama: com ``temperature=0`` e sem
    # ``repeat_penalty``, o modelo pode repetir categorias até o ``num_predict`` (ato
    # 14706). Repetidas são tiradas antes da conferência do tamanho.
    finalidades: list[Finalidade] = Field(
        description='Categorias da finalidade (uma por uso citado), sem repetir.',
        max_length=len(FINALIDADES),
    )
    metodos_irrigacao: list[MetodoIrrigacao] = Field(
        description='Métodos de irrigação citados na finalidade, sem repetir.',
        max_length=len(METODOS_IRRIGACAO),
    )
    area_ha: float | None = Field(description='Área em hectares (ex.: "área 26 ha").')
    localidade: str | None = Field(
        description='Fazenda, unidade ou localidade do uso ("localizado na ...").'
    )
    municipios: list[str] = Field(description='Municípios onde fica o uso.')
    pontos: list[PontoUso] = Field(description='Pontos do uso, na ordem do texto.')

    @field_validator('dt_validade', 'dt_publicacao_portaria_prazo')
    @classmethod
    def _data_no_padrao(cls, valor: str | None) -> str | None:
        return normalizar_data(valor)

    @field_validator('finalidades', 'metodos_irrigacao', mode='before')
    @classmethod
    def _sem_repetir(cls, valores: object) -> object:
        if not isinstance(valores, list):
            return valores
        return list(dict.fromkeys(valores))

    @field_validator('municipios')
    @classmethod
    def _municipios_da_bahia(cls, valores: list[str]) -> list[str]:
        nomes = []
        for valor in valores:
            if (nome := normalizar_municipio(valor)) and nome not in nomes:
                nomes.append(nome)
        return nomes


class UsoCaptacao(UsoRecursoHidrico):
    """Captação de água subterrânea (poço) ou superficial."""

    modo: Literal['captacao_subterranea', 'captacao_superficial']


class ParametroEfluente(BaseModel):
    """Concentração de um parâmetro do efluente lançado (DBO, coliformes...)."""

    nome: str = Field(description='Parâmetro (ex.: DBO; Coliformes Termotolerantes).')
    valor: str = Field(description='Valor como no texto (ex.: 13,94; 1x10³).')
    unidade: str = Field(description='Unidade como no texto (ex.: mg/L; UFC/100mL).')

    @computed_field
    @property
    def valor_numero(self) -> float | None:
        """O valor como número, lendo a notação ``1,8 x 10²`` (-> 180.0)."""
        if achado := NOTACAO_CIENTIFICA.search(self.valor):
            base = float((achado.group('base') or '1').replace(',', '.'))
            return base * 10 ** int(achado.group('expoente').translate(EXPOENTE))
        numero = re.search(r'\d+(?:[.,]\d+)*', self.valor)
        if numero is None:
            return None
        texto = numero.group()
        if ',' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        return float(texto)


class UsoLancamento(UsoRecursoHidrico):
    """Lançamento de efluente para diluição no corpo hídrico."""

    modo: Literal['lancamento_efluente']
    vazao_diluicao_m3_dia: float | None = Field(
        description='Vazão de diluição em m³/dia.'
    )
    vazao_diluicao_m3_s: float | None = Field(description='Vazão de diluição em m³/s.')
    parametros: list[ParametroEfluente] = Field(
        description='Concentrações autorizadas no efluente.'
    )

    @model_validator(mode='after')
    def _vazao_nas_duas_unidades(self) -> 'UsoLancamento':
        self.vazao_diluicao_m3_dia, self.vazao_diluicao_m3_s = vazao_nas_duas_unidades(
            self.vazao_diluicao_m3_dia, self.vazao_diluicao_m3_s
        )
        return self


class UsoIntervencao(UsoRecursoHidrico):
    """Obra no corpo hídrico: barramento, canalização, ponte, hidrelétrica, dragagem."""

    modo: Literal['intervencao']
    tipo_intervencao: TipoIntervencao = Field(description='Tipo da obra.')
    volume_maximo_acumulacao_m3: float | None = Field(
        description='Volume máximo de acumulação do barramento, em m³.'
    )
    altura_maxima_m: float | None = Field(
        description='Altura máxima do barramento, em metros.'
    )
    vazao_minima_jusante_m3_dia: float | None = Field(
        description='Vazão mínima a manter para jusante, em m³/dia.'
    )
    vazao_minima_jusante_m3_s: float | None = Field(
        description='Vazão mínima a manter para jusante, em m³/s.'
    )
    descarga_de_fundo: bool = Field(
        description='true se o texto exige descarga de fundo no barramento.'
    )
    vazao_projeto_m3_dia: float | None = Field(
        description='Vazão de projeto (canalização, ponte), em m³/dia.'
    )
    vazao_projeto_m3_s: float | None = Field(
        description='Vazão de projeto (canalização, ponte), em m³/s.'
    )
    extensao_m: float | None = Field(description='Extensão da obra, em metros.')
    largura_m: float | None = Field(description='Largura da obra, em metros.')
    comprimento_m: float | None = Field(description='Comprimento da obra, em metros.')

    @model_validator(mode='after')
    def _vazao_nas_duas_unidades(self) -> 'UsoIntervencao':
        self.vazao_minima_jusante_m3_dia, self.vazao_minima_jusante_m3_s = (
            vazao_nas_duas_unidades(
                self.vazao_minima_jusante_m3_dia, self.vazao_minima_jusante_m3_s
            )
        )
        self.vazao_projeto_m3_dia, self.vazao_projeto_m3_s = vazao_nas_duas_unidades(
            self.vazao_projeto_m3_dia, self.vazao_projeto_m3_s
        )
        return self


Uso = Annotated[
    UsoCaptacao | UsoLancamento | UsoIntervencao, Field(discriminator='modo')
]


class Outorga(BaseModel):
    """Uma portaria de outorga (OUT, ROUT, AOUT ou AMOUT)."""

    natureza: Literal['outorga', 'renovacao', 'alteracao', 'ampliacao'] = Field(
        description=(
            'O que a portaria autoriza: outorga ("Autorizar o direito de uso"), '
            'renovacao, alteracao ou ampliacao (da outorga).'
        )
    )
    nro_portaria: str | None = Field(
        description='Número da portaria sem os pontos (ex.: "Nº 20.771" -> 20771).'
    )
    dt_portaria: str | None = Field(description='Data da portaria, em AAAA-MM-DD.')
    nro_processo: str | None = Field(
        description='Processo da portaria (ex.: 2019.001.007825/INEMA/LIC-07825).'
    )
    nro_processo_relacionado: str | None = Field(
        description=(
            'Na alteração e na ampliação, o processo da outorga original '
            '("relacionada ao processo nº ..."). Null nos demais casos.'
        )
    )
    outorgado: Pessoa | None = Field(
        description='Quem recebe a outorga, com o endereço da sede.'
    )
    usos: list[Uso] = Field(description='Usos autorizados, na ordem do texto.')

    @field_validator('dt_portaria')
    @classmethod
    def _data_no_padrao(cls, valor: str | None) -> str | None:
        return normalizar_data(valor)


class ExtracaoOutorga(BaseModel):
    """Resposta da extração: as outorgas do trecho (em geral uma)."""

    outorgas: list[Outorga] = Field(
        description='Uma outorga por "Autorizar ... direito de uso" do trecho.'
    )
