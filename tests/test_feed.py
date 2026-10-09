from stewarxiv.feed import latex_to_unicode


def test_latex_to_unicode():
    # issue #18: real author names from the astro-ph RSS feed
    assert latex_to_unicode("Sebasti\\'an P\\'erez") == 'Sebastián Pérez'
    assert latex_to_unicode("Jos\\'e Carlos Olvera M.") == 'José Carlos Olvera M.'
    assert latex_to_unicode("Elena Gonz\\'{a}lez Prieto") == 'Elena González Prieto'
    assert latex_to_unicode("Claude-Andr\\'e Faucher-Gigu\\`ere") == 'Claude-André Faucher-Giguère'
    assert latex_to_unicode('Jorge Pe\\~narrubia') == 'Jorge Peñarrubia'
    assert latex_to_unicode('Nuutti Hyv\\"onen') == 'Nuutti Hyvönen'
    assert latex_to_unicode('Emile Pr\\^ele') == 'Emile Prêle'
    assert latex_to_unicode("Du\\v{s}an Vukadinovi\\'c") == 'Dušan Vukadinović'
    assert latex_to_unicode("Zs. K\\H{o}v\\'ari") == 'Zs. Kővári'
    assert latex_to_unicode('Do\\u{g}a Tolgay') == 'Doğa Tolgay'
    assert latex_to_unicode('Deniz Cennet \\c{C}{\\i}nar') == 'Deniz Cennet Çınar'
    assert latex_to_unicode("Borja P\\'{e}rez-D\\'{i}az") == 'Borja Pérez-Díaz'
    assert latex_to_unicode("Rodr\\'{\\i}guez") == 'Rodríguez'
    assert latex_to_unicode('Micha{\\l} K. Szyma\\\'nski') == 'Michał K. Szymański'
    assert latex_to_unicode('Bj\\o rn') == 'Bjørn'
    assert latex_to_unicode("\\'Alvaro S\\'anchez-Monge") == 'Álvaro Sánchez-Monge'
    # names without LaTeX, and notes after names, are unchanged
    assert latex_to_unicode('Edgar Ferris (DES Collaboration)') == 'Edgar Ferris (DES Collaboration)'
    assert latex_to_unicode('Sebastián Pérez') == 'Sebastián Pérez'

def test_latex_to_unicode_leaves_other_commands():
    # \c only takes a letter in braces or after a space, so \cdot is kept
    assert latex_to_unicode('a \\cdot b') == 'a \\cdot b'
    assert latex_to_unicode('\\ldots') == '\\ldots'
