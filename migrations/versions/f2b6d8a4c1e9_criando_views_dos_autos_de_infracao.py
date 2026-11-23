"""criando as views dos autos de infração

Uma view por tabela de auto no esquema ``auto_infracao``, com uma linha por auto:

- ``vw_auto_infracao``: as colunas comuns a todos os autos, já com o autuado
  (``public.pessoa``), os endereços em texto, a geometria e os dados do ato, da
  publicação e da edição do DOE de onde o auto foi extraído.
- ``vw_auto_<subtipo>``: ``vw_auto_infracao`` mais as colunas da tabela do subtipo.
  Na apreensão e na destruição de produtos, os bens/produtos ficam juntos em texto
  (``'; '``), para manter uma linha por auto; a lista detalhada fica em
  ``bem_produto_autuado``.

As views de subtipo dependem de ``vw_auto_infracao``: para mudar uma coluna dela,
apague e recrie todas.

Revision ID: f2b6d8a4c1e9
Revises: e7a3c9d1f4b6
Create Date: 2026-11-23 14:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f2b6d8a4c1e9'
down_revision: Union[str, None] = 'e7a3c9d1f4b6'
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


VW_AUTO_INFRACAO = f"""
    CREATE VIEW auto_infracao.vw_auto_infracao AS
    SELECT
        a.id,
        et.sigla_tipo_ato,
        a.nro_processo,
        a.natureza,
        a.resultado_recurso,
        a.nro_ato_decisorio,
        a.dt_homologacao,
        a.gravidade,
        a.conduta,
        a.dt_constatacao,
        a.hr_constatacao,
        a.autuado_nome,
        pe.tipo_documento AS autuado_tipo_documento,
        pe.nro_documento AS autuado_nro_documento,
        {_endereco_em_texto('ea')} AS endereco_autuado,
        ea.municipio AS municipio_autuado,
        {_endereco_em_texto('li')} AS local_infracao,
        li.municipio AS municipio_infracao,
        a.area_hectare,
        a.nro_lacre,
        a.especie_citada,
        a.sistema_referencia_espacial,
        a.ponto,
        a.poligono,
        db.nro_edicao,
        db.dt_edicao,
        tp.nome AS tipo_publicacao,
        p.nome_ato,
        p.link AS link_publicacao
    FROM auto_infracao.auto_infracao a
    JOIN auto_infracao.extracao_trecho et ON a.extracao_trecho_id = et.id
    JOIN processing.ato ato ON et.ato_id = ato.id
    JOIN processing.publicacao p ON ato.publicacao_id = p.id
    JOIN processing.doe_bruto db ON p.doe_bruto_id = db.id
    JOIN public.pessoa pe ON a.autuado_pessoa_id = pe.id
    LEFT JOIN auto_infracao.endereco ea ON a.endereco_autuado_id = ea.id
    LEFT JOIN auto_infracao.endereco li ON a.local_infracao_id = li.id
    LEFT JOIN dominio.tipo_publicacao tp ON p.tipo_publicacao_id = tp.id;
"""


def _bens_em_texto(nome: str) -> str:
    """Bens/produtos do auto juntos em texto e a quantidade de itens."""
    item = (
        "concat_ws(' ', b.descricao, "
        "'(' || NULLIF(concat_ws(' ', trim_scale(b.quantidade), b.unidade), '') || ')')"
    )
    return f"""
        (SELECT string_agg({item}, '; ' ORDER BY b.id)
         FROM auto_infracao.bem_produto_autuado b
         WHERE b.auto_infracao_id = v.id) AS {nome},
        (SELECT count(*)
         FROM auto_infracao.bem_produto_autuado b
         WHERE b.auto_infracao_id = v.id) AS qtd_{nome},
        (SELECT sum(b.valor_avaliado)
         FROM auto_infracao.bem_produto_autuado b
         WHERE b.auto_infracao_id = v.id) AS valor_avaliado_total"""


# tabela do subtipo -> colunas próprias na view (depois das de vw_auto_infracao)
SUBTIPOS: dict[str, str] = {
    'auto_interdicao': """
        s.modalidade,
        s.atividade_interditada,
        s.excecao_interdicao,
        s.condicao""",
    'auto_multa': """
        s.valor_multa,
        s.tipo_multa,
        s.reincidente,
        s.percentual_desconto,
        s.nro_notificacao""",
    'auto_advertencia': """
        s.exigencia,
        s.prazo_atendimento_dias,
        s.nro_notificacao""",
    'auto_apreensao': f"""
        s.fiel_depositario,
        s.destinacao,{_bens_em_texto('bem_apreendido')}""",
    'auto_embargo': """
        s.modalidade,
        s.objeto_embargado,
        s.area_restricao_legal_uso""",
    'auto_demolicao': """
        s.obra_demolida,
        s.area_restricao_legal_uso""",
    'auto_destruicao_fornos': """
        s.qtd_fornos,
        s.tipo_forno,
        s.capacidade_por_forno,
        s.situacao_forno""",
    'auto_destruicao_produtos': _bens_em_texto('produto_destruido').lstrip(),
}


def upgrade() -> None:
    op.execute(sa.text(VW_AUTO_INFRACAO))
    for tabela, colunas in SUBTIPOS.items():
        op.execute(
            sa.text(f"""
            CREATE VIEW auto_infracao.vw_{tabela} AS
            SELECT
                v.*,{colunas}
            FROM auto_infracao.vw_auto_infracao v
            JOIN auto_infracao.{tabela} s ON s.auto_infracao_id = v.id;
        """)
        )


def downgrade() -> None:
    for tabela in SUBTIPOS:
        op.execute(sa.text(f'DROP VIEW IF EXISTS auto_infracao.vw_{tabela};'))
    op.execute(sa.text('DROP VIEW IF EXISTS auto_infracao.vw_auto_infracao;'))
