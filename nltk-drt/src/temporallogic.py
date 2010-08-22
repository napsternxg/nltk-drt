import re, operator
import nltk.sem.logic as logic
from nltk.sem.logic import is_funcvar, is_eventvar, Variable, Tokens, ParseException
from nltk.internals import Counter

"""
Basic type of times added on top of nltk.sem.logic.
Extend to utterance time referent 'n'.
"""

_counter = Counter()

class TimeType(logic.BasicType):
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

class Expression(logic.Expression):
    
    def applyto(self, other):
        assert isinstance(other, Expression), "%s is not an Expression" % other
        return ApplicationExpression(self, other)
    
    def __neg__(self):
        return NegatedExpression(self)
    
    def __and__(self, other):
        assert isinstance(other, Expression), "%s is not an Expression" % other
        return AndExpression(self, other)
    
    def __or__(self, other):
        assert isinstance(other, Expression), "%s is not an Expression" % other
        return OrExpression(self, other)
    
    def __gt__(self, other):
        assert isinstance(other, Expression), "%s is not an Expression" % other
        return ImpExpression(self, other)
    
    def __lt__(self, other):
        assert isinstance(other, Expression), "%s is not an Expression" % other
        return IffExpression(self, other)
                                 
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

class ApplicationExpression(Expression, logic.ApplicationExpression):
    def resolve(self, trail=[]):
        return self.__class__(self.function.resolve(trail + [self]),
                              self.argument.resolve(trail + [self]))

class AbstractVariableExpression(Expression, logic.AbstractVariableExpression):
    def resolve(self, trail=[]):
        return self

class IndividualVariableExpression(AbstractVariableExpression, logic.IndividualVariableExpression):
    pass

class FunctionVariableExpression(AbstractVariableExpression, logic.FunctionVariableExpression):
    pass
    
class EventVariableExpression(IndividualVariableExpression, logic.EventVariableExpression):
    pass

class TimeVariableExpression(IndividualVariableExpression):
    """This class represents variables that take the form of a single lowercase
    'i' character followed by zero or more digits."""
    type = TIME_TYPE

class ConstantExpression(AbstractVariableExpression, logic.ConstantExpression):
    pass


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

    
class VariableBinderExpression(Expression, logic.VariableBinderExpression):
    """This an abstract class for any Expression that binds a variable in an
    Expression.  This includes LambdaExpressions and Quantified Expressions"""

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

class LambdaExpression(VariableBinderExpression, logic.LambdaExpression):
    def resolve(self, trail=[]):
        return self.__class__(self.variable, self.term.resolve(trail + [self]))

class QuantifiedExpression(VariableBinderExpression, logic.QuantifiedExpression):
    pass

class ExistsExpression(QuantifiedExpression, logic.ExistsExpression):
    pass

class AllExpression(QuantifiedExpression, logic.AllExpression):
    pass

class NegatedExpression(Expression, logic.NegatedExpression):
    def resolve(self, trail=[]):
        return self.__class__(self.term.resolve(trail + [self]))
        
class BinaryExpression(Expression, logic.BinaryExpression):
    def resolve(self, trail=[]):
        return self.__class__(self.first.resolve(trail + [self]), 
                              self.second.resolve(trail + [self]))
        
class BooleanExpression(BinaryExpression, logic.BooleanExpression):
    pass

class AndExpression(BooleanExpression, logic.AndExpression):
    pass

class OrExpression(BooleanExpression, logic.OrExpression):
    pass

class ImpExpression(BooleanExpression, logic.ImpExpression):
    def resolve(self, trail=[]):
        return self.__class__(self.first.resolve(trail + [self]),
                              self.second.resolve(trail + [self, self.first]))

class IffExpression(BooleanExpression, logic.IffExpression):
    pass

class EqualityExpression(BinaryExpression, logic.EqualityExpression):
    def resolve(self, trail=[]):
        return self

class LogicParser(logic.LogicParser):
    """A lambda calculus expression parser extended for temporal logic."""

    def make_VariableExpression(self, name):
        return VariableExpression(Variable(name))
    
    def make_LambdaExpression(self, variable, term):
        return LambdaExpression(variable, term)
    
    def get_QuantifiedExpression_factory(self, tok):
        """This method serves as a hook for other logic parsers that
        have different quantifiers"""
        if tok in Tokens.EXISTS:
            return ExistsExpression
        elif tok in Tokens.ALL:
            return AllExpression
        else:
            self.assertToken(tok, Tokens.QUANTS)
    
    def get_BooleanExpression_factory(self, tok):
        """This method serves as a hook for other logic parsers that
        have different boolean operators"""
        if tok in Tokens.AND:
            return AndExpression
        elif tok in Tokens.OR:
            return OrExpression
        elif tok in Tokens.IMP:
            return ImpExpression
        elif tok in Tokens.IFF:
            return IffExpression
        else:
            return None
    
    def make_QuanifiedExpression(self, factory, variable, term):
        return factory(variable, term)

    def make_NegatedExpression(self, expression):
        return NegatedExpression(expression)
    
    def make_ApplicationExpression(self, function, argument):
        return ApplicationExpression(function, argument)

def test():
    p = LogicParser().parse
    e = p('exists n t x.((((loc_time(t) & utter_time(n)) & earlier(n,t)) & Angus(x)) & -exists z3 s t05.((((dog(z3) & own(s,x,z3)) & state(s)) & overlap(s,t05)) & (t05 = t)))')
    print(e)
    e = p('P(x) & Q(x)')
    print(e.simplify())
if __name__ == "__main__":
    test()
    
