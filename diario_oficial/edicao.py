"""Consulta a edição do DOE de uma data.

É a mesma consulta que o campo de data do site faz antes de abrir o sumário. Feita daqui,
dispensa o navegador nas datas sem edição e o preenchimento do campo, que falhava quando
o calendário da página não reformatava a data digitada a tempo.
"""

import datetime
import warnings
from typing import NamedTuple

import requests

URL_SITE = 'https://dool.egba.ba.gov.br'
URL_EDICOES_DA_DATA = f'{URL_SITE}/apifront/portal/edicoes/edicoes_from_data/'
MENSAGEM_SEM_EDICAO = 'Edição não existente!'


class EdicaoDoDia(NamedTuple):
    nro_edicao: int
    # Endereço do sumário html, o mesmo para onde o site redireciona
    url: str


def buscar_edicao(data: datetime.date) -> EdicaoDoDia | None:
    """Busca a edição publicada na data.

    Havendo mais de uma edição no dia, usa a primeira da resposta, como o site.

    Returns:
        A edição, ou None quando o site informa que não há edição na data.

    Raises:
        requests.RequestException: Falha de rede ou resposta que não é a esperada.
        RuntimeError: O site devolveu um erro diferente de edição inexistente. Não pode
            ser confundido com data sem edição, que é gravada e nunca mais raspada.
    """
    # O certificado do site não é validado, como na coleta do conteúdo dos links
    warnings.filterwarnings('ignore', message='Unverified HTTPS request')
    resposta = requests.get(
        f'{URL_EDICOES_DA_DATA}{data:%Y-%m-%d}', verify=False, timeout=(5, 30)
    )
    resposta.raise_for_status()
    dados = resposta.json()

    if dados['erro']:
        if dados['msg'] == MENSAGEM_SEM_EDICAO:
            return None
        raise RuntimeError(f'Erro ao buscar a edição de {data:%d-%m-%Y}: {dados["msg"]}')

    edicao = dados['itens'][0]
    id_edicao = edicao['id']
    return EdicaoDoDia(
        nro_edicao=int(edicao['numero']),
        url=f'{URL_SITE}/portal/visualizacoes/html/{id_edicao}#/p:1/e:{id_edicao}',
    )
