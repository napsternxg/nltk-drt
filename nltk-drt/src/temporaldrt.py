"""
Temporal logic extension of nltk.sem.drt
Keeps track of time referents and temporal DRS-conditions. 

New function resolving LOCPRO(t) from a non-finite verb
to the location time referent introduced by a finite auxiliary. 
"""

__author__ = "Peter Makarov"
__version__ = "1.0"
__date__ = "Tue, 24 Aug 2010"

import re
import operator

from nltk.sem.logic import Variable
from nltk.sem.logic import EqualityExpression, ApplicationExpression, ExistsExpression, AndExpression
from nltk.sem.logic import IndividualVariableExpression
from nltk.sem.logic import _counter, is_eventvar, is_funcvar
from nltk.sem.logic import BasicType
from nltk.sem.logic import Expression
from nltk.sem.logic import ParseException
from nltk.sem.drt import DrsDrawer, AnaphoraResolutionException

import nltk.sem.drt as drt


class TimeType(BasicType):
    """
    Basic type of times added on top of nltk.sem.logic.
    """
    def __str__(self):
        return 'i'

    def str(self):
        return 'TIME'

TIME_TYPE = TimeType()

class StateType(BasicType):
    """
    Basic type of times added on top of nltk.sem.logic.
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

def is_timevar(expr):
    """
    An time variable must be a single lowercase 't' or 'n' character followed by
    zero or more digits. Do we need a separate type for utterance time n?
    
    @param expr: C{str}
    @return: C{boolean} True if expr is of the correct form 
    """
    assert isinstance(expr, str), "%s is not a string" % expr
    return re.match(r'^[tn]\d*$', expr)


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

class TimeVariableExpression(IndividualVariableExpression):
    """This class represents variables that take the form of a single lowercase
    'i' character followed by zero or more digits."""
    type = TIME_TYPE
    
class StateVariableExpression(IndividualVariableExpression):
    """This class represents variables that take the form of a single lowercase
    's' character followed by zero or more digits."""
    type = STATE_TYPE

def is_unary_predicate(expr):
    """check whether the given expression is an unary predicate"""
    return isinstance(expr, DrtApplicationExpression) and isinstance(expr.function, DrtAbstractVariableExpression)

class ReverseIterator:
    """A generator which yields the given sequence in a reverse order"""
    def __init__(self, sequence, start=-1):
        self.sequence = sequence
        self.start = start
    def __iter__(self):
        if self.start > 0:
            i = self.start + 1
        else: 
            i = len(self.sequence) + self.start + 1
        while i > 0:
            i -= 1
            yield self.sequence[i]

class Reading(list):
    """
    A single reading, consists of a list of operations
    each operation is a tuple of a drs and a function,
    where the function would be executed on the given drs
    when the reading is generated
    """
    pass

class VariableReplacer(object):
    """A generic variable replacer functor to be used in readings"""
    def __init__(self, var, new_var, remove_ref=True):
        self.var = var
        self.new_var = new_var
        self.remove_ref = remove_ref
    def __call__(self, drs):
        if self.remove_ref:
            drs.refs.remove(self.var)
        return drs.__class__(drs.refs, [cond.replace(self.var, self.new_var, False) for cond in drs.conds])

class ConditionRemover(object):
    """A generic condition remover functor to be used in readings"""
    def __init__(self, cond_index):
        self.cond_index = cond_index
    def __call__(self, drs):
        drs.conds.pop(self.cond_index)
        return drs

class DrtTokens(drt.DrtTokens):
    OPEN_BRACE = '{'
    CLOSE_BRACE = '}'
    PUNCT = [OPEN_BRACE, CLOSE_BRACE]
    SYMBOLS = drt.DrtTokens.SYMBOLS + PUNCT
    TOKENS = drt.DrtTokens.TOKENS + PUNCT
    NEWINFO_DRS = 'NEWINFO'
    PROPER_NAME_DRS = 'PROP'
    DEFINITE_DESCRIPTION_DRS = 'DEF'
    PRONOUN_DRS = 'PRON'
    PRESUPPOSITION_DRS = [PROPER_NAME_DRS, DEFINITE_DESCRIPTION_DRS, PRONOUN_DRS]
    PRONOUN = 'PRO'
    REFLEXIVE_PRONOUN = 'RPRO'
    POSSESSIVE_PRONOUN = 'PPRO'
    
    ################ Some temporal rubbish ##############
    
    LOCATION_TIME = 'LOCPRO'
    UTTER_TIME = 'UTTER'
    REFER_TIME = 'REFER'
    PERF = 'PERF'
    UTTER = "UTTER"
    REFER = "REFER"
    OVERLAP = "overlap"
    EARLIER = "earlier"
    INCLUDE = "include"
    ABUT = "abut"
    END = "end"
    TEMP_CONDS = [OVERLAP, EARLIER, INCLUDE]
    
    PAST = "PAST"
    PRES = "PRES"
    FUT = "FUT"
    
    TENSE = [PAST, PRES, FUT]

class AbstractDrs(drt.AbstractDrs):
    """
    This is the base abstract Temporal DRT Expression from which every Temporal DRT 
    Expression extends.
    """

    def applyto(self, other):
        return DrtApplicationExpression(self, other)
    
    def __neg__(self):
        return DrtNegatedExpression(self)

    def __or__(self, other):
        assert isinstance(other, AbstractDrs)
        return DrtOrExpression(self, other)

    def __gt__(self, other):
        assert isinstance(other, AbstractDrs)
        return DrtImpExpression(self, other)

    def __lt__(self, other):
        assert isinstance(other, AbstractDrs)
        return DrtIffExpression(self, other)

    def __add__(self, other):
        return ConcatenationDRS(self, other)
    
    def __deepcopy__(self, memo):
        return self.deepcopy()
    
    def make_EqualityExpression(self, first, second):
        return DrtEqualityExpression(first, second)

    def make_VariableExpression(self, variable):
        return DrtVariableExpression(variable)

    def normalize(self):
        """Rename auto-generated unique variables"""
        print "visited %s", 'TemporalExpression'
        def f(e):
            if isinstance(e, Variable):
                if re.match(r'^z\d+$', e.name) or re.match(r'^[est]0\d+$', e.name):
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
                        self.make_VariableExpression(Variable(newVar)), True)
        return result
    
    def substitute_bindings(self, bindings):
        expr = self
        for var in expr.variables():
            val = bindings.get(var, None)
            if val:
                if isinstance(val, Variable):
                    val = DrtVariableExpression(val)
                elif isinstance(val, Expression):
                    val = val.substitute_bindings(bindings)
                elif isinstance(val, str):
                    val = DrtFeatureExpression(Variable(val))
                else:
                    raise ValueError('Can not substitute a non-expression '
                                         'value into an expression: %r' % (val,))
                expr = expr.replace(var, val)
        return expr.simplify()
    
    def readings(self, verbose=False):
        """
        This method does the whole job of collecting multiple readings.
        We aim to get new readings from the old ones by resolving
        presuppositional DRSs one by one. Every time one presupposition
        is resolved, new readings are created and replace the old ones,
        until there are no presuppositions left to resolve.
        """
        readings = []

        def get_operations(expr):
            ops = expr._readings()
            if ops:
                return [(expr, ops[0])]
            else:
                readings.append(expr)
                return []

        operations = get_operations(self)

        while operations:
            # Go through the list of readings we already have
            new_operations = []
            for reading, operation_list in operations:
                # If a presupposition resolution took place, _readings() 
                # returns a tuple (DRS, operation). Otherwise
                # it will return a None.
                for operation in operation_list:
                    new_reading = reading.deepcopy(operation)
                    if verbose:
                        print("reading: %s" % new_reading)
                    new_operations.extend(get_operations(new_reading))

            operations = new_operations

        return readings
    
    def _readings(self, trail=[]):
        raise NotImplementedError()

class DRS(AbstractDrs, drt.DRS):
    """A Temporal Discourse Representation Structure."""
    
    def fol(self):
        if not self.conds:
            raise Exception("Cannot convert DRS with no conditions to FOL.")
        accum = reduce(AndExpression, [c.fol() for c in self.conds])
        for ref in ReverseIterator(self.refs):
            accum = ExistsExpression(ref, AndExpression(accum,DRS._ref_type(ref).fol()))
        return accum

    @staticmethod
    def _ref_type(referent):
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
    

    def replace(self, variable, expression, replace_bound=False):
        """Replace all instances of variable v with expression E in self,
        where v is free in self."""
        if variable in self.get_refs():
            #if a bound variable is the thing being replaced
            if not replace_bound:
                return self
            else:
                if variable in self.refs:
                    i = self.refs.index(variable)
                    refs = self.refs[:i]+[expression.variable]+self.refs[i+1:]
                else:
                    refs = self.refs
                return self.__class__(refs,
                           [cond.replace(variable, expression, True) for cond in self.conds])
        else:
            #variable not bound by this DRS
            
            # any bound variable that appears in the expression must
            # be alpha converted to avoid a conflict
            for ref in (set(self.get_refs()) & expression.free()):
                newvar = unique_variable(ref) 
                newvarex = DrtVariableExpression(newvar)
                if ref in self.refs:
                    i = self.refs.index(ref)
                    refs = self.refs[:i]+[newvar]+self.refs[i+1:]
                else:
                    refs = self.refs
                self = self.__class__(refs,
                           [cond.replace(ref, newvarex, True) 
                            for cond in self.conds])
                
            #replace in the conditions
            return self.__class__(self.refs,
                       [cond.replace(variable, expression, replace_bound) 
                        for cond in self.conds])
            
    def free(self, indvar_only=True):
        """@see: Expression.free()"""
        conds_free = reduce(operator.or_, 
                            [c.free(indvar_only) for c in self.conds], set()) 
        return conds_free - (set(self.refs) | reduce(operator.or_, [set(c.refs) for c in self.conds if isinstance(c, PresuppositionDRS)], set()))

    def get_refs(self, recursive=False):
        """@see: AbstractExpression.get_refs()"""
        if recursive:
            cond_refs = reduce(operator.add, 
                               [c.get_refs(True) for c in self.conds], [])
            return self.refs + cond_refs
        else:
            return self.refs + reduce(operator.add, [c.refs for c in self.conds if isinstance(c, PresuppositionDRS)], [])

    def deepcopy(self, operations=[]):
        """This method returns a deep copy of the DRS.
        Optionally, it can take a list of lists of tuples (DRS, function) 
        as an argument and generate a reading by performing 
        a substitution in the DRS as specified by the function.
        @param operations: a list of lists of tuples
        """
        functions = [function for drs, function in operations if drs is self]
        newdrs = self.__class__(list(self.refs), [cond.deepcopy(operations) for cond in self.conds])
        for function in functions:
            newdrs = function(newdrs)
        return newdrs

    def simplify(self):
        return self.__class__(self.refs, [cond.simplify() for cond in self.conds])

    def _readings(self, trail=[]):
        """get the readings for this DRS"""
        for i, cond in enumerate(self.conds):
            readings = cond._readings(trail + [self])
            if readings:
                if readings[1]:
                    for reading in readings[0]:
                        reading.append((self, ConditionRemover(i)))
                return readings[0], False

    def str(self, syntax=DrtTokens.NLTK):
        if syntax == DrtTokens.PROVER9:
            return self.fol().str(syntax)
        else:
            return '([%s],[%s])' % (','.join([str(r) for r in self.refs]),
                                    ', '.join([c.str(syntax) for c in self.conds]))

def DrtVariableExpression(variable):
    """
    This is a factory method that instantiates and returns a subtype of 
    C{DrtAbstractVariableExpression} appropriate for the given variable.
    Extended with DrtTimeVariableExpression for time referents.
    """

    if is_indvar(variable.name):
        return DrtIndividualVariableExpression(variable)
    elif is_funcvar(variable.name):
        return DrtFunctionVariableExpression(variable)
    elif is_eventvar(variable.name):
        return DrtEventVariableExpression(variable)
    elif is_statevar(variable.name):
        return DrtStateVariableExpression(variable)
    elif is_uttervar(variable.name):
        return DrtUtterVariableExpression(variable)
    elif is_timevar(variable.name):
        return DrtTimeVariableExpression(variable)
    else:
        return DrtConstantExpression(variable)
    

class DrtAbstractVariableExpression(AbstractDrs, drt.DrtAbstractVariableExpression):   
    def _readings(self, trail=[]):
        return None
    
    def deepcopy(self, operations=[]):
        return self.__class__(self.variable)

class DrtIndividualVariableExpression(DrtAbstractVariableExpression, drt.DrtIndividualVariableExpression):
    pass

class DrtFunctionVariableExpression(DrtAbstractVariableExpression, drt.DrtFunctionVariableExpression):
    pass

class DrtEventVariableExpression(DrtIndividualVariableExpression, drt.DrtEventVariableExpression):
    pass

class DrtConstantExpression(DrtAbstractVariableExpression, drt.DrtConstantExpression):
    pass

class DrtFeatureExpression(DrtConstantExpression):
    """An expression for a single syntactic feature"""
    pass

class DrtFeatureConstantExpression(DrtConstantExpression):
    """A constant expression with syntactic features attached"""
    def __init__(self, variable, features):
        DrtConstantExpression.__init__(self, variable)
        self.features = features

    def replace(self, variable, expression, replace_bound=False):
        """@see: Expression.replace()"""
        assert isinstance(variable, Variable), "%s is not an Variable" % variable
        assert isinstance(expression, Expression), "%s is not an Expression" % expression
        return self.__class__(DrtConstantExpression.replace(self, variable, expression, replace_bound).variable, [feature.replace(variable, expression, replace_bound) for feature in self.features])

    def visit(self, function, combinator, default):
        """@see: Expression.visit()"""
        re = combinator(function(self.variable), reduce(combinator, 
                      [function(e) for e in self.features], default))
        return re

    def str(self, syntax=DrtTokens.NLTK):
        return str(self.variable) + "{" + ",".join([str(feature) for feature in self.features]) + "}"
    
    def deepcopy(self, operations=[]):
        return self.__class__(self.variable, self.features)
    
    def fol(self):
        return DrtConstantExpression(self.variable)

class DrtProperNameExpression(DrtConstantExpression):
    """Class for proper names"""
    pass

class DrtNegatedExpression(AbstractDrs, drt.DrtNegatedExpression):
    def _readings(self, trail=[]):
        return self.term._readings(trail + [self])

    def deepcopy(self, operations=None):
        return self.__class__(self.term.deepcopy(operations))

class DrtLambdaExpression(AbstractDrs, drt.DrtLambdaExpression):
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

    def _readings(self, trail=[]):
        return self.term._readings(trail + [self])
    
    def deepcopy(self, operations=[]):
        return self.__class__(self.variable, self.term.deepcopy(operations))
    
    def get_refs(self, recursive=False):
        """@see: AbstractExpression.get_refs()"""
        return []

class DrtBooleanExpression(AbstractDrs, drt.DrtBooleanExpression):
    def _readings(self, trail=[]):
        first_readings = self.first._readings(trail + [self])
        if first_readings:
            return first_readings
        else:
            return self.second._readings(trail + [self])
    
    def deepcopy(self, operations=[]):
        return self.__class__(self.first.deepcopy(operations), self.second.deepcopy(operations))

    def simplify(self):
        """When dealing with DRSs, it is good to have unique names for
        the referents bound by each DRS."""
        if isinstance(self.first, DRS) and isinstance(self.second, DRS):
            new_second = self.second
            for ref in set(self.first.get_refs(True)) & set(self.second.get_refs(True)):
                newref = DrtVariableExpression(unique_variable(ref))
                new_second = self.second.replace(ref,newref,True)

            return drt.DrtBooleanExpression.simplify(self.__class__(self.first, new_second))
        
        else: return drt.DrtBooleanExpression.simplify(self)
    
class DrtOrExpression(DrtBooleanExpression, drt.DrtOrExpression):
    pass

class DrtImpExpression(DrtBooleanExpression, drt.DrtImpExpression):
    def _readings(self, trail=[]):
        first_readings = self.first._readings(trail + [self])
        if first_readings:
            return first_readings
        else:
            return self.second._readings(trail + [self, self.first])

class DrtIffExpression(DrtBooleanExpression, drt.DrtIffExpression):
    pass

class DrtEqualityExpression(AbstractDrs, drt.DrtEqualityExpression):
    def _readings(self, trail=[]):
        return None
    
    def deepcopy(self, operations=[]):
        return self.__class__(self.first.deepcopy(operations), self.second.deepcopy(operations))

class ConcatenationDRS(DrtBooleanExpression, drt.ConcatenationDRS):
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
            
            """DRS type is derived from the first member or from the second one"""
            drs_type = first.__class__ if isinstance(first, PresuppositionDRS) else second.__class__
            return drs_type(first.refs + second.refs, first.conds + second.conds)
        else:
            return self.__class__(first,second)

class DrtApplicationExpression(AbstractDrs, drt.DrtApplicationExpression):
    
    def fol(self):
        if self.is_propername():
            return EqualityExpression(self.function.fol(),
                                      self.argument.fol())
                 
        else: return ApplicationExpression(self.function.fol(), 
                                           self.argument.fol())
        
        
    def is_propername(self):
        """
        A proper name is capitalised. We assume that John(x) uniquely
        identifies the bearer of the name John and so, when going from Kamp & Reyle's
        DRT format into classical FOL logic, we change a condition like that into John = x.   

        @return: C{boolean} True if expr is of the correct form 
        """
        return isinstance(self.function, DrtConstantExpression) and\
        self.function.variable.name.istitle()

    def _readings(self, trail=[]):
        function_readings = self.function._readings(trail + [self])
        if function_readings:
            return function_readings
        else:
            return self.argument._readings(trail + [self])

    def deepcopy(self, operations=[]):
        return self.__class__(self.function.deepcopy(operations), self.argument.deepcopy(operations))


class DrtTimeVariableExpression(DrtIndividualVariableExpression, TimeVariableExpression):
    """Type of discourse referents of time"""
    pass

class DrtStateVariableExpression(DrtIndividualVariableExpression, StateVariableExpression):
    """Type of discourse referents of state"""
    pass

class DrtTimeApplicationExpression(DrtApplicationExpression):
    """Type of DRS-conditions used in temporal logic"""
    pass

class DrtEventualityApplicationExpression(DrtApplicationExpression):
    """Type of application expression with state argument"""
    pass

class DrtUtterVariableExpression(DrtTimeVariableExpression):
    """Type of utterance time referent"""
    pass

class LocationTimeResolutionException(Exception):
    pass

class DrtLocationTimeApplicationExpression(DrtTimeApplicationExpression):
    def _readings(self, trail=[]):
        utter_time_search = False

        for drs in (ancestor for ancestor in ReverseIterator(trail) if isinstance(ancestor, DRS)):
            search_list = drs.refs
            
            if self.argument.variable in drs.refs:
                search_list = drs.refs[:drs.refs.index(self.argument.variable)]
            
            for ref in ReverseIterator(search_list):
                refex = DrtVariableExpression(ref)
                
                if isinstance(refex, DrtUtterVariableExpression):
                    """In case there is no location time referent that has not yet been used
                    to relate some eventuality to utterance time, use utter time as loc time."""
                    return [Reading([(trail[-1], VariableReplacer(self.argument.variable, refex))])], True
  
                elif not utter_time_search and isinstance(refex, DrtTimeVariableExpression) and \
                   not (refex == self.argument):
                                      
                    if any(isinstance(c, DrtApplicationExpression) and isinstance(c.function, DrtApplicationExpression) and \
                        c.function.argument == refex and (c.function.function.variable.name == DrtTokens.OVERLAP or \
                        c.function.function.variable.name == DrtTokens.INCLUDE) for c in drs.conds):
                        utter_time_search = True

                    else:
                        """Return first suitable antecedent expression"""
                        return [Reading([(trail[-1], VariableReplacer(self.argument.variable, refex))])], True
                                
        raise LocationTimeResolutionException("Variable '%s' does not "
                            "resolve to anything." % self.argument)
        
    class Replacer(object):
        def __init__(self, index, new_cond):
            self.index = index
            self.new_cond = new_cond
        def __call__(self, drs):
            drs.conds[self.index] = self.new_cond
            return drs

class DrtFindUtterTimeExpression(DrtApplicationExpression):
    """Type of application expression looking to equate its argument with utterance time"""
    def _readings(self, trail=[]):
        for ancestor in trail:    
            for ref in ancestor.get_refs():
                refex = DrtVariableExpression(ref)
                if isinstance(refex, DrtUtterVariableExpression):
                    
                    return [Reading([(trail[-1], VariableReplacer(self.argument.variable, refex))])], True                  
        
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
    def _readings(self, trail=[]):

        state_reference_point = None
        index = trail[-1].conds.index(self)
        """state reference point in case there are no previous events"""
        for drs in (ancestor for ancestor in ReverseIterator(trail) if isinstance(ancestor, DRS)):                               
            
            search_list = drs.refs
                        
            if drs is trail[-1]:
                """Described eventuality in the object's referents?
                Take refs' list up to described eventuality"""
                search_list = drs.refs[:drs.refs.index(self.argument.variable)]
                
            for ref in ReverseIterator(search_list):
                """search for the most recent reference"""
                refex = DrtVariableExpression(ref)
            
                if isinstance(refex, DrtEventVariableExpression) and \
                not (refex == self.argument) and not self.function.variable.name == DrtTokens.PERF:
                    
                    if isinstance(self.argument,DrtEventVariableExpression):
                        """In case given eventuality is an event, return earlier"""
                        return [Reading([(trail[-1], DrtFindEventualityExpression.Replacer(index,
                        self._combine(DrtTokens.EARLIER,refex,self.argument)))])], False               

                    
                    elif isinstance(self.argument, DrtStateVariableExpression):
                        """In case given eventuality is a state, return include"""
                        return [Reading([(trail[-1], DrtFindEventualityExpression.Replacer(index,
                        self._combine(DrtTokens.INCLUDE,self.argument,refex)))])], False               
     
                
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
                    
                    return [Reading([(trail[-1], DrtFindEventualityExpression.Replacer(index,
                    self._combine(DrtTokens.ABUT,self.argument,state_reference_point)))])], False                       

                    
                elif isinstance(self.argument, DrtStateVariableExpression):
                    """Reference point is a state and described eventuality a state,
                    then add an event referent to the ancestor's refs list and two conditions
                    that that event is the end of eventuality (function needed!!!) and
                    that event abuts on ref.state"""
                    termination_point = unique_variable(Variable("e"))
                    conds = [DrtEqualityExpression(DrtEventVariableExpression(termination_point), DrtApplicationExpression(self.make_ConstantExpression(DrtTokens.END),self.argument)),
                    self._combine(DrtTokens.ABUT,DrtEventVariableExpression(termination_point), state_reference_point)]
                    return [Reading([(trail[-1], DrtFindEventualityExpression.PerfReplacer(termination_point, index, conds))])], False
                    
                
            elif isinstance(self.argument, DrtStateVariableExpression):
                """Reference point is a state and given eventuality is also a state,
                return overlap"""
 
                return [Reading([(trail[-1], DrtFindEventualityExpression.Replacer(index,
                self._combine(DrtTokens.OVERLAP, state_reference_point, self.argument)))])], False               
        
            elif isinstance(self.argument, DrtEventVariableExpression):
                """Reference point is a state and given eventuality is an event,
                return include"""
                return [Reading([(trail[-1], DrtFindEventualityExpression.Replacer(index, 
                self._combine(DrtTokens.INCLUDE,state_reference_point,self.argument)))])], False               
                
        else:
            """no suitable reference found"""
            return [Reading([(trail[-1], ConditionRemover(index))])], False
        
    class Replacer(object):
        def __init__(self, index, new_cond):
            self.index = index
            self.new_cond = new_cond
        def __call__(self, drs):
            drs.conds[self.index] = self.new_cond
            return drs
        
    class PerfReplacer(object):
        def __init__(self, ref, index, conds):
            self.conds = conds
            self.index = index
            self.ref = ref
        def __call__(self, drs):
            drs.refs.append(self.ref) 
            drs.conds.remove(drs.conds[self.index])
            drs.conds.extend(self.conds)
            return drs

    def make_ConstantExpression(self,name):
        return DrtConstantExpression(Variable(name))
    
    def _combine(self, cond, arg1, arg2):
        """Combines two arguments into a DrtEventualityApplicationExpression
        that has another DrtEventualityApplicationExpression as its functor"""
        return DrtEventualityApplicationExpression(DrtEventualityApplicationExpression(self.make_ConstantExpression(cond),arg1),arg2)

