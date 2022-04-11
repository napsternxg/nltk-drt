"""
Test suit for the temporaldrt module
"""
__author__ = "Alex Kislev, Emma Li, Peter Makarov"
__version__ = "1.0"
__date__ = "Tue, 24 Aug 2010"

import sys, os, pytest
sys.path.append("..")

from nltk_drt.util import Tester
from nltk_drt.wntemporaldrt import DrtParser

#background knowledge
BK = {
    'earlier' : r'all x y z.(earlier(x,y) & earlier(y,z) -> earlier(x,z)) & all x y.(earlier(x,y) -> -overlap(x,y))',

    'include' : r'all x y z.((include(x,y) & include(z,y)) -> (overlap(x,z)))',

    'die' : r'all x z y.((die(x) & AGENT(x,y) & die(z) & AGENT(z,y)) -> x = z)',

    'husband' : r'(([t,x,y],[POSS(y,x), husband(y)]) -> ([s],[married(s),THEME(s,x),overlap(t,s)]))',

    'married' : r'(([t,s],[married(s),THEME(s,x),overlap(t,s)]) -> ([x,y],[POSS(y,x), husband(y)]))',

    'own' : r'(([s,x,y],[own(s),AGENT(s,x),PATIENT(s,y)]) -> ([],[POSS(y,x)]))',

    'POSS' : r'(([t,y,x],[POSS(y,x)]) -> ([s],[own(s),AGENT(s,x),PATIENT(s,y),overlap(t,s)]))',

   'dead' : r'(([t,s,e,x],[include(s,t),abut(e,s),die(e),AGENT(e,x)]) -> ([],[dead(s),THEME(s,x),overlap(t,s)]))'
    }


@pytest.mark.rpro
def test_rpro(subtests):

    tester = Tester('file:./nltk-drt/data/grammar.fcfg', DrtParser, subtests)

    cases = [
        (16, "Every farmer who owns a donkey, likes it.", "([n],[(([x,z167,s],[donkey{sg,n}(z167), own(s), AGENT(s,x), PATIENT(s,z167), overlap(n,s), farmer{sg,m}(x)]) -> ([s0181],[like(s0181), AGENT(s0181,x), PATIENT(s0181,z167), overlap(n,s0181), overlap(s,s0181)]))])")
    ]
    tester.test(cases)


HASH_LINE = "#"*80

def print_header(header):
    len_hash = (74 - len(header)) // 2
    print("\n\t# {0} #\n\t### {1} {2} {1} ###\n\t# {0} #\n\n".format(HASH_LINE, "#"*len_hash, header))

TESTS = [("Test accounting RPRO processing", test_rpro)
         ]


def main():
    """Main function to start it all."""
    tester = Tester('file:../data/grammar.fcfg', DrtParser)
    for header, test in TESTS:
        print_header("Testing %s" % header)
        test(tester)
    print("\n\t{0} THE  END {0}".format("#"*37))

if __name__ == '__main__':
    main()
