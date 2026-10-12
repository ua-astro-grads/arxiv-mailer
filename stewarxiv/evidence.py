"""Step 2b: count UofA affiliation mentions in a posting's LaTeX source."""
import io
import logging
import re
import tarfile

import requests

log = logging.getLogger(__name__)

UOFA_RE = re.compile(r'(university of arizona|steward observatory|arizona\.edu|lbto\.org|gmto\.org)', flags=re.IGNORECASE)

# Where papers name their authors' institutions. Only these parts are
# searched, because acknowledgements often list UofA without any UofA author
# (e.g. SDSS's list of participating institutions).
# The front matter is everything before the abstract or \maketitle.
FRONT_MATTER_END_RE = re.compile(r'\\begin\s*\{abstract\}|\\abstract\b|\\maketitle\b')
# Author and affiliation commands of the common journal classes: AASTeX
# (\affiliation, \altaffiliation, \email), A&A (\institute), MNRAS (\author),
# authblk (\affil) and elsarticle (\address). These are searched anywhere in
# a file, since affiliations can come after the abstract or be in a separate
# file pulled in with \input.
AFFILIATION_CMD_RE = re.compile(
    r'\\(?:author|affiliation|altaffiliation|affil|institute|address|email)\*?'
    r'\s*(?:\[[^\]]*\])?\s*\{')

def braced_argument(text, start):
    """Return a LaTeX command's braced argument, including nested braces.

    Walks forward from just after the opening brace, counting unescaped
    braces until the matching closing brace.

    Args:
        text: LaTeX text.
        start: Index just after the opening '{'.

    Returns:
        str: The text up to the matching '}', or to the end of text if the
        brace is never closed.
    """
    depth = 1
    i = start
    while i < len(text):
        char = text[i]
        if char == '\\':
            i += 2  # skip escaped characters such as \{ and \}
            continue
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return text[start:i]
        i += 1
    return text[start:]

def evidence_in_texfile(fh):
    """Count mentions of UofA affiliations in the author block of one LaTeX file.

    Decodes the file, skips lines starting with '%' (LaTeX comments), and
    counts UOFA_RE matches ('University of Arizona', 'Steward Observatory',
    'arizona.edu', 'lbto.org', 'gmto.org') in two places: the front matter
    before the first \\begin{abstract}, \\abstract or \\maketitle, and the
    arguments of author and affiliation commands (AFFILIATION_CMD_RE) after
    it. A file with no abstract or \\maketitle, such as one pulled in with
    \\input, is searched only in those commands. Mentions elsewhere, such as
    the acknowledgements, aren't counted.

    Args:
        fh: Binary file object of a .tex file, decoded as UTF-8.

    Returns:
        int: Number of matches.

    Raises:
        UnicodeDecodeError: If the file isn't valid UTF-8.
    """
    lines = fh.read().decode('utf8').splitlines(keepends=True)
    text = ''.join(line for line in lines if not line.startswith('%'))
    end = FRONT_MATTER_END_RE.search(text)
    front_end = end.start() if end else 0
    evidence = len(UOFA_RE.findall(text[:front_end]))
    for command in AFFILIATION_CMD_RE.finditer(text, front_end):
        evidence += len(UOFA_RE.findall(braced_argument(text, command.end())))
    return evidence


def gather_affiliation_evidence(arxiv_id):
    """Count UofA affiliation mentions in a posting's LaTeX source.

    Downloads the source from https://arxiv.org/e-print/<arxiv_id>, opens it
    as a tar archive and runs evidence_in_texfile on every .tex file in it,
    so only the author and affiliation parts of the source are counted.
    Any failure (download error, a source that isn't a tar archive such as a
    PDF-only submission, undecodable text) is logged at debug level and
    reported as success=False instead of raised.

    Args:
        arxiv_id: arXiv identifier, e.g. '2610.00462'.

    Returns:
        tuple[int, bool]: (evidence, success). evidence is the total number
        of matches; success is False if the source couldn't be downloaded or
        read.
    """
    url = f'https://arxiv.org/e-print/{arxiv_id}'
    evidence = 0
    gather_success = False
    try:
        log.debug(f"Gathering evidence from {url}")
        res = requests.get(url)
        buff = io.BytesIO(res.content)
        archive = tarfile.open(fileobj=buff)
        texfiles = [m for m in archive.getmembers() if m.name.lower().endswith('.tex')]
        for info in texfiles:
            fh = archive.extractfile(info)
            evidence += evidence_in_texfile(fh)
        gather_success = True
        log.info(f'Found {evidence=} for {arxiv_id=}')
    except Exception as e:
        log.debug(e)
    return evidence, gather_success
