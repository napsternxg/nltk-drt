import temporaldrt
from temporaldrt import DrtAbstractVariableExpression, DrtIndividualVariableExpression, PresuppositionDRS, DRS, DrtTokens, DrtApplicationExpression, DefiniteDescriptionDRS, DrtConstantExpression, DrtFeatureConstantExpression
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

def get_drses(trail):
    for ancestor in trail:
        if isinstance(ancestor, DRS):
            yield ancestor

class PronounDRS(PresuppositionDRS):
    """A superclass for DRSs for personal, reflexive, 
    and possessive pronouns"""
    def is_pronoun_application_expression(self, expr):
        """Is expr of the form "PRO(x)"? """
        return isinstance(expr, DrtApplicationExpression) and\
             isinstance(expr.function, DrtAbstractVariableExpression) and \
             expr.function.variable.name == DrtTokens.PRONOUN and \
             isinstance(expr.argument, DrtIndividualVariableExpression)

    def _presupposition_readings(self, trail=[]):
        possible_antecedents = []
        pro = [cond for cond in self.conds if self.is_pronoun_application_expression(cond)][0]
        pro_variable = pro.argument.variable
        pro_features = (isinstance(pro.function, DrtFeatureConstantExpression) and pro.function.features) or None
        roles = {}
        events = {}
        refs = []
        for drs in get_drses(trail):
            print "drs", drs
            refs.extend(drs.refs)
            for cond in drs.conds:
                #exclude pronouns from resolution
                if self.is_pronoun_application_expression(cond) and\
                    not self._resolve_to_pronouns():
                    continue

                elif isinstance(cond, DrtApplicationExpression) and\
                    cond.argument.__class__ is DrtIndividualVariableExpression:
                    var = cond.argument.variable
                    # nouns/proper names
                    if isinstance(cond.function, DrtConstantExpression):
                        #filter out the variable itself
                        #filter out the variables with non-matching features
                        #allow only backward resolution

                        #print "refs", refs, "var", var, "pro_variable", pro_variable

                        if not var == pro_variable and\
                                (not isinstance(cond.function, DrtFeatureConstantExpression or\
                                 not pro_features) or\
                                 cond.function.features == pro_features):
                            possible_antecedents.append((self.make_VariableExpression(var), 0))
                    # role application
                    if isinstance(cond.function, DrtApplicationExpression) and\
                        isinstance(cond.function.argument, DrtIndividualVariableExpression):
                            roles.setdefault(var,set()).add(cond.function.function)
                            events.setdefault(var,set()).add(cond.function.argument)

        antecedents = []
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
            if self._is_possible_antecedent(var.variable, pro_variable, events):
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
                v = idx_map[key]
                for index, (var, rate) in enumerate(antecedents):
                    if var == v:
                        antecedents[index] = (var, rate+i)
                        break

        if len(antecedents) == 0:
            raise AnaphoraResolutionException("Variable '%s' does not "
                                "resolve to anything." % pro_variable)
            
        inner_drs = trail[-1]
        antecedents = sorted(antecedents, key=lambda e: e[1], reverse=True)
        print "antecedents", antecedents
        print inner_drs, antecedents[0] in inner_drs.refs
        self.refs.remove(pro_variable)
        return [[(inner_drs, lambda d: d.__class__(d.refs, [cond.replace(pro_variable, antecedent[0], False) for cond in d.conds]))] for antecedent in antecedents]

    def _is_possible_antecedent(self, variable, pro_variable, events):
        #non reflexive pronouns can not resolve to variables having a role in the same event
        return events[variable].isdisjoint(events[pro_variable])
    
    def _resolve_to_pronouns(self):
        return False

def main():
    from util import Tester
    tester = Tester('file:../data/grammar.fcfg', DrtParser)
    drs = tester.parse( "Mary kissed a girl. She bit she.")
    print drs
    readings = drs.readings()
    print readings
    for reading in readings:
        reading.draw()

if __name__ == '__main__':
    main()