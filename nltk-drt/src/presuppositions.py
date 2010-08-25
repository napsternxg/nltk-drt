import temporaldrt
from temporaldrt import DrtAbstractVariableExpression, \
                        DrtIndividualVariableExpression, DrtApplicationExpression, \
                        DRS, DrtConstantExpression, DrtEqualityExpression, Variable
                        
class DrtTokens(temporaldrt.DrtTokens):
    PRESUPPOSITION = 'PRESUPP'
    PRESUPP_ACCOMODATION = 'ACCOMOD'

class DrtParser(temporaldrt.DrtParser):
    def make_ApplicationExpression(self, function, argument):
        if isinstance(function, DrtAbstractVariableExpression) and \
                function.variable.name == DrtTokens.PRESUPPOSITION and \
                isinstance(argument, DrtIndividualVariableExpression):
                    return DrtPresuppositionApplicationExpression(function, argument)
        else:
            super(DrtParser, self).make_ApplicationExpression(function, argument)

class DrtPresuppositionApplicationExpression(DrtApplicationExpression):
    
    def resolve(self, trail=[], output=[]):
        # We have three possible types of accomodation :
        # local (in this very DRS), intermediate (in the preceeding DRS),
        # and global (in the outermost DRS)
        
        # First, get the inner DRS and ,if possible (if they are not the same DRS), 
        # the preceeding DRS and the outer DRS
        inner_drs = None # local accomodation
        preceeding_drs = None # intermediate accomodation
        outermost_drs = None # global accomodation
        while trail:
            ancestor = trail.pop()
            if isinstance(ancestor, DRS):
                if not inner_drs: inner_drs = ancestor
                elif not preceeding_drs:
                    preceeding_drs = ancestor
                    break
        while trail:
            ancestor = trail.pop(0)
            if isinstance(ancestor, DRS):
                outermost_drs = ancestor
                break
        
        # Now go through the conditions of the inner DRS and take out all 
        # conditions pertaining to the presupposition
        presupp_referents = [] # Probably this list will never have more than one element.
        presupp_conditions = [] # All the presupposition conditions will be removed 
        for cond in inner_drs.conds:
            if not isinstance(cond, DrtApplicationExpression): # for example, DrtEqualityExpression
                continue
            if self == cond.function:
                presupp_referents.append(cond.argument)
                presupp_conditions.append(cond)
            elif cond.argument in presupp_referents:
                presupp_conditions.append(cond)
        
        for prcon in presupp_conditions:            
            if self == prcon.function:
                # Add a DrtEqualityExpression to the inner DRS
                inner_drs.conds.append(DrtEqualityExpression(self.argument, prcon.argument))
                inner_drs.conds.remove(prcon)
                # If possible, add a DrtPossiblePresuppAccomodationExpression 
                # to each of the 3 DRS's (inner, preceeding, outermost)
                accomodation = DrtPossiblePresuppAccomodationExpression(DrtConstantExpression(Variable(DrtTokens.PRESUPP_ACCOMODATION)), prcon.argument)
                inner_drs.conds.append(accomodation)
                if preceeding_drs: preceeding_drs.conds.append(accomodation)
                if outermost_drs: outermost_drs.conds.append(accomodation)
            else:
                # If possible, put the prcon condition into each of the 3 DRS's 
                # (inner [it is already there], preceeding, outermost)
                if preceeding_drs: preceeding_drs.conds.append(prcon)
                if outermost_drs: outermost_drs.conds.append(prcon)
        return self

    def get_variable(self):
        return self.argument.variable
    
class DrtPossiblePresuppAccomodationExpression(DrtApplicationExpression):
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
    if draworig: tree.draw()
    print '========================== Tree node SEM, simplified'
    a = tree.simplify()
    print a
    print "========================== The same SEM, resolved"
    a.resolve()
    print a
    print "\n\n"
    if drawdrs: a.draw()
    
if __name__ == '__main__':
    
    from nltk import load_parser

    parser = load_parser('file:../data/emmastest.fcfg', logic_parser=DrtParser())
    #parser = load_parser('file:../data/tenseaspect.fcfg', logic_parser=DrtParser())



    sentences = ['The boy marries a girl', # works, but! see 'The boy marries the girl'
                 'A boy marries the girl', # works, but! see 'The boy marries the girl'
                 'The boy marries the girl', # This doesn't work.
                            # It introduces z for both the boy and the girl. 
                            # It should rename the variable at some point before resolve() is called.
                            # It seems that rename() gets called, but it doesn't handle free variables. Check this.
                 'Every boy marries the girl', # This seems to work.
                            # It has all three types of accomodations: local, intermediate, global.
                            # It has all three types of accomodations: local, intermediate, global.
                 ['A boy marries a girl','He walks'] # no presupposition here
                 ]
    
    for sentence in sentences[:]: test(sentence, parser, draworig = True, drawdrs = True)