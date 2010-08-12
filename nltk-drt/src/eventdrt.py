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
    def get_role(self):
        return self.function.function
    def get_variable(self):
        return self.argument.variable

class PossibleEventAntecedents(PossibleAntecedents):

    def free(self, indvar_only=True):
        """Set of free variables."""
        return set([item[0] for item in self])

    def replace(self, variable, expression, replace_bound=False):
        """Replace all instances of variable v with expression E in self,
        where v is free in self."""
        result = PossibleEventAntecedents()
        for item in self:
            if item[0] == variable:
                result.append(expression, item[1], item[2])
            else:
                result.append(item)
        return result
            
    def exclude(self, vars):
        result = PossibleEventAntecedents()
        for item in self:
            if item[0] not in vars:
                result.append(item)
        return result
        
    def index(self, variable):
        for i, item in enumerate(self):
            if item[0] == variable:
                return i
        raise ValueError
            
    def str(self, syntax=DrtTokens.NLTK):
        return '[' +  ','.join([str(item[0]) + "(" + str(item[2]) + ")" for item in self]) + ']'

def resolve_anaphora(expression, trail=[]):
    
    if isinstance(expression, ApplicationExpression):
        if expression.is_pronoun_function():
            possible_antecedents = PossibleEventAntecedents()
            pronouns = []
            for ancestor in trail:
                #look for role assigning expressions:
                for cond in ancestor.conds:
                    if isinstance(cond, DrtRoleApplicationExpression):
                        var = expression.make_VariableExpression(cond.get_variable())
                        if not var == expression.argument:
                            possible_antecedents.append((var, cond.get_role(), 0))
                        else:
                            expression.argument.role = cond.get_role()
                    elif cond.is_pronoun_function():
                        pronouns.append(cond.argument)

            #exclude pronouns from resolution
            possible_antecedents = possible_antecedents.exclude(pronouns)

            return expression.make_EqualityExpression(expression.argument, possible_antecedents)
        
        else:
            r_function = resolve_anaphora(expression.function, trail + [expression])
            r_argument = resolve_anaphora(expression.argument, trail + [expression])
            return expression.__class__(r_function, r_argument)

    elif isinstance(expression, EventDRS):
        r_conds = []

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
                first_features = expression.features[r_cond.first.variable]
                #print "start:", r_cond.second
                # filter by features
                for var,role,rank in r_cond.second:
                    if expression.features[var.variable] == first_features:
                        filtered_antecedents.append((var, role, rank))

                # allow only backward resolution
                #print "before:", r_cond.first.variable, filtered_antecedents
                new_filtered_antecedents = PossibleEventAntecedents()
                first_index = expression.refs.index(r_cond.first.variable)
                idx_map = {}
                for idx, ref in enumerate(expression.refs[:first_index]):
                    try:
                        i = filtered_antecedents.index(expression.make_VariableExpression(ref))
                        new_filtered_antecedents.append(filtered_antecedents[i])
                        idx_map[idx] = filtered_antecedents[i][0]
                    except ValueError:
                        pass

                filtered_antecedents = new_filtered_antecedents
                #rank by proximity
                if len(idx_map) > 1:
                    for i,key in enumerate(sorted(idx_map)):
                        j = filtered_antecedents.index(idx_map[key])
                        filtered_antecedents[j] = (filtered_antecedents[j][0], filtered_antecedents[j][1], filtered_antecedents[j][2]+i)
                
                #print "after:", r_cond.first.variable, filtered_antecedents
                # rank by thematic role
                for i,(var, role, rank) in enumerate(filtered_antecedents):
                    if role == r_cond.first.role:
                        filtered_antecedents[i] = (var, role, rank+1)
                
                    #print(third_filtered_antecedents)

                if len(filtered_antecedents) == 1:
                    r_cond.second  = filtered_antecedents[0][0]
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


