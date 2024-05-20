from diario_oficial.diario_oficial import DiarioOficialBa


diario_oficial = DiarioOficialBa()


def test_navegador():
    diario_oficial.abrir_site()

def test_clicar_versao_html():
    diario_oficial.clicar_versao_html()
    print('oi')

