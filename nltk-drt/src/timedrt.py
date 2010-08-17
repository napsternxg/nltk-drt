import re
import operator, nltk.sem

from nltk.sem.logic import *
from nltk.sem.drt import DrtTokens, PossibleAntecedents, AnaphoraResolutionException, \
DRS, DrtApplicationExpression, DrtAbstractVariableExpression, DrtIndividualVariableExpression, \
DrtParser, DrtConstantExpression, DrtVariableExpression, DrtFunctionVariableExpression, DrtEventVariableExpression, \
ConcatenationDRS, DrtOrExpression, DrtImpExpression, DrtIffExpression

_counter = Counter()


################################ Extension to nltk.sem.logic
"""
Basic type of times added on top of nltk.sem.logic.
Extend to utterance time referent 'n'.
""" 

class TimeType(BasicType):
    def __str__(self):
        return 'i'

    def str(self):
        return 'TIME'


TIME_TYPE = TimeType()
    
class TimeVariableExpression(IndividualVariableExpression):
    """This class represents variables that take the form of a single lowercase
    'i' character followed by zero or more digits."""
    type = TIME_TYPE


def VariableExpression(variable):
    """
    This is a factory method that instantiates and returns a subtype of 
    C{AbstractVariableExpression} appropriate for the given variable.
    """
    assert isinstance(variable, Variable), "%s is not a Variable" % variable
    if is_indvar(variable.name):
        return IndividualVariableExpression(variable)
    elif is_funcvar(variable.name):
        return FunctionVariableExpression(variable)
    elif is_eventvar(variable.name):
        return EventVariableExpression(variable)
    elif is_timevar(variable.name):
        return TimeVariableExpression(variable)
    else:
        return ConstantExpression(variable)

# Hack
nltk.sem.logic.VariableExpression = VariableExpression

def is_indvar(expr):
    """
    An individual variable must be a single lowercase character other than 'e', 't', 'n',
    followed by zero or more digits.
    
    @param expr: C{str}
    @return: C{boolean} True if expr is of the correct form 
    """
    assert isinstance(expr, str), "%s is not a string" % expr
    return re.match(r'^[a-df-mo-su-z]\d*$', expr)

# Hack
nltk.sem.logic.is_indvar = is_indvar


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

#hack
nltk.sem.logic.unique_variable = unique_variable

class TemporalExpression(Expression):
    def normalize(self):
        """Rename auto-generated unique variables"""
        print "visited %s", 'TemporalExpression'
        def f(e):
            if isinstance(e,Variable):
                if re.match(r'^z\d+$', e.name) or re.match(r'^[et]0\d+$', e.name):
                    return set([e])
                else:
                    return set([])
            else: 
                combinator = lambda *parts: reduce(operator.or_, parts)
                return e.visit(f, combinator, set())
        
        result = self
        for i,v in enumerate(sorted(list(f(self)))):
            if is_eventvar(v.name):
                newVar = 'e0%s' % (i+1)
            elif is_timevar(v.name):
                newVar = 't0%s' % (i+1)
            else:
                newVar = 'z%s' % (i+1)
            result = result.replace(v, 
                        self.make_VariableExpression(Variable(newVar)), True)
        return result

# hack    
nltk.sem.logic.Expression.normalize = TemporalExpression.normalize


###################################################################################
"""
Temporal logic extension of nltk.sem.drt
Keeps track of time referents and temporal DRS-conditions. 

New function resolving LOCPRO(t) from a non-finite verb
to the location time referent introduced by a finite auxiliary. 
"""

class TemporalDrtTokens(DrtTokens):
    LOCATION_TIME = 'LOCPRO'



def is_location_time_function(expression):
    """ Is self of the form "LOCPRO(t)"? """
    return isinstance(expression, DrtTemporalApplicationExpression) and \
        isinstance(expression.function, DrtAbstractVariableExpression) and \
        expression.function.variable.name == TemporalDrtTokens.LOCATION_TIME and \
        isinstance(expression.argument, DrtTimeVariableExpression)

        
def make_VariableExpression(variable):
    return DrtTemporalVariableExpression(variable) 
    

class DrtTimeVariableExpression(DrtIndividualVariableExpression, TimeVariableExpression):
    """
    Type of discourse referents of time
    """
    pass


class DrtTemporalApplicationExpression(DrtApplicationExpression):
    """
    Type of DRS-conditions used in temporal logic 
    """
    pass


def DrtTemporalVariableExpression(variable):
    """
    This is a factory method that instantiates and returns a subtype of 
    C{DrtAbstractVariableExpression} appropriate for the given variable.
    Extended with DrtTimeVariableExpression for time referents.
    """
    
    if is_timevar(variable.name):
        return DrtTimeVariableExpression(variable)
    else:
        return DrtVariableExpression(variable)
    


