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
pasta_primeiro_nivel_sumario = ["EXECUTIVO", "LICITAÇÕES"]

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
    print(f'Tentando encontrar "{elemento}" by {by}')
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
            i.click()


abrir_pastas(pastas=["EXECUTIVO", "LICITAÇÕES"])

# Abrir o conteúdo de cada pasta
# Pasta EXECUTIVO

dados = {}

lista_nivel_adm_indireta = []
lista_licitacao = []

executivo = False
licitacao = False
for i in navegador.find_elements(By.CLASS_NAME, "folder"):
    if i.text == "EXECUTIVO":
        executivo = True
        continue
    if i.text == "LICITAÇÕES":
        licitacao = True
        continue
    if i.text != "" and licitacao is False:
        lista_nivel_adm_indireta.append(i.text)
    if i.text != "" and licitacao is True:
        lista_licitacao.append(i.text)


# print(lista_nivel_adm_indireta)
# print(lista_licitacao)

# Construindo o dicionario da árvore das pastas
arvore_sumario = {}
count_nivel_1 = 0
count_nivel_2 = 0
for i in navegador.find_elements(By.CLASS_NAME, "folder"):
    print(i.text)
    if i.text == pasta_primeiro_nivel_sumario[count_nivel_1 + 1]:
        # Muda para o próximo nível da lista (LICITAÇÕES)
        count_nivel_1 += 1
    if i.text == lista_nivel_adm_indireta[count_nivel_2] and i.text != "":
        if not arvore_sumario:  # se true o dict esta vazio
            arvore_sumario = {pasta_primeiro_nivel_sumario[count_nivel_1]: {i.text: {}}}
        elif bool(arvore_sumario):  # se true o dict tem dados nele
            arvore_sumario[pasta_primeiro_nivel_sumario[count_nivel_1]].update({i.text: {}})
    if i.text == lista_nivel_adm_indireta[count_nivel_2]:
        # Muda para o proximo elemento da lista
        count_nivel_2 += 1
    if count_nivel_2 == len(lista_nivel_adm_indireta):
        break

# TODO Fazer o mapeamento no formato dict para o nivel LICITAÇÕES

# TODO clicar no nivel 3 dos objetos da arvore
executivo = False
licitacao = False
for i in navegador.find_elements(By.CLASS_NAME, "folder"):
    if i.text == "EXECUTIVO":
        executivo = True
        continue
    if i.text == "LICITAÇÕES":
        licitacao = True
        continue
    # if i.text != "" and licitacao is False:
    #     lista_nivel_adm_indireta.append(i.text)
    # if i.text != "" and licitacao is True:
    #     lista_licitacao.append(i.text)
    if i.text != "":
        print(i.text)
        try:
            i.click()
        except Exception as e:
            print(e)

time.sleep(60)

page_content = navegador.page_source

site = BeautifulSoup(page_content, "html.parser")
