from nltk.inference.prover9 import Prover9Command, Prover9
from nltk.inference.mace import MaceCommand, Mace
from anaphora import DrtParser
from nltk.sem.drt import AbstractDrs
from nltk import LogicParser
from nltk.sem.logic import AndExpression, NegatedExpression
from nltk.inference.api import ParallelProverBuilderCommand, Prover, ModelBuilder
import temporaldrt as drt
#import anaphora as drt
import util
from threading import Thread
import os

import nltkfixtemporal

def gr(s, recursive=False):
    return []

AbstractDrs.get_refs = gr

"""
As Mace looks for a minimal solution, those are the things we need to have so that 
models make sense:

done    (i) the basic types distinction is lost in Mace. It needs to be reintroduced
     in the background so that the following DRS-conditions are added into the DRSs
     in which a referent of a certain basic type appears: e.g. DRS([x,e,t],[]) should,
     at the point the inference tools are called, carry conditions
     DRS([x,e.t],[individual(x),event(e),time(t)]).
     
done    (ii) at each call of the inference tools, the following meaning postulate should
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
    
Admissibility Constraints:

Prover - negative check for consistency.
Prover - negative check for informativity.
Builder - positive check for consistency.
Builder - positive check for informativity.

Global Constraints:

Global Consistency: On adding a new reading to the previous discourse, give NegatedExpression
    of the resulting discourse to the prover. If it returns True, the discourse is inconsistent.
    Give the resulting discourse to the builder. If it returns a model, the discourse is
    consistent.
    
Global Informativity: Give a new reading to the prover as the goal and the previous discourse
    as an assumption (meaning postulates and background knowledge should be added as assumptions
    as well). If the prover returns True, then the resulting discourse is uninformative.
    Conjoin NegatedExpression of the new reading with the previous discourse and give the
    resulting formula to the builder. If it returns a model, the new reading is informative.
    [if (phi -> psi) is a theorem, then -(phi -> psi) is a contradiction and could not
    have a model. Thus, if there is a model, (phi -> psi) is not a theorem.]
    
Local Constraints (Kartunen's Filters):

    Superordinate DRSs should entail neither a DRS nor its negation.  
    Generate a list of ordered pairs such that the first element of the pair is a FOL
    expression representing superordinate DRSs and the second is a subordinate DRS to
    be checked on entailment:
    
        (i) From DrtNegatedExpression -K, if K is a DRS, take K and put it in the second
        place of the ordered pair. Remove the DrtNegatedExpression and place the rest in
        the first place of the order pair. 
        
        (ii) From a DrtImpCondition K->L, provided that both are DRSs, create two ordered
        pairs: (a) Put the antecedent DRS K into the second place, remove the DrtImpCondition
        and put the result into the first place of the ordered pair; (b) Put the consequent
        DRS L into the second place, merge the antecedent DRS K globally (??) and put the
        result into the first place of the ordered pair.
        
        (iii) From a DrtOrExpression K | L, provided that both are DRSs, create two ordered
        pairs: Put each of the disjuncts into the second place of each pair, remove the
        DrtORExpression and put the result into the first place of that pair. 
"""


def inference_check(expr, background_knowledge=False):
    """General function for all kinds of inference-based checks:
    consistency, global and local informativity"""
    
    assert isinstance(expr, drt.DRS), "Expression %s is not a DRS"
    
    expression = expr.deepcopy()
    print "first version: ",expression
    
    def remove_temporal_conds(e):
    
        for cond in list(e.conds):
            if isinstance(cond, drt.DrtEventualityApplicationExpression) and \
            isinstance(cond.function, drt.DrtEventualityApplicationExpression) and \
            cond.function.function.variable.name in drt.DrtTokens.TEMP_CONDS:
                e.conds.remove(cond)
                
            elif isinstance(cond, drt.DRS):
                remove_temporal_conds(cond)
                
            elif isinstance(cond, drt.DrtNegatedExpression) and \
                isinstance(cond.term, drt.DRS):
                remove_temporal_conds(cond.term)
                
            elif isinstance(cond, drt.DrtBooleanExpression) and \
                isinstance(cond.first, drt.DRS) and isinstance(cond.second, drt.DRS): 
                remove_temporal_conds(cond.first)
                remove_temporal_conds(cond.second)