class NewInfoDRS(DRS):
    pass

class PresuppositionDRS(DRS):
        
    def _readings(self, trail=[]):
        inner_readings = DRS._readings(self, trail)
        if inner_readings:
            return inner_readings
        else:
            self._init_presupp_data()
            return self._presupposition_readings(trail)
    
    def filter_drs(self, expr_list):
        """A generator that iterates over the drss in the trail and filters out PresuppositionDrs and NewInfoDrs objects"""
        return (expr for expr in expr_list if isinstance (expr, DRS) and\
                 not isinstance(expr, PresuppositionDRS) and\
                   not isinstance(expr, NewInfoDRS))
        
    def _find_outer_drs(self, trail):
        for drs in self.filter_drs(trail):
            return drs
    
    def is_possible_binding(self, cond):
        return is_unary_predicate(cond) and\
                self.has_same_features(cond) and\
                 cond.argument.__class__ is DrtIndividualVariableExpression
                
    def find_bindings(self, drs_list, collect_event_data=False):
        bindings = []
        if collect_event_data:
            event_data_map = {}
        is_bindable = True # do not allow forward binding
        for drs in drs_list:
            for cond in (c for c in drs.conds if isinstance(c, DrtApplicationExpression)):
                # Ignore conditions following the presupposition DRS
                if cond is self:
                    if not collect_event_data: 
                        break
                    is_bindable = False 
                if is_bindable and self.is_possible_binding(cond): 
                    bindings.append(cond)
                elif collect_event_data:
                    event_data = self.collect_event_data(cond)
                    if event_data:
                        event_data_map.setdefault(cond.argument.variable,[]).append(event_data)
        return (bindings, event_data_map) if collect_event_data else bindings
    
    def collect_event_data(self, cond):
        if isinstance(cond.function, DrtApplicationExpression) and\
              isinstance(cond.function.argument, DrtIndividualVariableExpression):
            return (cond.function.argument, cond.function.function)
        
    def is_presupposition_cond(self, cond):
        return True
        
    def _init_presupp_data(self):
        """ Return the referent, features and function name of the presupposition condition. Make sure it passes the check.
        @param check: a boolean function; a check that the presupposition condition must pass.""" 
        """In DRSs representing sentences like 'John, who owns a dog, feeds it',
        there will be more than one condition in the presupposition DRS, because the conditions from the relative clause
        will be put in the same box as the presupposition condition (e.g. 'John' -> John(x); 'the boy' -> boy(x)).
        This is also the case for presuppositions triggered by the definite article + noun,
        where, apart from a relative clause, there can be an adjective / adjectives modifying the noun 
        to complicate the matters.
        If an adjective and a noun both turn into one-place predicates, how do we distinguish between them?
        In our system, nouns are DrtFeatureConstantExpressions, and adjectives are simple DrtApplicationExpressions.
        But this is not set in stone, as we do not require the user to define any syntactic nominal features.
        """
        
        # The referent we are looking for is always the first on the list of referents of the presuppositional DRS.
        # The head of the presuppositional NP, however, doesn't have to be the first on the list of conditions.
        # It depends on how the lambda terms are written (e.g. for adjective, for complementizers).
        # If there are no agreement features in the grammar, we have to consider all unary predicates 
        # with this referent potential heads of the NP.
        presupp_cond_list = [cond for cond in self.conds if is_unary_predicate(cond) and cond.argument.variable == self.refs[0] and self.is_presupposition_cond(cond)]
        for cond in presupp_cond_list:
            if isinstance(cond.function, DrtFeatureConstantExpression): # this is the one
                # There can be more than one DrtFeatureConstantExpression on the conditions on list, e.g.
                # "Tom, a kind boy, took her hand", or "Tom, who is a kind boy,...", or "Linguist Grimm suggested ...", 
                # or "The distinguished physicist Einstein ...". But 'check' helps us find the right one.
                self.variable = cond.argument.variable
                self.features = cond.function.features
                self.function_name = cond.function.variable.name
                return

        self.variable = self.refs[0]
        self.features = None
        self.function_name = presupp_cond_list[0].variable.name
    
    def has_same_features(self, cond):
        return (not isinstance(cond.function, DrtFeatureConstantExpression) and not self.features) \
                or (isinstance(cond.function, DrtFeatureConstantExpression) and cond.function.features == self.features)
                
    class Binding(object):
        def __init__(self, presupp_drs, presupp_variable, presupp_funcname, antecedent_ref, condition_index):
            self.presupp_drs = presupp_drs
            self.presupp_variable = presupp_variable
            self.presupp_funcname = presupp_funcname
            self.antecedent_ref = antecedent_ref
            self.condition_index = condition_index
        def __call__(self, drs):
            """Put all conditions from the presupposition DRS
            (if presupposition condition is a proper name: except the proper name itself) into the drs, 
            and replace the presupposition condition referent in them with antecedent_ref"""
            #print "BINDING, drs", drs
            newdrs = self.presupp_drs.replace(self.presupp_variable, self.antecedent_ref, True)
            # There will be referents and conditions to move 
            # if there is a relative clause modifying the noun that has triggered the presuppositon
            drs.refs.extend([ref for ref in newdrs.refs \
                             if ref != self.antecedent_ref.variable])
            conds_to_move = [cond for cond in newdrs.conds \
                            if not is_unary_predicate(cond) or cond.function.variable.name != self.presupp_funcname]
            # Put the conditions at the position of the original presupposition DRS
            if self.condition_index is None: # it is an index, it can be zero
                drs.conds.extend(conds_to_move)
            else:
                drs.conds = drs.conds[:self.condition_index+1]+conds_to_move+drs.conds[self.condition_index+1:]
            return drs
            
    class InnerReplace(object):
        def __init__(self, presupp_drs, presupp_variable, presupp_funcname, antecedent_ref, class_to_call=None, condition_index=None):
            self.presupp_drs = presupp_drs
            self.presupp_variable = presupp_variable
            self.presupp_funcname = presupp_funcname
            self.antecedent_ref = antecedent_ref
            self.class_to_call = class_to_call
            self.condition_index = condition_index
        def __call__(self, drs):
                """In the conditions of the local DRS, replace the 
                referent of the presupposition condition with antecedent_ref"""
                if self.class_to_call:
                    func = self.class_to_call(self.presupp_drs, self.presupp_variable, self.presupp_funcname, self.antecedent_ref, self.condition_index)
                    drs = func(drs)
                return drs.replace(self.presupp_variable, self.antecedent_ref, True)
    
    class Accommodation(object):
        def __init__(self, presupp_drs, condition_index):
            """We need the condition index so that the conditions are not just appended to the list of conditions of the DRS,
            but inserted where the presuppositional DRS had been. The order of conditions is important, because it reflects
            the proximity of a possible antecedent, which affects antecedent ranking (and our architecture does not allow us to use the 
            index on the list of referents to reflect the proximity/focus)."""
            self.presupp_drs = presupp_drs
            self.condition_index = condition_index
        def __call__(self, drs):
            """Accommodation: put all referents and conditions from 
            the presupposition DRS into the given DRS"""
            drs.refs.extend(self.presupp_drs.refs)
            if self.condition_index is None:
                drs.conds.extend(self.presupp_drs.conds)
            else:
                drs.conds = drs.conds[:self.condition_index+1]+self.presupp_drs.conds+drs.conds[self.condition_index+1:]
            #print drs
            return drs
    
    def _get_condition_index(self, superordinate_drs, trail):
        """Use a for loop and 'is' to find the condition. 
        Do not use index(), because it calls a time-consuming equals method."""
        for ind, trailee in enumerate(trail):
            if trailee is superordinate_drs:
                # The condition might be not in superordinate_drs, but inside one of its conditions (however deep we might need to go)
                look_for = trail[ind+1] if ind < len(trail) -1 else self
                for i, cond in enumerate(superordinate_drs.conds):
                    if cond is look_for:
                        return i # condition_index
        return None
                            
