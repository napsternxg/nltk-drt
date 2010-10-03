from nltk.inference.prover9 import Prover9Command, Prover9
from nltk.inference.mace import MaceCommand, Mace
from temporaldrt import DrtParser
from nltk.sem.drt import AbstractDrs
from nltk import LogicParser
from nltk.sem.logic import AndExpression, NegatedExpression, ParseException
from nltk.inference.api import ParallelProverBuilderCommand, Prover, ModelBuilder
from theorem import Builder, Prover 
import temporaldrt as drt
#import util
#from util import local_DrtParser
#from threading import Thread
#import os

import nltkfixtemporal

def gr(s, recursive=False):
    return []

AbstractDrs.get_refs = gr

"""
As Mace looks for a minimal solution, those are the things we need to have so that 
models make sense:
    
    (iv) presupposition that all individuals mentioned in a discourse are uniquely
     and disjointly identified by their names. This could be done with following
     DRS-condition: DRS([x,y],[Bill(x),Claire(y)]) turns into 
     DRS([x,y],[x=Bill, y=Claire, -(x=y)]). In other words, for each pair of proper name
     carrying individuals x and y, it should be stated in a DRS from which both are
     acceptable that -(x=y).
    
Admissibility Constraints:

An expression to be checked for admissibility should be a DRS which embeds a NewInfoDRS:
The former represents previous discourse (if any), the latter is some new discourse that
has been resolved with respect to that previous discourse. There are two groups of Admissibility
Constraints (van der Sandt 1992): 

Global Constraints:

Prover - negative check for consistency.
Prover - negative check for informativity.
Builder - positive check for consistency.
Builder - positive check for informativity.

Global Consistency: Give a NegatedExpression of the resulting discourse to the prover.
    If it returns True, the discourse is inconsistent. Give the resulting discourse to
    the builder. If it returns a model, the discourse is consistent.
    
Global Informativity: Negate new discourse. Give a NegatedExpression of the resulting
    discourse to the prover. If the prover returns True, then the resulting discourse
    is uninformative. Give the resulting discourse to the builder. If it returns a model,
    the new reading is informative.
    [if (phi -> psi) is a theorem, then -(phi -> psi) is a contradiction and could not
    have a model. Thus, if there is a model, (phi -> psi) is not a theorem.]
    
Local Constraints (Kartunen's Filters):

    Superordinate DRSs should entail neither a DRS nor its negation.  
    Generate a list of ordered pairs such that the first element of the pair is the DRS
    representing the entire discourse but without some subordinate DRS and the second is
    this subordinate DRS to be checked on entailment:
    
        (i) From DrtNegatedExpression -K, if K is a DRS, take K and put it in the second
        place of the ordered pair. Remove the DrtNegatedExpression and place the rest in
        the first place of the order pair. 
        
        (ii) From a DrtImpCondition K->L, provided that both are DRSs, create two ordered
        pairs: (a) Put the antecedent DRS K into the second place, remove the DrtImpCondition
        and put the result into the first place of the ordered pair; (b) Put the consequent
        DRS L into the second place, merge the antecedent DRS K globally and put the
        result into the first place of the ordered pair.
        
        (iii) From a DrtOrExpression K | L, provided that both are DRSs, create two ordered
        pairs: Put each of the disjuncts into the second place of each pair, remove the
        DrtORExpression and put the result into the first place of that pair. 
"""


