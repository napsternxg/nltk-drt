"""
NLTK DRT module extended with presuppositions  
"""

__author__ = "Peter Makarov, Alex Kislev, Emma Li"
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
    def __init__(self, sequence, start= -1):
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

class LocalAccommodationReading(Reading): 
    pass

class IntermediateAccommodationReading(Reading): 
    pass

class GlobalAccommodationReading(Reading): 
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

class ConditionReplacer(object):
    """
    A generic condition replacer functor to be used in readings
    replace the condition at the given index with any number of
    conditions, optionally adds a referent
    """
    def __init__(self, index, conds, ref=None):
        self.index = index
        self.conds = conds
        self.ref = ref
    def __call__(self, drs):
        if self.ref:
            drs.refs.append(self.ref)
        drs.conds[self.index:self.index + 1] = self.conds
        return drs

class ConditionRemover(object):
    """A generic condition remover functor to be used in readings"""
    def __init__(self, cond_index):
        self.cond_index = cond_index
    def __call__(self, drs):
        drs.conds.pop(self.cond_index)
        return drs

class ResolutionException(Exception):
    pass

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
    A base abstract DRT Expression from which every DRT Expression inherits.
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
        #print "visited %s", 'TemporalExpression'
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
    
    def resolve(self, verbose=False):
        """
        This method does the whole job of collecting multiple readings.
        We aim to get new readings from the old ones by resolving
        presuppositional DRSs one by one. Every time one presupposition
        is resolved, new readings are created and replace the old ones,
        until there are no presuppositions left to resolve.
        """
        readings = []
        errors = []
        def get_operations(expr):
            try:
                ops = expr.readings()
            except Exception as ex:
                errors.append(str(ex))
                return []
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
                # If a presupposition resolution took place, readings() 
                # returns a tuple (DRS, operation). Otherwise
                # it will return a None.
                for operation in operation_list:
                    new_reading = reading.deepcopy(operation)
                    if verbose:
                        print("reading: %s" % new_reading)
                    new_operations.extend(get_operations(new_reading))

            operations = new_operations

        if not readings and errors:
            raise ResolutionException("\n".join(errors))
        return readings

    RESOLUTION_ORDER = {Reading:0,
                        GlobalAccommodationReading:1,
                        IntermediateAccommodationReading:2,
                        LocalAccommodationReading:3}

    def inf_resolve(self, inference_check=None, verbose=False):
        """
        This method does the whole job of collecting multiple readings.
        We aim to get new readings from the old ones by resolving
        presuppositional DRSs one by one. Every time one presupposition
        is resolved, new readings are created and replace the old ones,
        until there are no presuppositions left to resolve.
        """
        readings = []
        errors = []

        def traverse(base_reading, operations):
            print "sorted"
            for i in sorted(operations, key=lambda o: AbstractDrs.RESOLUTION_ORDER[type(o)]):
                print "operation:", type(i)
            for operation in sorted(operations, key=lambda o: AbstractDrs.RESOLUTION_ORDER[type(o)]):
                new_reading = base_reading.deepcopy(operation)
                if verbose:
                    print("reading: %s" % new_reading)
                try:
                    new_operations = new_reading.readings()
                except Exception as ex:
                    errors.append(str(ex))
                    continue
                if not new_operations:
                    if inference_check:
                        if inference_check(new_reading):
                            readings.append(new_reading)
                            return True
                    else:
                        readings.append(new_reading)
                else:
                    if traverse(new_reading, new_operations[0]):
                        if len(operations)==1 or AbstractDrs.RESOLUTION_ORDER[type(operation)] != 0:
                            return True
            return False

        operations = self.readings()
        if operations:
            traverse(self, operations[0])
        else:
            return [self]

        if not readings and errors:
            raise ResolutionException(". ".join(errors))
        return readings

    def readings(self, trail=[]):
        raise NotImplementedError()

class DRS(AbstractDrs, drt.DRS):
    """A Temporal Discourse Representation Structure."""
    
    def fol(self):
        if not self.conds:
            raise Exception("Cannot convert DRS with no conditions to FOL.")
        accum = reduce(AndExpression, [c.fol() for c in self.conds])
        for ref in ReverseIterator(self.refs):
            accum = ExistsExpression(ref, AndExpression(accum, DRS._ref_type(ref).fol()))
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
        
        return DrtApplicationExpression(ref_cond, DrtAbstractVariableExpression(referent))
    

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
                    refs = self.refs[:i] + [expression.variable] + self.refs[i + 1:]
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
                    refs = self.refs[:i] + [newvar] + self.refs[i + 1:]
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

    def readings(self, trail=[]):
        """get the readings for this DRS"""
        for i, cond in enumerate(self.conds):
            _readings = cond.readings(trail + [self])
            if _readings:
                if _readings[1]:
                    for reading in _readings[0]:
                        reading.append((self, ConditionRemover(i)))
                return _readings[0], False

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
    def readings(self, trail=[]):
        return None
    
    def deepcopy(self, operations=[]):
        return self.__class__(self.variable)

