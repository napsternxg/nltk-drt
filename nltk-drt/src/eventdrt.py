from nltk.sem.logic import ParseException, Variable, unique_variable, ApplicationExpression, EqualityExpression, AbstractVariableExpression, NegatedExpression, ImpExpression, BinaryExpression, LambdaExpression
from nltk.sem.drt import DrtImpExpression, AbstractDrs, DrtAbstractVariableExpression, DrtIndividualVariableExpression, DrtLambdaExpression, DrtEventVariableExpression, DrtConstantExpression, DRS, DrtTokens, DrtParser, DrtApplicationExpression, DrtVariableExpression, ConcatenationDRS, PossibleAntecedents, AnaphoraResolutionException
from nltk import load_parser

class EventDrtTokens(DrtTokens):
    REFLEXIVE_PRONOUN = 'REFPRO'
    POSSESSIVE_PRONOUN = 'POSPRO'
    PRONOUNS = [DrtTokens.PRONOUN, REFLEXIVE_PRONOUN, POSSESSIVE_PRONOUN]
    OPEN_BRACE = '{'
    CLOSE_BRACE = '}'
    PUNCT = [OPEN_BRACE, CLOSE_BRACE]
    SYMBOLS = DrtTokens.SYMBOLS + PUNCT
    TOKENS = DrtTokens.TOKENS + PUNCT

def is_pronoun_function(expr):
    """ Is self of the form "PRO(x)"? or "REFPRO(x)"? r "POSPRO(x)"? """
    return isinstance(expr, DrtApplicationExpression) and \
           isinstance(expr.function, DrtAbstractVariableExpression) and \
           (expr.function.variable.name in EventDrtTokens.PRONOUNS) and \
           isinstance(expr.argument, DrtIndividualVariableExpression)

def is_reflexive_pronoun_function(expr):
    """ Is self of the form "REFPRO(x)"? """
    return isinstance(expr, DrtApplicationExpression) and \
           isinstance(expr.function, DrtAbstractVariableExpression) and \
           expr.function.variable.name == EventDrtTokens.REFLEXIVE_PRONOUN and \
           isinstance(expr.argument, DrtIndividualVariableExpression)

def is_possessive_pronoun_function(expr):
    """ Is self of the form "REFPRO(x)"? """
    return isinstance(expr, DrtApplicationExpression) and \
           isinstance(expr.function, DrtAbstractVariableExpression) and \
           expr.function.variable.name == EventDrtTokens.POSSESSIVE_PRONOUN and \
           isinstance(expr.argument, DrtIndividualVariableExpression)

#AbstractDrs.is_pronoun_function = is_pronoun_function
#AbstractDrs.is_reflexive_pronoun_function = is_reflexive_pronoun_function

def get_refs(self, recursive=False):
    return []

AbstractDrs.get_refs = get_refs

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
        #print "expression:", expression
        if isinstance(expression, DrtLambdaExpression) and\
        isinstance(expression.term, ConcatenationDRS) and\
        isinstance(expression.term.first, DRS) and\
        expression.term.second.argument.variable in expression.term.first.refs:
            features_map = {expression.term.second.argument.variable: features}
            if isinstance(expression.term.first, EventDRS):
                features_map.update(expression.term.first.features)
            return DrtLambdaExpression(expression.variable, ConcatenationEventDRS(EventDRS(expression.term.first.refs, expression.term.first.conds, features_map), expression.term.second))
        elif isinstance(expression, DrtLambdaExpression) and\
        isinstance(expression.term, DRS) and\
        len(expression.term.conds) == 1 and\
        isinstance(expression.term.conds[0], DrtImpExpression) and\
        isinstance(expression.term.conds[0].first, DRS) and\
        expression.term.conds[0].second.argument.variable in expression.term.conds[0].first.refs:
            #print type(expression.term.conds[0])
            features_map = {expression.term.conds[0].second.argument.variable: features}
            return DrtLambdaExpression(expression.variable, EventDRS(expression.term.refs, [DrtImpExpression(EventDRS(expression.term.conds[0].first.refs, expression.term.conds[0].first.conds, features_map), expression.term.conds[0].second)]))


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
                        self.features)

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
            return ConcatenationDRS.simplify(self)

