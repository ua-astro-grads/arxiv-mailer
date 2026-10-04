from stewarxiv.names import NAME_RE, INITIAL_RE, strip_initials, approximate_name_lookup


def test_name_regex():
    assert NAME_RE.match('J.Long').groupdict() == {'first': 'J.', 'initial': 'J', 'last': 'Long'}
    assert NAME_RE.match('Joseph D. Long').groupdict() == {'first': 'Joseph D. ', 'initial': 'J', 'last': 'Long'}
    assert NAME_RE.match('J. D. Long').groupdict() == {'first': 'J. D. ', 'initial': 'J', 'last': 'Long'}
    assert NAME_RE.match('J Long').groupdict() == {'first': 'J ', 'initial': 'J', 'last': 'Long'}
def test_initial_regex():
    assert INITIAL_RE.match('J. D.')
    assert not INITIAL_RE.match('Jo. D.')
    assert INITIAL_RE.match('J.D.')
    assert INITIAL_RE.match('J')
    assert INITIAL_RE.match('J D')

def test_strip_initials():
    assert strip_initials('J. Long') == 'Long'

def test_approximate_name_lookup():
    people = {
        ('dave', 'a. bob c.'): None,
        ('ferris', 'edgar'): None,
        ('hausschuh', 'georgina'): None,
        ('rodrigo', 'marco navarro'): None
    }
    assert approximate_name_lookup('edgar ferris', people) == (('ferris', 'edgar'), 2)
    assert approximate_name_lookup('bob dave', people) == (('dave', 'a. bob c.'), 2)
    assert approximate_name_lookup('G. Hausschuh', people) == (('hausschuh', 'georgina'), 1)
    assert approximate_name_lookup('{M. Navarro Rodrigo}', people) == (('rodrigo', 'marco navarro'), 1)

def test_approximate_name_lookup_directory_initials():
    # issue #17: directory has a middle initial the arXiv name leaves out
    people = {
        ('rieke', 'marcia j'): None,
        ('long', 'joseph d'): None,
        ('smith', 'alice'): None,
    }
    assert approximate_name_lookup('Marcia Rieke', people) == (('rieke', 'marcia j'), 2)
    assert approximate_name_lookup('Joseph Long', people) == (('long', 'joseph d'), 2)
    # whole words only: 'Al' is not 'Alice'
    assert approximate_name_lookup('Al Smith', people) == (None, 0)
