from nltk.inference.prover9 import Prover9Command
from nltk.inference.mace import MaceCommand
from nltk import load_parser
from temporaldrt import DrtParser
from nltk.sem.drt import AbstractDrs

import nltkfixtemporal

def gr(s, recursive=False):
    return []

AbstractDrs.get_refs = gr

"""
As Mace looks for a minimal solution, those are the things we need to have so that 
models make sense:

    (i) the basic types distinction is lost in Mace. It needs to be reintroduced
     in the background so that the following DRS-conditions are added into the DRSs
     in which a referent of a certain basic type appears: e.g. DRS([x,e,t],[]) should,
     at the point the inference tools are called, carry conditions
     DRS([x,e.t],[individual(x),event(e),time(t)]).
     
    (ii) at each call of the inference tools, the following meaning postulate should
     be added all x.((individual(x) -> -(eventuality(x) | time(x))) & (eventuality(t) ->
     -time(x)) & (state(x) -> (eventuality(x) & -event(x))) & (event(x) -> eventuality(x))).
     
done (iii) John in John(x) is no longer treated as a predicate: the condition is converted
    into John = x when the fol() method is called. 
     
    (iv) presupposition that all individuals mentioned in a discourse are uniquely
     and disjointly identified by their names. This could be done with following
     DRS-condition: DRS([x,y],[Bill(x),Claire(y)]) turns into 
     DRS([x,y],[x=Bill, y=Claire, -(x=y)]). In other words, for each pair of proper name
     carrying individuals x and y, it should be stated in a DRS from which both are
     acceptable that -(x=y). This could be added when the inference tools are called.
"""

if __name__ == "__main__":
    parser = load_parser('file:../data/tenseaspect.fcfg', logic_parser=DrtParser())
    trees = parser.nbest_parse('Angus does not own a dog'.split())
    expr = trees[0].node['SEM'].resolve()
    parse = expr.fol()
    
    print "Temporal DRT Expression in FOL: %s \n" % parse
    
    m = MaceCommand(None, [parse])
    print "Mace: %s \n\n %s \n" % (m.build_model(), m.valuation) 
    
    p = Prover9Command(parse, []).prove()
    print "Prover9: %s: %s" % (parse, p)
    
    expr.draw()
            