#    
#    class InferenceTool():
#        def __init__(self, expression):
#            self.tool = ParallelProverBuilderCommand(Prover(), ModelBuilder())
#        
#        def run(self):
#            return self.tool.build_model(True)
#            
    
    class Prover(Thread):
        """Wrapper class for Prover9"""
        def __init__(self,expression):
            Thread.__init__(self)
            self.prover = Prover9Command(expression,timeout=60)
            self.result = None
        
        def run(self):
            self.result = self.prover.prove(verbose=False)
            
        
    class Builder(Thread):
        """Wrapper class for Mace"""
        def __init__(self,expression):
            Thread.__init__(self)              
            self.builder = MaceCommand(None,[expression],max_models=50)
            self.result = None 
        
        def run(self):
            self.result = self.builder.build_model(verbose=True) 

#    def check(expression):
#        os.system('killall mace4')
#        if background_knowledge:
#            p = Prover(NegatedExpression(AndExpression(expression,background_knowledge)))
#            m = Builder(AndExpression(expression,background_knowledge))
#        else:
#            p = Prover(NegatedExpression(expression))
#            m = Builder(expression)
#    
#        print p
#        print m
#        p.start()
#        m.start()
#        
#        while p.is_alive() and m.is_alive():
#            pass
#        if m.is_alive():
#            """If builder is still running, there is a high
#            likelihood of the formula to be a contradiction.
#            """
#            print "prover check:",p, p.result
#            return not p.result
##            os.system('killall mace4')
#            """If builder returned, return its value"""
#        print "builder check:",m, m.builder.valuation
#        return m.result  
    
    def check(expression):
        if background_knowledge:
            expr = NegatedExpression(AndExpression(expression,background_knowledge))
        else:
            expr = NegatedExpression(expression)
            
        return ParallelProverBuilderCommand(Prover9(), Mace(),expr).build_model()


