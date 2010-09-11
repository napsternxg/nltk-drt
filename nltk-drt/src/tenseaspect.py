import re
import operator

import nltkfixtemporal
import util

from nltk.sem.logic import Variable
from nltk.sem.logic import IndividualVariableExpression
from nltk.sem.logic import _counter
from nltk.sem.logic import BasicType
from nltk.sem.logic import Expression
from nltk.sem.logic import AndExpression, ExistsExpression
import temporaldrt as drt

from temporaldrt import is_timevar, DrtIndividualVariableExpression, \
                        DrtFunctionVariableExpression, DrtEventVariableExpression, \
                        DrtTimeVariableExpression, DrtProperNameExpression, \
                        DrtApplicationExpression, DrtAbstractVariableExpression, \
                        DrtLocationTimeApplicationExpression, DrtTimeApplicationExpression, \
                        DrtProperNameApplicationExpression, is_propername, is_funcvar, \
                        is_eventvar

class StateType(BasicType):
    """
    Basic type of times added on top of nltk.sem.logic.
    Extend to utterance time referent 'n'.
    """
    def __str__(self):
        return 's'

    def str(self):
        return 'STATE'

STATE_TYPE = StateType()


def is_indvar(expr):
    """
    An individual variable must be a single lowercase character other than 'e', 't', 'n', 's',
    followed by zero or more digits.
    
    @param expr: C{str}
    @return: C{boolean} True if expr is of the correct form 
    """
    assert isinstance(expr, str), "%s is not a string" % expr
    return re.match(r'^[a-df-mo-ru-z]\d*$', expr)


def is_statevar(expr):
    """
    An state variable must be a single lowercase 's' character followed by
    zero or more digits.
    
    @param expr: C{str}
    @return: C{boolean} True if expr is of the correct form 
    """
    assert isinstance(expr, str), "%s is not a string" % expr
    return re.match(r'^s\d*$', expr)


def is_uttervar(expr):
    """
    An utterance time variable must be a single lowercase 'n' character followed by
    zero or more digits.
    
    @param expr: C{str}
    @return: C{boolean} True if expr is of the correct form 
    """
    assert isinstance(expr, str), "%s is not a string" % expr
    return re.match(r'^n\d*$', expr)


  
def unique_variable(pattern=None, ignore=None):
    """
    Return a new, unique variable.
    param pattern: C{Variable} that is being replaced.  The new variable must
    be the same type.
    param term: a C{set} of C{Variable}s that should not be returned from 
    this function.
    return: C{Variable}
    """
    if pattern is not None:
        if is_indvar(pattern.name):
            prefix = 'z'
        elif is_funcvar(pattern.name):
            prefix = 'F'
        elif is_eventvar(pattern.name):
            prefix = 'e0'
        elif is_timevar(pattern.name):
            prefix = 't0'
        elif is_statevar(pattern.name):
            prefix = 's0'
        else:
            assert False, "Cannot generate a unique constant"
    else:
        prefix = 'z'
        
    v = Variable(prefix + str(_counter.get()))
    while ignore is not None and v in ignore:
        v = Variable(prefix + str(_counter.get()))
    return v
            
#            v = Variable(prefix + str(_counter.get()))
#            while ignore is not None and v in ignore:
#                v = Variable(prefix + str(_counter.get()))
#            return v

#    else:
#        return drt.unique_variable(pattern, ignore)
    
    
############### Needed?

class DrtTokens(drt.DrtTokens):
    UTTER_TIME = 'UTTER'
    REFER_TIME = 'REFER'
    PERF = 'PERF'
    UTTER = drt.DrtConstantExpression(Variable("UTTER"))
    PERFECT = drt.DrtConstantExpression(Variable("PERF"))
    REFER = drt.DrtConstantExpression(Variable("REFER"))
    OVERLAP = drt.DrtConstantExpression(Variable("overlap"))
    EARLIER = drt.DrtConstantExpression(Variable("earlier"))
    INCLUDE = drt.DrtConstantExpression(Variable("include"))
    ABUT = drt.DrtConstantExpression(Variable("abut"))
    END = drt.DrtConstantExpression(Variable("end"))
    TEMP_CONDS = [OVERLAP, EARLIER, INCLUDE]
    
    PAST = drt.DrtConstantExpression(Variable("PAST"))
    PRES = drt.DrtConstantExpression(Variable("PRES"))
    FUT = drt.DrtConstantExpression(Variable("FUT"))
    
    TENSE = [PAST, PRES, FUT]
    
    EVENT = Variable("e")
