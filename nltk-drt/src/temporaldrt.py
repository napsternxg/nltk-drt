"""
Temporal logic extension of nltk.sem.drt
Keeps track of time referents and temporal DRS-conditions. 

New function resolving LOCPRO(t) from a non-finite verb
to the location time referent introduced by a finite auxiliary. 
"""

__author__ = "Peter Makarov"
__version__ = "1.0"
__date__ = "Tue, 24 Aug 2010"

import presuppdrt as drt
from nltk.sem.logic import Variable
from presuppdrt import DrsDrawer
from presuppdrt import ReverseIterator
from presuppdrt import AnaphoraResolutionException
from presuppdrt import DrtApplicationExpression
from presuppdrt import DrtTimeVariableExpression
from presuppdrt import DRS
from presuppdrt import DrtVariableExpression
from presuppdrt import DrtStateVariableExpression
from presuppdrt import Reading 
from presuppdrt import DrtEventVariableExpression
from presuppdrt import VariableReplacer
from presuppdrt import ConditionReplacer
from presuppdrt import ConditionRemover
from presuppdrt import DrtEqualityExpression
from presuppdrt import DrtConstantExpression
from presuppdrt import unique_variable
from presuppdrt import DrtNegatedExpression
from presuppdrt import is_statevar
from presuppdrt import is_eventvar
from presuppdrt import is_timevar
from presuppdrt import is_uttervar
from presuppdrt import DrtAbstractVariableExpression
from presuppdrt import DrtUtterVariableExpression
from presuppdrt import DrtIndividualVariableExpression
from presuppdrt import DefiniteDescriptionDRS
from presuppdrt import DrtEventualityApplicationExpression
from presuppdrt import DrtLambdaExpression
from presuppdrt import DrtBooleanExpression
from presuppdrt import ConcatenationDRS
from presuppdrt import DrtImpExpression
from presuppdrt import DrtOrExpression
from presuppdrt import DrtFeatureConstantExpression

class DrtTokens(drt.DrtTokens):
    NEWINFO_DRS = 'NEWINFO'

    LOCATION_TIME = 'LOCPRO'
    UTTER_TIME = 'UTTER'
    REFER_TIME = 'REFER'
    PERF = 'PERF'
    UTTER = "UTTER"
    REFER = "REFER"
    OVERLAP = "overlap"
    EARLIER = "earlier"
    INCLUDE = "include"
    ABUT = "abut"
    END = "end"
    TEMP_CONDS = [OVERLAP, EARLIER, INCLUDE]
    
    PAST = "PAST"
    PRES = "PRES"
    FUT = "FUT"
    
    TENSE = [PAST, PRES, FUT]

class DrtTimeApplicationExpression(DrtApplicationExpression):
    """Type of DRS-conditions used in temporal logic"""
    pass

class LocationTimeResolutionException(Exception):
    pass

class DrtLocationTimeApplicationExpression(DrtTimeApplicationExpression):
    def readings(self, trail=[]):
        utter_time_search = False

        for drs in (ancestor for ancestor in ReverseIterator(trail) if isinstance(ancestor, DRS)):
            search_list = drs.refs
            
            if self.argument.variable in drs.refs:
                search_list = drs.refs[:drs.refs.index(self.argument.variable)]
            
            for ref in ReverseIterator(search_list):
                refex = DrtVariableExpression(ref)
                
                if isinstance(refex, DrtUtterVariableExpression):
                    """In case there is no location time referent that has not yet been used
                    to relate some eventuality to utterance time, use utter time as loc time."""
                    return [Reading([(trail[-1], VariableReplacer(self.argument.variable, refex))])], True
  
                elif not utter_time_search and isinstance(refex, DrtTimeVariableExpression) and \
                   not (refex == self.argument):
                                      
                    if any(isinstance(c, DrtApplicationExpression) and isinstance(c.function, DrtApplicationExpression) and \
                        c.function.argument == refex and (c.function.function.variable.name == DrtTokens.OVERLAP or \
                        c.function.function.variable.name == DrtTokens.INCLUDE) for c in drs.conds):
                        utter_time_search = True

                    else:
                        """Return first suitable antecedent expression"""
                        return [Reading([(trail[-1], VariableReplacer(self.argument.variable, refex))])], True
                                
        raise LocationTimeResolutionException("Variable '%s' does not "
                            "resolve to anything." % self.argument)

