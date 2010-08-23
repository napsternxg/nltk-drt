import re, operator
from nltk.sem.logic import BooleanExpression, Variable, Expression,\
BasicType, IffExpression, ImpExpression, ApplicationExpression,\
EqualityExpression, AllExpression, OrExpression, AbstractVariableExpression,\
ConstantExpression, LambdaExpression, NegatedExpression, FunctionVariableExpression,\
EventVariableExpression, IndividualVariableExpression, is_indvar, is_eventvar,\
is_funcvar, unique_variable, ExistsExpression, AndExpression
import nltk.sem.drt as drt
from nltk.internals import Counter
from nltk.sem.drt import DrsDrawer, AnaphoraResolutionException

"""
Basic type of times added on top of nltk.sem.logic.
Extend to utterance time referent 'n'.
"""

_counter = Counter()

class TimeType(BasicType):
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


def is_propername(expr):
    """
    A proper name is capitalized. We assume that John(x) uniquely
    identifies the bearer of the name John and so, when going from Kamp & Reyle's
    DRT format into classical FOL logic, we change a condition like that into John = x.   
    
    @param expr: C{str}
    @return: C{boolean} True if expr is of the correct form 
    """
    assert isinstance(expr, str), "%s is not a string" % expr
    return expr[:1].isupper() and not expr.isupper()

  
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

"""
Temporal logic extension of nltk.sem.drt
Keeps track of time referents and temporal DRS-conditions. 

New function resolving LOCPRO(t) from a non-finite verb
to the location time referent introduced by a finite auxiliary. 
"""

class DrtTokens(drt.DrtTokens):
    LOCATION_TIME = 'LOCPRO'

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

    def resolve(self, trail=[]):
        """
        resolve anaphora should not resolve individuals and events to time referents.

        resolve location time picks out the nearest time referent other than the one in
        LOCPRO(t), for which purpose the PossibleAntecedents class is not used.
        """
        raise NotImplementedError()

