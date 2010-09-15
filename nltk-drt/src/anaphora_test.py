from temporaldrt import DrtParser, DrtFeatureExpression
from util import Tester
import nltkfixtemporal

class AnaphoraResolutionException(Exception):
    pass

def get_refs(self, recursive=False):
    return []

from nltk.sem.drt import AbstractDrs

AbstractDrs.get_refs = get_refs

def main():
    #parser = load_parser('file:../data/featuredrt_test.fcfg', logic_parser=DrtParser())
    cases = [
    (1, "He wants a car. Jones needs it.", "DRS([x,z8,e,z11,z10,e012],[PRO{sg,m}(x), car{sg,n}(z8), want(e), AGENT(e,x), THEME(e,z8), Jones{sg,m}(z11), PRO{sg,n}(z10), need(e012), AGENT(e012,z11), THEME(e012,z10)])", AnaphoraResolutionException),
    (2, "He invites Jones.", "DRS([x,z14,e],[PRO{sg,m}(x), Jones{sg,m}(z14), invite(e), AGENT(e,x), THEME(e,z14)])", AnaphoraResolutionException),
    (3, "Jones loves Charlotte but Bill loves her too and he asks himself why.", "DRS([x,z10,e,z13,z12,e014,z26,z25,e027],[Jones{sg,m}(x), Charlotte{sg,f}(z10), love(e), AGENT(e,x), THEME(e,z10), Bill{sg,m}(z13), (z12 = z10), love(e014), AGENT(e014,z13), THEME(e014,z12), (z26 = z13), (z25 = z26), ask(e027), AGENT(e027,z26), THEME(e027,z25)])", None),
    (4, "Jones loves Charlotte but Bill loves her too and he asks him why.", "DRS([x,z33,e,z36,z35,e037,z49,z48,e050],[Jones{sg,m}(x), Charlotte{sg,f}(z33), love(e), AGENT(e,x), THEME(e,z33), Bill{sg,m}(z36), (z35 = z33), love(e037), AGENT(e037,z36), THEME(e037,z35), (z49 = z36), (z48 = z36), ask(e050), AGENT(e050,z49), THEME(e050,z48)])", None),
    (5, "Jones loves Charlotte but Bill loves her too and himself asks him why.", "DRS([x,z44,e,z47,z46,e048,z53,z50,e054],[Jones{sg,m}(x), Charlotte{sg,f}(z44), love(e), AGENT(e,x), THEME(e,z44), Bill{sg,m}(z47), PRO{sg,f}(z46), love(e048), AGENT(e048,z47), THEME(e048,z46), REFPRO{sg,m}(z53), PRO{sg,m}(z50), ask(e054), AGENT(e054,z53), THEME(e054,z50)])", AnaphoraResolutionException),
    (6, "Jones likes a picture of himself.", "DRS([x,z5,z3,e],[Jones{sg,m}(x), (z3 = x), THEME(z5,z3), picture{sg,n}(z5), like(e), AGENT(e,x), THEME(e,z5)])", None),
    (7, "Jones likes a picture of him.", "DRS([x,z66,z64,e],[Jones{sg,m}(x), PRO{sg,m}(z64), THEME(z66,z64), picture{sg,n}(z66), like(e), AGENT(e,x), THEME(e,z66)])", AnaphoraResolutionException),
    (8, "Bill likes Jones's picture of himself", "DRS([x,z92,z,z91,e],[Bill{sg,m}(x), Jones{sg,m}(z92), POSSESSOR(z,z92), (z91 = z92), THEME(z,z91), picture{sg,n}(z), like(e), AGENT(e,x), THEME(e,z)])", None),
    (9, "Bill likes Jones's picture of him", "DRS([x,z97,z,z96,e],[Bill{sg,m}(x), Jones{sg,m}(z97), POSSESSOR(z,z97), (z96 = x), THEME(z,z96), picture{sg,n}(z), like(e), AGENT(e,x), THEME(e,z)])", None),
    (10,"Jones shows Bill his room. He likes it", "DRS([x,z3,e,y,z,z6,z5,e07],[Jones{sg,m}(x), Bill{sg,m}(z3), show(e), AGENT(e,x), PATIENT(e,z3), POSPRO{sg,m}(y), POSSESSOR(z,y), room{sg,n}(z), THEME(e,z), PRO{sg,m}(z6), PRO{sg,n}(z5), like(e07), AGENT(e07,z6), THEME(e07,z5)])", None),
    (14,"Jones owns a Porsche. He likes it.", "DRS([x,z106,e,z109,z108,e0110],[Jones{sg,m}(x), Porsche{sg,n}(z106), own(e), AGENT(e,x), THEME(e,z106), (z109 = x), (z108 = z106), like(e0110), AGENT(e0110,z109), THEME(e0110,z108)])", None),
    (18,"Jones owns a car or he commutes.", "DRS([],[(([x,z2,e],[Jones{sg,m}(x), car{sg,n}(z2), own(e), AGENT(e,x), THEME(e,z2)]) | ([x,e],[PRO{sg,m}(x), commute(e), AGENT(e,x)]))])", None),
    (19,"Jones owns a Porsche or Brown owns it", "DRS([],[(([x,z2,e],[Jones{sg,m}(x), Porsche{sg,n}(z2), own(e), AGENT(e,x), THEME(e,z2)]) | ([x,z4,e],[Brown{sg,f}(x), PRO{sg,n}(z4), own(e), AGENT(e,x), THEME(e,z4)]))])", AnaphoraResolutionException)

    ]

    #test(parser, DrtParser(), cases)

    #print(parse(parser, "Bill's car walks"))
    #print(parse(parser, "His car walks"))
    #Jones shows Bill his room. He likes it.
    p = DrtParser()
    drs = p.parse("DRS([x,z2,e],[Jones{sg,m}(x), Porsche{sg,n}(z2), own(e)])")
    print drs
    tester = Tester('file:../data/grammar.fcfg', DrtParser)
    drs = tester.parse("A boy does walk. His car does walk.")
    readings = drs.readings()
    print readings
    for reading in readings:
        reading.draw()

if __name__ == '__main__':
    main()