class DrtIndividualVariableExpression(DrtAbstractVariableExpression, drt.DrtIndividualVariableExpression):
    pass

class DrtFunctionVariableExpression(DrtAbstractVariableExpression, drt.DrtFunctionVariableExpression):
    pass

class DrtEventVariableExpression(DrtIndividualVariableExpression, drt.DrtEventVariableExpression):
    pass

class DrtTimeVariableExpression(DrtIndividualVariableExpression, TimeVariableExpression):
    """Type of discourse referents of time"""
    pass

class DrtStateVariableExpression(DrtIndividualVariableExpression, StateVariableExpression):
    """Type of discourse referents of state"""
    pass

class DrtConstantExpression(DrtAbstractVariableExpression, drt.DrtConstantExpression):
    pass

class DrtUtterVariableExpression(DrtTimeVariableExpression):
    """Type of utterance time referent"""
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
        assert isinstance(variable, Variable), "%s is not a Variable" % variable
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
    def readings(self, trail=[]):
        return self.term.readings(trail + [self])

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

    def readings(self, trail=[]):
        return self.term.readings(trail + [self])
    
    def deepcopy(self, operations=[]):
        return self.__class__(self.variable, self.term.deepcopy(operations))
    
    def get_refs(self, recursive=False):
        """@see: AbstractExpression.get_refs()"""
        return []

class DrtBooleanExpression(AbstractDrs, drt.DrtBooleanExpression):
    def readings(self, trail=[]):
        first_readings = self.first.readings(trail + [self])
        if first_readings:
            return first_readings
        else:
            return self.second.readings(trail + [self])
    
    def deepcopy(self, operations=[]):
        return self.__class__(self.first.deepcopy(operations), self.second.deepcopy(operations))

    def simplify(self):
        """When dealing with DRSs, it is good to have unique names for
        the referents bound by each DRS."""
        if isinstance(self.first, DRS) and isinstance(self.second, DRS):
            new_second = self.second
            for ref in set(self.first.get_refs(True)) & set(self.second.get_refs(True)):
                newref = DrtVariableExpression(unique_variable(ref))
                new_second = self.second.replace(ref, newref, True)

            return drt.DrtBooleanExpression.simplify(self.__class__(self.first, new_second))
        
        else:
            return drt.DrtBooleanExpression.simplify(self)
    
class DrtOrExpression(DrtBooleanExpression, drt.DrtOrExpression):
    pass

class DrtImpExpression(DrtBooleanExpression, drt.DrtImpExpression):
    def readings(self, trail=[]):
        first_readings = self.first.readings(trail + [self])
        if first_readings:
            return first_readings
        else:
            return self.second.readings(trail + [self, self.first])

class DrtIffExpression(DrtBooleanExpression, drt.DrtIffExpression):
    pass

class DrtEqualityExpression(AbstractDrs, drt.DrtEqualityExpression):
    def readings(self, trail=[]):
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
            first = first.replace(variable, expression, True)
            second = second.replace(variable, expression, True)
            
        # If variable is bound by first
        elif isinstance(first, DRS) and variable in first.refs:
            if replace_bound: 
                first = first.replace(variable, expression, replace_bound)
                second = second.replace(variable, expression, replace_bound)

        # If variable is bound by second
        elif isinstance(second, DRS) and variable in second.refs:
            if replace_bound:
                first = first.replace(variable, expression, replace_bound)
                second = second.replace(variable, expression, replace_bound)

        else:
            # alpha convert every ref that is free in 'expression'
            for ref in (set(self.get_refs(True)) & expression.free()): 
                v = DrtVariableExpression(unique_variable(ref))
                first = first.replace(ref, v, True)
                second = second.replace(ref, v, True)

            first = first.replace(variable, expression, replace_bound)
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
            return self.__class__(first, second)

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

    def readings(self, trail=[]):
        function_readings = self.function.readings(trail + [self])
        if function_readings:
            return function_readings
        else:
            return self.argument.readings(trail + [self])

    def deepcopy(self, operations=[]):
        return self.__class__(self.function.deepcopy(operations), self.argument.deepcopy(operations))

class DrtEventualityApplicationExpression(DrtApplicationExpression):
    """Type of application expression with state argument"""
    pass

