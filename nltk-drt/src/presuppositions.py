from nltk.sem.drt import DrtParser as OldParser
import temporaldrt
import nltk.sem.drt as drt
import deepcopy_readings
from deepcopy_readings import PresuppositionDRS, DRS
import nltkfixtemporal
from nltk.sem.drt import AbstractDrs
def gr(s, recursive=False):
    return []

AbstractDrs.get_refs = gr
                        
class DrtTokens(temporaldrt.DrtTokens):
    PROPER_NAME_DRS = 'PROPERNAME'
    PERSONAL_PRONOUN_DRS = 'PERSPRON'
    PRESUPP_OF_EXISTENCE_DRS = 'PRSPEX' # presupposition of existence triggered by the definite article, 
    # the possessiive marker and a possessive pronoun
    POSSESSION_DRS = 'POSSDRS'
    #PRESUPPOSITION_DRS = 'PRESUPP'
    #PRESUPPOSITION_ACCOMODATION = 'ACCOMOD'
    PRESUPPOSITION_DRS = [PROPER_NAME_DRS, PERSONAL_PRONOUN_DRS, PRESUPP_OF_EXISTENCE_DRS, POSSESSION_DRS]

class DrtParser(temporaldrt.DrtParser):

    def handle(self, tok, context):
        """We add new types of DRS to represent presuppositions"""
        if tok.upper() in DrtTokens.PRESUPPOSITION_DRS:
            return self.handle_PRESUPPOSITION_DRS(tok.upper(), context)
        else: return super(DrtParser, self).handle(tok, context)
        
    def handle_PRESUPPOSITION_DRS(self, tok, context):
        """Parse new types of DRS: presuppositon DRSs.
        """
        self.assertNextToken(DrtTokens.OPEN)
        drs = self.handle_DRS(tok,context)
        
        if tok == DrtTokens.PROPER_NAME_DRS:
            return ProperNameDRS(drs.refs, drs.conds)
        elif tok == DrtTokens.PERSONAL_PRONOUN_DRS:
            return PersonalPronounDRS(drs.refs, drs.conds)
        elif tok == DrtTokens.PRESUPP_OF_EXISTENCE_DRS:
            return PresuppOfExistenceDRS(drs.refs, drs.conds)
        elif tok == DrtTokens.POSSESSION_DRS:
            return PossessionDRS(drs.refs, drs.conds)

    def handle_DRS(self, tok, context):
        drs = drt.DrtParser.handle_DRS(self, tok, context)
        return DRS(drs.refs, drs.conds)

class ProperNameDRS(PresuppositionDRS):
    pass

class PersonalPronounDRS(PresuppositionDRS):
    pass

class PresuppOfExistenceDRS(PresuppositionDRS):
    pass

class PossessionDRS(PresuppositionDRS):
    pass

#################################
## Demo
#################################
def test (sentence, parser, draworig = True, drawdrs=True):
    print '==========================', sentence , '=========================='
    if isinstance(sentence, list):
        tree = parser.nbest_parse(sentence.pop(0).split())[0].node['SEM']
        while sentence:
            sent = sentence.pop(0)
            tree_new = parser.nbest_parse(sent.split())[0].node['SEM']
            tree = tree + tree_new
    else: 
        tree = parser.nbest_parse(sentence.split())[0].node['SEM']
    print '========================== Tree node SEM'
    print tree
    #if draworig: tree.draw()
    print '========================== Tree node SEM, simplified'
    a = tree.simplify()
    print a
    #print "========================== The same SEM, resolved"
    #a.resolve()
    #print a
    #print "\n\n"
    if drawdrs: a.draw()
    
if __name__ == '__main__':
    
    from nltk import load_parser
    #parser = load_parser('file:../data/emmastest.fcfg', logic_parser=OldParser())
    parser = load_parser('file:../data/emmastest.fcfg', logic_parser=DrtParser())
    #parser = load_parser('file:../data/tenseaspect.fcfg', logic_parser=DrtParser())

    sentences = ['The boy marries a girl',
                 'A boy marries the girl',
                 'The boy marries the girl',
                 'Every boy marries the girl',
                 ['A boy marries a girl','He walks'], # no presuppositions here
                 'The boy s father marries his girl',
                 ['John marries his girl','He walks'],
                 'The boy walks',
                 ['A boy marries the girl', 'He walks']
                 ]
    p = DrtParser().parse
    #expr = p(r'DRS([x],[smoke(x)])')
    expr = p(r'\x.DRS([],[PRSPEX([x],[boy(x)])walk(x)])(z)')
    expr_1 = p(r'DRS([],[PRSPEX([x],[boy(x)])walk(x)])')
    expr_11 = p(r'DRS([x],[PRSPEX([],[boy(x)])walk(x)])')
    print expr.simplify()
    print expr_1.free()
    print expr_1.get_refs(True)
    print expr_11.free()
    print expr_11.get_refs(True)
    expr_2 = p(r'\x.DRS([x],[DRS([],[boy(x)])walk(x)])(z)')
    print expr.simplify()
    print expr_2.simplify()
    #expr_2 = p('DRS([x],[smoke(x)])')
    #print (expr+expr_2).simplify()
    for sentence in sentences[-1:]: test(sentence, parser, draworig = True, drawdrs = True)