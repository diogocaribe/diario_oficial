"""Gera o modelo lógico do banco diario_oficial em draw.io.

Uso: python gerar_drawio.py [nome_da_saida]
Grava na pasta deste script, de onde quer que seja rodado (caminho absoluto vale como
está) e acrescenta .drawio se o nome não tiver extensão. Sem argumento, grava
modelo_logico_diario_oficial.drawio.

As tabelas abaixo são escritas à mão a partir das entidades de
diario_oficial/database/entity/ e das migrações: ao mudar o banco, atualize aqui.
"""

import sys
from html import escape
from pathlib import Path

ROW_H = 26
KEY_W = 46

# Cores (preenchimento, borda) por esquema
DOM = ('#dae8fc', '#6c8ebf')
PROC = ('#d5e8d4', '#82b366')
AUTO = ('#e1d5e7', '#9673a6')
VIEW = ('#f5f5f5', '#666666')
PUB = ('#fff2cc', '#d6b656')
NOTA = ('#ffffff', '#999999')

# (id, título, x, y, largura, cor, [(chave, coluna)])
TABELAS = [
    # ---------------- esquema dominio ----------------
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
    ('tipo_ato', 'dominio.tipo_ato', 40, 960, 300, DOM, [
        ('PK', 'id: INTEGER'),
        ('UK', 'nome: VARCHAR NOT NULL'),
        ('', 'sigla: VARCHAR (não única)'),
    ]),
    # ---------------- esquema processing ----------------
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
    ('ato_tipo_ato', 'processing.ato_tipo_ato', 560, 860, 320, PROC, [
        ('PK,FK', 'ato_id: INTEGER'),
        ('PK,FK', 'tipo_ato_id: INTEGER'),
    ]),
    ('log_erro', 'processing.log_erro', 1180, 420, 340, PROC, [
        ('PK', 'id: INTEGER'),
        ('', 'criado_em: TIMESTAMPTZ NOT NULL DEFAULT now()'),
        ('CK', 'etapa: VARCHAR NOT NULL'),
        ('', 'tipo: VARCHAR NOT NULL'),
        ('', 'descricao: TEXT NOT NULL'),
        ('', 'trecho: TEXT'),
        ('FK', 'doe_bruto_id: INTEGER NOT NULL'),
        ('FK', 'publicacao_id: INTEGER'),
        ('FK', 'ato_id: INTEGER'),
    ]),
    # ---------------- esquema auto_infracao (extração com LLM) ----------------
    ('extracao_trecho', 'auto_infracao.extracao_trecho', 560, 1200, 360, AUTO, [
        ('PK', 'id: INTEGER'),
        ('FK', 'ato_id: INTEGER NOT NULL'),
        ('', 'sigla_tipo_ato: TEXT NOT NULL'),
        ('', 'trecho: TEXT NOT NULL'),
        ('', 'erro: TEXT'),
        ('', 'conferencia: JSONB'),
        ('', "preenchido_pela_regex: TEXT[] NOT NULL DEFAULT '{}'"),
        ('', 'modelo_llm: TEXT'),
        ('', 'extraido_em: TIMESTAMPTZ NOT NULL DEFAULT now()'),
    ]),
    ('auto_infracao', 'auto_infracao.auto_infracao', 560, 1510, 400, AUTO, [
        ('PK', 'id: INTEGER'),
        ('FK', 'extracao_trecho_id: INTEGER NOT NULL'),
        ('', 'tipo_auto: TEXT NOT NULL (discriminador)'),
        ('', 'nro_processo: TEXT'),
        ('CK', 'natureza: TEXT NOT NULL'),
        ('CK', 'resultado_recurso: TEXT'),
        ('', 'nro_ato_decisorio: TEXT'),
        ('', 'dt_homologacao: DATE'),
        ('', 'conduta: TEXT'),
        ('FK', 'local_infracao_id: INTEGER'),
        ('', 'dt_constatacao: DATE'),
        ('', 'hr_constatacao: TIME'),
        ('', 'sistema_referencia_espacial: TEXT'),
        ('', 'area_hectare: NUMERIC'),
        ('CK', 'gravidade: TEXT'),
        ('', "nro_lacre: TEXT[] NOT NULL DEFAULT '{}'"),
        ('', "especie_citada: TEXT[] NOT NULL DEFAULT '{}'"),
        ('FK', 'autuado_pessoa_id: INTEGER NOT NULL'),
        ('', 'autuado_nome: TEXT NOT NULL'),
        ('FK', 'endereco_autuado_id: INTEGER'),
        ('', 'ponto: geometry(POINT, 4674)'),
        ('', 'poligono: geometry(POLYGON, 4674)'),
    ]),
    ('pessoa', 'public.pessoa', 40, 1200, 300, PUB, [
        ('PK', 'id: INTEGER'),
        ('', 'nome: TEXT NOT NULL'),
        ('CK,UK', 'tipo_documento: TEXT'),
        ('UK', 'nro_documento: TEXT (só dígitos)'),
    ]),
    ('endereco', 'auto_infracao.endereco', 40, 1370, 300, AUTO, [
        ('PK', 'id: INTEGER'),
        ('', 'localidade: TEXT'),
        ('', 'logradouro: TEXT'),
        ('', 'numero: TEXT'),
        ('', 'complemento: TEXT'),
        ('', 'bairro: TEXT'),
        ('', 'rodovia: TEXT'),
        ('', 'cep: TEXT'),
        ('', 'municipio: TEXT'),
    ]),
    ('coordenada_extraida_trecho', 'auto_infracao.coordenada_extraida_trecho',
     40, 1670, 300, AUTO, [
        ('PK', 'id: INTEGER'),
        ('FK', 'auto_infracao_id: INTEGER NOT NULL'),
        ('', 'latitude: TEXT NOT NULL'),
        ('', 'longitude: TEXT NOT NULL'),
        ('', 'fuso_utm: TEXT'),
        ('CK', 'tipo: TEXT NOT NULL'),
    ]),
    ('bem_produto_autuado', 'auto_infracao.bem_produto_autuado', 40, 1890, 300, AUTO, [
        ('PK', 'id: INTEGER'),
        ('FK', 'auto_infracao_id: INTEGER NOT NULL'),
        ('', 'descricao: TEXT NOT NULL'),
        ('', 'quantidade: NUMERIC'),
        ('', 'unidade: TEXT'),
        ('', 'valor_avaliado: NUMERIC'),
        ('', 'identificacao: TEXT'),
    ]),
    # Subtipos (herança joined-table): PK = FK para auto_infracao.id
    ('auto_interdicao', 'auto_infracao.auto_interdicao (AIIN)', 1180, 1200, 340, AUTO, [
        ('PK,FK', 'auto_infracao_id: INTEGER'),
        ('CK', 'modalidade: TEXT'),
        ('', 'atividade_interditada: TEXT'),
        ('', 'excecao_interdicao: TEXT'),
        ('', 'condicao: TEXT'),
    ]),
    ('auto_multa', 'auto_infracao.auto_multa (AIMU)', 1180, 1390, 340, AUTO, [
        ('PK,FK', 'auto_infracao_id: INTEGER'),
        ('', 'valor_multa: NUMERIC'),
        ('CK', 'tipo_multa: TEXT'),
        ('', 'reincidente: BOOLEAN NOT NULL'),
        ('', 'percentual_desconto: NUMERIC'),
        ('', 'nro_notificacao: TEXT'),
    ]),
    ('auto_advertencia', 'auto_infracao.auto_advertencia (AIAD)',
     1180, 1606, 340, AUTO, [
        ('PK,FK', 'auto_infracao_id: INTEGER'),
        ('', 'exigencia: TEXT'),
        ('', 'prazo_atendimento_dias: INTEGER'),
        ('', 'nro_notificacao: TEXT'),
    ]),
    ('auto_apreensao', 'auto_infracao.auto_apreensao (AIAP)', 1180, 1770, 340, AUTO, [
        ('PK,FK', 'auto_infracao_id: INTEGER'),
        ('', 'fiel_depositario: TEXT'),
        ('', 'destinacao: TEXT'),
    ]),
    ('auto_embargo', 'auto_infracao.auto_embargo (AIEM)', 1180, 1908, 340, AUTO, [
        ('PK,FK', 'auto_infracao_id: INTEGER'),
        ('CK', 'modalidade: TEXT'),
        ('', 'objeto_embargado: TEXT'),
        ('', 'area_restricao_legal_uso: TEXT'),
    ]),
    ('auto_demolicao', 'auto_infracao.auto_demolicao (AIDM)', 1180, 2072, 340, AUTO, [
        ('PK,FK', 'auto_infracao_id: INTEGER'),
        ('', "obra_demolida: TEXT[] NOT NULL DEFAULT '{}'"),
        ('', 'area_restricao_legal_uso: TEXT'),
    ]),
    ('auto_destruicao_fornos', 'auto_infracao.auto_destruicao_fornos (AIDF)',
     1180, 2210, 340, AUTO, [
        ('PK,FK', 'auto_infracao_id: INTEGER'),
        ('', 'qtd_fornos: INTEGER'),
        ('', 'tipo_forno: TEXT'),
        ('', 'capacidade_por_forno: NUMERIC'),
        ('CK', 'situacao_forno: TEXT'),
    ]),
    ('auto_destruicao_produtos', 'auto_infracao.auto_destruicao_produtos (AIDP)',
     1180, 2400, 340, AUTO, [
        ('PK,FK', 'auto_infracao_id: INTEGER'),
    ]),
]