class EventDrtParser(DrtParser):
    """A lambda calculus expression parser."""

    def get_all_symbols(self):
        return EventDrtTokens.SYMBOLS

    def isvariable(self, tok):
        return tok not in EventDrtTokens.TOKENS

    def handle_variable(self, tok):
        var = DrtParser.handle_variable(self, tok)
        if isinstance(var, DrtConstantExpression): #or isinstance(var, DrtApplicationExpression):
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

    def get_BooleanExpression_factory(self, tok):
        """This method serves as a hook for other logic parsers that
        have different boolean operators"""
        if tok == DrtTokens.DRS_CONC:
            return ConcatenationEventDRS
        else:
            return DrtParser.get_BooleanExpression_factory(self, tok)

class DrtEventApplicationExpression(DrtApplicationExpression):
    pass
class DrtRoleApplicationExpression(DrtApplicationExpression):
    def get_role(self):
        return self.function.function
    def get_variable(self):
        return self.argument.variable
    def get_event(self):
        return self.function.argument

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
                result.append(expression, item[1])
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
        raise ValueError, type(variable)
            
    def str(self, syntax=DrtTokens.NLTK):
        return '[' +  ','.join([str(item[0]) + "(" + str(item[1]) + ")" for item in self]) + ']'

def resolve_anaphora(expression, trail=[]):
    
    if isinstance(expression, ApplicationExpression):
        if is_pronoun_function(expression):
            possible_antecedents = PossibleEventAntecedents()
            pronouns = []
            pro_var = expression.argument.variable
            roles = {}
            events = {}
            pro_role = None
            pro_event = None
            pro_features = None
            features = {}
            refs = []
            for ancestor in trail:
                if isinstance(ancestor, EventDRS):
                    features.update(ancestor.features)
                    refs.extend(ancestor.refs)
                    if pro_var in features:
                        #print features
                        if not pro_features:
                            pro_features = features[pro_var]
                        for cond in ancestor.conds:
                            #look for role assigning expressions:
                            if isinstance(cond, DrtRoleApplicationExpression):
                                var = cond.get_variable()
                                #filter out the variable itself
                                #filter out the variables with non-matching features
                                #allow only backward resolution
                                if not var == pro_var:
                                    if features[var] == pro_features and refs.index(var) <  refs.index(pro_var):
                                        possible_antecedents.append((expression.make_VariableExpression(var), 0))
                                        roles[var] = cond.get_role()
                                        events[var] = cond.get_event()
                                else:
                                    pro_role = cond.get_role()
                                    pro_event = cond.get_event()
        
                            elif cond.is_pronoun_function():
                                pronouns.append(cond.argument)

            #exclude pronouns from resolution
            #possible_antecedents = possible_antecedents.exclude(pronouns)

            #non reflexive pronouns can not resolve to variables having a role in the same event
            antecedents = PossibleEventAntecedents()
            
            is_reflexive = is_reflexive_pronoun_function(expression)
            is_possesive = is_possessive_pronoun_function(expression)
            if not is_reflexive:
                possible_antecedents = possible_antecedents.exclude(pronouns)
            for index, (var, rank) in enumerate(possible_antecedents):
                if not is_reflexive and not events[var.variable] == pro_event:
                    antecedents.append((var, rank))
                elif (is_reflexive or is_possesive) and events[var.variable] == pro_event:
                    antecedents.append((var, rank))

            #ranking system
            #increment ranking for matching roles and map the positions of antecedents
            if len(antecedents) > 1:
                idx_map = {}
                for index, (var, rank) in enumerate(antecedents):
                    idx_map[refs.index(var.variable)] = var
                    if roles[var.variable] == pro_role:
                        antecedents[index] = (var, rank+1)
    
                #rank by proximity

                for i,key in enumerate(sorted(idx_map)):
                    j = antecedents.index(idx_map[key])
                    antecedents[j] = (antecedents[j][0], antecedents[j][1]+i)

            if len(antecedents) == 1:
                resolution = antecedents[0][0]
            else:
                resolution = antecedents 

            return expression.make_EqualityExpression(expression.argument, resolution)
        
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

    else:
        return expression

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


