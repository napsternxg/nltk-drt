from nltk.sem.logic import ParseException, Variable, unique_variable, ApplicationExpression, EqualityExpression, AbstractVariableExpression, NegatedExpression, ImpExpression, BinaryExpression, LambdaExpression
from nltk.sem.drt import DrtLambdaExpression, DrtEventVariableExpression, DrtConstantExpression, DRS, DrtTokens, DrtParser, DrtApplicationExpression, DrtVariableExpression, ConcatenationDRS, PossibleAntecedents, AnaphoraResolutionException
from nltk import load_parser

class EventDrtTokens(DrtTokens):
    OPEN_BRACE = '{'
    CLOSE_BRACE = '}'
    PUNCT = [OPEN_BRACE, CLOSE_BRACE]
    SYMBOLS = DrtTokens.SYMBOLS + PUNCT
    TOKENS = DrtTokens.TOKENS + PUNCT
    

class FeatureExpression(DrtConstantExpression):
    """An expression with syntactic features attached"""
    def __init__(self, expression, features):
        self.variable = expression
        self.features = features

    def substitute_bindings(self, bindings):
        #print "FeatureConstantExpression.substitute_bindings(%s)" % (bindings)
        expression = self.variable.substitute_bindings(bindings)

        features = []
        for var in self.features:
            try:
                val = bindings[var]
                if not isinstance(val, str):
                    raise ValueError('expected a string feature value')
                features.append(val)
            except KeyError:
                pass

        #print features
        return self._make_DrtLambdaExpression(expression, features)

    def _make_DrtLambdaExpression(self, expression, features):
        assert isinstance(expression, DrtLambdaExpression)
        assert isinstance(expression.term, ConcatenationDRS)
        assert isinstance(expression.term.first, DRS), type(expression.term.first)
        assert len(expression.term.first.refs) == 1
        var = expression.term.first.refs[-1]
        features = {var: features}

        return DrtLambdaExpression(expression.variable, ConcatenationEventDRS(EventDRS(expression.term.first.refs, expression.term.first.conds, features), expression.term.second))


class EventDRS(DRS):
    """An event based Discourse Representation Structure with features."""
    def __init__(self, refs, conds, features={}):
        """
        @param refs: C{list} of C{DrtIndividualVariableExpression} for the 
        discourse referents
        @param conds: C{list} of C{Expression} for the conditions
        """ 
        self.refs = refs
        self.conds = conds
        self.features = features

    def __add__(self, other):
        return ConcatenationEventDRS(self, other)
    
    def _replace_features(self, var, new_var):
        try:
            data = self.features[var]
            features = dict(self.features)
            del features[var]
            features[new_var] = data
        except KeyError:
            features = self.features
        return features

    def replace(self, variable, expression, replace_bound=False):

        """Replace all instances of variable v with expression E in self,
        where v is free in self."""

        try:
            #if a bound variable is the thing being replaced
            i = self.refs.index(variable)
            if not replace_bound:
                return self
            else:
                return EventDRS(self.refs[:i] + [expression.variable] + self.refs[i + 1:],
                           [cond.replace(variable, expression, True) for cond in self.conds],
                           self._replace_features(variable, expression.variable))
        except ValueError:
            #variable not bound by this DRS
            
            # any bound variable that appears in the expression must
            # be alpha converted to avoid a conflict
            for ref in (set(self.refs) & expression.free()):
                newvar = unique_variable(ref) 
                newvarex = DrtVariableExpression(newvar)
                i = self.refs.index(ref)
                self = EventDRS(self.refs[:i] + [newvar] + self.refs[i + 1:],
                           [cond.replace(ref, newvarex, True) for cond in self.conds],
                            self._replace_features(ref, newvar))

            #replace in the conditions
            return EventDRS(self.refs,
                       [cond.replace(variable, expression, replace_bound) 
                        for cond in self.conds],
                        self._replace_features(variable, expression.variable))

    def simplify(self):
        return EventDRS(self.refs, [cond.simplify() for cond in self.conds], self.features)
    
    def resolve_anaphora(self):
        return resolve_anaphora(self)

    def str(self, syntax=DrtTokens.NLTK):
        if syntax == DrtTokens.PROVER9:
            return self.fol().str(syntax)
        else:
            refs = []
            for ref in self.refs:
                features = ""
                if ref in self.features:
                    features = '{' + ','.join(self.features[ref]) +'}'
                refs.append(str(ref) + features)
            return '([%s],[%s])' % (','.join(refs),
                                    ', '.join([c.str(syntax) for c in self.conds]))

class ConcatenationEventDRS(ConcatenationDRS):
    def simplify(self):
        #print "ConcatenationEventDRS.simplify(%s)" % (self)
        first = self.first.simplify()
        second = self.second.simplify()
        
        def _alpha_covert_second(first, second):
            # For any ref that is in both 'first' and 'second'
            for ref in (set(first.get_refs(True)) & set(second.get_refs(True))):
                # alpha convert the ref in 'second' to prevent collision
                newvar = DrtVariableExpression(unique_variable(ref))
                second = second.replace(ref, newvar, True)
            return second

        if isinstance(first, EventDRS) and isinstance(second, EventDRS):
            second = _alpha_covert_second(first, second)
            features = dict(first.features)
            for idx,ref in enumerate(first.refs):
                if ref not in first.features and idx in second.features:
                    features[ref] = second.features[idx]

            features.update(second.features)
            # remove all features with integer keys
            for key in features.keys():
                if isinstance(key, int):
                    del features[key]
            return EventDRS(first.refs + second.refs, first.conds + second.conds, features)

        elif isinstance(first, EventDRS) and isinstance(second, DRS):
            second = _alpha_covert_second(first, second)            
            return EventDRS(first.refs + second.refs, first.conds + second.conds, first.features)

        elif isinstance(first, DRS) and isinstance(second, EventDRS):
            second = _alpha_covert_second(first, second)            
            return EventDRS(first.refs + second.refs, first.conds + second.conds, second.features)

        else:
            return self.__class__(first, second)

