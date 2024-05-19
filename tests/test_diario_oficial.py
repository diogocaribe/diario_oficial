from diario_oficial.diario_oficial import DiarioOficialBa


diario_oficial = DiarioOficialBa()


def test_site():
    print(diario_oficial.site())
