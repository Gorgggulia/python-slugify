"""Differential fuzzing of surviving mutants: original vs mutant on random inputs.
Run from <project>/mutants. Finding a differing input proves a mutant is NOT equivalent;
finding none after many trials is (strong, not formal) evidence of equivalence."""
import io, os, random, sys, contextlib
sys.path.insert(0, os.getcwd())
from slugify import slugify, smart_truncate
from slugify.__main__ import parse_args

random.seed(20261017)
POOL = list("abcXYZ019 -_,.'\"&;#!?") + ['é','Ñ','ß','Ü','ö','я','Щ','中','文','🙂','ﬁ','№','½','&amp;','&#65;','&#x41;','&#57344;','1,000','--','  ','\u00a0','İ','Å','ǆ']
def rtext():
    return ''.join(random.choice(POOL) for _ in range(random.randint(0, 14)))
def rcase():
    t = rtext()
    if random.random() < 0.1:
        t = t.encode('utf-8', 'ignore')
        if random.random() < .5: t += b'\xff\xfe'
    kw = dict(
        max_length=random.choice([0, 0, 1, 2, 3, 5, 8, 12, -1]),
        word_boundary=random.random() < .5, save_order=random.random() < .5,
        separator=random.choice(['-', '-', '_', '--', '', '.', '+x']),
        lowercase=random.random() < .7, allow_unicode=random.random() < .4,
        stopwords=random.choice([(), ('a',), ('abc', 'X')]),
        replacements=random.choice([(), (), [('a', 'b')], [('x', '-y-')], [('&', ' and ')]]),
        replacement_stage=random.choice(['both', 'pre', 'post']),
        backend=random.choice(['auto', 'text-unidecode', 'unidecode', 'anyascii']),
        algorithm=random.choice(['legacy', 'modern']),
        regex_pattern=random.choice([None, None, r'[^a-z]+']),
    )
    return t, kw
def call(t, kw):
    try: return ('ok', slugify(t, **kw))
    except Exception as e: return ('err', type(e).__name__, str(e))
def trunc_case():
    s = ''.join(random.choice('ab -_') for _ in range(random.randint(0, 14)))
    return s, dict(max_length=random.randint(-2, 12), word_boundary=random.random() < .5,
                   separator=random.choice([' ', '-', '_']), save_order=random.random() < .5)
def tcall(s, kw):
    try: return ('ok', smart_truncate(s, **kw))
    except Exception as e: return ('err', type(e).__name__, str(e))
ARGVS = [[], ['x'], ['a', 'b'], ['--stdin'], ['--separator', '_', 'a b'], ['--no-entities'], ['--no-decimal'],
         ['--no-hexadecimal'], ['--no-lowercase'], ['--word-boundary'], ['--save-order'], ['--allow-unicode'],
         ['--max-length', '3'], ['--replacements', 'a->b'], ['--replacements', 'x'], ['--stopwords', 'a', 'b'],
         ['--algorithm', 'modern'], ['--algorithm', 'zzz'], ['--backend', 'anyascii'], ['--replacement-stage', 'post'],
         ['--stdin', 'x'], ['--help']]
def cli_case(argv):
    out, err = io.StringIO(), io.StringIO()
    os.environ['COLUMNS'] = '200'
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            sys.stdin = io.StringIO('stdin text')
            ns = parse_args(['slugify', *argv])
        return ('ok', sorted(vars(ns).items(), key=lambda kv: kv[0]), [type(v).__name__ for _, v in sorted(vars(ns).items())])
    except SystemExit as e:
        return ('exit', e.code, err.getvalue(), out.getvalue())

survivors = [l.strip() for l in open('../../artifacts/survivors_after.txt') if l.strip()]
N = int(sys.argv[1]) if len(sys.argv) > 1 else 6000
cases = [rcase() for _ in range(N)]
tcases = [trunc_case() for _ in range(N)]
os.environ['MUTANT_UNDER_TEST'] = ''
base = [call(*c) for c in cases]; tbase = [tcall(*c) for c in tcases]
cbase = [cli_case(a) for a in ARGVS]
print('mutant | slugify diffs | smart_truncate diffs | cli diffs')
for m in survivors:
    os.environ['MUTANT_UNDER_TEST'] = m
    d = [(c, b, call(*c)) for c, b in zip(cases, base) if call(*c) != b]
    td = [(c, b, tcall(*c)) for c, b in zip(tcases, tbase) if tcall(*c) != b]
    cd = [(a, b, cli_case(a)) for a, b in zip(ARGVS, cbase) if cli_case(a) != b]
    print(m.replace('slugify.', '', 1), '|', len(d), '|', len(td), '|', len(cd))
    for x in (d[:1] + td[:1] + cd[:1]): print('    DIFF', str(x)[:300])
