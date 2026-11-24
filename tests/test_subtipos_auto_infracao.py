from decimal import Decimal

import pytest
from sqlalchemy import inspect

from diario_oficial.database.entity import auto_infracao as entidades
from diario_oficial.extracao import auto_infracao
from diario_oficial.extracao.gravacao_auto_infracao import CAMPOS_ANINHADOS, para_auto
from diario_oficial.extracao.modelo_auto_infracao import (
    AutoAdvertencia,
    AutoApreensao,
    AutoDemolicao,
    AutoDestruicaoFornos,
    AutoDestruicaoProdutos,
    AutoEmbargo,
    AutoInfracao,
    AutoMulta,
    ExtracaoAdvertencia,
    ExtracaoApreensao,
    ExtracaoDemolicao,
    ExtracaoDestruicaoFornos,
    ExtracaoDestruicaoProdutos,
    ExtracaoEmbargo,
    ExtracaoMulta,
    BemProdutoAutuado,
)
from diario_oficial.extracao.modelo_comum import Pessoa
from diario_oficial.extracao.normalizacao import normalizar_numero
from diario_oficial.extracao.registro import EXTRACOES

SUBTIPOS = {
    AutoAdvertencia: ExtracaoAdvertencia,
    AutoApreensao: ExtracaoApreensao,
    AutoDemolicao: ExtracaoDemolicao,
    AutoDestruicaoFornos: ExtracaoDestruicaoFornos,
    AutoDestruicaoProdutos: ExtracaoDestruicaoProdutos,
    AutoEmbargo: ExtracaoEmbargo,
    AutoMulta: ExtracaoMulta,
}


def _auto(classe, **campos):
    padrao = dict.fromkeys(classe.model_fields)
    padrao.update(
        natureza='homologacao',
        coordenada=[],
        nro_lacre=[],
        especie_citada=[],
        autuado=Pessoa(
            nome='FULANO', tipo_documento=None, nro_documento=None, endereco=None
        ),
    )
    for campo, info in classe.model_fields.items():
        if campo not in AutoInfracao.model_fields and info.annotation is not None:
            if getattr(info.annotation, '__origin__', None) is list:
                padrao[campo] = []
    if 'reincidente' in classe.model_fields:
        padrao['reincidente'] = False
    return classe(**{**padrao, **campos})


def _item(**campos) -> BemProdutoAutuado:
    return BemProdutoAutuado(
        **{**dict.fromkeys(BemProdutoAutuado.model_fields), **campos}
    )


@pytest.mark.parametrize('classe', SUBTIPOS)
def test_subtipo_herda_o_auto_e_obriga_todos_os_campos(classe):
    assert issubclass(classe, AutoInfracao)
    esquema = classe.model_json_schema()
    assert set(esquema['required']) == set(classe.model_fields)
    assert 'ponto' not in esquema['properties']
    assert SUBTIPOS[classe].model_fields['auto'].annotation == list[classe]


def test_item_autuado_obriga_todos_os_campos():
    esquema = BemProdutoAutuado.model_json_schema()
    assert set(esquema['required']) == set(BemProdutoAutuado.model_fields)


def test_normalizar_numero():
    assert normalizar_numero('R$ 12.000,00') == 12000.0
    assert normalizar_numero('6,29 ST') == 6.29
    assert normalizar_numero('6.29') == 6.29
    assert normalizar_numero('12.000') == 12000.0
    assert normalizar_numero('1.250.000,50') == 1250000.5
    assert normalizar_numero(45) == 45.0
    assert normalizar_numero('sem valor') is None
    assert normalizar_numero(None) is None


def test_item_converte_quantidade_e_valor_do_texto():
    item = _item(descricao='motosserra', quantidade='01', valor_avaliado='R$ 1.000,00')
    assert item.quantidade == 1.0
    assert item.valor_avaliado == 1000.0


def test_apreensao_e_destruicao_de_produtos_usam_itens():
    apreensao = _auto(
        AutoApreensao,
        bem_apreendido=[_item(descricao='lenha', quantidade='14', unidade='st')],
        fiel_depositario='o próprio autuado',
    )
    assert apreensao.bem_apreendido[0].quantidade == 14.0
    destruicao = _auto(
        AutoDestruicaoProdutos,
        produto_destruido=[_item(descricao='carvão vegetal', quantidade='45')],
    )
    assert destruicao.produto_destruido[0].descricao == 'carvão vegetal'


def test_multa_converte_valor_e_desconto():
    multa = _auto(
        AutoMulta,
        valor_multa='R$ 50.000,00',
        tipo_multa='simples',
        percentual_desconto='60%',
        nro_notificacao='2018-003698/TEC/NOT-1040',
    )
    assert multa.valor_multa == 50000.0
    assert multa.percentual_desconto == 60.0
    assert multa.reincidente is False


