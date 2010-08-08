from nltk.sem.logic import Variable, unique_variable, ApplicationExpression, EqualityExpression, AbstractVariableExpression, NegatedExpression, ImpExpression, BinaryExpression, LambdaExpression
from nltk.sem.drt import DRS, Tokens, DrtTokens, DrtParser, DrtApplicationExpression, DrtConstantExpression, DrtLambdaExpression, DrtVariableExpression, ConcatenationDRS, PossibleAntecedents, AnaphoraResolutionException
from nltk import load_parser

#def sb(e, bindings):
#    print "Expression.substitute_bindings(%s,%s)" % (e,bindings)
#    expr = e
#    for var in expr.variables():
#        if var in bindings:
#            val = bindings[var]
#            if isinstance(val, Variable):
#                val = VariableExpression(val)
#            elif not isinstance(val, Expression):
#                raise ValueError('Can not substitute a non-expression '
#                                 'value into an expression: %r' % (val,))
#            # Substitute bindings in the target value.
#            val = val.substitute_bindings(bindings)
#            # Replace var w/ the target value.
#            print "expr=%s, var=%s, val=%s" % (expr, var,val)
#            expr = expr.replace(var, val)
#    r = expr.simplify()
#    print "result=%s" % (r)
#    return r

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
        #print "FocusConstantExpression.substitute_bindings(%s)" % (bindings)
        expression = self.variable.substitute_bindings(bindings)

        features = []
        for var in self.focus_features:
            if var in bindings:
                val = bindings[var]
                if not isinstance(val, str):
                    raise ValueError('expected a string feature value')
                features.append(val)

        return self._make_DrtLambdaExpression(expression, self.focus_type, features)

    def _make_DrtLambdaExpression(self, expression, focus_type, features):
        assert isinstance(expression, DrtLambdaExpression)
        assert isinstance(expression.term, ConcatenationDRS)
        assert isinstance(expression.term.first, DRS)
        assert len(expression.term.first.refs) > 0
        var = expression.term.first.refs[-1]
        focus_structure = {var: (focus_type, features)}

        return DrtLambdaExpression(expression.variable, ConcatenationFocusDRS(FocusDRS(expression.term.first.refs, expression.term.first.conds, focus_structure), expression.term.second))

