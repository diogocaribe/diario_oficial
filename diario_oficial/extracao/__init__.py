"""Extração de variáveis estruturadas do texto dos atos.

Fica separada do pipeline que organiza o DOE (raspagem -> publicação -> ato): aqui o
ponto de partida é ``processing.ato.conteudo_ato`` e a saída são registros com campos
tipados. Sem banco e sem efeito no import. Organização:

- ``normalizacao``: regras que padronizam valores escritos no texto (processo, data,
  hora, CEP, sistema de referência, município).
- ``utils_geo``: leitura de coordenadas em graus e UTM, conversão com o pyproj e a
  lista dos municípios da Bahia.
- ``modelo_comum``: os esquemas Pydantic comuns a todas as extrações (endereço,
  pessoa, par de coordenadas).
- ``modelo_auto_infracao``: os esquemas dos autos de infração: o auto comum
  (``AutoInfracao``) e os de cada subtipo (interdição, multa, advertência, apreensão,
  embargo, demolição, destruição).
- ``llm``: cadeia do LangChain com saída estruturada no ``ChatOllama``.
- ``base``: o contrato ``Extracao`` e a função ``extrair``, comum a todas.
- ``registro``: ``EXTRACOES``, as extrações pela sigla do tipo de ato.
- ``auto_infracao``: a extração dos autos de infração, a mesma para todos os subtipos
  (corte do texto em trechos, instruções e conferência por regex); cada subtipo é um
  ``SubtipoAuto`` com a sua sigla, penalidade, esquema e tabela, e vira uma
  ``Extracao`` em ``auto_infracao.EXTRACOES``.
- outro tipo de ato ganha o próprio módulo, com a sua ``Extracao``.
"""