class PronounDRS(PresuppositionDRS):
    """
    A superclass for DRSs for personal, reflexive, 
    and possessive pronouns
    """
    PRONOUNS = [DrtTokens.PRONOUN, DrtTokens.REFLEXIVE_PRONOUN, DrtTokens.POSSESSIVE_PRONOUN]

    def is_presupposition_cond(self, cond):
        return cond.function.variable.name in PronounDRS.PRONOUNS
    
    def _presupposition_readings(self, trail=[]):
        possible_bindings, event_data = self.find_bindings(self.filter_drs(trail), True)
        bindings = [cond for cond in possible_bindings if self._is_binding(cond, self._get_pro_events(event_data), event_data)]
        ranked_bindings = self._rank_bindings(bindings, event_data)
        return [Reading([(trail[-1], VariableReplacer(self.variable, cond.argument, False))]) for cond, rank in sorted(ranked_bindings, key=lambda e: e[1], reverse=True)], True

    def _get_pro_events(self, event_data):
        #in case pronoun participates in only one event, which has no other participants,
        #try to extend it with interlinked events
        #f.e. THEME(z5,z3), THEME(e,z5) where z3 only participates in event z5
        #will be extended to participate in e, but only in case z5 has one participant
        pro_events = [event for event, role in event_data.get(self.variable, ())]
        if len(pro_events) == 1:
            pro_event = pro_events[0]
            #number of participants in the pro_event
            participant_count = sum((1 for event_list in event_data.itervalues() for event, role in event_list if event == pro_event))
            # if there is only one participant in the pro_event and pro_event itself participates in other events
            if participant_count == 1 and pro_event.variable in event_data:
                pro_events.extend((event for event, role in event_data[pro_event.variable]))

        return set(pro_events)

    def _rank_bindings(self, bindings, event_data):
        #ranking system
        #increment ranking for matching roles and map the positions of antecedents
        if len(bindings) == 0:
            raise AnaphoraResolutionException("Variable '%s' does not "
                                "resolve to anything." % self.variable)
        elif len(bindings) == 1:
            bindings[0] = (bindings[0], 0)
        else:
            pro_roles = set((role for event, role in event_data.get(self.variable, ())))
            for index, variable in enumerate(bindings):
                var_roles = set((role for event_list in event_data.get(variable, ()) for event, role in event_list))
                bindings[index] = (variable, index + len(var_roles.intersection(pro_roles)))
        return bindings

    def _is_binding(self, cond, pro_events, event_data):
        #non reflexive pronouns can not resolve to variables having a role in the same event
        if self.function_name == DrtTokens.POSSESSIVE_PRONOUN:
            return True
        else:  
            variable = cond.argument.variable
            variable_events = set((event for event, role in event_data.get(variable,())))
        if self.function_name == DrtTokens.PRONOUN:
            return variable_events.isdisjoint(pro_events)
        elif self.function_name == DrtTokens.REFLEXIVE_PRONOUN:
            return not variable_events.isdisjoint(pro_events)
        else:
            return True

