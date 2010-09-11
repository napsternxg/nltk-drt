import temporaldrt
import nltk.sem.drt as drt
from temporaldrt import PresuppositionDRS, DRS, DrtTokens, DrtApplicationExpression

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

    def handle_DRS(self, tok, context):
        drs = drt.DrtParser.handle_DRS(self, tok, context)
        return DRS(drs.refs, drs.conds)

class ProperNameDRS(PresuppositionDRS):
    
    def _readings(self, trail=[]):
        """A proper name always yields one reading: it is either global binding 
        or global accommodation (if binding is not possible)"""
        # In DRSs representing sentences like 'John, who owns a dog, feeds it',
        # there will be more than one condition in the presupposition DRS.
        # Find the proper name application expression.
        print "PROPER NAME READINGs"
        proper_name = None
        for cond in self.conds:
            if isinstance(cond, DrtApplicationExpression) and cond.is_propername():
                proper_name = cond
                break
        assert(proper_name is not None)
        print "PROPER NAME", proper_name
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
            if isinstance(cond, DrtApplicationExpression) and cond.is_propername() \
            and cond.function.variable.name == proper_name.function.variable.name:
                antecedent_ref = cond.argument
                break
        if antecedent_ref:
            def outer_binding(drs):
                """Put all conditions from the presupposition DRS
                (except the proper name itself) into the outer DRS, 
                and replace the proper name referent in them with antecedent_ref"""
                print "called outer binding"
                newdrs = self.replace(proper_name.argument.variable, antecedent_ref, True)
                # There will be referents and conditions to move 
                # if there is a relative clause modifying the proper name
                drs.refs.extend([ref for ref in newdrs.refs \
                                 if ref != antecedent_ref.variable])
                drs.conds.extend([cond for cond in newdrs.conds \
                                  if cond.function.variable.name != proper_name.function.variable.name])
                
            def inner(drs):
                """In the conditions of the local DRS, replace the 
                referent of the proper name with antecedent_ref"""
                print "called inner"
                if local_drs is outer_drs: outer_binding(drs)
                newdrs = drs.replace(proper_name.argument.variable, antecedent_ref, True)
                drs.refs = newdrs.refs
                drs.conds = newdrs.conds
                drs.conds.remove(self)
            # Return the reading
            if local_drs is outer_drs:
                return [[(local_drs, inner)]]
            return [[(outer_drs, outer_binding),
                     (local_drs, inner)]]
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
        if local_drs is outer_drs:
            return [[(local_drs, inner_remove)]]
        return [[(outer_drs, outer_accommodation),
                 (local_drs, inner_remove)]]

class DefiniteDescriptionDRS(PresuppositionDRS):
    def readings(self, trail=[]):
        pass

class PronounDRS(PresuppositionDRS):
    """A superclass for DRSs for personal, reflexive, 
    and possessive pronouns"""
    def readings(self, trail=[]):
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
    for cond in a.conds: print "TYPE", type(cond), cond
    a.draw()
    for reading in tree.readings(): reading.draw()
    
def test_3(parser):
    trees = parser.nbest_parse('John walks'.split())
    first = trees[0].node['SEM'].simplify().readings()[0]
    trees = parser.nbest_parse('Every girl marries John'.split())
    second = (first + trees[0].node['SEM']).simplify().readings()[0]
    print second, second.__class__
    second.draw()

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
                 'A boy s father marries his girl', 'his girl'
                 ]
    sentences_2 = [['John walks', 'Every girl marries John'], "John marries Mia"]
    
    #for sentence in sentences[-1:]: test(sentence, parser, draworig = True, drawdrs = True)
    #for sentence in sentences_2[:-1]: test_2(sentence, parser)
    test_3(parser)