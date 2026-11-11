from database.repository.doe_bruto_repository import DiarioOficialBrutoRepository
from diario_oficial.database.repository.publicacao_repository import PublicacaoRepository
from diario_oficial.database.repository.ato_repository import AtoRepository
from diario_oficial.database.repository.auditoria_repository import AuditoriaRepository
from diario_oficial.database.repository.log_erro_repository import LogErroRepository
from diario_oficial.database.repository.tipo_ato_repository import TipoAtoRepository

doe_bruto = DiarioOficialBrutoRepository()

publicacao = PublicacaoRepository()

ato = AtoRepository()

auditoria = AuditoriaRepository()

log_erro = LogErroRepository()

tipo_ato = TipoAtoRepository()
