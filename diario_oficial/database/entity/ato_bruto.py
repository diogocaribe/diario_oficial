from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column


from ..configs.base import Base


class AtoBruto(Base):
    """_summary_

    Args:
        Base (_type_): _description_

    Returns:
        _type_: _description_
    """

    __tablename__ = 'ato_bruto'
    __table_args__ = {'schema': 'processing'}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    edicao_id: Mapped[int] = mapped_column(ForeignKey('diario_oficial_bruto.edicao'))
    poder_id: Mapped[int] = mapped_column(ForeignKey('poder.id'))
    nome_ato: Mapped[str]
    identificador_link: Mapped[str]
    html_link: Mapped[str]

    def __repr__(self):
        return f'Ato Bruto [Identificador={self.edicao}, data={self.data}]'
