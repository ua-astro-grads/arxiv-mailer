"""Step 2b: count UofA affiliation mentions in a posting's LaTeX source."""
import io
import logging
import re
import tarfile

import requests

log = logging.getLogger(__name__)

def gather_affiliation_evidence(arxiv_id):
    url = f'https://arxiv.org/e-print/{arxiv_id}'
    evidence = 0
    try:
        res = requests.get(url)
        buff = io.BytesIO(res.content)
        archive = tarfile.open(fileobj=buff)
        texfiles = [m for m in archive.getmembers() if m.name.lower().endswith('.tex')]

        UOFA_RE = re.compile(r'(university of arizona|steward observatory|arizona\.edu|lbto\.org|gmto\.org)', flags=re.IGNORECASE)

        for info in texfiles:
            fh = archive.extractfile(info)
            contents = fh.read().decode('utf8')
            matches = UOFA_RE.findall(contents)
            evidence += len(matches)
    except Exception as e:
        log.debug(e)
    return evidence

UOFA_RE = re.compile(r'(university of arizona|steward observatory|arizona\.edu|lbto\.org|gmto\.org)', flags=re.IGNORECASE)

def evidence_in_texfile(fh):
    evidence = 0
    for line in fh:
        line = line.decode('utf8')
        if line[0] == '%':
            continue
        matches = UOFA_RE.findall(line)
        evidence += len(matches)
    return evidence


def gather_affiliation_evidence(arxiv_id):
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