class DRS(AbstractDrs, Expression):
    """A Temporal Discourse Representation Structure."""
    
    def __init__(self, refs, conds):
        """
        @param refs: C{list} of C{DrtIndividualVariableExpression} for the 
        discourse referents
        @param conds: C{list} of C{Expression} for the conditions
        """ 
        self.refs = refs
        self.conds = conds

    def replace(self, variable, expression, replace_bound=False):
        """Replace all instances of variable v with expression E in self,
        where v is free in self."""
        try:
            #if a bound variable is the thing being replaced
            i = self.refs.index(variable)
            if not replace_bound:
                return self
            else: 
                return DRS(self.refs[:i]+[expression.variable]+self.refs[i+1:],
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
            return DRS(self.refs,
                       [cond.replace(variable, expression, replace_bound) 
                        for cond in self.conds])

    def variables(self):
        """@see: Expression.variables()"""
        conds_vars = reduce(operator.or_, 
                            [c.variables() for c in self.conds], set())
        return conds_vars - set(self.refs)
    
    def free(self, indvar_only=True):
        """@see: Expression.free()"""
        conds_free = reduce(operator.or_, 
                            [c.free(indvar_only) for c in self.conds], set())
        return conds_free - set(self.refs)

    def get_refs(self, recursive=False):
        """@see: AbstractExpression.get_refs()"""
        if recursive:
            cond_refs = reduce(operator.add, 
                               [c.get_refs(True) for c in self.conds], [])
            return self.refs + cond_refs
        else:
            return self.refs
        
    def resolve(self, trail=[]):
        r_conds = []
        for cond in self.conds:
            r_cond = cond.resolve(trail + [self])            
            r_conds.append(r_cond)
        return self.__class__(self.refs, r_conds)

    def visit(self, function, combinator, default):
        """@see: Expression.visit()"""
        return reduce(combinator, 
                      [function(e) for e in self.refs + self.conds], default)
    
    def simplify(self):
        return DRS(self.refs, [cond.simplify() for cond in self.conds])
    
    def fol(self):
        if not self.conds:
            raise Exception("Cannot convert DRS with no conditions to FOL.")
        accum = reduce(AndExpression, [c.fol() for c in self.conds])
        for ref in self.refs[::-1]:
            accum = ExistsExpression(ref, accum)
        return accum
    
    def __eq__(self, other):
        r"""Defines equality modulo alphabetic variance.
        If we are comparing \x.M  and \y.N, then check equality of M and N[x/y]."""
        if isinstance(other, DRS):
            if len(self.refs) == len(other.refs):
                converted_other = other
                for (r1, r2) in zip(self.refs, converted_other.refs):
                    varex = self.make_VariableExpression(r1)
                    converted_other = converted_other.replace(r2, varex, True)
                return self.conds == converted_other.conds
        return False
    
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
    elif is_timevar(variable.name):
        return DrtTimeVariableExpression(variable)
        """Condition for proper names added"""
    elif is_propername(variable.name):
        return DrtProperNameExpression(variable)
    else:
        return DrtConstantExpression(variable)
    

class DrtAbstractVariableExpression(AbstractDrs, AbstractVariableExpression):
    def fol(self):
        return self
    
    def get_refs(self, recursive=False):
        """@see: AbstractExpression.get_refs()"""
        return []
    
    def resolve(self, trail=[]):
        return self
    
class DrtIndividualVariableExpression(DrtAbstractVariableExpression, IndividualVariableExpression):
    pass

class DrtFunctionVariableExpression(DrtAbstractVariableExpression, FunctionVariableExpression):
    pass

class DrtEventVariableExpression(DrtIndividualVariableExpression, EventVariableExpression):
    pass

class DrtConstantExpression(DrtAbstractVariableExpression, ConstantExpression):
    pass

    """Class for proper names added"""
class DrtProperNameExpression(DrtConstantExpression):
    pass

class DrtNegatedExpression(AbstractDrs, NegatedExpression):
    def fol(self):
        return NegatedExpression(self.term.fol())

    def get_refs(self, recursive=False):
        """@see: AbstractExpression.get_refs()"""
        return self.term.get_refs(recursive)
    
    def resolve(self, trail=[]):
        return self.__class__(self.term.resolve(trail + [self]))

class DrtLambdaExpression(AbstractDrs, LambdaExpression):
    def alpha_convert(self, newvar):
        """Rename all occurrences of the variable introduced by this variable
        binder in the expression to @C{newvar}.
        @param newvar: C{Variable}, for the new variable
        """
        return self.__class__(newvar, self.term.replace(self.variable, 
                          DrtVariableExpression(newvar), True))

    def fol(self):
        return LambdaExpression(self.variable, self.term.fol())
    
    def resolve(self, trail=[]):
        return self.__class__(self.variable, self.term.resolve(trail + [self]))

    def replace(self, variable, expression, replace_bound=False):
        """@see: Expression.replace()"""
        assert isinstance(variable, Variable), "%s is not a Variable" % variable
        assert isinstance(expression, Expression), "%s is not an Expression" % expression
        #if the bound variable is the thing being replaced
        if self.variable == variable:
            if replace_bound: 
                assert isinstance(expression, AbstractVariableExpression), \
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

class DrtBooleanExpression(AbstractDrs, BooleanExpression):
    def get_refs(self, recursive=False):
        """@see: AbstractExpression.get_refs()"""
        if recursive:
            return self.first.get_refs(True) + self.second.get_refs(True)
        else:
            return []
        
    def resolve(self, trail=[]):
        return self.__class__(self.first.resolve(trail + [self]), 
                              self.second.resolve(trail + [self]))

class DrtOrExpression(DrtBooleanExpression, OrExpression):
    def fol(self):
        return OrExpression(self.first.fol(), self.second.fol())

class DrtImpExpression(DrtBooleanExpression, ImpExpression):
    def fol(self):
        first_drs = self.first
        second_drs = self.second

        accum = None
        if first_drs.conds:
            accum = reduce(AndExpression, 
                           [c.fol() for c in first_drs.conds])
   
        if accum:
            accum = ImpExpression(accum, second_drs.fol())
        else:
            accum = second_drs.fol()
    
        for ref in first_drs.refs[::-1]:
            accum = AllExpression(ref, accum)
            
        return accum
    
    def resolve(self, trail=[]):
        return self.__class__(self.first.resolve(trail + [self]),
                              self.second.resolve(trail + [self, self.first]))

class DrtIffExpression(DrtBooleanExpression, IffExpression):
    def fol(self):
        return IffExpression(self.first.fol(), self.second.fol())

class DrtEqualityExpression(AbstractDrs, EqualityExpression):
    def fol(self):
        return EqualityExpression(self.first.fol(), self.second.fol())

    def get_refs(self, recursive=False):
        """@see: AbstractExpression.get_refs()"""
        if recursive:
            return self.first.get_refs(True) + self.second.get_refs(True)
        else:
            return []

    def resolve(self, trail=[]):
        if isinstance(self.second, PossibleAntecedents):
            return self.__class__(self.first, self.second.resolve(trail))
        else:
            return self

class ConcatenationDRS(DrtBooleanExpression):
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
        
    def get_refs(self, recursive=False):
        """@see: AbstractExpression.get_refs()"""
        return self.first.get_refs(recursive) + self.second.get_refs(recursive)

    def getOp(self, syntax=DrtTokens.NLTK):
        return DrtTokens.DRS_CONC
    
    def __eq__(self, other):
        r"""Defines equality modulo alphabetic variance.
        If we are comparing \x.M  and \y.N, then check equality of M and N[x/y]."""
        if isinstance(other, ConcatenationDRS):
            self_refs = self.get_refs()
            other_refs = other.get_refs()
            if len(self_refs) == len(other_refs):
                converted_other = other
                for (r1,r2) in zip(self_refs, other_refs):
                    varex = self.make_VariableExpression(r1)
                    converted_other = converted_other.replace(r2, varex, True)
                return self.first == converted_other.first and \
                        self.second == converted_other.second
        return False
        
    def fol(self):
        return AndExpression(self.first.fol(), self.second.fol())

class DrtApplicationExpression(AbstractDrs, ApplicationExpression):
    def fol(self):
        """New condition for proper names added"""
        if isinstance(self.function, DrtProperNameExpression):
            return EqualityExpression(self.function.fol(),
                                            self.argument.fol())          
        else:
            return ApplicationExpression(self.function.fol(), 
                                           self.argument.fol())

    def get_refs(self, recursive=False):
        """@see: AbstractExpression.get_refs()"""
        if recursive:
            return self.function.get_refs(True) + self.argument.get_refs(True)
        else:
            return []
        
    def resolve(self, trail=[]):
        return self.__class__(self.function.resolve(trail + [self]),
                              self.argument.resolve(trail + [self]))

class PossibleAntecedents(list, AbstractDrs, Expression):
    def free(self, indvar_only=True):
        """Set of free variables."""
        return set(self)

    def replace(self, variable, expression, replace_bound=False):
        """Replace all instances of variable v with expression E in self,
        where v is free in self."""
        result = PossibleAntecedents()
        for item in self:
            if item == variable:
                self.append(expression)
            else:
                self.append(item)
        return result
    
    def str(self, syntax=DrtTokens.NLTK):
        return '[' + ','.join(map(str, self)) + ']'

class DrtTimeVariableExpression(DrtIndividualVariableExpression, TimeVariableExpression):
    """
    Type of discourse referents of time
    """
    pass


class DrtTimeApplicationExpression(DrtApplicationExpression):
    """
    Type of DRS-conditions used in temporal logic 
    """
    pass

class LocationTimeResolutionException(Exception):
    pass

class DrtLocationTimeApplicationExpression(DrtTimeApplicationExpression):
    def resolve(self, trail=[]):
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

class DrtParser(drt.DrtParser):
    """DrtParser producing conditions and referents for temporal logic"""
        
    def handle_DRS(self, tok, context):
        # a DRS
        self.assertNextToken(DrtTokens.OPEN_BRACKET)
        refs = []
        while self.inRange(0) and self.token(0) != DrtTokens.CLOSE_BRACKET:
            # Support expressions like: DRS([x y],C) == DRS([x,y],C)
            if refs and self.token(0) == DrtTokens.COMMA:
                self.token() # swallow the comma
            refs.append(self.get_next_token_variable('quantified'))
        self.assertNextToken(DrtTokens.CLOSE_BRACKET)
        
        if self.inRange(0) and self.token(0) == DrtTokens.COMMA: #if there is a comma (it's optional)
            self.token() # swallow the comma
            
        self.assertNextToken(DrtTokens.OPEN_BRACKET)
        conds = []
        while self.inRange(0) and self.token(0) != DrtTokens.CLOSE_BRACKET:
            # Support expressions like: DRS([x y],C) == DRS([x, y],C)
            if conds and self.token(0) == DrtTokens.COMMA:
                self.token() # swallow the comma
            conds.append(self.parse_Expression(context))
        self.assertNextToken(DrtTokens.CLOSE_BRACKET)
        self.assertNextToken(DrtTokens.CLOSE)
        
        return DRS(refs, conds)

    
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
        if isinstance(argument, DrtTimeVariableExpression):
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
    
if __name__ == "__main__":
    
    test()
    
    print "\nCheck: Converts Proper Names from DRT format 'John(x) into FOL 'John = x'"
    test_2()
