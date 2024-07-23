from sqlalchemy import Column, Integer, JSON, Boolean, Date
from sqlalchemy.orm import declarative_base

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

    id = Column(Integer, primary_key=True, autoincrement=True)
    diario_oficial_json = Column(JSON)
    data = Column(Date)
    edicao = Column(Integer)
    exist = Column(Boolean)

    def __repr__(self):
        return f'Dados Diário Oficial Bruto [edicao={self.edicao}, data={self.data}]'
