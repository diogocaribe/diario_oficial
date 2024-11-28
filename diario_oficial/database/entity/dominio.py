from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..configs.base import Base


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

    publicacao = relationship('Publicacao', back_populates='poder', cascade='all, delete-orphan')


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
    sigla: Mapped[str] = mapped_column(nullable=True)

    publicacao = relationship(
        'Publicacao', back_populates='adm_direta', cascade='all, delete-orphan'
    )


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
    nome: Mapped[str] = mapped_column(nullable=True, unique=True)
    sigla: Mapped[str] = mapped_column(nullable=True)

    publicacao = relationship(
        'Publicacao', back_populates='adm_indireta', cascade='all, delete-orphan'
    )


class DivisaoAdministracaoDireta(Base):
    """Tabela para registro do dominio da adm indireta (Orgãos, Institutos)
        Ex.
        nome : Diretoria
        sigla : DG
    Args:
        Base (_type_): _description_
    """

    __tablename__ = 'divisao_adm_direta'
    __table_args__ = {'schema': 'dominio'}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    nome: Mapped[str] = mapped_column(nullable=True, unique=True)
    sigla: Mapped[str] = mapped_column(nullable=True)

    publicacao = relationship(
        'Publicacao', back_populates='divisao_adm_direta', cascade='all, delete-orphan'
    )

class DivisaoAdministracaoInireta(Base):
    """Tabela para registro do dominio da adm indireta (Orgãos, Institutos)
        Ex.
        nome : Diretoria
        sigla : DG
    Args:
        Base (_type_): _description_
    """

    __tablename__ = 'divisao_adm_indireta'
    __table_args__ = {'schema': 'dominio'}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    nome: Mapped[str] = mapped_column(nullable=True, unique=True)
    sigla: Mapped[str] = mapped_column(nullable=True)

    publicacao = relationship(
        'Publicacao', back_populates='divisao_adm_indireta', cascade='all, delete-orphan'
    )

class TipoPublicacao(Base):
    __tablename__ = 'tipo_publicacao'
    __table_args__ = {'schema': 'dominio'}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    nome: Mapped[str] = mapped_column(nullable=True, unique=True)
    sigla: Mapped[str] = mapped_column(nullable=True)

    publicacao = relationship(
        'Publicacao', back_populates='tipo_publicacao', cascade='all, delete-orphan'
    )
