import temporaldrt
from temporaldrt import PronounDRS, Reading, Variable, DrtVariableExpression, DrtAbstractVariableExpression, DrtIndividualVariableExpression, PresuppositionDRS, DRS, DrtTokens, DrtApplicationExpression, DefiniteDescriptionDRS, DrtConstantExpression, DrtFeatureConstantExpression
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

def main():
    from util import Tester
    tester = Tester('file:../data/grammar.fcfg', DrtParser)
    #drs = tester.parse( "a boy kissed a girl. She bit he.")
    drs = tester.parse( "His car did walk. John did walk.", utter=True)
    #drs = tester.parse( "Mary does write John s letter of himself.")
    print drs
    #drs.draw()
    readings = drs.readings()
    print readings
    for reading in readings:
        reading.draw()
        
def test():
    from util import Tester
    tester = Tester('file:../data/grammar.fcfg', DrtParser)
    expr = tester.parse('Mary owned a blue car. it has died.', utter=True)
    print expr
    expr.draw()
    
    for reading in expr.readings():
        print reading
        reading.draw()

if __name__ == '__main__':
    #main()
    test()