class ProperNameDRS(PresuppositionDRS):

    def _presupposition_readings(self, trail=[]):
        """A proper name always yields one reading: it is either global binding 
        or global accommodation (if binding is not possible)"""
        outer_drs = self._find_outer_drs(trail)
        inner_drs = trail[-1]
        possible_bindings = self.find_bindings([outer_drs])
        
        assert len(possible_bindings) <= 1
        condition_index = self._get_condition_index(outer_drs, trail)
        if possible_bindings:           
            # Return the reading
            antecedent_ref = possible_bindings[0].argument
            if inner_drs is outer_drs:
                return [Reading([(inner_drs, PresuppositionDRS.InnerReplace(self, self.variable, self.function_name, antecedent_ref, PresuppositionDRS.Binding, condition_index))])], True
            return [Reading([(outer_drs, PresuppositionDRS.Binding(self, self.variable, self.function_name, antecedent_ref, condition_index)),
                     (inner_drs, PresuppositionDRS.InnerReplace(self, self.variable, self.function_name, antecedent_ref, PresuppositionDRS.Binding, condition_index))])], True
        # If no suitable antecedent has been found in the outer DRS,
        # binding is not possible, so we go for accommodation instead.
        return [Reading([(outer_drs, PresuppositionDRS.Accommodation(self, condition_index))])], True
       
    def is_possible_binding(self, cond):
        return PresuppositionDRS.is_possible_binding(self, cond) and cond.is_propername() and cond.function.variable.name == self.function_name
       
    def is_presupposition_cond(self, cond):
        return cond.is_propername()
    
