from sqlalchemy.orm import Mapped, mapped_column
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
