"""Gera o modelo lógico do banco diario_oficial em draw.io."""

import sys
from html import escape

ROW_H = 26
KEY_W = 46

# (id, título, x, y, largura, cor, [(chave, coluna)], tracejado)
DOM = ('#dae8fc', '#6c8ebf')
PROC = ('#d5e8d4', '#82b366')
NOVO = ('#fff2cc', '#d6b656')
VIEW = ('#f5f5f5', '#666666')
NOTA = ('#ffffff', '#999999')

TABELAS = [
    # ---------------- schema dominio ----------------
    ('poder', 'dominio.poder', 40, 80, 300, DOM, [
        ('PK', 'id: INTEGER'),
        ('UK', 'nome: VARCHAR NOT NULL'),
    ]),
    ('adm_direta', 'dominio.adm_direta', 40, 200, 300, DOM, [
        ('PK', 'id: INTEGER'),
        ('UK', 'nome: VARCHAR NOT NULL'),
        ('', 'sigla: VARCHAR'),
    ]),
    ('adm_indireta', 'dominio.adm_indireta', 40, 346, 300, DOM, [
        ('PK', 'id: INTEGER'),
        ('UK', 'nome: VARCHAR'),
        ('', 'sigla: VARCHAR'),
    ]),
    ('divisao_adm_direta', 'dominio.divisao_adm_direta', 40, 492, 300, DOM, [
        ('PK', 'id: INTEGER'),
        ('UK', 'nome: VARCHAR'),
        ('', 'sigla: VARCHAR'),
    ]),
    ('divisao_adm_indireta', 'dominio.divisao_adm_indireta', 40, 638, 300, DOM, [
        ('PK', 'id: INTEGER'),
        ('UK', 'nome: VARCHAR'),
        ('', 'sigla: VARCHAR'),
    ]),
    ('tipo_publicacao', 'dominio.tipo_publicacao', 40, 784, 300, DOM, [
        ('PK', 'id: INTEGER'),
        ('UK', 'nome: VARCHAR'),
        ('', 'sigla: VARCHAR'),
    ]),
    # ---------------- schema processing ----------------
    ('doe_bruto', 'processing.doe_bruto', 1180, 80, 340, PROC, [
        ('PK', 'id: INTEGER'),
        ('', 'criado_em: TIMESTAMP DEFAULT now()'),
        ('UK', 'nro_edicao: INTEGER'),
        ('UK', 'dt_edicao: DATE'),
        ('', 'existe: BOOLEAN NOT NULL'),
        ('', 'doe_json: JSONB'),
        ('', 'url: VARCHAR'),
        ('', 'doe_bruto_para_publicacao: BOOLEAN'),
    ]),
    ('publicacao', 'processing.publicacao', 520, 120, 400, PROC, [
        ('PK', 'id: INTEGER'),
        ('FK', 'doe_bruto_id: INTEGER NOT NULL'),
        ('FK', 'poder_id: INTEGER NOT NULL'),
        ('FK', 'adm_direta_id: INTEGER'),
        ('FK', 'adm_indireta_id: INTEGER'),
        ('FK', 'divisao_adm_direta_id: INTEGER'),
        ('FK', 'divisao_adm_indireta_id: INTEGER'),
        ('FK', 'tipo_publicacao_id: INTEGER'),
        ('', 'nome_ato: VARCHAR NOT NULL'),
        ('UK', 'identificador_link: VARCHAR NOT NULL'),
        ('', 'link: VARCHAR NOT NULL'),
        ('', 'conteudo_link: VARCHAR'),
        ('', 'processada_para_ato: BOOLEAN'),
        ('', 'auditoria: BOOLEAN'),
    ]),
    ('ato', 'processing.ato', 560, 640, 320, PROC, [
        ('PK', 'id: INTEGER'),
        ('FK', 'publicacao_id: INTEGER NOT NULL'),
        ('', 'conteudo_ato: VARCHAR'),
    ]),
    ('log_erro', 'processing.log_erro', 1180, 420, 340, PROC, [
        ('PK', 'id: INTEGER'),
        ('', 'criado_em: TIMESTAMPTZ NOT NULL DEFAULT now()'),
        ('CK', "etapa: VARCHAR NOT NULL"),
        ('', 'tipo: VARCHAR NOT NULL'),
        ('', 'descricao: TEXT NOT NULL'),
        ('', 'trecho: TEXT'),
        ('FK', 'doe_bruto_id: INTEGER NOT NULL'),
        ('FK', 'publicacao_id: INTEGER'),
        ('FK', 'ato_id: INTEGER'),
    ]),
    # ---------- feat/tipos-de-ato (migração 4e8a2f6b1c37, não aplicada) ----------
    ('ato_tipo_ato', 'processing.ato_tipo_ato', 560, 860, 320, NOVO, [
        ('PK,FK', 'ato_id: INTEGER'),
        ('PK,FK', 'tipo_ato_id: INTEGER'),
    ]),
    ('tipo_ato', 'dominio.tipo_ato', 40, 960, 300, NOVO, [
        ('PK', 'id: INTEGER'),
        ('UK', 'nome: VARCHAR NOT NULL'),
        ('', 'sigla: VARCHAR (não única)'),
    ]),
]

