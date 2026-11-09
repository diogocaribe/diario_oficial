"""criando vw_ato

Revision ID: bcd56ebfe8e3
Revises: c5884e0d6cc3
Create Date: 2026-11-09 16:31:07.384513

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bcd56ebfe8e3'
down_revision: Union[str, None] = 'c5884e0d6cc3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text('''
        -- Atos das publicações com auditoria aprovada
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
    '''))


def downgrade() -> None:
    op.execute(sa.text('DROP VIEW IF EXISTS vw_ato;'))
