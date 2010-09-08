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
import nltk.sem.drt as drt

from operator import __and__ as AND
def isListOfTuples(x):
    """From http://effbot.org/zone/python-list.htm, list of lists."""
    if not isinstance(x, list): return False
    return reduce(AND, map(lambda z: isinstance(z, tuple), x))


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
        self.readings = list(drt.__deepcopy__()) # Start with one reading
        # Next, resolve the DRT and keep the multiple readings.
        self.collect_readings()
    
    def __iter__(self):
        "Iterator over the readings"
        for r in self.readings: yield r
        
    def get_readings(self):
        return self.readings
    
    def collect_readings(self):
        "This method does the whole job of collecting multiple readings."
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
            # returns a list of tuples (DRS, operation). Otherwise
            # it will return a DRS.
            r = drs.readings()
            if isListOfTuples(r):
                old_readings.append(drs)
                new_readings += self.get_drs_deepcopies(drs, operations=r)
        # If there has been no new readings, we are done.
        if not new_readings: return
        # Else, remove the old readings, add the new ones 
        # and call this method again.
        for oldr in old_readings: self.readings.remove(oldr)
        self.readings += new_readings
        self.collect_readings()
        
    def get_drs_deepcopies(self, drs, operations):
        """Return a list of DRSs that are new readings to replace the older
        one (the argument drs).
        @param drs: a C{DRS} object (the outermost DRS)
        @param operations: C{list} of tuples (DRS, function)
        The argument DRS gets copied as many times as there are tuples on 
        the operations list, and for each copy, one of the operations is performed."""
        for o in operations:
            # Get a deep copy of the drs with one substitution
            drs.deepcopy(operation=o)
        
                    
class DRS(temporaldrt.DRS):
    
    def __deepcopy__(self):
        """A deep copy constructs a new compound object and then, 
        recursively, inserts copies into it of the objects found 
        in the original."""
        return self.deepcopy(operation=None)[0]
    
    def deepcopy(self, operation=None):
        """This method returns a deep copy of the DRS.
        Optionally, it can take a tuple (DRS, function) 
        as an argument and generate a reading by performing 
        a substitution in the DRS as specified by the function.
        @param operation: a tuple (DRS, function), 
        where the DRS is an argument to pass to that function.
        """
        function = None
        if operation and self == operation[0]:
            function = operation[1]
            operation = None
        new_drs = self.__class__(list(self.refs), \
                                 [cond.deepcopy(operation) for cond in self.conds])
        if function:
            return function(new_drs)
        else:
            return new_drs

class AbstractVariableExpression(logic.AbstractVariableExpression):
    def deepcopy(self):
        variable = self.variable
        return self.__class__(variable=variable)

class HasTerm():
    """An abstract class for DrtNegatedExpression and DrtLambdaExpression"""
    def deepcopy(self):
        term = self.term
        return self.__class__(term=term.deepcopy())

class HasFirstAndSecond():
    """An abstract class for DrtBooleanExpression (and its subclasses DrtOrExpression, 
    DrtImpExpression, DrtIffExpression, ConcatenationDRS) and DrtEqualityExpression"""
    def deepcopy(self):
        first = self.first
        second = self.second
        return self.__class__(first=first.deepcopy(), second=second.deepcopy())
    
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