class DrtFindUtterTimeExpression(DrtApplicationExpression):
    """Type of application expression looking to equate its argument with utterance time"""
    def readings(self, trail=[]):
        for ancestor in trail:    
            for ref in ancestor.get_refs():
                refex = DrtVariableExpression(ref)
                if isinstance(refex, DrtUtterVariableExpression):
                    
                    return [Reading([(trail[-1], VariableReplacer(self.argument.variable, refex))])], True                  
        
        raise UtteranceTimeTimeResolutionException("Variable '%s' does not "
                            "resolve to anything." % self.argument)

class UtteranceTimeTimeResolutionException(Exception):
    pass

class DrtFindEventualityExpression(DrtApplicationExpression):
    """Comprises reference point REFER condition and aspectual PERF condition.
    DRS-condition REFER(e) or REFER(s) returns a temporal condition that
    relates given eventuality and some previous event or state. In the simplified
    version of the reference point selection algorithm, the condition picks out the
    most recent event and, depending on the type of its argument, returns either an
    earlier(e*,e) or include(s,e*), where e* is the reference point and e/s is the given
    eventuality. In case there is no event in the previous discourse, the most recent
    state is taken as the reference point and overlap(s*,s) or include(s*,e) is introduced
    depending on the type of the given eventuality.
    PERF(e) locates the most recent state referent s and resolves to a condition abut(e,s).
    PERF(s) locates the most recent state referent s* and resolves to a condition abut(e*,s*),
    e* = end(s) and adds a new event referent e*. Note that end(.) is an operator on states
    that returns events."""
    def readings(self, trail=[]):

        state_reference_point = None
        index = trail[-1].conds.index(self)
        """state reference point in case there are no previous events"""
        for drs in (ancestor for ancestor in ReverseIterator(trail) if isinstance(ancestor, DRS)):                               
            
            search_list = drs.refs
                        
            if drs is trail[-1]:
                """
                Described eventuality in the object's referents?
                Take refs' list up to described eventuality
                """
                search_list = drs.refs[:drs.refs.index(self.argument.variable)]
                
            for ref in ReverseIterator(search_list):
                """search for the most recent reference"""
                refex = DrtVariableExpression(ref)
            
                if isinstance(refex, DrtEventVariableExpression) and \
                not (refex == self.argument) and not self.function.variable.name == DrtTokens.PERF:
                    
                    if isinstance(self.argument, DrtEventVariableExpression):
                        """In case given eventuality is an event, return earlier"""
                        return [Reading([(trail[-1], ConditionReplacer(index,
                        [self._combine(DrtTokens.EARLIER, refex, self.argument)]))])], False               

                    
                    elif isinstance(self.argument, DrtStateVariableExpression):
                        """In case given eventuality is a state, return include"""
                        return [Reading([(trail[-1], ConditionReplacer(index,
                        [self._combine(DrtTokens.INCLUDE, self.argument, refex)]))])], False               
     
                
                elif not state_reference_point and \
                    isinstance(refex, DrtStateVariableExpression) and \
                    not (refex == self.argument):
                    """In case no event is found, locate the most recent state"""
                    state_reference_point = refex                            

        if state_reference_point:

            if self.function.variable.name == DrtTokens.PERF:
                """in case we are dealing with PERF"""
                if isinstance(self.argument, DrtEventVariableExpression):
                    """
                    Reference point is a state and described eventuality an event,
                    return event abuts on state
                    """
                    return [Reading([(trail[-1], ConditionReplacer(index,
                    [self._combine(DrtTokens.ABUT, self.argument, state_reference_point)]))])], False                       

                    
                elif isinstance(self.argument, DrtStateVariableExpression):
                    """Reference point is a state and described eventuality a state,
                    then add an event referent to the ancestor's refs list and two conditions
                    that that event is the end of eventuality (function needed!!!) and
                    that event abuts on ref.state"""
                    termination_point = unique_variable(Variable("e"))
                    conds = [DrtEqualityExpression(DrtEventVariableExpression(termination_point), DrtApplicationExpression(self.make_ConstantExpression(DrtTokens.END), self.argument)),
                    self._combine(DrtTokens.ABUT, DrtEventVariableExpression(termination_point), state_reference_point)]
                    return [Reading([(trail[-1], DrtFindEventualityExpression.ConditionReplacer(index, conds, termination_point))])], False
                    
                
            elif isinstance(self.argument, DrtStateVariableExpression):
                """Reference point is a state and given eventuality is also a state,
                return overlap"""
 
                return [Reading([(trail[-1], ConditionReplacer(index,
                [self._combine(DrtTokens.OVERLAP, state_reference_point, self.argument)]))])], False               
        
            elif isinstance(self.argument, DrtEventVariableExpression):
                """Reference point is a state and given eventuality is an event,
                return include"""
                return [Reading([(trail[-1], ConditionReplacer(index,
                [self._combine(DrtTokens.INCLUDE, state_reference_point, self.argument)]))])], False               
                
        else:
            """no suitable reference found"""
            return [Reading([(trail[-1], ConditionRemover(index))])], False

    def make_ConstantExpression(self, name):
        return DrtConstantExpression(Variable(name))
    
    def _combine(self, cond, arg1, arg2):
        """Combines two arguments into a DrtEventualityApplicationExpression
        that has another DrtEventualityApplicationExpression as its functor"""
        return DrtEventualityApplicationExpression(DrtEventualityApplicationExpression(self.make_ConstantExpression(cond), arg1), arg2)

