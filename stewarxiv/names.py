"""Step 2a: match arXiv author names against the directory."""
import logging
import re
import unicodedata
from typing import NamedTuple

log = logging.getLogger(__name__)

class Author(NamedTuple):
    """One author of an arXiv posting, and who they matched in the directory."""
    name: str                        # as written on arXiv, e.g. 'Edgar Ferris'
    key: tuple[str, ...] | None      # directory key, e.g. ('ferris', 'edgar'), or None if no match
    score: int                       # 0 no match, 1 first initial + last name, 2 full name

def normalize_caseless(text):
    text = re.sub(r'[^\w]', ' ', text)
    # thanks to https://stackoverflow.com/a/29247821
    text = unicodedata.normalize("NFKD", text.casefold())
    text = text.strip()
    return text

NAME_RE = re.compile(r'^(?P<first>(?:(?P<initial>\w).*)[\. ]+)+(?P<last>\w.*)$')
INITIAL_RE = re.compile(r'^\w(\.|\s|$)')

ALL_INITIALS_RE = re.compile(r'\b\w\.?\s')
def strip_initials(names):
    return ' '.join(ALL_INITIALS_RE.sub('', names).split())

def approximate_name_lookup(name, people):
    # normalize at input boundary so comparisons are simply ==
    normalized_name = normalize_caseless(name)
    name_match = NAME_RE.match(normalized_name)
    if not name_match:
        log.warning(f"Unable to parse {normalized_name=} with regex")
        return None, 0
    parts = name_match.groupdict()
    first_names = parts['first'].strip()
    first_initial = parts['initial']
    last_name = parts['last'].strip()

    for person_last, person_first in people:
        score = 0
        if person_last == last_name:
            # last name matches, but what about first?
            if person_first == first_names:
                # easy: last name matches, first name(s) match
                score = 2
            elif first_names.startswith(person_first):
                score = 2
            elif first_names != first_initial and first_names in person_first:
                # first_names is a substring of person_first
                # does person_first match after removing initials?
                if strip_initials(first_names).startswith(person_first):
                    score = 2
            elif person_first in first_names:
                # does first_names match after removing initials?
                if strip_initials(first_names).startswith(person_first):
                    score = 2
            elif person_first[0] == first_initial[0]:
                # harder: last name matches, first initial matches
                # check if it's an initial (single letter followed by space, period, or end of string
                re_match = INITIAL_RE.match(first_names)
                if re_match:
                    score = 1
                # otherwise, same first initial, different first name, so no match
            # else: same last name, different first name, no match
        if score:
            return (person_last, person_first), score
    return None, 0
