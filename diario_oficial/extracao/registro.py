"""Extrações disponíveis, pela sigla do tipo de ato (``dominio.tipo_ato.sigla``).

Os autos de infração (AIIN, AIMU, AIAD, AIAP, AIEM, AIDM, AIDF, AIDP) vêm de
``auto_infracao.EXTRACOES``. Extração de outro tipo de ato: criar o módulo com a sua
``Extracao`` e incluir aqui.
"""

from diario_oficial.extracao import auto_infracao
from diario_oficial.extracao.base import Extracao

EXTRACOES: dict[str, Extracao] = {**auto_infracao.EXTRACOES}