class FocusDRS(DRS):
    """A Discourse Representation Structure with Focus."""
    def __init__(self, refs, conds, focus={}):
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
                return FocusDRS(self.refs[:i] + [expression.variable] + self.refs[i + 1:],
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
                self = FocusDRS(self.refs[:i] + [newvar] + self.refs[i + 1:],
                           [cond.replace(ref, newvarex, True) for cond in self.conds],
                            self._replace_focus(ref, newvar))

            #replace in the conditions
            return FocusDRS(self.refs,
                       [cond.replace(variable, expression, replace_bound) 
                        for cond in self.conds],
                        self._replace_focus(variable, expression.variable))

    def simplify(self):
        return FocusDRS(self.refs, [cond.simplify() for cond in self.conds], self.focus)
    
    def resolve_anaphora(self):
        return resolve_anaphora(self)

    def str(self, syntax=DrtTokens.NLTK):
        if syntax == DrtTokens.PROVER9:
            return self.fol().str(syntax)
        else:
            return '([%s],[%s],[%s])' % (','.join([str(r) for r in self.refs]),
                                    ', '.join([c.str(syntax) for c in self.conds]),
                                    ','.join([str(v) + str(d) for v, d in self.focus.iteritems()]))

class ConcatenationFocusDRS(ConcatenationDRS):
    def simplify(self):
        first = self.first.simplify()
        second = self.second.simplify()
        
        def _alpha_covert_second(first, second):
            # For any ref that is in both 'first' and 'second'
            for ref in (set(first.get_refs(True)) & set(second.get_refs(True))):
                # alpha convert the ref in 'second' to prevent collision
                newvar = DrtVariableExpression(unique_variable(ref))
                second = second.replace(ref, newvar, True)
            return second

        if isinstance(first, FocusDRS) and isinstance(second, FocusDRS):
            second = _alpha_covert_second(first, second)            
            focus = dict(first.focus)
            focus.update(second.focus)
            return FocusDRS(first.refs + second.refs, first.conds + second.conds, focus)

        elif isinstance(first, FocusDRS) and isinstance(second, DRS):
            second = _alpha_covert_second(first, second)            
            return FocusDRS(first.refs + second.refs, first.conds + second.conds, first.focus)

        elif isinstance(first, DRS) and isinstance(second, FocusDRS):
            second = _alpha_covert_second(first, second)            
            return FocusDRS(first.refs + second.refs, first.conds + second.conds, second.focus)

        else:
            return self.__class__(first, second)

class FocusDrtParser(DrtParser):
    """A lambda calculus expression parser."""

    def isvariable(self, tok):
        return tok not in FocusDrtTokens.TOKENS

    def handle(self, tok):
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

        #focus handling

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

        if self.token(0) == Tokens.OPEN:
            #The Focus is used as a function
            self.token() #swallow the Open Parenthesis
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

    def substitute_bindings(self, bindings):
        argument = self.argument.substitute_bindings(bindings)
        function = self.function.substitute_bindings(bindings)
        return FocusDrtApplicationExpression(function, argument).simplify()

def resolve_anaphora(expression, trail=[]):
    
    if isinstance(expression, ApplicationExpression):
        if expression.is_pronoun_function():
            possible_antecedents = PossibleAntecedents()
            for ancestor in trail:
                for ref in ancestor.focus:
                    var = expression.make_VariableExpression(ref)
                    if not var == expression.argument:
                        possible_antecedents.append(var)
                    
                    #==========================================================
                    # Don't allow resolution to itself or other types
                    #==========================================================
#                        if refex.__class__ == expression.argument.__class__ and \
#                           not (refex == expression.argument):
#                            possible_antecedents.append(refex)

            if len(possible_antecedents) == 1:
                resolution = possible_antecedents[0]
            else:
                resolution = possible_antecedents 
            return expression.make_EqualityExpression(expression.argument, resolution)
        else:
            r_function = resolve_anaphora(expression.function, trail + [expression])
            r_argument = resolve_anaphora(expression.argument, trail + [expression])
            return expression.__class__(r_function, r_argument)

    elif isinstance(expression, FocusDRS):
        r_conds = []
        focus = {}
        for key, value in expression.focus.iteritems():
            focus[expression.make_VariableExpression(key)] = value

        for cond in expression.conds:
            r_cond = resolve_anaphora(cond, trail + [expression])

            # if the condition is of the form '(x = [])' then raise exception
            if isinstance(r_cond, EqualityExpression):
                if isinstance(r_cond.first, PossibleAntecedents):
                    #Reverse the order so that the variable is on the left
                    temp = r_cond.first
                    r_cond.first = r_cond.second
                    r_cond.second = temp
                #filter out the variables with non-matching features
                filtered_antecedents = PossibleAntecedents()
                first_features = focus[r_cond.first]
                print "var=", r_cond.first
                for var in r_cond.second:
                    if focus[var] == first_features:
                        filtered_antecedents.append(var)

                r_cond.second = filtered_antecedents
                print(filtered_antecedents)
                
                if isinstance(r_cond.second, PossibleAntecedents):
                    if not r_cond.second:
                        raise AnaphoraResolutionException("Variable '%s' does not "
                                "resolve to anything." % r_cond.first)
                        
            r_conds.append(r_cond)

        return expression.__class__(expression.refs, r_conds, expression.focus)
    
    elif isinstance(expression, AbstractVariableExpression):
        return expression
    
    elif isinstance(expression, NegatedExpression):
        return expression.__class__(resolve_anaphora(expression.term, trail + [expression]))

    elif isinstance(expression, ImpExpression): 
        return expression.__class__(resolve_anaphora(expression.first, trail + [expression]),
                              resolve_anaphora(expression.second, trail + [expression, expression.first]))

    elif isinstance(expression, BinaryExpression):
        return expression.__class__(resolve_anaphora(expression.first, trail + [expression]), 
                              resolve_anaphora(expression.second, trail + [expression]))

    elif isinstance(expression, LambdaExpression):
        return expression.__class__(expression.variable, resolve_anaphora(expression.term, trail + [expression]))


def test():

    parser = load_parser('file:../data/focus-drt.fcfg', logic_parser=FocusDrtParser())

    trees = parser.nbest_parse('Butch picks-up a chainsaw'.split())

    drs1 = trees[0].node['SEM'].simplify()
    print(drs1)
    trees = parser.nbest_parse('He likes it'.split())
    drs2 = trees[0].node['SEM'].simplify()
    print(drs2)
    drs3 = drs1 + drs2
    drs3 = drs3.simplify()
    print(drs3)
    drs4 = drs3.resolve_anaphora()
    print(drs4)
    
    import nltkfix

    drs4.draw()

if __name__ == '__main__':
    test()


