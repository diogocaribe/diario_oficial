"""Testando a respagem de dados."""

from scripts.diario_oficial import DiarioOficialBa


diario_oficial = DiarioOficialBa()


def test_site():
    """_summary_"""
    diario_oficial.site()
