"""Codigo para raspar dados do DOE.
Estruturação dos niveis do diario oficial bahia
NIVEL 1 = EXECUTIVO, LICITAÇÕES, MUNICÍPIOS, ESPECIAL, DIVERSOS
NIVEL 2 = SECRETARIA, PROCURADORIA
NIVEL 3 = Superintendencias,  Diretoria, Superintendência,
          Superintendências, Companhia, Departamento, Instituto, Policia, Corpo,
NIVEL 4 = Atos, Outros
"""

from collections import namedtuple
from functools import partial
import time
import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
import util as u
from database.entity.doe_bruto import DiarioOficialBruto
from database.repository.doe_bruto_repository import DiarioOficialBrutoRepository
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from settings import Settings
from dados import diario_oficial_bruto

# Primeiro data do diário oficial 05/01/2016??

site_link = 'https://dool.egba.ba.gov.br/'
data_inicial = datetime.date(2024, 1, 15)  # 2024, 3, 15 tem um caso especial
data_final = datetime.date(2024, 1, 25)


chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument('--headless')

# LIsta de pastas que serão abertas para coleta de dados
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


def select_pasta_nivel_2(
    lista1=selecao_pasta_nivel_2_executivo,
    lista2=selecao_pasta_nivel_2_licitacao,
    lista3=selecao_pasta_nivel_2_municipio,
    lista4=selecao_pasta_nivel_2_diverso,
    lista5=selecao_pasta_nivel_2_especial,
):
    """Juntando a lista de seleções das pastas.

    Args:
        lista1 (_type_, optional): _description_. Defaults to selecao_pasta_nivel_2_executivo.
        lista2 (_type_, optional): _description_. Defaults to selecao_pasta_nivel_2_licitacao.
        lista3 (_type_, optional): _description_. Defaults to selecao_pasta_nivel_2_municipio.
        lista4 (_type_, optional): _description_. Defaults to selecao_pasta_nivel_2_diverso.
        lista5 (_type_, optional): _description_. Defaults to selecao_pasta_nivel_2_especial.

    Returns:
        _type_: _description_
    """
    return set(lista1 + lista2 + lista3 + lista4 + lista5)


selecao_pasta_nivel_2 = select_pasta_nivel_2()

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


# Clicar no botão para continuar sem cadastro
def esperar_elemento(by, elemento, navegador):
    """Função para realizar a espera do elemento na tela do navegador.

    Args:
        by (_type_): _description_
        elemento (_type_): _description_
        driver (_type_): _description_

    Returns:
        _type_: _description_
    """
    # print(f'Tentando encontrar "{elemento}" by {by}')
    if navegador.find_elements(by, elemento):
        return True
    return False


# Listar elementos da pagina que tenham nomes diferentes de '' (if i.text != '')
def listar_elmento(navegador, by: By, name: str):
    """Criar lista de elementos que o text não seja ''

    Args:
        by (By): _description_
        name (str): _description_

    Returns:
        _type_: _description_
    """
    return [i for i in navegador.find_elements(by, name) if i.text != '']


def coletar_lista_link_ato(navegador, i):
    """Função que no ultimo nivel das pastas lista todos os atos.

    Returns:
        _type_: _description_
    """
    time.sleep(0.5)
    i.click()
    nt = namedtuple('ato', ['nome', 'identificador', 'link_conteudo'])
    lista_ato = [
        {
            'nome': i.text,
            'identificador': i.get_attribute('identificador'),
            'link': f"https://dool.egba.ba.gov.br/apifront/portal/edicoes/publicacoes_ver_conteudo/{i.get_attribute('identificador')}",
        }
        for i in listar_elmento(navegador, By.TAG_NAME, 'a')
        if i.text[0] == '#'
    ]
    time.sleep(0.5)
    i.click()
    return lista_ato


