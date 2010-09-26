from temporaldrt import DrtFeatureExpression, AnaphoraResolutionException
from anaphora import DrtParser
from util import Tester
import nltkfixtemporal

def get_refs(self, recursive=False):
    return []

from nltk.sem.drt import AbstractDrs

AbstractDrs.get_refs = get_refs

def main():
    #parser = load_parser('file:../data/featuredrt_test.fcfg', logic_parser=DrtParser())
    cases = [
    (1, "He wants a car. Jones needs it.", None, AnaphoraResolutionException),
    (2, "He invites Jones.", None, AnaphoraResolutionException),
    (3, "Jones loves Charlotte but Bill loves her and he asked himself.", "DRS([n,s,s024,t032,e,x,z18,z23],[Jones{sg,m}(x), Charlotte{sg,f}(z18), love(s), AGENT(s,x), PATIENT(s,z18), overlap(n,s), Bill{sg,m}(z23), love(s024), AGENT(s024,z23), PATIENT(s024,z18), overlap(n,s024), overlap(s,s024), earlier(t032,n), ask(e), AGENT(e,z23), PATIENT(e,z23), include(t032,e), include(s024,e)])", None),
    (4, "Jones loves Charlotte but Bill loves her and he asked him.", "DRS([n,s,s043,t051,e,x,z37,z42],[Jones{sg,m}(x), Charlotte{sg,f}(z37), love(s), AGENT(s,x), PATIENT(s,z37), overlap(n,s), Bill{sg,m}(z42), love(s043), AGENT(s043,z42), PATIENT(s043,z37), overlap(n,s043), overlap(s,s043), earlier(t051,n), ask(e), AGENT(e,z42), PATIENT(e,x), include(t051,e), include(s043,e)])", None),
    (5, "Jones loves Charlotte but Bill loves her and himself asked him.", None, AnaphoraResolutionException),
    (6, "Jones likes a picture of himself.", "DRS([n,z79,e,x],[Jones{sg,m}(x), REL(z79,x), picture{sg,n}(z79), like(e), AGENT(e,x), PATIENT(e,z79), include(n,e)])", None),
    (7, "Jones likes a picture of him.", "DRS([x,z66,z64,e],[Jones{sg,m}(x), PRO{sg,m}(z64), THEME(z66,z64), picture{sg,n}(z66), like(e), AGENT(e,x), THEME(e,z66)])", AnaphoraResolutionException),
    (8, "Bill likes Jones's picture of himself", "DRS([x,z92,z,z91,e],[Bill{sg,m}(x), Jones{sg,m}(z92), POSSESSOR(z,z92), (z91 = z92), THEME(z,z91), picture{sg,n}(z), like(e), AGENT(e,x), THEME(e,z)])", None),
    (9, "Bill likes Jones's picture of him", "DRS([x,z97,z,z96,e],[Bill{sg,m}(x), Jones{sg,m}(z97), POSSESSOR(z,z97), (z96 = x), THEME(z,z96), picture{sg,n}(z), like(e), AGENT(e,x), THEME(e,z)])", None),
    (10,"Jones shows Bill his room. He likes it", "DRS([x,z3,e,y,z,z6,z5,e07],[Jones{sg,m}(x), Bill{sg,m}(z3), show(e), AGENT(e,x), PATIENT(e,z3), POSPRO{sg,m}(y), POSSESSOR(z,y), room{sg,n}(z), THEME(e,z), PRO{sg,m}(z6), PRO{sg,n}(z5), like(e07), AGENT(e07,z6), THEME(e07,z5)])", None),
    (11, "If Jones is at work, he will be late for dinner.", None, None),
    (12, "No one dates Charlotte and she is upset.", None, None),
    (13, "Everyone who thinks that Jones is stupid clearly underestimates him.", None, None),
    (14, "Jones owns a porsche. He likes it.", "([n,z89,s,e,x],[Jones{sg,m}(x), porsche{sg,n}(z89), own(s), AGENT(s,x), PATIENT(s,z89), overlap(n,s), like(e), AGENT(e,x), PATIENT(e,z89), include(n,e), include(s,e)])", None),
    (15, "Jones does not own a porsche . He likes it.", None, None),
    (16, "Every farmer who owns a donkey beats it.", None, None),
    (17, "Every farmer owns a donkey. He beats it.", None, None),
    (18, "Jones owns a car or he commutes.", "DRS([],[(([x,z2,e],[Jones{sg,m}(x), car{sg,n}(z2), own(e), AGENT(e,x), THEME(e,z2)]) | ([x,e],[PRO{sg,m}(x), commute(e), AGENT(e,x)]))])", None),
    (19, "Jones owns a porsche or Brown owns it", None, AnaphoraResolutionException),
    (20, "Jones owns it or Brown owns a porsche", None, AnaphoraResolutionException),
    (21, "Jones does not own a car or he hides it.", None, None),
    (22, "Jones loves the baroness and Bill loves her.", None, None),
    (23, "Jones loves her and Bill loves the baroness.", None, AnaphoraResolutionException)

    ]

    tester = Tester('file:../data/grammar.fcfg', DrtParser)
    tester.test(cases)

#    tester = Tester('file:../data/grammar.fcfg', DrtParser)
#    drs = tester.parse("Jones owns a car or he commutes.")
#    print drs
#    readings = drs.readings(True)
#    print readings
#    for reading in readings:
#        reading.draw()

if __name__ == '__main__':
    main()