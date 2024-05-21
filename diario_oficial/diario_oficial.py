"""Codigo para raspar dados do DOE."""
from selenium import webdriver
from selenium.webdriver.common.by import By
import time

class DiarioOficialBa:
    """_summary_
    """
    def __init__(self) -> None:
        self.site_link = "https://dool.egba.ba.gov.br/"
        self.data = '17-05-2024'

    def site(self):
        """_summary_
        """
        time.sleep(1)
        driver = webdriver.Chrome()
        time.sleep(1)
        driver.get(self.site_link)
        time.sleep(1)
        driver.find_element(By.ID, "downloadHTML").click()
        time.sleep(1)
        driver.find_element(By.CLASS_NAME, "modal-footer").find_element(
            By.TAG_NAME, "button"
        ).click()
        time.sleep(1)
        driver.find_element(By.CLASS_NAME, "date-input").clear()
        time.sleep(5)
        driver.switch_to.alert.accept()
        time.sleep(2)
        driver.find_element(By.CLASS_NAME, "date-input").send_keys(self.data)
        time.sleep(2)
        driver.find_element(By.CLASS_NAME, "date-input").click()
        time.sleep(2)
        driver.find_element(By.CLASS_NAME, "fa-search").click()
        time.sleep(5)
        driver.find_element(By.CLASS_NAME, "modal-footer").find_element(
            By.TAG_NAME, "button"
        ).click()
        time.sleep(60)

    def clicar_versao_html(self):
        """_summary_
        """
        time.sleep(2)
        # self.driver.find_element(By.ID, "downloadHTML").click()
        time.sleep(60)

    def clicar_splashscreen(self):
        """_summary_
        """


    def definir_data(self):
        """_summary_
        """

DiarioOficialBa().site()