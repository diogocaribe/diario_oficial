import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from datetime import datetime
from bs4 import BeautifulSoup

response = requests.get(
    "https://dool.egba.ba.gov.br/ver-html/18003/#e:18003", verify=False
)

content = response.content

site = BeautifulSoup(content, "html.parser")

versao = int(
    site.find("li", attrs={"class": "li-versao"}).a.attrs["href"].split("/")[-1]
)
data = datetime.strptime(
    site.find("div", attrs={"class": "input-group date datepicker-btn"}).input.attrs[
        "value"
    ],
    "%d/%m/%Y",
).date()

edicao = int(
    site.find("div", attrs={"class": "text-center"}).strong.contents[0].split(" ")[-1]
)

print(edicao, versao, data)

############### SELENIUM ###############
# Fazendo a busca com selenium
# doe = diário oficial do estado
navegador_doe = webdriver.Chrome()

navegador_doe.get("https://dool.egba.ba.gov.br/ver-html/18003/#e:18003")

# Clicando no botão do splashscreen para continar sem cadastro
navegador_doe.find_element(By.CLASS_NAME, "modal-footer").find_element(
    By.TAG_NAME, "button"
).click()

# Clicando na primeiro elemento para expandir o sumário lateral (folder)
navegador_doe.find_element(By.CLASS_NAME, "folder").click()

print(navegador_doe)

# continuar_sem_cadastro = navegador.
