"""criando as views das outorgas de recursos hídricos

Uma view por tipo de uso no esquema ``recurso_hidrico``, com uma linha por ponto:

- ``vw_outorga_captacao``: captação subterrânea e superficial (``modo`` diz qual);
- ``vw_outorga_lancamento``: lançamento de efluente, com a vazão de diluição e os
  parâmetros do efluente juntos em texto (``'; '``), repetidos em cada ponto do uso;
- ``vw_outorga_intervencao``: barramento, canalização, ponte, hidrelétrica, dragagem.

Cada linha traz o ponto (com a geometria em SIRGAS 2000), o uso, a portaria, o
outorgado (``public.pessoa``) e o ato, a publicação e a edição do DOE de onde a
outorga foi extraída.

``dt_vencimento`` é a data "válida até" do texto ou, sem ela, a data da portaria mais o
prazo em anos. Fica nula quando o prazo é o de outra portaria (``nro_portaria_prazo``)
ou quando falta o prazo ou a data da portaria.

O ponto entra por LEFT JOIN: um uso sem ponto aparece uma vez,
com as colunas do ponto nulas. A união das três dá todos os pontos
(``count(ponto_id)``) mais os usos sem ponto.

As três views são independentes (o SELECT comum é montado aqui): mudar uma não
obriga a apagar e recriar as outras.

Revision ID: 91d5d19a8321
Revises: 3a75dc1d4897
Create Date: 2026-11-24 15:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '91d5d19a8321'
down_revision: Union[str, None] = '3a75dc1d4897'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _endereco_em_texto(alias: str) -> str:
    """Partes preenchidas do endereço, separadas por vírgula (NULL se nenhuma)."""
    partes = (
        'logradouro',
        'numero',
        'complemento',
        'bairro',
        'localidade',
        'rodovia',
        'municipio',
        'cep',
    )
    return "NULLIF(concat_ws(', ', {}), '')".format(
        ', '.join(f"NULLIF(btrim({alias}.{p}), '')" for p in partes)
    )


def _lista_em_texto(coluna: str) -> str:
    """``text[]`` junto por ``'; '`` (NULL se vazio), como ``tipo_ato`` em vw_ato."""
    return f"NULLIF(array_to_string({coluna}, '; '), '')"


def _view(nome: str, colunas_proprias: str, join_proprio: str, filtro: str) -> str:
    """Uma linha por ponto: ponto, uso, portaria, outorgado e DOE."""
    return f"""
    CREATE VIEW recurso_hidrico.{nome} AS
    SELECT
        pt.id AS ponto_id,
        u.id AS uso_recurso_hidrico_id,
        o.id AS outorga_id,
        ato.id AS ato_id,
        et.sigla_tipo_ato,
        o.natureza,
        o.nro_portaria,
        o.dt_portaria,
        o.nro_processo,
        o.nro_processo_relacionado,
        o.outorgado_nome,
        pe.tipo_documento AS outorgado_tipo_documento,
        pe.nro_documento AS outorgado_nro_documento,
        {_endereco_em_texto('eo')} AS endereco_outorgado,
        eo.municipio AS municipio_outorgado,
        u.modo,
        u.prazo_validade_anos,
        u.dt_validade,
        COALESCE(
            u.dt_validade,
            (o.dt_portaria + make_interval(years => u.prazo_validade_anos))::date
        ) AS dt_vencimento,
        u.nro_portaria_prazo,
        u.dt_publicacao_portaria_prazo,
        u.bacia_hidrografica,
        u.finalidade_texto,
        {_lista_em_texto('u.finalidades')} AS finalidades,
        {_lista_em_texto('u.metodos_irrigacao')} AS metodos_irrigacao,
        u.area_ha,
        u.localidade,
        {_lista_em_texto('u.municipios')} AS municipios,
        pt.identificacao,
        pt.corpo_hidrico,
        pt.barramento,
        pt.barramento_dispensado,
        pt.latitude,
        pt.longitude,
        pt.sistema_referencia_espacial,
        pt.vazao_m3_dia,
        pt.vazao_m3_s,
        pt.captacao_horas_dia,
        pt.ponto,{colunas_proprias}
        db.nro_edicao,
        db.dt_edicao,
        tp.nome AS tipo_publicacao,
        p.nome_ato,
        p.link AS link_publicacao
    FROM recurso_hidrico.uso_recurso_hidrico u{join_proprio}
    LEFT JOIN recurso_hidrico.ponto_uso pt ON pt.uso_recurso_hidrico_id = u.id
    JOIN recurso_hidrico.outorga o ON u.outorga_id = o.id
    JOIN recurso_hidrico.extracao_trecho et ON o.extracao_trecho_id = et.id
    JOIN processing.ato ato ON et.ato_id = ato.id
    JOIN processing.publicacao p ON ato.publicacao_id = p.id
    JOIN processing.doe_bruto db ON p.doe_bruto_id = db.id
    LEFT JOIN public.pessoa pe ON o.outorgado_pessoa_id = pe.id
    LEFT JOIN recurso_hidrico.endereco eo ON o.endereco_outorgado_id = eo.id
    LEFT JOIN dominio.tipo_publicacao tp ON p.tipo_publicacao_id = tp.id
    WHERE {filtro};
"""


PARAMETROS_EM_TEXTO = """
        (SELECT string_agg(
                    pa.nome || ': ' || concat_ws(' ', pa.valor, pa.unidade),
                    '; ' ORDER BY pa.id)
         FROM recurso_hidrico.parametro_efluente pa
         WHERE pa.uso_lancamento_id = u.id) AS parametros_efluente,"""

# nome da view -> (colunas próprias, join da especialização, filtro)
VIEWS: dict[str, tuple[str, str, str]] = {
    'vw_outorga_captacao': ('', '', "u.tipo_uso = 'uso_captacao'"),
    'vw_outorga_lancamento': (
        """
        l.vazao_diluicao_m3_dia,
        l.vazao_diluicao_m3_s,"""
        + PARAMETROS_EM_TEXTO,
        """
    JOIN recurso_hidrico.uso_lancamento l ON l.uso_recurso_hidrico_id = u.id""",
        "u.tipo_uso = 'uso_lancamento'",
    ),
    'vw_outorga_intervencao': (
        """
        i.tipo_intervencao,
        i.volume_maximo_acumulacao_m3,
        i.altura_maxima_m,
        i.vazao_minima_jusante_m3_dia,
        i.vazao_minima_jusante_m3_s,
        i.descarga_de_fundo,
        i.vazao_projeto_m3_dia,
        i.vazao_projeto_m3_s,
        i.extensao_m,
        i.largura_m,
        i.comprimento_m,""",
        """
    JOIN recurso_hidrico.uso_intervencao i ON i.uso_recurso_hidrico_id = u.id""",
        "u.tipo_uso = 'uso_intervencao'",
    ),
}


def upgrade() -> None:
    for nome, (colunas, join, filtro) in VIEWS.items():
        op.execute(sa.text(_view(nome, colunas, join, filtro)))


def downgrade() -> None:
    for nome in VIEWS:
        op.execute(sa.text(f'DROP VIEW IF EXISTS recurso_hidrico.{nome};'))