# TEM DE CLICAR NA PASTA PARA LOOPAR O CONTEUDO
# Abrindo as pastas do sumário para acessar o conteúdo
# Primerio nivel de pastas
def abrir_pastas(navegador, pastas: list):
    """Esta função abrirá as pastas de interesse do diário oficial html

    Args:
        pastas (list): Opções de nome das pastas ['EXECUTIVO', 'LICITAÇÕES',
        'MUNICÍPIOS', 'DIVERSOS', 'ESPECIAL']
    """
    for i in listar_elmento(navegador, By.CLASS_NAME, 'folder'):
        if i.text in pastas:
            try:
                time.sleep(0.5)
                i.click()
            except Exception as e:
                print(e)


def raspar_diario_oficial(data: str) -> dict:
    """Função que coleta os dados sumarizados do diario oficial
    do Estado da Bahia.

    Args:
        data (str): Data do diario oficial.
                    Formato: 'YYYY-MM-DD'

    Returns:
        dict: _description_
    """
    data_ = data.strftime('%d-%m-%Y')
    print(f'Diario oficial: {data}')
    navegador = webdriver.Chrome(options=chrome_options)

    # Sintaxe do wait
    wdw = WebDriverWait(
        navegador,  # webdriver
        timeout=60,  # tempo de espera pelo erro
        poll_frequency=0.5,  # tempo entre uma tentativa e outra
        # ignored_exceptions=None, # Lista de coisas que vamos ignorar
    )

    # Abrindo a pagina principal do diário oficial
    navegador.get(site_link)

    # Clicar no botão da versão html do diário oficial
    navegador.find_element(By.ID, 'downloadHTML').click()

    # Janela para seleção de continuar na versão html
    wdw.until(partial(esperar_elemento, By.CLASS_NAME, 'modal-footer'))
    navegador.find_element(By.CLASS_NAME, 'modal-footer').find_element(
        By.TAG_NAME, 'button'
    ).click()

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
        # print("Tratando a edição não existente")
        time.sleep(2)
        alert = wdw.until(lambda d: d.switch_to.alert)
        if alert.text == 'Edição não existente!':
            alert.accept()
            time.sleep(1)
            print(f'Edição não existe: {data_}')
            return {'data': data, 'exist': False}
    except Exception:
        print(f'Edição existente: {data_}')

    # Janela para seleção de continuar na versão html
    wdw.until(partial(esperar_elemento, By.CLASS_NAME, 'modal-footer'))
    navegador.find_element(By.CLASS_NAME, 'modal-footer').find_element(
        By.TAG_NAME, 'button'
    ).click()

    # TODO coletar o numero da edição
    edicao = int(
        navegador.find_element(By.CLASS_NAME, 'text-center')
        .find_element(By.TAG_NAME, 'strong')
        .text.split()[-1]
    )
    ######################## NIVEL 1 ########################
    # Listar pastas no nivel 1 do sumário
    lista_pasta_nivel_1 = [i.text for i in listar_elmento(navegador, By.CLASS_NAME, 'folder')]
    nao_selecao_pasta_nivel_1 = set(lista_pasta_nivel_1) - set(selecao_pasta_nivel_1)

    abrir_pastas(navegador, pastas=selecao_pasta_nivel_1)

    #########################################################
    ######################## NIVEL 2 ########################
    ###################### SECRETARIA #######################
    #########################################################
    lista_pasta_nivel_2 = [
        i.text
        for i in listar_elmento(navegador, By.CLASS_NAME, 'folder')
        if i.text not in lista_pasta_nivel_1
    ]

    # Construindo o dicionario da árvore de todas as pastas nivel 2
    dict_pasta_nivel_2 = {}
    count_nivel_2 = 0
    for i in listar_elmento(navegador, By.CLASS_NAME, 'folder'):
        #  NIVEL 1
        if i.text in selecao_pasta_nivel_1:
            # Adicionando o primeiro nivel no dict
            count_nivel_1 = selecao_pasta_nivel_1.index(i.text)
            if not dict_pasta_nivel_2:  # testando se o dict esta vazio, se true o dict esta vazio
                dict_pasta_nivel_2.update({selecao_pasta_nivel_1[count_nivel_1]: {}})
                pass
            if bool(dict_pasta_nivel_2):  # se true o dict tem dados nele
                dict_pasta_nivel_2.update({selecao_pasta_nivel_1[count_nivel_1]: {}})
        #  NIVEL 2
        if i.text in lista_pasta_nivel_2:
            count_nivel_2 = lista_pasta_nivel_2.index(i.text)
        if (
            i.text == lista_pasta_nivel_2[count_nivel_2]
            # Selecionando as pastas nivel 2 que terão dados coletadas
            and i.text in select_pasta_nivel_2()
        ):
            if not dict_pasta_nivel_2:  # se true o dict esta vazio
                dict_pasta_nivel_2 = {selecao_pasta_nivel_1[count_nivel_1]: {i.text: {}}}
            elif bool(dict_pasta_nivel_2):  # se true o dict tem dados nele
                dict_pasta_nivel_2[selecao_pasta_nivel_1[count_nivel_1]].update({i.text: {}})

    print(dict_pasta_nivel_2)

    # Clicando nas no nivel 2 (SECRETARIAS)
    abrir_pastas(navegador, pastas=selecao_pasta_nivel_2)

    #########################################################
    ######################## NIVEL 3 ########################
    ############# AUTARQUIAS, SUPERINTENDENCIA ##############
    #########################################################
    # Lista nivel 3 das pastas
    print('Construindo pastas nivel 3')
    lista_pasta_nivel_3 = [
        i.text
        for i in listar_elmento(navegador, By.CLASS_NAME, 'folder')
        if i.text not in lista_pasta_nivel_1
        and i.text not in lista_pasta_nivel_2
        # Todas as pasta nivel 3 tem padrão camel case (ex. Portaria)
        and i.text[1].islower()
    ]

    # Construindo o dicionario da árvore de todas as pastas nivel 3
    dict_pasta_nivel_3 = dict_pasta_nivel_2.copy()
    count_nivel_1 = 0
    count_nivel_2 = 0
    count_nivel_3 = 0
    for i in listar_elmento(navegador, By.CLASS_NAME, 'folder'):
        #  NIVEL 1
        if i.text in selecao_pasta_nivel_1:
            # Adicionando o primeiro nivel no dict
            index_nivel_1 = selecao_pasta_nivel_1.index(i.text)
            count_nivel_1 += 1
            count_nivel_2 = 0
            count_nivel_3 = 0
        #  NIVEL 2
        if i.text in lista_pasta_nivel_2:
            index_nivel_2 = lista_pasta_nivel_2.index(i.text)
            count_nivel_2 += 1
        #  NIVEL 3
        if i.text in lista_pasta_nivel_3:
            # Fazer o filtro por atos e depois adicionar autarquias
            index_nivel_3 = lista_pasta_nivel_3.index(i.text)
            if u.check_word_or_list_exist_in_list(
                i.text, tipo_adm_direta
            ):  # Se verdadeiro é um setor da adm direta
                select_dict = dict_pasta_nivel_3[lista_pasta_nivel_1[index_nivel_1]][
                    lista_pasta_nivel_2[index_nivel_2]
                ]

                if not select_dict:  # Se true o dict vazio
                    dict_pasta_nivel_3[lista_pasta_nivel_1[index_nivel_1]][
                        lista_pasta_nivel_2[index_nivel_2]
                    ] = {i.text: {}}
                    pass

                # Aqui é adicionando o INEMA no dict
                if bool(select_dict):  # Se False dict tem dados
                    select_dict.update({i.text: {}})
                    pass
            if u.check_word_or_list_exist_in_list(
                i.text, tipo_ato
            ):  # Se verdadeiro é uma pasta de atos
                print(i.text)
                select_dict = dict_pasta_nivel_3[lista_pasta_nivel_1[index_nivel_1]][
                    lista_pasta_nivel_2[index_nivel_2]
                ]

                if not select_dict:  # Se true o dict vazio
                    # Adicionar
                    dict_pasta_nivel_3[lista_pasta_nivel_1[index_nivel_1]][
                        lista_pasta_nivel_2[index_nivel_2]
                    ] = {i.text: coletar_lista_link_ato(navegador, i)}
                    pass

                if bool(select_dict):  # Se False dict tem dados
                    # Verificar se vai precisar adicionar a adição do ato nesta parte do codigo
                    select_dict.update({i.text: coletar_lista_link_ato(navegador, i)})
                    pass

    # Clicando nas no nivel 3 (Autarquias, Superintendencias, Diretorias)
    lista_pasta_clicar = set(lista_pasta_nivel_3) - set(lista_pasta_nivel_3).intersection(tipo_ato)
    abrir_pastas(navegador, set(lista_pasta_clicar))
    #########################################################
    ######################## NIVEL 4 ########################
    ######################### ATOS ##########################
    #########################################################
    print('Construindo pastas nivel 4')
    lista_elemento_pasta = listar_elmento(navegador, By.CLASS_NAME, 'folder')
    lista_nivel_4_ = {
        i.text
        for i in lista_elemento_pasta
        if i.text not in lista_pasta_nivel_1
        and i.text not in lista_pasta_nivel_2
        and i.text not in lista_pasta_nivel_3
    }

    lista_nivel_4__ = {i.text for i in lista_elemento_pasta if i.text in tipo_ato}

    # Tive que realizar essa união por causa que a lista_pasta_nivel_3 retirava os ato da lista
    lista_pasta_nivel_4 = lista_nivel_4_.union(lista_nivel_4__)

    # Construindo o dicionario da árvore de todas as pastas nivel 4
    dict_pasta_nivel_4 = dict_pasta_nivel_3.copy()
    count_nivel_1 = 0
    count_nivel_2 = 0
    count_nivel_3 = 0
    count_nivel_4 = 0
    for i in listar_elmento(navegador, By.CLASS_NAME, 'folder'):
        #  NIVEL 1
        if i.text in selecao_pasta_nivel_1:
            # Adicionando o primeiro nivel no dict
            index_nivel_1 = selecao_pasta_nivel_1.index(i.text)
            count_nivel_1 += 1
            count_nivel_2 = 0
            count_nivel_3 = 0
            count_nivel_4 = 0
        #  NIVEL 2
        if i.text in lista_pasta_nivel_2:
            index_nivel_2 = lista_pasta_nivel_2.index(i.text)
            count_nivel_2 += 1
        #  NIVEL 3
        if i.text in lista_pasta_nivel_3:
            # Fazer o filtro por atos e depois adicionar autarquias
            index_nivel_3 = lista_pasta_nivel_3.index(i.text)
            count_nivel_3 += 1
        if i.text in lista_pasta_clicar:
            if u.check_word_or_list_exist_in_list(
                i.text, tipo_adm_direta
            ):  # Se verdadeiro é um setor da adm direta
                index_nivel_4 = list(lista_pasta_clicar).index(i.text)
                count_nivel_4 += 1
        if (
            u.check_word_or_list_exist_in_list(i.text, tipo_ato) and count_nivel_4 != 0
        ):  # Se verdadeiro é uma pasta de atos
            print(i.text)

            select_dict = dict_pasta_nivel_4[lista_pasta_nivel_1[index_nivel_1]][
                lista_pasta_nivel_2[index_nivel_2]
            ][list(lista_pasta_clicar)[index_nivel_4]]

            if not select_dict:  # Se true o dict vazio
                # Adicionar
                dict_pasta_nivel_4[lista_pasta_nivel_1[index_nivel_1]][
                    lista_pasta_nivel_2[index_nivel_2]
                ][list(lista_pasta_clicar)[index_nivel_4]] = {
                    i.text: coletar_lista_link_ato(navegador, i)
                }
                pass

            count_nivel_4 = 0

    print(dict_pasta_nivel_4)
    return {
        'diario_oficial_json': dict_pasta_nivel_4,
        'edicao': edicao,
        'data': data,
        'exist': True,
    }


def coleta_doe_data(data: str):
    """Esta função raspa e salva os dados no banco a partir de uma única data

    Args:
        data (str): _description_
    """
    if diario_oficial_bruto.check_if_date_doe_coleted(data) is None:

        try:
            a = raspar_diario_oficial(data=data)
        except Exception as exception:
            print(exception)

        dados = DiarioOficialBrutoRepository()
        dados.save_data(**a)


# carga_banco(data=data_inicial)

# Exemplo de como utilizar a função
# coletar_dado_data(data_inicial=data_inicial, data_final=data_final)
