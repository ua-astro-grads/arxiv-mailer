import io

from stewarxiv.evidence import evidence_in_texfile


def evidence(tex):
    return evidence_in_texfile(io.BytesIO(tex.encode('utf8')))

# the SDSS acknowledgement that let 2610.13742 (J. Li, Copenhagen) through
SDSS_ACK = r"""
\begin{acknowledgements}
SDSS is managed by the Astrophysical Research Consortium for the Participating
Institutions of the SDSS Collaboration including ... University of Arizona,
University of Colorado Boulder, University of Oxford ...
\end{acknowledgements}
"""

def test_acknowledgements_not_counted():
    # A&A: affiliations in \institute, none at UofA
    tex = r"""\documentclass{aa}
\begin{document}
\title{A strategy for astrometric quasar selection}
\author{J. Li \inst{1,2}\email{djw465@alumni.ku.dk}
\and J. P. U. Fynbo \inst{1,2}}
\institute{Cosmic Dawn Center (DAWN), Denmark
\and Niels Bohr Institute, University of Copenhagen, Denmark}
\abstract{We aim to provide a cookbook.}
\maketitle
\section{Introduction}
""" + SDSS_ACK
    assert evidence(tex) == 0

def test_aastex_affiliation():
    tex = r"""\documentclass[twocolumn]{aastex631}
\begin{document}
\title{A dust-reddened quasar}
\author[0000-0003-3310-0131]{Xiaohui Fan}
\affiliation{Steward Observatory, University of Arizona, 933 North Cherry Avenue, Tucson, AZ 85721, USA}
\email{fan@arizona.edu}
\begin{abstract}
We report a quasar.
\end{abstract}
""" + SDSS_ACK
    # 'Steward Observatory', 'University of Arizona' and 'arizona.edu'
    assert evidence(tex) == 3

def test_aa_institute():
    tex = r"""\author{J. Li\inst{1} \and A. Person\inst{2}}
\institute{Niels Bohr Institute, Denmark
\and Steward Observatory, The University of Arizona, Tucson, AZ, USA}
\abstract{...}
"""
    assert evidence(tex) == 2

def test_mnras_author_with_newlines():
    tex = r"""\author[D. J. Sand et al.]{
David J. Sand,$^{1}$\thanks{E-mail: dsand@arizona.edu}
Dennis Zaritsky$^{1}$
\\
$^{1}$Steward Observatory, University of Arizona, 933 North Cherry Avenue, Tucson, AZ 85721-0065, USA\\
}
\begin{document}
\maketitle
\begin{abstract}
...
\end{abstract}
"""
    assert evidence(tex) == 3

def test_affiliation_after_abstract():
    # revtex and elsarticle papers sometimes give affiliations after the abstract
    tex = r"""\title{Title}
\begin{abstract}
Our abstract mentions nothing.
\end{abstract}
\author{A. Person}
\affiliation{Department of Astronomy and Steward Observatory, University of Arizona}
\maketitle
\section{Data}
""" + SDSS_ACK
    assert evidence(tex) == 2

def test_nested_braces_in_affiliation():
    tex = r"""\begin{abstract}x\end{abstract}
\affiliation{{\it Steward Observatory}, University of Arizona, \{Tucson\}, {AZ}, USA}
Text after the affiliation: University of Arizona.
"""
    assert evidence(tex) == 2

def test_input_file_with_only_authors():
    # an authors.tex pulled in with \input: no abstract, so only commands count
    tex = r"""\author{Jianwei Lyu}
\affiliation{Steward Observatory, University of Arizona, Tucson, AZ 85721, USA}
"""
    assert evidence(tex) == 2

def test_section_file_not_counted():
    # a section file with no abstract and no author commands
    tex = r"""\section{Observations}
We used the Large Binocular Telescope (lbto.org) and the MMT, a joint
facility of the Smithsonian Institution and the University of Arizona.
"""
    assert evidence(tex) == 0

def test_commented_lines_skipped():
    tex = r"""\author{A. Person}
%\affiliation{Steward Observatory, University of Arizona}
\affiliation{Other University}
\begin{abstract}x\end{abstract}
"""
    assert evidence(tex) == 0

def test_command_names_are_whole_words():
    # \authorrunning and \affiliations are not author commands
    tex = r"""\begin{abstract}x\end{abstract}
\authorrunning{Person et al., University of Arizona}
\affiliations{University of Arizona}
"""
    assert evidence(tex) == 0
