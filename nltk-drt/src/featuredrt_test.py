from nltk import load_parser
from featuredrt import DrtParser, AnaphoraResolutionException
from util import parse, test
import nltkfixtemporal

def get_refs(self, recursive=False):
    return []

from nltk.sem.drt import AbstractDrs

AbstractDrs.get_refs = get_refs

def main():
    parser = load_parser('file:../data/test.fcfg', logic_parser=DrtParser())
    cases = [
    (1, "He wants a car. Jones needs it.", "DRS([x,z8,e,z11,z10,e012],[PRO{sg,m}(x), car{sg,n}(z8), want(e), AGENT(e,x), THEME(e,z8), Jones{sg,m}(z11), PRO{sg,n}(z10), need(e012), AGENT(e012,z11), THEME(e012,z10)])", AnaphoraResolutionException),
    (2, "He invites Jones.", "DRS([x,z14,e],[PRO{sg,m}(x), Jones{sg,m}(z14), invite(e), AGENT(e,x), THEME(e,z14)])", AnaphoraResolutionException),
    (3, "Jones loves Charlotte but Bill loves her and he asks himself.", "DRS([x,z16,e,z19,z18,e020,z25,z22,e026],[Jones{sg,m}(x), Charlotte{sg,f}(z16), love(e), AGENT(e,x), THEME(e,z16), Bill{sg,m}(z19), PRO{sg,f}(z18), love(e020), AGENT(e020,z19), THEME(e020,z18), PRO{sg,m}(z25), REFPRO{sg,m}(z22), ask(e026), AGENT(e026,z25), THEME(e026,z22)])", None),
    (4, "Jones loves Charlotte but Bill loves her and he asks him.", "DRS([x,z30,e,z33,z32,e034,z39,z36,e040],[Jones{sg,m}(x), Charlotte{sg,f}(z30), love(e), AGENT(e,x), THEME(e,z30), Bill{sg,m}(z33), PRO{sg,f}(z32), love(e034), AGENT(e034,z33), THEME(e034,z32), PRO{sg,m}(z39), PRO{sg,m}(z36), ask(e040), AGENT(e040,z39), THEME(e040,z36)])", None),
    (5, "Jones loves Charlotte but Bill loves her and himself asks him.", "DRS([x,z44,e,z47,z46,e048,z53,z50,e054],[Jones{sg,m}(x), Charlotte{sg,f}(z44), love(e), AGENT(e,x), THEME(e,z44), Bill{sg,m}(z47), PRO{sg,f}(z46), love(e048), AGENT(e048,z47), THEME(e048,z46), REFPRO{sg,m}(z53), PRO{sg,m}(z50), ask(e054), AGENT(e054,z53), THEME(e054,z50)])", AnaphoraResolutionException),
    (6, "Jones likes a picture of himself.", "DRS([x,z61,z59,e],[Jones{sg,m}(x), REFPRO{sg,m}(z59), THEME(z61,z59), picture{sg,n}(z61), like(e), AGENT(e,x), THEME(e,z61)])", None),
    (7, "Jones likes a picture of him.", "DRS([x,z66,z64,e],[Jones{sg,m}(x), PRO{sg,m}(z64), THEME(z66,z64), picture{sg,n}(z66), like(e), AGENT(e,x), THEME(e,z66)])", AnaphoraResolutionException),
    (8, "Bill likes Jones's picture of himself", "DRS([x,z72,z,z71,e],[Bill{sg,m}(x), Jones{sg,m}(z72), POSSESSOR(z,z72), REFPRO{sg,m}(z71), THEME(z,z71), picture{sg,n}(z), like(e), AGENT(e,x), THEME(e,z)])", None),
    (9, "Bill likes Jones's picture of him", "DRS([x,z6,z,z5,e],[Bill{sg,m}(x), Jones{sg,m}(z6), POSSESSOR(z,z6), PRO{sg,m}(z5), THEME(z,z5), picture{sg,n}(z), like(e), AGENT(e,x), THEME(e,z)])", None)
#    (10, "Bill's car walks", "DRS([x{sg,m},e,z51{sg,n},e052],[Bill(x), possession(e), POSSESSOR(e,x), POSSESSED(e,z51), car(z51), walk(e052), AGENT(e052,z51)])", None)
    ]

    test(parser, DrtParser(), cases, False)

    #print(parse(parser, "Bill's car walks"))
    #print(parse(parser, "His car walks"))

    parser = load_parser('file:../data/test.fcfg', logic_parser=DrtParser())
    drs = parse(parser, "Jones likes a picture of himself.", True)
    drs = drs.resolve()
    print drs
    drs.draw()

if __name__ == '__main__':
    main()