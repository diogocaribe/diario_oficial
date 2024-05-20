"""Testando a respagem de dados."""
from diario_oficial.diario_oficial import DiarioOficialBa


diario_oficial = DiarioOficialBa()


def test_navegador():
    """_summary_
    """
    diario_oficial.abrir_site()

def test_clicar_versao_html():
    """_summary_
    """
    diario_oficial.clicar_versao_html()
    print('oi')