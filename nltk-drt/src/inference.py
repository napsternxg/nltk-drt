"""
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
__author__ = "Peter Makarov, Alex Kislev, Emma Li"
__version__ = "1.0"
__date__ = "Tue, 24 Aug 2010"

from nltk.sem.logic import AndExpression, NegatedExpression
from temporaldrt import DRS, DrtBooleanExpression, DrtNegatedExpression, DrtConstantExpression, \
                        DrtApplicationExpression, DrtVariableExpression, unique_variable, \
                        ConcatenationDRS, DrtImpExpression, DrtOrExpression, PresuppositionDRS, \
                        ReverseIterator, DrtTokens, DrtEventualityApplicationExpression, NewInfoDRS

import subprocess
import nltk
from nltk.sem import Valuation
from nltk.sem.logic import is_indvar
from nltk.inference.mace import MaceCommand
from nltk.inference.prover9 import convert_to_prover9
from threading import Thread

class Communicator(Thread):
    """a thread communicating with a process, terminates once the communication is over"""
    def __init__(self, process, input=None):
        Thread.__init__(self)
        self.process = process
        self.input = input
    
    def run(self):
        try:
            self.result = self.process.communicate(self.input)
        except OSError:
            pass

class Theorem(object):

    BINARY_LOCATIONS = ('/usr/local/bin', '/usr/bin', '/home/pmakarov/prover9/bin')
    PROVER_BINARY = None
    BUILDER_BINARY = None
    INTERPFORMAT_BINARY = None

    def __init__(self, prover_goal, builder_goal, prover_timeout=60, builder_max_models=500):
        self.prover_goal = prover_goal
        self.builder_goal = builder_goal
        self.prover_timeout = prover_timeout
        self.builder_max_models = builder_max_models
    
    def _find_binary(self, name, verbose=False):
        return nltk.internals.find_binary(name, 
            searchpath=Theorem.BINARY_LOCATIONS, 
            env_vars=['PROVER9HOME'],
            url='http://www.cs.unm.edu/~mccune/prover9/',
            binary_names=[name],
            verbose=verbose)

    def _prover9_input(self):
        return "clear(auto_denials).\n%s" % self._input(self.prover_goal)

    def _mace_input(self):
        return self._input(self.builder_goal)
    
    def _input(self, goal):
        return "formulas(goals).\n    %s.\nend_of_list.\n\n" % convert_to_prover9(goal)

    def check(self, verbose=False):
        prover_input = 'assign(max_seconds, %d).\n\n' % self.prover_timeout if self.prover_timeout > 0 else ""
        prover_input += self._prover9_input()

        builder_input = 'assign(end_size, %d).\n\n' % self.builder_max_models if self.builder_max_models > 0 else ""
        builder_input += self._mace_input()

        return self._call(prover_input, builder_input, verbose)

    def _model(self, valuation_str, verbose=False):
        """
        Transform the output file into an NLTK-style Valuation. 
        
        @return: A model if one is generated; None otherwise.
        @rtype: L{nltk.sem.Valuation} 
        """
        valuation_standard_format = self._transform_output(valuation_str, 'standard', verbose)
        
        val = []
        for line in valuation_standard_format.splitlines(False):
            l = line.strip()

            if l.startswith('interpretation'):
                # find the number of entities in the model
                num_entities = int(l[l.index('(')+1:l.index(',')].strip())

            elif l.startswith('function') and l.find('_') == -1:
                # replace the integer identifier with a corresponding alphabetic character
                name = l[l.index('(')+1:l.index(',')].strip()
                if is_indvar(name):
                    name = name.upper()
                value = int(l[l.index('[')+1:l.index(']')].strip())
                val.append((name, MaceCommand._make_model_var(value)))

            elif l.startswith('relation'):
                l = l[l.index('(')+1:]
                if '(' in l:
                    #relation is not nullary
                    name = l[:l.index('(')].strip()
                    values = [int(v.strip()) for v in l[l.index('[')+1:l.index(']')].split(',')]
                    val.append((name, MaceCommand._make_relation_set(num_entities, values)))
                else:
                    #relation is nullary
                    name = l[:l.index(',')].strip()
                    value = int(l[l.index('[')+1:l.index(']')].strip())
                    val.append((name, value == 1))

        return Valuation(val)

    def _transform_output(self, input_str, format, verbose=False):

        if Theorem.INTERPFORMAT_BINARY is None:
            Theorem.INTERPFORMAT_BINARY = self._find_binary('interpformat', verbose)

        if verbose:
            print 'Calling Interpformat:', Theorem.INTERPFORMAT_BINARY
            print 'Args:', format
            print 'Input:\n', input_str, '\n'

        p = subprocess.Popen([Theorem.INTERPFORMAT_BINARY, format], stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             stdin=subprocess.PIPE)
        (stdout, stderr) = p.communicate(input_str)
        
        if verbose:
            print 'Return code:', p.returncode
            if stdout: print 'stdout:\n', stdout, '\n'
            if stderr: print 'stderr:\n', stderr, '\n'
            
        return stdout

    def _call(self, prover_input, builder_input, verbose):
        if Theorem.PROVER_BINARY is None:
            Theorem.PROVER_BINARY = self._find_binary('prover9', verbose)

        if Theorem.BUILDER_BINARY is None:
            Theorem.BUILDER_BINARY = self._find_binary('mace4', verbose)
        
        if verbose:
            print 'Calling Prover:', Theorem.PROVER_BINARY
            print 'Prover Input:\n', prover_input, '\n'
            print 'Calling Builder:', Theorem.BUILDER_BINARY
            print 'Builder Input:\n', builder_input, '\n'

        prover_process = subprocess.Popen([Theorem.PROVER_BINARY], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
        #builder_process = subprocess.Popen([Theorem.BUILDER_BINARY], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)

        prover_thread = Communicator(prover_process, prover_input)
        #builder_thread = Communicator(builder_process, builder_input)
        
        prover_thread.start()
        #builder_thread.start()

        while prover_thread.is_alive(): #and builder_thread.is_alive():
            pass

        stdout, stderr = prover_thread.result
        returncode = prover_process.poll()
        result = not (returncode == 0)
        output = None

#        if not prover_thread.is_alive():
#            if verbose:
#                print "Prover done, Builder %s " % ("done" if not builder_thread.is_alive() else "running")
#            stdout, stderr = prover_thread.result
#            returncode = prover_process.poll()
#            result = not (returncode == 0)
#            output = None
#            if builder_process.poll() is None:
#                if verbose:
#                    print "builder is still running, terminating..."
#                try:
#                    builder_process.terminate()
#                except OSError:
#                    pass
#
#        elif not builder_thread.is_alive():
#            if verbose:
#                print "Prover %s, Builder done " % ("done" if not prover_thread.is_alive() else "running")
#            stdout, stderr = builder_thread.result
#            returncode = builder_process.poll()
#            result = (returncode == 0)
#            output = stdout
#            if prover_process.poll() is None:
#                if verbose:
#                    print "prover is still running, terminating..."
#                try:
#                    prover_process.terminate()
#                except OSError:
#                    pass

        if verbose:
            if stdout: print('output:\t%s' % stdout)
            if stderr: print('error:\t%s' % stderr)
            print 'return code:', returncode

        # transform the model if one is available
        if output is not None:
            output = self._model(stdout, verbose)

        return (result, output)

def inference_check(expr, background_knowledge=False,verbose=False):
    """General function for all kinds of inference-based checks:
    consistency, global and local informativity"""
    
    assert isinstance(expr, DRS), "Expression %s is not a DRS"

    expression = expr.deepcopy()
    if verbose: print "\n##### Inference check initiated #####\n\nExpression:\t%s\n" % expression
    
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
            if verbose:
                print "performing check on:", e
            t = Theorem(NegatedExpression(e), e)
        else:
            if verbose:
                print "performing check on:", expression.fol()
            t = Theorem(NegatedExpression(expression), expression)
        
        result, output = t.check()
        if verbose:
            if output:
                print "\nMace4 returns:\n%s\n" % output
            else:
                print "\nProver9 returns: %s\n" % (not result)
        return result      
    
    def consistency_check(expression):
        """1. Consistency check"""
        if verbose: print "### Consistency check initiated...\n"
        if not _check(expression):
            error_message = "New discourse is inconsistent on the following interpretation:\n\n%s" % expression
            if verbose:
                print "#!!!#: ", error_message
            return ConsistencyOuput(error_message)
        else:
            if verbose:
                print "##OK##: Expression is consistent\n"
            return True
        
    
    def informativity_check(expression):
        """2. Global informativity check"""
        if verbose:
            print "### Informativity check initiated...\n"
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
                    error_message = "New expression is uninformative on the following interpretation:\n\n%s" % expression
                    if verbose:
                        print "#!!!#", error_message
                    return InformativityOuput(error_message)
                else:
                    temp = (expression.conds[:expression.conds.index(cond)]+
                    expression.conds[expression.conds.index(cond)+1:])
                    """Put sub-DRS into main DRS and start informativity check"""
                    return informativity_check(expression.__class__(expression.refs+cond.refs,temp+cond.conds))
                            
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
            if verbose:
                print "##OK##: Expression is informative\n"
            return True
        
    def local_informativity_check(check_list):
        """3. Local admissibility constraints"""
        if verbose: print "### Local admissibility check initiated...\n%s\n" % check_list

        for main,sub in check_list:
            assert isinstance(main, DRS), "Expression %s is not a DRS"
            assert isinstance(sub, DRS), "Expression %s is not a DRS"

            if not _check(main.__class__(main.refs,main.conds+[DrtNegatedExpression(sub)])):
                error_message = "New discourse is inadmissible due to local uninformativity:\n\n%s entails %s" % (main, sub)
                if verbose:
                    print "#!!!#: ", error_message
                return AdmissibilityOuput(error_message)
                
            elif not _check(main.__class__(main.refs,main.conds+[sub])):
                error_message = "New discourse is inadmissible due to local uninformativity:\n\n%s entails the negation of %s" % (main, sub)
                if verbose:
                    print "#!!!#: ", error_message
                return AdmissibilityOuput(error_message)
                
        if verbose: print "##OK##: Main %s does not entail sub %s nor its negation\n" % (main,sub)
        return True                

    _remove_temporal_conds(expression)
    if verbose: print "Expression without eventuality-relating conditions: %s \n" % expression
    
    cons_check = consistency_check(expression)
    
    if cons_check is True:
        inf_check = informativity_check(expression)
        
        if inf_check is True: 
            for cond in expr.conds:
                #Merge DRS of the new expression into the previous discourse
                result = expr
                if isinstance(cond, NewInfoDRS):
                    #change to NewInfoDRS when done
                    result = expr.__class__(expr.refs+cond.refs,
                            (expression.conds[:expr.conds.index(cond)]+
                            expression.conds[expr.conds.index(cond)+1:])+cond.conds)
            if verbose:
                print "\n#### Inference check passed ####\n"
            return result, "Sentence admitted"
        
        else:
            if verbose:
                print "\n###!!!# Inference check failed #!!!###\n"
            return False, inf_check
    
    else:
        if verbose:
            print "\n###!!!# Inference check failed #!!!###\n"
        return False, cons_check

    
class AdmissibilityOuput(str):
    pass

class ConsistencyOuput(str):
    pass

class InformativityOuput(str):
    pass


def prenex_normal_form(expression,subexpression):
    """Combines sub-DRS with superordinate DRS"""
    #Not used currently
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
