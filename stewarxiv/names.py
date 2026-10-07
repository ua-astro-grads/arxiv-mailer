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
    """Normalize a name so names can be compared with ==.

    Replaces every non-word character (such as '.', '-' or '{') with a space,
    casefolds (lowercases), applies Unicode NFKD normalization, and strips
    leading/trailing whitespace. Inner spaces are kept, so 'A. Bob' becomes
    'a  bob'.

    Args:
        text: A name or part of a name.

    Returns:
        str: The normalized text.
    """
    text = re.sub(r'[^\w]', ' ', text)
    # thanks to https://stackoverflow.com/a/29247821
    text = unicodedata.normalize("NFKD", text.casefold())
    text = text.strip()
    return text

NAME_RE = re.compile(r'^(?P<first>(?:(?P<initial>\w).*)[\. ]+)+(?P<last>\w.*)$')
INITIAL_RE = re.compile(r'^\w(\.|\s|$)')

ALL_INITIALS_RE = re.compile(r'\b\w\.?\s')
def strip_initials(names):
    """Remove single-letter initials from a name.

    Deletes every single letter at the start of a word that is followed by
    an optional period and a space (ALL_INITIALS_RE), then collapses repeated
    spaces. An initial at the very end has no space after it and is kept:
    'a bob c' becomes 'bob c'.

    Args:
        names: One or more names, e.g. 'J. D. Long'.

    Returns:
        str: The names without initials, e.g. 'Long'.
    """
    return ' '.join(ALL_INITIALS_RE.sub('', names).split())

def approximate_name_lookup(name, people):
    """Find the directory entry that matches an arXiv author name.

    Normalizes the name and splits it into first name(s) and surname, then
    looks for a directory entry with that surname whose first names match
    (see _match_first_names for the rules and scores). The split is tried
    three ways, stopping at the first match:

    1. The last word is the surname (NAME_RE), e.g. 'J. D. Long'.
    2. The last 2, 3, ... words are the surname, for multi-word surnames
       such as 'Kyle Van Gorkom' or "Dillon O'Reilly" ('o reilly').
    3. The directory surname is only the first part of a multi-word or
       hyphenated arXiv surname, e.g. directory 'faramaz' for 'Virginie
       Faramaz-Gorka'. This is less certain, so the score is at most 1 and
       the posting still has to pass the affiliation check.

    Args:
        name: Author name as written on arXiv, e.g. 'J. D. Long'.
        people: Directory keyed by (last_name, first_names); only the keys
            are used.

    Returns:
        tuple: (key, score). key is the matched (last_name, first_names), or
        None; score is 2, 1, or 0 for no match (also returned, with a
        warning, if the name can't be parsed).
    """
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

    # 1. the usual split: the last word is the surname
    key, score = _match_first_names(first_names, first_initial, last_name, people)
    if score:
        return key, score

    # 2. multi-word surnames: try the last 2, 3, ... words as the surname
    words = normalized_name.split()
    for n in range(2, len(words)):
        key, score = _match_first_names(' '.join(words[:-n]), first_initial,
                                        ' '.join(words[-n:]), people)
        if score:
            return key, score

    # 3. the directory has only the first part of a multi-word surname,
    #    e.g. 'faramaz' for 'faramaz gorka'; less certain, so score at most 1
    for n in range(2, len(words)):
        surname = words[-n:]
        for k in range(1, n):
            key, score = _match_first_names(' '.join(words[:-n]), first_initial,
                                            ' '.join(surname[:k]), people)
            if score:
                return key, 1
    return None, 0

def _match_first_names(first_names, first_initial, last_name, people):
    """Find the first directory entry with this surname whose first names match.

    Goes through the directory in order, and for entries whose surname
    equals last_name, compares first names:

    - score 2: the arXiv first name(s) equal or start with the directory's
      first names, or match them as whole words once initials are removed
      from either one (e.g. 'J. Edgar' matches 'edgar', and 'Marcia'
      matches 'marcia j')
    - score 1: the arXiv first name is just an initial (e.g. 'G.') matching
      the first letter of the directory's first name

    Runs of spaces are collapsed on both sides first, since punctuation
    (e.g. the periods in 'J. Roger P.') leaves double spaces when names are
    normalized.

    Args:
        first_names: Normalized arXiv first name(s), e.g. 'marcia'.
        first_initial: First letter of first_names.
        last_name: Normalized arXiv surname, e.g. 'van gorkom'.
        people: Directory keyed by (last_name, first_names).

    Returns:
        tuple: (key, score) for the first match, or (None, 0).
    """
    first_names = ' '.join(first_names.split())
    for key in people:
        person_last, person_first = (' '.join(part.split()) for part in key)
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
                # does person_first match after removing initials? e.g. arXiv
                # 'marcia' vs directory 'marcia j'. Compare whole words, so
                # 'al' doesn't match 'alice'.
                if (strip_initials(person_first) + ' ').startswith(first_names + ' '):
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
            return key, score
    return None, 0
