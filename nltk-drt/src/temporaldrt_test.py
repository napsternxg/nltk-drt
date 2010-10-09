import nltkfixtemporal
from nltk.sem.drt import AbstractDrs
import util
from temporaldrt import DrtParser
from nltk.inference.prover9 import Prover

def gr(s, recursive=False):
    return []

AbstractDrs.get_refs = gr


def main():
    cases = [
    #simple tenses with / without negation, quantified NPs
    (1,"Angus owns a car","([n,z6,s,x],[Angus{sg,m}(x), car{sg,n}(z6), own(s), AGENT(s,x), PATIENT(s,z6), overlap(n,s)])", None),
    (2, "Angus does not own a car", "([n,x],[Angus{sg,m}(x), -([z9,s],[car{sg,n}(z9), own(s), AGENT(s,x), PATIENT(s,z9), overlap(n,s)])])", None),
    (3,"Angus owned a car", "([n,t,z13,s,x],[earlier(t,n), Angus{sg,m}(x), car{sg,n}(z13), own(s), AGENT(s,x), PATIENT(s,z13), overlap(t,s)])", None),
    (4,"Angus did not own a car", "([n,t,x],[earlier(t,n), Angus{sg,m}(x), -([z16,s],[car{sg,n}(z16), own(s), AGENT(s,x), PATIENT(s,z16), overlap(t,s)])])", None),
    (5,"Angus will own a car", "([n,t,z20,s,x],[earlier(n,t), Angus{sg,m}(x), car{sg,n}(z20), own(s), AGENT(s,x), PATIENT(s,z20), overlap(t,s)])", None),
    (6,"Angus will not own a car", "([n,t,x],[earlier(n,t), Angus{sg,m}(x), -([z23,s],[car{sg,n}(z23), own(s), AGENT(s,x), PATIENT(s,z23), overlap(t,s)])])", None),
    (7,"A dog bit Angus", "([n,t,x,e,z27],[earlier(t,n), dog{sg,n}(x), Angus{sg,m}(z27), bite(e), AGENT(e,x), PATIENT(e,z27), include(t,e)])", None),
    (8,"Everyone owns a car", "([n],[(([x],[human{sg,m}(x)]) -> ([z30,s],[car{sg,n}(z30), own(s), AGENT(s,x), PATIENT(s,z30), overlap(n,s)]))])", None),
    (9,"Everyone owned a car","([n,t],[earlier(t,n), (([x],[human{sg,m}(x)]) -> ([z33,s],[car{sg,n}(z33), own(s), AGENT(s,x), PATIENT(s,z33), overlap(t,s)]))])",None),
    (10,"Angus will buy every car.","([n,t,z36],[earlier(n,t), Angus{sg,m}(z36), (([x],[car{sg,n}(x)]) -> ([e],[buy(e), AGENT(e,z36), PATIENT(e,x), include(t,e)]))])", None),
    #perfect tenses
    (11,"Angus has written a letter","([n,s,z39,e,x],[include(s,n), Angus{sg,m}(x), letter{sg,n}(z39), write(e), AGENT(e,x), PATIENT(e,z39), abut(e,s)])",None),
    (12,"Angus has not written a letter","([n,s,x],[include(s,n), Angus{sg,m}(x), -([z41,e],[letter{sg,n}(z41), write(e), AGENT(e,x), PATIENT(e,z41), abut(e,s)])])",None),
    (13,"No one has written a letter","([n,s],[include(s,n), -([x,z44,e],[human{sg,m}(x), letter{sg,n}(z44), write(e), AGENT(e,x), PATIENT(e,z44), abut(e,s)])])",None),
    (14,"Angus had died","([n,t,s,e,x],[overlap(s,t), earlier(t,n), Angus{sg,m}(x), die(e), AGENT(e,x), abut(e,s)])",None),
    (15,"Angus had not died","([n,t,s,x],[overlap(s,t), earlier(t,n), Angus{sg,m}(x), -([e],[die(e), AGENT(e,x), abut(e,s)])])",None),
    #Reference points 
    (16,"Mary kissed John. John smiled","([n,t,e,t055,e053,x,z48],[earlier(t,n), Mary{sg,f}(x), John{sg,m}(z48), kiss(e), AGENT(e,x), PATIENT(e,z48), include(t,e), earlier(t055,n), smile(e053), AGENT(e053,z48), include(t055,e053), earlier(e,e053)])",None),
    (17,"Mary will kiss John and John will smile","([n,t,e,t063,e062,x,z57],[earlier(n,t), Mary{sg,f}(x), John{sg,m}(z57), kiss(e), AGENT(e,x), PATIENT(e,z57), include(t,e), earlier(n,t063), smile(e062), AGENT(e062,z57), include(t063,e062), earlier(e,e062)])",None),
    (18,"John was away. John's car was broken", "([n,t,s,t072,s070,x,y],[earlier(t,n), John{sg,m}(x), away(s), THEME(s,x), overlap(t,s), earlier(t072,n), POSS(y,x), car{sg,n}(y), broken(s070), THEME(s070,y), overlap(t072,s070), overlap(s,s070)])",None),
    (19,"If John owns a car John is rich","([n,x],[(([z74,s],[car{sg,n}(z74), own(s), AGENT(s,x), PATIENT(s,z74), overlap(n,s)]) -> ([s079],[rich(s079), THEME(s079,x), overlap(n,s079), overlap(s,s079)])), John{sg,m}(x)])",None),
    (20,"John owns a broken car or John is rich","([n,x],[(([z82,s],[broken(z82), car{sg,n}(z82), own(s), AGENT(s,x), PATIENT(s,z82), overlap(n,s)]) | ([s087],[rich(s087), THEME(s087,x), overlap(n,s087)])), John{sg,m}(x)])",None),
    (21,"If Mia is married her husband is away",None,None)
    ]

    tester = util.Tester('file:../data/grammar.fcfg', DrtParser)
    
    #tester.test(cases)
    
    #config_prover9('/usr/share/prover9/bin')
    #config_mace4('/usr/share/prover9/bin')
    
    cases_inf = [
    # No background knowledge attached
    (1,"Mia is away","Angus owns a car","ok"),
    (2,"Mia is away","Mia is not away","inconsistent"),
    (3,"Mia is away", "Mia is away","uninformative"),
    (4,"Mia is away", "If Mia is away Angus walked","inadmissible"),
    (5,"Mia is away", "If Mia is not away Angus walked","uninformative"),
    (6,"Mia is away", "If Angus walked Mia is away","uninformative"),
    (7,"Mia is away", "If Angus walked Mia is not away","inadmissible"),
    (8,"Mia is away", "Angus walked or Mia is away","uninformative"),
    (9,"Mia is away", "Angus walked or Mia is not away","inadmissible"),
    # Background knowledge (not temporal)
    (10,"Mia owns a husband", "Mia is married","uninformative"),
    (11,"Mia owns a husband", "Mia is not married","inconsistent"),
    (12,"Mia owns a husband", "If Mia is married Angus walked", "inadmissible"),
    (13,"Mia owns a husband", "If Mia is not married Angus walked", "uninformative"),
    (14,"Mia owns a husband", "If Angus walked Mia is married", "uninformative"),
    (15,"Mia owns a husband", "If Angus walked Mia is not married","inadmissible"),
    (16,"Mia owns a husband", "Angus walked or Mia is married", "uninformative"),
    (17,"Mia owns a husband", "Angus walked or Mia is not married","inadmissible"),
    # Background knowledge (temporal)
    (18,"Mia died", "Mia will die", "inconsistent"),
    (19,"Mia died", "Mia will not die","ok"),
    (20,"Mia died", "If Angus lives Mia will die","inadmissible"),
    (21,"Mia died", "If Angus lives Mia will not die", "ok"),
    (22,"Mia died", "Angus lives or Mia will die", "inadmissible"),
    (23,"Mia died", "Angus lives or Mia will not die", "ok"),
    # Background knowledge (not temporal), multiple readings:
    (24,"Mia is away", "If Mia kissed someone her husband is away","global - ok, local - ok, intermediate - ok"),
    (25,"Mia is away", "If Mia is married Mia's husband is away","global - inadmissible, local - ok, intermediate - ok"),
    (26,"Mia is away", "Mia does not own a car or her car is red", "global - inadmissible, local - ok"),
    # Free variable check: Not implemented
    # Temporal logic
    (27,"Mia died", "Mia will die","inconsistent"),
    (28,None,"Mia lives and Mia does not live","inconsistent"),
    (29,"Jones has died", "Jones is dead","uninformative"),
    #(30,"Jones has owned a car", "Jones owns it","not working yet"),           
    ]
    
    
    bk = {'earlier' : r'all x y z.(earlier(x,y) & earlier(y,z) -> earlier(x,z)) & all x y.(earlier(x,y) -> -overlap(x,y))',
    'include' : r'all x y z.((include(x,y) & include(z,y)) -> (overlap(x,z)))',
    'die' : r'all x z y.((die(x) & AGENT(x,y) & die(z) & AGENT(z,y)) -> x = z)',   
    'husband' : r'(([t,x,y],[POSS(y,x), husband(y)]) -> ([s],[married(s),THEME(s,x),overlap(t,s)]))',
    'married' : r'(([t,s],[married(s),THEME(s,x),overlap(t,s)]) -> ([x,y],[POSS(y,x), husband(y)]))',
    'own' : r'(([s,x,y],[own(s),AGENT(s,x),PATIENT(s,y)]) -> ([],[POSS(y,x)]))',
    'POSS' : r'(([t,y,x],[POSS(y,x)]) -> ([s],[own(s),AGENT(s,x),PATIENT(s,y),overlap(t,s)]))',
   'dead' : r'(([t,s,e,x],[include(s,t),abut(e,s),die(e),AGENT(e,x)]) -> ([],[dead(s),THEME(s,x),overlap(t,s)]))'
    } 
    
    
    #tester.inference_test(cases_inf,bk)
    
    for i in tester.interpret("Mia is away", "If Mia is married Mia's husband is away",bk,True):
        if not isinstance(i, str):
            print i
    
    #expr = tester.parse('If a boy did not kiss a girl he is red', utter=True)
    
    #print expr
    #expr.draw()
    
    #for read in expr.readings():
        #print read
        #read.draw()

if __name__ == '__main__':
    main()