from sqlalchemy.orm import Mapped, mapped_column
from ..configs.base import Base
from diario_oficial.database.configs.connection import DBConnectionHandler


class Poder(Base):
    """Tabela para registro do dominio do poder das três esferas
       EXECUTIVO, LEGISLATIVO, JUDICIÁRIO
    Args:
        Base (_type_): _description_
    """

    __tablename__ = 'poder'
    __table_args__ = {'schema': 'dominio'}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    nome: Mapped[str] = mapped_column(nullable=False, unique=True)


class AdministracaoDireta(Base):
    """Tabela para registro do dominio da adm direta (Secretarias)
        Ex.
        nome : Secretaria de Meio Ambiente
        sigla: SEMA

    Args:
        Base (_type_): _description_
    """

    __tablename__ = 'adm_direta'
    __table_args__ = {'schema': 'dominio'}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    nome: Mapped[str] = mapped_column(nullable=False, unique=True)
    sigla: Mapped[str] = mapped_column(nullable=False)


class AdministracaoIndireta(Base):
    """Tabela para registro do dominio da adm indireta (Orgãos, Institutos)
        Ex.
        nome : Instituto de Meio Ambiente e Recursos Hídricos
        sigla: INEMA
    Args:
        Base (_type_): _description_
    """

    __tablename__ = 'adm_indireta'
    __table_args__ = {'schema': 'dominio'}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    nome: Mapped[str] = mapped_column(nullable=False, unique=True)
    sigla: Mapped[str] = mapped_column(nullable=False)


class OrgaoAdministracaoDireta(Base):
    """Tabela para registro do dominio da adm indireta (Orgãos, Institutos)
        Ex.
        nome : Diretoria
        sigla : DG
    Args:
        Base (_type_): _description_
    """

    __tablename__ = 'orgao_adm_indireta'
    __table_args__ = {'schema': 'dominio'}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    nome: Mapped[str] = mapped_column(nullable=False, unique=True)
    sigla: Mapped[str] = mapped_column(nullable=False)