class NewInfoDRS(DRS):
    pass

class PresuppositionDRS(drt.PresuppositionDRS):

    def collect_event_data(self, cond, event_data_map, event_strings_map, individuals=None):
        if isinstance(cond.function, DrtApplicationExpression) and not isinstance(cond.function, DrtTimeApplicationExpression) and \
        isinstance(cond.argument, DrtIndividualVariableExpression) and not isinstance(cond.argument, DrtTimeVariableExpression):
                event_data_map.setdefault(cond.argument.variable,[]).append((cond.function.argument, cond.function.function.variable.name))
        elif cond.__class__ == DrtEventualityApplicationExpression and \
        (isinstance(cond.argument, DrtEventVariableExpression) or isinstance(cond.argument, DrtStateVariableExpression)) and\
        not isinstance(cond.function, DrtApplicationExpression):
            assert cond.argument not in event_strings_map
            event_strings_map[cond.argument] = cond.function.variable.name
        # The rest are nouns and attributive adjectives
        elif individuals is not None and cond.__class__ == DrtApplicationExpression and \
        not isinstance(cond.function, DrtApplicationExpression):
            individuals.setdefault(cond.argument.variable,[]).append(cond)

class DefiniteDescriptionDRS(drt.DefiniteDescriptionDRS):

    def _get_free(self):
        free =  self.free(True)
        temporal_conditions = []
        # If there are free variables that stem from conditions like 'overlap', earlier', 'include',
        # those conditions will be moved to the local drs
        for cond in self.conds:
            
            if isinstance(cond, DrtTimeApplicationExpression) and isinstance(cond.function, DrtTimeApplicationExpression):
                assert cond.function.function.variable.name in DrtTokens.TEMP_CONDS
                for expression in [cond.argument, cond.function.argument]:
                    expression_variable = expression.variable
                    if expression_variable in free and isinstance(expression, DrtUtterVariableExpression):
                        free.remove(expression_variable)

            if isinstance(cond, DrtEventualityApplicationExpression) and \
               isinstance(cond.function, DrtEventualityApplicationExpression):
                assert cond.function.function.variable.name in DrtTokens.TEMP_CONDS
                for expression_variable in [cond.argument.variable, cond.function.argument.variable]:
                    if expression_variable in free:
                        free.remove(expression_variable)
                temporal_conditions.append(cond)
                self.conds.remove(cond)
        return free, temporal_conditions

