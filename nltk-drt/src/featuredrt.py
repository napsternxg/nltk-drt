from nltk.sem.logic import ParseException
from nltk.sem.logic import Variable
import temporaldrt as drt
from temporaldrt import AnaphoraResolutionException

class DrtTokens(drt.DrtTokens):
    REFLEXIVE_PRONOUN = 'REFPRO'
    POSSESSIVE_PRONOUN = 'POSPRO'
    OPEN_BRACE = '{'
    CLOSE_BRACE = '}'
    PUNCT = [OPEN_BRACE, CLOSE_BRACE]
    SYMBOLS = drt.DrtTokens.SYMBOLS + PUNCT
    TOKENS = drt.DrtTokens.TOKENS + PUNCT

class DrtFeatureConstantExpression(drt.DrtConstantExpression):
    """An expression with syntactic features attached"""
    def __init__(self, expression, features):
        self.variable = expression
        self.features = features
        
    def str(self, syntax=DrtTokens.NLTK):
        return str(self.variable) + "{" + ",".join([str(feature) for feature in self.features]) + "}"

class DrtFeatureConstantSubstitutionExpression(DrtFeatureConstantExpression):

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

        return self._make_DrtLambdaExpression(expression, features)

    def _make_DrtLambdaExpression(self, expression, features):
        assert isinstance(expression, drt.DrtLambdaExpression)
        if isinstance(expression.term, drt.ConcatenationDRS):
            term = drt.ConcatenationDRS(drt.DRS(expression.term.first.refs, self._make_conds(expression.term.first.conds, features)), expression.term.second)
        elif isinstance(expression.term, drt.DRS):
            term = drt.DRS(expression.term.refs, self._make_conds(expression.term.conds, features))
        else:
            #print "expression:", expression, type(expression), type(expression.term), type(expression.term.first)
            raise NotImplementedError()
        return drt.DrtLambdaExpression(expression.variable, term)

    def _make_conds(self, conds, features):
        assert len(conds) == 1, conds
        cond = conds[0]
        assert isinstance(cond, drt.DrtApplicationExpression)
        assert isinstance(cond.function, drt.DrtConstantExpression)
        return [cond.__class__(DrtFeatureConstantExpression(cond.function.variable, features), cond.argument)]

class DrtParser(drt.DrtParser):
    """A lambda calculus expression parser."""

    def get_all_symbols(self):
        return DrtTokens.SYMBOLS

    def isvariable(self, tok):
        return tok not in DrtTokens.TOKENS

    def handle_variable(self, tok, context):
        var = drt.DrtParser.handle_variable(self, tok, context)
        if isinstance(var, drt.DrtConstantExpression): #or isinstance(var, DrtApplicationExpression):
            # handle the feature structure of the variable
            try:
                if self.token(0) == DrtTokens.OPEN_BRACE:
                    self.token() # swallow the OPEN_BRACE
                    features = []
                    while self.token(0) != DrtTokens.CLOSE_BRACE:
                        features.append(Variable(self.token()))
                        
                        if self.token(0) == drt.DrtTokens.COMMA:
                            self.token() # swallow the comma
                    self.token() # swallow the CLOSE_BRACE
                    return DrtFeatureConstantSubstitutionExpression(var, features)
            except ParseException:
                #we reached the end of input, this constant has no features
                pass
        return var

    def make_ApplicationExpression(self, function, argument):
        """ Is self of the form "PRO(x)"? """
        if isinstance(function, drt.DrtAbstractVariableExpression) and \
               function.variable.name == DrtTokens.PRONOUN and \
               isinstance(argument, drt.DrtIndividualVariableExpression):
            return DrtPronounApplicationExpression(function, argument)

        """ Is self of the form "REFPRO(x)"? """
        if isinstance(function, drt.DrtAbstractVariableExpression) and \
               function.variable.name == DrtTokens.REFLEXIVE_PRONOUN and \
               isinstance(argument, drt.DrtIndividualVariableExpression):
            return DrtReflexivePronounApplicationExpression(function, argument)

        """ Is self of the form "POSPRO(x)"? """
        if isinstance(function, drt.DrtAbstractVariableExpression) and \
               function.variable.name == DrtTokens.POSSESSIVE_PRONOUN and \
               isinstance(argument, drt.DrtIndividualVariableExpression):
            return DrtPossessivePronounApplicationExpression(function, argument)

        elif isinstance(argument, drt.DrtEventVariableExpression):
            return DrtEventApplicationExpression(function, argument)

        elif isinstance(function, DrtEventApplicationExpression):
            return DrtRoleApplicationExpression(function, argument)

        else:
            return drt.DrtParser.make_ApplicationExpression(self, function, argument)

class DrtEventApplicationExpression(drt.DrtApplicationExpression):
    pass

class DrtRoleApplicationExpression(drt.DrtApplicationExpression):
    def get_role(self):
        return self.function.function
    def get_variable(self):
        return self.argument
    def get_event(self):
        return self.function.argument

class DrtPronounApplicationExpression(drt.DrtApplicationExpression):
    def resolve(self, trail=[], output=[]):
        possible_antecedents = PossibleEventAntecedents()
        pronouns = []
        pro_var = self.argument
        roles = {}
        events = {}
        pro_role = None
        pro_event = None
        refs = []
        for ancestor in trail:
            if isinstance(ancestor, drt.DRS):
                refs.extend(ancestor.refs)
                for cond in ancestor.conds:
                    #look for role assigning expressions:
                    if isinstance(cond, drt.DrtApplicationExpression) and\
                        not isinstance(cond, DrtEventApplicationExpression) and \
                        isinstance(cond.argument, drt.DrtIndividualVariableExpression):
                        var = cond.get_variable()
                        #filter out the variable itself
                        #filter out the variables with non-matching features
                        #allow only backward resolution
                        if not var.variable == pro_var.variable:
                            if var.features == pro_var.features and refs.index(var.variable) <  refs.index(pro_var.variable):
                                possible_antecedents.append((self.make_VariableExpression(var.variable), 0))
                                roles[var.variable] = cond.get_role()
                                events[var.variable] = cond.get_event()
                        else:
                            pro_role = cond.get_role()
                            pro_event = cond.get_event()

                    elif cond.is_pronoun_function():
                        pronouns.append(cond.argument)

        #exclude pronouns from resolution
        #possible_antecedents = possible_antecedents.exclude(pronouns)

        #non reflexive pronouns can not resolve to variables having a role in the same event
        antecedents = PossibleEventAntecedents()
        
        is_reflexive = isinstance(self, DrtReflexivePronounApplicationExpression)
        is_possessive = isinstance(self, DrtPossessivePronounApplicationExpression)
        if not is_reflexive:
            possible_antecedents = possible_antecedents.exclude(pronouns)
        for index, (var, rank) in enumerate(possible_antecedents):
            if not is_reflexive and not events[var.variable] == pro_event:
                antecedents.append((var, rank))
            elif (is_reflexive or is_possessive) and events[var.variable] == pro_event:
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

        if len(antecedents) == 0:
            raise drt.AnaphoraResolutionException("Variable '%s' does not "
                                "resolve to anything." % self.argument)
        elif len(antecedents) == 1:
            resolution = antecedents[0][0]
        else:
            resolution = antecedents

        return self.make_EqualityExpression(self.argument, resolution)

class DrtReflexivePronounApplicationExpression(DrtPronounApplicationExpression):
    pass

class DrtPossessivePronounApplicationExpression(DrtPronounApplicationExpression):
    pass

class PossibleEventAntecedents(drt.PossibleAntecedents):

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
