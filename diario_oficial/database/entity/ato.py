from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey
from diario_oficial.database.entity.publicacao import Publicacao
from ..configs.base import Base


class Ato(Base):
    """Tabela responsável por armazenar a primeira coleta do sistema.
    Diário Oficial Estado = doe.
    nro = numero
    dt = data
    """

    __tablename__ = 'ato'
    # O schema deve ser adicionado na versão gerada pelo alembic
    __table_args__ = {'schema': 'processing'}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    publicacao_id: Mapped[int] = mapped_column(
        ForeignKey('processing.publicacao.id', ondelete='CASCADE'), nullable=False
    )
    conteudo_ato: Mapped[str] = mapped_column(nullable=True)

    publicacao = relationship('Publicacao', backref='processing.ato')

    def __repr__(self):
        return f'Ato [publicacao={self.publicacao_id}, ato={self.conteudo_ato}]'
