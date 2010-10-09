from util import Tester

TESTWN = True # True if we test wn_presupp_drt, False otherwise

if TESTWN: 
    from wn_presupp_drt import DrtParserWN as DrtParser
else:
    from temporaldrt import DrtParser


# Nltk fix
import nltkfixtemporal
from nltk.sem.drt import AbstractDrs
def gr(s, recursive=False):
    return []
AbstractDrs.get_refs = gr

def test(tester):

    #expr = tester.parse("Mia is away. If Mia is married, John is dead.", utter=True)
    #expr = tester.parse("If a girl owns a dog, the girl that owns the dog walks", utter=True)
    #expr = tester.parse("If a girl owns a dog, the baroness that bit a car lives", utter=True)
    #expr = tester.parse("If a dead baroness walks, the dead girl lives", utter=True) # Global accommodation and intermediate binding. Shouldn't repeat 'dead' when binds. OK.
    #expr = tester.parse("If Angus owns a child, his child is away", utter=True) #Also: the child that likes him, the child that likes himself
    #expr = tester.parse("Mia is away. If Mia kissed someone, her husband is away.", utter=True) # Global accommodation + 'husband' is bound to 'human'. Hmm.
    
    # Test these with wn_presupp_drt !
    #expr = tester.parse("Angus owns a hammer. Angus owns a garden. He likes the tool.", utter=True) # Should be one reading (tool=hammer). OK.
    #expr = tester.parse("The garden is dead. The car is broken.", utter=True) # No binding. OK.
    #expr = tester.parse("A dog needs a kitchen. If a donkey dances, the animal is stupid.", utter=True) # Animal=dog or animal=donkey. OK.
    #expr = tester.parse("Fido bites a farmer. If a donkey dances, the animal is stupid.", utter=True) # Animal=Fido or animal=donkey. OK.
    #expr = tester.parse("John hates the student. The student is upset.", utter=True) # Bind to student. OK. But it also binds to "John"
    #expr = tester.parse("If Mary does not like the president, she will not vote him.", utter=True) # Although 'child', 'letter' and 'dog' are all neuter, 'the dog' doesn't bind to either 'child' or 'kitchen'
    #expr = tester.parse("Mary likes the president or she will not vote him.", utter=True)
    expr = tester.parse("Mary likes John's car or she hates his car.", utter=True)
    
    
    #########
    #parser = DrtParser()
    #expr = parser.parse("([n,x],[(([z6,s],[child{sg,m}(z6), own(s), AGENT(s,x), PATIENT(s,z6), overlap(n,s)]) -> ([s019,t09],[DEF([z20],[POSS(z20,z6), child{sg,m}(z20)]), away(s019), THEME(s019,z20), LOCPRO(t09)])), Angus{sg,m}(x)])")
    #expr = parser.parse("([n,x],[(([z6,s],[child{sg,m}(z6), own(s), AGENT(s,x), PATIENT(s,z6), overlap(n,s)]) -> ([s019,t09],[DEF([z20],[POSS(z20,x), child{sg,m}(z20)]), away(s019), THEME(s019,z20), LOCPRO(t09)])), Angus{sg,m}(x)])")
    # If John has a child, the child that likes him (him = the child in the antecedent of the impl. cond) is away.
    #expr = parser.parse("([n,x],[(([z6,s],[child{sg,m}(z6), own(s), AGENT(s,x), PATIENT(s,z6), overlap(n,s)]) -> ([s019,t09],[DEF([z20, s100],[child{sg,m}(z20), like(s100), AGENT(s100,z20), PATIENT(s100,z6)]), away(s019), THEME(s019,z20), LOCPRO(t09)])), Angus{sg,m}(x)])")
    #########
    
#    for cond in expr.conds: 
#        print "CONDITION", type(cond), cond
#        try: print "\t", type(cond.argument)
#        except:pass

    expr.draw()
    r = expr.readings(verbose=True)
    print len(r)
    for reading in r:
        reading.draw()

if __name__ == '__main__':
    tester = Tester('file:../data/grammar.fcfg', DrtParser)
    test(tester)