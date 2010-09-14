import temporaldrt
from temporaldrt import Reading, Variable, DrtVariableExpression, DrtAbstractVariableExpression, DrtIndividualVariableExpression, PresuppositionDRS, DRS, DrtTokens, DrtApplicationExpression, DefiniteDescriptionDRS, DrtConstantExpression, DrtFeatureConstantExpression
from nltk.sem.drt import AnaphoraResolutionException
from presuppositions import ProperNameDRS
# Nltk fix
import nltkfixtemporal
from nltk.sem.drt import AbstractDrs
def gr(s, recursive=False):
    return []
AbstractDrs.get_refs = gr
                        
class DrtParser(temporaldrt.DrtParser):
        
    def handle_PRESUPPOSITION_DRS(self, tok, context):
        """Parse new types of DRS: presuppositon DRSs.
        """
        self.assertNextToken(DrtTokens.OPEN)
        drs = self.handle_DRS(tok, context)
        if tok == DrtTokens.PROPER_NAME_DRS:
            return ProperNameDRS(drs.refs, drs.conds)
        elif tok == DrtTokens.DEFINITE_DESCRIPTION_DRS:
            return DefiniteDescriptionDRS(drs.refs, drs.conds)
        elif tok == DrtTokens.PRONOUN_DRS:
            return PronounDRS(drs.refs, drs.conds)

class PronounDRS(PresuppositionDRS):
    """A superclass for DRSs for personal, reflexive, 
    and possessive pronouns"""
    PRONOUNS = [DrtTokens.PRONOUN, DrtTokens.REFLEXIVE_PRONOUN, DrtTokens.POSSESSIVE_PRONOUN]

    def get_pronoun_data(self):
        """Is expr of the form "PRO(x)"? """
        for cond in self.conds:
            if isinstance(cond, DrtApplicationExpression) and\
             isinstance(cond.function, DrtAbstractVariableExpression) and \
             cond.function.variable.name in PronounDRS.PRONOUNS and \
             isinstance(cond.argument, DrtIndividualVariableExpression):
                return cond.argument.variable, cond.function.features if isinstance(cond.function, DrtFeatureConstantExpression) else None, cond.function.variable.name
                break

    def _presupposition_readings(self, trail=[]):
        possible_antecedents = []
        pro_variable, pro_features, pro_type = self.get_pronoun_data()
        roles = {}
        events = {}
        for drs in (ancestor for ancestor in trail if isinstance(ancestor, DRS)):
            print drs
            for cond in drs.conds:
                if isinstance(cond, DrtApplicationExpression) and\
                    cond.argument.__class__ is DrtIndividualVariableExpression:
                    var = cond.argument.variable
                    # nouns/proper names
                    if isinstance(cond.function, DrtConstantExpression):
                        #filter out the variable itself
                        #filter out the variables with non-matching features
                        #allow only backward resolution

                        #print "refs", refs, "var", var, "pro_variable", pro_variable

                        if (not isinstance(cond.function, DrtFeatureConstantExpression or\
                                 not pro_features) or cond.function.features == pro_features):
                            possible_antecedents.append((self.make_VariableExpression(var), 0))
                    # role application
                    if isinstance(cond.function, DrtApplicationExpression) and\
                        isinstance(cond.function.argument, DrtIndividualVariableExpression):
                            roles.setdefault(var,set()).add(cond.function.function)
                            events.setdefault(var,set()).add(cond.function.argument)

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

        antecedents = [(var, rank) for var, rank in possible_antecedents if self._is_possible_antecedent(var.variable, pro_variable, pro_type, events)]

        #ranking system
        #increment ranking for matching roles and map the positions of antecedents
        if len(antecedents) > 1:
            for index, (var, rank) in enumerate(antecedents):
                antecedents[index] = (var, rank + index + len(roles[var.variable].intersection(roles[pro_variable])))

        if len(antecedents) == 0:
            raise AnaphoraResolutionException("Variable '%s' does not "
                                "resolve to anything." % pro_variable)

        return [Reading([(trail[-1], PronounReplacer(pro_variable, var))]) for var, rank in sorted(antecedents, key=lambda e: e[1], reverse=True)], True

    def _is_possible_antecedent(self, variable, pro_variable, pro_type, events):
        #non reflexive pronouns can not resolve to variables having a role in the same event
        if pro_type == DrtTokens.PRONOUN:
            return events[variable].isdisjoint(events[pro_variable])
        elif pro_type == DrtTokens.REFLEXIVE_PRONOUN:
            return not events[variable].isdisjoint(events[pro_variable])
        else:
            return True

class PronounReplacer(object):
    def __init__(self, pro_var, new_var):
        self.pro_var = pro_var
        self.new_var = new_var
    def __call__(self, drs):
        return drs.__class__(drs.refs, [cond.replace(self.pro_var, self.new_var, False) for cond in drs.conds])

def main():
    from util import Tester
    tester = Tester('file:../data/grammar.fcfg', DrtParser)
    drs = tester.parse( "a boy kissed a girl. She bit he.")
    #drs = tester.parse( "John does walk. His car does walk.")
    #drs = tester.parse( "Mary does write John s letter of himself.")
    print drs
    #drs.draw()
    readings = drs.readings()
    print readings
    for reading in readings:
        reading.draw()

if __name__ == '__main__':
    main()