class PresuppositionDRS(DRS):
        
    def readings(self, trail=[]):
        inner_readings = DRS.readings(self, trail)
        if inner_readings:
            return inner_readings
        else:
            self._init_presupp_data()
            return self._presupposition_readings(trail)
        
    def _find_outer_drs(self, trail):
        for expr in trail:
            if expr.__class__ is DRS:
                return expr
        
    def _find_local_drs(self, trail):
        drs = None
        for expr in ReverseIterator(trail):
            if drs:
                if not isinstance(expr, DrtNegatedExpression):
                    return drs
                else: drs = None
            if expr.__class__ is DRS:
                drs = expr
        return drs
    
    def is_possible_binding(self, cond):
        return is_unary_predicate(cond) and self.has_same_features(cond) and cond.argument.__class__ is DrtIndividualVariableExpression
                
    def find_bindings(self, trail, collect_event_data=False, filter=lambda x: x.__class__ is DRS, individuals=None):
        bindings = []
        if collect_event_data:
            event_data_map = {}
            event_strings_map = {}
        is_bindable = True # do not allow forward binding
        for drs in (expr for expr in trail if filter(expr)):
            for cond in drs.conds:
                # Ignore conditions following the presupposition DRS
                if cond is self:
                    if not collect_event_data: 
                        break # assuming that the filtered_trail has drss ordered from the outermost to the innermost
                if not isinstance(cond, DrtApplicationExpression):
                    continue 
                    is_bindable = False 
                if is_bindable and self.is_possible_binding(cond): 
                    bindings.append(cond)
                if collect_event_data:
                    self.collect_event_data(cond, event_data_map, event_strings_map, individuals)
        if collect_event_data:
            self._enrich_event_data_map(event_data_map, event_strings_map)
        return (bindings, event_data_map) if collect_event_data else bindings

    def collect_event_data(self, cond, event_data_map, event_strings_map, individuals=None):
        if isinstance(cond.function, DrtApplicationExpression) and \
        isinstance(cond.argument, DrtIndividualVariableExpression) and not isinstance(cond.argument, DrtTimeVariableExpression):
                event_data_map.setdefault(cond.argument.variable,[]).append((cond.function.argument, cond.function.function.variable.name))
        elif cond.__class__ == DrtEventualityApplicationExpression and \
        (isinstance(cond.argument, DrtEventVariableExpression) or isinstance(cond.argument, DrtStateVariableExpression)) and\
        not isinstance(cond.function, DrtApplicationExpression):
            assert cond.argument not in event_strings_map
            event_strings_map[cond.argument] = cond.function.variable.name
        # The rest are nouns and attributive adjectives
        elif individuals is not None and cond.__class__ == DrtApplicationExpression and \
        not isinstance(cond.function, DrtApplicationExpression):
            individuals.setdefault(cond.argument.variable,[]).append(cond)
        
    def _enrich_event_data_map(self, event_data_map, event_strings_map):
        for individual in event_data_map:
            new_event_list = []
            for event_tuple in event_data_map[individual]:
                new_event_list.append((event_tuple[0], event_tuple[1], event_strings_map.get(event_tuple[0], None))) 
            event_data_map[individual] = new_event_list
                
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
                # or "The distinguished physicist Einstein ...". But 'is_presupposition_cond' helps us find the right one.
                self.variable = cond.argument.variable
                self.features = cond.function.features
                self.function_name = cond.function.variable.name
                self.cond = cond
                return

        self.variable = self.refs[0]
        self.features = None
        self.function_name = presupp_cond_list[0].variable.name
        self.cond = presupp_cond_list[0]
    
    def has_same_features(self, cond):
        return (not isinstance(cond.function, DrtFeatureConstantExpression) and not self.features) \
                or (isinstance(cond.function, DrtFeatureConstantExpression) and cond.function.features == self.features)
                
    #____________________________________________________________________________________________
    def _get_condition_index(self, superordinate_drs, trail, condition_index_cache={}):
        """Use a for loop and 'is' to find the condition. 
        Do not use index(), because it calls a time-consuming equals method."""
        # Keep a condition index cache
        if not condition_index_cache:
            condition_index_cache = {}
        superordinate_drs_index = id(superordinate_drs)
        if superordinate_drs_index in condition_index_cache:
            return condition_index_cache[superordinate_drs_index]
        for ind, trailee in enumerate(trail):
            if trailee is superordinate_drs:
                # The condition might be not in superordinate_drs, but inside one of its conditions (however deep we might need to go)
                look_for = trail[ind+1] if ind < len(trail) -1 else self
                for i, cond in enumerate(superordinate_drs.conds):
                    if cond is look_for:
                        condition_index_cache[superordinate_drs_index] = i
                        return i # condition_index
        return None
    
    class Operation(object):
        """An interface for all operations"""
        def __call__(self, drs):
            raise NotImplementedError
    
    class Accommodate(Operation):
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
            return drs
    
    class Bind(Operation):
        def __init__(self, presupp_drs, presupp_variable, presupp_funcname, antecedent_cond, condition_index):
            self.presupp_drs = presupp_drs
            self.presupp_variable = presupp_variable
            self.presupp_funcname = presupp_funcname
            self.antecedent_cond = antecedent_cond
            self.condition_index = condition_index
        def __call__(self, drs):
            """Put all conditions from the presupposition DRS
            (if presupposition condition is a proper name: except the proper name itself) into the drs, 
            and replace the presupposition condition referent in them with antecedent referent"""
            #print "BINDING, drs", drs
            newdrs = self.presupp_drs.replace(self.presupp_variable, self.antecedent_cond.argument, True)
            # There will be referents and conditions to move 
            # if there is a relative clause modifying the noun that has triggered the presuppositon
            drs.refs.extend([ref for ref in newdrs.refs \
                             if ref != self.antecedent_cond.argument.variable])
            conds_to_move = [cond for cond in newdrs.conds \
                             if not cond in drs.conds]
            # Put the conditions at the position of the original presupposition DRS
            if self.condition_index is None: # it is an index, it can be zero
                drs.conds.extend(conds_to_move)
            else:
                drs.conds = drs.conds[:self.condition_index+1]+conds_to_move+drs.conds[self.condition_index+1:]
            return drs
            
    class InnerReplace(Operation):
        def __init__(self, presupp_variable, antecedent_ref):
            self.presupp_variable = presupp_variable
            self.antecedent_ref = antecedent_ref
        def __call__(self, drs):
                """In the conditions of the local DRS, replace the 
                referent of the presupposition condition with antecedent_ref"""
                return drs.replace(self.presupp_variable, self.antecedent_ref, True)
            
    class MoveTemporalConditions(Operation):
        def __init__(self, temporal_conditions):
            self.temporal_conditions = temporal_conditions
        def __call__(self, drs):
                """In the conditions of the local DRS, replace the 
                referent of the presupposition condition with antecedent_ref"""
                drs.conds.extend(self.temporal_conditions)
                return drs
            
    class DoMultipleOperations(Operation):
        def __init__(self, operations_list):
            self.operations_list = operations_list
            
        def __call__(self, drs):
            """Do the operations one by one"""
            for operation in self.operations_list:
                drs = operation(drs)
            return drs   
                
    def binding_reading(self, inner_drs, target_drs, antecedent_cond, trail, temporal_conditions=None, local_drs=None):
        condition_index = self._get_condition_index(target_drs, trail)
        binder = self.Bind(self, self.variable, self.function_name, antecedent_cond, condition_index)
        inner_replacer = self.InnerReplace(self.variable, antecedent_cond.argument)
        temp_cond_mover = self.MoveTemporalConditions(temporal_conditions) if temporal_conditions else None
        if inner_drs is target_drs:
            if temp_cond_mover:
                if local_drs is target_drs:
                    return Reading([(inner_drs, self.DoMultipleOperations([binder, temp_cond_mover, inner_replacer]))])
                else: 
                    return Reading([(local_drs, temp_cond_mover),
                                    (inner_drs, self.DoMultipleOperations([binder, inner_replacer]))])
            else:
                return Reading([(inner_drs, self.DoMultipleOperations([binder, inner_replacer]))])
        else:
            if temp_cond_mover:
                if local_drs is target_drs:
                    return Reading([(target_drs, self.DoMultipleOperations([binder, temp_cond_mover])),
                                    (inner_drs, inner_replacer)])
                elif local_drs is inner_drs:
                    return Reading([(target_drs, binder),
                                    (inner_drs, self.DoMultipleOperations([temp_cond_mover, inner_replacer]))])
                else:
                    return Reading([(target_drs, binder),
                                    (local_drs, temp_cond_mover),
                                    (inner_drs, inner_replacer)])
            else:
                return Reading([(target_drs, binder),
                        (inner_drs, inner_replacer)])
    
    def accommodation_reading(self, target_drs, trail, temporal_conditions=None, local_drs=None, reading_type=Reading):
        condition_index = self._get_condition_index(target_drs, trail)
        accommodator = self.Accommodate(self, condition_index)
        if temporal_conditions:
            temp_cond_mover = self.MoveTemporalConditions(temporal_conditions)
            if local_drs is target_drs:
                return reading_type([(target_drs, self.DoMultipleOperations([temp_cond_mover, accommodator]))])
            else:
                return reading_type([(target_drs, accommodator),
                                (local_drs, temp_cond_mover)])
        else:
            return reading_type([(target_drs, accommodator)])
                            
