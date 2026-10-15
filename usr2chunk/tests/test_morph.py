import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from morph import verb, noun, adj

CASES = [
    (verb('go', 'past'), 'went'), (verb('go', 'pp'), 'gone'), (verb('find', 'pp'), 'found'),
    (verb('build', 'past'), 'built'), (verb('hypnotise', 'pres3sg'), 'hypnotises'), (verb('teach', 'pp'), 'taught'),
    (verb('lose', 'pp'), 'lost'), (verb('visit', 'ger'), 'visiting'), (verb('bathe', 'ger'), 'bathing'),
    (verb('begin', 'pp'), 'begun'), (verb('be', 'pres3sg'), 'is'), (verb('be', 'past'), 'were'),
    (verb('be', 'past3sg'), 'was'), (verb('have', 'pres3sg'), 'has'), (verb('pass away', 'past'), 'passed away'),
    (verb('worship', 'pp'), 'worshipped'), (verb('organize', 'pp'), 'organized'), (verb('dig', 'pp'), 'dug'),
    (verb('fulfil', 'pp'), 'fulfilled'), (verb('lie', 'pres3sg'), 'lies'),
    (noun('church', 'pl'), 'churches'), (noun('child', 'pl'), 'children'), (noun('devotee', 'pl'), 'devotees'),
    (noun('tirthankara', 'pl'), 'tirthankaras'), (noun('goods-train', 'pl'), 'goods-trains'), (noun('city', 'pl'), 'cities'),
    (noun('person', 'pl'), 'persons'), (adj('old', 'sup'), 'oldest'), (adj('big', 'comp'), 'bigger'),
    (adj('important', 'sup'), 'most important'),
]
bad = [(got, exp) for got, exp in CASES if got != exp]
print('morph tests: %d/%d pass' % (len(CASES) - len(bad), len(CASES)))
for got, exp in bad:
    print('  FAIL got %r expected %r' % (got, exp))
sys.exit(1 if bad else 0)
