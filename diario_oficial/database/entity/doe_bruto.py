from sqlalchemy import Column, Date, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

from typing import List

from ..configs.base import Base


class DiarioOficialBruto(Base):
    """Tabela responsável por armazenar a primeira coleta do sistema.
        Diário Oficial Estado = doe.
        nro = numero
        dt = data
    """

    __tablename__ = "doe_bruto"
    # O schema deve ser adicionado na versão gerada pelo alembic
    __table_args__ = {"schema": "processing"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    criado_em: Mapped[datetime] = mapped_column(
        server_default=func.now(), comment="Data e horario da coleta desse registro."
    )
    nro_edicao: Mapped[int] = mapped_column(
        nullable=True, unique=True, comment="Edição do DOE coletado."
    )
    dt_edicao = Column(Date, unique=True, comment="Data do DOE coletado.")
    existe: Mapped[bool] = mapped_column(
        nullable=False, comment="Se existe ou não publicação do DOE na data solicitada."
    )
    doe_json: Mapped[JSONB] = mapped_column(
        type_=JSONB, nullable=True, comment="Dados extraídos do DOE em formato json."
    )

    def __repr__(self):
        return f"Dados Diário Oficial Bruto [edicao={self.nro_edicao}, data={self.dt_edicao}]"