class EventDrtParser(DrtParser):
    """A lambda calculus expression parser."""

    def get_all_symbols(self):
        return EventDrtTokens.SYMBOLS

    def isvariable(self, tok):
        return tok not in EventDrtTokens.TOKENS

    def handle_variable(self, tok):
        var = DrtParser.handle_variable(self, tok)
        if isinstance(var, DrtConstantExpression) or isinstance(var, DrtApplicationExpression):
            # handle the feature structure of the variable
            try:
                if self.token(0) == EventDrtTokens.OPEN_BRACE:
                    self.token() # swallow the OPEN_BRACE
                    features = []
                    while self.token(0) != EventDrtTokens.CLOSE_BRACE:
                        features.append(Variable(self.token()))
                        
                        if self.token(0) == DrtTokens.COMMA:
                            self.token() # swallow the comma
                    self.token() # swallow the CLOSE_BRACE
                    return FeatureExpression(var, features)
            except ParseException:
                #we reached the end of input, this constant has no features
                pass
        return var

    def make_ApplicationExpression(self, function, argument):
        if isinstance(argument, DrtEventVariableExpression):
            return DrtEventApplicationExpression(function, argument)
        elif isinstance(function, DrtEventApplicationExpression):
            return DrtRoleApplicationExpression(function, argument)
        else:
            return DrtApplicationExpression(function, argument)

class DrtEventApplicationExpression(DrtApplicationExpression):
    pass
class DrtRoleApplicationExpression(DrtApplicationExpression):
    pass

class PossibleEventAntecedents(PossibleAntecedents):
    def __init__(self):
        self.roles = []

    def append(self, var, role):
        list.append(self, var)
        self.roles.append(role)
        
    def iteritems(self):
        for var, role in zip(self, self.roles):
            yield var, role

def resolve_anaphora(expression, trail=[]):
    
    if isinstance(expression, ApplicationExpression):
        if expression.is_pronoun_function():
            possible_antecedents = PossibleEventAntecedents()
            for ancestor in trail:
                for cond in ancestor.conds:
                    if isinstance(cond, DrtRoleApplicationExpression):
                        #print(cond.argument.variable)
                        var = expression.make_VariableExpression(cond.argument.variable)
                        if not var == expression.argument:
                            possible_antecedents.append(var, cond.function.function)
                        else:
                            expression.argument.role = cond.function.function
                    
                    #==========================================================
                    # Don't allow resolution to itself or other types
                    #==========================================================
#                        if refex.__class__ == expression.argument.__class__ and \
#                           not (refex == expression.argument):
#                            possible_antecedents.append(refex)

            return expression.make_EqualityExpression(expression.argument, possible_antecedents)
        
        else:
            r_function = resolve_anaphora(expression.function, trail + [expression])
            r_argument = resolve_anaphora(expression.argument, trail + [expression])
            return expression.__class__(r_function, r_argument)

    elif isinstance(expression, EventDRS):
        r_conds = []
        features = {}
        for key, value in expression.features.iteritems():
            features[expression.make_VariableExpression(key)] = value

        for cond in expression.conds:
            r_cond = resolve_anaphora(cond, trail + [expression])

            # if the condition is of the form '(x = [])' then raise exception
            if isinstance(r_cond, EqualityExpression):
                if isinstance(r_cond.first, PossibleEventAntecedents):
                    #Reverse the order so that the variable is on the left
                    temp = r_cond.first
                    r_cond.first = r_cond.second
                    r_cond.second = temp
                #filter out the variables with non-matching features
                filtered_antecedents = PossibleEventAntecedents()
                first_features = features[r_cond.first]
                #print r_cond.second, r_cond.second.roles
                # first filter by features
                for var,role in r_cond.second.iteritems():
                    if features[var] == first_features:
                        filtered_antecedents.append(var, role)

                #print(filtered_antecedents)
                # second filter by thematic role
                if len(filtered_antecedents) > 1:
                    second_filtered_antecedents = PossibleEventAntecedents()
                    for var, role in filtered_antecedents.iteritems():
                        if role == r_cond.first.role:
                            second_filtered_antecedents.append(var, role)
                    # check if we still have some variables left, otherwise revert
                    if len(filtered_antecedents) > 0:
                        filtered_antecedents = second_filtered_antecedents
                        
                    #print(second_filtered_antecedents)

                if len(filtered_antecedents) == 1:
                    r_cond.second  = filtered_antecedents[0]
                else:
                    r_cond.second = filtered_antecedents
                    
                    if isinstance(r_cond.second, PossibleEventAntecedents):
                        if not r_cond.second:
                            raise AnaphoraResolutionException("Variable '%s' does not "
                                    "resolve to anything." % r_cond.first)
                        
            r_conds.append(r_cond)

        return expression.__class__(expression.refs, r_conds, expression.features)
    
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

    parser = load_parser('file:../data/eventdrt.fcfg', logic_parser=EventDrtParser())

    trees = parser.nbest_parse('Jeff likes a car'.split())
    drs1 = trees[0].node['SEM'].simplify()
    print(drs1)
    trees = parser.nbest_parse('He kills it'.split())
    drs2 = trees[0].node['SEM'].simplify()
    print(drs2)
    drs = drs1 + drs2
    drs = drs.simplify()
    print(drs)
    drs = drs.resolve_anaphora()
    print(drs)

    #import nltkfix

    #drs.draw()

if __name__ == '__main__':
    test()


