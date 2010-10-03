from nltk.inference.prover9 import Prover9Command, Prover9
#from nltk.inference.mace import MaceCommand, Mace
from temporaldrt import DrtParser
from nltk.sem.drt import AbstractDrs
from nltk import LogicParser
from nltk.sem.logic import AndExpression, NegatedExpression, ParseException
#from nltk.inference.api import ParallelProverBuilderCommand, Prover, ModelBuilder
from theorem import Builder, Prover 
import temporaldrt as drt
import util
from util import local_DrtParser
#from threading import Thread
#import os

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

    def check(expression):
        #os.system('killall mace4')
        if background_knowledge:
            print "check on:", NegatedExpression(AndExpression(expression.fol(),background_knowledge))
            p = Prover(NegatedExpression(AndExpression(expression,background_knowledge)))
            m = Builder(AndExpression(expression,background_knowledge))
        else:
            p = Prover(NegatedExpression(expression))
            m = Builder(expression)
    
        print p
        print m
        p.start()
        m.start()
        result = None
        
        while p.is_alive() and m.is_alive():
            pass
        if m.is_alive():
            """If builder is still running, there is a high
            likelihood of the formula to be a contradiction.
            """
            print "prover check:",p, p.result
            result = not p.result
            
            while not m.builder._modelbuilder.isrunning():
                pass
            
            m.builder._modelbuilder.terminate()
            return not p.result
            """If builder returned, return its value"""

        print "builder check:",m, m.builder.valuation
        while not p.prover._prover.isrunning():
                pass
        result = m.result
        p.prover._prover.terminate()
        return result
    
#    def check(expression):
#        if background_knowledge:
#            expr = NegatedExpression(AndExpression(expression,background_knowledge))
#        else:
#            expr = NegatedExpression(expression)
#            
#        return ParallelProverBuilderCommand(Prover9(), Mace(),expr).build_model()
      
    
    def consistency_check(expression):
        """1. Consistency check"""
        print "consistency check initiated\n", expression
        return check(expression)
        
    
    def informativity_check(expression):
        """2. Global informativity check"""
        print "informativity check initiated"
        local_check = []
        for cond in drt.ReverseIterator(expression.conds):
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
                raise InferenceCheckException("New discourse is inadmissible due to local uninformativity:\n\n%s entails %s" % (main, sub))
                
            elif not check(main.__class__(main.refs,main.conds+[sub])):
                print "main %s entails neg of sub %s" % (main,sub)
                #return False
                raise InferenceCheckException("New discourse is inadmissible due to local uninformativity:\n\n%s entails the negation of %s" % (main, sub))
                
        print "main %s does not entail sub %s nor its negation" % (main,sub)
        return True                

    remove_temporal_conds(expression)
    print "Second version: ",expression
    
    if not consistency_check(expression):
            print "Expression %s is inconsistent" % expression
            #return None
            raise InferenceCheckException("New discourse is inconsistent on the following interpretation:\n\n%s" % expression)
    
    if not informativity_check(expression):
            print "Expression %s is uninformative" % expression
            #return None
            
            raise InferenceCheckException("New expression is uninformative on the following interpretation:\n\n%s" % expression)
 
    
    for cond in expr.conds:
        """Merge DRS of the new expression into the previous discourse"""
        if isinstance(cond, drt.DRS):
            return prenex_normal_form(expr.__class__(expr.refs,
                    expression.conds[:expr.conds.index(cond)]+
                    expression.conds[expr.conds.index(cond)+1:]), cond)
    return expr


