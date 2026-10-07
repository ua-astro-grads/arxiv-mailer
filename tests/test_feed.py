from stewarxiv.feed import split_author_names


def test_split_author_names_plain():
    assert split_author_names('D. Tsiklauri') == ['D. Tsiklauri']
    assert split_author_names('Jane Doe, John Smith') == ['Jane Doe', 'John Smith']

def test_split_author_names_with_affiliation():
    # issue #27: an affiliation with no comma of its own used to stay
    # attached to the name, e.g. 'W. Cerny (DELVE Collaboration)', which
    # then failed to match the person by name.
    assert split_author_names('W. Cerny (DELVE Collaboration), M. Geha (DELVE Collaboration)') == \
        ['W. Cerny', 'M. Geha']

def test_split_author_names_with_comma_in_affiliation():
    # issue #27: a comma inside the affiliation used to split one author
    # into two bogus names, e.g. 'Jane Doe (Some Institute' and
    # 'Some City)'.
    assert split_author_names(
        'Lucy Taylor (School of Physics, University of Bristol), '
        'Simon J. Lock (School of Earth Sciences, University of Bristol)'
    ) == ['Lucy Taylor', 'Simon J. Lock']
    assert split_author_names('Muhammad Akashi (Technion, Israel), Noam Soker (Technion, Israel)') == \
        ['Muhammad Akashi', 'Noam Soker']

def test_split_author_names_extra_whitespace():
    # real feed data has occasionally had doubled spaces between names
    assert split_author_names('Pawan Kumar,  Sadashiv') == ['Pawan Kumar', 'Sadashiv']