#    def check(expression):
#        if background_knowledge:
#            inference_tool = InferenceTool(NegatedExpression(AndExpression(expression,background_knowledge)))
#        else:
#            inference_tool = InferenceTool(NegatedExpression(expression),True)
#    
#        return inference_tool.run()
      
    
    def consistency_check(expression):
        """1. Consistency check"""
        print "consistency check initiated\n", expression
        return check(expression)
        
    
    def informativity_check(expression):
        """2. Global informativity check"""
        print "informativity check initiated"
        local_check = []
        for cond in expression.conds:
            if isinstance(cond, drt.DRS) and \
            not isinstance(cond, drt.PresuppositionDRS):
                """New discourse in the previous discourse"""
                temp = (expression.conds[:expression.conds.index(cond)]+
                        [drt.DrtNegatedExpression(cond)]+
                    expression.conds[expression.conds.index(cond)+1:])
                print "new discourse %s found in %s" % (cond,expression)
                print "expression for global check", expression.__class__(expression.refs,temp)
                if not check(expression.__class__(expression.refs,temp)):
                    """new discourse is uninformative"""
                    return False
                else:
                    temp = (expression.conds[:expression.conds.index(cond)]+
                    expression.conds[expression.conds.index(cond)+1:])
                    """Put sub-DRS into main DRS and start informativity check"""
                    return informativity_check(prenex_normal_form(expression.__class__(expression.refs,temp),cond))
                
                """generates tuples for local admissibility check"""

            elif isinstance(cond, drt.DrtOrExpression) and \
                isinstance(cond.first, drt.DRS) and isinstance(cond.second, drt.DRS):
                temp = (expression.conds[:expression.conds.index(cond)]+
                    expression.conds[expression.conds.index(cond)+1:])
                local_check.append((expression.__class__(expression.refs,temp),cond.first))
                local_check.append((expression.__class__(expression.refs,temp),cond.second))
    
            elif isinstance(cond, drt.DrtImpExpression) and \
                isinstance(cond.first, drt.DRS) and isinstance(cond.second, drt.DRS):
                temp = (expression.conds[:expression.conds.index(cond)]+
                    expression.conds[expression.conds.index(cond)+1:])
                local_check.append((expression.__class__(expression.refs,temp),cond.first))
                local_check.append((drt.ConcatenationDRS(expression.__class__(expression.refs,temp),
                                                         cond.first).simplify(),cond.second))


        if not local_check == []:
            return local_informativity_check(local_check)
        else:
            print "Expression %s is informative" % expression
            return True
        
    def local_informativity_check(check_list):
        """3. Local admissibility constraints"""
        print "local admissibility check initiated:", check_list

        for main,sub in check_list:
            assert isinstance(main, drt.DRS), "Expression %s is not a DRS"
            assert isinstance(sub, drt.DRS), "Expression %s is not a DRS"

            if not check(main.__class__(main.refs,main.conds+[drt.DrtNegatedExpression(sub)])):
                print "main %s entails sub %s" % (main,sub)
                #return False
                raise Inference_check("New discourse is inadmissible due to local uninformativity:\n\n%s entails %s" % (main, sub))
                
            elif not check(main.__class__(main.refs,main.conds+[sub])):
                print "main %s entails neg of sub %s" % (main,sub)
                #return False
                raise Inference_check("New discourse is inadmissible due to local uninformativity:\n\n%s entails the negation of %s" % (main, sub))
                
        print "main %s does not entail sub %s nor its negation" % (main,sub)
        return True                

    remove_temporal_conds(expression)
    print "Second version: ",expression
    
    if not consistency_check(expression):
            print "Expression %s is inconsistent" % expression
            #return None
            raise Inference_check("New discourse is inconsistent on the following interpretation:\n\n%s" % expression)
    
    if not informativity_check(expression):
            print "Expression %s is uninformative" % expression
            #return None
            
            raise Inference_check("New expression is uninformative on the following interpretation:\n\n%s" % expression)
 
    
    for cond in expr.conds:
        """Merge DRS of the new expression into the previous discourse"""
        if isinstance(cond, drt.DRS):
            return prenex_normal_form(expr.__class__(expr.refs,
                    expression.conds[:expr.conds.index(cond)]+
                    expression.conds[expr.conds.index(cond)+1:]), cond)
    return expr


class Inference_check(Exception):
    def __init__(self, value):
        self.value = value
        
    def __str__(self):
        return repr(self.value)


def prenex_normal_form(expression,subexpression):
    """Combines sub-DRS with superordinate DRS"""

    assert isinstance(subexpression, drt.DRS), "Expression %s is not a DRS" % subexpression
    assert isinstance(expression, drt.DRS), "Expression %s is not a DRS" % expression

    subexpr = subexpression.__class__(subexpression.refs,subexpression.conds)
    expr = expression.__class__(expression.refs, expression.conds)

    for ref in subexpression.refs:
        if ref in expression.refs:
            newref = drt.DrtVariableExpression(drt.unique_variable(ref))
            subexpr = subexpr.replace(ref,newref,True)
    
    return expr.__class__(expr.refs+subexpr.refs,expr.conds+subexpr.conds)


  
