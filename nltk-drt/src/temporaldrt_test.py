import nltkfixtemporal
from nltk.sem.drt import AbstractDrs
import util
from temporaldrt import DrtParser

def gr(s, recursive=False):
    return []

AbstractDrs.get_refs = gr


def main():
    cases = [
    #simple tenses with / without negation, quantified NPs
    (1,"Angus owns a car","([n,z6,s],[([x],[Angus{sg,m}(x)]), car{sg,n}(z6), own(s), AGENT(s,x), PATIENT(s,z6), overlap(n,s)])", None),
    (2, "Angus does not own a car", "([n],[([x],[Angus{sg,m}(x)]), -([z9,s],[car{sg,n}(z9), own(s), AGENT(s,x), PATIENT(s,z9), overlap(n,s)])])", None),
    (3,"Angus owned a car", "([n,t,z13,s],[earlier(t,n), ([x],[Angus{sg,m}(x)]), car{sg,n}(z13), own(s), AGENT(s,x), PATIENT(s,z13), overlap(t,s)])", None),
    (4,"Angus did not own a car", "([n,t],[earlier(t,n), ([x],[Angus{sg,m}(x)]), -([z16,s],[car{sg,n}(z16), own(s), AGENT(s,x), PATIENT(s,z16), overlap(t,s)])])", None),
    (5,"Angus will own a car", "([n,t,z20,s],[earlier(n,t), ([x],[Angus{sg,m}(x)]), car{sg,n}(z20), own(s), AGENT(s,x), PATIENT(s,z20), overlap(t,s)])", None),
    (6,"Angus will not own a car", "([n,t],[earlier(n,t), ([x],[Angus{sg,m}(x)]), -([z23,s],[car{sg,n}(z23), own(s), AGENT(s,x), PATIENT(s,z23), overlap(t,s)])])", None),
    (7,"A dog bit Angus", "([n,t,x,e],[earlier(t,n), dog{sg,n}(x), ([z27],[Angus{sg,m}(z27)]), bite(e), AGENT(e,x), PATIENT(e,z27), include(t,e)])", None),
    (8,"Everyone owns a car", "([n],[(([x],[human{sg,m}(x)]) -> ([z30,s],[car{sg,n}(z30), own(s), AGENT(s,x), PATIENT(s,z30), overlap(n,s)]))])", None),
    (9,"Everyone owned a car","([n,t],[earlier(t,n), (([x],[human{sg,m}(x)]) -> ([z33,s],[car{sg,n}(z33), own(s), AGENT(s,x), PATIENT(s,z33), overlap(t,s)]))])",None),
    (10,"Angus will buy every car.","([n,t],[earlier(n,t), ([z36],[Angus{sg,m}(z36)]), (([x],[car{sg,n}(x)]) -> ([e],[buy(e), AGENT(e,z36), PATIENT(e,x), include(t,e)]))])", None),
    #perfect tenses
    (11,"Angus has written a letter","([n,s,z39,e],[include(s,n), ([x],[Angus{sg,m}(x)]), letter{sg,n}(z39), write(e), AGENT(e,x), PATIENT(e,z39), abut(e,s)])",None),
    (12,"Angus has not written a letter","([n,s],[include(s,n), ([x],[Angus{sg,m}(x)]), -([z41,e],[letter{sg,n}(z41), write(e), AGENT(e,x), PATIENT(e,z41), abut(e,s)])])",None),
    (13,"No-one has written a letter","([n,s],[include(s,n), -([x,z44,e],[human{sg,m}(x), letter{sg,n}(z44), write(e), AGENT(e,x), PATIENT(e,z44), abut(e,s)])])",None),
    (14,"Angus had died","([n,t,s,e],[overlap(s,t), earlier(t,n), ([x],[Angus{sg,m}(x)]), die(e), AGENT(e,x), abut(e,s)])",None),
    (15,"Angus had not died","([n,t,s],[overlap(s,t), earlier(t,n), ([x],[Angus{sg,m}(x)]), -([e],[die(e), AGENT(e,x), abut(e,s)])])",None),
    #Reference points 
    (16,"Mary kissed John. John smiled","([n,t,e,t055,e053],[earlier(t,n), ([x],[Mary{sg,f}(x)]), ([z48],[John{sg,m}(z48)]), kiss(e), AGENT(e,x), PATIENT(e,z48), include(t,e), earlier(t055,n), ([z52],[John{sg,m}(z52)]), smile(e053), AGENT(e053,z52), include(t055,e053), earlier(e,e053)])",None),
    (17,"Mary will kiss John and John will smile","([n,t,e,t063,e062],[earlier(n,t), ([x],[Mary{sg,f}(x)]), ([z57],[John{sg,m}(z57)]), kiss(e), AGENT(e,x), PATIENT(e,z57), include(t,e), earlier(n,t063), ([z61],[John{sg,m}(z61)]), smile(e062), AGENT(e062,z61), include(t063,e062), earlier(e,e062)])",None),
    (18,"John was away. John's car was broken", "([n,t,s,t072,s070],[earlier(t,n), ([x],[John{sg,m}(x)]), away(s), THEME(s,x), overlap(t,s), earlier(t072,n), ([y],[([z69],[John{sg,m}(z69)]), POSS(z69,y), car{sg,n}(y)]), broken(s070), THEME(s070,y), overlap(t072,s070), overlap(s,s070)])",None),
    (19,"If John owns a car John is rich","([n],[(([z74,s],[([x],[John{sg,m}(x)]), car{sg,n}(z74), own(s), AGENT(s,x), PATIENT(s,z74), overlap(n,s)]) -> ([s079],[([x],[John{sg,m}(x)]), rich(s079), THEME(s079,x), overlap(n,s079), overlap(s,s079)]))])",None),
    (20,"John owns a broken car or John is rich","([n],[(([z81,s],[([x],[John{sg,m}(x)]), broken(z81), car{sg,n}(z81), own(s), AGENT(s,x), PATIENT(s,z81), overlap(n,s)]) | ([s086],[([x],[John{sg,m}(x)]), rich(s086), THEME(s086,x), overlap(n,s086)]))])",None)
    ]

    tester = util.Tester('file:../data/grammar.fcfg', DrtParser)
    
    tester.test(cases)
    
    #expr = tester.parse('Angus owns a car', utter=True)
    
    #print expr
    #expr.draw()
    
    #for read in expr.readings():
        #print read
        #read.draw()

if __name__ == '__main__':
    main()