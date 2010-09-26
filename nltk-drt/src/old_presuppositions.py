""" !!! The latest working version is presuppositions v.114 + temporaldrt v.114.
In presuppositions v.114, fix the bug in test by replacing tree with a""" 

import temporaldrt
import nltk.sem.drt as drt
from temporaldrt import PresuppositionDRS, DRS, DrtTokens, DrtApplicationExpression, Reading, DrtVariableExpression
import util

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
    
    class OuterBinding(object):
        def __init__(self, presupp_drs, proper_name, antecedent_ref, condition_index):
            self.presupp_drs = presupp_drs
            self.proper_name = proper_name
            self.antecedent_ref = antecedent_ref
            self.condition_index = condition_index
        def __call__(self, drs):
            """Put all conditions from the presupposition DRS
            (except the proper name itself) into the outer DRS, 
            and replace the proper name referent in them with antecedent_ref"""
            newdrs = self.presupp_drs.replace(self.proper_name.argument.variable, self.antecedent_ref, True)
            # There will be referents and conditions to move 
            # if there is a relative clause modifying the proper name
            drs.refs.extend([ref for ref in newdrs.refs \
                             if ref != self.antecedent_ref.variable])
            conds_to_move = [cond for cond in newdrs.conds \
                            if cond.function.variable.name != self.proper_name.function.variable.name]
            # Put the conditions at the position of the original presupposition DRS
            if self.condition_index is None: # it is an index, it can be zero
                drs.conds.extend(conds_to_move)
            else:
                drs.conds = drs.conds[:self.condition_index+1]+conds_to_move+drs.conds[self.condition_index+1:]
            return drs
            
    class InnerReplace(object):
        def __init__(self, presupp_drs, proper_name, antecedent_ref, local_is_outer, condition_index):
            self.presupp_drs = presupp_drs
            self.proper_name = proper_name
            self.antecedent_ref = antecedent_ref
            self.local_is_outer = local_is_outer
            self.condition_index = condition_index
        def __call__(self, drs):
                """In the conditions of the local DRS, replace the 
                referent of the proper name with antecedent_ref"""
                if self.local_is_outer:
                    func = ProperNameDRS.OuterBinding(self.presupp_drs, self.proper_name, self.antecedent_ref, self.condition_index)
                    drs = func(drs)
                return drs.replace(self.proper_name.argument.variable, self.antecedent_ref, True)
    
    class OuterAccommodation(object):
        def __init__(self, presupp_drs, condition_index):
            self.presupp_drs = presupp_drs
            self.condition_index = condition_index
        def __call__(self, drs):
            """Accommodation: put all referents and conditions from 
            the presupposition DRS into the outer DRS"""
            
            #in case variables in the presuppositional DRS carry the same names as
            #variable in the outer DRS.
            presupp_drs = self.presupp_drs
            for ref in self.presupp_drs.refs:
                if ref in drs.refs:
                    newref = DrtVariableExpression(drt.unique_variable(ref))
                    presupp_drs = presupp_drs.replace(ref,newref,True)

            drs.refs.extend(presupp_drs.refs)
             
            if self.condition_index is None:
                drs.conds.extend(presupp_drs.conds)
            else:
                print self.condition_index
                #print "outer accommodation drs.conds before",drs.conds
                drs.conds = drs.conds[:self.condition_index+1]+presupp_drs.conds+drs.conds[self.condition_index+1:]
                #print "outer accommodation drs.conds after",drs.conds
            return drs
        
    def _presupposition_readings(self, trail=[]):
        """A proper name always yields one reading: it is either global binding 
        or global accommodation (if binding is not possible)"""
        # In DRSs representing sentences like 'John, who owns a dog, feeds it',
        # there will be more than one condition in the presupposition DRS.
        # Find the proper name application expression.
        proper_name = None
        for cond in self.conds:
            if isinstance(cond, DrtApplicationExpression) and cond.is_propername():
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
            if isinstance(cond, DrtApplicationExpression) and cond.is_propername() \
            and cond.function.variable.name == proper_name.function.variable.name:
                antecedent_ref = cond.argument
                break
        condition_index = None
        if local_drs is outer_drs:
            condition_index = local_drs.conds.index(self)
        if antecedent_ref:           
            # Return the reading
            if local_drs is outer_drs:
                return [Reading([(local_drs, ProperNameDRS.InnerReplace(self, proper_name, antecedent_ref, (local_drs is outer_drs), condition_index))])], True
            return [Reading([(outer_drs, ProperNameDRS.OuterBinding(self, proper_name, antecedent_ref, condition_index)),
                     (local_drs, ProperNameDRS.InnerReplace(self, proper_name, antecedent_ref, (local_drs is outer_drs), condition_index))])], True
        # If no suitable antecedent has been found in the outer DRS,
        # binding is not possible, so we go for accommodation instead.
        return [Reading([(outer_drs, ProperNameDRS.OuterAccommodation(self, condition_index))])], True
    
class DefiniteDescriptionDRS(PresuppositionDRS):
    def _presupposition_readings(self, trail=[]):
        pass

class PronounDRS(PresuppositionDRS):
    """A superclass for DRSs for personal, reflexive, 
    and possessive pronouns"""
    def _presupposition_readings(self, trail=[]):
        pass

#################################
## Demo, tests
#################################
def presuppositions_test (sentence, parser):
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
    print '========================== Tree node SEM, simplified'
    a = tree.simplify()
    print a
    a.draw()
    for reading in a.readings(): reading.draw()

def proper_names_test_1(sentence, parser):
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
    for reading in a.readings(): reading.draw()
    
def proper_names_test_2(parser):
    trees = parser.nbest_parse('John walks'.split())
    first = trees[0].node['SEM'].simplify().readings()[0]
    trees = parser.nbest_parse('Every girl marries John'.split())
    second = (first + trees[0].node['SEM']).simplify().readings()[0]
    print second, second.__class__
    second.draw()
    
def integration_test():
    tester = util.Tester('file:../data/grammar.fcfg', DrtParser)
    expr = tester.parse('Every girl bit John')
    expr.readings()[0].draw()
    
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
    sentences_2 = [['John walks','John walks'], ['John walks', 'Every girl marries John'], "John marries Mia"]
    
    #for sentence in sentences[:1]: presuppositions_test(sentence, parser)
    for sentence in sentences_2[:-1]: proper_names_test_1(sentence, parser)
    proper_names_test_2(parser)
    integration_test()