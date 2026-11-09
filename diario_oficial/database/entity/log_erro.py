from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from diario_oficial.database.configs.base import Base


class LogErro(Base):
    """Histórico de erros da separação em atos e de achados da auditoria.

    Cada ocorrência é gravada uma vez, e criado_em guarda a primeira detecção (ver
    INSERIR_LOG_ERRO). Nas FKs, doe_bruto e publicacao usam RESTRICT porque não devem ser
    apagados (refazê-los exige nova raspagem ou coleta). Já os atos são apagados para
    reprocessar uma publicação, e o histórico sobrevive com ato_id NULL.
    """

    __tablename__ = 'log_erro'
    __table_args__ = (
        CheckConstraint("etapa IN ('separacao', 'auditoria')", name='etapa'),
        {'schema': 'processing'},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    etapa: Mapped[str] = mapped_column(String, nullable=False)
    tipo: Mapped[str] = mapped_column(
        String,
        nullable=False,
        comment='Nome da regra da auditoria ou tipo do erro da separação.',
    )
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    trecho: Mapped[str | None] = mapped_column(Text, nullable=True)
    doe_bruto_id: Mapped[int] = mapped_column(
        ForeignKey('processing.doe_bruto.id', ondelete='RESTRICT'),
        nullable=False,
        index=True,
    )
    publicacao_id: Mapped[int | None] = mapped_column(
        ForeignKey('processing.publicacao.id', ondelete='RESTRICT'),
        nullable=True,
        index=True,
    )
    ato_id: Mapped[int | None] = mapped_column(
        ForeignKey('processing.ato.id', ondelete='SET NULL'), nullable=True
    )

    def __repr__(self):
        return f'LogErro [etapa={self.etapa}, tipo={self.tipo}, publicacao={self.publicacao_id}]'
