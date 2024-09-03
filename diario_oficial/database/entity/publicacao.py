from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from typing import List


from ..configs.base import Base


class Publicacao(Base):
    """_summary_

    Args:
        Base (_type_): _description_

    Returns:
        _type_: _description_
    """

    __tablename__ = 'publicacao'
    __table_args__ = {'schema': 'processing'}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    doe_nro_edicao: Mapped[int] = mapped_column(ForeignKey('processing.doe_bruto.nro_edicao'))
    poder_id: Mapped[int] = mapped_column(ForeignKey('dominio.poder.id'))
    adm_direta_id: Mapped[int] = mapped_column(ForeignKey('dominio.adm_direta.id'))
    adm_indireta_id: Mapped[int] = mapped_column(ForeignKey('dominio.adm_indireta.id'))
    divisao_adm_direta_id: Mapped[int] = mapped_column(ForeignKey('dominio.divisao_adm_direta.id'))
    nome_ato: Mapped[str]
    identificador_link: Mapped[str]
    link: Mapped[str]

    def __repr__(self):
        return f'Publicação [Identificador={self.doe_nro_edicao}, nome={self.nome_ato}]'
