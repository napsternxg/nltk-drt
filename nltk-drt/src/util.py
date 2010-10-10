import nltkfixtemporal

from nltk import load_parser
from nltk.sem.drt import AbstractDrs
from temporaldrt import DRS, DrtApplicationExpression, DrtVariableExpression, unique_variable
from presuppdrt import DrtParser as PresuppDrtParser
from presuppdrt import ResolutionException
import nltk.sem.drt as drt
import temporaldrt
import re
from types import LambdaType

from nltk import LogicParser
from nltk.sem.logic import AndExpression, ParseException
from inference_check import inference_check, get_bk, AdmissibilityOuput, ConsistencyOuput, InformativityOuput


class Tester(object):
    
    INFERROR = {
    3 : AdmissibilityOuput,
    2 : InformativityOuput,
    1 : ConsistencyOuput           
    }
    
    WORD_SPLIT = re.compile(" |, |,")
    EXCLUDED_NEXT = re.compile("^ha[sd]|is|was|not|will$")
    EXCLUDED = re.compile("^does|h?is|red|[a-z]+ness$")
    SUBSTITUTIONS = [
    (re.compile("^died$"), ("did", "die")),
     (re.compile("^([A-Z][a-z]+)'s?$"),   lambda m: (m.group(1), "s")),
     (re.compile("^(?P<stem>[a-z]+)s$"),  lambda m: ("does", m.group("stem"))),
     (re.compile("^([a-z]+(?:[^cvklt]|lk|nt))ed|([a-z]+[cvlkt]e)d$"), lambda m: ("did", m.group(1) if m.group(1) else m.group(2))),
     (re.compile("^([A-Z]?[a-z]+)one$"), lambda m: (m.group(1), "one")),
     (re.compile("^([A-Z]?[a-z]+)thing$"), lambda m: (m.group(1), "thing")),
      (re.compile("^bit$"), ("did", "bite")),
      (re.compile("^bought$"), ("did", "buy")),
      (re.compile("^wrote$"), ("did", "write")),
    ]
    
    def __init__(self, grammar, logic_parser):
        assert isinstance(grammar, str) and grammar.endswith('.fcfg'), \
                            "%s is not a grammar name" % grammar
        self.logic_parser = logic_parser()
        self.parser = load_parser(grammar, logic_parser=self.logic_parser) 

    def _split(self, sentence):
        words = []
        exlude_next = False
        for word in Tester.WORD_SPLIT.split(sentence):
            match = None
            if Tester.EXCLUDED_NEXT.match(word):
                exlude_next = True
                words.append(word)
                continue
            if exlude_next or Tester.EXCLUDED.match(word):
                exlude_next = False
                words.append(word)
                continue
            for pattern, replacement in Tester.SUBSTITUTIONS:
                match = pattern.match(word)
                if match:
                    if isinstance(replacement, LambdaType):
                        words.extend(replacement(match))
                    else:
                        words.extend(replacement)
                    break

            if not match:
                words.append(word)

        return words

    def parse(self, text, **args):
        sentences = text.split('.')
        utter = args.get("utter", True)
        verbose = args.get("verbose", False)
        drs = (utter and self.logic_parser.parse('DRS([n],[])')) or []
        
        for sentence in sentences:
            sentence = sentence.lstrip()
            if sentence:
                words = self._split(sentence)
                if verbose:
                    print words
                trees = self.parser.nbest_parse(words)
                new_drs = trees[0].node['SEM'].simplify()
                if verbose:
                    print(new_drs)
                if drs:
                    drs = (drs + new_drs).simplify()
                else:
                    drs = new_drs
    
        if verbose:
            print drs
        return drs

    def test(self, cases, **args):
        verbose = args.get("verbose", False)
        presupp_parser = PresuppDrtParser()
        for number, sentence, expected in cases:
            expected_drs = []
            if expected:
                for item in expected if isinstance(expected, list) else [expected]:
                    expected_drs.append(presupp_parser.parse(item, verbose))
                               
            expression = None
            readings = []
            try:
                expression = self.parse(sentence, **args)
                readings, errors = expression.inf_resolve(lambda x: (True, None), verbose)
                #print readings
                #print expected_drs
                
                #if ResolutionException:
                #    print("%s. !error: expected %s" % (number, str(ResolutionException)))
                #else:
                if len(expected_drs) == len(readings):
                    for index, pair in enumerate(zip(expected_drs, readings)):
                        if pair[0] == pair[1]:
                            print("%s. %s -- Reading (%s): %s\n" % (number, sentence, index+1, pair[1]))
                        else:
                            print("%s. ################# !failed reading (%s)! #################\n\n%s\n\nExpected:\t%s\n\nReturns:\t%s\n" % (number, index+1, sentence, pair[0], pair[1]))
                else:
                        print("%s. ################# !comparison failed! #################\n\n%s\n" % (number, sentence))
            except Exception, e:
                if ResolutionException:
                    print("%s. *%s -- Exception:%s\n" % (number, sentence,  e))
                else:
                    print("%s. ################# !unexpected error! #################\n%s\n" % (number, sentence, e))
                    
            
   
    def interpret(self, expr_1, expr_2, bk=False,verbose=False, test=False):
        """Interprets a new expression with respect to some previous discourse 
        and background knowledge. The function first generates relevant background
        knowledge and then performs inference check on readings generated by 
        the resolve() method. It returns a list of admissible interpretations in
        the form of DRSs."""
        
        if expr_1 and not isinstance(expr_1, str):
            return "\nDiscourse uninterpretable. Expression %s is not a string" % expr_1
        elif not isinstance(expr_2, str):
            return "\nDiscourse uninterpretable. Expression %s is not a string" % expr_2
        elif bk and not isinstance(bk, dict):
            return "\nDiscourse uninterpretable. Background knowledge is not in dictionary format"
            
        else:
            buffer = self.logic_parser.parse(r'\Q P.(Q+DRS([],[P]))')
            #buffer = parser_obj.parse(r'\Q P.(NEWINFO([],[P])+Q)')
            try:
                try:
                    if expr_1:
                        discourse = self.parse(expr_1, utter=True)
                        
                        expression = self.parse(expr_2, utter=False)
                        
                        for ref in set(expression.get_refs(True)) & set(discourse.get_refs(True)):
                            newref = DrtVariableExpression(unique_variable(ref))
                            expression = expression.replace(ref,newref,True)                   
                        
                        new_discourse = DrtApplicationExpression(DrtApplicationExpression(buffer,discourse),expression).simplify()
                    
                    else: new_discourse = self.parse(expr_2, utter=True)
                                       
                    background_knowledge = None
                    if bk:
                        lp = LogicParser().parse
                        
                        #in order for bk in DRT-language to be parsed without REFER
                        #as this affects inference
                        parser_obj = PresuppDrtParser()
                        #takes bk in both DRT language and FOL
                        try:
                                                      
                            for formula in get_bk(new_discourse, bk):
                                if background_knowledge:
                                    try:
                                        background_knowledge = AndExpression(background_knowledge, parser_obj.parse(formula).fol())
                                    except ParseException:
                                        try:
                                            background_knowledge = AndExpression(background_knowledge, lp(formula))
                                        except Exception:
                                            print Exception
                                else:
                                    try:
                                        background_knowledge = parser_obj.parse(formula).fol()
                                    except ParseException:
                                        try:
                                            background_knowledge = lp(formula)
                                        except Exception:
                                            print Exception
                                            
                            if verbose: print "Generated background knowledge:\n%s" % background_knowledge
                        
                        except AssertionError as e:
                            #catches dictionary exceptions 
                            print e
                            
                    interpretations, errors = new_discourse.inf_resolve(lambda x: inference_check(x, background_knowledge, verbose), verbose) 
                    
                    index = 1
                    