VIEWS = [
    ('vw_publicacao', 'public.vw_publicacao (VIEW)', 1180, 780, 340,
     'publicacao + doe_bruto + dominio.*'),
    ('vw_ato', 'public.vw_ato (VIEW)', 1180, 870, 340,
     'ato + publicacao (auditoria IS TRUE)<br>+ doe_bruto + dominio.*'),
]

# (origem/tabela filha, coluna FK, destino/tabela pai, rótulo, cardinalidade do filho)
# cardinalidade: 'many' = 0..N, 'one_many' = 1..N
RELACOES = [
    ('publicacao', 1, 'doe_bruto', 'ON DELETE CASCADE'),
    ('publicacao', 2, 'poder', ''),
    ('publicacao', 3, 'adm_direta', ''),
    ('publicacao', 4, 'adm_indireta', ''),
    ('publicacao', 5, 'divisao_adm_direta', ''),
    ('publicacao', 6, 'divisao_adm_indireta', ''),
    ('publicacao', 7, 'tipo_publicacao', ''),
    ('ato', 1, 'publicacao', 'ON DELETE CASCADE'),
    ('log_erro', 6, 'doe_bruto', 'RESTRICT'),
    ('log_erro', 7, 'publicacao', 'RESTRICT'),
    ('log_erro', 8, 'ato', 'SET NULL'),
    ('ato_tipo_ato', 0, 'ato', 'ON DELETE CASCADE'),
    ('ato_tipo_ato', 1, 'tipo_ato', 'RESTRICT'),
]

# FKs obrigatórias (NOT NULL) → lado pai "exatamente um"; opcionais → "zero ou um"
FK_OBRIGATORIA = {
    ('publicacao', 1), ('publicacao', 2), ('ato', 1), ('log_erro', 6),
    ('ato_tipo_ato', 0), ('ato_tipo_ato', 1),
}

NOTAS = [
    ('nota_trigger', 560, 960 + 0, 320, 110,
     '<b>Trigger</b> after_delete_delete_atos_da_mesma_pubalicacao<br>'
     'AFTER DELETE ON processing.ato: apaga os demais atos da mesma '
     'publicação e faz publicacao.processada_para_ato = NULL.'),
    ('nota_ck', 1180, 700, 340, 60,
     "<b>CHECK</b> ck_log_erro_etapa:<br>etapa IN ('separacao', 'auditoria')"),
    ('legenda', 40, 1110, 880, 90,
     '<b>Legenda</b> &nbsp; Azul: schema <i>dominio</i> (lookup, carregado por migração) '
     '&nbsp;|&nbsp; Verde: schema <i>processing</i> &nbsp;|&nbsp; Amarelo: branch '
     'feat/tipos-de-ato, migração 4e8a2f6b1c37 ainda não aplicada &nbsp;|&nbsp; Cinza: '
     'views em <i>public</i>.<br>PK = chave primária, FK = chave estrangeira, UK = único, '
     'CK = check. FKs para dominio.* sem ON DELETE explícito (NO ACTION).'),
]


def geom(x, y, w, h):
    return f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry" />'