class TemporalDRS(DRS):
    """
    DRS using temporal logic    
    """
    
    
    def replace(self, variable, expression, replace_bound=False):
        """Replace all instances of variable v with expression E in self,
        where v is free in self.
        
        Changed return statements from DRS into TemporalDRS
        and DrtVariableExpression into DrtTemporalVariableExpression
        """
        try:
            #if a bound variable is the thing being replaced
            i = self.refs.index(variable)
            if not replace_bound:
                return self
            else: 
                return TemporalDRS(self.refs[:i]+[expression.variable]+self.refs[i+1:],
                           [cond.replace(variable, expression, True) for cond in self.conds])
        except ValueError:
            #variable not bound by this DRS
            
            # any bound variable that appears in the expression must
            # be alpha converted to avoid a conflict
            for ref in (set(self.refs) & expression.free()):
                newvar = unique_variable(ref) 
                newvarex = DrtTemporalVariableExpression(newvar)
                i = self.refs.index(ref)
                self = TemporalDRS(self.refs[:i]+[newvar]+self.refs[i+1:],
                           [cond.replace(ref, newvarex, True) 
                            for cond in self.conds])
                
            #replace in the conditions
            return TemporalDRS(self.refs,
                       [cond.replace(variable, expression, replace_bound) 
                        for cond in self.conds])
            
            
    def simplify(self):
        """simplify returns TemporalDRS"""
        return TemporalDRS(self.refs, [cond.simplify() for cond in self.conds])
    
    
    def __eq__(self, other):
        r"""Defines equality modulo alphabetic variance.
        If we are comparing \x.M  and \y.N, then check equality of M and N[x/y].
        
        Changed from DRS into TemporalDRS"""
        if isinstance(other, TemporalDRS):
            if len(self.refs) == len(other.refs):
                converted_other = other
                for (r1, r2) in zip(self.refs, converted_other.refs):
                    varex = self.make_VariableExpression(r1)
                    converted_other = converted_other.replace(r2, varex, True)
                return self.conds == converted_other.conds
        return False
        
    
    def resolve_location_time(self):
        return resolve_location_time(self)
    
    

class TemporalConcatenationDRS(ConcatenationDRS):
    """DRS of the form '(DRS + DRS)'"""
    def replace(self, variable, expression, replace_bound=False):
        """Replace all instances of variable v with expression E in self,
        where v is free in self.
        
        Changed return statements from DRS into TemporalDRS
        and DrtVariableExpression into DrtTemporalVariableExpression
        """
        first = self.first
        second = self.second

        # If variable is bound by both first and second 
        if isinstance(first, TemporalDRS) and isinstance(second, TemporalDRS) and \
           variable in (set(first.get_refs(True)) & set(second.get_refs(True))):
            first  = first.replace(variable, expression, True)
            second = second.replace(variable, expression, True)
            
        # If variable is bound by first
        elif isinstance(first, TemporalDRS) and variable in first.refs:
            if replace_bound: 
                first  = first.replace(variable, expression, replace_bound)
                second = second.replace(variable, expression, replace_bound)

        # If variable is bound by second
        elif isinstance(second, TemporalDRS) and variable in second.refs:
            if replace_bound:
                first  = first.replace(variable, expression, replace_bound)
                second = second.replace(variable, expression, replace_bound)

        else:
            # alpha convert every ref that is free in 'expression'
            for ref in (set(self.get_refs(True)) & expression.free()): 
                v = DrtTemporalVariableExpression(unique_variable(ref))
                first  = first.replace(ref, v, True)
                second = second.replace(ref, v, True)

            first  = first.replace(variable, expression, replace_bound)
            second = second.replace(variable, expression, replace_bound)
            
        return self.__class__(first, second)
    
    def simplify(self):
        """Changed from DRS into TemporalDRS
        and from DrtVariableExpression to DrtTemporalVariableExpression"""
        first = self.first.simplify()
        second = self.second.simplify()

        if isinstance(first, TemporalDRS) and isinstance(second, TemporalDRS):
            
            # For any ref that is in both 'first' and 'second'
            for ref in (set(first.get_refs(True)) & set(second.get_refs(True))):
                # alpha convert the ref in 'second' to prevent collision
                newvar = DrtTemporalVariableExpression(unique_variable(ref))
                second = second.replace(ref, newvar, True)
            
            return TemporalDRS(first.refs + second.refs, first.conds + second.conds)
        else:
            return self.__class__(first,second)
        
    
    def __eq__(self, other):
        r"""Defines equality modulo alphabetic variance.
        If we are comparing \x.M  and \y.N, then check equality of M and N[x/y].
        
        Changed from ConcatenationDRS into TemporalConcatenationDRS"""
        if isinstance(other, TemporalConcatenationDRS):
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