################ a?    

class AbstractDrs(drt.AbstractDrs):
    
    def __add__(self, other):
        return ConcatenationDRS(self, other)
    
    def applyto(self, other):
        return DrtApplicationExpression(self, other)
    
    def make_VariableExpression(self, variable):
        return DrtVariableExpression(variable)
   

    def normalize(self):
        """Rename auto-generated unique variables"""
        print "visited %s", 'TemporalExpression'
        def f(e):
            if isinstance(e, Variable):
                if re.match(r'^z\d+$', e.name) or re.match(r'^[et]0\d+$', e.name):
                    return set([e])
                else:
                    return set([])
            else: 
                combinator = lambda * parts: reduce(operator.or_, parts)
                return e.visit(f, combinator, set())
        
        result = self
                
        for i, v in enumerate(sorted(list(f(self)))):
            if is_eventvar(v.name):
                newVar = 'e0%s' % (i + 1)
            elif is_timevar(v.name):
                newVar = 't0%s' % (i + 1)
            elif is_statevar(v.name):
                newVar = 's0%s' % (i + 1)
            else:
                newVar = 'z%s' % (i + 1)
            result = result.replace(v,
                        DrtVariableExpression(Variable(newVar)), True)
        return result


def ref_type(referent):
    """Checks a referent type and returns corresponding predicate"""
    ref_cond = None
    if is_eventvar(referent.name):
        ref_cond = drt.DrtConstantExpression(Variable("event"))
    elif is_statevar(referent.name):
        ref_cond = drt.DrtConstantExpression(Variable("state"))
    elif is_timevar(referent.name):
        ref_cond = drt.DrtConstantExpression(Variable("time"))
    else:
        ref_cond = drt.DrtConstantExpression(Variable("individual"))
    
    return DrtApplicationExpression(ref_cond,DrtAbstractVariableExpression(referent))


class DRS(AbstractDrs, drt.DRS):
    """A Temporal Discourse Representation Structure."""
    
    def fol(self):
        if not self.conds:
            raise Exception("Cannot convert DRS with no conditions to FOL.")
        accum = reduce(AndExpression, [c.fol() for c in self.conds])
        for ref in self.refs[::-1]:
            accum = ExistsExpression(ref, AndExpression(accum,ref_type(ref).fol()))
        return accum
    

    def replace(self, variable, expression, replace_bound=False):
        """Replace all instances of variable v with expression E in self,
        where v is free in self."""
        try:
            #if a bound variable is the thing being replaced
            i = self.refs.index(variable)
            if not replace_bound:
                return self
            else: 
                return self.__class__(self.refs[:i]+[expression.variable]+self.refs[i+1:],
                           [cond.replace(variable, expression, True) for cond in self.conds])
        except ValueError:
            #variable not bound by this DRS
            
            # any bound variable that appears in the expression must
            # be alpha converted to avoid a conflict
            for ref in (set(self.refs) & expression.free()):
                newvar = unique_variable(ref) 
                newvarex = DrtVariableExpression(newvar)
                i = self.refs.index(ref)
                self = DRS(self.refs[:i]+[newvar]+self.refs[i+1:],
                           [cond.replace(ref, newvarex, True) 
                            for cond in self.conds])
                
            #replace in the conditions
            return self.__class__(self.refs,
                       [cond.replace(variable, expression, replace_bound) 
                        for cond in self.conds])
            
    def simplify(self):
        simplified_conds = []
        for cond in self.conds:
            if cond is not None:
                simplified_conds.append(cond.simplify())
        return self.__class__(self.refs, simplified_conds)
    
    def resolve(self, trail=[]):
        resolved_conds = [cond.resolve(trail + [self]) for cond in self.conds]
        result_conds = []
        for cond in resolved_conds:
            if cond is not None:
                result_conds.append(cond)
        return self.__class__(self.refs, result_conds)
 


