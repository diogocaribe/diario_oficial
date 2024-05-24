"""Codigo para raspar dados do DOE."""
from functools import partial
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
import time

site_link = "https://dool.egba.ba.gov.br/"
data = "17-05-2024"

driver = webdriver.Chrome()

# Sintaxe do wait
wdw = WebDriverWait(
    driver,  # webdriver
    timeout=10,  # tempo de espera pelo erro
    # poll_frequency=0.5,  # tempo entre uma tentativa e outra
    # ignored_exceptions=None, # Lista de coisas que vamos ignorar
)
# Abrindo a pagina principal do diário oficial
driver.get(site_link)

# Clicar no botão da versão html do diário oficial
driver.find_element(By.ID, "downloadHTML").click()

# Clicar no botão para continuar sem cadastro
def esperar_elemento(by, elemento, driver):
    """_summary_

    Args:
        by (_type_): _description_
        elemento (_type_): _description_
        driver (_type_): _description_

    Returns:
        _type_: _description_
    """
    print(f'Tentando encontrar "{elemento}" by {by}')
    if driver.find_elements(by, elemento):
        return True
    return False

# Janela para seleção de continuar na versão html
wdw.until(partial(esperar_elemento, By.CLASS_NAME, 'modal-footer'))
driver.find_element(By.CLASS_NAME, "modal-footer").find_element(
    By.TAG_NAME, "button"
).click()

# Selecionando a data
driver.find_element(By.CLASS_NAME, "date-input").clear()

time.sleep(2)
driver.switch_to.alert.accept()

driver.find_element(By.CLASS_NAME, "date-input").send_keys(data)

driver.find_element(By.CLASS_NAME, "date-input").click()

driver.find_element(By.CLASS_NAME, "fa-search").click()

# Janela para seleção de continuar na versão html
time.sleep(2)
wdw.until(partial(esperar_elemento, By.CLASS_NAME, 'modal-footer'))
driver.find_element(By.CLASS_NAME, "modal-footer").find_element(
    By.TAG_NAME, "button"
).click()

# Clicando na primeiro elemento para expandir o sumário lateral (folder)
# EXECUTIVO
driver.find_element(By.CLASS_NAME, "folder").click()

time.sleep(60)