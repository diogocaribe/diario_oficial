from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from diario_oficial.database.configs.base import Base


class AtoTipoAto(Base):
    """Tipos de ato encontrados em cada ato: um ato pode ter vários tipos.
        Classe responsável por armazenar a relação entre atos e tipos de atos, 
        permitindo que um ato tenha múltiplos tipos associados a ele (um para muitos).     
    """

    __tablename__ = 'ato_tipo_ato'
    __table_args__ = {'schema': 'processing'}

    # CASCADE: reprocessar a publicação apaga os atos e, com eles, os tipos extraídos
    ato_id: Mapped[int] = mapped_column(
        ForeignKey('processing.ato.id', ondelete='CASCADE'), primary_key=True
    )
    # CASCADE: apagar um tipo classificado por engano em dominio.tipo_ato apaga os
    # vínculos dele; os atos que ficarem sem tipo voltam a ser analisados
    tipo_ato_id: Mapped[int] = mapped_column(
        ForeignKey('dominio.tipo_ato.id', ondelete='CASCADE'),
        primary_key=True,
        index=True,
    )