VIEWS = [
    ('vw_publicacao', 'public.vw_publicacao (VIEW)', 1180, 780, 340,
     'publicacao + doe_bruto + dominio.*'),
    ('vw_ato', 'public.vw_ato (VIEW)', 1180, 870, 340,
     'ato + publicacao (auditoria IS TRUE) + doe_bruto<br>+ dominio.* + tipo_ato e '
     "sigla_tipo_ato (juntos por '; ')"),
]

SUBTIPOS = [
    'auto_interdicao', 'auto_multa', 'auto_advertencia', 'auto_apreensao',
    'auto_embargo', 'auto_demolicao', 'auto_destruicao_fornos',
    'auto_destruicao_produtos',
]

# (tabela filha, coluna FK, tabela pai, rótulo). A cardinalidade sai das linhas:
# FK NOT NULL ou na PK → pai "exatamente um"; FK que é a PK inteira → filho "zero ou um".
RELACOES = [
    ('publicacao', 'doe_bruto_id', 'doe_bruto', 'ON DELETE CASCADE'),
    ('publicacao', 'poder_id', 'poder', ''),
    ('publicacao', 'adm_direta_id', 'adm_direta', ''),
    ('publicacao', 'adm_indireta_id', 'adm_indireta', ''),
    ('publicacao', 'divisao_adm_direta_id', 'divisao_adm_direta', ''),
    ('publicacao', 'divisao_adm_indireta_id', 'divisao_adm_indireta', ''),
    ('publicacao', 'tipo_publicacao_id', 'tipo_publicacao', ''),
    ('ato', 'publicacao_id', 'publicacao', 'ON DELETE CASCADE'),
    ('log_erro', 'doe_bruto_id', 'doe_bruto', ''),  # RESTRICT; rótulo tirado à mão
    ('log_erro', 'publicacao_id', 'publicacao', 'RESTRICT'),
    ('log_erro', 'ato_id', 'ato', 'SET NULL'),
    ('ato_tipo_ato', 'ato_id', 'ato', 'ON DELETE CASCADE'),
    ('ato_tipo_ato', 'tipo_ato_id', 'tipo_ato', 'ON DELETE CASCADE'),
    ('extracao_trecho', 'ato_id', 'ato', 'ON DELETE CASCADE'),
    ('auto_infracao', 'extracao_trecho_id', 'extracao_trecho', 'ON DELETE CASCADE'),
    ('auto_infracao', 'autuado_pessoa_id', 'pessoa', 'RESTRICT'),
    ('auto_infracao', 'local_infracao_id', 'endereco', 'SET NULL'),
    ('auto_infracao', 'endereco_autuado_id', 'endereco', 'SET NULL'),
    ('coordenada_extraida_trecho', 'auto_infracao_id', 'auto_infracao',
     'ON DELETE CASCADE'),
    ('bem_produto_autuado', 'auto_infracao_id', 'auto_infracao', 'ON DELETE CASCADE'),
] + [(sub, 'auto_infracao_id', 'auto_infracao', '') for sub in SUBTIPOS]