class DefiniteDescriptionDRS(PresuppositionDRS): pass
#    
#    def _presupposition_readings(self, trail=[]):
#        def accommodation(drs):
#            condition_index = self._get_condition_index(drs, trail)
#            return Reading([(drs, PresuppositionDRS.Accommodation(self, condition_index))])
#        
#        """'A car is going down the road. If Mia is married, then the car that her husband drives is black.'
#        'A car is going down the road. If Mia is married, then the car of her neighbours is black.'
#        'A car is going down the road. If Mia is married, then the car at home is black.'
#        From these sentences we see that a _restrictive_ relative clause and adjunct PPs 
#        require accommodation of the presuppositional NP as the only way of presupposition resolution.
#        It seems that no binding to referents from the DRSs up along the trail can take place.
#        """
#        # If there is a restrictive clause or an adjunct PP, accommodate the presupposition locally
#        events_states = set()
#        # Are there any states/events in this presuppositional drs that the presupposition referent takes part in?
#        for cond in self.conds:
#            if isinstance(cond.function, DrtApplicationExpression) and \
#                (isinstance(cond.function.argument, DrtStateVariableExpression) or 
#                isinstance(cond.function.argument, DrtEventVariableExpression)) and \
#                cond.argument.variable == self.variable:
#                # This will give us conditions like AGENT(s,x), PATIENT(e,x)
#                # TODO: will add() perform the equals check correctly? After all, even though they will be variables of the same name,
#                # they will be different objects 
#                events_states.add(cond.function.argument.variable)
#        
#        if events_states:
#            # Only accommodation is possible.
#            # Global accommodation will be preferred over all other accommodations. But we can't guarantee that 
#            # the most preferred reading won't violate acceptability constraints, so we have to keep all of the readings for now.  
#            """(1)'If a woman is married, then her car is black or her boss is mean.'
#            (2)'If Mia is married, then her car is black or her boss is mean.'
#            Global accommodation in (2), intermediate (preferred, according to van der Sandt) or local accommodation in (1).
#            Focus: linguistic, cognitive, and computational perspectives. Peter Bosch, Rob A. van der Sandt. P. 281
#            
#            David Beaver (Accommodating Topics, When Variables Don't Vary Enough) 
#            argues that local accommodation should be preferred over intermediate, but see Bosch & van der Sandt, p. 282-283
#            """
#            # TODO:
#            """I think that there are some cases when it makes more sense to prefer local accommodation over intermediate
#            (if global accommodation is not possible).
#            (1) 'Every woman likes her hands'
#            Have a look at wordnet in nltk: >>> S('person.n.01'). part_meronyms()
#            [Synset('human_body.n.01'), Synset('personality.n.01')]
#            """
#            
#            # TODO:
#            """
#            Always accommodate when there are any events or states in the presuppositional DRS that the referent takes part in?
#            No.
#            (1) Mia wins a prize. The prize that her neighbours win is a car.
#            (2) Mia wins a prize, The prize that her neighbours make fun of is a car.
#            (3) If Mia wins a prize, the prize that Mia wins is a car.
#            (4) Mia wins a prize. The prize that Mia wins is a car.
#            In (1), global accommodation is the only reading. In (2), binding is preferred to accommodation.
#            In (3), binding is the only reading; local accommodation will be ruled out by acceptability constraints, 
#            but what about intermediate accommodation?
#            In (4), binding is the only reading. Will acceptability constraints let the accommodation reading through? 
#            """
#            accommodations = []
#            # TODO: the loop for finding the global, intermediate and local DRSs will find all DRSs on the trail,
#            # but can we just accommodate anywhere we want? I don't think so.
#            # This means that this will work for 'if', but not for sentences like 
#            # "If a woman is married or she has a dog, then her car is black or her boss is mean."
#            for drs in self.filter_drs(trail):
#                    accommodations.append(accommodation(drs))
#            return accommodations, True
#        # No restrictive clause or PP -> try binding
#        """ Van der Sandt's algorithm would favour closest binding. But consider this sentence:
#        (1) 'Mary is at the concert. If a singer kisses John, the woman is happy.'
#        I think, for a discourse to remain coherent, the listener will always try to look for referents in the global DRS.
#        Other readings will be dispreferred. Only if no referent in the global DRS is found could (but does it?) van der Sand's heuristics 
#        come into play: the lower the level of binding, the better.
#        
#        Even then, we should ask ourselves why we used a definite description in the first place.
#        Here are a couple of examples showing that anaphoric pronouns and definite descriptions do not behave in the same way.
#        
#        I.
#        (2) Butch picks up a hammer. Then he picks up a flower. He puts it back on the shelf.
#        In (2), there is some ambiguity as to the antecedent of 'it', but since 'flower' is the closest referent in the topic focus,
#        it will be preferred. Compare (2) to:
#        (3) Butch picks up a hammer. Then he picks up a flower. He puts the tool back on the shelf.
#        The definite description lifts the ambiguity.
#        
#        II.
#        (4) 'If a girl plays piano, then the child is happy'.
#        If we wanted to refer to the girl, it would have been more economical to say 'she is happy'.
#        'The child' is a resource-consuming, marked way. In this sentence, there was no ambiguity that a pronoun could have introduced
#        (then a definite description would have help us stick to the maxim of manner).
#        The referent isn't too far away from the presupposition, either. But (the listener will think) the definite description 
#        was used for some reason. This is why global accommodation will be at least as preferred as the binding to the referent 
#        from the antecendent of the implicative condition.
#        
#        III.
#        With definite descriptions, binding is very tricky.
#        If condition functors are the same, the two referents will be bound (and indeed, this is the only way to do binding for proper names).
#        Since pronouns have little semantic content, we can find referents by simply going through possible antecedents and comparing
#        their features (number and gender) to those of the pronoun. But,
#        (5) The garage is empty. The car is in the driveway.
#        'The garage' and 'the car' are both inanimate singular nouns, but it is clear that these features are an insufficient basis
#        for binding. We have to use ontologies.
#        FOR INANIMATE NOUNS:
#        First, we find the presupposition condition (the head of the presuppositional NP). If the antecedent is a subclass of the
#        presupposition condition synset, there will be binding with little ambiguity.
#        FOR ANIMATE NOUNS:
#        This is even trickier. First of all, the presupposition condition has to be a subclass of 'person' or 'animal'. But how do we
#        account for the gender?
#        (6) Mia plays with John. The mother is happy.
#        In wordnet, 'mother' is not a subclass of 'woman' or 'female'. The same is true for all gender-specific noun, like
#        'seamstress', 'husband', 'bull', etc. We probably have to specify noun gender in the grammar, then.
#        We do this, but we don't restrict the user in any way, for example gender doesn't have to be {m,f,n}, and these letters
#        can be used for other features than gender, too.
#        >>> S('singer.n.1').common_hypernyms(S('person.n.1'))
#        [Synset('living_thing.n.01'), Synset('physical_entity.n.01'), Synset('person.n.01'), Synset('entity.n.01'), Synset('causal_agent.n.01'), Synset('object.n.01'), Synset('organism.n.01'), Synset('whole.n.02')]
#        >>> S('mother.n.1').common_hypernyms(S('person.n.1'))
#        [Synset('living_thing.n.01'), Synset('physical_entity.n.01'), Synset('person.n.01'), Synset('entity.n.01'), Synset('causal_agent.n.01'), Synset('object.n.01'), Synset('organism.n.01'), Synset('whole.n.02')]
#        >>> S('dog.n.1').common_hypernyms(S('animal.n.1'))
#        [Synset('living_thing.n.01'), Synset('physical_entity.n.01'), Synset('animal.n.01'), Synset('entity.n.01'), Synset('object.n.01'), Synset('organism.n.01'), Synset('whole.n.02')]
#        """
#        # First, try global binding. If we can bind globally, it will be our preferred reading
#        # (not by van der Sand's algorithm, though). Return it.
#        # TODO: THERE CAN BE MORE THAN ONE POSSIBILITIES FOR GLOBAL BINDING. EITHER RANK THEM OR FILTER THEM (or both)
#        # TODO: Even if we find a perfect binding candidate, e.g. hammer-tool, do we return this binding as the only reading?
#        # A dog is outside. If a cat hisses, the animal is afraid.
#        # For this to be a coherent discourse, animal should refer to the dog, but the other binding is also possible (no discourse coherence, though).
#        # At least, if we extend the discourse, the binding to cat may be justified.
#        # A dog is outside. If a cat hisses, the animal is afraid. The dog meets a hissing cat. Or: the dog meets a cat. The cat hisses.
#
#        # Note that 'cat' does not introduce a new individual as such (though it does put the referent on the referents list of the 
#        # antecedent of the implicative condition), like 'dog' does.
#        # If we bind 'animal' to 'cat', 'the animal' still won't refer to an individual, it will refer to a group of individuals that are cats.
#        # This means that the if-sentence just puts some irrelevant background information in the middle of our discourse. 
#        # Naturally, we want to exclde this reading.  
#        
#        # But if we introduce a referent that is a cat (before or after the if-sentence), this background information gets relevant to
#        # our discourse. So maybe, for the future: as long as the bg info is irrelevant, consider only the first reading,
#        # but keep the second reading as a possibility. If after n sentences the info is still irrelevant, throw the 2nd reading away.
#        
#        #-----------------
#        # "The cat is black or the cat is fat", "The cat is black. The cat is fat". Both seem to require binding and sound weird.
#         
#        inner_drs = trail[-1]
#        for drs in self.filter_drs(trail):
#            antecedent_ref = self._binding_check(drs)
#            if antecedent_ref:
#                condition_index = self._get_condition_index(drs, trail)
#                if inner_drs == drs:
#                    return [Reading([(inner_drs, PresuppositionDRS.InnerReplace(self, self.variable, self.function_name, antecedent_ref, PresuppositionDRS.Binding, condition_index))])], True
#                return [Reading([(drs, PresuppositionDRS.Binding(self, self.variable, self.function_name, antecedent_ref, condition_index)),
#                                 (inner_drs, PresuppositionDRS.InnerReplace(self, self.variable, self.function_name, antecedent_ref, PresuppositionDRS.Binding, condition_index))])], True
#        # We have gone through all boxes in the trail, and nowhere did we find an unambiguous antecedent
#        # self.possible_antecedents is a list of lists (but those lists can be empty)
#        # Return all the readings (binding + accommodation), prefer global binding.
#        # TODO:
#        """
#        If we can't use ontologies and there wasn't a restrictive clause / PP, we are not so sure about which reading is the right one.
#        Self.possible_antecedents holds antecedent candidates for binding, but we would probably need advanced lexical information
#        beyond the scope of this project to lift, or at least narrow down, the ambiguity.
#        So the best option would be to return all possible readings, with some preference order,
#        and maybe have a more sophisticated semantic component filter them later 
#        (In this project, these readings will be subjected to acceptability checks, but that's it.).
#        """
#        readings = []
#        # If we bind at some level, there will be no accommodation at this level or below (van der Sandt)
#        binding = False
#        i = 0
#        for drs in candidate_trail:
#            antecedents = self.possible_antecedents[i]
#            i += 1
#            for antecedent in antecedents:
#                condition_index = self._get_condition_index(drs, trail)
#                if inner_drs == drs: r = Reading([(inner_drs, PresuppositionDRS.InnerReplace(self, self.variable, self.function_name, antecedent, PresuppositionDRS.Binding, condition_index))])
#                else: r = Reading([(drs, PresuppositionDRS.Binding(self, self.variable, self.function_name, antecedent, condition_index)),
#                             (inner_drs, PresuppositionDRS.InnerReplace(self, self.variable, self.function_name, antecedent, PresuppositionDRS.Binding, condition_index))])
#                readings.append(r)
#                binding = True
#            if not binding:
#                # If global accommodation passes acceptability check, all other accommodations will be eliminated
#                readings.append(accommodation(drs))
#        return readings, True
#             
#    def _binding_check(self, drs):
#        # Iterate over unary predicates from the conditions of the drs
#        possible_antecedents = []
#        for cond in drs.conds:
#            if is_unary_predicate(cond) and self.has_same_features(cond, self.features):
#                for funcname in self.function_name:
##                    if (cond.function.variable.name == funcname or issuperclasssof(cond.function.variable.name, funcname)) \
##                        and not is_adjective(cond.function.variable.name):
##                        # either equal, or second is a superclass of the first, and they are not adjectives
##                        # (Because if they are adjectives, we could bind 'blue(x)' and 'blue(x)', and we don't want that.)
##                        return cond.argument.variable
##                    elif (issuperclasssof(cond.function.variable.name, 'person') and 
##                         issuperclasssof(funcname, 'person')) or \
##                         (issuperclasssof(cond.function.variable.name, 'animal') and 
##                          issuperclasssof(funcname, 'animal')):
#                        possible_antecedents.append(self.make_VariableExpression(cond.argument.variable))
#        self.possible_antecedents.append(possible_antecedents)
#        # TODO:
#        """issuperclasssof(cond.function.variable.name, funcname).
#        Is binding possible only when the second is the superclass of the first? What if it is the other way round?
#        (1) A car is going down the road. The vehicle is black.
#        (2) A vehicle is going down the road. The car is black.
#        (3) Butch picks up a hammer. Then he puts the tool back on the shelf.
#        (4) Butch picks up a tool. Then he puts the hammer back on the shelf.
#        (5) The seamstress is at home. The woman is happy.
#        (6) The woman is happy. The seamstress is at home.
#        (7) If John has sons, his children are happy.
#        (8) If John has children, his sons are happy.
#        Somehow, with living beings 'the other way round' binding sounds impossible, with inanimate objects it's just very weird. 
#        """
#        return None