def test_fornos_e_embargo():
    fornos = _auto(
        AutoDestruicaoFornos,
        qtd_fornos=2,
        tipo_forno='iglu',
        capacidade_por_forno='05',
        situacao_forno='ativo',
    )
    assert fornos.capacidade_por_forno == 5.0
    embargo = _auto(AutoEmbargo, modalidade='temporario')
    assert embargo.modalidade == 'temporario'
    with pytest.raises(ValueError):
        _auto(AutoEmbargo, modalidade='temporária')


def test_demolicao_e_advertencia():
    demolicao = _auto(
        AutoDemolicao,
        obra_demolida=['casa', 'sanitário'],
        area_restricao_legal_uso='APP - faixa marginal do Rio Formoso',
    )
    assert demolicao.obra_demolida == ['casa', 'sanitário']
    advertencia = _auto(
        AutoAdvertencia, exigencia='cessar a atividade', prazo_atendimento_dias=90
    )
    assert advertencia.prazo_atendimento_dias == 90


# Extração e gravação de cada subtipo (auto_infracao e gravacao_auto_infracao).

# Edital com um autuado de cada subtipo (trechos reais encurtados).
EDITAL_DE_TODOS = (
    'Autuados: ANA, CPF nº 111.111.111-11 nos autos do processo administrativo nº '
    '2017-009301/TEC/AIIN-0222, em 01/04/2019, foi homologado o Auto de Infração de '
    'Interdição Temporária, "por operar sem licença."; BETO, CPF nº 222.222.222-22 '
    'nos autos do processo administrativo nº 2014-001430/TEC/AIMU-0094, em '
    '25/06/2020, foi homologado o Auto de Infração de Multa no valor original de '
    'R$ 30.000,00, "por descumprir o Auto de Infração de Embargo Temporário n° '
    '2013-009522/TEC/AIEM-0024."; CARLA, CPF nº 333.333.333-33 nos autos do processo '
    'administrativo nº 2011-013177/TEC/AIAD-0174, em 09/05/2019, foi homologado o Auto '
    'de Infração de Advertência, "por operar sem licença."; DANI, CPF nº '
    '444.444.444-44 nos autos do processo administrativo nº 2015-000284/TEC/AIAP-0006, '
    'em 02/02/2016, foi homologado o Auto de Infração de Apreensão, "de 14 st de '
    'lenha."; EDU, CPF nº 555.555.555-55 nos autos do processo administrativo nº '
    '2009-032890/TEC/AIEM-0058, em 03/03/2015, foi homologado o Auto de Infração de '
    'Embargo Definitivo, "de obra em APP."; FABI, CPF nº 666.666.666-66 nos autos do '
    'processo administrativo nº 2012-000001/TEC/AIDM-0001, em 04/04/2014, foi '
    'homologado o Auto de Infração de Demolição, "de casa em APP."; GUI, CPF nº '
    '777.777.777-77 nos autos do processo administrativo nº '
    '2012-000002/TEC/AIDF-0002, em 05/05/2014, foi homologado o Auto de Infração de '
    'Destruição de Fornos para Produção de Carvão Vegetal, "de 02 fornos."; HELO, CPF '
    'nº 888.888.888-88 nos autos do processo administrativo nº '
    '2012-000003/TEC/AIDP-0003, em 06/06/2014, foi homologado o Auto de Infração de '
    'Destruição ou Inutilização de Produtos, "de 45 m³ de carvão."'
)
AUTUADO_DE_CADA_SIGLA = {
    'AIIN': 'ANA',
    'AIMU': 'BETO',
    'AIAD': 'CARLA',
    'AIAP': 'DANI',
    'AIEM': 'EDU',
    'AIDM': 'FABI',
    'AIDF': 'GUI',
    'AIDP': 'HELO',
}


def test_cada_subtipo_registrado_pela_sigla_com_o_seu_esquema():
    autos = {sigla for sigla in EXTRACOES if sigla.startswith('AI')}
    assert autos == set(AUTUADO_DE_CADA_SIGLA)
    for subtipo in auto_infracao.SUBTIPOS:
        extracao = EXTRACOES[subtipo.sigla]
        assert extracao.esquema is subtipo.esquema
        assert extracao.entidade is subtipo.entidade
        assert extracao.pasta == 'Portarias'
        assert f'/{subtipo.sigla}-' in extracao.instrucoes
        assert f'AAAA-NNNNNN/TEC/{subtipo.sigla}-NNNN' in extracao.instrucoes


@pytest.mark.parametrize('sigla', AUTUADO_DE_CADA_SIGLA)
def test_edital_vira_um_trecho_so_do_autuado_do_subtipo(sigla):
    trechos = EXTRACOES[sigla].separar_trechos(EDITAL_DE_TODOS)

    assert len(trechos) == 1
    assert trechos[0].startswith(AUTUADO_DE_CADA_SIGLA[sigla])
    assert f'/{sigla}-' in trechos[0]