class InferenceCheckException(Exception):
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
    
    if expr_1 and not isinstance(expr_1, str):
        return "\nDiscourse uninterpretable. Expression %s is not a string" % expr_1
    elif not isinstance(expr_2, str):
        return "\nDiscourse uninterpretable. Expression %s is not a string" % expr_2
    elif not bk and not isinstance(bk, dict):
        return "\nDiscourse uninterpretable. Background knowledge is not in dictionary format"
        
    else:
            
        parser_obj = DrtParser()
        buffer = parser_obj.parse(r'\Q P.(Q+DRS([],[P]))')
        #buffer = parser_obj.parse(r'\Q P.(NEWINFO([],[P])+Q)')
        tester = util.Tester('file:../data/grammar.fcfg', DrtParser)
        try:
            try:
                if expr_1:
                    discourse = tester.parse(expr_1, utter=True)
                    
                    expression = tester.parse(expr_2, utter=False)
                                        
                    for ref in expression.get_refs():
                        if ref in discourse.get_refs():
                            newref = drt.DrtVariableExpression(drt.unique_variable(ref))
                            expression = expression.replace(ref,newref,True)
                    
                    new_discourse = drt.DrtApplicationExpression(drt.DrtApplicationExpression(buffer,discourse),expression).simplify()
                
                else: new_discourse = tester.parse(expr_2, utter=True)
                                   
                background_knowledge = None
                
                lp = LogicParser().parse
                
                #in order for bk in DRT-language to be parsed without REFER
                #this affects inference
                parser_obj = local_DrtParser()
                #should take bk in both DRT language and FOL
                try:
                    print get_bk(new_discourse, bk)
                    for formula in get_bk(new_discourse, bk):
                        if background_knowledge:
                            try:
                                background_knowledge = AndExpression(background_knowledge, parser_obj.parse(formula).fol())
                            except ParseException:
                                try:
                                    background_knowledge = AndExpression(background_knowledge, lp(formula))
                                except Exception:
                                    print Exception
                        else:
                            try:
                                background_knowledge = parser_obj.parse(formula).fol()
                            except ParseException:
                                try:
                                    background_knowledge = lp(formula)
                                except Exception:
                                    print Exception
                                    
                    print background_knowledge
                    interpretations = []
                    
                    index = 1
                    for reading in new_discourse.readings():
                        print index
                        index = index + 1
                        interpretation = None
                        try:
                            interpretation = inference_check(reading, background_knowledge)
                        except InferenceCheckException as e:
                            print "Note:", e.value
                        if interpretation:
                            interpretations.append(interpretation)
                    
                    print "Return interpretations:"
                    return interpretations
                    
                except AssertionError as e:
                    print e
                
            except IndexError:
                print "Input sentences only!"
            
        except ValueError as e:
            print "Error:", e
    
        return "\nDiscourse uninterpretable"
    

