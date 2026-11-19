"""Esquemas Pydantic da extração estruturada dos autos de infração com LLM: o auto
comum (``AutoInfracao``) e os de cada subtipo. Endereço, pessoa e coordenada vêm de
``modelo_comum``.

As descrições dos campos vão para o JSON Schema que o modelo recebe, então dizem o que o
modelo deve copiar do texto. Os validadores corrigem o formato do que o modelo devolve
(datas no padrão do banco, número de processo, sistema de referência) e os campos
calculados (``ponto`` e ``poligono``) são montados aqui a partir das coordenadas: não
entram no esquema de entrada do modelo.
"""

import re
from typing import Literal

from pydantic import (
    BaseModel,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

from diario_oficial.extracao.utils_geo import (
    FUSOS_DA_BAHIA,
    utm_para_lon_lat,
)
from diario_oficial.extracao.modelo_comum import (
    CoordenadaGeografica,
    Endereco,
    Pessoa,
)
from diario_oficial.extracao.normalizacao import (
    normalizar_data,
    normalizar_hora,
    normalizar_numero,
    normalizar_processo,
    normalizar_sistema_referencia,
)

NUMERO_DE_LACRE = re.compile(r'\d{4,}')


def _wkt_par(par: tuple[float, float]) -> str:
    return f'{par[0]} {par[1]}'


class AutoInfracao(BaseModel):
    """Atributos comuns a qualquer auto de infração (AIIN, AIMU, AIAD, AIAP...)."""

    nro_processo: str | None = Field(
        description=(
            'Número do processo do auto, sempre no padrão AAAA-NNNNNN/TEC/AIXX-NNNN '
            '(ex.: 2017-009301/TEC/AIIN-0222). Se o texto escrever o número com '
            'espaços, pontos ou outro erro de digitação, escreva-o corrigido nesse '
            'padrão. Null só se o texto não trouxer o número.'
        )
    )
    natureza: Literal[
        'homologacao', 'recurso', 'termo_de_compromisso', 'sustacao', 'outro'
    ] = Field(
        description=(
            'O que a publicação faz com o auto: homologacao (foi homologado), recurso '
            '(julgamento de recurso pelo CEPRAM), termo_de_compromisso (suspensão por '
            'termo de compromisso), sustacao (auto sustado) ou outro.'
        )
    )
    resultado_recurso: Literal['deferido', 'indeferido'] | None = Field(
        description=(
            'Só quando a publicação julga recurso: deferido se o texto diz "Deferir o '
            'recurso" (penalidade anulada); indeferido se diz "Indeferir o recurso" '
            '(penalidade mantida). Null nos demais casos.'
        )
    )
    nro_ato_decisorio: str | None = Field(
        description=('Número do ato(ex.: "Nº 4.817" -> 4.817). Null se não houver.')
    )
    dt_homologacao: str | None = Field(
        description=(
            'Data em que o auto foi homologado, no formato AAAA-MM-DD (ex.: "em '
            '01/04/2019, foi homologado" -> 2019-04-01).'
        )
    )
    conduta: str | None = Field(
        description=(
            'Resumo curto da infração cometida, sem o local ou endereço. Null se o '
            'texto não descreve a infração (ex.: resoluções do CEPRAM).'
        )
    )

    local_infracao: Endereco | None = Field(
        description='Onde a infração ocorreu. Não use o endereço do autuado.'
    )

    dt_constatacao: str | None = Field(
        description=(
            'Data em que a infração foi constatada, no formato AAAA-MM-DD. Converta '
            'datas por extenso (ex.: "aos cinco dias do mês de agosto de 2010" -> '
            '2010-08-05) e corrija erros de digitação (ex.: 27/05/215 -> 2015-05-27).'
        )
    )
    hr_constatacao: str | None = Field(
        description='Hora em que a infração foi constatada, no formato HH:MM.'
    )
    coordenada: list[CoordenadaGeografica] = Field(
        description=(
            'Todos os pares de coordenadas do local da infração ou da área '
            'interditada, na ordem do texto, um item por par latitude/longitude.'
        )
    )
    sistema_referencia_espacial: str | None = Field(
        description=(
            'Datum ou sistema de referência das coordenadas, se o texto informar '
            '(ex.: SIRGAS 2000, SAD 69, WGS 84).'
        )
    )
    area_hectare: float | None = Field(
        description='Área atingida em hectares, se o texto informar.'
    )
    gravidade: Literal['leve', 'grave', 'gravissima'] | None = Field(
        description=(
            'Gravidade da infração, só quando o texto a classifica (ex.: "classificada '
            'como GRAVE"). "Grave dano ambiental" não é classificação: use null.'
        )
    )
    nro_lacre: list[str] = Field(
        description=(
            'Números dos lacres citados (ex.: "Lacre N° 0029770" -> 0029770). Lista '
            'vazia se não houver.'
        )
    )
    especie_citada: list[str] = Field(
        description=(
            'Espécies da fauna ou da flora citadas, com o nome como está no texto '
            '(ex.: aroeira-do-sertão (Myracrodruon urundeuva); jequitibá). Lista '
            'vazia se não houver.'
        )
    )
    autuado: Pessoa = Field(description='Pessoa ou empresa autuada.')

    @field_validator('nro_processo')
    @classmethod
    def _processo_no_padrao(cls, valor: str | None) -> str | None:
        """Corrige espaços e pontos; mantém o valor do modelo se não reconhecer."""
        if valor is None or not valor.strip():
            return None
        return normalizar_processo(valor) or valor.strip()

    @field_validator('dt_homologacao', 'dt_constatacao')
    @classmethod
    def _data_no_padrao(cls, valor: str | None) -> str | None:
        return normalizar_data(valor)

    @field_validator('sistema_referencia_espacial')
    @classmethod
    def _sistema_no_padrao(cls, valor: str | None) -> str | None:
        return normalizar_sistema_referencia(valor)

    @field_validator('hr_constatacao')
    @classmethod
    def _hora_no_padrao(cls, valor: str | None) -> str | None:
        return normalizar_hora(valor)

    @field_validator('nro_lacre')
    @classmethod
    def _so_numeros_de_lacre(cls, valores: list[str]) -> list[str]:
        """Fica só com números de lacre: 4 ou mais dígitos, sem repetição.

        Descarta o item que tem algo além de "lacre", "nº", números e separadores (o
        modelo às vezes põe aqui o processo, uma data ou uma quantidade).
        """
        numeros = []
        for valor in valores:
            resto = re.sub(r'lacres?|n[º°o]\.?|\d+|[\s,;e]', '', valor, flags=re.I)
            if resto:
                continue
            for numero in NUMERO_DE_LACRE.findall(valor):
                if numero not in numeros:
                    numeros.append(numero)
        return numeros

    @field_validator('coordenada')
    @classmethod
    def _sem_par_vazio(
        cls, valores: list[CoordenadaGeografica]
    ) -> list[CoordenadaGeografica]:
        """Tira os pares sem número (o modelo devolve um par vazio quando não há)."""
        return [
            par
            for par in valores
            if re.search(r'\d', par.latitude) and re.search(r'\d', par.longitude)
        ]

    def _fuso_utm(
        self, pares_utm: list[tuple[float, float]], referencia: tuple | None
    ) -> int | None:
        """Fuso para converter os pares UTM do auto.

        Usa o fuso informado no texto. Sem ele, fica com o fuso em que todos os pares
        caem dentro da Bahia; se os dois fusos servirem, escolhe o mais perto de um par
        em graus do mesmo auto e, sem esse par, não converte.
        """
        informado = next((c.fuso() for c in self.coordenada if c.fuso()), None)
        if informado or not pares_utm:
            return informado
        sistema = self.sistema_referencia_espacial
        candidatos = {
            fuso: utm_para_lon_lat(*pares_utm[0], fuso, sistema)
            for fuso in FUSOS_DA_BAHIA
            if all(utm_para_lon_lat(*par, fuso, sistema) for par in pares_utm)
        }
        if len(candidatos) == 1:
            return next(iter(candidatos))
        if candidatos and referencia:
            return min(
                candidatos,
                key=lambda fuso: abs(candidatos[fuso][0] - referencia[0])
                + abs(candidatos[fuso][1] - referencia[1]),
            )
        return None

    def _pares(self) -> list[tuple[str, tuple[float, float] | None]]:
        """Tipo e (lon, lat) de cada coordenada, em graus ou convertida de UTM."""
        em_graus = [c.lon_lat() for c in self.coordenada]
        em_utm = [c.utm() for c in self.coordenada]
        referencia = next((par for par in em_graus if par), None)
        fuso = self._fuso_utm([par for par in em_utm if par], referencia)
        pares = []
        for coordenada, graus, utm in zip(self.coordenada, em_graus, em_utm):
            par = graus
            if par is None and utm and fuso:
                par = utm_para_lon_lat(*utm, fuso, self.sistema_referencia_espacial)
            pares.append((coordenada.tipo, par))
        return pares

    @model_validator(mode='after')
    def _sistema_citado_no_fuso(self) -> 'AutoInfracao':
        """Usa o datum que o modelo pôs em ``fuso_utm`` quando o sistema veio vazio."""
        if self.sistema_referencia_espacial is None:
            self.sistema_referencia_espacial = next(
                (
                    sistema
                    for par in self.coordenada
                    if (sistema := normalizar_sistema_referencia(par.fuso_utm))
                ),
                None,
            )
        return self

    @computed_field
    @property
    def ponto(self) -> str | None:
        """WKT ``POINT(lon lat)`` do primeiro par do tipo ponto que for convertido."""
        for tipo, par in self._pares():
            if tipo == 'ponto' and par:
                return f'POINT({_wkt_par(par)})'
        return None

    @computed_field
    @property
    def poligono(self) -> str | None:
        """WKT ``POLYGON`` fechado com os vértices, se houver três ou mais.

        Se algum vértice não converter, não monta o polígono: faltaria um canto.
        """
        vertices = [par for tipo, par in self._pares() if tipo == 'vertice']
        if len(vertices) < 3 or any(par is None for par in vertices):
            return None
        if vertices[0] != vertices[-1]:
            vertices.append(vertices[0])
        return f'POLYGON(({", ".join(_wkt_par(par) for par in vertices)}))'


class AutoInterdicao(AutoInfracao):
    """Um auto de infração de interdição citado no trecho."""

    modalidade: Literal['temporaria', 'definitiva'] | None = Field(
        description=(
            'temporaria se o texto diz "Interdição Temporária"; definitiva se diz '
            '"Interdição Definitiva"; null se não diz.'
        )
    )
    atividade_interditada: str | None = Field(
        description=(
            'Atividade interditada que deu causa a interdição.'
        )
    )
    excecao_interdicao: str | None = Field(
        description=(
            'O que continua permitido apesar da interdição (ex.: "exceto para uso '
            'humano e dessedentação animal" -> uso humano e dessedentação animal). '
            'Null se o texto não traz exceção.'
        )
    )
    condicao: str | None = Field(
        description=(
            'Ato ou ação que encerra a interdição (ex.: "até a regularização no órgão '
            'ambiental" -> regularização no órgão ambiental; "até a obtenção da '
            'licença" -> obtenção da licença). Null se o texto não diz.'
        )
    )


class ExtracaoInterdicao(BaseModel):
    """Autos de infração de interdição encontrados no trecho."""

    auto: list[AutoInterdicao] = Field(
        description='Um item por auto de infração de interdição (AIIN) do trecho.'
    )


# Subtipos de auto de infração. Os atributos de cada um saíram dos textos de
# processing.ato com o tipo em processing.ato_tipo_ato (amostra por autuado).


class BemProdutoAutuado(BaseModel):
    """Bem ou produto citado num auto: apreendido, destruído ou inutilizado."""

    descricao: str = Field(
        description=(
            'O que é o item, como está no texto, sem a quantidade (ex.: lenha de '
            'espécies nativas; motosserra STIHL modelo 051; caminhão Mercedes; '
            'carvão vegetal; Saruê (Didelphis aurita)).'
        )
    )
    quantidade: float | None = Field(
        description=(
            'Quantidade do item em número (ex.: "06 (seis)" -> 6; "6,29 ST" -> '
            '6.29). Null se o texto não informar.'
        )
    )
    unidade: str | None = Field(
        description=(
            'Unidade da quantidade como está no texto (ex.: st; m³; MDC; kg; '
            'unidade; peças). Null se a quantidade não tem unidade.'
        )
    )
    valor_avaliado: float | None = Field(
        description=(
            'Valor em reais em que o item foi avaliado, em número (ex.: "avaliado em '
            'R$ 12.000,00" -> 12000). Null se o texto não informar.'
        )
    )
    identificacao: str | None = Field(
        description=(
            'Placa, chassi, Renavam ou número de série do item, como está no texto. '
            'Null se não houver.'
        )
    )

    @field_validator('quantidade', 'valor_avaliado', mode='before')
    @classmethod
    def _numero(cls, valor):
        return normalizar_numero(valor)


DESCRICAO_NOTIFICACAO = (
    'Número do processo de notificação descumprida que deu origem ao auto, no padrão '
    'AAAA-NNNNNN/TEC/NOT-NNNN (ex.: "não atendimento à Notificação nº '
    '2018-003698/TEC/NOT-1040" -> 2018-003698/TEC/NOT-1040). Null se o texto não '
    'citar notificação.'
)
DESCRICAO_AREA_RESTRICAO_LEGAL_USO = (
    'Área com restrição legal de uso atingida, como está no texto: Área de '
    'Preservação Permanente com o corpo hídrico (ex.: APP - faixa marginal do Rio '
    'Formoso), unidade de conservação (ex.: Parque Estadual de Pituaçu), reserva '
    'legal ou terreno de marinha. Null se o texto não citar.'
)


class AutoAdvertencia(AutoInfracao):
    """Um auto de infração de advertência (AIAD) citado no trecho."""

    exigencia: str | None = Field(
        description=(
            'O que o autuado deve fazer para atender a advertência (ex.: "O '
            'responsável deverá manter o saldo do Sistema DOF igual ao do pátio"; '
            '"apresentar o Plano de Recuperação"; "A atividade deverá cessar"). Null '
            'se o texto não diz.'
        )
    )
    prazo_atendimento_dias: int | None = Field(
        description=(
            'Prazo em dias para cumprir a exigência (ex.: "deverá cessar em 90 '
            '(noventa) dias" -> 90). Não é o prazo de 20 dias para interpor recurso. '
            'Null se o texto não diz.'
        )
    )
    nro_notificacao: str | None = Field(description=DESCRICAO_NOTIFICACAO)


class AutoApreensao(AutoInfracao):
    """Um auto de infração de apreensão (AIAP) citado no trecho."""

    bem_apreendido: list[BemProdutoAutuado] = Field(
        description=(
            'Cada bem apreendido: produto (madeira, lenha, carvão, areia), animal, '
            'equipamento (motosserra) ou veículo. Lista vazia se o texto não diz.'
        )
    )
    fiel_depositario: str | None = Field(
        description=(
            'Quem ficou como fiel depositário dos bens, como está no texto (o próprio '
            'autuado, uma pessoa, uma delegacia). Null se o texto não diz.'
        )
    )
    destinacao: str | None = Field(
        description=(
            'O que foi ou deve ser feito com os bens (ex.: doação; soltura; '
            'encaminhado ao CETAS; retido no pátio do INEMA). Null se o texto não '
            'diz.'
        )
    )


class AutoDestruicaoFornos(AutoInfracao):
    """Um auto de destruição de fornos para produção de carvão vegetal (AIDF)."""

    qtd_fornos: int | None = Field(
        description=(
            'Quantidade de fornos destruídos (ex.: "02 (dois) fornos" -> 2; "um forno" '
            '-> 1). Null se o texto não diz.'
        )
    )
    tipo_forno: str | None = Field(
        description='Tipo do forno (ex.: iglu; rabo-quente). Null se o texto não diz.'
    )
    capacidade_por_forno: float | None = Field(
        description=(
            'Capacidade de cada forno em metros de carvão (ex.: "capacidade para 05 '
            '(cinco) metros cada" -> 5). Null se o texto não diz.'
        )
    )
    situacao_forno: Literal['ativo', 'inativo'] | None = Field(
        description=(
            'ativo se os fornos estavam em atividade ou operando; inativo se o texto '
            'diz que estavam inativos ou desativados; null se não diz.'
        )
    )

    @field_validator('capacidade_por_forno', mode='before')
    @classmethod
    def _numero(cls, valor):
        return normalizar_numero(valor)


class AutoDestruicaoProdutos(AutoInfracao):
    """Um auto de destruição ou inutilização de produtos (AIDP) citado no trecho."""

    produto_destruido: list[BemProdutoAutuado] = Field(
        description=(
            'Cada produto destruído ou inutilizado (ex.: 45 m³ de carvão vegetal). '
            'Lista vazia se o texto não diz.'
        )
    )


class AutoDemolicao(AutoInfracao):
    """Um auto de infração de demolição (AIDM) citado no trecho."""

    obra_demolida: list[str] = Field(
        description=(
            'Cada construção ou obra a demolir, como está no texto (ex.: "de casa, '
            'sanitário e fossa" -> casa; sanitário; fossa). Lista vazia se não diz.'
        )
    )
    area_restricao_legal_uso: str | None = Field(description=DESCRICAO_AREA_RESTRICAO_LEGAL_USO)


class AutoEmbargo(AutoInfracao):
    """Um auto de infração de embargo (AIEM) citado no trecho."""

    modalidade: Literal['temporario', 'definitivo'] | None = Field(
        description=(
            'temporario se o texto diz "Embargo Temporário"; definitivo se diz '
            '"Embargo Definitivo"; null se não diz.'
        )
    )
    objeto_embargado: str | None = Field(
        description=(
            'Obra, atividade ou área embargada (ex.: obras de ampliação do '
            'empreendimento; perfuração de poços artesianos). Null se não diz.'
        )
    )
    area_restricao_legal_uso: str | None = Field(description=DESCRICAO_AREA_RESTRICAO_LEGAL_USO)


class AutoMulta(AutoInfracao):
    """Um auto de infração de multa (AIMU) citado no trecho."""

    valor_multa: float | None = Field(
        description=(
            'Valor original da multa em reais, em número (ex.: "valor original de R$ '
            '50.000,00" -> 50000). Na multa diária, o valor por dia. Null se não diz.'
        )
    )
    tipo_multa: Literal['simples', 'diaria'] | None = Field(
        description=(
            'diaria se a multa aplicada é diária; simples se o texto diz multa simples '
            'ou só traz o valor. "Poderá ser aplicada multa diária" é aviso, não a '
            'multa aplicada. Null se o texto não traz a multa.'
        )
    )
    reincidente: bool = Field(
        description=(
            'true se o texto diz que o autuado é reincidente ou "reincidiu"; false '
            'nos demais casos.'
        )
    )
    percentual_desconto: float | None = Field(
        description=(
            'Percentual de redução ou desconto aplicado a esta multa (ex.: "com '
            'redução de 50%" -> 50; "desconto de 60% sobre o montante consolidado do '
            'Auto ... AIMU-0190" -> 60, só para esse auto). Null se não houver.'
        )
    )
    nro_notificacao: str | None = Field(description=DESCRICAO_NOTIFICACAO)

    @field_validator('valor_multa', 'percentual_desconto', mode='before')
    @classmethod
    def _numero(cls, valor):
        return normalizar_numero(valor)


class ExtracaoAdvertencia(BaseModel):
    """Autos de infração de advertência encontrados no trecho."""

    auto: list[AutoAdvertencia] = Field(
        description='Um item por auto de infração de advertência (AIAD) do trecho.'
    )


class ExtracaoApreensao(BaseModel):
    """Autos de infração de apreensão encontrados no trecho."""

    auto: list[AutoApreensao] = Field(
        description='Um item por auto de infração de apreensão (AIAP) do trecho.'
    )


class ExtracaoDestruicaoFornos(BaseModel):
    """Autos de destruição de fornos de carvão encontrados no trecho."""

    auto: list[AutoDestruicaoFornos] = Field(
        description='Um item por auto de destruição de fornos (AIDF) do trecho.'
    )


class ExtracaoDestruicaoProdutos(BaseModel):
    """Autos de destruição ou inutilização de produtos encontrados no trecho."""

    auto: list[AutoDestruicaoProdutos] = Field(
        description='Um item por auto de destruição de produtos (AIDP) do trecho.'
    )


class ExtracaoDemolicao(BaseModel):
    """Autos de infração de demolição encontrados no trecho."""

    auto: list[AutoDemolicao] = Field(
        description='Um item por auto de infração de demolição (AIDM) do trecho.'
    )


class ExtracaoEmbargo(BaseModel):
    """Autos de infração de embargo encontrados no trecho."""

    auto: list[AutoEmbargo] = Field(
        description='Um item por auto de infração de embargo (AIEM) do trecho.'
    )


class ExtracaoMulta(BaseModel):
    """Autos de infração de multa encontrados no trecho."""

    auto: list[AutoMulta] = Field(
        description='Um item por auto de infração de multa (AIMU) do trecho.'
    )
