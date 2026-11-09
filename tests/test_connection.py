"""O engine é único por processo. Nenhum teste abre conexão com o banco."""

import pytest

from diario_oficial.database.configs import connection
from diario_oficial.database.configs.connection import DBConnectionHandler


@pytest.fixture(autouse=True)
def engine_isolado(monkeypatch):
    """Cada teste começa sem engine e não depende do .env."""
    variaveis = {
        'DATABASE': 'teste',
        'USER_DB': 'usuario',
        'PASSWORD_DB': 'senha',
        'HOST': 'localhost',
        'PORT': '5432',
        'DATABASE_URL': 'postgresql+psycopg://usuario:senha@localhost:5432/teste',
        'SELENIUM_ADDRESS': 'http://localhost',
        'SELENIUM_PORT': '4444',
    }
    for nome, valor in variaveis.items():
        monkeypatch.setenv(nome, valor)
    monkeypatch.setattr(connection, '_engine', None)
    monkeypatch.setattr(connection, '_pid_do_engine', None)


def test_handlers_compartilham_o_mesmo_engine():
    assert DBConnectionHandler().get_engine() is DBConnectionHandler().get_engine()


def test_sessao_usa_o_engine_do_processo():
    with DBConnectionHandler() as db:
        assert db.session.get_bind() is connection.obter_engine()


def test_processo_filho_cria_engine_proprio(monkeypatch):
    engine_do_pai = connection.obter_engine()
    descartes = []
    monkeypatch.setattr(
        engine_do_pai, 'dispose', lambda close=True: descartes.append(close)
    )

    # Simula o fork: mesmo módulo já carregado, outro pid
    monkeypatch.setattr(connection.os, 'getpid', lambda: -1)
    engine_do_filho = connection.obter_engine()

    assert engine_do_filho is not engine_do_pai
    # As conexões herdadas continuam em uso no pai: não podem ser fechadas pelo filho
    assert descartes == [False]
    assert connection.obter_engine() is engine_do_filho