class DrtParser(drt.DrtParser):
    """DrtParser producing conditions and referents for temporal logic"""
        
    def handle(self, tok, context):
        """We add new types of DRS to represent presuppositions"""
        if tok == DrtTokens.NEWINFO_DRS:
            return self.handle_NewInfoDRS(tok, context)
        else:
            return drt.DrtParser.handle(self, tok, context)

    def handle_PresuppositionDRS(self, tok, context):
        """Parse all the Presuppositon DRSs."""
        if tok == DrtTokens.DEFINITE_DESCRIPTION_DRS:
            self.assertNextToken(DrtTokens.OPEN)
            drs = self.handle_DRS(tok, context)
            return DefiniteDescriptionDRS(drs.refs, drs.conds)
        else:
            return drt.DrtParser.handle_PresuppositionDRS(self, tok, context)
        
    def handle_NewInfoDRS(self, tok, context):
        """DRS for linking previous discourse with new discourse"""
        self.assertNextToken(DrtTokens.OPEN)
        drs = self.handle_DRS(tok, context)
        return NewInfoDRS(drs.refs, drs.conds)

    def handle_DRS(self, tok, context):
        drs = drt.DrtParser.handle_DRS(self, tok, context)
        location_time = None
        
        for cond in drs.conds:
            if isinstance(cond, DrtFindEventualityExpression):
                """PERF(.) gives rise to a DrtFindEventualityExpression;
                in case it is among the DRS-conditions, the eventuality carried by
                this DRS does not give rise to a REFER(.) condition"""
                return DRS(drs.refs, drs.conds)
           
            if not location_time and isinstance(cond, DrtLocationTimeApplicationExpression):
                location_time = cond.argument
        
        for ref in drs.refs:
            """Change DRS: introduce REFER(s/e) condition, add INCLUDE/OVERLAP
            conditions to verbs (triggered by LOCPRO) and given some trigger
            from DrtTokens.TENSE put UTTER(.) condition and,for PAST and FUT,
            earlier(.,.) condition w.r.t. to some new discourse
            referent bound to utterance time."""
        
            if is_statevar(ref.name):
                """Adds REFER(s) condition."""
                if location_time:
                    """Relates location time and eventuality"""
                    drs.conds.append(DrtTimeApplicationExpression(DrtTimeApplicationExpression(self.make_ConstantExpression(DrtTokens.OVERLAP), location_time), DrtStateVariableExpression(ref)))
                drs.conds.append(DrtFindEventualityExpression(self.make_ConstantExpression(DrtTokens.REFER), DrtVariableExpression(ref)))
                
            if is_eventvar(ref.name):
                """Adds REFER(e) condition."""
                if location_time:
                    """Relates location time and eventuality"""
                    drs.conds.append(DrtTimeApplicationExpression(DrtTimeApplicationExpression(self.make_ConstantExpression(DrtTokens.INCLUDE), location_time), DrtStateVariableExpression(ref)))
                drs.conds.append(DrtFindEventualityExpression(self.make_ConstantExpression(DrtTokens.REFER), DrtVariableExpression(ref)))
            
            if is_timevar(ref.name) and not is_uttervar(ref.name):
                """Relates location time with utterance time"""

                tense_cond = [c for c in drs.conds if isinstance(c, DrtApplicationExpression) and \
                               isinstance(c.function, DrtConstantExpression) and \
                               c.function.variable.name in DrtTokens.TENSE and DrtVariableExpression(ref) == c.argument]
                if not tense_cond == []:
                    if tense_cond[0].function.variable.name == DrtTokens.PRES:
                        """Put UTTER(t) instead"""
                        #drs.conds.remove(drs.conds.index(tense_cond[0]))
                        drs.conds[drs.conds.index(tense_cond[0])] = DrtFindUtterTimeExpression(self.make_ConstantExpression(DrtTokens.UTTER), DrtTimeVariableExpression(ref))
                        
                    else:
                        """Put new discourse referent and bind it to utterance time
                        by UTTER(.) and also add earlier(.,.) condition"""
                        utter_time = unique_variable(ref)
                        drs.refs.insert(0, utter_time)
                        drs.conds[drs.conds.index(tense_cond[0])] = DrtFindUtterTimeExpression(self.make_ConstantExpression(DrtTokens.UTTER), DrtTimeVariableExpression(utter_time))

                        if tense_cond[0].function.variable.name == DrtTokens.PAST:
                            drs.conds.append(DrtTimeApplicationExpression(DrtTimeApplicationExpression(self.make_ConstantExpression(DrtTokens.EARLIER), DrtTimeVariableExpression(ref)), DrtTimeVariableExpression(utter_time)))
                        
                        else:
                            drs.conds.append(DrtTimeApplicationExpression(DrtTimeApplicationExpression(self.make_ConstantExpression(DrtTokens.EARLIER), DrtTimeVariableExpression(utter_time)), DrtTimeVariableExpression(ref)))       
        
        return DRS(drs.refs, drs.conds)
  
    def make_VariableExpression(self, name):
        return DrtVariableExpression(Variable(name))

    def make_ApplicationExpression(self, function, argument):
        """If statement added returning DrtTimeApplicationExpression"""
        """ Is self of the form "LOCPRO(t)"? """
        if isinstance(function, DrtAbstractVariableExpression) and \
           function.variable.name == DrtTokens.LOCATION_TIME and \
           isinstance(argument, DrtTimeVariableExpression):
            return DrtLocationTimeApplicationExpression(function, argument)
        
        elif isinstance(function, DrtAbstractVariableExpression) and \
            function.variable.name == DrtTokens.PERF:
            return DrtFindEventualityExpression(function, argument)
        
        elif isinstance(argument, DrtStateVariableExpression) or \
            isinstance(argument, DrtEventVariableExpression):
            return DrtEventualityApplicationExpression(function, argument)
        
        elif isinstance(argument, DrtTimeVariableExpression):
            return DrtTimeApplicationExpression(function, argument)
        else:
            return DrtApplicationExpression(function, argument)
