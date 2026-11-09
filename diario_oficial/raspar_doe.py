"""Codigo para raspar dados do DOE.
Estruturação dos niveis do diario oficial bahia
NIVEL 1 = EXECUTIVO, LICITAÇÕES, MUNICÍPIOS, ESPECIAL, DIVERSOS
NIVEL 2 = SECRETARIA, PROCURADORIA
NIVEL 3 = Superintendencias,  Diretoria, Superintendência,
          Superintendências, Companhia, Departamento, Instituto, Policia, Corpo,
NIVEL 4 = Atos, Outros

A árvore do sumário é lida como uma lista plana de elementos '.folder' (na ordem em
que aparecem na página). O nível de cada pasta é deduzido pelo texto e pela posição,
guardando o nome da pasta-pai atual de cada nível.
"""

import datetime
import time

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import util as u
from dados import doe_bruto  # noqa: F401 (reexportado para cli.py)
from diario_oficial.settings import Settings

# Primeiro data do diário oficial 05/01/2016??

site_link = 'https://dool.egba.ba.gov.br/'
URL_CONTEUDO_PUBLICACAO = (
    'https://dool.egba.ba.gov.br/apifront/portal/edicoes/publicacoes_ver_conteudo/'
)

# O site às vezes devolve a página inicial sem o botão da versão html. Esperar mais não
# adianta, porque a página não muda sozinha: é preciso carregá-la de novo.
TENTATIVAS_CARREGAR_PAGINA = 3
SEGUNDOS_ESPERA_BOTAO_HTML = 20

# Lista de pastas que serão abertas para coleta de dados
# Nível 1
selecao_pasta_nivel_1 = ['EXECUTIVO']  # "LICITAÇÕES"

# Nível 2 (Secretarias)
# Não adicionar muitas secretarias por que isso causa um bug na renderização da árvore
selecao_pasta_nivel_2_executivo = [
    # "DECRETOS FINANCEIROS",
    # "SECRETARIA DE RELAÇÕES INSTITUCIONAIS",
    # "SECRETARIA DA ADMINISTRAÇÃO",
    # 'PROCURADORIA GERAL DO ESTADO', # ver se consegue tirar a redundancia com LICITAÇÕES
    'SECRETARIA DO MEIO AMBIENTE',
    # "SECRETARIA DA EDUCAÇÃO",
    # "SECRETARIA DA FAZENDA",
]
selecao_pasta_nivel_2_licitacao = []  # "AVISOS DE LICITAÇÃO"
selecao_pasta_nivel_2_municipio = []
selecao_pasta_nivel_2_diverso = []
selecao_pasta_nivel_2_especial = []

selecao_pasta_nivel_2 = set(
    selecao_pasta_nivel_2_executivo
    + selecao_pasta_nivel_2_licitacao
    + selecao_pasta_nivel_2_municipio
    + selecao_pasta_nivel_2_diverso
    + selecao_pasta_nivel_2_especial
)

# Separar atos das instituições
tipo_ato = ['Portarias', 'Outros', 'Resoluções']
tipo_adm_direta = [
    'Diretoria',
    'Superintendência',
    'Superintendências',
    'Companhia',
    'Departamento',
    'Instituto',
    'Policia',
    'Corpo',
]
tipo_adm_indireta = ['Diretoria', 'Diretoria Geral']


def _listar_pastas(navegador) -> list:
    """Lista as pastas visíveis do sumário como pares (texto, elemento).

    O texto é lido uma única vez por elemento: cada leitura de `.text` é uma chamada
    HTTP ao Selenium remoto. Pastas sem texto são descartadas.
    """
    return [
        (texto, el)
        for el in navegador.find_elements(By.CLASS_NAME, 'folder')
        if (texto := el.text) != ''
    ]


def abrir_pastas(navegador, pastas):
    """Clica (abre) as pastas visíveis cujo nome está em `pastas`.

    Args:
        pastas: Nomes das pastas, ex.: ['EXECUTIVO', 'LICITAÇÕES', 'MUNICÍPIOS'].
    """
    for texto, el in _listar_pastas(navegador):
        if texto in pastas:
            try:
                time.sleep(0.5)
                el.click()
            except Exception as e:
                print(e)