def test_1():
    
    #with ontology
    bk_0 = {'individual' : r'all x.((individual(x) -> -(eventuality(x) | time(x))) & (eventuality(t) -> -time(x)) & (state(x) -> (eventuality(x) & -event(x))) & (event(x) -> eventuality(x)))',
            'time' : r'all x.((individual(x) -> -(eventuality(x) | time(x))) & (eventuality(t) -> -time(x)) & (state(x) -> (eventuality(x) & -event(x))) & (event(x) -> eventuality(x)))',
            'state' : r'all x.((individual(x) -> -(eventuality(x) | time(x))) & (eventuality(t) -> -time(x)) & (state(x) -> (eventuality(x) & -event(x))) & (event(x) -> eventuality(x)))',
            'event' : r'all x.((individual(x) -> -(eventuality(x) | time(x))) & (eventuality(t) -> -time(x)) & (state(x) -> (eventuality(x) & -event(x))) & (event(x) -> eventuality(x)))'
            }

    
    bk_2 = {'earlier' : r'all x y z.(earlier(x,y) & earlier(y,z) -> earlier(x,z)) & all x y.(earlier(x,y) -> -overlap(x,y))',
            'include' : r'all x y z.((include(x,y) & include(z,y)) -> (overlap(x,z)))',
            'die' : r'all x z y.((die(x) & AGENT(x,y) & die(z) & AGENT(z,y)) -> x = z)',
            
            'husband' : r'(([t,x,y],[POSS(y,x), husband(y)]) -> ([s],[married(s),THEME(s,x),overlap(t,s)]))',
            'married' : r'(([t,s],[married(s),THEME(s,x),overlap(t,s)]) -> ([x,y],[POSS(y,x), husband(y)]))',
            'own' : r'(([s,x,y],[own(s),AGENT(s,x),PATIENT(s,y)]) -> ([],[POSS(y,x)]))',
            'POSS' : r'(([t,y,x],[POSS(y,x)]) -> ([s],[own(s),AGENT(s,x),PATIENT(s,y),overlap(t,s)]))',
            
            #bk should be got from readings, not from unresolved expression
            #'PERF' : r'all x y z v.((include(x,y),abut(z,y),(z = end(v))) -> -(overlap(x,v)))',
            #'dead' : r'(([t,e,x],[die(e),AGENT(e,x)]) -> ([s1],[dead(s1),THEME(s1,x),overlap(t,s1),abut(e,s1)]))',
            
            'dead' : r'(([t,s,e,x],[include(s,t),abut(e,s),die(e),AGENT(e,x)]) -> ([],[dead(s),THEME(s,x),overlap(t,s)]))'
            }
             
    
    for interpretation in interpret("Jones has died", "Jones is dead", bk_2):
        if not isinstance(interpretation, str):
            print interpretation
            #interpretation.draw()
            
        #TODO: Double referents of same name (because of buffer)
        #TODO: Double outer accommodation readings because of NewInfroDRS
        #TODO: POSS(x,x) should be ruled out
        #TODO: Free variable check
        #TODO: Recursive substitution of bound variable names, otherwise temporal conditions fail
        #TODO: bk update after reading is generated
        #TODO: add get_refs() into buffer merge 
          
        # No background knowledge attached:
        ###################################
        #
        #"Mia is away", "Mia is away" -- uninformative
        #
        #"Mia is away", "Mia is not away" -- inconsistent
        #
        #"Mia is away", "If Mia is away Angus walked" -- inadmissible
        #
        #"Mia is away", "If Mia is not away Angus walked" -- uninformative
        #
        #"Mia is away", "If Angus walked Mia is away" -- uninformative
        #
        #"Mia is away", "If Angus walked Mia is not away" -- inadmissible
        #
        #"Mia is away", "Angus walked or Mia is away" -- uninformative
        #
        #"Mia is away", "Angus walked or Mia is not away" -- inadmissible
        
        ##################################################################
        
        # Background knowledge (not temporal):
        ######################################
        #
        #"Mia owns a husband", "Mia is married" -- uninformative
        #
        #"Mia owns a husband", "Mia is not married" -- inconsistent
        #
        #"Mia owns a husband", "If Mia is married Angus walked" -- inadmissible
        #
        #"Mia owns a husband", "If Mia is not married Angus walked" -- uninformative
        #
        #"Mia owns a husband", "If Angus walked Mia is married" -- uninformative
        #
        #"Mia owns a husband", "If Angus walked Mia is not married" -- inadmissible
        #
        #"Mia owns a husband", "Angus walked or Mia is married" -- uninformative
        #
        #"Mia owns a husband", "Angus walked or Mia is not married" -- inadmissible
        
        ###################################################################

        # Background knowledge (temporal):
        ######################################
        #
        #"Mia died", "Mia will die" -- inconsistent, DRT-language & FOL used to write bk input
        #
        #"Mia died", "Mia will not die" -- ok
        #
        #"Mia died", "If Angus lives Mia will die" -- inadmissible 
        #
        #"Mia died", "If Angus lives Mia will not die" -- ok
        #
        #"Mia died", "Angus lives or Mia will die" -- inadmissible
        #
        #"Mia died", "Angus lives or Mia will not die" -- ok
        
        ###################################################################
        
        # Background knowledge (not temporal), multiple readings:
        #########################################################
        #
        #"Mia is away", "If Mia kissed someone her husband is away"
        #
        #global - ok, local - ok, intermediate - ok
        #
        #"Mia is away", "If Mia is married Mia's husband is away"
        #
        #global - inadmissible, local - ok, intermediate - ok
        #
        #"Mia is away", "If Mia owns a car her car is red"
        #
        #global - inadmissible, local - ok, intermediate - ok
        #No binding!!!
        #
        #"Mia is away", "Mia does not own a car or her car is red"
        #
        #global - inadmissible, local - ok
        
        # Free variable check:
        ######################
        #
        #"Mia is away", "Every boy loves his car"
        #
        #Not implemented
        
        # Miscellaneous:
        ################
        #
        #"Angus is away", "If Angus owns a child his child is away"
        #
        # 'his' binds both child and Angus which is good. No free variable check.
        #
        #"Mia is away", "If a child kissed his dog he is red"
        #
        #AnaphoraResolutionException
        #
        #"Mia is away", "If Angus has sons his children are happy" - not tried yet
        
        # Temporal logic:
        #################
        #
        #"Mia died", "Mia will die" -- inconsistent due to bk
        #
        #"Mia lives and she does not live"  -- inconsistent  (backgrounding turned off)
        #
        #"Jones has owned a car", "Jones owns it" - worked on PERF
        #
        #"Jones has died", "Jones is dead" -- uninformative
        #
        
        ####################################################################
        ############################# TEST #################################
        ####################################################################
        