def gerar():
    cells = []
    posicoes = {}
    for tid, titulo, x, y, w, (fill, stroke), linhas in TABELAS:
        h = 30 + ROW_H * len(linhas)
        posicoes[tid] = (x, y, w, h)
        cells.append(
            f'<mxCell id="{tid}" value="{escape(titulo)}" style="shape=table;startSize=30;'
            f'container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=0;'
            f'fontStyle=1;align=center;resizeLast=1;html=1;fillColor={fill};'
            f'strokeColor={stroke};" vertex="1" parent="1">{geom(x, y, w, h)}</mxCell>'
        )
        for i, (chave, coluna) in enumerate(linhas):
            rid = f'{tid}_r{i}'
            borda = 1 if chave.startswith('PK') and (
                i + 1 == len(linhas) or not linhas[i + 1][0].startswith('PK')
            ) else 0
            cells.append(
                f'<mxCell id="{rid}" value="" style="shape=tableRow;horizontal=0;'
                f'startSize=0;swimlaneHead=0;swimlaneBody=0;fillColor=#ffffff;'
                f'collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];'
                f'portConstraint=eastwest;top=0;left=0;right=0;bottom={borda};'
                f'strokeColor={stroke};" vertex="1" parent="{tid}">'
                f'{geom(0, 30 + i * ROW_H, w, ROW_H)}</mxCell>'
            )
            negrito = 1 if chave else 0
            sublinhado = 4 if 'PK' in chave else 0
            cells.append(
                f'<mxCell id="{rid}_k" value="{escape(chave)}" style="shape=partialRectangle;'
                f'connectable=0;fillColor=none;top=0;left=0;bottom=0;right=0;'
                f'fontStyle={negrito};fontSize=10;overflow=hidden;html=1;" vertex="1" '
                f'parent="{rid}">{geom(0, 0, KEY_W, ROW_H)}</mxCell>'
            )
            cells.append(
                f'<mxCell id="{rid}_c" value="{escape(coluna)}" style="shape=partialRectangle;'
                f'connectable=0;fillColor=none;top=0;left=0;bottom=0;right=0;align=left;'
                f'spacingLeft=6;fontStyle={sublinhado};overflow=hidden;html=1;" vertex="1" '
                f'parent="{rid}">{geom(KEY_W, 0, w - KEY_W, ROW_H)}</mxCell>'
            )

    for vid, titulo, x, y, w, texto in VIEWS:
        fill, stroke = VIEW
        cells.append(
            f'<mxCell id="{vid}" value="{escape("<b>" + titulo + "</b><br>" + texto)}" '
            f'style="rounded=1;whiteSpace=wrap;html=1;dashed=1;fillColor={fill};'
            f'strokeColor={stroke};align=left;spacingLeft=8;" vertex="1" parent="1">'
            f'{geom(x, y, w, 70)}</mxCell>'
        )

    for nid, x, y, w, h, texto in NOTAS:
        fill, stroke = NOTA
        cells.append(
            f'<mxCell id="{nid}" value="{escape(texto)}" style="shape=note;size=14;'
            f'whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};align=left;'
            f'spacingLeft=8;fontSize=11;" vertex="1" parent="1">{geom(x, y, w, h)}</mxCell>'
        )

    for n, (filho, idx, pai, rotulo) in enumerate(RELACOES):
        fim = 'ERmandOne' if (filho, idx) in FK_OBRIGATORIA else 'ERzeroToOne'
        fx = posicoes[filho][0]
        px = posicoes[pai][0]
        if abs(px - fx) < 100 and px != fx:
            saida, entrada = 'exitX=0;exitY=0.5;', 'entryX=0;entryY=0.5;'
        elif px < fx:
            saida, entrada = 'exitX=0;exitY=0.5;', 'entryX=1;entryY=0.5;'
        elif px > fx:
            saida, entrada = 'exitX=1;exitY=0.5;', 'entryX=0;entryY=0.5;'
        else:
            saida, entrada = 'exitX=1;exitY=0.5;', 'entryX=1;entryY=0.5;'
        estilo = (
            f'edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;startArrow=ERzeroToMany;'
            f'startFill=0;endArrow={fim};endFill=0;{saida}{entrada}fontSize=10;'
            f'labelBackgroundColor=#ffffff;'
        )
        cells.append(
            f'<mxCell id="rel{n}" value="{escape(rotulo)}" style="{estilo}" edge="1" '
            f'parent="1" source="{filho}_r{idx}" target="{pai}_r0">'
            f'<mxGeometry relative="1" as="geometry" /></mxCell>'
        )

    cells.append(
        '<mxCell id="titulo" value="&lt;b&gt;Modelo lógico — banco diario_oficial'
        '&lt;/b&gt; (PostgreSQL, estado das migrações Alembic em 11-11-2026)" '
        'style="text;html=1;fontSize=16;align=left;" vertex="1" parent="1">'
        f'{geom(40, 20, 900, 40)}</mxCell>'
    )

    corpo = '\n        '.join(cells)
    return f'''<mxfile host="app.diagrams.net">
  <diagram name="Modelo lógico" id="modelo-logico-diario-oficial">
    <mxGraphModel grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1600" pageHeight="1250" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        {corpo}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
'''


if __name__ == '__main__':
    with open(sys.argv[1], 'w', encoding='utf-8') as f:
        f.write(gerar())
