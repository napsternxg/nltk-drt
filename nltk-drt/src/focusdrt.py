from nltk.sem.logic import Variable, Expression, VariableExpression, unique_variable
from nltk.sem.drt import DRS,Tokens,DrtTokens,DrtParser,DrtApplicationExpression, DrtConstantExpression, DrtLambdaExpression, DrtVariableExpression, ConcatenationDRS
from nltk import load_parser

def sb(e, bindings):
    print "Expression.substitute_bindings(%s,%s)" % (e,bindings)
    expr = e
    for var in expr.variables():
        if var in bindings:
            val = bindings[var]
            if isinstance(val, Variable):
                val = VariableExpression(val)
            elif not isinstance(val, Expression):
                raise ValueError('Can not substitute a non-expression '
                                 'value into an expression: %r' % (val,))
            # Substitute bindings in the target value.
            val = val.substitute_bindings(bindings)
            # Replace var w/ the target value.
            print "expr=%s, var=%s, val=%s" % (expr, var,val)
            expr = expr.replace(var, val)
    r = expr.simplify()
    print "result=%s" % (r)
    return r

#Expression.substitute_bindings = sb

class FocusDrtTokens(Tokens):
    FOCUS = 'FOCUS'
    THEME = 'THEME'
    AGENT = 'AGENT'
    FOCUS_TYPE = [THEME, AGENT]
    TOKENS = Tokens.TOKENS + [FOCUS]

class FocusConstantExpression(DrtConstantExpression):
    """A focus expression"""
    def __init__(self, expression, focus_type, focus_features):
        self.variable = expression
        self.focus_type = focus_type
        self.focus_features = focus_features

    def substitute_bindings(self, bindings):
        print "FocusConstantExpression.substitute_bindings(%s)" % (bindings)
        expression = self.variable.substitute_bindings(bindings)

        features = []
        for var in self.focus_features:
            if var in bindings:
                val = bindings[var]
                if isinstance(val, str):
#TODO: remove this crap
                    val = val
                else:
                    raise ValueError('expected a string feature value')
                features.append(val)

        return self.make_DrtLambdaExpression(expression, self.focus_type, features)

    def make_DrtLambdaExpression(self, expression, focus_type, features):
        assert isinstance(expression, DrtLambdaExpression)
        assert isinstance(expression.term, ConcatenationDRS)
        assert isinstance(expression.term.first, DRS)
        assert len(expression.term.first.refs) > 0
        var = expression.term.first.refs[-1]
        print "NP", var
        focus_structure = {var: (focus_type, features)}

        return DrtLambdaExpression(expression.variable, ConcatenationFocusDRS(FocusDRS(expression.term.first.refs, expression.term.first.conds, focus_structure), expression.term.second))

#    def replace(self, variable, expression, replace_bound=False):
#        print "FocusAbstractExpression.replace(%s, %s, %s)" % (variable, expression, replace_bound)
#        return FocusConstantExpression(self.expression.replace(variable, expression, replace_bound), self.focus_structure)

#    def free(self, indvar_only=True):
#        return self.expression.free(indvar_only)

#    def variables(self):
#        print "FocusExpression.variables()", type(self.expression)
#        return self.expression.variables()

#    def visit(self, function, combinator, default):
#        if hasattr(self.expression, 'visit'):
#            print 'visit'
#            self.expression.visit(function, combinator, default)

