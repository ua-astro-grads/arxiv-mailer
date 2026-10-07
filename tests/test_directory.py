from stewarxiv.directory import drop_nicknames
from stewarxiv.names import normalize_caseless


def normalized(text):
    return normalize_caseless(drop_nicknames(text).strip())

def test_drop_nicknames():
    # issue #17: nicknames as written on astro.arizona.edu are ignored
    assert normalized('Robert S. (Bob)') == 'robert s'
    assert normalized('Hubert (Buddy)') == 'hubert'
    assert normalized('Chi-Kwan "CK"') == 'chi kwan'
    assert normalized('(Laurence) Gong') == 'gong'
    # apostrophes are part of the name
    assert normalized("O'Reilly") == 'o reilly'
    assert normalized("D'Souza") == 'd souza'
