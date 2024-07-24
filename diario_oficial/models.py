from sqlalchemy import Column, Date
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
Base = declarative_base()


class DiarioOficialBruto(Base):
    """_summary_

    Args:
        Base (_type_): _description_

    Returns:
        _type_: _description_
    """

    __table_args__ = {'schema': 'processing'}
    __tablename__ = 'diario_oficial_bruto'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    diario_oficial_json: Mapped[JSONB] = mapped_column(type_=JSONB, nullable=True)
    data = Column(Date, unique=True)
    edicao: Mapped[int] = mapped_column(nullable=True, unique=True)
    exist: Mapped[bool] = mapped_column(nullable=False)

    def __repr__(self):
        return f'Dados Diário Oficial Bruto [edicao={self.edicao}, data={self.data}]'