class PronounDRS(PresuppositionDRS):
    """
    A superclass for DRSs for personal, reflexive, 
    and possessive pronouns
    """
    PRONOUNS = [DrtTokens.PRONOUN, DrtTokens.REFLEXIVE_PRONOUN, DrtTokens.POSSESSIVE_PRONOUN]

    def is_presupposition_cond(self, cond):
        return cond.function.variable.name in PronounDRS.PRONOUNS

    def _presupposition_readings(self, trail=[]):
        #trail[0].draw()
        possible_bindings, event_data = self.find_bindings(trail, True, filter=lambda x: x.__class__ is DRS or isinstance(x, PresuppositionDRS))
        bindings = [cond for cond in possible_bindings if self._is_binding(cond, self._get_pro_events(event_data), event_data)]
        ranked_bindings = self._rank_bindings(bindings, event_data)
        return [Reading([(trail[-1], VariableReplacer(self.variable, cond.argument, False))]) for cond, rank in sorted(ranked_bindings, key=lambda e: e[1], reverse=True)], True

    def _get_pro_events(self, event_data):
        #in case pronoun participates in only one event, which has no other participants,
        #try to extend it with interlinked events
        #f.e. THEME(z5,z3), THEME(e,z5) where z3 only participates in event z5
        #will be extended to participate in e, but only in case z5 has one participant
        pro_events = [event for event, role, event_string in event_data.get(self.variable, ())]
        if len(pro_events) == 1:
            pro_event = pro_events[0]
            #number of participants in the pro_event
            participant_count = sum((1 for event_list in event_data.itervalues() for event, role, event_string in event_list if event == pro_event))
            # if there is only one participant in the pro_event and pro_event itself participates in other events
            if participant_count == 1 and pro_event.variable in event_data:
                pro_events.extend((event for event, role, event_string in event_data[pro_event.variable]))

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
            pro_roles = set((role for event, role, event_string in event_data.get(self.variable, ())))
            for index, variable in enumerate(bindings):
                var_roles = set((role for event_list in event_data.get(variable, ()) for event, role, event_string in event_list))
                bindings[index] = (variable, index + len(var_roles.intersection(pro_roles)))
        return bindings

    def _is_binding(self, cond, pro_events, event_data):
        #print "PRO EVENTS", pro_events
        #non reflexive pronouns can not resolve to variables having a role in the same event
        if self.function_name == DrtTokens.POSSESSIVE_PRONOUN:
            return True
        else:  
            variable = cond.argument.variable
            variable_events = set((event for event, role, event_string in event_data.get(variable,())))
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
        if possible_bindings:           
            # Return the reading
            return [self.binding_reading(inner_drs, outer_drs, possible_bindings[0], trail)], True
        # If no suitable antecedent has been found in the outer DRS,
        # binding is not possible, so we go for accommodation instead.
        return [self.accommodation_reading(outer_drs, trail)], True
       
    def is_possible_binding(self, cond):
        return super(ProperNameDRS, self).is_possible_binding(cond) and cond.is_propername() and cond.function.variable.name == self.function_name
       
    def is_presupposition_cond(self, cond):
        return cond.is_propername()
    
