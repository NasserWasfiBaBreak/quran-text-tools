import os

import pytest

from quran_text_tools import Quran, find_quotations, near_one, skeleton

HERE = os.path.dirname(__file__)


@pytest.fixture(scope='module')
def quran():
    return Quran.from_csv(os.path.join(HERE, 'fixture.csv'))


@pytest.mark.parametrize('mushaf, typed', [
    ('ٱلصَّلَوٰةَ', 'الصلاة'), ('ٱلرَّحۡمَٰنِ', 'الرحمن'), ('ٱلرَّحۡمَٰنِ', 'الرحمان'),
    ('بِهِۦ', 'به'), ('إِنَّهُۥ', 'انه'), ('ٱلصَّٰبِرِينَ', 'الصابرين'),
])
def test_skeleton_folds_spelling(mushaf, typed):
    assert skeleton(mushaf) == skeleton(typed)


def test_skeleton_keeps_different_words_apart():
    assert skeleton('صبر') != skeleton('صبروا')


def test_near_one():
    assert near_one('كتاب', 'كتب') and not near_one('كتاب', 'قلم')


def test_correct_quotation(quran):
    (q,) = find_quotations('قال تعالى: ﴿وقل رب زدني علما﴾ صدق الله', quran)
    assert (q.surah, q.ayah) == (20, 114) and q.correct


def test_changed_word_is_found_and_corrected(quran):
    (q,) = find_quotations('قال تعالى: «وقل ربي زدني علما»', quran)
    assert not q.correct and q.ref == '20:114'
    assert [d['kind'] for d in q.differences] == ['changed']
    assert skeleton(q.differences[0]['mushaf']) == skeleton('رب')


def test_hamza_is_a_difference(quran):
    (q,) = find_quotations('واعلموا «أن الله مع الصابرين»', quran)
    assert not q.correct and any(d['kind'] == 'changed' for d in q.differences)


def test_two_quotations_are_kept_apart(quran):
    qs = find_quotations('«بسم الله الرحمن الرحيم» و«الحمد لله رب العالمين»', quran)
    assert [q.ref for q in qs] == ['1:1', '1:2'] and all(q.correct for q in qs)


def test_ya_written_apart(quran):
    (q,) = find_quotations('يا أيها الذين آمنوا استعينوا بالصبر والصلاة إن الله مع الصابرين', quran)
    assert q.ref == '2:153' and q.correct and q.quoted.startswith('يا أيها')


def test_plain_text_finds_nothing(quran):
    assert find_quotations('هذا نص عادي لا آيات فيه', quran) == []
