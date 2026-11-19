"""Dados e regras geográficas da extração: coordenadas e municípios da Bahia.

Coordenadas escritas no texto são lidas em graus ou em UTM; as UTM são convertidas para
geográficas com o pyproj, no datum do sistema de referência informado (SIRGAS 2000 se
não houver).

``MUNICIPIOS_BA`` traz os 417 municípios da Bahia, com o nome oficial do IBGE. Fonte: API
de localidades do IBGE
(``servicodados.ibge.gov.br/api/v1/localidades/estados/29/municipios``), baixada em
2026-11-12. Lista fixa para a extração não depender de rede nem de banco.
"""

import re
from functools import lru_cache

from pyproj import Transformer

GRAU_MINUTO_SEGUNDO = re.compile(
    r'(?P<grau>\d{1,3})\s*[°º]\s*(?P<minuto>\d{1,2})\s*[\'’′]\s*'
    r'(?P<segundo>\d{1,2}(?:[.,]\d+)?)?'
)
NUMERO_DECIMAL = re.compile(r'\d+(?:\.\d+)?')

# Faixa da Bahia (com folga), em valor absoluto: latitude sul e longitude oeste.
LATITUDE_BAHIA = (7.0, 20.0)
LONGITUDE_BAHIA = (36.0, 48.0)

# UTM: a Bahia fica nos fusos 23 e 24 do hemisfério sul. Para cada sistema de referência,
# o EPSG geográfico e o da projeção UTM de cada fuso. Sem sistema no texto, usa o
# SIRGAS 2000, o oficial do Brasil.
EPSG_POR_SISTEMA = {
    'SIRGAS 2000': (4674, {23: 31983, 24: 31984}),
    'SAD 69': (4618, {23: 29193, 24: 29194}),
    'WGS 84': (4326, {23: 32723, 24: 32724}),
    'Córrego Alegre': (4225, {23: 22523, 24: 22524}),
}
SISTEMA_PADRAO = 'SIRGAS 2000'
FUSOS_DA_BAHIA = (23, 24)
LESTE_UTM = (100_000.0, 900_000.0)
NORTE_UTM = (7_800_000.0, 9_300_000.0)
METRO_UTM = re.compile(r'\d{6,7}(?:[.,]\d+)?')
# Limite da Bahia sem folga (lon_min, lon_max, lat_min, lat_max), para escolher o fuso.
LIMITE_BAHIA = (-46.7, -37.2, -18.4, -8.4)


def grau_decimal(valor: str | None) -> float | None:
    """Valor absoluto em graus decimais de uma latitude ou longitude escrita no texto.

    Lê grau-minuto-segundo (``10°11’58,7”``) e grau decimal com vírgula ou ponto
    (``S -12,20388º``, ``-44. 56615``). O sinal e as letras S/W são ignorados: quem
    chama aplica o hemisfério. Devolve ``None`` sem número ou para valores fora de
    graus (coordenada UTM, como ``8405671``).
    """
    if not valor:
        return None
    if achado := GRAU_MINUTO_SEGUNDO.search(valor):
        segundo = float((achado.group('segundo') or '0').replace(',', '.'))
        return (
            int(achado.group('grau'))
            + int(achado.group('minuto')) / 60
            + segundo / 3600
        )
    texto = re.sub(r'\s+', '', valor).replace(',', '.')
    texto = re.sub(r'\.{2,}', '.', texto)
    achado = NUMERO_DECIMAL.search(texto)
    if achado is None:
        return None
    numero = float(achado.group())
    return numero if numero <= 180 else None


def metro_utm(valor: str | None) -> float | None:
    """Valor em metros de uma coordenada UTM escrita no texto (``Y8599194.221``)."""
    achado = METRO_UTM.search(re.sub(r'\s+', '', valor or ''))
    return float(achado.group().replace(',', '.')) if achado else None


@lru_cache
def _transformador(origem: int, destino: int) -> Transformer:
    return Transformer.from_crs(f'EPSG:{origem}', f'EPSG:{destino}', always_xy=True)