class DrtLambdaExpression(drt.DrtLambdaExpression):
    def alpha_convert(self, newvar):
        """Rename all occurrences of the variable introduced by this variable
        binder in the expression to @C{newvar}.
        @param newvar: C{Variable}, for the new variable
        """

        return self.__class__(newvar, self.term.replace(self.variable, 
                          DrtVariableExpression(newvar), True))

    def replace(self, variable, expression, replace_bound=False):
        """@see: Expression.replace()"""
        assert isinstance(variable, Variable), "%s is not a Variable" % variable
        assert isinstance(expression, Expression), "%s is not an Expression" % expression
        #if the bound variable is the thing being replaced
        if self.variable == variable:
            if replace_bound: 
                assert isinstance(expression, DrtAbstractVariableExpression), \
                       "%s is not a AbstractVariableExpression" % expression
                return self.__class__(expression.variable,
                                      self.term.replace(variable, expression, True))
            else: 
                return self
        else:
            # if the bound variable appears in the expression, then it must
            # be alpha converted to avoid a conflict
            if self.variable in expression.free():
                self = self.alpha_convert(unique_variable(pattern=self.variable))
                
            #replace in the term
            return self.__class__(self.variable,
                                  self.term.replace(variable, expression, replace_bound))

    def get_refs(self, recursive=False):
        """@see: AbstractExpression.get_refs()"""
        return []




class ConcatenationDRS(AbstractDrs, drt.ConcatenationDRS):
    """DRS of the form '(DRS + DRS)'"""
    def replace(self, variable, expression, replace_bound=False):
        """Replace all instances of variable v with expression E in self,
        where v is free in self."""
        first = self.first
        second = self.second

        # If variable is bound by both first and second 
        if isinstance(first, DRS) and isinstance(second, DRS) and \
           variable in (set(first.get_refs(True)) & set(second.get_refs(True))):
            first  = first.replace(variable, expression, True)
            second = second.replace(variable, expression, True)
            
        # If variable is bound by first
        elif isinstance(first, DRS) and variable in first.refs:
            if replace_bound: 
                first  = first.replace(variable, expression, replace_bound)
                second = second.replace(variable, expression, replace_bound)

        # If variable is bound by second
        elif isinstance(second, DRS) and variable in second.refs:
            if replace_bound:
                first  = first.replace(variable, expression, replace_bound)
                second = second.replace(variable, expression, replace_bound)

        else:
            # alpha convert every ref that is free in 'expression'
            for ref in (set(self.get_refs(True)) & expression.free()):         
                v = DrtVariableExpression(unique_variable(ref))
                first  = first.replace(ref, v, True)
                second = second.replace(ref, v, True)

            first  = first.replace(variable, expression, replace_bound)
            second = second.replace(variable, expression, replace_bound)
            
        return self.__class__(first, second)

    def simplify(self):
        first = self.first.simplify()
        second = self.second.simplify()

        if isinstance(first, DRS) and isinstance(second, DRS):
            # For any ref that is in both 'first' and 'second'
            for ref in (set(first.get_refs(True)) & set(second.get_refs(True))):
                # alpha convert the ref in 'second' to prevent collision
                newvar = DrtVariableExpression(unique_variable(ref))
                second = second.replace(ref, newvar, True)
            
            return DRS(first.refs + second.refs, first.conds + second.conds)
        else:
            return self.__class__(first,second)




class StateVariableExpression(IndividualVariableExpression):
    """This class represents variables that take the form of a single lowercase
    's' character followed by zero or more digits."""
    type = STATE_TYPE

    
    
def DrtVariableExpression(variable):
    """
    This is a factory method that instantiates and returns a subtype of 
    C{DrtAbstractVariableExpression} appropriate for the given variable.
    Extended with DrtStateVariableExpression for state referents.
    """
    if is_statevar(variable.name):
        return DrtStateVariableExpression(variable)
    elif is_uttervar(variable.name):
        return DrtUtterVariableExpression(variable)
    else:
        return drt.DrtVariableExpression(variable)

class DrtStateVariableExpression(DrtIndividualVariableExpression, StateVariableExpression):
    """Type of discourse referents of state"""
    pass


class DrtStateApplicationExpression(DrtApplicationExpression):
    """Type of application expression with state argument"""
    pass


class DrtUtterVariableExpression(DrtTimeVariableExpression):
    """Type of utterance time referent"""
    pass


class DrtFindUtterTimeExpression(DrtApplicationExpression):
    """Type of application expression looking to equate its argument with utterance time"""
    def resolve(self, trail=[], output=[]):       
        for ancestor in trail:          
            for ref in ancestor.get_refs():
                refex = DrtVariableExpression(ref)
                if isinstance(refex, DrtUtterVariableExpression):                   
                    return self.make_EqualityExpression(self.argument, refex)
        
        raise UtteranceTimeTimeResolutionException("Variable '%s' does not "
                            "resolve to anything." % self.argument)
        
class UtteranceTimeTimeResolutionException(Exception):
    pass


