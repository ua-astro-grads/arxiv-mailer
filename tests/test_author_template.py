"""Regression tests for author-list spacing in the HTML mailing."""

import os

import jinja2

from stewarxiv.names import Author


TEMPLATES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates"
)


def _render(authors):
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(TEMPLATES),
        autoescape=jinja2.select_autoescape(["html", "xml"]),
    )
    return env.get_template("mailing.jinja2.html").render(
        day_of_week="Thursday",
        run_time="2026-10-08 09:00 UTC",
        all_authors=[],
        people={
            ("observatory", "s"): {
                "thumb_cid": None,
                "image": "https://example.test/s.jpg",
                "page": "https://example.test/s",
            }
        },
        posts=[
            {
                "area": "astro-ph.GA",
                "arxiv_id": "2601.00001",
                "html_arxiv_id": "2601.00001",
                "title": "A paper",
                "abstract": "Abstract.",
                "authors": authors,
            }
        ],
    )


def test_unmatched_authors_have_no_space_before_comma():
    """Issue #27: unmatched authors were rendered with a space before the comma.

    The author include replaces spaces with nbsp, then the mailing template
    appends a comma. A trailing newline from the unmatched branch was collapsed
    by HTML into a space, producing 'Harvard CFA ,' while matched authors were
    already trimmed.
    """
    html = _render(
        [
            Author("S. Observatory", ("observatory", "s"), 2),
            Author("Harvard CFA", None, 0),
            Author("IFA", None, 0),
        ]
    )
    assert "Harvard&nbsp;CFA," in html
    assert "Harvard&nbsp;CFA ," not in html
    assert "Harvard CFA ," not in html
    assert "IFA ," not in html
    assert "S.&nbsp;Observatory</a>" in html


def test_long_author_list_keeps_comma_against_unmatched_name():
    authors = [Author(f"Author {i}", None, 0) for i in range(21)]
    authors[0] = Author("S. Observatory", ("observatory", "s"), 2)
    html = _render(authors)
    assert "Author&nbsp;1," in html
    assert "Author&nbsp;1 ," not in html