class DrtParser(drt.DrtParser):
    """DrtParser producing conditions and referents for temporal logic"""

    def get_all_symbols(self):
        return DrtTokens.SYMBOLS

    def isvariable(self, tok):
        return tok not in DrtTokens.TOKENS

    def handle(self, tok, context):
        """We add new types of DRS to represent presuppositions"""
        if tok.upper() in DrtTokens.PRESUPPOSITION_DRS:
            return self.handle_PRESUPPOSITION_DRS(tok.upper(), context)
        elif tok == DrtTokens.NEWINFO_DRS:
            return self.handle_NEWINFO_DRS(tok, context)
        else: return super(DrtParser, self).handle(tok, context)
        
    def handle_NEWINFO_DRS(self, tok, context):
        """DRS for linking previous discourse with new discourse"""
        self.assertNextToken(DrtTokens.OPEN)
        drs = self.handle_DRS(tok, context)
        return NewInfoDRS(drs.refs, drs.conds)
        
    def handle_PRESUPPOSITION_DRS(self, tok, context):
        """Parse new types of DRS: presuppositon DRSs.
        """
        self.assertNextToken(DrtTokens.OPEN)
        drs = self.handle_DRS(tok, context)
        if tok == DrtTokens.PROPER_NAME_DRS:
            return ProperNameDRS(drs.refs, drs.conds)
        elif tok == DrtTokens.DEFINITE_DESCRIPTION_DRS:
            return DefiniteDescriptionDRS(drs.refs, drs.conds)
        elif tok == DrtTokens.PRONOUN_DRS:
            return PronounDRS(drs.refs, drs.conds)

    def handle_variable(self, tok, context):
        #It's either: 1) a predicate expression: sees(x,y)
        #             2) an application expression: P(x)
        #             3) a solo variable: john OR x
        accum = self.make_VariableExpression(tok)
        # handle the feature structure of the variable
        features = []
        try:
            if self.token(0) == DrtTokens.OPEN_BRACE:
                self.token() # swallow the OPEN_BRACE
                while self.token(0) != DrtTokens.CLOSE_BRACE:
                    features.append(DrtFeatureExpression(Variable(self.token())))
                    if self.token(0) == drt.DrtTokens.COMMA:
                        self.token() # swallow the comma
                self.token() # swallow the CLOSE_BRACE
        except ParseException:
            #we've reached the end of input, this constant has no features
            pass
        if self.inRange(0) and self.token(0) == DrtTokens.OPEN:
            if features:
                accum = DrtFeatureConstantExpression(accum.variable, features)
            #The predicate has arguments
            if isinstance(accum, drt.DrtIndividualVariableExpression):
                raise ParseException(self._currentIndex, 
                                     '\'%s\' is an illegal predicate name.  '
                                     'Individual variables may not be used as '
                                     'predicates.' % tok)
            self.token() #swallow the Open Paren
            
            #curry the arguments
            accum = self.make_ApplicationExpression(accum, 
                                                    self.parse_Expression('APP'))
            while self.inRange(0) and self.token(0) == DrtTokens.COMMA:
                self.token() #swallow the comma
                accum = self.make_ApplicationExpression(accum, 
                                                        self.parse_Expression('APP'))
            self.assertNextToken(DrtTokens.CLOSE)
        elif features:
            accum = DrtFeatureConstantExpression(accum.variable, map(Variable,features))
        return accum

    def handle_DRS(self, tok, context):
        drs = drt.DrtParser.handle_DRS(self, tok, context)
        location_time = None
        
        for cond in drs.conds:
            if isinstance(cond,DrtFindEventualityExpression):
                """PERF(.) gives rise to a DrtFindEventualityExpression;
                in case it is among the DRS-conditions, the eventuality carried by
                this DRS does not give rise to a REFER(.) condition"""
                return DRS(drs.refs, drs.conds)
           
            if not location_time and isinstance(cond, DrtLocationTimeApplicationExpression):
                location_time = cond.argument
        
        for ref in drs.refs:
            """Change DRS: introduce REFER(s/e) condition, add INCLUDE/OVERLAP
            conditions to verbs (triggered by LOCPRO) and given some trigger
            from DrtTokens.TENSE put UTTER(.) condition and,for PAST and FUT,
            earlier(.,.) condition w.r.t. to some new discourse
            referent bound to utterance time."""
        
            if is_statevar(ref.name):
                """Adds REFER(s) condition."""
                if location_time:
                    """Relates location time and eventuality"""
                    drs.conds.append(DrtTimeApplicationExpression(DrtTimeApplicationExpression(self.make_ConstantExpression(DrtTokens.OVERLAP), location_time), DrtStateVariableExpression(ref)))
                drs.conds.append(DrtFindEventualityExpression(self.make_ConstantExpression(DrtTokens.REFER), DrtVariableExpression(ref)))
                
            if is_eventvar(ref.name):
                """Adds REFER(e) condition."""
                if location_time:
                    """Relates location time and eventuality"""
                    drs.conds.append(DrtTimeApplicationExpression(DrtTimeApplicationExpression(self.make_ConstantExpression(DrtTokens.INCLUDE), location_time), DrtStateVariableExpression(ref)))
                drs.conds.append(DrtFindEventualityExpression(self.make_ConstantExpression(DrtTokens.REFER), DrtVariableExpression(ref)))
            
            if is_timevar(ref.name) and not is_uttervar(ref.name):
                """Relates location time with utterance time"""

                tense_cond = [c for c in drs.conds if isinstance(c, DrtApplicationExpression) and \
                               isinstance(c.function, DrtConstantExpression) and \
                               c.function.variable.name in DrtTokens.TENSE and DrtVariableExpression(ref) == c.argument]
                if not tense_cond == []:
                    if tense_cond[0].function.variable.name == DrtTokens.PRES:
                        """Put UTTER(t) instead"""
                        #drs.conds.remove(drs.conds.index(tense_cond[0]))
                        drs.conds[drs.conds.index(tense_cond[0])] = DrtFindUtterTimeExpression(self.make_ConstantExpression(DrtTokens.UTTER), DrtTimeVariableExpression(ref))
                        
                    else:
                        """Put new discourse referent and bind it to utterance time
                        by UTTER(.) and also add earlier(.,.) condition"""
                        utter_time = unique_variable(ref)
                        drs.refs.insert(0, utter_time)
                        drs.conds[drs.conds.index(tense_cond[0])] = DrtFindUtterTimeExpression(self.make_ConstantExpression(DrtTokens.UTTER), DrtTimeVariableExpression(utter_time))

                        if tense_cond[0].function.variable.name == DrtTokens.PAST:
                            drs.conds.append(DrtTimeApplicationExpression(DrtTimeApplicationExpression(self.make_ConstantExpression(DrtTokens.EARLIER), DrtTimeVariableExpression(ref)), DrtTimeVariableExpression(utter_time)))
                        
                        else:
                            drs.conds.append(DrtTimeApplicationExpression(DrtTimeApplicationExpression(self.make_ConstantExpression(DrtTokens.EARLIER), DrtTimeVariableExpression(utter_time)), DrtTimeVariableExpression(ref)))       
        
        return DRS(drs.refs, drs.conds)

    
    def get_BooleanExpression_factory(self, tok):
        """This method serves as a hook for other logic parsers that
        have different boolean operators"""
        
        if tok == DrtTokens.DRS_CONC:
            return ConcatenationDRS
        elif tok in DrtTokens.OR:
            return DrtOrExpression
        elif tok in DrtTokens.IMP:
            return DrtImpExpression
        elif tok in DrtTokens.IFF:
            return DrtIffExpression
        else:
            return None
  
    def make_VariableExpression(self, name):
        return DrtVariableExpression(Variable(name))

    def make_ApplicationExpression(self, function, argument):
        """If statement added returning DrtTimeApplicationExpression"""
        """ Is self of the form "LOCPRO(t)"? """
        if isinstance(function, DrtAbstractVariableExpression) and \
           function.variable.name == DrtTokens.LOCATION_TIME and \
           isinstance(argument, DrtTimeVariableExpression):
            return DrtLocationTimeApplicationExpression(function, argument)
        
        elif isinstance(function, DrtAbstractVariableExpression) and \
            function.variable.name == DrtTokens.PERF:
            return DrtFindEventualityExpression(function, argument)
        
        elif isinstance(argument, DrtStateVariableExpression) or \
            isinstance(argument, DrtEventVariableExpression):
            return DrtEventualityApplicationExpression(function, argument)
        
        elif isinstance(argument, DrtTimeVariableExpression):
            return DrtTimeApplicationExpression(function, argument)
        else:
            return DrtApplicationExpression(function, argument)

    
    def make_ConstantExpression(self,name):
        return DrtConstantExpression(Variable(name))


    def make_NegatedExpression(self, expression):
        return DrtNegatedExpression(expression)
    
    def make_EqualityExpression(self, first, second):
        """This method serves as a hook for other logic parsers that
        have different equality expression classes"""
        return DrtEqualityExpression(first, second)
    
    def make_LambdaExpression(self, variables, term):
        return DrtLambdaExpression(variables, term)
