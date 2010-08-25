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

class DrtTokens(drt.DrtTokens):
    LOCATION_TIME = 'LOCPRO'
    PRESUPPOSITION = 'PRESUPP'
    PRESUPP_ACCOMODATION = 'ACCOMOD'

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
    
    def resolve(self, trail=[], output=[]):
        """
        resolve anaphora should not resolve individuals and events to time referents.

        resolve location time picks out the nearest time referent other than the one in
        LOCPRO(t), for which purpose the PossibleAntecedents class is not used.
        """
        raise NotImplementedError()

class DRS(AbstractDrs, drt.DRS):
    """A Temporal Discourse Representation Structure."""

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
        return self.__class__(self.refs, [cond.simplify() for cond in self.conds])
   
    
    def resolve(self, trail=[], output=[]):
        drs = self.__class__(list(self.refs), [])
        for cond in self.conds:
            r_cond = cond.resolve(trail + [self], output + [drs])
            if r_cond:
                drs.conds.append(r_cond)
        return drs

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
    

class DrtAbstractVariableExpression(AbstractDrs, drt.DrtAbstractVariableExpression):
    def resolve(self, trail=[], output=[]):
        return self

class DrtIndividualVariableExpression(DrtAbstractVariableExpression, drt.DrtIndividualVariableExpression):
    pass

class DrtFunctionVariableExpression(DrtAbstractVariableExpression, drt.DrtFunctionVariableExpression):
    pass

class DrtEventVariableExpression(DrtIndividualVariableExpression, drt.DrtEventVariableExpression):
    pass

class DrtConstantExpression(DrtAbstractVariableExpression, drt.DrtConstantExpression):
    pass

class DrtProperNameExpression(DrtConstantExpression):
    """Class for proper names"""
    pass

class DrtNegatedExpression(AbstractDrs, drt.DrtNegatedExpression):
    def resolve(self, trail=[], output=[]):
        return self.__class__(self.term.resolve(trail + [self], output))

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

    def resolve(self, trail=[], output=[]):
        return self.__class__(self.variable, self.term.resolve(trail + [self], output))


class DrtBooleanExpression(AbstractDrs, drt.DrtBooleanExpression):
    def resolve(self, trail=[], output=[]):
        return self.__class__(self.first.resolve(trail + [self], output), 
                              self.second.resolve(trail + [self], output))

class DrtOrExpression(DrtBooleanExpression, drt.DrtOrExpression):
    pass

class DrtImpExpression(DrtBooleanExpression, drt.DrtImpExpression):
    def resolve(self, trail=[], output=[]):
        return self.__class__(self.first.resolve(trail + [self], output),
                              self.second.resolve(trail + [self, self.first], output))

class DrtIffExpression(DrtBooleanExpression, drt.DrtIffExpression):
    pass

class DrtEqualityExpression(AbstractDrs, drt.DrtEqualityExpression):
    def resolve(self, trail=[], output=[]):
        return self

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
    def resolve(self, trail=[], output=[]):
        return self.__class__(self.function.resolve(trail + [self], output),
                              self.argument.resolve(trail + [self], output))

class PossibleAntecedents(AbstractDrs, drt.PossibleAntecedents):
    pass

class DrtTimeVariableExpression(DrtIndividualVariableExpression, TimeVariableExpression):
    """Type of discourse referents of time"""
    pass


class DrtTimeApplicationExpression(DrtApplicationExpression):
    """Type of DRS-conditions used in temporal logic"""
    pass

class DrtProperNameApplicationExpression(DrtApplicationExpression):
    def fol(self):
        """New condition for proper names added"""
        return EqualityExpression(self.function.fol(), self.argument.fol())
    def resolve(self, trail=[], output=[]):
        outer_drs = output[0]
        inner_drs = output[-1]
        if inner_drs is not outer_drs:
            inner_drs.refs.remove(self.get_variable())
            outer_drs.refs.append(self.get_variable())
            outer_drs.conds.append(self)
            return None
        else:
            return self

    def get_variable(self):
        return self.argument.variable

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
        
class DrtPresuppositionApplicationExpression(DrtApplicationExpression):
    
    def resolve(self, trail=[], output=[]):
        # We have three possible types of accomodation :
        # local (in this very DRS), intermediate (in the preceeding DRS),
        # and global (in the outermost DRS)
        
        # First, get the inner DRS and ,if possible (if they are not the same DRS), 
        # the preceeding DRS and the outer DRS
        inner_drs = None # local accomodation
        preceeding_drs = None # intermediate accomodation
        outermost_drs = None # global accomodation
        while trail:
            ancestor = trail.pop()
            if isinstance(ancestor, DRS):
                if not inner_drs: inner_drs = ancestor
                elif not preceeding_drs:
                    preceeding_drs = ancestor
                    break
        while trail:
            ancestor = trail.pop(0)
            if isinstance(ancestor, DRS):
                outermost_drs = ancestor
                break
        
        # Now go through the conditions of the inner DRS and take out all 
        # conditions pertaining to the presupposition
        presupp_referents = [] # Probably this list will never have more than one element.
        presupp_conditions = [] # All the presupposition conditions will be removed 
        for cond in inner_drs.conds:
            if not isinstance(cond, DrtApplicationExpression): # for example, DrtEqualityExpression
                continue
            if self == cond.function:
                presupp_referents.append(cond.argument)
                presupp_conditions.append(cond)
            elif cond.argument in presupp_referents:
                presupp_conditions.append(cond)
        
        for prcon in presupp_conditions:            
            if self == prcon.function:
                # Add a DrtEqualityExpression to the inner DRS
                inner_drs.conds.append(DrtEqualityExpression(self.argument, prcon.argument))
                inner_drs.conds.remove(prcon)
                # If possible, add a DrtPossiblePresuppAccomodationExpression 
                # to each of the 3 DRS's (inner, preceeding, outermost)
                accomodation = DrtPossiblePresuppAccomodationExpression(DrtConstantExpression(Variable(DrtTokens.PRESUPP_ACCOMODATION)), prcon.argument)
                inner_drs.conds.append(accomodation)
                if preceeding_drs: preceeding_drs.conds.append(accomodation)
                if outermost_drs: outermost_drs.conds.append(accomodation)
            else:
                # If possible, put the prcon condition into each of the 3 DRS's 
                # (inner [it is already there], preceeding, outermost)
                if preceeding_drs: preceeding_drs.conds.append(prcon)
                if outermost_drs: outermost_drs.conds.append(prcon)
        return self

    def get_variable(self):
        return self.argument.variable
    
class DrtPossiblePresuppAccomodationExpression(DrtApplicationExpression):
    pass

class DrtParser(drt.DrtParser):
    """DrtParser producing conditions and referents for temporal logic"""
        
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
        elif isinstance(function, DrtProperNameExpression):
            return DrtProperNameApplicationExpression(function, argument)
        elif isinstance(function, DrtAbstractVariableExpression) and \
        function.variable.name == DrtTokens.PRESUPPOSITION and \
        isinstance(argument, DrtIndividualVariableExpression):
            return DrtPresuppositionApplicationExpression(function, argument)
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