def get_bk(drs, dictionary):
    """Collects background knowledge relevant for a given expression.
    DrtConstantExpression variable names are used as keys"""
    
    assert isinstance(drs, drt.DRS), "Expression %s is not a DRS" % drs
    assert isinstance(dictionary, dict), "%s is not a dictionary" % dictionary
    bk_list = []
    
    for cond in drs.conds:
        if isinstance(cond, drt.DrtApplicationExpression):
            if isinstance(cond.function, drt.DrtConstantExpression):
                bk_formula = dictionary.get(cond.function.variable.name,False)
               
            elif isinstance(cond.function, drt.ApplicationExpression) and \
             isinstance(cond.function.function, drt.DrtConstantExpression):
                bk_formula = dictionary.get(cond.function.function.variable.name,False)
               
            if bk_formula:
                bk_list.append(bk_formula)
                
        elif isinstance(cond, drt.DRS):
            bk_list.extend(get_bk(cond,dictionary))
            
        elif isinstance(cond, drt.DrtNegatedExpression) and \
            isinstance(cond.term, drt.DRS):
            bk_list.extend(get_bk(cond.term,dictionary))
            
        elif isinstance(cond, drt.DrtBooleanExpression) and \
            isinstance(cond.first, drt.DRS) and isinstance(cond.second, drt.DRS):
            bk_list.extend(get_bk(cond.first,dictionary))
            bk_list.extend(get_bk(cond.second,dictionary))
            
    
    return list(set(bk_list))


def interpret(expr_1, expr_2, bk=False):
    """Interprets a new expression with respect to some previous discourse 
    and background knowledge. The function first generates relevant background
    knowledge and then performs inference check on readings generated by 
    the readings() method. It returns a list of admissible interpretations in
    the form of DRSs.
    
    Could be enlarged to take a grammar argument and a parser argument"""
    
    try:
        assert isinstance(expr_1, str), "Expression %s is not a string" % expr_1
        assert isinstance(expr_2, str), "Expression %s is not a string" % expr_2
        if not bk:
            assert isinstance(bk, dict), "Background knowledge is not in dictionary format"
    except AssertionError as e:
        print e
        return "\nDiscourse uninterpretable"
    else:
            
        parser_obj = DrtParser()
        buffer = parser_obj.parse(r'\Q P.(DRS([],[P])+Q)')
        tester = util.Tester('file:../data/grammar.fcfg', DrtParser)
        try:
            try:
                discourse = tester.parse(expr_1, utter=True)
                
                expression = tester.parse(expr_2, utter=False)
                
                #discourse = parser_obj.parse(r'DRS([x,s],[Mia(x),die(x)])')
                #expression = parser_obj.parse(r'DRS([],[-DRS([x,s],[Mia(x),die(x)])])')
                
                #discourse = parser_obj.parse(r'DRS([x],[Mia(x),die(x)])')
                #inconsistent
                #expression = parser_obj.parse(r'DRS([x],[Mia(x),-DRS([],[die(x)])])')
                #globally uninformative
                #expression = parser_obj.parse(r'DRS([],[DRS([x],[Mia(x),-DRS([],[die(x)])]) -> DRS([y],[Angus(y),live(y)])])')
                #locally inadmissible
                #expression = parser_obj.parse(r'DRS([],[DRS([x],[Mia(x),die(x)]) -> DRS([y],[Angus(y),live(y)])])')
                #globally uninformative
                #expression = parser_obj.parse(r'DRS([],[DRS([y],[Angus(y),live(y)]) -> DRS([x],[Mia(x),die(x)])])')
                #locally inadmissible
                #expression = parser_obj.parse(r'DRS([],[DRS([y],[Angus(y),live(y)]) -> DRS([x],[Mia(x),-DRS([],[die(x)])])])')
                
                #for ref in expression.get_refs():
                #    if ref in discourse.get_refs():
                #        newref = drt.DrtVariableExpression(drt.unique_variable(ref))
                #        expression = expression.replace(ref,newref,True)
                
                new_discourse = drt.DrtApplicationExpression(drt.DrtApplicationExpression(buffer,discourse),expression).simplify()
                
                #new_discourse = parser_obj.parse(r'DRS([x,e],[Mia(x),AGENT(e,x),die(e),DRS([e01],[AGENT(e01,x),die(e01)]) ])')
                #new_discourse = parser_obj.parse(r'DRS([n,e,t,x],[Mia(x),AGENT(e,x),die(e),earlier(e,n),DRS([e01],[AGENT(e01,x),die(e01),earlier(e01,n)]) ])')
                #([n,t,e,x],[([t09,e],[earlier(t09,n), die(e), AGENT(e,x), include(t09,e), REFER(e)]), earlier(t,n), die(e), AGENT(e,x), include(t,e), REFER(e), Mia{sg,f}(x)])
                
                
                
                background_knowledge = None
                
                lp = LogicParser().parse
                try:
                    print get_bk(new_discourse, bk)
                    for formula in get_bk(new_discourse, bk):
                        if background_knowledge:
                            background_knowledge = AndExpression(background_knowledge, lp(formula))
                        else:
                            background_knowledge = lp(formula)
     
                    interpretations = []
                    try:
                        for reading in new_discourse.readings():
                            interpretation = inference_check(reading, background_knowledge)
                            if interpretation:
                                interpretations.append(interpretation)
                        
                        return interpretations
                    
                    except Inference_check as e:
                        print "Note:", e.value
                        
                except AssertionError as e:
                    print e
                
            except IndexError:
                print "Input sentences only!"
            
        except ValueError as e:
            print "Error:", e
    
        return "\nDiscourse uninterpretable"

    
    

