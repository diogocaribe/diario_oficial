"""Codigo para raspar dados do DOE."""

from functools import partial
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
import time

# Primeiro data do diário oficial 05/01/2016??

site_link = "https://dool.egba.ba.gov.br/"
data = "17-05-2024"
selecao_pasta_nivel_1 = ["EXECUTIVO", "LICITAÇÕES"]
# TODO implementar a seleção de pastas no nivel 2
# LIsta de pastas que serão abertas para coleta de dados
selecao_pasta_nivel_2_executivo = [
    "DECRETOS FINANCEIROS",
    # 'PROCURADORIA GERAL DO ESTADO', # ver se consegue tirar a redundancia com LICITAÇÕES
    # "SECRETARIA DO MEIO AMBIENTE",
    "SECRETARIA DA EDUCAÇÃO",
    "SECRETARIA DA FAZENDA",
]
selecao_pasta_nivel_2_licitacao = ["AVISOS DE LICITAÇÃO"]
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
    selecao_pasta_nivel_2 = set(lista1 + lista2 + lista3 + lista4 + lista5)
    return selecao_pasta_nivel_2


selecao_pasta_nivel_2 = select_pasta_nivel_2()

navegador = webdriver.Chrome()

# Sintaxe do wait
wdw = WebDriverWait(
    navegador,  # webdriver
    timeout=60,  # tempo de espera pelo erro
    # poll_frequency=0.5,  # tempo entre uma tentativa e outra
    # ignored_exceptions=None, # Lista de coisas que vamos ignorar
)
# Abrindo a pagina principal do diário oficial
navegador.get(site_link)

# Clicar no botão da versão html do diário oficial
navegador.find_element(By.ID, "downloadHTML").click()


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


# Janela para seleção de continuar na versão html
wdw.until(partial(esperar_elemento, By.CLASS_NAME, "modal-footer"))
navegador.find_element(By.CLASS_NAME, "modal-footer").find_element(
    By.TAG_NAME, "button"
).click()

# Selecionando a data
navegador.find_element(By.CLASS_NAME, "date-input").clear()

time.sleep(2)
navegador.switch_to.alert.accept()

navegador.find_element(By.CLASS_NAME, "date-input").send_keys(data)

navegador.find_element(By.CLASS_NAME, "date-input").click()

navegador.find_element(By.CLASS_NAME, "fa-search").click()

# Janela para seleção de continuar na versão html
time.sleep(2)
wdw.until(partial(esperar_elemento, By.CLASS_NAME, "modal-footer"))
navegador.find_element(By.CLASS_NAME, "modal-footer").find_element(
    By.TAG_NAME, "button"
).click()


# Listar pastas no nivel 1 do sumário
lista_pasta_nivel_1 = [
    i.text for i in navegador.find_elements(By.CLASS_NAME, "folder") if i.text != ""
]

# print(lista_pasta_nivel_1)

nao_selecao_pasta_nivel_1 = set(lista_pasta_nivel_1) - set(selecao_pasta_nivel_1)


# TEM DE CLICAR NA PASTA PARA LOOPAR O CONTEUDO
# Abrindo as pastas do sumário para acessar o conteúdo
# Primerio nivel de pastas
def abrir_pastas(pastas: list):
    """Esta função abrirá as pastas de interesse do diário oficial html

    Args:
        pastas (list): Opções de nome das pastas ['EXECUTIVO', 'LICITAÇÕES',
        'MUNICÍPIOS', 'DIVERSOS', 'ESPECIAL']
    """
    for i in navegador.find_elements(By.CLASS_NAME, "folder"):
        if i.text in pastas:
            try:
                i.click()
            except Exception as e:
                print(e)


abrir_pastas(pastas=selecao_pasta_nivel_1)


lista_pasta_nivel_2 = [
    i.text
    for i in navegador.find_elements(By.CLASS_NAME, "folder")
    if i.text != "" and i.text not in lista_pasta_nivel_1
]

# print(lista_pasta_nivel_2)

# Construindo o dicionario da árvore de todas as pastas nivel 2
dict_pasta_nivel_2 = {}
count_nivel_2 = 0
for i in navegador.find_elements(By.CLASS_NAME, "folder"):
    if i.text != "":
        #  NIVEL 1
        if i.text in selecao_pasta_nivel_1:
            # Adicionando o primeiro nivel no dict
            count_nivel_1 = selecao_pasta_nivel_1.index(i.text)
            if (
                not dict_pasta_nivel_2
            ):  # testando se o dict esta vazio, se true o dict esta vazio
                dict_pasta_nivel_2.update({selecao_pasta_nivel_1[count_nivel_1]: {}})
                continue
            elif bool(dict_pasta_nivel_2):  # se true o dict tem dados nele
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
                dict_pasta_nivel_2 = {
                    selecao_pasta_nivel_1[count_nivel_1]: {i.text: {}}
                }
            elif bool(dict_pasta_nivel_2):  # se true o dict tem dados nele
                dict_pasta_nivel_2[selecao_pasta_nivel_1[count_nivel_1]].update(
                    {i.text: {}}
                )

# print(dict_pasta_nivel_2)

# Clicando no nivel 2 das pastas selecionadas para abrir o nivel 3
lista_toda_elemento_pasta = navegador.find_elements(By.CLASS_NAME, "folder")
lista_pasta_nivel_3_to_click = [
    i.text
    for i in lista_toda_elemento_pasta
    if i.text in lista_pasta_nivel_2 and i.text not in (nao_selecao_pasta_nivel_1)
    # Selecionando as pastas nivel 2 que serão clicadas pelo usuário
    and i.text in selecao_pasta_nivel_2 and i.text != ""
]

abrir_pastas(pastas=lista_pasta_nivel_3_to_click)


# Lista nivel 3 das pastas
lista_pasta_nivel_3 = [
    i.text
    for i in navegador.find_elements(By.CLASS_NAME, "folder")
    if i.text != ""
    and i.text not in lista_pasta_nivel_1
    and i.text not in lista_pasta_nivel_2
    # Todas as pasta nivel 3 tem padrão camel case (ex. Portaria)
    and i.text[1].islower()
]

# TODO Pensar nos links para coletar
# TODO constuir a adição do nivel 3 do dicionário

time.sleep(60)

page_content = navegador.page_source

site = BeautifulSoup(page_content, "html.parser")