def utm_para_lon_lat(
    leste: float, norte: float, fuso: int, sistema: str | None
) -> tuple[float, float] | None:
    """Longitude e latitude, no mesmo datum, de um par UTM do hemisfério sul.

    Devolve ``None`` se o fuso não for da Bahia ou se o ponto cair fora dela.
    """
    geografico, projecoes = EPSG_POR_SISTEMA.get(
        sistema or SISTEMA_PADRAO, EPSG_POR_SISTEMA[SISTEMA_PADRAO]
    )
    if fuso not in projecoes:
        return None
    longitude, latitude = _transformador(projecoes[fuso], geografico).transform(
        leste, norte
    )
    lon_min, lon_max, lat_min, lat_max = LIMITE_BAHIA
    if not (lon_min <= longitude <= lon_max and lat_min <= latitude <= lat_max):
        return None
    return round(longitude, 7), round(latitude, 7)


PAR_WKT = re.compile(r'(-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?)')


def wkt_em_sirgas(wkt: str | None, sistema: str | None) -> str | None:
    """O WKT em longitude/latitude do ``sistema`` convertido para o SIRGAS 2000.

    Sem sistema (ou já em SIRGAS 2000), devolve o WKT como está.
    """
    if not wkt:
        return None
    origem = EPSG_POR_SISTEMA.get(
        sistema or SISTEMA_PADRAO, EPSG_POR_SISTEMA[SISTEMA_PADRAO]
    )[0]
    destino = EPSG_POR_SISTEMA[SISTEMA_PADRAO][0]
    if origem == destino:
        return wkt
    transformador = _transformador(origem, destino)

    def converter(achado: re.Match) -> str:
        longitude, latitude = transformador.transform(
            float(achado.group(1)), float(achado.group(2))
        )
        return f'{round(longitude, 7)} {round(latitude, 7)}'

    return PAR_WKT.sub(converter, wkt)