def test_2():
    parser_obj = DrtParser()
    parser = LogicParser().parse
    expression_4 = parser_obj.parse(r'(([t,s],[married(s),THEME(s,x),overlap(t,s)]) -> ([x,y],[POSS(y,x), husband(y)]))')
    expression_1 = parser_obj.parse(r'(([s,x,y],[own(s),AGENT(s,x),PATIENT(s,y)]) -> ([],[POSS(y,x)]))')
    expression_2 = parser_obj.parse(r'(([t,y,x],[POSS(y,x)]) -> ([s],[own(s),AGENT(s,x),PATIENT(s,y),overlap(t,s)]))')
    expression_3 = parser_obj.parse(r'(([t,x,y],[POSS(y,x), husband(y)]) -> ([s],[married(s),THEME(s,x),overlap(t,s)]))')
    #expression_4 = parser_obj.parse(r'(([t,s],[married(s),THEME(s,x),overlap(t,s)]) -> ([x,y],[POSS(y,x), husband(y)]))')
    #expression_2 = parser(r'exists x.((POSS(x, Mia) & husband(x)) -> -married(Mia))')
    #expression = parser_obj.parse(r'DRS([n,e,x,t],[Mia(x),die(e),AGENT(e,x),include(t,e),earlier(t,n),-DRS([t02,e01],[die(e01),AGENT(e01,x),include(t02,e01),earlier(t02,n)]) ])')
    #expression = parser_obj.parse(r'([n,t,e,x,y],[-([s],[married(s), THEME(s,x), overlap(n,s)]), POSS(y,x), husband{sg,m}(y), Mia{sg,f}(x), earlier(t,n), walk(e), AGENT(e,x), include(t,e)])')
    #expression = parser_obj.parse(r'([x],[POSS(x,Mia),husband(x),-([s],[married(s),THEME(s,Mia)])])')
    expression = parser_obj.parse(r'([n,z6,s,x],[Mia{sg,f}(x), husband{sg,m}(z6), own(s), AGENT(s,x), PATIENT(s,z6), overlap(n,s), -([s011],[married(s011), THEME(s011,x), overlap(n,s011)])])')
    #expression = parser(r'DRS([],[die(Mia),-(DRS([],[die(Mia)])])')
    #expression = parser(r'(p & -(-p -> q))')
    parsed = NegatedExpression(AndExpression(expression.fol(),
                    AndExpression(AndExpression(expression_1.fol(),expression_3.fol()),
                                  AndExpression(expression_2.fol(),expression_4.fol()))) )
    
    #parsed = r'-(([n,z6,s,x],[Mia{sg,f}(x), husband{sg,m}(z6), own(s), AGENT(s,x), PATIENT(s,z6), overlap(n,s), ([s011],[married(s011), THEME(s011,x), overlap(n,s011)])]) & ((all t s.((((married(s) & THEME(s,x)) & overlap(t,s)) & REFER(s)) -> exists x.(exists y.((POSS(y,x) & husband(y)) & individual(y)) & individual(x))) & all s x y.((((own(s) & AGENT(s,x)) & PATIENT(s,y)) & REFER(s)) -> POSS(y,x))) & all t x y.((POSS(y,x) & husband(y)) -> exists s.((((married(s) & THEME(s,x)) & overlap(t,s)) & REFER(s)) & state(s)))))'
    print parsed
    #expression = parser('m')
    #assumption = parser('m')
    prover = Prover9Command(parsed,timeout=60)
    print prover.prove()
#      
#
#def test_3():
#           
#    parser_obj = DrtParser()       
#    expression = parser_obj.parse(r'([n,t,e,x],[-([t09,e],[earlier(t09,n), die(e), AGENT(e,x), include(t09,e), REFER(e)]), earlier(t,n), die(e), AGENT(e,x), include(t,e), REFER(e), Mia{sg,f}(x)])')
#    print expression
#    print ParallelProverBuilderCommand(Prover9(), Mace(),expression).build_model()
    
if __name__ == "__main__":
    test_1()
     
