"""Codigo para raspar dados do DOE."""
from selenium import webdriver
from selenium.webdriver.common.by import By


class DiarioOficialBa:
    """_summary_
    """
    def __init__(self) -> None:
        self.site_link = "https://dool.egba.ba.gov.br/"
        self.navegador = webdriver.Chrome()

        self.site_map = {}

    def abrir_site(self):
        """_summary_
        """
        self.navegador.get(self.site_link)

    def clicar_versao_html(self):
        """_summary_
        """
        self.navegador.find_element(By.ID, "downloadHTML")

    def clicar_splashscreen(self):
        """_summary_
        """


    def definir_data(self):
        """_summary_
        """


diario_oficial = DiarioOficialBa()