class DrtFindEventualityExpression(DrtApplicationExpression):
    """Comprises reference point REFER condition and aspectual PERF condition.
    DRS-condition REFER(e) or REFER(s) returns a temporal condition that
    relates given eventuality and some previous event or state. In the simplified
    version of the reference point selection algorithm, the condition picks out the
    most recent event and, depending on the type of its argument, returns either an
    earlier(e*,e) or include(s,e*), where e* is the reference point and e/s is the given
    eventuality. In case there is no event in the previous discourse, the most recent
    state is taken as the reference point and overlap(s*,s) or include(s*,e) is introduced
    depending on the type of the given eventuality.
    PERF(e) locates the most recent state referent s and resolves to a condition abut(e,s).
    PERF(s) locates the most recent state referent s* and resolves to a condition abut(e*,s*),
    e* = end(s) and adds a new event referent e*. Note that end(.) is an operator on states
    that returns events."""
    def resolve(self, trail=[], output=[]):
        state_reference_point = None
        """state reference point in case there are no previous events"""
        for ancestor in trail[::-1]:                               
            
            search_list = ancestor.get_refs()
            
            if self.argument.variable in search_list:
                """Described eventuality in the object's referents?
                Take refs' list up to described eventuality"""
                search_list = search_list[:search_list.index(self.argument.variable)]
                
                for ref in search_list[::-1]:
                    """search for the most recent reference"""
                    refex = DrtVariableExpression(ref)
                
                    if isinstance(refex, DrtEventVariableExpression) and \
                    not (refex == self.argument) and not self.function.variable.name == DrtTokens.PERF:
                        
                        if isinstance(self.argument,DrtEventVariableExpression):
                            """In case given eventuality is an event, return earlier"""                 
                            return DrtStateApplicationExpression(DrtStateApplicationExpression(DrtTokens.EARLIER,refex),self.argument)
                        
                        elif isinstance(self.argument, DrtStateVariableExpression):
                            """In case given eventuality is a state, return include"""
                            return DrtStateApplicationExpression(DrtStateApplicationExpression(DrtTokens.INCLUDE,self.argument),refex)    
                    
                    elif not state_reference_point and \
                        isinstance(refex, DrtStateVariableExpression) and \
                        not (refex == self.argument):
                        """In case no event is found, locate the most recent state"""
                        state_reference_point = refex                            
                       
        if state_reference_point:
            if self.function.variable.name == DrtTokens.PERF:
                """in case we are dealing with PERF"""
                if isinstance(self.argument, DrtEventVariableExpression):
                    """Reference point is a state and described eventuality an event,
                    return event abuts on state"""
                    return DrtStateApplicationExpression(DrtStateApplicationExpression(DrtTokens.ABUT,self.argument),state_reference_point)
                if isinstance(self.argument, DrtStateVariableExpression):
                    """Reference point is a state and described eventuality a state,
                    then add an event referent to the ancestor's refs list and two conditions
                    that that event is the end of eventuality (function needed!!!) and
                    that event abuts on ref.state"""
                    termination_point = DrtEventVariableExpression(unique_variable(DrtTokens.EVENT))
                    # hackish append
                    ancestor.refs.append(termination_point)
                    ancestor.conds.append(drt.DrtEqualityExpression(termination_point,DrtApplicationExpression(DrtTokens.END,self.argument)))
                    
                    return DrtStateApplicationExpression(DrtStateApplicationExpression(DrtTokens.ABUT,termination_point),state_reference_point)
                
            elif isinstance(self.argument, DrtStateVariableExpression):
                """Reference point is a state and given eventuality is also a state,
                return overlap"""
                return DrtStateApplicationExpression(DrtStateApplicationExpression(DrtTokens.OVERLAP,state_reference_point),self.argument)    
            elif isinstance(self.argument, DrtEventVariableExpression):
                """Reference point is a state and given eventuality is an event,
                return include"""
                return DrtStateApplicationExpression(DrtStateApplicationExpression(DrtTokens.INCLUDE,state_reference_point),self.argument)
        else:
            """no suitable reference found"""
            return None
 