############################ resolve_location_time

"""
Resolve_anaphora() should not resolve individuals and events to time referents.


Resolve_location_time() picks out the nearest time referent other than the one in
LOCPRO(t), for which purpose the PossibleAntecedents class is not used.
"""

def resolve(expression):
    return expression.resolve_anaphora().resolve_location_time()

 
def resolve_location_time(expression, trail=[]):
    if isinstance(expression, ApplicationExpression):
        if is_location_time_function(expression):
            """Reverses trail list"""
            for ancestor in trail[::-1]:
                """Reverses refs list"""
                for ref in ancestor.get_refs()[::-1]:

                    refex = make_VariableExpression(ref)
                    
                    #==========================================================
                    # Don't allow resolution to itself or other types
                    #==========================================================
                    if refex.__class__ == expression.argument.__class__ and \
                       not (refex == expression.argument):
                        """Return first suitable antecedent expression"""
                        return expression.make_EqualityExpression(expression.argument, refex)
            
            raise LocationTimeResolutionException("Variable '%s' does not "
                                "resolve to anything." % expression.argument)
        
        
        else:
            r_function = resolve_location_time(expression.function, trail + [expression])
            r_argument = resolve_location_time(expression.argument, trail + [expression])
            return expression.__class__(r_function, r_argument)

    elif isinstance(expression, DRS):
        r_conds = []
        for cond in expression.conds:
            r_cond = resolve_location_time(cond, trail + [expression])            
            r_conds.append(r_cond)
        return expression.__class__(expression.refs, r_conds)
    
    elif isinstance(expression, AbstractVariableExpression):
        return expression
    
        """first-order equality condition"""
    elif isinstance(expression, EqualityExpression):
        return expression
    
    elif isinstance(expression, NegatedExpression):
        return expression.__class__(resolve_location_time(expression.term, trail + [expression]))

    elif isinstance(expression, ImpExpression):
        return expression.__class__(resolve_location_time(expression.first, trail + [expression]),
                              resolve_location_time(expression.second, trail + [expression, expression.first]))

    elif isinstance(expression, BinaryExpression):
        return expression.__class__(resolve_location_time(expression.first, trail + [expression]), 
                              resolve_location_time(expression.second, trail + [expression]))

    elif isinstance(expression, LambdaExpression):
        return expression.__class__(expression.variable, resolve_location_time(expression.term, trail + [expression]))


class LocationTimeResolutionException(Exception):
    pass


########################### Parser

class TemporalDrtParser(DrtParser):
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
        
        """Changed return value from DRS(refs, conds)""" 
        return TemporalDRS(refs, conds)

    
    def get_BooleanExpression_factory(self, tok):
        """This method serves as a hook for other logic parsers that
        have different boolean operators
        
        Changed return value from ConcatenationDRS into TemporalConcatenationDRS"""
        if tok == DrtTokens.DRS_CONC:
            return TemporalConcatenationDRS
        elif tok in DrtTokens.OR:
            return DrtOrExpression
        elif tok in DrtTokens.IMP:
            return DrtImpExpression
        elif tok in DrtTokens.IFF:
            return DrtIffExpression
        else:
            return None
    
    
    def make_VariableExpression(self, name):
        """Changed return value from DrtVariableExpression(Variable(name))""" 
        return DrtTemporalVariableExpression(Variable(name))

    def make_ApplicationExpression(self, function, argument):
        """If statement added returning DrtTemporalApplicationExpression""" 
        if isinstance(argument, DrtTimeVariableExpression):
            return DrtTemporalApplicationExpression(function, argument)
        else:
            return DrtApplicationExpression(function, argument)


####################################################################


def test():
    p = TemporalDrtParser().parse
    #expr = p('DRS([t,x,t02,y,e, t01],[location(t)]) + DRS([t],[LOCPRO(t)])')
    #expr = p('DRS([t02,x,t,y,e, t10],[location(t),-DRS([y,t04],[john(y)])]) + DRS([],[-DRS([t, t07],[LOCPRO(t)])])')
    expr = p('DRS([t01, e, t02, e03, x, y, t],[LOCPRO(t), PRO(x)])')
    simplified_expr = resolve(expr.simplify())
    
    print simplified_expr, "\n"
    for cond in simplified_expr.conds:
        print "%s : type %s" % (cond, cond.__class__)

    print ""
        
    for ref in simplified_expr.refs:
        print "%s : type %s" % (ref, ref.__class__)
        
    #print type(simplified_expr)
        
    
if __name__ == "__main__":
    
    test()
    