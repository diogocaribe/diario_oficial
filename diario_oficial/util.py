import collections


def deep_update(source, overrides):
    """
    Update a nested dictionary or similar mapping.
    Modify ``source`` in place.

        source = {'hello1': 1}
        overrides = {'hello2': 2}
        deep_update(source, overrides)
        assert source == {'hello1': 1, 'hello2': 2}

        source = {'hello': 'to_override'}
        overrides = {'hello': 'over'}
        deep_update(source, overrides)
        assert source == {'hello': 'over'}

        source = {'hello': {'value': 'to_override', 'no_change': 1}}
        overrides = {'hello': {'value': 'over'}}
        deep_update(source, overrides)
        assert source == {'hello': {'value': 'over', 'no_change': 1}}

        source = {'hello': {'value': 'to_override', 'no_change': 1}}
        overrides = {'hello': {'value': {}}}
        deep_update(source, overrides)
        assert source == {'hello': {'value': {}, 'no_change': 1}}

        source = {'hello': {'value': {}, 'no_change': 1}}
        overrides = {'hello': {'value': 2}}
        deep_update(source, overrides)
        assert source == {'hello': {'value': 2, 'no_change': 1}}
    """
    for key, value in overrides.iteritems():
        if isinstance(value, collections.Mapping) and value:
            returned = deep_update(source.get(key, {}), value)
            source[key] = returned
        else:
            source[key] = overrides[key]
    return source


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