class DrtParser(drt.DrtParser):
    """DrtParser producing conditions and referents for temporal logic"""
    
    def handle_DRS(self, tok, context):
        drs = drt.DrtParser.handle_DRS(self, tok, context)
        location_time = None
        
        for cond in drs.conds:
            if isinstance(cond,DrtFindEventualityExpression):
                """PERF(.) gives rise to a DrtFindRefPointApplicationExpression;
                in case it is among the DRS-conditions, the eventuality carried by
                this DRS does not give rise to a REFER(.) condition"""
                return DRS(drs.refs, drs.conds)
           
            if not location_time and isinstance(cond, DrtLocationTimeApplicationExpression):
                location_time = cond.argument
        
        for ref in drs.refs:
            """Change DRS: introduce REFER(s/e) condition, add INCLUDE/OVERLAP
            conditions to the semantics of infinitives (triggered by LOCPRO)
            and given some trigger from DrtTokens.TENSE put UTTER(.) condition and,
            for PAST and FUT, earlier(.,.) condition w.r.t. to some new discourse
            referent bound to utterance time."""
        
            if is_statevar(ref.name):
                """Adds REFER(s) condition."""
                if location_time:
                    """Relates location time and eventuality"""
                    drs.conds.append(DrtTimeApplicationExpression(DrtTimeApplicationExpression(DrtTokens.OVERLAP, location_time), DrtStateVariableExpression(ref)))
                drs.conds.append(DrtFindEventualityExpression(DrtTokens.REFER, DrtVariableExpression(ref)))
                
            if drt.is_eventvar(ref.name):
                """Adds REFER(e) condition."""
                if location_time:
                    """Relates location time and eventuality"""
                    drs.conds.append(DrtTimeApplicationExpression(DrtTimeApplicationExpression(DrtTokens.INCLUDE, location_time), DrtStateVariableExpression(ref)))
                drs.conds.append(DrtFindEventualityExpression(DrtTokens.REFER, DrtVariableExpression(ref)))
            
            if drt.is_timevar(ref.name) and not is_uttervar(ref.name):
                """Relates location time with utterance time"""

                tense_cond = [c for c in drs.conds if isinstance(c, DrtApplicationExpression) and \
                               c.function in DrtTokens.TENSE and DrtVariableExpression(ref) == c.argument]
                if not tense_cond == []:
                    if tense_cond[0].function == DrtTokens.PRES:
                        """Put UTTER(t) instead"""
                        drs.conds[drs.conds.index(tense_cond[0])] = DrtFindUtterTimeExpression(DrtTokens.UTTER, DrtTimeVariableExpression(ref))
                        
                    else:
                        """Put new discourse referent and bind it to utterance time
                        by UTTER(.) and also add earlier(.,.) condition"""
                        utter_time = unique_variable(ref)
                        drs.refs.insert(0, utter_time)
                        drs.conds[drs.conds.index(tense_cond[0])] = DrtFindUtterTimeExpression(DrtTokens.UTTER, DrtTimeVariableExpression(utter_time))

                        if tense_cond[0].function == DrtTokens.PAST:
                            drs.conds.append(DrtTimeApplicationExpression(DrtTimeApplicationExpression(DrtTokens.EARLIER, DrtTimeVariableExpression(ref)), DrtTimeVariableExpression(utter_time)))
                        
                        else:
                            drs.conds.append(DrtTimeApplicationExpression(DrtTimeApplicationExpression(DrtTokens.EARLIER, DrtTimeVariableExpression(utter_time)), DrtTimeVariableExpression(ref)))
                        
        return DRS(drs.refs, drs.conds)

    
    def get_BooleanExpression_factory(self, tok):
        """This method serves as a hook for other logic parsers that
        have different boolean operators"""
        
        if tok == DrtTokens.DRS_CONC:
            return ConcatenationDRS
        elif tok in DrtTokens.OR:
            return drt.DrtOrExpression
        elif tok in DrtTokens.IMP:
            return drt.DrtImpExpression
        elif tok in DrtTokens.IFF:
            return drt.DrtIffExpression
        else:
            return None

    def make_VariableExpression(self, name):
        return DrtVariableExpression(Variable(name))

    def make_ApplicationExpression(self, function, argument):
        
        if function == DrtTokens.PERFECT:
            return DrtFindEventualityExpression(function, argument)
        
        elif isinstance(argument, DrtStateVariableExpression):
            return DrtStateApplicationExpression(function, argument)
               
        else:
            return drt.DrtParser.make_ApplicationExpression(self, function, argument)
        
    def make_LambdaExpression(self, variables, term):
        return DrtLambdaExpression(variables, term)


    
##############################
# Test
##############################

    
def test():
    
    tester = util.Tester('file:../data/grammar.fcfg', DrtParser)
    
    expr = tester.parse('The car has written a letter', utter=True).resolve()
    print expr
    expr.draw()

if __name__ == "__main__":
    test()