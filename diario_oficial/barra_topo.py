"""Barra de progresso fixa na primeira linha do terminal.

A linha 1 fica fora da região de rolagem (DECSTBM): o texto rola da linha 2 para baixo e
nunca passa por cima da barra. A barra só é reescrita quando muda e sem ser apagada antes,
o que evita o piscar do redesenho contínuo.

O que sai de uma região que não começa na linha 1 não vai para o histórico do terminal.
Por isso o texto é guardado e reimpresso ao final, já sem a região de rolagem.
"""

from rich.progress import Progress
from rich.text import Text

SALVAR_CURSOR = '\x1b7'
RESTAURAR_CURSOR = '\x1b8'
ESCONDER_CURSOR = '\x1b[?25l'
MOSTRAR_CURSOR = '\x1b[?25h'
LIMPAR_FIM_DA_LINHA = '\x1b[K'
LIMPAR_TELA = '\x1b[2J\x1b[H'
SEM_REGIAO_DE_ROLAGEM = '\x1b[r'


class BarraFixaNoTopo:
    """Exibe um `Progress` já com tarefas, sem iniciá-lo (não usa o Live do rich).

    Sem terminal (saída redirecionada) não há barra e o texto é impresso direto.
    """

    def __init__(self, progresso: Progress):
        self.progresso = progresso
        self.console = progresso.console
        self.ativa = self.console.is_terminal and not self.console.is_dumb_terminal
        self._historico: list[Text] = []
        self._tamanho = None
        self._linha = None

    def __enter__(self):
        if self.ativa:
            altura = self.console.size.height
            # As quebras empurram a tela atual para o histórico; só depois a região existe
            self._escrever(
                '\n' * (altura - 1)
                + f'\x1b[2;{altura}r\x1b[2;1H'
                + ESCONDER_CURSOR
            )
            self._tamanho = self.console.size
            self.atualizar()
        return self

    def __exit__(self, *_):
        if not self.ativa:
            return
        self._escrever(SEM_REGIAO_DE_ROLAGEM + MOSTRAR_CURSOR + LIMPAR_TELA)
        for texto in self._historico:
            self.console.print(texto, soft_wrap=True)
        self.console.print(self.progresso.get_renderable())

    def imprimir(self, texto: Text):
        """Imprime abaixo da barra. `Text` já pronto, sem marcação nem realce."""
        if self.ativa:
            self._historico.append(texto)
        self.console.print(texto, soft_wrap=True)

    def atualizar(self):
        """Reescreve a barra se ela ou o tamanho do terminal mudaram."""
        if not self.ativa:
            return
        tamanho = self.console.size
        if tamanho != self._tamanho:
            self._tamanho = tamanho
            self._linha = None  # o terminal pode ter refeito a primeira linha
            self._escrever(
                f'{SALVAR_CURSOR}\x1b[2;{tamanho.height}r{RESTAURAR_CURSOR}'
            )

        linha = self._renderizar(tamanho.width)
        if linha != self._linha:
            self._linha = linha
            self._escrever(
                f'{SALVAR_CURSOR}\x1b[1;1H{linha}'
                f'{LIMPAR_FIM_DA_LINHA}{RESTAURAR_CURSOR}'
            )

    def _renderizar(self, largura: int) -> str:
        # Uma coluna de folga: na última, o limpar até o fim apagaria o último caractere
        with self.console.capture() as captura:
            self.console.print(
                self.progresso.get_renderable(),
                width=largura - 1,
                no_wrap=True,
                overflow='crop',
            )
        return captura.get().split('\n')[0]

    def _escrever(self, sequencia: str):
        self.console.file.write(sequencia)
        self.console.file.flush()
