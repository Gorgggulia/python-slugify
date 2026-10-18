"""Additional tests written to kill surviving mutants found by mutmut (lab 1).

Every test documents the behaviour of python-slugify that the original suite
did not pin down. All tests pass on the unmodified code.
"""
import re
import sys

import pytest

from slugify import slugify, smart_truncate
from slugify import _legacy
from slugify.__main__ import parse_args
from slugify.special import add_uppercase_char


# --------------------------------------------------------------------------
# _legacy.slugify / smart_truncate: default argument values (called directly,
# because the public slugify() always passes every argument explicitly)
# --------------------------------------------------------------------------
class TestLegacyDefaults:
    def test_entities_decimal_hexadecimal_default_on(self):
        assert _legacy.slugify('Tom &amp; Jerry') == 'tom-jerry'
        assert _legacy.slugify('&#65;bc') == 'abc'
        assert _legacy.slugify('&#x41;bc') == 'abc'

    def test_max_length_default_is_unlimited(self):
        assert _legacy.slugify('alpha beta gamma') == 'alpha-beta-gamma'

    def test_word_boundary_default_off(self):
        assert _legacy.slugify('aaa bbb ccc', max_length=5) == 'aaa-b'

    def test_save_order_default_off(self):
        assert _legacy.slugify('aaa bbbbbbb cc', max_length=6, word_boundary=True) == 'aaa-cc'

    def test_lowercase_default_on(self):
        assert _legacy.slugify('ABC') == 'abc'

    def test_allow_unicode_default_off(self):
        assert _legacy.slugify('Ñandú') == 'nandu'

    def test_replacement_stage_and_backend_defaults_are_valid(self):
        assert _legacy.slugify('x', replacements=[('x', 'y')]) == 'y'
        assert _legacy.slugify('Ñ') == 'n'

    def test_smart_truncate_word_boundary_default_off(self):
        assert smart_truncate('aaa bbb ccc', max_length=5) == 'aaa b'

    def test_smart_truncate_skips_empty_words_between_repeated_separators(self):
        # 'aa  bb cc'.split(' ') -> ['aa', '', 'bb', 'cc']: the empty word must be skipped.
        assert smart_truncate('aa  bb cc', max_length=6, word_boundary=True, separator=' ') == 'aa bb'


# --------------------------------------------------------------------------
# _legacy._transliterate: fallback and backend selection
# --------------------------------------------------------------------------
class TestLegacyTransliterate:
    def test_auto_falls_back_to_text_unidecode(self, monkeypatch):
        pytest.importorskip('text_unidecode')
        monkeypatch.setitem(sys.modules, 'unidecode', None)
        assert _legacy._transliterate('Ñ', 'auto') == 'N'

    def test_auto_reraises_unrelated_missing_module(self, monkeypatch):
        def boom(name):
            raise ModuleNotFoundError('other dependency', name='other_dep')
        monkeypatch.setattr(_legacy, 'import_module', boom)
        with pytest.raises(ModuleNotFoundError, match='other dependency'):
            _legacy._transliterate('Ñ', 'auto')

    def test_anyascii_backend_uses_anyascii_function(self):
        pytest.importorskip('anyascii')
        assert _legacy._transliterate('Ñ', 'anyascii') == 'N'

    def test_unidecode_backend_uses_unidecode_function(self):
        pytest.importorskip('unidecode')
        assert _legacy._transliterate('Ñ', 'unidecode') == 'N'


# --------------------------------------------------------------------------
# Error messages and input decoding (legacy and modern)
# --------------------------------------------------------------------------
@pytest.mark.parametrize('algorithm', ['legacy', 'modern'])
class TestValidation:
    def test_text_type_error_names_the_type(self, algorithm):
        with pytest.raises(TypeError, match=r'text must be str, bytes or bytearray, not int$'):
            slugify(5, algorithm=algorithm)

    def test_invalid_bytes_are_ignored(self, algorithm):
        assert slugify(b'abc\xffdef', algorithm=algorithm) == 'abcdef'
        assert slugify(bytearray(b'a\xc3\x28b'), algorithm=algorithm) == 'a-b'

    def test_replacement_stage_error_message(self, algorithm):
        with pytest.raises(ValueError, match=r"^replacement_stage must be 'both', 'pre' or 'post'$"):
            slugify('x', replacement_stage='bogus', algorithm=algorithm)

    def test_backend_error_message(self, algorithm):
        msg = r"^backend must be 'auto', 'text-unidecode', 'unidecode' or 'anyascii'$"
        with pytest.raises(ValueError, match=msg):
            slugify('x', backend='bogus', algorithm=algorithm)

    def test_post_only_replacement_stage_is_accepted_and_applied(self, algorithm):
        assert slugify('x', replacements=[('x', 'y')], replacement_stage='post', algorithm=algorithm) == 'y'
        assert slugify('x', replacements=[('x', 'y')], replacement_stage='pre', algorithm=algorithm) == 'y'

    def test_post_replacement_result_is_not_stripped(self, algorithm):
        assert slugify('x', replacements=[('x', '-y-')], replacement_stage='post', algorithm=algorithm) == '-y-'


def test_modern_type_error_messages():
    with pytest.raises(TypeError, match=r'^max_length must be an int, not str$'):
        slugify('x', max_length='3', algorithm='modern')
    with pytest.raises(TypeError, match=r'^max_length must be an int, not bool$'):
        slugify('x', max_length=True, algorithm='modern')
    with pytest.raises(TypeError, match=r'^separator must be str, not int$'):
        slugify('x', separator=1, algorithm='modern')