def coletar_lista_link_ato(navegador, pasta) -> list[dict]:
    """Abre uma pasta de atos, lista os atos (links que começam com '#') e a fecha."""
    time.sleep(0.5)
    pasta.click()
    lista_ato = []
    for link in navegador.find_elements(By.TAG_NAME, 'a'):
        texto = link.text
        if texto != '' and texto[0] == '#':
            identificador = link.get_attribute('data-materia-id')
            lista_ato.append(
                {
                    'nome': texto,
                    'identificador': identificador,
                    'link': f'{URL_CONTEUDO_PUBLICACAO}{identificador}',
                }
            )
    time.sleep(0.5)
    pasta.click()
    return lista_ato


def _adicionar(pai: dict, chave: str, filho: str, valor):
    """Faz pai[chave][filho] = valor.

    Se pai[chave] estiver vazio (inclusive uma lista de atos vazia), ele é trocado por
    {filho: valor}. É o comportamento original quando a heurística de níveis aponta
    para uma pasta de atos.
    """
    if not pai[chave]:
        pai[chave] = {filho: valor}
    else:
        pai[chave].update({filho: valor})


def _confirmar_modal_html(navegador, wdw):
    """Espera a janela de continuar na versão html e clica no botão dela."""
    wdw.until(EC.presence_of_element_located((By.CLASS_NAME, 'modal-footer')))
    navegador.find_element(By.CLASS_NAME, 'modal-footer').find_element(
        By.TAG_NAME, 'button'
    ).click()


def _carregar_botao_html(navegador):
    """Carrega a página inicial até o botão da versão html ficar clicável.

    Returns:
        O elemento do botão.

    Raises:
        TimeoutException: Se o botão não aparecer em nenhuma das tentativas.
    """
    espera = WebDriverWait(
        navegador, timeout=SEGUNDOS_ESPERA_BOTAO_HTML, poll_frequency=0.5
    )
    for tentativa in range(1, TENTATIVAS_CARREGAR_PAGINA + 1):
        navegador.get(site_link)
        try:
            return espera.until(EC.element_to_be_clickable((By.ID, 'downloadHTML')))
        except TimeoutException:
            if tentativa == TENTATIVAS_CARREGAR_PAGINA:
                raise
            print(f'Botão html não apareceu (tentativa {tentativa}); recarregando')


def _abrir_edicao(navegador, wdw, data_: str):
    """Abre o sumário html da edição da data informada.

    Args:
        data_: Data no formato 'DD-MM-YYYY'.

    Returns:
        (número da edição, url) ou None quando a edição não existe.
    """
    # Clicar no botão da versão html do diário oficial (espera a página carregar)
    _carregar_botao_html(navegador).click()
    _confirmar_modal_html(navegador, wdw)

    # Selecionando a data
    print('Clear date input')
    navegador.find_element(By.CLASS_NAME, 'date-input').clear()
    time.sleep(0.5)
    navegador.switch_to.alert.accept()
    print('Send date input')
    navegador.find_element(By.CLASS_NAME, 'date-input').send_keys(data_)
    print('Click date input')
    navegador.find_element(By.CLASS_NAME, 'date-input').click()
    print('Click search button')
    navegador.find_element(By.CLASS_NAME, 'fa-search').click()

    try:
        time.sleep(2)
        alert = wdw.until(lambda d: d.switch_to.alert)
        if alert.text == 'Edição não existente!':
            alert.accept()
            time.sleep(1)
            print(f'Edição não existe: {data_}')
            return None
    except Exception:
        print(f'Edição existente: {data_}')

    _confirmar_modal_html(navegador, wdw)

    edicao = int(
        navegador.find_element(By.CLASS_NAME, 'text-center')
        .find_element(By.TAG_NAME, 'strong')
        .text.split()[-1]
    )
    return edicao, navegador.current_url


def _montar_nivel_2(pastas, lista_pasta_nivel_2) -> dict:
    """Cria a árvore {poder: {secretaria: {}}} com as pastas selecionadas."""
    arvore = {}
    n1 = None
    for texto, _ in pastas:
        if texto in selecao_pasta_nivel_1:
            n1 = texto
            arvore[n1] = {}
        elif texto in lista_pasta_nivel_2 and texto in selecao_pasta_nivel_2:
            arvore[n1][texto] = {}
    return arvore


