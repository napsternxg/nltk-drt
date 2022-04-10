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


@pytest.mark.properties
def test_properties(subtests):

    tester = Tester('file:./nltk-drt/data/grammar.fcfg', DrtParser, subtests)

    cases = [
        (14, "Mary likes John's car or she hates it.", "([n,x,z307,y],[(([s],[like(s), AGENT(s,x), PATIENT(s,y), overlap(n,s)]) | ([s0327],[hate(s0327), AGENT(s0327,x), PATIENT(s0327,y), overlap(n,s0327)])), POSS(y,z307), car{sg,n}(y), John{sg,m}(z307), Mary{sg,f}(x)])")
    ]
    tester.test(cases)


HASH_LINE = "#"*80

def print_header(header):
    len_hash = (74 - len(header)) // 2
    print("\n\t# {0} #\n\t### {1} {2} {1} ###\n\t# {0} #\n\n".format(HASH_LINE, "#"*len_hash, header))

TESTS = [("Test accounting featstruct properties", test_properties)
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
