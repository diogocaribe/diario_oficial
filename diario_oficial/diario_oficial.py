import time
from selenium import webdriver
from selenium.webdriver.common.by import By


class DiarioOficialBa:
    def __init__(self) -> None:
        self.site_link = "https://dool.egba.ba.gov.br/"
        self.navegador = webdriver.Chrome()

        self.site_map = {}

    def abrir_site(self):
        self.navegador.get(self.site_link)
        

    def clicar_versao_html(self):
        self.navegador.find_element(By.ID, 'downloadHTML')
        

    def clicar_splashscreen(self):
        pass

    def definir_data(self):
        pass


diario_oficial = DiarioOficialBa()