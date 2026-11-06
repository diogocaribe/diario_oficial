"""Textos no formato real do DOE e helpers dos testes de separação e auditoria."""

from datetime import date

from diario_oficial.auditoria import Ato, Edicao, Publicacao, auditar_edicao

RESOLVE = (
    'O INSTITUTO DO MEIO AMBIENTE E RECURSOS HÍDRICOS - INEMA, no uso de suas '
    'atribuições, RESOLVE: Art. 1º - Autorizar o direito de uso dos recursos hídricos.'
)

# Formas reais de assinar um ato. O signatário muda com o tempo e o ato não diz qual é
TOPAZIO = 'EDUARDO FARIAS\r\nTOPÁZIO -\r\nDiretor Geral'
MARCIA = 'MÁRCIA CRISTINA TELLES DE ARAÚJO LIMA - Diretora Geral'
DANILO = 'DANILO LEITE MESQUITA - Diretor Geral em Exercício'
SIGNATARIOS = [
    TOPAZIO,
    MARCIA,
    DANILO,
    'MÁRCIA CRISTINA TELLES DE ARAÚJO LIMA Diretora Geral do INEMA',
    'MARCIA CRISTINA TELLES DE ARAUJO LIMA INST DO MEIO AMB E RECURSOS HÍDRICOS',
    'MARIA AMÉLIA DE CONI E MOURA MATTOS LINS - Diretora Geral',
    'DANIELLA TEIXEIRA FERNANDES DE ARAÚJO - Diretora Geral em\r\nExercício',
    'DANILO LEITE MESQUITA Diretor Geral em Exercício',
    'EDUARDO MENDONÇA SODRÉ MARTINS Presidente',
    'EDUARDO MENDONÇA SODRÉ MARTINS SECRETARIA DO MEIO AMBIENTE',
]

# Caso real: o preâmbulo vem no início da publicação e entre as portarias
PREAMBULO_RESOLVE = (
    'A\r\nDIRETORA GERAL DO INSTITUTO DO MEIO AMBIENTE E RECURSOS HÍDRICOS - INEMA, no '
    'uso de suas atribuições, RESOLVE:\n'
)


def ato(titulo, assinatura):
    return f'{titulo} {RESOLVE} {assinatura}'


def publicacao(textos, nome='#1 - 2026.10.06', conteudo=None, processada=True):
    atos = [Ato(i, texto) for i, texto in enumerate(textos, start=1)]
    return Publicacao(
        1, nome, '\n\n'.join(textos) if conteudo is None else conteudo, processada, atos
    )


def regras(*publicacoes, existe=True, transformada=True):
    edicao = Edicao(date(2026, 10, 6), existe, transformada, list(publicacoes))
    return [achado.regra for achado in auditar_edicao(edicao).achados]
