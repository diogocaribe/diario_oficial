from io import StringIO

import pytest
from rich.console import Console
from rich.progress import Progress, TextColumn
from rich.text import Text

from diario_oficial.barra_topo import BarraFixaNoTopo

DESENHO_DA_BARRA = '\x1b[1;1H'


def _barra(terminal=True):
    saida = StringIO()
    console = Console(
        file=saida, force_terminal=terminal, width=80, height=24, color_system=None
    )
    progresso = Progress(TextColumn('{task.fields[resumo]}'), console=console)
    tarefa = progresso.add_task('t', total=4, resumo='0/2 datas')
    return BarraFixaNoTopo(progresso), progresso, tarefa, saida


def test_reserva_a_primeira_linha_e_desenha_a_barra():
    barra, _, _, saida = _barra()
    with barra:
        conteudo = saida.getvalue()
        assert '\x1b[2;24r\x1b[2;1H' in conteudo
        assert f'{DESENHO_DA_BARRA}0/2 datas' in conteudo


def test_nao_redesenha_quando_nada_mudou():
    barra, _, _, saida = _barra()
    with barra:
        barra.atualizar()
        barra.atualizar()
        assert saida.getvalue().count(DESENHO_DA_BARRA) == 1


def test_redesenha_quando_o_resumo_muda():
    barra, progresso, tarefa, saida = _barra()
    with barra:
        progresso.update(tarefa, resumo='1/2 datas')
        barra.atualizar()
        assert f'{DESENHO_DA_BARRA}1/2 datas' in saida.getvalue()


def test_refaz_a_regiao_quando_o_terminal_muda_de_tamanho():
    barra, _, _, saida = _barra()
    with barra:
        barra.console.size = (100, 30)
        barra.atualizar()
        conteudo = saida.getvalue()
        assert '\x1b[2;30r' in conteudo
        assert conteudo.count(DESENHO_DA_BARRA) == 2


def test_restaura_o_terminal_e_reimprime_o_texto_mesmo_com_erro():
    barra, _, _, saida = _barra()
    with pytest.raises(ValueError):
        with barra:
            barra.imprimir(Text('linha do log'))
            raise ValueError
    conteudo = saida.getvalue()
    final = conteudo[conteudo.index('\x1b[r'):]
    assert '\x1b[?25h' in final
    assert 'linha do log' in final
    assert '0/2 datas' in final


def test_sem_terminal_so_imprime_o_texto():
    barra, _, _, saida = _barra(terminal=False)
    with barra:
        barra.imprimir(Text('linha do log'))
        barra.atualizar()
    assert saida.getvalue() == 'linha do log\n'