def inference_check(expr, background_knowledge=False,verbose=False):
    """General function for all kinds of inference-based checks:
    consistency, global and local informativity"""
    
    assert isinstance(expr, drt.DRS), "Expression %s is not a DRS"
    
    expression = expr.deepcopy()
    print expression, "\n"
    
    def _remove_temporal_conds(e):
        """Removes discourse structuring temporal conditions that could
        affect inference check"""
        for cond in list(e.conds):
            if isinstance(cond, drt.DrtEventualityApplicationExpression) and \
            isinstance(cond.function, drt.DrtEventualityApplicationExpression) and \
            cond.function.function.variable.name in drt.DrtTokens.TEMP_CONDS:
                e.conds.remove(cond)
                
            elif isinstance(cond, drt.DRS):
                _remove_temporal_conds(cond)
                
            elif isinstance(cond, drt.DrtNegatedExpression) and \
                isinstance(cond.term, drt.DRS):
                _remove_temporal_conds(cond.term)
                
            elif isinstance(cond, drt.DrtBooleanExpression) and \
                isinstance(cond.first, drt.DRS) and isinstance(cond.second, drt.DRS): 
                _remove_temporal_conds(cond.first)
                _remove_temporal_conds(cond.second)           

    def _check(expression):
        """method performing check"""
        if background_knowledge:
            e = AndExpression(expression.fol(),background_knowledge)
            if verbose: print "performing check on:", e
            p = Prover(NegatedExpression(e))
            m = Builder(e)
        else:
            if verbose: print "performing check on:", expression
            p = Prover(NegatedExpression(expression))
            m = Builder(expression)
        
        if verbose: print "\n%s, %s\n" % (p, m)
        
        p.start()
        m.start()
        
        while p.is_alive() and m.is_alive():
            pass
        
        if m.is_alive():
            result = p.result
            if verbose: print "prover returned with result:", p, result, "\n"
            
            while not m.builder._modelbuilder.isrunning():
                pass
            m.builder._modelbuilder.terminate()
            
            return not result

        if verbose: print "builder return with result:", m, "\n\n", m.builder.valuation, "\n"
        
        while not p.prover._prover.isrunning():
                pass
        p.prover._prover.terminate()
        
        return m.result
    
#    def check(expression):
#        """nltk class freezes, not using it"""
#        if background_knowledge:
#            expr = NegatedExpression(AndExpression(expression,background_knowledge))
#        else:
#            expr = NegatedExpression(expression)
#            
#        return ParallelProverBuilderCommand(Prover9(), Mace(),expr).build_model()
      
    
    def consistency_check(expression):
        """1. Consistency check"""
        if verbose: print "consistency check initiated...\n"
        return _check(expression)
        
    
    def informativity_check(expression):
        """2. Global informativity check"""
        if verbose: print "informativity check initiated...\n"
        local_check = []
        for cond in drt.ReverseIterator(expression.conds):
            if isinstance(cond, drt.DRS) and \
            not isinstance(cond, drt.PresuppositionDRS):
                """New discourse in the previous discourse"""
                temp = (expression.conds[:expression.conds.index(cond)]+
                        [drt.DrtNegatedExpression(cond)]+
                    expression.conds[expression.conds.index(cond)+1:])
                e = expression.__class__(expression.refs,temp)
                if verbose:
                    print "new discourse %s found in %s \n" % (cond,expression)
                    print "expression for global check: %s \n" % e
                if not _check(e):
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
            if verbose: print "Expression %s is informativ\n" % expression
            return True
        
    def local_informativity_check(check_list):
        """3. Local admissibility constraints"""
        if verbose: print "local admissibility check initiated...\n%s\n" % check_list

        for main,sub in check_list:
            assert isinstance(main, drt.DRS), "Expression %s is not a DRS"
            assert isinstance(sub, drt.DRS), "Expression %s is not a DRS"

            if not _check(main.__class__(main.refs,main.conds+[drt.DrtNegatedExpression(sub)])):
                if verbose: print "main %s entails sub %s \n" % (main,sub)
                raise InferenceCheckException("New discourse is inadmissible due to local uninformativity:\n\n%s entails %s" % (main, sub))
                
            elif not _check(main.__class__(main.refs,main.conds+[sub])):
                if verbose: print "main %s entails negation of sub %s \n" % (main,sub)
                raise InferenceCheckException("New discourse is inadmissible due to local uninformativity:\n\n%s entails the negation of %s" % (main, sub))
                
        if verbose: print "main %s does not entail sub %s nor its negation\n" % (main,sub)
        return True                

    _remove_temporal_conds(expression)
    if verbose: print "Expression without eventuality-relating conditions: %s \n" % expression
    
    if not consistency_check(expression):
            if verbose: print "Expression %s is inconsistent\n" % expression
            raise InferenceCheckException("New discourse is inconsistent on the following interpretation:\n\n%s" % expression)
    
    if not informativity_check(expression):
            if verbose: print "Expression %s is uninformative\n" % expression            
            raise InferenceCheckException("New expression is uninformative on the following interpretation:\n\n%s" % expression)
 
    
    for cond in expr.conds:
        """Merge DRS of the new expression into the previous discourse"""
        if isinstance(cond, drt.DRS):
            #change to NewInfoDRS when done
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
    #needed any longer?
    assert isinstance(subexpression, drt.DRS), "Expression %s is not a DRS" % subexpression
    assert isinstance(expression, drt.DRS), "Expression %s is not a DRS" % expression

    subexpr = subexpression.__class__(subexpression.refs,subexpression.conds)
    expr = expression.__class__(expression.refs, expression.conds)
    
    for ref in set(subexpression.get_refs(True)) & set(expression.get_refs(True)):
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