class FocusDRS(DRS):
    """A Discourse Representation Structure with Focus."""
    def __init__(self, refs, conds, focus = {}):
        """
        @param refs: C{list} of C{DrtIndividualVariableExpression} for the 
        discourse referents
        @param conds: C{list} of C{Expression} for the conditions
        """ 
        self.refs = refs
        self.conds = conds
        self.focus = focus

    def __add__(self, other):
        return ConcatenationFocusDRS(self, other)
    
    def _replace_focus(self, var, new_var):
        try:
            data = self.focus[var]
            focus = dict(self.focus)
            del focus[var]
            focus[new_var] = data
        except KeyError:
            focus = self.focus
        return focus

    def replace(self, variable, expression, replace_bound=False):

        """Replace all instances of variable v with expression E in self,
        where v is free in self."""

        try:
            #if a bound variable is the thing being replaced
            i = self.refs.index(variable)
            if not replace_bound:
                return self
            else:
                return FocusDRS(self.refs[:i]+[expression.variable]+self.refs[i+1:],
                           [cond.replace(variable, expression, True) for cond in self.conds],
                           self._replace_focus(variable, expression.variable))
        except ValueError:
            #variable not bound by this DRS
            
            # any bound variable that appears in the expression must
            # be alpha converted to avoid a conflict
            for ref in (set(self.refs) & expression.free()):
                newvar = unique_variable(ref) 
                newvarex = DrtVariableExpression(newvar)
                i = self.refs.index(ref)
                self = FocusDRS(self.refs[:i]+[newvar]+self.refs[i+1:],
                           [cond.replace(ref, newvarex, True) for cond in self.conds],
                            self._replace_focus(ref, newvar))

            #replace in the conditions
            return FocusDRS(self.refs,
                       [cond.replace(variable, expression, replace_bound) 
                        for cond in self.conds],
                        self._replace_focus(variable, expression.variable))

    def simplify(self):
        print "FocusDRS.simplify"
        return FocusDRS(self.refs, [cond.simplify() for cond in self.conds], self.focus)
    
    def str(self, syntax=DrtTokens.NLTK):
        if syntax == DrtTokens.PROVER9:
            return self.fol().str(syntax)
        else:
            return '([%s],[%s],[%s])' % (','.join([str(r) for r in self.refs]),
                                    ', '.join([c.str(syntax) for c in self.conds]),
                                    ','.join([str(v) + str(d) for v,d in self.focus.iteritems()]))

class ConcatenationFocusDRS(ConcatenationDRS):
    def simplify(self):
        first = self.first.simplify()
        second = self.second.simplify()

        if isinstance(first, FocusDRS) and isinstance(second, FocusDRS):
            # For any ref that is in both 'first' and 'second'
            for ref in (set(first.get_refs(True)) & set(second.get_refs(True))):
                # alpha convert the ref in 'second' to prevent collision
                newvar = DrtVariableExpression(unique_variable(ref))
                second = second.replace(ref, newvar, True)
            
            return FocusDRS(first.refs + second.refs, first.conds + second.conds, dict(first.focus).update(second.focus))
        else:
            return self.__class__(first,second)

class FocusDrtParser(DrtParser):
    """A lambda calculus expression parser."""
    def __init__(self):
        DrtParser.__init__(self)

    def isvariable(self, tok):
        return tok not in FocusDrtTokens.TOKENS

    def handle(self, tok):
        #print "handle(%s) = " % (tok)
        r = self.handle1(tok)
        #print " = %s" % (r)
        return r 

    def handle1(self, tok):
        """This method is intended to be overridden for logics that 
        use different operators or expressions"""
        if tok in DrtTokens.NOT:
            return self.handle_negation()
        
        elif tok in DrtTokens.LAMBDA:
            return self.handle_lambda(tok)
            
        elif tok == DrtTokens.OPEN:
            if self.token(0) == DrtTokens.OPEN_BRACKET:
                return self.handle_DRS()
            else:
                return self.handle_open(tok)

        elif tok.upper() == DrtTokens.DRS:
            self.assertToken(self.token(), DrtTokens.OPEN)
            return self.handle_DRS()

        #NEW ADDITION

        elif tok.upper() == FocusDrtTokens.FOCUS:
            self.assertToken(self.token(), DrtTokens.OPEN)
            return self.handle_focus()

        elif self.isvariable(tok):
            return self.handle_variable(tok)

    def handle_focus(self):
        # a focus construction

        # a focus type

        if self.token(0) in FocusDrtTokens.FOCUS_TYPE:
            focus_type = self.token()
        else:
            raise ValueError('expected focus type')

        if self.token(0) == DrtTokens.COMMA: #if there is a comma (it's optional)
            self.token() # swallow the comma

        # an expression to be the focus element
        expression = self.parse_Expression()

        if self.token(0) == DrtTokens.COMMA: #if there is a comma (it's optional)
            self.token() # swallow the comma

        self.assertToken(self.token(), DrtTokens.OPEN_BRACKET)

        # the features of the focus element
        features = []
        while self.token(0) != DrtTokens.CLOSE_BRACKET:
            # Support expressions like FOCUS([x y],C) in the same way as FOCUS([x,y],C)
            if self.token(0) == DrtTokens.COMMA:
                self.token() # swallow the comma
            else:
                features.append(Variable(self.token()))
        self.token() # swallow the CLOSE_BRACKET token

        self.assertToken(self.token(), DrtTokens.CLOSE)

        print(type(expression))
        #return Focus(features, expression)
        if self.token(0) == Tokens.OPEN:
            #The Focus is used as a function
            self.token() #swallow the Open Paren
            argument = self.parse_Expression()
            self.assertToken(self.token(), Tokens.CLOSE)
            return self.make_ApplicationExpression(FocusConstantExpression(expression, focus_type, features), argument)

        return FocusConstantExpression(expression, focus_type, features)

    def make_ApplicationExpression(self, function, argument):
        if isinstance(function, FocusConstantExpression) or isinstance(argument, FocusConstantExpression):
            return FocusDrtApplicationExpression(function, argument)
        else:
            return DrtApplicationExpression(function, argument)

