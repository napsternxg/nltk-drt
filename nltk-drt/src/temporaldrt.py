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
from nltk.sem.logic import EqualityExpression
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
    Extend to utterance time referent 'n'.
    """
    def __str__(self):
        return 'i'

    def str(self):
        return 'TIME'

TIME_TYPE = TimeType()

def is_indvar(expr):
    """
    An individual variable must be a single lowercase character other than 'e', 't', 'n',
    followed by zero or more digits.
    
    @param expr: C{str}
    @return: C{boolean} True if expr is of the correct form 
    """
    assert isinstance(expr, str), "%s is not a string" % expr
    return re.match(r'^[a-df-mo-su-z]\d*$', expr)


def is_timevar(expr):
    """
    An time variable must be a single lowercase 't' or 'n' character followed by
    zero or more digits. Do we need a separate type for utterance time n?
    
    @param expr: C{str}
    @return: C{boolean} True if expr is of the correct form 
    """
    assert isinstance(expr, str), "%s is not a string" % expr
    return re.match(r'^[tn]\d*$', expr)
  
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
    
    def readings(self, trail=[]):
        raise NotImplementedError()

class DRS(AbstractDrs, drt.DRS):
    """A Temporal Discourse Representation Structure."""

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

    def deepcopy(self, operations=None):
        """This method returns a deep copy of the DRS.
        Optionally, it can take a tuple (DRS, function) 
        as an argument and generate a reading by performing 
        a substitution in the DRS as specified by the function.
        @param operations: a dictionary DRS: function, 
        where the DRS is an argument to pass to that function.
        """
        function = (operations and self in operations and operations[self]) or None
        newdrs = self.__class__(list(self.refs), [cond.deepcopy(operations) for cond in self.conds])
        return (function and function(newdrs)) or newdrs
            

    def simplify(self):
        return self.__class__(self.refs, [cond.simplify() for cond in self.conds])

    def resolve(self, trail=[]):
        return self.__class__(self.refs, [cond.resolve(trail + [self]) for cond in self.conds])
    
    def readings(self, trail=[]):
        """get the readings for this DRS, if the second return value is true the condition is removed"""
        for cond in self.conds:
            readings = cond.readings(trail + [self])
            if readings:
                return readings

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
    elif is_timevar(variable.name):
        return DrtTimeVariableExpression(variable)
    else:
        return DrtConstantExpression(variable)
    

class DrtAbstractVariableExpression(AbstractDrs, drt.DrtAbstractVariableExpression):
    def resolve(self, trail=[]):
        return self
    
    def readings(self, trail=[]):
        return None
    
    def deepcopy(self, operations=None):
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
    
    def deepcopy(self, operations=None):
        return self.__class__(self.variable, self.features)

class DrtProperNameExpression(DrtConstantExpression):
    """Class for proper names"""
    pass

class DrtNegatedExpression(AbstractDrs, drt.DrtNegatedExpression):
    def resolve(self, trail=[]):
        return self.__class__(self.term.resolve(trail + [self]))

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

    def resolve(self, trail=[]):
        return self.__class__(self.variable, self.term.resolve(trail + [self]))

    def readings(self, trail=[]):
        return self.term.readings(trail + [self])
    
    def deepcopy(self, operations=None):
        return self.__class__(self.variable, self.term.deepcopy(operations))

class DrtBooleanExpression(AbstractDrs, drt.DrtBooleanExpression):
    def resolve(self, trail=[]):
        return self.__class__(self.first.resolve(trail + [self]), 
                              self.second.resolve(trail + [self]))
        
    def readings(self, trail=[]):
        first_readings = self.first.readings(trail + [self])
        if first_readings:
            return first_readings
        else:
            return self.second.readings(trail + [self])
    
    def deepcopy(self, operations=None):
        return self.__class__(self.first.deepcopy(operations), self.second.deepcopy(operations))

class DrtOrExpression(DrtBooleanExpression, drt.DrtOrExpression):
    pass

class DrtImpExpression(DrtBooleanExpression, drt.DrtImpExpression):
    def resolve(self, trail=[]):
        return self.__class__(self.first.resolve(trail + [self]),
                              self.second.resolve(trail + [self, self.first]))

    def readings(self, trail=[]):
        first_readings = self.first.readings(trail + [self])
        if first_readings:
            return first_readings
        else:
            return self.second.readings(trail + [self, self.first])

class DrtIffExpression(DrtBooleanExpression, drt.DrtIffExpression):
    pass

class DrtEqualityExpression(AbstractDrs, drt.DrtEqualityExpression):
    def resolve(self, trail=[]):
        return self
    
    def readings(self, trail=[]):
        return None
    
    def deepcopy(self, operations=None):
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

    def readings(self, trail=[]):
        function_readings = self.function.readings(trail + [self])
        if function_readings:
            return function_readings
        else:
            return self.argument.readings(trail + [self])

    def deepcopy(self, operations=None):
        return self.__class__(self.function.deepcopy(operations), self.argument.deepcopy(operations))

class PossibleAntecedents(AbstractDrs, drt.PossibleAntecedents):
    pass

class DrtTimeVariableExpression(DrtIndividualVariableExpression, TimeVariableExpression):
    """Type of discourse referents of time"""
    pass


class DrtTimeApplicationExpression(DrtApplicationExpression):
    """Type of DRS-conditions used in temporal logic"""
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
    def resolve(self, trail=[], output=[]):
        """Reverses trail list"""
        for ancestor in trail[::-1]:
            """Reverses refs list"""
            for ref in ancestor.get_refs()[::-1]:

                refex = self.make_VariableExpression(ref)
                
                #==========================================================
                # Don't allow resolution to itself or other types
                #==========================================================
                if refex.__class__ == self.argument.__class__ and \
                   not (refex == self.argument):
                    """Return first suitable antecedent expression"""
                    return self.make_EqualityExpression(self.argument, refex)
        
        raise LocationTimeResolutionException("Variable '%s' does not "
                            "resolve to anything." % self.argument)
        
    def readings(self, trail=[]):
        return None

class PresuppositionDRS(DRS):
    """A Discourse Representation Structure for presuppositions.
    Presuppositions triggered by a possessive pronoun/marker, the definite article, a proper name
    will be resolved in different ways. They are represented by subclasses of PresuppositionalDRS."""
    pass

class ProperNameDRS(PresuppositionDRS):
    def readings(self, trail=[]):
        pass

class DefiniteDescriptionDRS(PresuppositionDRS):
    def readings(self, trail=[]):
        pass

class PronounDRS(PresuppositionDRS):
    """A superclass for DRSs for personal, reflexive, 
    and possessive pronouns"""
    def readings(self, trail=[]):
        pass

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
        elif isinstance(argument, DrtTimeVariableExpression):
            return DrtTimeApplicationExpression(function, argument)
        else:
            return DrtApplicationExpression(function, argument)

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
    expr = p('DRS([x,y],[John(x), PRO(x), black(x)])')  
    print expr.fol()
    

def test_3():
    p = DrtParser().parse
    expr = p('DRS([v],[Claire(v), -(DRS([w], [Jim(w)]) -> DRS([],[small(w)])), DRS([x,y],[John(x), PRO(x), -black(x), (DRS([z],[Bill(z)]) | DRS([j],[ (man(j) | woman(j)) ]))])])')
    #expr = p(r'DRS([t],[-(DRS([w], [Jim(w)]) -> DRS([],[small(w)])), \x.DRS([k],[Bob(k), PRO(t)])])')
    print "lift_proper_names test:\nOriginal expression: ", expr
    #print expr.resolve()
    print "resolved expression: ", expr.resolve()
    
    #addDRS = DRS([],[expr])
    #print addDRS.__class__

def test_4():
    p = DrtParser().parse
    expr = p('DRS([x,y],[John(x), PRO(x), -black(x), -DRS([z],[Bill(z),smoke(z),black(z)])])')
    expr_2 = p('DRS([x],[John(x)])')
    print "%s - %s = %s" % (expr, expr_2, expr.subtract(expr_2))

if __name__ == "__main__":
    
    #test_2()
    test_3()