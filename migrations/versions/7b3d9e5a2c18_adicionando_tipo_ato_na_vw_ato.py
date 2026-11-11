"""adicionando tipo de ato na vw_ato

Revision ID: 7b3d9e5a2c18
Revises: 4e8a2f6b1c37
Create Date: 2026-11-11 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b3d9e5a2c18'
down_revision: Union[str, None] = '4e8a2f6b1c37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Definição anterior (bcd56ebfe8e3), recriada no downgrade
VW_ATO_ANTERIOR = '''
    CREATE VIEW vw_ato AS
    SELECT
        a.id,
        a.conteudo_ato AS ato,
        db.nro_edicao,
        db.dt_edicao,
        p2.nome AS poder,
        ad.nome AS adm_direta,
        dad.nome AS divisao_adm_direta,
        ai.nome AS adm_indireta,
        dai.nome AS divisao_adm_indireta,
        tp.nome AS tipo_publicacao,
        p.nome_ato,
        p.link AS link_publicacao
    FROM processing.ato a
    JOIN processing.publicacao p ON a.publicacao_id = p.id
    JOIN processing.doe_bruto db ON p.doe_bruto_id = db.id
    LEFT JOIN dominio.poder p2 ON p.poder_id = p2.id
    LEFT JOIN dominio.adm_direta ad ON p.adm_direta_id = ad.id
    LEFT JOIN dominio.adm_indireta ai ON p.adm_indireta_id = ai.id
    LEFT JOIN dominio.divisao_adm_direta dad ON p.divisao_adm_direta_id = dad.id
    LEFT JOIN dominio.divisao_adm_indireta dai ON p.divisao_adm_indireta_id = dai.id
    LEFT JOIN dominio.tipo_publicacao tp ON p.tipo_publicacao_id = tp.id
    WHERE p.auditoria IS TRUE;
'''


def upgrade() -> None:
    # DROP + CREATE: as colunas novas ficam no meio da view, o que o
    # CREATE OR REPLACE VIEW não permite
    op.execute(sa.text('DROP VIEW IF EXISTS vw_ato;'))
    op.execute(sa.text('''
        -- Atos das publicações com auditoria aprovada. Um ato pode ter vários
        -- tipos: a view mantém uma linha por ato e junta os tipos com '; '
        -- (NULL quando o ato ainda não foi classificado ou não tem tipo).
        CREATE VIEW vw_ato AS
        SELECT
            a.id,
            a.conteudo_ato AS ato,
            ta.tipo_ato,
            ta.sigla_tipo_ato,
            db.nro_edicao,
            db.dt_edicao,
            p2.nome AS poder,
            ad.nome AS adm_direta,
            dad.nome AS divisao_adm_direta,
            ai.nome AS adm_indireta,
            dai.nome AS divisao_adm_indireta,
            tp.nome AS tipo_publicacao,
            p.nome_ato,
            p.link AS link_publicacao
        FROM processing.ato a
        JOIN processing.publicacao p ON a.publicacao_id = p.id
        JOIN processing.doe_bruto db ON p.doe_bruto_id = db.id
        LEFT JOIN dominio.poder p2 ON p.poder_id = p2.id
        LEFT JOIN dominio.adm_direta ad ON p.adm_direta_id = ad.id
        LEFT JOIN dominio.adm_indireta ai ON p.adm_indireta_id = ai.id
        LEFT JOIN dominio.divisao_adm_direta dad ON p.divisao_adm_direta_id = dad.id
        LEFT JOIN dominio.divisao_adm_indireta dai
            ON p.divisao_adm_indireta_id = dai.id
        LEFT JOIN dominio.tipo_publicacao tp ON p.tipo_publicacao_id = tp.id
        LEFT JOIN LATERAL (
            SELECT
                string_agg(t.nome, '; ' ORDER BY t.nome) AS tipo_ato,
                string_agg(DISTINCT t.sigla, '; ') AS sigla_tipo_ato
            FROM processing.ato_tipo_ato att
            JOIN dominio.tipo_ato t ON att.tipo_ato_id = t.id
            WHERE att.ato_id = a.id
        ) ta ON TRUE
        WHERE p.auditoria IS TRUE;
    '''))


def downgrade() -> None:
    op.execute(sa.text('DROP VIEW IF EXISTS vw_ato;'))
    op.execute(sa.text(VW_ATO_ANTERIOR))
