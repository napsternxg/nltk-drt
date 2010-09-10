import temporaldrt
import nltk.sem.drt as drt
import deepcopy_readings
from deepcopy_readings import Readings
from temporaldrt import DrtProperNameApplicationExpression, PresuppositionDRS, DRS

# Nltk fix
import nltkfixtemporal
from nltk.sem.drt import AbstractDrs
def gr(s, recursive=False):
    return []
AbstractDrs.get_refs = gr
                        
class DrtTokens(temporaldrt.DrtTokens):
    PROPER_NAME_DRS = 'PROPERNAME'
    DEFINITE_DESCRIPTION_DRS = 'DEFDESCR'
    # And pronouns:
    PERSONAL_PRONOUN_DRS = 'PERSPRON'
    POSSESSIVE_PRONOUN_DRS = 'POSSPRON'
    REFLEXIVE_PRONOUN_DRS = 'REFLPRON'
    PRESUPPOSITION_DRS = [PROPER_NAME_DRS, DEFINITE_DESCRIPTION_DRS,
                          PERSONAL_PRONOUN_DRS, POSSESSIVE_PRONOUN_DRS,
                          REFLEXIVE_PRONOUN_DRS]

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
        drs = self.handle_DRS(tok, context)
        if tok == DrtTokens.PROPER_NAME_DRS:
            return ProperNameDRS(drs.refs, drs.conds)
        elif tok == DrtTokens.DEFINITE_DESCRIPTION_DRS:
            return DefiniteDescriptionDRS(drs.refs, drs.conds)
        elif tok == DrtTokens.PERSONAL_PRONOUN_DRS:
            return PersonalPronounDRS(drs.refs, drs.conds)
        elif tok == DrtTokens.POSSESSIVE_PRONOUN_DRS:
            return PossessivePronounDRS(drs.refs, drs.conds)
        elif tok == DrtTokens.REFLEXIVE_PRONOUN_DRS:
            return ReflexivePronounDRS(drs.refs, drs.conds)

    def handle_DRS(self, tok, context):
        drs = drt.DrtParser.handle_DRS(self, tok, context)
        return DRS(drs.refs, drs.conds)

class ProperNameDRS(PresuppositionDRS):
    def __init__(self, refs, conds):
        print "Proper name", refs, conds
        super(ProperNameDRS, self).__init__(refs, conds)
    def readings(self, trail=[]):
        """A proper name always yields one reading: it is either global binding 
        or global accommodation (if binding is not possible)"""
        # In DRSs representing sentences like 'John, who owns a dog, feeds it',
        # there will be more than one condition in the presupposition DRS.
        # Find the proper name application expression.
        print "PROPER NAME READINGs"
        proper_name = None
        for cond in self.conds:
            if isinstance(cond, DrtProperNameApplicationExpression):
                proper_name = cond
                break
        assert(proper_name is not None)
        drss = temporaldrt.get_drss(trail)
        ########
        # Try binding in the outer DRS
        ########
        antecedent_ref = None
        outer_drs = drss['global']
        local_drs = drss.get('local', outer_drs)
        for cond in outer_drs.conds:
            # Binding is only possible if there is a condition with the 
            # same functor (proper name) at the global level
            if isinstance(cond, DrtProperNameApplicationExpression) and \
            cond.function.variable.name == proper_name.function.variable.name:
                antecedent_ref = cond.argument
                break
        if antecedent_ref:
            # 1) Put all conditions (except the proper name itself)
            # into the outer DRS, and replace the proper name referent in them with
            # antecedent_ref.
            # 2) In the conditions of the local DRS, replace the 
            # referent of the proper name with antecedent_ref.
            def outer_binding(drs):
                """Put all conditions from the presupposition DRS
                (except the proper name itself) into the outer DRS, 
                and replace the proper name referent in them with antecedent_ref"""
                self.replace(proper_name.argument.variable, antecedent_ref, True)
                drs.conds.extend([cond for cond in self.conds if cond is not proper_name])
            def inner(drs):
                """In the conditions of the local DRS, replace the 
                referent of the proper name with antecedent_ref"""
                if local_drs is outer_drs: outer_binding(drs)
                drs.replace(proper_name.argument.variable, antecedent_ref, True)
                drs.conds.remove(self)
            # Return the reading
            return [{outer_drs: outer_binding,
                     local_drs: inner}]
        # If no suitable antecedent has been found in the outer DRS,
        # binding is not possible, so we go for accommodation instead.
        def outer_accommodation(drs):
            """Accommodation: put all referents and conditions from 
            the presupposition DRS into the outer DRS"""
            print "outer_accommodation"
            drs.refs.extend(self.refs) 
            drs.conds.extend(self.conds)
        def inner_remove(drs):
            if local_drs is outer_drs: outer_accommodation(drs)
            drs.conds.remove(self)
        return [{outer_drs: outer_accommodation,
                 local_drs: inner_remove}]

class DefiniteDescriptionDRS(PresuppositionDRS):
    def readings(self, trail=[]):
        pass

class PronounDRS(PresuppositionDRS):
    """A superclass for DRSs for personal, reflexive, 
    and possessive pronouns"""
    def readings(self, trail=[]):
        pass

class PersonalPronounDRS(PronounDRS):
    pass

class PossessivePronounDRS(PronounDRS):
    pass

class ReflexivePronounDRS(PronounDRS):
    pass

#################################
## Demo
#################################
def test (sentence, parser, draworig=True, drawdrs=True):
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

def test_2(sentence, parser):
    print '==========================', sentence , '=========================='
    if isinstance(sentence, list):
        tree = parser.nbest_parse(sentence.pop(0).split())[0].node['SEM']
        while sentence:
            sent = sentence.pop(0)
            tree_new = parser.nbest_parse(sent.split())[0].node['SEM']
            tree = tree + tree_new
    else: 
        tree = parser.nbest_parse(sentence.split())[0].node['SEM']
    a = tree.simplify()
    a.draw()
    for reading in Readings(tree): reading.draw()
    
if __name__ == '__main__':
    
    from nltk import load_parser
    #parser = load_parser('file:../data/emmastest.fcfg', logic_parser=OldParser())
    parser = load_parser('file:../data/emmastest.fcfg', logic_parser=DrtParser())
    #parser = load_parser('file:../data/tenseaspect.fcfg', logic_parser=DrtParser())

    sentences = ['The boy marries a girl',
                 'A boy marries the girl',
                 'The boy marries the girl',
                 'Every boy marries the girl',
                 ['A boy marries a girl', 'He walks'], # no presuppositions here
                 'The boy s father marries his girl',
                 ['John marries his girl', 'He walks'],
                 'The boy walks',
                 ['A boy marries the girl', 'He walks'],
                 'A boy s father marries his girl',
                 ]
    sentences_2 = ['John walks', 'Every girl marries John']
    #for sentence in sentences[2:3]: test(sentence, parser, draworig = True, drawdrs = True)
    for sentence in sentences_2[:]: test_2(sentence, parser)
