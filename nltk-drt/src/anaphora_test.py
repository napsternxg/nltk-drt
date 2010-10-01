from temporaldrt import AnaphoraResolutionException
from temporaldrt import DrtParser
from util import Tester
import nltkfixtemporal

def get_refs(self, recursive=False):
    return []

from nltk.sem.drt import AbstractDrs

AbstractDrs.get_refs = get_refs

def main():
    cases = [
    (1, "He wants a car. Jones needs it.", None, AnaphoraResolutionException),
    (2, "He invites Jones.", None, AnaphoraResolutionException),
    (3, "Jones loves Charlotte but Bill loves her and he asked himself.", "DRS([n,s,s024,t032,e,x,z18,z23],[Jones{sg,m}(x), Charlotte{sg,f}(z18), love(s), AGENT(s,x), PATIENT(s,z18), overlap(n,s), Bill{sg,m}(z23), love(s024), AGENT(s024,z23), PATIENT(s024,z18), overlap(n,s024), overlap(s,s024), earlier(t032,n), ask(e), AGENT(e,z23), PATIENT(e,z23), include(t032,e), include(s024,e)])", None),
    (4, "Jones loves Charlotte but Bill loves her and he asked him.", "DRS([n,s,s043,t051,e,x,z37,z42],[Jones{sg,m}(x), Charlotte{sg,f}(z37), love(s), AGENT(s,x), PATIENT(s,z37), overlap(n,s), Bill{sg,m}(z42), love(s043), AGENT(s043,z42), PATIENT(s043,z37), overlap(n,s043), overlap(s,s043), earlier(t051,n), ask(e), AGENT(e,z42), PATIENT(e,x), include(t051,e), include(s043,e)])", None),
    (5, "Jones loves Charlotte but Bill loves her and himself asked him.", None, AnaphoraResolutionException),
    (6, "Jones likes a picture of himself.", "DRS([n,z79,e,x],[Jones{sg,m}(x), REL(z79,x), picture{sg,n}(z79), like(e), AGENT(e,x), PATIENT(e,z79), include(n,e)])", None),
    (7, "Jones likes a picture of him.", None, AnaphoraResolutionException),
    (8, "Bill likes Jones's picture of himself", "DRS([n,e,x,z98,y],[Bill{sg,m}(x), POSS(y,z98), REL(y,z98), picture{sg,n}(y), Jones{sg,m}(z98), like(e), AGENT(e,x), PATIENT(e,y), include(n,e)])", None),
    (9, "Bill likes Jones's picture of him", "DRS([n,e,x,z111,y],[Bill{sg,m}(x), POSS(y,z111), REL(y,x), picture{sg,n}(y), Jones{sg,m}(z111), like(e), AGENT(e,x), PATIENT(e,y), include(n,e)])", None),
    (10,"Jones shows Bill his room. He likes it", "DRS([n,e,e0122,x,z115,z116],[Jones{sg,m}(x), POSS(z115,x), room{sg,n}(z115), Bill{sg,m}(z116), show(e), AGENT(e,x), PATIENT(e,z115), RECIP(e,z116), include(n,e), like(e0122), AGENT(e0122,x), PATIENT(e0122,z115), include(n,e0122), earlier(e,e0122)])", None),
    (11, "If Jones is not dead, he will die.", "DRS([n,x],[(([],[-([s],[dead(s), THEME(s,x), overlap(n,s)])]) -> ([t0128,e],[earlier(n,t0128), die(e), AGENT(e,x), include(t0128,e)])), Jones{sg,m}(x)])", None),
    (12, "No one dates Charlotte and she is upset.", "DRS([n,s,z131],[-([x,e],[human{sg,m}(x), date(e), AGENT(e,x), PATIENT(e,z131), include(n,e), include(s,e)]), Charlotte{sg,f}(z131), upset(s), THEME(s,z131), overlap(n,s)])", None),
    (13, "If Jones is stupid, everyone underestimates him.", "DRS([n,z145],[(([s],[stupid(s), THEME(s,z145), overlap(n,s)]) -> ([],[(([x],[human{sg,m}(x)]) -> ([s0150],[underestimate(s0150), AGENT(s0150,x), PATIENT(s0150,z145), overlap(n,s0150), overlap(s,s0150)]))])), Jones{sg,m}(z145)])", None),
    (14, "Jones owns a porsche. He likes it.", "DRS([n,z89,s,e,x],[Jones{sg,m}(x), porsche{sg,n}(z89), own(s), AGENT(s,x), PATIENT(s,z89), overlap(n,s), like(e), AGENT(e,x), PATIENT(e,z89), include(n,e), include(s,e)])", None),
    (15, "Jones does not own a porsche. He likes it.", None, AnaphoraResolutionException),
    (16, "Every farmer who owns a donkey beats it.", "DRS([n],[(([x,z171,s],[donkey{sg,n}(z171), own(s), AGENT(s,x), PATIENT(s,z171), overlap(n,s), farmer{sg,m}(x)]) -> ([e],[beat(e), AGENT(e,x), PATIENT(e,z171), include(n,e), include(s,e)]))])", None),
    (17, "Every farmer owns a donkey. He beats it.", None, AnaphoraResolutionException),
    (18, "Jones owns a car or he commutes.", "DRS([n,x],[(([z135,s],[car{sg,n}(z135), own(s), AGENT(s,x), PATIENT(s,z135), overlap(n,s)]) | ([e],[commute(e), AGENT(e,x), include(n,e)])), Jones{sg,m}(x)])", None),
    (19, "Jones owns a porsche or Brown owns it", None, AnaphoraResolutionException),
    (20, "Jones owns it or Brown owns a porsche", None, AnaphoraResolutionException),
#    (21, "Either Jones does not own a car or he hides it.", None, None),
    (22, "Jones loves the baroness and Bill loves her.", "DRS([n,s,s0175,x,z169,z174],[Jones{sg,m}(x), baroness{sg,f}(z169), love(s), AGENT(s,x), PATIENT(s,z169), overlap(n,s), Bill{sg,m}(z174), love(s0175), AGENT(s0175,z174), PATIENT(s0175,z169), overlap(n,s0175), overlap(s,s0175)])", None),
    (23, "Jones loves her and Bill loves the baroness.", None, AnaphoraResolutionException)

    ]

    tester = Tester('file:../data/grammar.fcfg', DrtParser)
    tester.test(cases)

#    tester = Tester('file:../data/grammar.fcfg', DrtParser)
#    drs = tester.parse("If Jones is stupid, everyone underestimates him.")
#    print drs
#    readings = drs.readings(True)
#    print readings
#    for reading in readings:
#        for cond in reading.conds:
#            print type(cond), cond
#        reading.draw()

if __name__ == '__main__':
    main()