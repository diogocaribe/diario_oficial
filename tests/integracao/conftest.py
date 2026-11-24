"""Testes de integração com o PostgreSQL/PostGIS, num banco descartável.

Cada banco é criado no servidor do ``.env`` com o nome ``teste_diario_oficial_<sufixo>``,
recebe as migrações (``alembic upgrade head``) e é apagado no fim. O banco de trabalho
(``DATABASE`` do ``.env``) não é lido nem alterado.

Ficam fora do ``pytest`` padrão (marcador ``integracao``). Para rodar::

    pytest -m integracao
"""

import os
import uuid
from datetime import date
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from sqlalchemy_utils import database_exists, drop_database

from diario_oficial.database.configs import connection
from diario_oficial.database.entity.ato import Ato
from diario_oficial.database.entity.doe_bruto import DiarioOficialBruto
from diario_oficial.database.entity.dominio import (
    AdministracaoDireta,
    AdministracaoIndireta,
    Poder,
    TipoPublicacao,
)
from diario_oficial.database.entity.publicacao import Publicacao

RAIZ = Path(__file__).resolve().parents[2]
PREFIXO = 'teste_diario_oficial_'

SEMA = 'SECRETARIA DO MEIO AMBIENTE'
INEMA = 'Instituto do Meio Ambiente e Recursos Hídricos - INEMA'

# Tabelas com os dados do pipeline e das extrações. O CASCADE leva as que apontam
# para elas (publicacao, ato, log_erro, extracao_trecho, autos, outorgas...); os
# endereços são apontados pelos autos e outorgas, e por isso entram na lista.
TABELAS_DE_DADOS = (
    'processing.doe_bruto',
    'public.pessoa',
    'auto_infracao.endereco',
    'recurso_hidrico.endereco',
)


def url_descartavel() -> URL:
    """A URL do servidor do .env com um banco de nome novo."""
    from diario_oficial.settings import Settings

    try:
        settings = Settings()
    except Exception as erro:  # sem .env
        pytest.skip(f'sem configuração do banco: {erro}')
    url = make_url(settings.DATABASE_URL).set(
        database=f'{PREFIXO}{uuid.uuid4().hex[:8]}'
    )
    assert url.database != settings.DATABASE
    return url


def migrar(url: URL, revisao: str = 'head', descer: bool = False) -> None:
    """Roda o Alembic do projeto no banco de ``url``.

    O ``migrations/env.py`` lê a URL de ``Settings``, e a variável de ambiente tem
    prioridade sobre o ``.env``. Ele cria o banco se não existir.
    """
    assert url.database.startswith(PREFIXO)
    config = Config(str(RAIZ / 'alembic.ini'))
    config.set_main_option('script_location', str(RAIZ / 'migrations'))
    with pytest.MonkeyPatch.context() as ambiente:
        ambiente.setenv('DATABASE_URL', url.render_as_string(hide_password=False))
        if descer:
            command.downgrade(config, revisao)
        else:
            command.upgrade(config, revisao)


def apagar_banco(url: URL) -> None:
    assert url.database.startswith(PREFIXO)
    if database_exists(url):
        drop_database(url)


@pytest.fixture
def banco_vazio():
    """URL de um banco descartável ainda sem migrações; apagado no fim do teste."""
    url = url_descartavel()
    try:
        create_engine(url.set(database='postgres')).connect().close()
    except OperationalError as erro:
        pytest.skip(f'servidor PostgreSQL fora do ar: {erro}')
    yield url
    apagar_banco(url)


@pytest.fixture(scope='session')
def engine_de_teste():
    """Engine de um banco descartável com todas as migrações, um por sessão."""
    url = url_descartavel()
    try:
        create_engine(url.set(database='postgres')).connect().close()
    except OperationalError as erro:
        pytest.skip(f'servidor PostgreSQL fora do ar: {erro}')
    try:
        migrar(url)
        engine = create_engine(url)
        yield engine
        engine.dispose()
    finally:
        apagar_banco(url)


@pytest.fixture
def banco(engine_de_teste: Engine, monkeypatch) -> Engine:
    """O banco de teste, também para os repositórios, limpo depois de cada teste.

    Os repositórios abrem a sessão pelo ``DBConnectionHandler``, que usa o engine
    único do processo: o teste troca esse engine pelo do banco descartável.
    """
    monkeypatch.setattr(connection, '_engine', engine_de_teste)
    monkeypatch.setattr(connection, '_pid_do_engine', os.getpid())
    yield engine_de_teste
    with engine_de_teste.begin() as conexao:
        conexao.execute(
            text(f'TRUNCATE {", ".join(TABELAS_DE_DADOS)} RESTART IDENTITY CASCADE')
        )


def id_por_nome(sessao: Session, entidade, nome: str) -> int:
    return sessao.scalars(select(entidade.id).where(entidade.nome == nome)).one()


@pytest.fixture
def criar_publicacao(banco: Engine):
    """Grava uma edição do DOE, uma publicação de Portarias do INEMA e os seus atos.

    Devolve ``(publicacao_id, [ato_id, ...])``. Cada chamada usa uma data nova.
    """
    contador = iter(range(1, 1000))

    def criar(
        atos: list[str], processada_para_ato: bool | None = True
    ) -> tuple[int, list[int]]:
        numero = next(contador)
        with Session(banco) as sessao:
            doe = DiarioOficialBruto(
                nro_edicao=23000 + numero,
                dt_edicao=date(2026, 1, numero),
                existe=True,
                doe_json={},
            )
            publicacao = Publicacao(
                doe_bruto=doe,
                poder_id=id_por_nome(sessao, Poder, 'EXECUTIVO'),
                adm_direta_id=id_por_nome(sessao, AdministracaoDireta, SEMA),
                adm_indireta_id=id_por_nome(sessao, AdministracaoIndireta, INEMA),
                tipo_publicacao_id=id_por_nome(sessao, TipoPublicacao, 'Portarias'),
                nome_ato=f'#{numero} - PORTARIAS',
                identificador_link=str(900000 + numero),
                link=f'https://dool.egba.ba.gov.br/{900000 + numero}',
                conteudo_link='\n'.join(atos),
                processada_para_ato=processada_para_ato,
                auditoria=True,
            )
            entidades_ato = [
                Ato(publicacao=publicacao, conteudo_ato=conteudo) for conteudo in atos
            ]
            sessao.add_all(entidades_ato)
            sessao.commit()
            return publicacao.id, [ato.id for ato in entidades_ato]

    return criar