#def interpret(expr_1, expr_2, bk=False,verbose=False):
#    """Interprets a new expression with respect to some previous discourse 
#    and background knowledge. The function first generates relevant background
#    knowledge and then performs inference check on readings generated by 
#    the readings() method. It returns a list of admissible interpretations in
#    the form of DRSs.
#    
#    Could be enlarged to take a grammar argument and a parser argument"""
#    
#    if expr_1 and not isinstance(expr_1, str):
#        return "\nDiscourse uninterpretable. Expression %s is not a string" % expr_1
#    elif not isinstance(expr_2, str):
#        return "\nDiscourse uninterpretable. Expression %s is not a string" % expr_2
#    elif not bk and not isinstance(bk, dict):
#        return "\nDiscourse uninterpretable. Background knowledge is not in dictionary format"
#        
#    else:
#            
#        parser_obj = DrtParser()
#        buffer = parser_obj.parse(r'\Q P.(Q+DRS([],[P]))')
#        #buffer = parser_obj.parse(r'\Q P.(NEWINFO([],[P])+Q)')
#        tester = util.Tester('file:../data/grammar.fcfg', DrtParser)
#        try:
#            try:
#                if expr_1:
#                    discourse = tester.parse(expr_1, utter=True)
#                    
#                    expression = tester.parse(expr_2, utter=False)
#                    
#                    for ref in set(expression.get_refs(True)) & set(discourse.get_refs(True)):
#                        newref = drt.DrtVariableExpression(drt.unique_variable(ref))
#                        expression = expression.replace(ref,newref,True)                   
#                    
#                    new_discourse = drt.DrtApplicationExpression(drt.DrtApplicationExpression(buffer,discourse),expression).simplify()
#                
#                else: new_discourse = tester.parse(expr_2, utter=True)
#                                   
#                background_knowledge = None
#                
#                lp = LogicParser().parse
#                
#                #in order for bk in DRT-language to be parsed without REFER
#                #this affects inference
#                parser_obj = local_DrtParser()
#                #should take bk in both DRT language and FOL
#                try:
#                    for formula in get_bk(new_discourse, bk):
#                        if background_knowledge:
#                            try:
#                                background_knowledge = AndExpression(background_knowledge, parser_obj.parse(formula).fol())
#                            except ParseException:
#                                try:
#                                    background_knowledge = AndExpression(background_knowledge, lp(formula))
#                                except Exception:
#                                    print Exception
#                        else:
#                            try:
#                                background_knowledge = parser_obj.parse(formula).fol()
#                            except ParseException:
#                                try:
#                                    background_knowledge = lp(formula)
#                                except Exception:
#                                    print Exception
#                                    
#                    if verbose: print "Generated background knowledge:\n%s" % background_knowledge
#                    interpretations = []
#                    
#                    index = 1
#                    for reading in new_discourse.readings():
#                        print "\nGenerated reading (%s):" % index
#                        index = index + 1
#                        interpretation = None
#                        try:
#                            interpretation = inference_check(reading, background_knowledge, verbose)
#                        except InferenceCheckException as e:
#                            print e.value
#                        if interpretation:
#                            interpretations.append(interpretation)
#                    
#                    print "Admissible interpretations:"
#                    return interpretations
#                    
#                except AssertionError as e:
#                    print e
#                
#            except IndexError:
#                print "Input sentences only!"
#            
#        except ValueError as e:
#            print "Error:", e
#    
#        return "\nDiscourse uninterpretable"
#    

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
    
            
    
    #for interpretation in interpret("Mia is away", "If Mia is married her husband is away", bk_2):
    ##    if not isinstance(interpretation, str):
    #       print interpretation
            #interpretation.draw()
            
        #TODO: Double referents of same name (because of buffer)
        #TODO: Double outer accommodation readings because of NewInfroDRS
        #TODO: POSS(x,x) should be ruled out
        #TODO: Free variable check
        #TODO: Recursive substitution of bound variable names, otherwise temporal conditions fail
        #TODO: bk update after reading is generated
        #TODO: add get_refs() into buffer merge
        #TODO: Add Negative DRS admissibility condition 
          
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
    
if __name__ == "__main__":
    test_1()
     