def test_1():
    
    #with ontology
    bk_0 = {'earlier' : r'all x y z.(earlier(x,y) & earlier(y,z) -> earlier(x,z)) & all x y.(earlier(x,y) -> -overlap(x,y))',
          'include' : r'all x y z.((include(x,y) & include(z,y)) -> (overlap(x,z)))',
          'die' : r'all x z y.((die(x) & AGENT(x,y) & die(z) & AGENT(z,y)) -> x = z)',
          'dead' : r'all x y z.((die(x) & AGENT(x,z) & abut(x,y)) -> (dead(y) & THEME(y,z)))',
          'live' : r'all x y z v.((overlap(x,y) & live(y) & AGENT(x,z)) <-> -(overlap(x,v) & dead(v) & THEME(v,z)))',
          'married' : r'all x y z v.((married(x) & THEME(x,y)) <-> (own(z) & AGENT(z,y) & PATIENT(z,v) & husband(v)))',
          'husband' : r'all x y z v.((married(x) & THEME(x,y)) <-> (own(z) & AGENT(z,y) & PATIENT(z,v) & husband(v)))',
          'individual' : r'all x.((individual(x) -> -(eventuality(x) | time(x))) & (eventuality(t) -> -time(x)) & (state(x) -> (eventuality(x) & -event(x))) & (event(x) -> eventuality(x)))',
          'time' : r'all x.((individual(x) -> -(eventuality(x) | time(x))) & (eventuality(t) -> -time(x)) & (state(x) -> (eventuality(x) & -event(x))) & (event(x) -> eventuality(x)))',
          'state' : r'all x.((individual(x) -> -(eventuality(x) | time(x))) & (eventuality(t) -> -time(x)) & (state(x) -> (eventuality(x) & -event(x))) & (event(x) -> eventuality(x)))',
          'event' : r'all x.((individual(x) -> -(eventuality(x) | time(x))) & (eventuality(t) -> -time(x)) & (state(x) -> (eventuality(x) & -event(x))) & (event(x) -> eventuality(x)))'
          }
    
    
    bk_1 = {'earlier' : r'all x y z.(earlier(x,y) & earlier(y,z) -> earlier(x,z)) & all x y.(earlier(x,y) -> -overlap(x,y))',
          'include' : r'all x y z.((include(x,y) & include(z,y)) -> (overlap(x,z)))',
          'die' : r'all x z y.((die(x) & AGENT(x,y) & die(z) & AGENT(z,y)) -> x = z)',
          'live' : r'all x y z v.((overlap(x,y) & live(y) & AGENT(x,z)) <-> -(overlap(x,v) & dead(v) & THEME(v,z)))',
          'dead' : r'all x y z.((die(x) & AGENT(x,z) & abut(x,y)) -> (dead(y) & THEME(y,z)))',
          'married' : r'all x y z v.((married(x) & THEME(x,y)) <-> (own(z) & AGENT(z,y) & PATIENT(z,v) & husband(v)))',
          'husband' : r'all x y z v.((married(x) & THEME(x,y)) <-> (own(z) & AGENT(z,y) & PATIENT(z,v) & husband(v)))'}
  
    #parser_obj = DrtParser()
    #buffer = parser_obj.parse(r'\Q P.(DRS([],[P])+Q)')
    #tester = util.Tester('file:../data/grammar.fcfg', DrtParser)
    #discourse = tester.parse("Angus owns a red car", utter=True)
    #expression = tester.parse("Mia owns a car", utter=False)
            
    #new_discourse = drt.DrtApplicationExpression(drt.DrtApplicationExpression(buffer,discourse),expression).simplify()
                
    #for read in new_discourse.readings():
        #read.draw()
    #    print read
    #    interpret = inference_check(read)
    #    if interpret:
    #        print interpret
            #interpret.draw()
    
    
    for interpretation in interpret("Mia died", "if Mia died a girl walked", bk_1):
        if not isinstance(interpretation, str):
            print interpretation
            #interpretation.draw()
    
            """
            Consistency check: Try "Mia died" and "Mia will die"
            
            Global informativity check: Try "Mia owns a red car" and "Mia owns a car"
            
            Local admissibility check: Try "Mia has died" and "If Mia is dead Angus lives"
                or "Mia is dead or Angus lives" or "If Mia is not dead Angus lives"        
            """
        #TODO: As it goes deep into DRS it hits unresolved presuppositional DRS and if
        #a name is repeated twice, it will prove uninformativity, as encoded.
        #Presuppositional DRS should be resolved to have a reasonable inference check.
        #Quick fix added.
        
        #TODO: Temporal conditions linking clauses break down informativity check!
        #Something needs to be done...
        #
        #If I comment the readings method of FindEventualityExpression class, the following 
        #discourses come out as expected:
        #
        #"Mia died", "If Mia died Angus walked"   -- locally inadmissible
        #
        #"Mia died", "If Angus walked Mia died"   -- globally uninformative
        #     
        