# Traçado das setas ajustado à mão no draw.io, por (tabela filha, coluna FK):
# 'pontos' são os pontos de passagem; 'rotulo' é (x, y, dx, dy) da posição do rótulo;
# 'sem_saida' deixa o draw.io escolher o lado de saída.
AJUSTES = {
    ('log_erro', 'doe_bruto_id'): {'pontos': [(1550, 619), (1550, 123)]},
    ('log_erro', 'publicacao_id'): {
        'pontos': [(1050, 645), (1050, 240), (1000, 240), (1000, 163)],
    },
    ('log_erro', 'ato_id'): {
        'pontos': [(1120, 671), (1120, 683)],
        'rotulo': (0.0192, -9, 9, -9),
    },
    ('ato_tipo_ato', 'ato_id'): {
        'pontos': [(1040, 904), (1040, 711), (990, 711), (990, 684)],
        'rotulo': (0.125, 0, 0, 0),
        'sem_saida': True,
    },
}

NOTAS = [
    ('nota_trigger', 560, 960, 320, 110,
     '<b>Trigger</b> after_delete_delete_atos_da_mesma_pubalicacao<br>'
     'AFTER DELETE ON processing.ato: apaga os demais atos da mesma '
     'publicação e faz publicacao.processada_para_ato = NULL.'),
    ('nota_ck', 1180, 700, 340, 60,
     "<b>CHECK</b> ck_log_erro_etapa:<br>etapa IN ('separacao', 'auditoria')"),
    ('nota_auto', 560, 2150, 400, 230,
     '<b>Herança joined-table</b>: cada auto_* tem PK = FK para auto_infracao.id '
     '(ON DELETE CASCADE), e tipo_auto guarda a tabela do subtipo.<br>'
     '<b>Geometrias</b> ponto e poligono em SIRGAS 2000 (SRID 4674), com índice GIST; '
     'o datum original fica em sistema_referencia_espacial.<br>'
     '<b>Único parcial</b> uq_pessoa_documento (tipo_documento, nro_documento) '
     'WHERE nro_documento IS NOT NULL.<br>'
     'bem_produto_autuado: bens do AIAP e produtos do AIDP.<br>'
     '<b>Trigger</b> after_delete_apagar_endereco_do_auto: AFTER DELETE ON '
     'auto_infracao apaga os endereços do auto (local_infracao_id e '
     'endereco_autuado_id). A pessoa continua.'),
    ('nota_ck_auto', 40, 2140, 500, 190,
     '<b>CHECK</b> do esquema auto_infracao:<br>'
     "auto_infracao.natureza IN ('homologacao', 'recurso', 'termo_de_compromisso', "
     "'sustacao', 'outro')<br>"
     "auto_infracao.resultado_recurso IN ('deferido', 'indeferido')<br>"
     "auto_infracao.gravidade IN ('leve', 'grave', 'gravissima')<br>"
     "public.pessoa.tipo_documento IN ('CPF', 'CNPJ', 'RG')<br>"
     "auto_interdicao.modalidade IN ('temporaria', 'definitiva')<br>"
     "auto_embargo.modalidade IN ('temporario', 'definitivo')<br>"
     "auto_multa.tipo_multa IN ('simples', 'diaria')<br>"
     "auto_destruicao_fornos.situacao_forno IN ('ativo', 'inativo')<br>"
     "coordenada_extraida_trecho.tipo IN ('ponto', 'vertice')"),
    ('legenda', 40, 2500, 1480, 70,
     '<b>Legenda</b> &nbsp; Azul: esquema <i>dominio</i> (lookup, carregado por migração) '
     '&nbsp;|&nbsp; Verde: esquema <i>processing</i> &nbsp;|&nbsp; Roxo: esquema '
     '<i>auto_infracao</i> (dados extraídos dos atos com LLM, PostGIS) &nbsp;|&nbsp; '
     'Amarelo: tabelas em <i>public</i>, comuns às extrações &nbsp;|&nbsp; '
     'Cinza: views em <i>public</i>.<br>PK = chave primária, FK = chave estrangeira, '
     'UK = único, CK = check. FKs para dominio.* sem ON DELETE explícito (NO ACTION).'),
]