class DefiniteDescriptionDRS(PresuppositionDRS):
    
    def _presupposition_readings(self, trail=[], overgenerate=False):
        #trail[0].draw()
        """
        If a dog barks, every cat likes the dog.
        For binding, we need to look for antecedents in the whole trail (i.e. in all candidate drss, see filter_trail)
        But what about accommodation?
        If a dog barks, every cat likes the mouse.
        See Mathematical Methods in Linguistics, top of p 121: P->(Q->R) is logically equivalent to (P&Q)-> R,
        which means that it doesn't matter whether we accommodate the mouse in P or Q (intermediate accommodation). I chose Q.
        """
        # If there is a restrictive clause or an adjunct PP, find the perfect binding or accommodate the presupposition
        presupp_event_data = {}
        presupp_event_strings = {}
        presupp_individuals = {}
        # Are there any states/events in this presuppositional drs that the presupposition referent takes part in?
        for cond in (c for c in self.conds if isinstance(c, DrtApplicationExpression)):
            self.collect_event_data(cond, presupp_event_data, presupp_event_strings, presupp_individuals)
        self._enrich_event_data_map(presupp_event_data, presupp_event_strings)
        
        possible_bindings = {}
        event_data = {}
        individuals = {}
        accommod_indices = set()
        intermediate_next = False # find the closest antecedent drs
        outer_drs = self._find_outer_drs(trail)
        local_drs = self._find_local_drs(trail)
        all_refs = []
        free, temporal_conditions = self._get_free()
        # Go through the filtered trail, find bindings and find the intermediate drs for possible accommodation
        for index, drs in enumerate(trail):
            if isinstance(drs, DrtImpExpression): intermediate_next = True
            if not drs.__class__ is DRS: continue
            # Free variable check
            if not self._free_variable_check(drs, free, all_refs): 
                intermediate_next = False
                continue
            # Find the (maximum) three drss
            if drs is outer_drs or drs is local_drs or intermediate_next:
                accommod_indices.add(index)
                intermediate_next = False
            # Find the bindings
            drs_possible_bindings, drs_event_data = self.find_bindings([drs], True, individuals=individuals)
            for var in drs_event_data: event_data.setdefault(var,[]).extend(drs_event_data[var])
            if drs_possible_bindings:
                possible_bindings[index] = drs_possible_bindings
                
        # Make accommodation indices a sorted list
        accommod_indices = sorted(list(accommod_indices))
        def accommodation_cite(drsindex):#LocalAccommodationReading, IntermediateAccommodationReading, GlobalAccommodationReading
            if not drsindex in accommod_indices:
                return None
            ind = accommod_indices.index(drsindex)
            if ind == 0:
                return [LocalAccommodationReading, GlobalAccommodationReading, GlobalAccommodationReading][len(accommod_indices)-1]
            elif ind == 1:
                return [LocalAccommodationReading, IntermediateAccommodationReading][len(accommod_indices)-2]
            else:
                assert ind == 2
                return LocalAccommodationReading
        
        # Filter the bindings, create the readings
        antecedent_tracker = [] # do not bind to the same referent twice
        readings = []
        inner_drs = trail[-1]
        for drsindex, drs in enumerate(trail):
            drs_readings = []
            if drsindex in possible_bindings:
                for cond in ReverseIterator(possible_bindings[drsindex]):
                    variable = cond.argument.variable
                    if self._is_binding(variable, individuals[variable], self._get_defdescr_events(event_data), event_data, presupp_event_data, presupp_individuals) and \
                    not cond.argument in antecedent_tracker:
                        antecedent_tracker.append(cond.argument)
                        drs_readings.append(self.binding_reading(inner_drs, drs, \
                                                                         cond, trail, temporal_conditions, local_drs))
            # If binding is possible, no accommodation at this level or below will take place
            # (unless we set the 'overgenerate' parameter to True)
            if not overgenerate and drs_readings: accommod_indices = [None]
            else:
                acc_cite = accommodation_cite(drsindex)
                if acc_cite:
                    drs_readings.append(self.accommodation_reading(drs, trail, temporal_conditions, local_drs, acc_cite))
                    accommod_indices.remove(drsindex)
            readings.extend(drs_readings)
        
        return readings, True

        # TODO:
        """
        In most cases, we will do only (preferably global) accommodation when there are any events or states 
        in the presuppositional DRS that the referent takes part in. But not always.
        ACCOMMODATION ONLY
        (1) Mia wins a prize. The prize that her neighbours win is a car.
        BOTH, BINDING PREFERRED? - Or maybe just binding
        (2) Mia wins a prize, The prize that her neighbours make fun of is a car.
        BINDING ONLY 3 & 4
        (3) If Mia wins a prize, the prize that the girl wins is a car.
        (4) Mia wins a prize. The prize that Mia wins is a car.
        ACCOMMODATION ONLY
        (5) A car is going down the road. The car at home is black. 
        (6) The blue dog that kissed Mia was fat. The red dog that kissed Mia sulked.
        
        Compare (1) & (2) to (5) "A car is going down the road. The car at home is black".
        In these sentences, world knowledge and other checks help us to choose accommodation:
        1) The same verb, different agents -> different objects. # This can be checked!
        5) An object can't be going down the road and be at home at the same time
        6) An object can't be red and blue at the same time.
        
        Some clues in the sentences can help us choose between binding and accommodation.
        Compare these two examples:
        ACCOMMODATION PREFERRED
        (7) A dog kissed Mia. The dog that will kiss Mia is fat.
        (8) A dog kissed Mia. The dog that Mia kissed is fat.
        BINDING PREFERRED
        (9) A dog kissed Mia. The dog that will kiss Mia AGAIN is fat.
        (10) A dog kissed Mia. The dog that Mia kissed BACK is fat.
        
        In the previous examples, the head of the presuppositional NP and the potential antecedent
        were the same nouns. What if we deal with two nouns with hyponym-hypernym relationship?
        (9) Mia picked up a hammer. The tool Mia picked up was heavy.
        
        From these examples stems the following algorithm:
        Find a perfect match for the noun (for inanimate, a matching string or a hyponym, for animate, a matching string only).
        (It can be a list of matches).
        For each variable on the list of matches, find the events and states it takes part in.
        The dictionary we are interested in is individual : (event, role string, event string), (event, role, event string)
        Our individual takes part in (at least some of) the events and states found in the relative clause.
        
        If event or state is the same (match strings), make sure its participants are the same (one of them is the potential antecedent).
        If they are not the same, choose accommodation. If they are, choose binding.
        
        If the event or state isn't the same, check: not self.conflict(events_states, event_data, antecedent(as event_data key))
        """
            # Global accommodation will be preferred over all other accommodations. But we can't guarantee that 
            # the most preferred reading won't violate acceptability constraints, so we have to keep all of the readings for now.  
            
        # No restrictive clause or PP -> try binding
        """ Van der Sandt's algorithm would favour closest binding. But consider this sentence:
        (1) 'Mary is at the concert. If a singer kisses John, the woman is happy.'
        I think, for a discourse to remain coherent, the listener will always try to look for referents in the global DRS.
        Other readings will be dispreferred. Only if no referent in the global DRS is found could (but does it?) van der Sand's heuristics 
        come into play: the lower the level of binding, the better.
        
        Even then, we should ask ourselves why we used a definite description in the first place.
        Here are a couple of examples showing that anaphoric pronouns and definite descriptions do not behave in the same way.
        
        I.
        (2) Butch picks up a hammer. Then he picks up a flower. He puts it back on the shelf.
        In (2), there is some ambiguity as to the antecedent of 'it', but since 'flower' is the closest referent in the topic focus,
        it will be preferred. Compare (2) to:
        (3) Butch picks up a hammer. Then he picks up a flower. He puts the tool back on the shelf.
        The definite description lifts the ambiguity.
        
        II.
        (4) 'If a girl plays piano, then the child is happy'.
        If we wanted to refer to the girl, it would have been more economical to say 'she is happy'.
        'The child' is a resource-consuming, marked way. In this sentence, there was no ambiguity that a pronoun could have introduced
        (then a definite description would have help us stick to the maxim of manner).
        The referent isn't too far away from the presupposition, either. But (the listener will think) the definite description 
        was used for some reason. This is why global accommodation will be at least as preferred as the binding to the referent 
        from the antecendent of the implicative condition.
        
        III.
        With definite descriptions, binding is very tricky.
        If condition functors are the same, the two referents will be bound (and indeed, this is the only way to do binding for proper names).
        Since pronouns have little semantic content, we can find referents by simply going through possible antecedents and comparing
        their features (number and gender) to those of the pronoun. But,
        (5) The garage is empty. The car is in the driveway.
        'The garage' and 'the car' are both inanimate singular nouns, but it is clear that these features are an insufficient basis
        for binding. We have to use ontologies.
        FOR INANIMATE NOUNS:
        First, we find the presupposition condition (the head of the presuppositional NP). If the antecedent is a subclass of the
        presupposition condition synset, there will be binding with little ambiguity.
        FOR ANIMATE NOUNS:
        This is even trickier. First of all, the presupposition condition has to be a subclass of 'person' or 'animal'. But how do we
        account for the gender?
        (6) Mia plays with John. The mother is happy.
        In wordnet, 'mother' is not a subclass of 'woman' or 'female'. The same is true for all gender-specific noun, like
        'seamstress', 'husband', 'bull', etc. We probably have to specify noun gender in the grammar, then.
        We do this, but we don't restrict the user in any way, for example gender doesn't have to be {m,f,n}, and these letters
        can be used for other features than gender, too.
        >>> S('singer.n.1').common_hypernyms(S('person.n.1'))
        [Synset('living_thing.n.01'), Synset('physical_entity.n.01'), Synset('person.n.01'), Synset('entity.n.01'), Synset('causal_agent.n.01'), Synset('object.n.01'), Synset('organism.n.01'), Synset('whole.n.02')]
        >>> S('mother.n.1').common_hypernyms(S('person.n.1'))
        [Synset('living_thing.n.01'), Synset('physical_entity.n.01'), Synset('person.n.01'), Synset('entity.n.01'), Synset('causal_agent.n.01'), Synset('object.n.01'), Synset('organism.n.01'), Synset('whole.n.02')]
        >>> S('dog.n.1').common_hypernyms(S('animal.n.1'))
        [Synset('living_thing.n.01'), Synset('physical_entity.n.01'), Synset('animal.n.01'), Synset('entity.n.01'), Synset('object.n.01'), Synset('organism.n.01'), Synset('whole.n.02')]
        """
        # First, try global binding. If we can bind globally, it will be our preferred reading
        # (not by van der Sand's algorithm, though). Return it.
        # TODO: THERE CAN BE MORE THAN ONE POSSIBILITIES FOR GLOBAL BINDING. EITHER RANK THEM OR FILTER THEM (or both)
        # TODO: Even if we find a perfect binding candidate, e.g. hammer-tool, do we return this binding as the only reading?
        # A dog is outside. If a cat hisses, the animal is afraid.
        # For this to be a coherent discourse, animal should refer to the dog, but the other binding is also possible (no discourse coherence, though).
        # At least, if we extend the discourse, the binding to cat may be justified.
        # A dog is outside. If a cat hisses, the animal is afraid. The dog meets a hissing cat. Or: the dog meets a cat. The cat hisses.

        # Note that 'cat' does not introduce a new individual as such (though it does put the referent on the referents list of the 
        # antecedent of the implicative condition), like 'dog' does.
        # If we bind 'animal' to 'cat', 'the animal' still won't refer to an individual, it will refer to a group of individuals that are cats.
        # This means that the if-sentence just puts some irrelevant background information in the middle of our discourse. 
        # Naturally, we want to exclde this reading.  
        
        # But if we introduce a referent that is a cat (before or after the if-sentence), this background information gets relevant to
        # our discourse. So maybe, for the future: as long as the bg info is irrelevant, consider only the first reading,
        # but keep the second reading as a possibility. If after n sentences the info is still irrelevant, throw the 2nd reading away.
        
        #-----------------
        # The cat is black. The cat is fat". Seems to require binding and sounds weird.
         
        
        # We have gone through all boxes in the trail, and nowhere did we find an unambiguous antecedent
        # self.possible_antecedents is a list of lists (but those lists can be empty)
        # Return all the readings (binding + accommodation), prefer global binding.
        # TODO:
        """
        If we can't use ontologies and there wasn't a restrictive clause / PP, we are not so sure about which reading is the right one.
        Self.possible_antecedents holds antecedent candidates for binding, but we would probably need advanced lexical information
        beyond the scope of this project to lift, or at least narrow down, the ambiguity.
        So the best option would be to return all possible readings, with some preference order,
        and maybe have a more sophisticated semantic component filter them later 
        (In this project, these readings will be subjected to acceptability checks, but that's it.).
        """
    def _get_free(self):
        free =  self.free(True)
        return free, []
    
    def _get_defdescr_events(self, event_data):
        """E.g. event 'like' from the sentence 'Every girl likes the boy', 
        state 'angry' from the sentence 'The boy is angry'"""
        return [item[0] for item in event_data.get(self.variable, ())]
    
    def _is_binding(self, variable, var_individuals, defdescr_events, event_data, presupp_event_data, presupp_individuals):
        # No binding is possible to variables having a role in the same event (look for events in drss other than self)
        variable_events = set((event for event, role, event_string in event_data.get(variable,())))
        if not variable_events.isdisjoint(defdescr_events):
            return False
        # Don't allow binding if the potential antecedent participates in the same event (in the relative clause) as self.variable, e.g.:
        # If John has a child, the child that likes him (him = the child in the antecedent of the impl. cond) is away.
        variable_presupp_events = set((event for event, role, event_string in presupp_event_data.get(variable,())))
        defdescr_presupp_events = set((event for event, role, event_string in presupp_event_data.get(self.variable,())))
        if not variable_presupp_events.isdisjoint(defdescr_presupp_events):
            return False

        # Don't allow binding x to y if there are conditions like POSS(x,y), POSS(y,x), REL(x,y), REL(y,x) and suchlike
        for event_tuple in presupp_event_data.get(variable, []):
            event = event_tuple[0]
            if event.__class__ == DrtIndividualVariableExpression and event.variable == self.variable:
                return False
        for event_tuple in presupp_event_data.get(self.variable, []):
            event = event_tuple[0]
            if event.__class__ == DrtIndividualVariableExpression and event.variable == variable:
                return False
        
        # Perform the semantic check
        if self.semantic_check(var_individuals, presupp_individuals):
            if not presupp_event_data: return True 
            return not self.event_conflict(event_data, presupp_event_data)
        return False
    
    # TODO:
    # Mia walks. Kate sings. The girl that sings is happy. - only binding to Kate
    # Mia owns a blue bag. Kate owns a red bag. The girl that owns a/the blue bag is happy. A, THE, OR BOTH?
    # Mia owns a blue bag. Kate owns a red bag. The girl _with_ the blue bag is happy.
    # Mia owns a flower. Kate owns a hammer. The girl that owns a tool is happy.
    #----
    # Predicative adjectives and intransitive stative verbs are treated the same way
    # (except that the argument of an adjective is its theme, and the argument of a verb is its agent, but that can be changed).
    # Given that, bind to Kate:
    # Kate owns a bag. Her bag is blue. Mary owns a red bag. The girl who owns a/the blue bag...
    #---- 
    # Use background knowledge for resolution:
    # Uncle Vernon and Harry are talking. The wizard is upset.
        
    def semantic_check(self, individuals, presupp_individuals, strict=False):
        """ Users can plug in their more sophisticated semantic checks here.
        As for this project, we confine ourselves to ontologies provided by WordNet.
        See the other file for how this is supposed to work."""
        if strict:
            # ------------------------ Plug in ontologies here
            if isinstance(self.cond, DrtFeatureConstantExpression):
                for individual in individuals:
                    if isinstance(individual, DrtFeatureConstantExpression) and self.function_name == individual.function.variable.name:
                        return True
                return False
            else:
                # If no features are used, we cannot guarantee that the condition we got self.function_name from wasn't an adjective
                for individual in individuals:
                    for presupp_individual in presupp_individuals[self.variable]:
                        if presupp_individual.function.variable.name == individual.function.variable.name:
                            return True
                return False
        else:
            return True
    
    def event_conflict(self, event_data, presupp_event_data):
        """Users can plug in their checks here. I just check whether, if the presupposition variable and the potential 
        antecedent participate in the (possibly) same events (plain string matching, not variable matching), the other 
        participants are the same. This should wave through the binding for 'boy' and 'boy' in 'A boy kissed Mia. The boy/urchin that 
        kissed the girl...', but prevent (or disprefer) binding in sentences like 'A boy kissed Mia. The boy that kissed Kate...' """
        return False
        
    def _free_variable_check(self, drs, free, all_refs):
        if free:
            all_refs.extend(drs.refs)
            for variable in free:
                if not variable in all_refs: 
                    return False
        return True

