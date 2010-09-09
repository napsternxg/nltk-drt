from nltk.sem.logic import ParseException
from nltk.sem.logic import Variable
import temporaldrt as drt
from temporaldrt import AnaphoraResolutionException
from temporaldrt import DrtEqualityExpression
from temporaldrt import is_propername
from temporaldrt import DrtProperNameApplicationExpression
from temporaldrt import DrtConstantExpression
class DrtTokens(drt.DrtTokens):
    REFLEXIVE_PRONOUN = 'REFPRO'
    POSSESSIVE_PRONOUN = 'POSPRO'
    OPEN_BRACE = '{'
    CLOSE_BRACE = '}'
    PUNCT = [OPEN_BRACE, CLOSE_BRACE]
    SYMBOLS = drt.DrtTokens.SYMBOLS + PUNCT
    TOKENS = drt.DrtTokens.TOKENS + PUNCT

class DrtFeatureConstantExpression(DrtConstantExpression):
    """An expression with syntactic features attached"""
    def __init__(self, expression, features):
        self.variable = expression
        self.features = features

    def str(self, syntax=DrtTokens.NLTK):
        return str(self.variable) + "{" + ",".join([str(feature) for feature in self.features]) + "}"
    
    def deepcopy(self, operation=None):
        return self.__class__(self.variable, self.features)

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

#    def handle_variable(self, tok, context):
#        var = drt.DrtParser.handle_variable(self, tok, context)
#        if isinstance(var, drt.DrtConstantExpression): #or isinstance(var, DrtApplicationExpression):
#            # handle the feature structure of the variable
#            try:
#                if self.token(0) == DrtTokens.OPEN_BRACE:
#                    self.token() # swallow the OPEN_BRACE
#                    features = []
#                    while self.token(0) != DrtTokens.CLOSE_BRACE:
#                        features.append(Variable(self.token()))
#                        
#                        if self.token(0) == drt.DrtTokens.COMMA:
#                            self.token() # swallow the comma
#                    self.token() # swallow the CLOSE_BRACE
#                    return DrtFeatureConstantSubstitutionExpression(var, features)
#            except ParseException:
#                #we reached the end of input, this constant has no features
#                pass
#        return var
    
    
    def handle_variable(self, tok, context):
        #It's either: 1) a predicate expression: sees(x,y)
        #             2) an application expression: P(x)
        #             3) a solo variable: john OR x
        accum = self.make_VariableExpression(tok)
        # handle the feature structure of the variable
        features = []
        try:
            if self.token(0) == DrtTokens.OPEN_BRACE:
                self.token() # swallow the OPEN_BRACE
                while self.token(0) != DrtTokens.CLOSE_BRACE:
                    features.append(self.token())
                    if self.token(0) == drt.DrtTokens.COMMA:
                        self.token() # swallow the comma
                self.token() # swallow the CLOSE_BRACE
        except ParseException:
            #we've reached the end of input, this constant has no features
            pass
        if self.inRange(0) and self.token(0) == DrtTokens.OPEN:
            if features:
                accum = DrtFeatureConstantExpression(accum.variable, features)
            #The predicate has arguments
            if isinstance(accum, drt.DrtIndividualVariableExpression):
                raise ParseException(self._currentIndex, 
                                     '\'%s\' is an illegal predicate name.  '
                                     'Individual variables may not be used as '
                                     'predicates.' % tok)
            self.token() #swallow the Open Paren
            
            #curry the arguments
            accum = self.make_ApplicationExpression(accum, 
                                                    self.parse_Expression('APP'))
            while self.inRange(0) and self.token(0) == DrtTokens.COMMA:
                self.token() #swallow the comma
                accum = self.make_ApplicationExpression(accum, 
                                                        self.parse_Expression('APP'))
            self.assertNextToken(DrtTokens.CLOSE)
        elif features:
            accum = DrtFeatureConstantSubstitutionExpression(accum.variable, map(Variable,features))
        return accum

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
        
        elif isinstance(function, DrtConstantExpression) and\
               is_propername(function.variable.name):
            return DrtProperNameApplicationExpression(function, argument)

#        elif isinstance(argument, drt.DrtEventVariableExpression):
#            return DrtEventApplicationExpression(function, argument)
#
#        elif isinstance(function, DrtEventApplicationExpression):
#            return DrtRoleApplicationExpression(function, argument)

        else:
            return drt.DrtParser.make_ApplicationExpression(self, function, argument)

#class DrtEventApplicationExpression(drt.DrtApplicationExpression):
#    pass
#
#class DrtRoleApplicationExpression(drt.DrtApplicationExpression):
#    def get_role(self):
#        return self.function.function
#    def get_variable(self):
#        return self.argument.variable
#    def get_event(self):
#        return self.function.argument