def test_unknown_algorithm_error_message():
    with pytest.raises(ValueError, match=r"^algorithm must be 'legacy' or 'modern'$"):
        slugify('x', algorithm='bogus')


@pytest.mark.parametrize('algorithm', ['legacy', 'modern'])
def test_dispatch_forwards_regex_pattern(algorithm):
    assert slugify('a_b c', regex_pattern=r'[^-a-zA-Z0-9_]+', algorithm=algorithm) == 'a_b-c'


# --------------------------------------------------------------------------
# Modern algorithm details
# --------------------------------------------------------------------------
def test_modern_numeric_reference_boundary_of_surrogate_range():
    # U+DFFF is a surrogate (left as text), U+E000 is a valid private-use code point.
    assert slugify('&#57343;', algorithm='modern') == '57343'
    assert slugify('&#57344;', algorithm='modern') == ''
    assert slugify('&#55295;', algorithm='modern') == ''
    assert slugify('&#55296;', algorithm='modern') == '55296'


def test_modern_thousands_separator_is_removed():
    assert slugify('1,000,000 items', algorithm='modern') == '1000000-items'


def test_modern_replacements_none_is_treated_as_empty():
    assert slugify('abc', replacements=None, algorithm='modern') == 'abc'


@pytest.mark.parametrize('text, limit, expected', [
    ('aa bb cc dd', 8, 'aa-bb-cc'),
    ('aa bb cc dd', 7, 'aa-bb-c'),
    ('a b c d e f', 9, 'a-b-c-d-e'),
])
def test_modern_hard_truncate_keeps_single_delimiters(text, limit, expected):
    assert slugify(text, max_length=limit, algorithm='modern') == expected


# --------------------------------------------------------------------------
# special.add_uppercase_char
# --------------------------------------------------------------------------
def test_add_uppercase_char_does_not_duplicate_or_add_for_uppercase():
    assert add_uppercase_char([('A', 'b')]) == [('A', 'b')]
    pairs = [('a', 'b'), ('A', 'B')]
    assert add_uppercase_char(pairs) == [('a', 'b'), ('A', 'B')]


def test_add_uppercase_char_compares_with_uppercased_char_not_translation():
    assert add_uppercase_char([('1a', '1a')]) == [('1A', '1a'), ('1a', '1a')]


# --------------------------------------------------------------------------
# CLI: argparse configuration
# --------------------------------------------------------------------------
def _help_text(capsys, monkeypatch):
    monkeypatch.setenv('COLUMNS', '300')
    with pytest.raises(SystemExit) as exc:
        parse_args(['slugify', '--help'])
    assert exc.value.code == 0
    return ' '.join(capsys.readouterr().out.split())


HELP_PHRASES = [
    'Slug string', 'Input', 'Text to slugify', 'Take the text from STDIN',
    'Do not convert HTML entities to unicode',
    'Do not convert HTML decimal to unicode',
    'Do not convert HTML hexadecimal to unicode',
    'Output string length, 0 for no limit',
    'Truncate to complete word even if length ends up shorter than --max_length',
    'When set and --max_length > 0 return whole words in the initial order',
    'Separator between words. By default -',
    'Words to discount',
    'Python regex pattern for disallowed characters',
    'Activate case sensitivity',
    'Additional replacement rules e.g. "|->or", "%->percent".',
    'Allow unicode characters',
    'Slug algorithm (legacy default; modern explicitly opts into changed output)',
    'Transliteration backend (auto preserves legacy preference)',
    'Apply replacement rules before, after, or both sides of cleanup',
]


@pytest.mark.parametrize('phrase', HELP_PHRASES)
def test_help_output_contains_exact_phrase(phrase, capsys, monkeypatch):
    out = _help_text(capsys, monkeypatch)
    assert re.search(r'(?<![\w])' + re.escape(phrase) + r'(?![\w])', out), phrase


def test_allow_unicode_is_a_flag():
    assert parse_args(['slugify', '--allow-unicode']).allow_unicode is True
    assert parse_args(['slugify']).allow_unicode is False


@pytest.mark.parametrize('option, bad', [
    ('--algorithm', 'bogus'), ('--backend', 'bogus'), ('--replacement-stage', 'bogus'),
])
def test_choice_options_reject_unknown_values(option, bad, capsys):
    with pytest.raises(SystemExit) as exc:
        parse_args(['slugify', option, bad])
    assert exc.value.code == 2
    assert 'invalid choice' in capsys.readouterr().err


@pytest.mark.parametrize('option, good', [
    ('--algorithm', 'modern'), ('--backend', 'anyascii'), ('--replacement-stage', 'post'),
])
def test_choice_options_accept_known_values(option, good):
    ns = parse_args(['slugify', option, good])
    assert getattr(ns, option[2:].replace('-', '_')) == good


def test_stdin_and_input_conflict_message(capsys):
    with pytest.raises(SystemExit) as exc:
        parse_args(['slugify', '--stdin', 'text'])
    assert exc.value.code == 2
    assert re.search(r'error: Input strings and --stdin cannot work together$', capsys.readouterr().err, re.M)


def test_replacement_format_error_message(capsys):
    with pytest.raises(SystemExit) as exc:
        parse_args(['slugify', 'x', '--replacements', 'no-arrow'])
    assert exc.value.code == 2
    assert re.search(r'error: Replacements must be of the form: ORIGINAL->REPLACED$', capsys.readouterr().err, re.M)


def test_replacement_is_split_on_first_separator_only():
    ns = parse_args(['slugify', 'x', '--replacements', 'a->b->c->d'])
    assert ns.replacements == [['a', 'b->c->d']]
