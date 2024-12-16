"""criando vw_publicacao vw_ato

Revision ID: e5c2ecd42738
Revises: ec81bc3343e8
Create Date: 2024-12-12 17:46:08.904481

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5c2ecd42738'
down_revision: Union[str, None] = 'ec81bc3343e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.execute(sa.text('''
        -- View da tabela de publicacao
        CREATE VIEW vw_publicacao AS
        SELECT 
            p.id, db.nro_edicao, db.dt_edicao, p2.nome AS poder,
            ad.nome AS adm_direta,
            dad.nome AS divisao_adm_direta,
            ai.nome AS adm_indireta,
            dai.nome AS divisao_adm_indireta,
            tp.nome AS tipo_publicacao, 
            p.nome_ato, p.identificador_link, p.link, p.conteudo_link  
        FROM processing.doe_bruto db 
        JOIN processing.publicacao p ON p.doe_bruto_id = db.id 
        LEFT JOIN dominio.poder p2 ON p.poder_id = p2.id 
        LEFT JOIN dominio.adm_direta ad ON p.adm_direta_id = ad.id
        LEFT JOIN dominio.adm_indireta ai ON p.adm_indireta_id = ai.id
        LEFT JOIN dominio.divisao_adm_direta dad ON p.divisao_adm_direta_id = dad.id
        LEFT JOIN dominio.divisao_adm_indireta dai ON p.divisao_adm_indireta_id = dai.id
        LEFT JOIN dominio.tipo_publicacao tp ON p.tipo_publicacao_id = tp.id;
    '''))

    op.execute(sa.text('''
        -- View para atos
        SELECT
            a.id,
            db.nro_edicao, db.dt_edicao,
            p2.nome AS poder,
            ad.nome AS adm_direta,
            dad.nome AS divisao_adm_direta,
            ai.nome AS adm_indireta,
            dai.nome AS divisao_adm_indireta,
            tp.nome AS tipo_publicacao,
            p.nome_ato, p.identificador_link AS identificador_publicacao, p.link AS link_publicacao, p.conteudo_link AS conteudo_publicacao, 
            a.conteudo_ato AS ato
        FROM processing.ato a
        LEFT JOIN processing.publicacao p ON a.publicacao_id = p.id
        LEFT JOIN processing.doe_bruto db ON p.doe_bruto_id = db.id 
        LEFT JOIN dominio.poder p2 ON p.poder_id = p2.id
        LEFT JOIN dominio.adm_direta ad ON p.adm_direta_id = ad.id
        LEFT JOIN dominio.adm_indireta ai ON p.adm_indireta_id = ai.id
        LEFT JOIN dominio.divisao_adm_direta dad ON p.divisao_adm_direta_id = dad.id
        LEFT JOIN dominio.divisao_adm_indireta dai ON p.divisao_adm_indireta_id = dai.id
        LEFT JOIN dominio.tipo_publicacao tp ON p.tipo_publicacao_id = tp.id;
    '''))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.execute(sa.text('DROP VIEW IF EXISTS vw_publicacao;'))
    op.execute(sa.text('DROP VIEW IF EXISTS vw_ato;'))
    # ### end Alembic commands ###