def test_2():
    parser_obj = DrtParser()
    #parser = LogicParser().parse
    #expression = parser(r'((p -> q) & ((p & q) -> m)) <-> ((p -> q) & (p -> (m & q)))')
    #expression = parser_obj.parse(r'DRS([n,e,x,t],[Mia(x),die(e),AGENT(e,x),include(t,e),earlier(t,n),-DRS([t02,e01],[die(e01),AGENT(e01,x),include(t02,e01),earlier(t02,n)]) ])')
    expression = parser_obj.parse(r'([n,t,e,x],[-([t09,e],[earlier(t09,n), die(e), AGENT(e,x), include(t09,e), REFER(e)]), earlier(t,n), die(e), AGENT(e,x), include(t,e), REFER(e), Mia{sg,f}(x)])')
    #expression = parser(r'DRS([],[die(Mia),-(DRS([],[die(Mia)])])')
    print expression
    #expression = parser('m')
    #assumption = parser('m')
    prover = Prover9Command(NegatedExpression(expression),timeout=60)
    print prover.prove()
      

def test_3():
           
    parser_obj = DrtParser()       
    expression = parser_obj.parse(r'([n,t,e,x],[-([t09,e],[earlier(t09,n), die(e), AGENT(e,x), include(t09,e), REFER(e)]), earlier(t,n), die(e), AGENT(e,x), include(t,e), REFER(e), Mia{sg,f}(x)])')
    print expression
    print ParallelProverBuilderCommand(Prover9(), Mace(),expression).build_model()
    
if __name__ == "__main__":
    test_1()
     
