"""Esquemas Pydantic comuns às extrações: endereço, pessoa e par de coordenadas.

As descrições dos campos vão para o JSON Schema que o modelo recebe, então dizem o que o
modelo deve copiar do texto. Os validadores corrigem o formato do que o modelo devolve
(CEP, município da Bahia) e ``CoordenadaGeografica`` lê os pares em graus ou em UTM.
"""

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from diario_oficial.extracao.normalizacao import normalizar_cep, normalizar_municipio
from diario_oficial.extracao.utils_geo import (
    FUSOS_DA_BAHIA,
    LATITUDE_BAHIA,
    LESTE_UTM,
    LONGITUDE_BAHIA,
    NORTE_UTM,
    grau_decimal,
    metro_utm,
)


class Endereco(BaseModel):
    """Lugar citado no ato: endereço urbano ou localidade rural.

    Todos os campos são obrigatórios no esquema (podem ser nulos) para o modelo decidir
    cada um; campos com default saem do ``required`` e o modelo tende a pulá-los. Sem
    ``examples``: o modelo pequeno copia o exemplo quando o campo não existe no texto.
    """

    localidade: str | None = Field(
        description=(
            'Fazenda, sítio, povoado, assentamento, distrito ou "zona rural", como '
            'está no texto. Não é o município: o nome do município vai em municipio. '
            'Null se o texto só citar o município ou se não houver.'
        )
    )
    logradouro: str | None = Field(
        description=(
            'Rua, avenida ou travessa, sem o número (o número vai em numero). Null se '
            'o lugar for rodovia ou localidade rural sem rua.'
        )
    )
    numero: str | None = Field(
        description='Número do endereço, separado do logradouro (ex.: 123; s/n).'
    )
    complemento: str | None = Field(
        description='Complemento (ex.: galpão 2; lote 5), só se existir no texto.'
    )
    bairro: str | None = Field(description='Bairro, só se existir no texto.')
    rodovia: str | None = Field(
        description='Rodovia e km (ex.: BA 459, km 65), só se existir no texto.'
    )
    cep: str | None = Field(description='CEP, só se existir no texto.')
    municipio: str | None = Field(
        description=(
            'Nome do município. Sem o BA (ex. "Salvador - BA" -> "Salvador", '
            '"Pilão Arcado/BA" -> "Pilão Arcado"). "BA" ou "Bahia" sozinho é o '
            'estado, não o município. Null se o texto não informar.'
        )
    )

    @field_validator('cep')
    @classmethod
    def _cep_no_padrao(cls, valor: str | None) -> str | None:
        return normalizar_cep(valor)

    @field_validator('municipio')
    @classmethod
    def _municipio_da_bahia(cls, valor: str | None) -> str | None:
        """Só aceita um dos 417 municípios da Bahia, com o nome oficial do IBGE."""
        return normalizar_municipio(valor)

    @model_validator(mode='after')
    def _localidade_nao_e_municipio(self) -> 'Endereco':
        """Localidade que é só o nome de um município da Bahia não é localidade.

        Sem município, o nome vai para ``municipio`` (o modelo pôs no campo errado).
        Compara o nome inteiro: "Zona rural de Barreiras" e "Fazenda Barreiras"
        continuam localidade, e o nome de outro município (povoado homônimo) também.
        """
        if (nome := normalizar_municipio(self.localidade)) is None:
            return self
        if self.municipio is None:
            self.municipio = nome
        if nome == self.municipio:
            self.localidade = None
        return self


class Pessoa(BaseModel):
    """Pessoa física ou jurídica citada no ato."""

    nome: str = Field(description='Nome da pessoa ou razão social da empresa.')
    tipo_documento: Literal['CPF', 'CNPJ', 'RG'] | None = Field(
        description='Tipo do documento da pessoa.'
    )
    nro_documento: str | None = Field(
        description='Número do documento, como está no texto.'
    )
    endereco: Endereco | None = Field(
        description=(
            'Endereço da pessoa (residência ou sede da empresa), se o texto informar.'
        )
    )


class CoordenadaGeografica(BaseModel):
    """Um par de coordenadas, copiado como está no texto."""

    latitude: str = Field(
        description=(
            "Latitude exatamente como no texto (ex.: S -12,20388º; -13°15'59.7). Em "
            'UTM, o valor de Y ou norte (ex.: 8405671).'
        )
    )
    longitude: str = Field(
        description=(
            "Longitude exatamente como no texto (ex.: W - 41,75649º; -43°24'39.9). "
            'Em UTM, o valor de X ou leste (ex.: 0494359).'
        )
    )
    fuso_utm: str | None = Field(
        description=(
            'Fuso (zona) UTM, só quando o par está em UTM e o texto informa o fuso '
            '(ex.: "UTM (24L)" -> 24L; "Zona 23" -> 23). Null nos demais casos.'
        )
    )
    tipo: Literal['ponto', 'vertice'] = Field(
        description=(
            'vertice se o par é um dos vértices que delimitam a área (o texto fala em '
            'vértices, poligonal, área delimitada ou compreendida entre os pontos); '
            'ponto nos demais casos (local de constatação, ponto de referência).'
        )
    )

    def utm(self) -> tuple[float, float] | None:
        """Leste e norte em metros, se o par é UTM (em qualquer ordem no texto)."""
        valores = [metro_utm(self.latitude), metro_utm(self.longitude)]
        if None in valores:
            return None
        leste, norte = sorted(valores)
        if not (LESTE_UTM[0] <= leste <= LESTE_UTM[1]):
            return None
        if not (NORTE_UTM[0] <= norte <= NORTE_UTM[1]):
            return None
        return leste, norte

    def fuso(self) -> int | None:
        """Número do fuso informado, se for um dos fusos da Bahia."""
        achado = re.search(r'\b(\d{2})\s*[A-Z]?\b', self.fuso_utm or '', re.IGNORECASE)
        numero = int(achado.group(1)) if achado else None
        return numero if numero in FUSOS_DA_BAHIA else None

    def lon_lat(self) -> tuple[float, float] | None:
        """Longitude e latitude com sinal (sul e oeste), ou ``None`` se não converter.

        Só para pares em graus; os em UTM são convertidos por ``AutoInfracao``, que
        conhece o sistema de referência e os demais pares do auto.

        Toda a Bahia fica ao sul do equador e a oeste de Greenwich, então o sinal sai
        da posição e não do texto. Se o texto inverteu a ordem (``x -41,8 y -13,0``),
        os valores são trocados. Pares fora da Bahia voltam ``None``.
        """
        latitude = grau_decimal(self.latitude)
        longitude = grau_decimal(self.longitude)
        if latitude is None or longitude is None:
            return None
        if latitude > longitude:
            latitude, longitude = longitude, latitude
        if not (LATITUDE_BAHIA[0] <= latitude <= LATITUDE_BAHIA[1]):
            return None
        if not (LONGITUDE_BAHIA[0] <= longitude <= LONGITUDE_BAHIA[1]):
            return None
        return -round(longitude, 7), -round(latitude, 7)