class DrtPronounApplicationExpression(drt.DrtApplicationExpression):
    def resolve(self, trail=[]):
        possible_antecedents = RankedPossibleAntecedents()
        pro_variable = self.argument.variable
        roles = {}
        events = {}
        refs = []
        for ancestor in trail:
            if isinstance(ancestor, drt.DRS):
                refs.extend(ancestor.refs)
                for cond in ancestor.conds:
                    #exclude pronouns from resolution
                    if isinstance(cond, DrtPronounApplicationExpression) and\
                        not self.resolve_to_pronouns():
                        continue

                    elif isinstance(cond, drt.DrtApplicationExpression) and\
                        cond.argument.__class__ is drt.DrtIndividualVariableExpression:
                        var = cond.argument.variable
                        # nouns/proper names
                        if isinstance(cond.function, DrtConstantExpression):
                            #filter out the variable itself
                            #filter out the variables with non-matching features
                            #allow only backward resolution
                            if not var == pro_variable and\
                                    (not isinstance(cond.function, DrtFeatureConstantExpression or\
                                     not isinstance(self.function, DrtFeatureConstantExpression)) or\
                                     cond.function.features == self.function.features) and\
                                    refs.index(var) <  refs.index(pro_variable):
                                possible_antecedents.append((self.make_VariableExpression(var), 0))
                        # role application
                        if isinstance(cond.function, drt.DrtApplicationExpression) and\
                            isinstance(cond.function.argument, drt.DrtIndividualVariableExpression):
                                roles.setdefault(var,set()).add(cond.function.function)
                                events.setdefault(var,set()).add(cond.function.argument)

        antecedents = RankedPossibleAntecedents()
        #filter by events
        #in case pronoun participates in only one event, which has no other participants,
        #try to extend it with interlinked events
        #f.e. THEME(z5,z3), THEME(e,z5) where z3 only participates in event z5
        #will be extended to participate in e, but only if z5 has only one participant
        if len(events[pro_variable]) == 1:
            for e in events[pro_variable]:
                event = e
            participant_count = 0
            for event_set in events.itervalues():
                if event in event_set:
                    participant_count+=1
            if participant_count == 1:
                try:
                    events[pro_variable] = events[pro_variable].union(events[event.variable])
                except KeyError:
                    pass
        for var, rank in possible_antecedents:
            if self.is_possible_antecedent(var.variable, events):
                antecedents.append((var, rank))

        #ranking system
        #increment ranking for matching roles and map the positions of antecedents
        if len(antecedents) > 1:
            idx_map = {}
            for index, (var, rank) in enumerate(antecedents):
                idx_map[refs.index(var.variable)] = var
                antecedents[index] = (var, rank + len(roles[var.variable].intersection(roles[pro_variable])))

            #rank by proximity

            for i,key in enumerate(sorted(idx_map)):
                j = antecedents.index(idx_map[key])
                antecedents[j] = (antecedents[j][0], antecedents[j][1]+i)

        if len(antecedents) == 0:
            raise AnaphoraResolutionException("Variable '%s' does not "
                                "resolve to anything." % self.argument)
        elif len(antecedents) == 1:
            return self.make_EqualityExpression(self.argument, antecedents[0][0])
        else:
            return DrtPossibleAntecedentsEqualityExpression(self.argument, antecedents)

    def is_possible_antecedent(self, variable, events):
        #non reflexive pronouns can not resolve to variables having a role in the same event
        return events[variable].isdisjoint(events[self.argument.variable])
    
    def resolve_to_pronouns(self):
        return False

class DrtReflexivePronounApplicationExpression(DrtPronounApplicationExpression):
    def is_possible_antecedent(self, variable, events):
        return not events[variable].isdisjoint(events[self.argument.variable])
    def resolve_to_pronouns(self):
        return True

class DrtPossessivePronounApplicationExpression(DrtPronounApplicationExpression):
    def is_possible_antecedent(self, variable, events):
        return True
    def resolve_to_pronouns(self):
        return True

class DrtPossibleAntecedentsEqualityExpression(DrtEqualityExpression):
    def resolve(self, trail=[]):
        return self.__class__(self.first, self.second.resolve(trail))

class RankedPossibleAntecedents(drt.PossibleAntecedents):

    def free(self, indvar_only=True):
        """Set of free variables."""
        return set([item[0] for item in self])

    def replace(self, variable, expression, replace_bound=False):
        """Replace all instances of variable v with expression E in self,
        where v is free in self."""
        result = RankedPossibleAntecedents()
        for item in self:
            if item[0] == variable:
                result.append(expression, item[1])
            else:
                result.append(item)
        return result
        
    def index(self, variable):
        for i, item in enumerate(self):
            if item[0] == variable:
                return i
        raise ValueError, type(variable)
    
    def resolve(self, trail=[]):
        max_rank = -1
        vars = []
        for var, rank in self:
            if rank == max_rank:
                vars.append(var)
            elif rank > max_rank:
                max_rank = rank
                vars = [var]

        if len(vars) == 1:
            return vars[0]
        else:
            raise AnaphoraResolutionException("Can't resolve based on ranking")
            
    def str(self, syntax=DrtTokens.NLTK):
        return '[' +  ','.join([str(item[0]) + "(" + str(item[1]) + ")" for item in self]) + ']'