class DrtParser(drt.DrtParser):
    """DrtParser producing conditions and referents for temporal logic"""

    def get_all_symbols(self):
        return DrtTokens.SYMBOLS

    def isvariable(self, tok):
        return tok not in DrtTokens.TOKENS

    def handle(self, tok, context):
        """We add new types of DRS to represent presuppositions"""
        if tok.upper() in DrtTokens.PRESUPPOSITION_DRS:
            return self.handle_PresuppositionDRS(tok.upper(), context)
        else:
            return drt.DrtParser.handle(self, tok, context)

        
    def handle_PresuppositionDRS(self, tok, context):
        """Parse all the Presuppositon DRSs."""
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
            accum = DrtFeatureConstantExpression(accum.variable, map(Variable, features))
        return accum

    def handle_DRS(self, tok, context):
        drs = drt.DrtParser.handle_DRS(self, tok, context)
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
        return DrtApplicationExpression(function, argument)
    
    def make_ConstantExpression(self, name):
        return DrtConstantExpression(Variable(name))

    def make_NegatedExpression(self, expression):
        return DrtNegatedExpression(expression)
    
    def make_EqualityExpression(self, first, second):
        """This method serves as a hook for other logic parsers that
        have different equality expression classes"""
        return DrtEqualityExpression(first, second)
    
    def make_LambdaExpression(self, variables, term):
        return DrtLambdaExpression(variables, term)