#                    for reading in new_discourse.resolve():
#                        print "\nGenerated reading (%s):" % index
#                        index = index + 1
#                        interpretation = None
#                        try:
#                            interpretation = inference_check(reading, background_knowledge, verbose)
#                            #print interpretation
#                            interpretations.append(interpretation)
#                            if verbose: print interpretation[1]
#                        except Exception:
#                            print Exception
                    
                    print "\nAdmissible interpretations:"
                    if not test: return interpretations
                    #else: return [int for int, e in interpretations if int]
                    else: return interpretations, errors
                    
                except IndexError:
                    print "Input sentences only!"
                
            except ValueError as e:
                print "Error:", e
        
            return "\nDiscourse uninterpretable"                    
                    
                    
    def inference_test(self, cases, bk,verbose=False):
        for number, discourse, expression, judgement in cases:
            print "\n%s. %s, %s" % (number, discourse, expression)
            for interpretation in self.interpret(discourse, expression, bk, verbose, test=True):
                print interpretation
                error_message = Tester.INFERROR.get(judgement,False)
                print error_message
                if type(interpretation[1]) is error_message:
                    print "Reading %s returns as expected: %s" % (interpretation[0], interpretation[1])

def main():
    tester = Tester('file:../data/grammar.fcfg', temporaldrt.DrtParser)
    sentences = ["Mia walked", "Angus wanted a boy"]
    for sentence in sentences:
        print tester._split(sentence)

if __name__ == '__main__':
    main()