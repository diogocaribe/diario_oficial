from bs4 import BeautifulSoup
import requests


class DiarioOficialBa:
    def __init__(self) -> None:
        self.site_link = "https://dool.egba.ba.gov.br/"
        self.site_map = {}

    def site(self):
        response = requests.get(self.site_link, verify=False)
        content = response.content
        site = BeautifulSoup(content, "html.parser")

        return site

    def clicar_splashscreen(self):
        pass

    def definir_data(self):
        pass


DiarioOficialBa()
