import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from diario_oficial.settings import Settings

# Um engine por processo: criar um a cada uso abria uma conexão nova por consulta e
# esgotava o max_connections do PostgreSQL com o pipeline em paralelo.
_engine = None
_pid_do_engine = None


def obter_engine():
    """Devolve o engine do processo atual, criando-o no primeiro uso.

    Um processo filho (fork) não pode usar as conexões herdadas do pai: o engine herdado
    é descartado sem fechá-las, porque continuam em uso no pai, e um novo é criado.
    """
    global _engine, _pid_do_engine
    pid = os.getpid()
    if _engine is not None and _pid_do_engine != pid:
        _engine.dispose(close=False)
        _engine = None
    if _engine is None:
        # pool_pre_ping troca a conexão que caiu (ex.: banco reiniciado) antes de usá-la
        _engine = create_engine(Settings().DATABASE_URL, pool_pre_ping=True)
        _pid_do_engine = pid
    return _engine


class DBConnectionHandler:
    def __init__(self) -> None:
        self.__engine = obter_engine()
        self.session = None

    def get_engine(self):
        return self.__engine

    def __enter__(self):
        self.session = Session(bind=self.__engine)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Devolve a conexão ao pool do engine, que a mantém aberta para o próximo uso
        self.session.close()
