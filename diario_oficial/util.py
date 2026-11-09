"""Codigos úteis ao sistema."""

from datetime import date, timedelta


def dias_do_periodo(inicio: date, fim: date, ultimo_dia: date) -> list[date]:
    """Lista os dias de `inicio` a `fim`, inclusive, sem passar de `ultimo_dia`.

    Returns:
        Os dias em ordem crescente; lista vazia se o período não tiver nenhum dia.
    """
    fim = min(fim, ultimo_dia)
    return [inicio + timedelta(days=i) for i in range((fim - inicio).days + 1)]


def check_word_in_list(word: str, list1: list):
    """Verifica se existe uma palavra numa lista

    Args:
        word (str): _description_
        list (list): _description_

    Returns:
        _type_: _description_
    """
    if word in list1:
        return True
    else:
        return False


def check_word_or_list_exist_in_list(word: str, list_word: list):
    """Verifica se existe qualquer palavra de uma frase em uma lista de palavras

    Args:
        frase (str): _description_
        list (list): _description_

    Returns:
        _type_:  boolean
    """
    list_from_word = word.split()
    for i in list_from_word:
        if check_word_in_list(i, list_word):
            return True
        else:
            return False
