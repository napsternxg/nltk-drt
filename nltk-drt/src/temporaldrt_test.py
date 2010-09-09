import nltkfixtemporal

from nltk import load_parser
from nltk.sem.drt import AbstractDrs

from util import parse, test

#from temporaldrt import DrtParser
from tenseaspect import DrtParser

def gr(s, recursive=False):
    return []

AbstractDrs.get_refs = gr


def main():
#    parser = load_parser('file:../data/tenseaspect.fcfg', logic_parser=DrtParser())
    cases = [
    # 1 through 6: a state predicate in simple tenses with / without negation 
    (1,"Angus owns a car","([n,t,x,z2,e],[loc_time(t), utter_time(n), eq(t,n), Angus(x), car(z2), own(e,x,z2), state(e), include(e,t)])",None),
    (2, "Angus does not own a car", "([n,t,x],[loc_time(t), utter_time(n), eq(t,n), Angus(x), -([z2,e,t04],[car(z2), own(e,x,z2), state(e), overlap(t04,e), (t04 = t)])])",None),
    (3,"Angus owned a car", "([n,t,x,z2,e],[loc_time(t), utter_time(n), earlier(t,n), Angus(x), car(z2), own(e,x,z2), state(e), overlap(t,e)])", None),
    (4,"Angus did not own a car", "([n,t,x],[loc_time(t), utter_time(n), earlier(t,n), Angus(x), -([z2,e,t04],[car(z2), own(e,x,z2), state(e), overlap(t04,e), (t04 = t)])])",None),
    (5,"Angus will own a car","([n,t,x,z2,e,t03],[loc_time(t), utter_time(n), earlier(n,t), Angus(x), car(z2), own(e,x,z2), state(e), overlap(t03,e), (t03 = t)])",None),
    (6,"Angus will not own a car","([n,t,x],[loc_time(t), utter_time(n), earlier(n,t), Angus(x), -([z2,e,t04],[car(z2), own(e,x,z2), state(e), overlap(t04,e), (t04 = t)])])",None),
    # 7 through 8: tense and quantifiers, note resolution of proper names
    (7,"Every dog will bite Angus","([n,t,z2],[loc_time(t), utter_time(n), earlier(n,t), Angus(z2), (([x],[dog(x)]) -> ([e,t03],[bite(e,x,z2), achiev(e), include(t03,e), (t03 = t)]))])",None),
    (8,"No dog bit Angus","([n,t,z2],[loc_time(t), utter_time(n), earlier(t,n), Angus(z2), -([x,e],[dog(x), bite(e,x,z2), achiev(e), include(t,e)])])",None),
    (9,"Angus bit a dog. He owns a dog.",None, None)
    ]

    #test(DrtParser(), 'tenseaspect.fcfg', cases)
    expr = parse(DrtParser(), 'tenseaspect.fcfg', "Angus owns a car. Angus owns a kitchen", True, False).resolve()
    print expr
    #expr = parse(DrtParser(), 'tenseaspect.fcfg', "Angus owns a dog. Angus owns a kitchen", True, False).resolve()
    #print expr
    expr.draw()
    

if __name__ == '__main__':
    main()