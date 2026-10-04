"""Step 2b: count UofA affiliation mentions in a posting's LaTeX source."""
import io
import logging
import re
import tarfile

import requests

log = logging.getLogger(__name__)

UOFA_RE = re.compile(r'(university of arizona|steward observatory|arizona\.edu|lbto\.org|gmto\.org)', flags=re.IGNORECASE)

def evidence_in_texfile(fh):
    """Count mentions of UofA affiliations in one LaTeX file.

    Reads the file line by line, skips lines starting with '%' (LaTeX
    comments), and counts every UOFA_RE match ('University of Arizona',
    'Steward Observatory', 'arizona.edu', 'lbto.org', 'gmto.org').

    Args:
        fh: Binary file object of a .tex file; lines are decoded as UTF-8.

    Returns:
        int: Number of matches.

    Raises:
        UnicodeDecodeError: If a line isn't valid UTF-8.
    """
    evidence = 0
    for line in fh:
        line = line.decode('utf8')
        if line[0] == '%':
            continue
        matches = UOFA_RE.findall(line)
        evidence += len(matches)
    return evidence


def gather_affiliation_evidence(arxiv_id):
    """Count UofA affiliation mentions in a posting's LaTeX source.

    Downloads the source from https://arxiv.org/e-print/<arxiv_id>, opens it
    as a tar archive and runs evidence_in_texfile on every .tex file in it.
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
