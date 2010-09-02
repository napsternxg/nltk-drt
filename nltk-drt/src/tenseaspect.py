import re
import operator

from nltk.sem.logic import Variable
from nltk.sem.logic import IndividualVariableExpression
from nltk.sem.logic import _counter
from nltk.sem.logic import BasicType
from nltk.sem.logic import Expression
import temporaldrt as drt

from temporaldrt import is_timevar, DrtIndividualVariableExpression, \
                        DrtFunctionVariableExpression, DrtEventVariableExpression, \
                        DrtTimeVariableExpression, DrtProperNameExpression, DrtConstantExpression, \
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
        if is_statevar(pattern.name):
            prefix = 's0'
            
            v = Variable(prefix + str(_counter.get()))
            while ignore is not None and v in ignore:
                v = Variable(prefix + str(_counter.get()))
            return v

    else:
        return drt.unique_variable(pattern, ignore)
    
    
############### Needed?

class DrtTokens(drt.DrtTokens):
    UTTER_TIME = 'UTTER'
   
    
################ a?    

class AbstractDrs(drt.AbstractDrs):
   

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


class DRS(drt.DRS):
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


#class ConcatenationDRS(drt.ConcatenationDRS):
#    """DRS of the form '(DRS + DRS)'"""
#    def replace(self, variable, expression, replace_bound=False):
#        """Replace all instances of variable v with expression E in self,
#        where v is free in self."""
#        first = self.first
#        second = self.second
#
#        # If variable is bound by both first and second 
#        if isinstance(first, DRS) and isinstance(second, DRS) and \
#           variable in (set(first.get_refs(True)) & set(second.get_refs(True))):
#            first  = first.replace(variable, expression, True)
#            second = second.replace(variable, expression, True)
#            
#        # If variable is bound by first
#        elif isinstance(first, DRS) and variable in first.refs:
#            if replace_bound: 
#                first  = first.replace(variable, expression, replace_bound)
#                second = second.replace(variable, expression, replace_bound)
#
#        # If variable is bound by second
#        elif isinstance(second, DRS) and variable in second.refs:
#            if replace_bound:
#                first  = first.replace(variable, expression, replace_bound)
#                second = second.replace(variable, expression, replace_bound)
#
#        else:
#            # alpha convert every ref that is free in 'expression'
#            for ref in (set(self.get_refs(True)) & expression.free()):
#                v = DrtVariableExpression(unique_variable(ref))
#                first  = first.replace(ref, v, True)
#                second = second.replace(ref, v, True)
#
#            first  = first.replace(variable, expression, replace_bound)
#            second = second.replace(variable, expression, replace_bound)
#            
#        return self.__class__(first, second)
#
#    def simplify(self):
#
#        first = self.first.simplify()
#        second = self.second.simplify()
#
#        if isinstance(first, DRS) and isinstance(second, DRS):
#            # For any ref that is in both 'first' and 'second'
#            for ref in (set(first.get_refs(True)) & set(second.get_refs(True))):
#                # alpha convert the ref in 'second' to prevent collision
#                newvar = DrtVariableExpression(unique_variable(ref))
#                
#                second = second.replace(ref, newvar, True)
#            
#            return DRS(first.refs + second.refs, first.conds + second.conds)
#        else:
#            return self.__class__(first,second)


class ConcatenationDRS(drt.ConcatenationDRS):
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


class DrtFindUtterTimeApplicationExpression(DrtApplicationExpression):
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
            return drt.DrtOrExpression
        elif tok in DrtTokens.IMP:
            return drt.DrtImpExpression
        elif tok in DrtTokens.IFF:
            return drt.DrtIffExpression
        else:
            return None
        
#        if tok == DrtTokens.DRS_CONC:
#            print "I'm a concDRS"
#            return ConcatenationDRS
#        else:
#            return drt.DrtParser.get_BooleanExpression_factory(self, tok)

    def make_VariableExpression(self, name):
        return DrtVariableExpression(Variable(name))

    def make_ApplicationExpression(self, function, argument):

        if isinstance(argument, DrtStateVariableExpression):
            return DrtStateApplicationExpression(function, argument)
        if isinstance(argument, DrtUtterVariableExpression):
            """to be deleted"""
            return DrtTimeApplicationExpression(function, argument)
        
        if isinstance(function, DrtAbstractVariableExpression) and \
                function.variable.name == DrtTokens.UTTER_TIME  and \
                isinstance(argument, DrtTimeVariableExpression):
            return DrtFindUtterTimeApplicationExpression(function, argument)
        else:
            return drt.DrtParser.make_ApplicationExpression(self, function, argument)

def test():
    p = DrtParser().parse
    #expr = p('DRS([t,x,t02,y,e, t01],[location(t)]) + DRS([t],[LOCPRO(t)])')
    #expr = p('DRS([t02,x,t,y,e, t10],[location(t),-DRS([y,t04],[john(y)])]) + DRS([],[-DRS([t, t07],[LOCPRO(t)])])')
    expr = p('DRS([t01, e, t02, e03, s, x, y, t],[LOCPRO(t), PRO(x), live(s)])')
    print type(expr.simplify())
    simplified_expr = expr.simplify().resolve()
    
    print simplified_expr, "\n"
    for cond in simplified_expr.conds:
        print "%s : type %s" % (cond, cond.__class__)

    print ""
        
    for ref in simplified_expr.refs:
        print "%s : type %s" % (ref, ref.__class__)
        
        
def test_2():
    p = DrtParser().parse
    expr = p('DRS([s, x],[live(s)])+DRS([s,y],[own(s)])').simplify()
    for ref in expr.refs:
        print ref.name, is_statevar(ref.name)
    print expr
        

def test_3():
    p = DrtParser().parse
    expr = p('DRS([n, t],[UTTER(t)])').resolve()
    for ref in expr.refs:
        print ref.name, ref.__class__, DrtVariableExpression(ref).__class__, issubclass(DrtVariableExpression(ref).__class__, DrtIndividualVariableExpression)
    for cond in expr.conds:
        print "%s : type %s" % (cond, cond.__class__)
    print expr
    
    
def test_4():
    
    from nltk import load_parser
    parser = load_parser('file:../data/tenseaspect.fcfg', logic_parser=DrtParser())
    trees = parser.nbest_parse("Angus owns a dog".split())
    expr = trees[0].node['SEM']
    print expr
    expr.draw()
    
if __name__ == "__main__":
    test_4()