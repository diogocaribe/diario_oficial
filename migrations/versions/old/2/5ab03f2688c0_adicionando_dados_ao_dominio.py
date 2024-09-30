"""adicionando dados ao dominio

Revision ID: 5ab03f2688c0
Revises: dfae75d03e16
Create Date: 2024-09-02 17:00:39.909988

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5ab03f2688c0'
down_revision: Union[str, None] = 'dfae75d03e16'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Inserir dados na tabela 'adm_direta'
    op.execute(
        sa.text("""
            INSERT INTO dominio.adm_direta (nome, sigla) VALUES
            ('SECRETARIA DO MEIO AMBIENTE', 'SEMA')
            ON CONFLICT (nome) DO NOTHING
        """)
    )

    # Inserir dados na tabela 'adm_indireta'
    op.execute(
        sa.text("""
            INSERT INTO dominio.adm_indireta (nome, sigla) VALUES
            ('Instituto do Meio Ambiente e Recursos Hídricos - INEMA', 'INEMA')
            ON CONFLICT (nome) DO NOTHING
        """)
    )

    # Inserir dados na tabela 'orgao_adm_indireta'
    op.execute(
        sa.text("""
            INSERT INTO dominio.divisao_adm_direta (nome, sigla) VALUES
            ('Diretoria Geral', 'DG')
            ON CONFLICT (nome) DO NOTHING
        """)
    )

    # Lista de valores a serem inseridos
    nomes = ['EXECUTIVO', 'LEGISLATIVO', 'JUDICIÁRIO']

    # Itera sobre cada valor e executa o INSERT
    for nome in nomes:
        op.execute(
            sa.text(f"INSERT INTO dominio.poder (nome) VALUES ('{nome}')"),
        )


def downgrade() -> None:
    # Remover os dados inseridos na reversão da migração
    op.execute(
        sa.text("""
            DELETE FROM dominio.adm_direta
            WHERE nome = 'SECRETARIA DO MEIO AMBIENTE'
        """)
    )

    op.execute(
        sa.text("""
            DELETE FROM dominio.adm_indireta
            WHERE nome = 'Instituto do Meio Ambiente e Recursos Hídricos - INEMA'
        """)
    )

    op.execute(
        sa.text("""
            DELETE FROM dominio.divisao_adm_indireta
            WHERE nome = 'Diretoria Geral'
        """)
    )

    op.execute(
        sa.text('DELETE FROM dominio.poder WHERE nome = :nome'),
        [{'nome': 'EXECUTIVO'}, {'nome': 'LEGISLATIVO'}, {'nome': 'JUDICIÁRIO'}],
    )
