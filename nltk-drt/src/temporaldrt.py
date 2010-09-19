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

class DrtTokens(drt.DrtTokens):
    OPEN_BRACE = '{'
    CLOSE_BRACE = '}'
    PUNCT = [OPEN_BRACE, CLOSE_BRACE]
    SYMBOLS = drt.DrtTokens.SYMBOLS + PUNCT
    TOKENS = drt.DrtTokens.TOKENS + PUNCT
    LOCATION_TIME = 'LOCPRO'
    PROPER_NAME_DRS = 'PROP'
    DEFINITE_DESCRIPTION_DRS = 'DEF'
    PRONOUN_DRS = 'PRON'
    PRESUPPOSITION_DRS = [PROPER_NAME_DRS, DEFINITE_DESCRIPTION_DRS, PRONOUN_DRS]
    REFLEXIVE_PRONOUN = 'RPRO'
    POSSESSIVE_PRONOUN = 'PPRO'
    
    ################ Some temporal rubbish ##############
    
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
    This is the base abstract Temproal DRT Expression from which every Temporal DRT 
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

    def resolve(self, trail=[]):
        """
        resolve anaphora should not resolve individuals and events to time referents.

        resolve location time picks out the nearest time referent other than the one in
        LOCPRO(t), for which purpose the PossibleAntecedents class is not used.
        """
        raise NotImplementedError()
    
    def readings(self):
        "This method does the whole job of collecting multiple readings."
        """We aim to get new readings from the old ones by resolving
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
                    new_operations.extend(get_operations(reading.deepcopy(operation)))

            operations = new_operations

        return readings
    
    def _readings(self, trail=[]):
        raise NotImplementedError()

class Reading(list):
    pass

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

    def resolve(self, trail=[]):
        return self.__class__(self.refs, [cond.resolve(trail + [self]) for cond in self.conds])
    
    def _readings(self, trail=[]):
        """get the readings for this DRS"""
        for i, cond in enumerate(self.conds):
            readings = cond._readings(trail + [self])
            if readings:
                if readings[1]:
                    for reading in readings[0]:
                        reading.append((self, PresuppositionDRS.Remover(i)))
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
    def resolve(self, trail=[]):
        return self
    
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
    def resolve(self, trail=[]):
        return self.__class__(self.term.resolve(trail + [self]))

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

    def resolve(self, trail=[]):
        return self.__class__(self.variable, self.term.resolve(trail + [self]))

    def _readings(self, trail=[]):
        return self.term._readings(trail + [self])
    
    def deepcopy(self, operations=[]):
        return self.__class__(self.variable, self.term.deepcopy(operations))
    
    def get_refs(self, recursive=False):
        """@see: AbstractExpression.get_refs()"""
        return []

class DrtBooleanExpression(AbstractDrs, drt.DrtBooleanExpression):
    def resolve(self, trail=[]):
        return self.__class__(self.first.resolve(trail + [self]), 
                              self.second.resolve(trail + [self]))
        
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
            
            new_second = DRS(self.second.refs,self.second.conds)
        
            for ref in self.second.refs:
                if ref in self.first.refs:
                    newref = DrtVariableExpression(unique_variable(ref))
                    new_second = new_second.replace(ref,newref,True)
            
            return drt.DrtBooleanExpression.simplify(self.__class__(self.first,new_second))
        
        else: return drt.DrtBooleanExpression.simplify(self)
    
class DrtOrExpression(DrtBooleanExpression, drt.DrtOrExpression):
    pass

class DrtImpExpression(DrtBooleanExpression, drt.DrtImpExpression):
    def resolve(self, trail=[]):
        return self.__class__(self.first.resolve(trail + [self]),
                              self.second.resolve(trail + [self, self.first]))

    def _readings(self, trail=[]):
        first_readings = self.first._readings(trail + [self])
        if first_readings:
            return first_readings
        else:
            return self.second._readings(trail + [self, self.first])

class DrtIffExpression(DrtBooleanExpression, drt.DrtIffExpression):
    pass

class DrtEqualityExpression(AbstractDrs, drt.DrtEqualityExpression):
    def resolve(self, trail=[]):
        return self
    
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
            
            return DRS(first.refs + second.refs, first.conds + second.conds)
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
   
    def resolve(self, trail=[]):
        return self.__class__(self.function.resolve(trail + [self]),
                              self.argument.resolve(trail + [self]))

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

class ReverseIterator:
    def __init__(self, sequence, start=-1):
        self.sequence = sequence
        self.start = start
    def __iter__(self):
        if self.start > 0:
            i = self.start + 1
        else: 
            i = len(self.sequence) + self.start + 1
        while i > 0:
            i = i - 1
            yield self.sequence[i]

def get_drss(trail=[]):
    """Take a trail (a list of all previously visited DRSs and expressions) 
    and return the local, intermediate and outer DRSs"""
    drss = {}
    outer_drs = trail[0]
    assert isinstance(outer_drs, DRS)
    drss['global'] = outer_drs
    inner_drs = trail[-1]
    if inner_drs is not outer_drs:
        assert isinstance(inner_drs, DRS)
        drss['local'] = inner_drs
    for ancestor in ReverseIterator(trail,-2):
        if isinstance(ancestor, DRS):
            if ancestor is not outer_drs: 
                drss['intermediate'] = ancestor
            break
    return drss

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

                if not utter_time_search and isinstance(refex, DrtTimeVariableExpression) and \
                   not (refex == self.argument):
                    
                    if any(isinstance(c, DrtApplicationExpression) and isinstance(c.function, DrtApplicationExpression) and \
                            c.function.argument == refex and (c.function.function.variable.name == DrtTokens.OVERLAP or \
                            c.function.function.variable.name == DrtTokens.INCLUDE) for c in drs.conds):
                            utter_time_search = True

                    else:
                        """Return first suitable antecedent expression"""
                        return [Reading([(trail[-1], DrtLocationTimeApplicationExpression.VariableReplacer(self.argument.variable, refex))])], True
                 
                elif isinstance(refex, DrtUtterVariableExpression):
                    """In case there is no location time referent that has not yet been used
                    to relate some eventuality to utterance time, use utter time as loc time."""
                    return [Reading([(trail[-1], DrtFindUtterTimeExpression.VariableReplacer(self.argument.variable, refex))])], True
                    
        raise LocationTimeResolutionException("Variable '%s' does not "
                            "resolve to anything." % self.argument)
        
    class Replacer(object):
        def __init__(self, index, new_cond):
            self.index = index
            self.new_cond = new_cond
        def __call__(self, drs):
            drs.conds[self.index] = self.new_cond
            return drs
        
    class VariableReplacer(object):
        def __init__(self, var, new_var):
            self.var = var
            self.new_var = new_var
        def __call__(self, drs):
            drs.refs.remove(self.var)
            return drs.__class__(drs.refs, [cond.replace(self.var, self.new_var, False) for cond in drs.conds])



class PresuppositionDRS(DRS):
    """A Discourse Representation Structure for presuppositions.
    Presuppositions triggered by a possessive pronoun/marker, the definite article, a proper name
    will be resolved in different ways. They are represented by subclasses of PresuppositionalDRS."""

    class Remover(object):
        def __init__(self, cond_index):
            self.cond_index = cond_index
        def __call__(self, drs):
            #assert isinstance(drs.conds[self.cond_index], PresuppositionDRS)
            drs.conds.pop(self.cond_index)
            return drs
    
    def _readings(self, trail=[]):
        return (DRS._readings(self, trail) or
        self._presupposition_readings(trail))

class ProperNameDRS(PresuppositionDRS):
    def _presupposition_readings(self, trail=[]):
        pass

class DefiniteDescriptionDRS(PresuppositionDRS):
    def _presupposition_readings(self, trail=[]):
        pass

class PronounDRS(PresuppositionDRS):
    """A superclass for DRSs for personal, reflexive, 
    and possessive pronouns"""
    PRONOUNS = [DrtTokens.PRONOUN, DrtTokens.REFLEXIVE_PRONOUN, DrtTokens.POSSESSIVE_PRONOUN]

    def get_pronoun_data(self):
        """Is expr of the form "PRO(x)"? """
        for cond in self.conds:
            if isinstance(cond, DrtApplicationExpression) and\
             isinstance(cond.function, DrtAbstractVariableExpression) and \
             cond.function.variable.name in PronounDRS.PRONOUNS and \
             isinstance(cond.argument, DrtIndividualVariableExpression):
                return cond.argument.variable, cond.function.features if isinstance(cond.function, DrtFeatureConstantExpression) else None, cond.function.variable.name
                break

    def _presupposition_readings(self, trail=[]):
        possible_antecedents = []
        pro_variable, pro_features, pro_type = self.get_pronoun_data()
        roles = {}
        events = {}
        for drs in (ancestor for ancestor in trail if isinstance(ancestor, DRS)):
            for cond in drs.conds:
                if isinstance(cond, DrtApplicationExpression) and\
                    cond.argument.__class__ is DrtIndividualVariableExpression:
                    var = cond.argument.variable
                    # nouns/proper names
                    if isinstance(cond.function, DrtConstantExpression):
                        #filter out the variable itself
                        #filter out the variables with non-matching features
                        #allow only backward resolution

                        #print "refs", refs, "var", var, "pro_variable", pro_variable

                        if (not isinstance(cond.function, DrtFeatureConstantExpression or\
                                 not pro_features) or cond.function.features == pro_features):
                            possible_antecedents.append((self.make_VariableExpression(var), 0))
                    # role application
                    if isinstance(cond.function, DrtApplicationExpression) and\
                        isinstance(cond.function.argument, DrtIndividualVariableExpression):
                            roles.setdefault(var,set()).add(cond.function.function)
                            events.setdefault(var,set()).add(cond.function.argument)

        #filter by events
        #in case pronoun participates in only one event, which has no other participants,
        #try to extend it with interlinked events
        #f.e. THEME(z5,z3), THEME(e,z5) where z3 only participates in event z5
        #will be extended to participate in e, but only if z5 has only one participant
        if pro_variable in events and len(events[pro_variable]) == 1:
            for e in events[pro_variable]:
                event = e
            participant_count = 0
            for event_set in events.itervalues():
                if event in event_set:
                    participant_count+=1
            if participant_count == 1:
                try:
                    events[pro_variable] = events[pro_variable].union(events[event.variable])
                except KeyError:
                    pass

        antecedents = [(var, rank) for var, rank in possible_antecedents if self._is_possible_antecedent(var.variable, pro_variable, pro_type, events)]
        #ranking system
        #increment ranking for matching roles and map the positions of antecedents
        if len(antecedents) > 1:
            for index, (var, rank) in enumerate(antecedents):
                antecedents[index] = (var, rank + index + len(roles[var.variable].intersection(roles[pro_variable])))

        if len(antecedents) == 0:
            raise AnaphoraResolutionException("Variable '%s' does not "
                                "resolve to anything." % pro_variable)

        return [Reading([(trail[-1], PronounDRS.VariableReplacer(pro_variable, var))]) for var, rank in sorted(antecedents, key=lambda e: e[1], reverse=True)], True

    def _is_possible_antecedent(self, variable, pro_variable, pro_type, events):
        #non reflexive pronouns can not resolve to variables having a role in the same event
        if pro_type == DrtTokens.PRONOUN:
            return events[variable].isdisjoint(events[pro_variable])
        elif pro_type == DrtTokens.REFLEXIVE_PRONOUN:
            return not events[variable].isdisjoint(events[pro_variable])
        else:
            return True

    class VariableReplacer(object):
        def __init__(self, pro_var, new_var):
            self.pro_var = pro_var
            self.new_var = new_var
        def __call__(self, drs):
            return drs.__class__(drs.refs, [cond.replace(self.pro_var, self.new_var, False) for cond in drs.conds])


class DrtFindUtterTimeExpression(DrtApplicationExpression):
    """Type of application expression looking to equate its argument with utterance time"""
    def _readings(self, trail=[]):
        for ancestor in trail:    
            for ref in ancestor.get_refs():
                refex = DrtVariableExpression(ref)
                if isinstance(refex, DrtUtterVariableExpression):
                    
                    return [Reading([(trail[-1], DrtFindUtterTimeExpression.VariableReplacer(self.argument.variable, refex))])], True                  
        
        raise UtteranceTimeTimeResolutionException("Variable '%s' does not "
                            "resolve to anything." % self.argument)
        
    class VariableReplacer(object):
        def __init__(self, var, new_var):
            self.var = var
            self.new_var = new_var
        def __call__(self, drs):
            drs.refs.remove(self.var)
            return drs.__class__(drs.refs, [cond.replace(self.var, self.new_var, False) for cond in drs.conds])

      
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
                        self.combine(DrtTokens.EARLIER,refex,self.argument)))])], False               

                    
                    elif isinstance(self.argument, DrtStateVariableExpression):
                        """In case given eventuality is a state, return include"""
                        return [Reading([(trail[-1], DrtFindEventualityExpression.Replacer(index,
                        self.combine(DrtTokens.INCLUDE,self.argument,refex)))])], False               
     
                
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
                    self.combine(DrtTokens.ABUT,self.argument,state_reference_point)))])], False                       

                    
                elif isinstance(self.argument, DrtStateVariableExpression):
                    """Reference point is a state and described eventuality a state,
                    then add an event referent to the ancestor's refs list and two conditions
                    that that event is the end of eventuality (function needed!!!) and
                    that event abuts on ref.state"""
                    termination_point = unique_variable(Variable("e"))
                    conds = [DrtEqualityExpression(DrtEventVariableExpression(termination_point),DrtApplicationExpression(self.make_ConstantExpression(DrtTokens.END),self.argument)),
                    self.combine(DrtTokens.ABUT,DrtEventVariableExpression(termination_point),state_reference_point)]
                    return [Reading([(trail[-1], DrtFindEventualityExpression.PerfReplacer(termination_point, index, conds))])], False
                    
                
            elif isinstance(self.argument, DrtStateVariableExpression):
                """Reference point is a state and given eventuality is also a state,
                return overlap"""
 
                return [Reading([(trail[-1], DrtFindEventualityExpression.Replacer(index,
                self.combine(DrtTokens.OVERLAP,state_reference_point,self.argument)))])], False               
        
            elif isinstance(self.argument, DrtEventVariableExpression):
                """Reference point is a state and given eventuality is an event,
                return include"""
                return [Reading([(trail[-1], DrtFindEventualityExpression.Replacer(index, 
                self.combine(DrtTokens.INCLUDE,state_reference_point,self.argument)))])], False               
                
        else:
            """no suitable reference found"""
            return [Reading([(trail[-1],PresuppositionDRS.Remover(index))])], False
        
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
    
    def combine(self,cond, arg1, arg2):
        """Combines two arguments into a DrtEventualityApplicationExpression
        that has another DrtEventualityApplicationExpression as its functor"""
        return DrtEventualityApplicationExpression(DrtEventualityApplicationExpression(self.make_ConstantExpression(cond),arg1),arg2)



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
        else: return super(DrtParser, self).handle(tok, context)
        
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

def test():
    p = DrtParser().parse
    #expr = p('DRS([t,x,t02,y,e, t01],[location(t)]) + DRS([t],[LOCPRO(t)])')
    #expr = p('DRS([t02,x,t,y,e, t10],[location(t),-DRS([y,t04],[john(y)])]) + DRS([],[-DRS([t, t07],[LOCPRO(t)])])')
    expr = p('DRS([t01, e, t02, e03, x, y, t],[LOCPRO(t), PRO(x)])')
    print type(expr.simplify())
    simplified_expr = expr.simplify().resolve()
    
    print simplified_expr, "\n"
    for cond in simplified_expr.conds:
        print "%s : type %s" % (cond, cond.__class__)

    print ""
        
    for ref in simplified_expr.refs:
        print "%s : type %s" % (ref, ref.__class__)
        
    #print type(simplified_expr)
 
"""Converts Proper Names from DRT format 'John(x) into FOL 'John = x'"""
def test_2():
    p = DrtParser().parse
    expr = p('DRS([x,e],[John(x), PRO(x), black(x)])')  
    print expr.fol()
    
def test_3():
    p = DrtParser().parse
    expr = p('DRS([x,y],[John(x), PRO(x), -black(x), -DRS([z],[Bill(z),smoke(z),black(z)])])')
    expr_2 = p('DRS([x],[John(x)])')
    print "%s - %s = %s" % (expr, expr_2, expr.subtract(expr_2))
    
def test_4():    
    from util import Tester
    tester = Tester('file:../data/grammar.fcfg', DrtParser)
    expr = tester.parse("Mary lived and Mary owns a car", utter=True).simplify()
    print expr
    #expr.draw()
    
    for reading in expr.readings():
        print reading
        reading.draw()

if __name__ == "__main__":
    
    #test_2()
    test_4()