def _coletar_nivel_3(
    navegador, arvore, pastas, lista_pasta_nivel_2, lista_pasta_nivel_3
):
    """Adiciona as pastas de adm direta e coleta os atos que estão no nível 3."""
    n1 = n2 = None
    for texto, el in pastas:
        if texto in selecao_pasta_nivel_1:
            n1 = texto
        if texto in lista_pasta_nivel_2:
            n2 = texto
        if texto not in lista_pasta_nivel_3:
            continue
        if u.check_word_or_list_exist_in_list(texto, tipo_adm_direta):
            arvore[n1][n2][texto] = {}
        if u.check_word_or_list_exist_in_list(texto, tipo_ato):
            print(texto)
            arvore[n1][n2][texto] = coletar_lista_link_ato(navegador, el)


def _coletar_nivel_4(navegador, arvore, lista_pasta_nivel_2, lista_pasta_clicar):
    """Coleta a primeira pasta de atos que aparece depois de cada pasta de adm direta."""
    n1 = n2 = n3 = None
    aguardando_ato = False
    for texto, el in _listar_pastas(navegador):
        if texto in selecao_pasta_nivel_1:
            n1 = texto
            aguardando_ato = False
        if texto in lista_pasta_nivel_2:
            n2 = texto
        if texto in lista_pasta_clicar and u.check_word_or_list_exist_in_list(
            texto, tipo_adm_direta
        ):
            n3 = texto
            aguardando_ato = True
        if aguardando_ato and u.check_word_or_list_exist_in_list(texto, tipo_ato):
            print(texto)
            pai = arvore[n1][n2]
            if not pai[n3]:
                pai[n3] = {texto: coletar_lista_link_ato(navegador, el)}
            aguardando_ato = False


def _percorrer_nivel_5(pastas, lista_pasta_nivel_2, lista_pasta_nivel_3):
    """Percorre as pastas acompanhando a posição na árvore para o nível 5.

    A pasta de nível 3 atual é deduzida contando quantas pastas com nome de nível 3
    já apareceram (`count_nivel_3`). O nível 4 (Diretoria, Diretoria Geral) só é
    considerado depois que essa contagem passa do tamanho da lista do nível 3.

    Yields:
        (texto, elemento, n1, n2, count_nivel_3, n4, ativo). A pasta de nível 3 é
        `lista_pasta_nivel_3[count_nivel_3 - 1]`; `ativo` indica que já se está
        dentro de uma pasta de adm indireta.
    """
    n1 = n2 = n4 = None
    count_nivel_3 = count_nivel_4 = 0
    for texto, el in pastas:
        if texto in selecao_pasta_nivel_1:
            n1 = texto
            count_nivel_3 = count_nivel_4 = 0
        if texto in lista_pasta_nivel_2:
            n2 = texto
        if texto in lista_pasta_nivel_3:
            count_nivel_3 += 1
        if texto in tipo_adm_indireta and count_nivel_3 > len(lista_pasta_nivel_3):
            n4 = texto
            count_nivel_4 += 1
        ativo = count_nivel_4 != 0
        if texto in tipo_adm_indireta and ativo and texto in lista_pasta_nivel_3:
            count_nivel_3 -= 1
        yield texto, el, n1, n2, count_nivel_3, n4, ativo


def _coletar_nivel_5(navegador, arvore, lista_pasta_nivel_2, lista_pasta_nivel_3):
    """Abre as pastas de adm indireta (Diretorias) e coleta os atos dentro delas."""
    print('Abrindo pastas nivel 5')
    for texto, _, n1, n2, count_nivel_3, _, ativo in _percorrer_nivel_5(
        _listar_pastas(navegador), lista_pasta_nivel_2, lista_pasta_nivel_3
    ):
        if texto in tipo_adm_indireta and ativo:
            # TODO: abre (clica) todas as Diretorias a cada Diretoria encontrada,
            # iterando sobre a lista antiga de elementos; pode reabrir/fechar pastas.
            abrir_pastas(navegador, set(tipo_adm_indireta))
            pasta_nivel_3 = lista_pasta_nivel_3[count_nivel_3 - 1]
            _adicionar(arvore[n1][n2], pasta_nivel_3, texto, {})

    print('Coletando dados no NIVEL 5')
    for texto, el, n1, n2, count_nivel_3, n4, ativo in _percorrer_nivel_5(
        _listar_pastas(navegador), lista_pasta_nivel_2, lista_pasta_nivel_3
    ):
        if ativo and u.check_word_or_list_exist_in_list(texto, tipo_ato):
            print(texto)
            pasta_nivel_3 = lista_pasta_nivel_3[count_nivel_3 - 1]
            pai = arvore[n1][n2][pasta_nivel_3]
            if not pai[n4]:
                pai[n4] = {texto: coletar_lista_link_ato(navegador, el)}