def test_processo_so_citado_na_descricao_nao_vira_trecho_do_subtipo():
    # O AIEM-0024 só aparece na descrição da multa de BETO.
    trechos = EXTRACOES['AIEM'].separar_trechos(EDITAL_DE_TODOS)
    assert all('AIEM-0024' not in trecho for trecho in trechos)


def test_sem_numero_de_processo_o_subtipo_sai_da_penalidade():
    texto = (
        'Autuado: FULANO, CPF nº 012.219.575-20 nos autos do processo administrativo '
        'nº , em 01/01/2020, foi homologado o Auto de Infração de Demolição, "de muro."'
    )
    assert len(EXTRACOES['AIDM'].separar_trechos(texto)) == 1
    assert EXTRACOES['AIEM'].separar_trechos(texto) == []


def _trecho(sigla):
    return EXTRACOES[sigla].separar_trechos(EDITAL_DE_TODOS)[0]


def test_regex_le_a_modalidade_do_embargo_e_o_valor_da_multa():
    embargo = auto_infracao.campos_por_regex(auto_infracao.EMBARGO, _trecho('AIEM'))
    assert embargo['modalidade'] == 'definitivo'
    multa = auto_infracao.campos_por_regex(auto_infracao.MULTA, _trecho('AIMU'))
    assert multa['valor_multa'] == 30000.0
    assert 'modalidade' not in multa
    advertencia = auto_infracao.campos_por_regex(
        auto_infracao.ADVERTENCIA, _trecho('AIAD')
    )
    assert advertencia['tipo_documento'] == 'CPF'
    assert 'modalidade' not in advertencia


def test_regex_preenche_a_modalidade_vazia_do_embargo():
    resposta = ExtracaoEmbargo(
        auto=[
            _auto(
                AutoEmbargo,
                nro_processo='2009-032890/TEC/AIEM-0058',
                modalidade=None,
            )
        ]
    )
    preenchidos = EXTRACOES['AIEM'].preencher_vazios_pela_regex(
        _trecho('AIEM'), resposta
    )
    assert preenchidos == ['modalidade']
    assert resposta.auto[0].modalidade == 'definitivo'


def test_multa_nao_preenche_pela_regex_e_confere_o_valor():
    resposta = ExtracaoMulta(
        auto=[
            _auto(
                AutoMulta,
                nro_processo='2014-001430/TEC/AIMU-0094',
                valor_multa=3000,
                autuado=Pessoa(
                    nome='BETO',
                    tipo_documento='CPF',
                    nro_documento='222.222.222-22',
                    endereco=None,
                ),
                dt_homologacao='2020-06-25',
            )
        ]
    )
    extracao = EXTRACOES['AIMU']
    assert extracao.preencher_vazios_pela_regex(_trecho('AIMU'), resposta) == []
    conferencia = extracao.conferir(_trecho('AIMU'), resposta)
    assert conferencia['divergencias'] == {'valor_multa': [3000.0, 30000.0]}
    assert conferencia['faltantes'] == [] and conferencia['inesperados'] == []


@pytest.mark.parametrize('subtipo', auto_infracao.SUBTIPOS, ids=lambda s: s.sigla)
def test_todo_campo_do_subtipo_tem_coluna_ou_tabela_filha(subtipo):
    classe = subtipo.esquema.model_fields['auto'].annotation.__args__[0]
    mapeamento = inspect(subtipo.entidade)
    campos = set(classe.model_fields) - CAMPOS_ANINHADOS
    faltando = (
        campos - set(mapeamento.columns.keys()) - set(mapeamento.relationships.keys())
    )
    assert faltando == set()


def test_apreensao_grava_os_bens_na_tabela_filha():
    auto = para_auto(
        _auto(
            AutoApreensao,
            bem_apreendido=[
                _item(descricao='lenha', quantidade='14', unidade='st'),
                _item(descricao='motosserra', valor_avaliado='R$ 1.000,00'),
            ],
            fiel_depositario='o próprio autuado',
        ),
        entidades.AutoApreensao,
    )
    assert isinstance(auto, entidades.AutoApreensao)
    assert [bem.descricao for bem in auto.bem_apreendido] == ['lenha', 'motosserra']
    assert auto.bem_apreendido[0].quantidade == Decimal('14.0')
    assert auto.bem_apreendido[1].valor_avaliado == Decimal('1000.0')
    assert auto.fiel_depositario == 'o próprio autuado'


def test_multa_e_demolicao_viram_entidade():
    multa = para_auto(
        _auto(AutoMulta, valor_multa='R$ 50.000,00', tipo_multa='simples'),
        entidades.AutoMulta,
    )
    assert multa.valor_multa == Decimal('50000.0')
    assert multa.reincidente is False
    demolicao = para_auto(
        _auto(AutoDemolicao, obra_demolida=['casa']), entidades.AutoDemolicao
    )
    assert demolicao.obra_demolida == ['casa']
