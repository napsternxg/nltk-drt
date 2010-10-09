from nltk.sem.logic import AndExpression, NegatedExpression
from theorem import Theorem
from temporaldrt import DRS, DrtBooleanExpression, DrtNegatedExpression, DrtConstantExpression, \
                        DrtApplicationExpression, DrtVariableExpression, unique_variable, \
                        ConcatenationDRS, DrtImpExpression, DrtOrExpression, PresuppositionDRS, \
                        ReverseIterator, DrtTokens, DrtEventualityApplicationExpression

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
    
    assert isinstance(expr, DRS), "Expression %s is not a DRS"
    
    expression = expr.deepcopy()
    print expression, "\n"
    
    def _remove_temporal_conds(e):
        """Removes discourse structuring temporal conditions that could
        affect inference check"""
        for cond in list(e.conds):
            if isinstance(cond, DrtEventualityApplicationExpression) and \
            isinstance(cond.function, DrtEventualityApplicationExpression) and \
            cond.function.function.variable.name in DrtTokens.TEMP_CONDS:
                e.conds.remove(cond)
                
            elif isinstance(cond, DRS):
                _remove_temporal_conds(cond)
                
            elif isinstance(cond, DrtNegatedExpression) and \
                isinstance(cond.term, DRS):
                _remove_temporal_conds(cond.term)
                
            elif isinstance(cond, DrtBooleanExpression) and \
                isinstance(cond.first, DRS) and isinstance(cond.second, DRS): 
                _remove_temporal_conds(cond.first)
                _remove_temporal_conds(cond.second)           

    def _check(expression):
        """method performing check"""
        if background_knowledge:
            e = AndExpression(expression.fol(),background_knowledge)
            if verbose: print "performing check on:", e
            t = Theorem(NegatedExpression(e), e)
        else:
            if verbose: print "performing check on:", expression
            t = Theorem(NegatedExpression(expression), expression)
        
        result, output = t.check()
        if verbose:
            if output:
                print "\nMace4 returns:\n%s\n" % output
            else:
                print "\nProver9 returns: %s\n" % result
        return result      
    
    def consistency_check(expression):
        """1. Consistency check"""
        if verbose: print "consistency check initiated...\n"
        return _check(expression)
        
    
    def informativity_check(expression):
        """2. Global informativity check"""
        if verbose: print "informativity check initiated...\n"
        local_check = []
        for cond in ReverseIterator(expression.conds):
            if isinstance(cond, DRS) and \
            not isinstance(cond, PresuppositionDRS):
                """New discourse in the previous discourse"""
                temp = (expression.conds[:expression.conds.index(cond)]+
                        [DrtNegatedExpression(cond)]+
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

            elif isinstance(cond, DrtOrExpression) and \
                isinstance(cond.first, DRS) and isinstance(cond.second, DRS):
                temp = (expression.conds[:expression.conds.index(cond)]+
                    expression.conds[expression.conds.index(cond)+1:])
                local_check.append((expression.__class__(expression.refs,temp),cond.first))
                local_check.append((expression.__class__(expression.refs,temp),cond.second))
    
            elif isinstance(cond, DrtImpExpression) and \
                isinstance(cond.first, DRS) and isinstance(cond.second, DRS):
                temp = (expression.conds[:expression.conds.index(cond)]+
                    expression.conds[expression.conds.index(cond)+1:])
                local_check.append((expression.__class__(expression.refs,temp),cond.first))
                local_check.append((ConcatenationDRS(expression.__class__(expression.refs,temp),
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
            assert isinstance(main, DRS), "Expression %s is not a DRS"
            assert isinstance(sub, DRS), "Expression %s is not a DRS"

            if not _check(main.__class__(main.refs,main.conds+[DrtNegatedExpression(sub)])):
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
        if isinstance(cond, DRS):
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
    assert isinstance(subexpression, DRS), "Expression %s is not a DRS" % subexpression
    assert isinstance(expression, DRS), "Expression %s is not a DRS" % expression

    subexpr = subexpression.__class__(subexpression.refs,subexpression.conds)
    expr = expression.__class__(expression.refs, expression.conds)
    
    for ref in set(subexpression.get_refs(True)) & set(expression.get_refs(True)):
        newref = DrtVariableExpression(unique_variable(ref))
        subexpr = subexpr.replace(ref,newref,True)
       
    return expr.__class__(expr.refs+subexpr.refs,expr.conds+subexpr.conds)


  
def get_bk(drs, dictionary):
    """Collects background knowledge relevant for a given expression.
    DrtConstantExpression variable names are used as keys"""
    
    assert isinstance(drs, DRS), "Expression %s is not a DRS" % drs
    assert isinstance(dictionary, dict), "%s is not a dictionary" % dictionary
    bk_list = []
    
    for cond in drs.conds:
        if isinstance(cond, DrtApplicationExpression):
            if isinstance(cond.function, DrtConstantExpression):
                bk_formula = dictionary.get(cond.function.variable.name,False)
               
            elif isinstance(cond.function, DrtApplicationExpression) and \
             isinstance(cond.function.function, DrtConstantExpression):
                bk_formula = dictionary.get(cond.function.function.variable.name,False)
               
            if bk_formula:
                bk_list.append(bk_formula)
                
        elif isinstance(cond, DRS):
            bk_list.extend(get_bk(cond,dictionary))
            
        elif isinstance(cond, DrtNegatedExpression) and \
            isinstance(cond.term, DRS):
            bk_list.extend(get_bk(cond.term,dictionary))
            
        elif isinstance(cond, DrtBooleanExpression) and \
            isinstance(cond.first, DRS) and isinstance(cond.second, DRS):
            bk_list.extend(get_bk(cond.first,dictionary))
            bk_list.extend(get_bk(cond.second,dictionary))
            
    
    return list(set(bk_list))



    
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
        
def test_1():
    from nltk.inference.prover9 import Prover9Command
    from temporaldrt import DrtParser
    from nltk import LogicParser   
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
     
