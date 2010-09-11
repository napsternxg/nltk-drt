# TODO: Implement readings() for Presuppositional DRS (i.e. if I am a 
# Presuppositional DRS, I go through my conditions looking for an 
# embedded Presuppositional DRS. If I find one, I can't be resolved 
# yet. I go into that embedded DRS). 

# TODO: I am a DRS (presuppositional or normal). When I get a list of tuples
# from some embedded DRS, I stop resolution and return the list of tuples to the
# DRS above me. The outermost DRS eventually returns it. Also, check whether the 
# DRS below me wants to be deleted (returns a list of tuples and 'deleteme'=True). 
# Delete it if yes. 

# TODO: Implement readings() for each of the subclasses of 
# Presuppositional DRS
 
# TODO: Implement deepcopy for referents and conditions, not just DRSs.

# TODO: Test it.

# TODO: A DRS thinks the referents of its embedded Presuppositional DRSs
# are its referents

import temporaldrt
import nltk.sem.logic as logic
from temporaldrt import DrtVariableExpression, unique_variable

import operator

class Readings:
    """
    When we want to resolve a whole-discourse (i.e. outermost) DRS, 
    we wrap it in a Readings object first, e.g.:
    #
    readings = Readings(myDrs) # we don't call resolve() explicitly
    for r in readings: print r; r.draw()
    #
    This object takes care of multiple readings. 
    """
    def __init__(self, drt):
        self.readings = [drt] # Start with one reading
        # Next, resolve the DRT and keep the multiple readings.
        self.collect_readings()
    
    def __iter__(self):
        "Iterator over the readings"
        for r in self.readings: yield r
        
    def get_readings(self):
        return self.readings
    
    def collect_readings(self):
        "This method does the whole job of collecting multiple readings."
        print "COLLECT READINGS"
        new_readings = []
        old_readings = []
        """We aim to get new readings from the old ones by resolving
        presuppositional DRSs one by one. Every time one presupposition
        is resolved, new readings are created and replace the old ones,
        until there are no presuppositions left to resolve.
        """
        # Go through the list of readings we already have
        for drs in self.readings:
            # If a presupposition resolution took place, readings() 
            # returns a dictionary (DRS, operation). Otherwise
            # it will return a None.
            r = drs.readings()
            if not r: return
            if isinstance(r, list):
                old_readings.append(drs)
                print 'new_readings', new_readings
                new_readings += self.get_drs_deepcopies(drs, operations=r)
        # If there has been no new readings, we are done.
        if not new_readings: return
        # Else, remove the old readings, add the new ones 
        # and call this method again.
        for oldr in old_readings: self.readings.remove(oldr)
        self.readings += new_readings
        print "self readings in collect r", self.readings
        self.collect_readings()
        
    def get_drs_deepcopies(self, drs, operations):
        """Return a list of DRSs that are new readings to replace the older
        one (the argument drs).
        @param drs: a C{DRS} object (the outermost DRS)
        @param operations: C{dict} of the form DRS function
        The argument DRS gets copied as many times as there are tuples on 
        the operations list, and for each copy, one of the operations is performed."""
        new_readings = []
        for o in operations:
            # Get a deep copy of the drs with substitutions for one reading
            new_readings.append(drs.deepcopy(operations=o))
        return new_readings

class AbstractVariableExpression(logic.AbstractVariableExpression):
    def deepcopy(self):
        return self.__class__(self.variable)
    
"""
Maybe here we have to show that such classes as DrtFunctionExpression, etc. are subclasses
of AbstractVariableExpression. From temporaldrt:
class DrtIndividualVariableExpression(DrtAbstractVariableExpression, drt.DrtIndividualVariableExpression):
    pass

class DrtFunctionVariableExpression(DrtAbstractVariableExpression, drt.DrtFunctionVariableExpression):
    pass

class DrtEventVariableExpression(DrtIndividualVariableExpression, drt.DrtEventVariableExpression):
    pass

class DrtConstantExpression(DrtAbstractVariableExpression, drt.DrtConstantExpression):
    pass
"""

class HasTerm():
    """An abstract class for DrtNegatedExpression and DrtLambdaExpression"""
    def deepcopy(self):
        return self.__class__(self.term.deepcopy())

class HasFirstAndSecond():
    """An abstract class for DrtBooleanExpression (and its subclasses DrtOrExpression, 
    DrtImpExpression, DrtIffExpression, ConcatenationDRS) and DrtEqualityExpression"""
    def deepcopy(self):
        return self.__class__(self.first.deepcopy(), self.second.deepcopy())
    
class DrtNegatedExpression(temporaldrt.DrtNegatedExpression, HasTerm):
    pass

class DrtLambdaExpression(temporaldrt.DrtLambdaExpression, HasTerm):
    pass

class DrtBooleanExpression(temporaldrt.DrtBooleanExpression, HasFirstAndSecond):
    pass

class DrtOrExpression(DrtBooleanExpression, temporaldrt.DrtOrExpression):
    pass

class DrtImpExpression(DrtBooleanExpression, temporaldrt.DrtImpExpression):
    pass

class DrtIffExpression(DrtBooleanExpression, temporaldrt.DrtIffExpression):
    pass

class DrtEqualityExpression(temporaldrt.DrtEqualityExpression, HasFirstAndSecond):
    pass

class ConcatenationDRS(DrtBooleanExpression, temporaldrt.ConcatenationDRS):
    pass

#===================================================================
if __name__ == '__main__':
    pass