def raspar_diario_oficial(data: datetime.date) -> dict:
    """Coleta os dados sumarizados do diario oficial do Estado da Bahia.

    Args:
        data: Data do diario oficial.

    Returns:
        dict com 'doe_json', 'nro_edicao', 'dt_edicao', 'existe' e 'url', ou
        {'dt_edicao': data, 'existe': False} quando não há edição na data.
    """
    data_ = data.strftime('%d-%m-%Y')
    print(f'Raspando o Diario oficial de: {data}')
    settings = Settings()
    endereco_selenium = f'{settings.SELENIUM_ADDRESS}:{settings.SELENIUM_PORT}'
    print(endereco_selenium)
    navegador = webdriver.Remote(endereco_selenium, options=webdriver.ChromeOptions())
    try:
        wdw = WebDriverWait(navegador, timeout=60, poll_frequency=0.5)

        edicao_aberta = _abrir_edicao(navegador, wdw, data_)
        if edicao_aberta is None:
            return {'dt_edicao': data, 'existe': False}
        edicao, url = edicao_aberta

        # NIVEL 1 (Poder)
        lista_pasta_nivel_1 = [texto for texto, _ in _listar_pastas(navegador)]
        abrir_pastas(navegador, selecao_pasta_nivel_1)

        # NIVEL 2 (Secretaria)
        pastas = _listar_pastas(navegador)
        lista_pasta_nivel_2 = [t for t, _ in pastas if t not in lista_pasta_nivel_1]
        arvore = _montar_nivel_2(pastas, lista_pasta_nivel_2)
        print(arvore)
        abrir_pastas(navegador, selecao_pasta_nivel_2)

        # NIVEL 3 (Autarquias, Superintendências e atos da secretaria)
        print('Construindo pastas nivel 3')
        pastas = _listar_pastas(navegador)
        lista_pasta_nivel_3 = [
            t
            for t, _ in pastas
            if t not in lista_pasta_nivel_1
            and t not in lista_pasta_nivel_2
            # Todas as pastas nivel 3 tem padrão camel case (ex. Portaria)
            and t[1].islower()
        ]
        _coletar_nivel_3(
            navegador, arvore, pastas, lista_pasta_nivel_2, lista_pasta_nivel_3
        )
        lista_pasta_clicar = set(lista_pasta_nivel_3) - set(tipo_ato)
        abrir_pastas(navegador, lista_pasta_clicar)

        # NIVEL 4 (Atos das autarquias/superintendências)
        print('Construindo pastas nivel 4')
        _coletar_nivel_4(navegador, arvore, lista_pasta_nivel_2, lista_pasta_clicar)

        # NIVEL 5 (Diretoria, Diretoria Geral → atos)
        _coletar_nivel_5(navegador, arvore, lista_pasta_nivel_2, lista_pasta_nivel_3)
    finally:
        navegador.quit()

    return {
        'doe_json': arvore,
        'nro_edicao': edicao,
        'dt_edicao': data,
        'existe': True,
        'url': url,
    }


def coleta_doe_data(data: datetime.date) -> bool:
    """Raspa e salva no banco o diário oficial de uma data, se ainda não foi coletado.

    Returns:
        True se a data tem edição em `doe_bruto` (com ou sem publicações).
    """
    registro = doe_bruto.check_if_date_doe_coleted(data)
    if registro is not None:
        return registro.existe
    try:
        resultado = raspar_diario_oficial(data=data)
    except Exception as exception:
        print(exception)
        return False
    try:
        doe_bruto.save_data(**resultado)
    except Exception as e:
        print(f'Erro: {e}')
        return False
    return resultado['existe']
