from datetime import date

from diario_oficial.util import dias_do_periodo

ULTIMO_DIA = date(2026, 11, 8)


def test_periodo_inclui_inicio_e_fim():
    assert dias_do_periodo(date(2026, 10, 30), date(2026, 11, 1), ULTIMO_DIA) == [
        date(2026, 10, 30),
        date(2026, 10, 31),
        date(2026, 11, 1),
    ]


def test_periodo_de_um_dia():
    dia = date(2026, 11, 3)
    assert dias_do_periodo(dia, dia, ULTIMO_DIA) == [dia]


def test_fim_nao_passa_do_ultimo_dia():
    dias = dias_do_periodo(date(2026, 11, 7), date(2026, 11, 30), ULTIMO_DIA)
    assert dias == [date(2026, 11, 7), ULTIMO_DIA]


def test_inicio_depois_do_fim_nao_tem_dias():
    assert dias_do_periodo(date(2026, 11, 5), date(2026, 11, 1), ULTIMO_DIA) == []


def test_inicio_depois_do_ultimo_dia_nao_tem_dias():
    assert dias_do_periodo(date(2026, 11, 9), date(2026, 11, 10), ULTIMO_DIA) == []