class FocusDrtApplicationExpression(DrtApplicationExpression):

    def __init__(self, function, argument):
        DrtApplicationExpression.__init__(self, function, argument)

    def substitute_bindings(self, bindings):
        argument = self.argument.substitute_bindings(bindings)
        function = self.function.substitute_bindings(bindings)
        return FocusDrtApplicationExpression(function, argument).simplify()

    def __simplify(self):
        function = self.function.simplify()
        argument = self.argument.simplify()
        print "function=", function, "argument=", argument
        if isinstance(function, FocusLambdaExpression) and isinstance(argument, FocusAbstractExpression):

            #result = function.replace(function.variable, argument, True).simplify()
            result = function.term.replace(function.variable, argument.expression, True).simplify()
            print "fofo result=", result, type(result)
            return FocusExpression(result, function.focus_structure)
        elif isinstance(function, FocusLambdaExpression):
            #a_refs = function.expression.visit(lambda e: isinstance(e, DRS) and [e.refs] or [], lambda *parts: sum(parts, []), [])
            drs = function.expression.term.first
            if isinstance(drs, DRS):
                refs = function.expression.term.first.refs
            else:
                raise ValueError("expected a DRS")

            result = function.expression.term.replace(function.expression.variable, argument).simplify()
            print "foa refs=", refs
            print "result=", result
            if len(refs) == 1:
                a_refs = {refs[0]:(self.function.focus_type, self.function.features)}
            else:
                raise ValueError("expected a DRS with exactly one referent")

            return FocusDRS(result.refs,a_refs,[],result.conds)

        elif isinstance(argument, FocusAbstractExpression): 
            result = function.term.replace(function.variable, argument.expression).simplify()
            return FocusExpression(result, argument.focus_structure)
        else:
            return self.__class__(function, argument)


from nltk.sem.drt import AbstractDrs

def gr(s, recursive=False):
    print "I am %s, %s" % (s, type(s))
    return []

AbstractDrs.get_refs = gr

def test():

    parser = load_parser('file:../data/focus-drt.fcfg', logic_parser=FocusDrtParser())

    #parser = load_parser('file:check.fcfg', logic_parser=DrtParser())

    #trees = parser.nbest_parse('Butch smokes'.split())
    trees = parser.nbest_parse('Butch picks-up a chainsaw'.split())
    #trees = parser.nbest_parse('no hammer does smoke'.split())

    drs1 = trees[0].node['SEM'].simplify()
    print(drs1)
    print(type(drs1))
    #drs1.draw()

if __name__ == '__main__':
    test()