# Municípios da Bahia (IBGE), em ordem alfabética.
MUNICIPIOS_BA = (
    'Abaré',
    'Abaíra',
    'Acajutiba',
    'Adustina',
    'Aiquara',
    'Alagoinhas',
    'Alcobaça',
    'Almadina',
    'Amargosa',
    'Amélia Rodrigues',
    'América Dourada',
    'Anagé',
    'Andaraí',
    'Andorinha',
    'Angical',
    'Anguera',
    'Antas',
    'Antônio Cardoso',
    'Antônio Gonçalves',
    'Aporá',
    'Apuarema',
    'Aracatu',
    'Araci',
    'Aramari',
    'Arataca',
    'Aratuípe',
    'Araçás',
    'Aurelino Leal',
    'Baianópolis',
    'Baixa Grande',
    'Banzaê',
    'Barra',
    'Barra da Estiva',
    'Barra do Choça',
    'Barra do Mendes',
    'Barra do Rocha',
    'Barreiras',
    'Barro Alto',
    'Barro Preto',
    'Barrocas',
    'Belmonte',
    'Belo Campo',
    'Biritinga',
    'Boa Nova',
    'Boa Vista do Tupim',
    'Bom Jesus da Lapa',
    'Bom Jesus da Serra',
    'Boninal',
    'Bonito',
    'Boquira',
    'Botuporã',
    'Brejolândia',
    'Brejões',
    'Brotas de Macaúbas',
    'Brumado',
    'Buerarema',
    'Buritirama',
    'Caatiba',
    'Cabaceiras do Paraguaçu',
    'Cachoeira',
    'Caculé',
    'Caetanos',
    'Caetité',
    'Cafarnaum',
    'Cairu',
    'Caldeirão Grande',
    'Camacan',
    'Camamu',
    'Camaçari',
    'Campo Alegre de Lourdes',
    'Campo Formoso',
    'Canarana',
    'Canavieiras',
    'Candeal',
    'Candeias',
    'Candiba',
    'Cansanção',
    'Canudos',
    'Canápolis',
    'Capela do Alto Alegre',
    'Capim Grosso',
    'Caravelas',
    'Caraíbas',
    'Cardeal da Silva',
    'Carinhanha',
    'Casa Nova',
    'Castro Alves',
    'Catolândia',
    'Catu',
    'Caturama',
    'Caém',
    'Central',
    'Chorrochó',
    'Cipó',
    'Coaraci',
    'Cocos',
    'Conceição da Feira',
    'Conceição do Almeida',
    'Conceição do Coité',
    'Conceição do Jacuípe',
    'Conde',
    'Condeúba',
    'Contendas do Sincorá',
    'Coração de Maria',
    'Cordeiros',
    'Coribe',
    'Coronel João Sá',
    'Correntina',
    'Cotegipe',
    'Cravolândia',
    'Cristópolis',
    'Crisópolis',
    'Cruz das Almas',
    'Curaçá',
    'Cândido Sales',
    'Cícero Dantas',
    "Dias d'Ávila",
    'Dom Basílio',
    'Dom Macedo Costa',
    'Dário Meira',
    'Elísio Medrado',
    'Encruzilhada',
    'Entre Rios',
    'Esplanada',
    'Euclides da Cunha',
    'Eunápolis',
    'Feira da Mata',
    'Feira de Santana',
    'Filadélfia',
    'Firmino Alves',
    'Floresta Azul',
    'Formosa do Rio Preto',
    'Fátima',
    'Gandu',
    'Gavião',
    'Gentio do Ouro',
    'Glória',
    'Gongogi',
    'Governador Mangabeira',
    'Guajeru',
    'Guanambi',
    'Guaratinga',
    'Heliópolis',
    'Iaçu',
    'Ibiassucê',
    'Ibicaraí',
    'Ibicoara',
    'Ibicuí',
    'Ibipeba',
    'Ibipitanga',
    'Ibiquera',
    'Ibirapitanga',
    'Ibirapuã',
    'Ibirataia',
    'Ibitiara',
    'Ibititá',
    'Ibotirama',
    'Ichu',
    'Igaporã',
    'Igrapiúna',
    'Iguaí',
    'Ilhéus',
    'Inhambupe',
    'Ipecaetá',
    'Ipiaú',
    'Ipirá',
    'Ipupiara',
    'Irajuba',
    'Iramaia',
    'Iraquara',
    'Irará',
    'Irecê',
    'Itabela',
    'Itaberaba',
    'Itabuna',
    'Itacaré',
    'Itaeté',
    'Itagi',
    'Itagibá',
    'Itagimirim',
    'Itaguaçu da Bahia',
    'Itaju do Colônia',
    'Itajuípe',
    'Itamaraju',
    'Itamari',
    'Itambé',
    'Itanagra',
    'Itanhém',
    'Itaparica',
    'Itapebi',
    'Itapetinga',
    'Itapicuru',
    'Itapitanga',
    'Itapé',
    'Itaquara',
    'Itarantim',
    'Itatim',
    'Itiruçu',
    'Itiúba',
    'Itororó',
    'Ituaçu',
    'Ituberá',
    'Iuiu',
    'Jaborandi',
    'Jacaraci',
    'Jacobina',
    'Jaguaquara',
    'Jaguarari',
    'Jaguaripe',
    'Jandaíra',
    'Jequié',
    'Jeremoabo',
    'Jiquiriçá',
    'Jitaúna',
    'João Dourado',
    'Juazeiro',
    'Jucuruçu',
    'Jussara',
    'Jussari',
    'Jussiape',
    'Lafaiete Coutinho',
    'Lagoa Real',
    'Laje',
    'Lajedinho',
    'Lajedo do Tabocal',
    'Lajedão',
    'Lamarão',
    'Lapão',
    'Lauro de Freitas',
    'Lençóis',
    'Licínio de Almeida',
    'Livramento de Nossa Senhora',
    'Luís Eduardo Magalhães',
    'Macajuba',
    'Macarani',
    'Macaúbas',
    'Macururé',
    'Madre de Deus',
    'Maetinga',
    'Maiquinique',
    'Mairi',
    'Malhada',
    'Malhada de Pedras',
    'Manoel Vitorino',
    'Mansidão',
    'Maracás',
    'Maragogipe',
    'Maraú',
    'Marcionílio Souza',
    'Mascote',
    'Mata de São João',
    'Matina',
    'Medeiros Neto',
    'Miguel Calmon',
    'Milagres',
    'Mirangaba',
    'Mirante',
    'Monte Santo',
    'Morpará',
    'Morro do Chapéu',
    'Mortugaba',
    'Mucugê',
    'Mucuri',
    'Mulungu do Morro',
    'Mundo Novo',
    'Muniz Ferreira',
    'Muquém do São Francisco',
    'Muritiba',
    'Mutuípe',
    'Nazaré',
    'Nilo Peçanha',
    'Nordestina',
    'Nova Canaã',
    'Nova Fátima',
    'Nova Ibiá',
    'Nova Itarana',
    'Nova Redenção',
    'Nova Soure',
    'Nova Viçosa',
    'Novo Horizonte',
    'Novo Triunfo',
    'Olindina',
    'Oliveira dos Brejinhos',
    'Ouriçangas',
    'Ourolândia',
    'Palmas de Monte Alto',
    'Palmeiras',
    'Paramirim',
    'Paratinga',
    'Paripiranga',
    'Pau Brasil',
    'Paulo Afonso',
    'Pedro Alexandre',
    'Pedrão',
    'Piatã',
    'Pilão Arcado',
    'Pindaí',
    'Pindobaçu',
    'Pintadas',
    'Piraí do Norte',
    'Piripá',
    'Piritiba',
    'Planaltino',
    'Planalto',
    'Pojuca',
    'Ponto Novo',
    'Porto Seguro',
    'Potiraguá',
    'Poções',
    'Prado',
    'Presidente Dutra',
    'Presidente Jânio Quadros',
    'Presidente Tancredo Neves',
    'Pé de Serra',
    'Queimadas',
    'Quijingue',
    'Quixabeira',
    'Rafael Jambeiro',
    'Remanso',
    'Retirolândia',
    'Riacho de Santana',
    'Riachão das Neves',
    'Riachão do Jacuípe',
    'Ribeira do Amparo',
    'Ribeira do Pombal',
    'Ribeirão do Largo',
    'Rio Real',
    'Rio de Contas',
    'Rio do Antônio',
    'Rio do Pires',
    'Rodelas',
    'Ruy Barbosa',
    'Salinas da Margarida',
    'Salvador',
    'Santa Brígida',
    'Santa Bárbara',
    'Santa Cruz Cabrália',
    'Santa Cruz da Vitória',
    'Santa Inês',
    'Santa Luzia',
    'Santa Maria da Vitória',
    'Santa Rita de Cássia',
    'Santa Terezinha',
    'Santaluz',
    'Santana',
    'Santanópolis',
    'Santo Amaro',
    'Santo Antônio de Jesus',
    'Santo Estêvão',
    'Sapeaçu',
    'Saubara',
    'Saúde',
    'Seabra',
    'Sebastião Laranjeiras',
    'Senhor do Bonfim',
    'Sento Sé',
    'Serra Dourada',
    'Serra Preta',
    'Serra do Ramalho',
    'Serrinha',
    'Serrolândia',
    'Simões Filho',
    'Sobradinho',
    'Souto Soares',
    'Sátiro Dias',
    'São Desidério',
    'São Domingos',
    'São Felipe',
    'São Francisco do Conde',
    'São Félix',
    'São Félix do Coribe',
    'São Gabriel',
    'São Gonçalo dos Campos',
    'São José da Vitória',
    'São José do Jacuípe',
    'São Miguel das Matas',
    'São Sebastião do Passé',
    'Sítio do Mato',
    'Sítio do Quinto',
    'Tabocas do Brejo Velho',
    'Tanhaçu',
    'Tanque Novo',
    'Tanquinho',
    'Taperoá',
    'Tapiramutá',
    'Teixeira de Freitas',
    'Teodoro Sampaio',
    'Teofilândia',
    'Teolândia',
    'Terra Nova',
    'Tremedal',
    'Tucano',
    'Uauá',
    'Ubaitaba',
    'Ubatã',
    'Ubaíra',
    'Uibaí',
    'Umburanas',
    'Una',
    'Urandi',
    'Uruçuca',
    'Utinga',
    'Valente',
    'Valença',
    'Varzedo',
    'Vera Cruz',
    'Vereda',
    'Vitória da Conquista',
    'Várzea Nova',
    'Várzea da Roça',
    'Várzea do Poço',
    'Wagner',
    'Wanderley',
    'Wenceslau Guimarães',
    'Xique-Xique',
    'Água Fria',
    'Érico Cardoso',
)
