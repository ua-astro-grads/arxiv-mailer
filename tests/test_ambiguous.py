import io
import types
from unittest import mock

import pytest

from stewarxiv import feed
from stewarxiv.evidence import AMBIGUOUS_RE, UOFA_RE, evidence_in_texfile

PEOPLE = {('Smith', 'Jane'): {'name': 'Jane Smith'}}


def tex(text):
    return io.BytesIO(text.encode())


@pytest.mark.parametrize('line', [
    'Steward Observatory, University of Arizona, Tucson',
    'Department of Astronomy, University of Arizona',
    'Steward~Observatory, The University~of~Arizona',
    r'Steward Observatory \\ University of Arizona',
    'steward observatory, university of arizona',
    r'\affiliation{University of Arizona, Steward Observatory, 933 N Cherry Ave}',
    'University of Arizona, Department of Astronomy',
])
def test_ambiguous_re_hits(line):
    assert evidence_in_texfile(tex(line + '\n'), AMBIGUOUS_RE) == 1


@pytest.mark.parametrize('line', [
    'Department of Optical Sciences, University of Arizona',
    'Lunar and Planetary Laboratory, University of Arizona',
    'Steward Observatory',
    'jdoe@arizona.edu',
    r'\and University of Arizona, Tucson, AZ, USA',
    'Tucson: University of Arizona Press, 1985',
])
def test_ambiguous_re_misses(line):
    assert evidence_in_texfile(tex(line + '\n'), AMBIGUOUS_RE) == 0


def test_default_pattern_is_uofa_re():
    assert evidence_in_texfile(tex('jdoe@arizona.edu\n')) == 1


def make_entry(author):
    return types.SimpleNamespace(
        title='A paper', tags=[{'term': 'astro-ph.GA'}], author=author,
        link='https://arxiv.org/abs/2610.00001',
        id='oai:arXiv.org:2610.00001',
        summary='arXiv:2610.00001 Announce Type: new\nAbstract: Hello')


@pytest.fixture(autouse=True)
def no_sleep():
    with mock.patch.object(feed.time, 'sleep'):
        yield


def lookup_none(name, people):
    return None, 0


def run(evidence, success, author='Nobody Here'):
    with mock.patch.object(feed, 'approximate_name_lookup', lookup_none), \
         mock.patch.object(feed, 'gather_affiliation_evidence',
                           return_value=(evidence, success)) as gather:
        out = feed.unpack_feed_entry(make_entry(author), PEOPLE)
    return out, gather


def test_unmatched_with_evidence_is_ambiguous():
    out, gather = run(2, True)
    assert out['ambiguous'] is True
    assert gather.call_args.args[1] is AMBIGUOUS_RE


def test_unmatched_without_evidence_dropped():
    assert run(0, True)[0] is None


def test_unmatched_download_failure_dropped():
    assert run(0, False)[0] is None


def test_unmatched_skipped_without_affiliation_check():
    with mock.patch.object(feed, 'approximate_name_lookup', lookup_none):
        assert feed.unpack_feed_entry(make_entry('Nobody'), PEOPLE,
                                      check_affiliation=False) is None


def test_weak_match_without_evidence_still_dropped():
    with mock.patch.object(feed, 'approximate_name_lookup',
                           return_value=(('Smith', 'Jane'), 1)), \
         mock.patch.object(feed, 'gather_affiliation_evidence',
                           return_value=(0, True)):
        assert feed.unpack_feed_entry(make_entry('J. Smith'), PEOPLE) is None


def test_matched_post_not_ambiguous():
    with mock.patch.object(feed, 'approximate_name_lookup',
                           return_value=(('Smith', 'Jane'), 2)), \
         mock.patch.object(feed, 'gather_affiliation_evidence',
                           return_value=(1, True)):
        out = feed.unpack_feed_entry(make_entry('Jane Smith'), PEOPLE)
    assert out['ambiguous'] is False