def geom(x, y, w, h):
    return f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry" />'


def indice_coluna(linhas, coluna):
    for i, (_, texto) in enumerate(linhas):
        if texto.split(':')[0] == coluna:
            return i
    raise ValueError(f'coluna {coluna} não encontrada')


def gerar():
    cells = []
    posicoes = {}
    colunas = {}
    for tid, titulo, x, y, w, (fill, stroke), linhas in TABELAS:
        h = 30 + ROW_H * len(linhas)
        posicoes[tid] = (x, y, w, h)
        colunas[tid] = linhas
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
        posicoes[vid] = (x, y, w, 70)
        cells.append(
            f'<mxCell id="{vid}" value="{escape("<b>" + titulo + "</b><br>" + texto)}" '
            f'style="rounded=1;whiteSpace=wrap;html=1;dashed=1;fillColor={fill};'
            f'strokeColor={stroke};align=left;spacingLeft=8;" vertex="1" parent="1">'
            f'{geom(x, y, w, 70)}</mxCell>'
        )

    for nid, x, y, w, h, texto in NOTAS:
        fill, stroke = NOTA
        posicoes[nid] = (x, y, w, h)
        cells.append(
            f'<mxCell id="{nid}" value="{escape(texto)}" style="shape=note;size=14;'
            f'whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};align=left;'
            f'spacingLeft=8;fontSize=11;" vertex="1" parent="1">{geom(x, y, w, h)}</mxCell>'
        )

    for n, (filho, coluna, pai, rotulo) in enumerate(RELACOES):
        linhas = colunas[filho]
        idx = indice_coluna(linhas, coluna)
        chave, texto = linhas[idx]
        fim = 'ERmandOne' if 'NOT NULL' in texto or 'PK' in chave else 'ERzeroToOne'
        pk_unica = sum('PK' in k for k, _ in linhas) == 1
        inicio = 'ERzeroToOne' if 'PK' in chave and pk_unica else 'ERzeroToMany'
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
        ajuste = AJUSTES.get((filho, coluna), {})
        if ajuste.get('sem_saida'):
            saida = ''
        estilo = (
            f'edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;startArrow={inicio};'
            f'startFill=0;endArrow={fim};endFill=0;{saida}{entrada}fontSize=10;'
            f'labelBackgroundColor=#ffffff;'
        )
        lx, ly, dx, dy = ajuste.get('rotulo', (0, 0, 0, 0))
        internos = ''
        if dx or dy:
            internos += f'<mxPoint x="{dx}" y="{dy}" as="offset" />'
        if ajuste.get('pontos'):
            pontos = ''.join(f'<mxPoint x="{x}" y="{y}" />' for x, y in ajuste['pontos'])
            internos += f'<Array as="points">{pontos}</Array>'
        cells.append(
            f'<mxCell id="rel{n}" value="{escape(rotulo)}" style="{estilo}" edge="1" '
            f'parent="1" source="{filho}_r{idx}" target="{pai}_r0">'
            f'<mxGeometry x="{lx}" y="{ly}" relative="1" as="geometry">{internos}'
            f'</mxGeometry></mxCell>'
        )

    cells.append(
        '<mxCell id="titulo" value="&lt;b&gt;Modelo lógico — banco diario_oficial'
        '&lt;/b&gt; (PostgreSQL + PostGIS, migrações Alembic até b2d7f4a9c1e6, '
        '23-11-2026)" style="text;html=1;fontSize=16;align=left;" vertex="1" '
        f'parent="1">{geom(40, 20, 1000, 40)}</mxCell>'
    )

    largura = max(x + w for x, _, w, _ in posicoes.values()) + 80
    altura = max(y + h for _, y, _, h in posicoes.values()) + 40
    corpo = '\n        '.join(cells)
    return f'''<mxfile host="app.diagrams.net">
  <diagram name="Modelo lógico" id="modelo-logico-diario-oficial">
    <mxGraphModel grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{largura}" pageHeight="{altura}" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        {corpo}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
'''


PASTA_DO_SCRIPT = Path(__file__).resolve().parent
NOME_PADRAO = 'modelo_logico_diario_oficial.drawio'


def caminho_saida(nome: str) -> Path:
    """Caminho relativo vai para a pasta deste script; sem extensão, ganha .drawio."""
    saida = PASTA_DO_SCRIPT / nome  # caminho absoluto em `nome` prevalece
    return saida if saida.suffix else saida.with_suffix('.drawio')


if __name__ == '__main__':
    saida = caminho_saida(sys.argv[1] if len(sys.argv) > 1 else NOME_PADRAO)
    saida.write_text(gerar(), encoding='utf-8')
    print(f'Modelo lógico gravado em {saida}')
