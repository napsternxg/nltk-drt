import operator
from temporallogic import LogicParser, BooleanExpression, Variable,\
TimeVariableExpression, IffExpression, ImpExpression, ApplicationExpression,\
EqualityExpression, AllExpression, OrExpression, AbstractVariableExpression,\
ConstantExpression, LambdaExpression, NegatedExpression, FunctionVariableExpression,\
EventVariableExpression, IndividualVariableExpression, Expression, is_indvar, is_eventvar,\
is_funcvar, is_timevar, unique_variable, ExistsExpression, AndExpression
import nltk.sem.drt as drt
from nltk.sem.drt import DrsDrawer, AnaphoraResolutionException

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
    else:
        return DrtConstantExpression(variable)
    

class DrtAbstractVariableExpression(AbstractDrs, AbstractVariableExpression):
    def fol(self):
        return self
    
    def get_refs(self, recursive=False):
        """@see: AbstractExpression.get_refs()"""
        return []
    
class DrtIndividualVariableExpression(DrtAbstractVariableExpression, IndividualVariableExpression):
    pass

class DrtFunctionVariableExpression(DrtAbstractVariableExpression, FunctionVariableExpression):
    pass

class DrtEventVariableExpression(DrtIndividualVariableExpression, EventVariableExpression):
    pass

class DrtConstantExpression(DrtAbstractVariableExpression, ConstantExpression):
    pass

class DrtNegatedExpression(AbstractDrs, NegatedExpression):
    def fol(self):
        return NegatedExpression(self.term.fol())

    def get_refs(self, recursive=False):
        """@see: AbstractExpression.get_refs()"""
        return self.term.get_refs(recursive)

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

class DrtBooleanExpression(AbstractDrs, BooleanExpression):
    def get_refs(self, recursive=False):
        """@see: AbstractExpression.get_refs()"""
        if recursive:
            return self.first.get_refs(True) + self.second.get_refs(True)
        else:
            return []

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
        return ApplicationExpression(self.function.fol(), 
                                           self.argument.fol())

    def get_refs(self, recursive=False):
        """@see: AbstractExpression.get_refs()"""
        if recursive:
            return self.function.get_refs(True) + self.argument.get_refs(True)
        else:
            return []

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

class DrtTimeVariableExpression(TimeVariableExpression, DrtIndividualVariableExpression):
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

class DrtParser(LogicParser, drt.DrtParser):
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
        
    
if __name__ == "__main__":
    
    test()
