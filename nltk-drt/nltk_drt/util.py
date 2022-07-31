"""
Common Utilities for parsing and testing
"""
__author__ = "Alex Kislev, Emma Li, Peter Makarov"
__version__ = "1.0"
__date__ = "Tue, 24 Aug 2010"

import re
from nltk import load_parser
from .temporaldrt import DrtVariableExpression, unique_variable, NewInfoDRS
from .presuppdrt import ResolutionException, DrtParser as PresuppDrtParser
from .presuppdrt import DrtConcatenation, DrtExpression, DRS
from types import LambdaType
from nltk.sem.logic import AndExpression, LogicalExpressionException, LogicParser
from nltk.sem import drt
from .inference import inference_check, get_bk, AdmissibilityError, ConsistencyError, InformativityError


class UngrammaticalException(Exception):
    pass

class FailedReading(Exception):
    pass

class ComparisonFailed(Exception):
    pass

class NoReadingProduced(Exception):
    pass

class Tester(object):

    INFERROR = {
    3 : AdmissibilityError,
    2 : InformativityError,
    1 : ConsistencyError
    }

    WORD_SPLIT = re.compile(" |, |,")
    EXCLUDED_NEXT = re.compile("^ha[sd]|is|was|not|will$")
    EXCLUDED = re.compile("^does|h?is|red|[a-z]+ness$")
    SUBSTITUTIONS = [
     (re.compile("^died$"), ("did", "die")),
     (re.compile("^([A-Z][a-z]+)'s?$"), lambda m: (m.group(1), "s")),
     (re.compile("^(?P<stem>[a-z]+)s$"), lambda m: ("does", m.group("stem"))),
     (re.compile("^([a-z]+(?:[^cvklt]|lk|nt))ed|([a-z]+[cvlkt]e)d$"), lambda m: ("did", m.group(1) if m.group(1) else m.group(2))),
     (re.compile("^([A-Z]?[a-z]+)one$"), lambda m: (m.group(1), "one")),
     (re.compile("^([A-Z]?[a-z]+)thing$"), lambda m: (m.group(1), "thing")),
     (re.compile("^bit$"), ("did", "bite")),
     (re.compile("^bought$"), ("did", "buy")),
     (re.compile("^wrote$"), ("did", "write")),
    ]

    def __init__(self, grammar, drt_parser, subtests=None):
        assert isinstance(grammar, str) and grammar.endswith('.fcfg'), \
                            "%s is not a grammar name" % grammar
        self.drt_parser = drt_parser()
        self.presupp_parser = PresuppDrtParser()
        self.logic_parser = LogicParser()
        self.parser = load_parser(grammar, logic_parser=self.drt_parser)
        self.subtests = subtests

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

    def parse(self, text, **args) -> DrtExpression:
        sentences = text.split('.')
        utter = args.get("utter", True)
        verbose = args.get("verbose", False)
        drs = (utter and self.drt_parser.parse('DRS([n],[])')) or []

        for sentence in sentences:
            sentence = sentence.lstrip()
            if sentence:
                words = self._split(sentence)
                if verbose:
                    print(words)
                trees = [tree for tree in self.parser.parse(words)]

                try:
                    new_drs = trees[0].label()["SEM"].simplify()
                except IndexError:
                    raise UngrammaticalException()
                if verbose:
                    print(new_drs)
                if drs:
                    drs = (drs + new_drs).simplify()
                else:
                    drs = new_drs

        if verbose:
            print(drs)
        return drs

    def test(self, cases, **args):
        verbose = args.get("verbose", False)
        i = 0
        for number, sentence, expected in cases:
            expected_drs = []
            if expected:
                for item in expected if isinstance(expected, list) else [expected]:
                    expected_drs.append(self.presupp_parser.parse(item, verbose))

            expression = self.parse(sentence, **args)
            readings = []
            errors = []
            try:
                readings, errors = expression.resolve(lambda x: (True, None), verbose)
            except ResolutionException as e:
                pass
            '''except Exception as e:
                with self.subtests.test(msg="seed", i=i):
                    i += 1
                    raise e'''

            #result = expression.resolve_anaphora()
            #readings = [result] # TODO
            #errors = [] # TODO (??)
            if not readings and expected:
                with self.subtests.test(msg="seed", i=i):
                    i += 1
                    raise NoReadingProduced(f"{number}. No reading produced, but expected in test!")
            elif not readings and not expected:
                pass
            elif len(expected_drs) == len(readings):
                for index, pair in enumerate(zip(expected_drs, readings)):
                    with self.subtests.test(msg="seed", i=i):
                        i += 1
                        if pair[0] == pair[1]:
                            print(("%s. %s -- Reading (%s): %s\n" % (number, sentence, index + 1, pair[1])))
                        else:
                            raise FailedReading(("%s. !!!failed reading (%s)!!!\n\n%s\n\nExpected:\t%s\n\nReturns:\t%s\n" %
                                (number, index + 1, sentence, pair[0], pair[1])))
                        
            else:
                
                with self.subtests.test(msg="seed", i=i):
                    i += 1
                    msg = f"{number}. {sentence} \n"
                    msg += "!!! comparison failed !!! \n\n Expected: \n " + '\n'.join(str(x) for x in expected_drs) + "\n\n"
                    msg += "Got:\n" + '\n'.join(str(x) for x in readings)
                    raise ComparisonFailed(msg)
                    #raise ComparisonFailed(("%s. !!!comparison failed!!!\n\n%s\n" % (number, sentence)))


    def interpret(self, expr_1, expr_2, background=None, verbose=True, test=False):
        """Interprets a new expression with respect to some previous discourse
        and background knowledge. The function first generates relevant background
        knowledge and then performs inference check on readings generated by
        the resolve() method. It returns a list of admissible interpretations in
        the form of DRSs."""

        assert(not expr_1 or isinstance(expr_1, str)), "Expression %s is not a string" % expr_1
        assert(isinstance(expr_2, str)), "Expression %s is not a string" % expr_2
        assert(not background or  isinstance(background, dict)), "Background knowledge is not in dictionary format"
        try:
            if expr_1:
                discourse = self.parse(expr_1, utter=True)
                expression = self.parse_new(discourse, expr_2)
            else:
                discourse = None
                expression = self.parse(expr_2, utter=True)

            #interpretations, errors = self.interpret_new(discourse, expression, background=background, verbose=verbose)
            result = self.interpret_new(discourse, expression, background=background, verbose=verbose)
            interpretations = [result]
            errors = [] # TODO

            if test:
                return interpretations, errors
            else:
                return interpretations

        except IndexError:
            print("Input sentences only!")

        except ValueError as e:
            print("Error:", e)

    def collect_background(self, discourse, background, verbose=True):
        background_knowledge = None
        for formula in get_bk(discourse, background):
            try:
                parsed_formula = self.presupp_parser.parse(formula).fol()
            except LogicalExpressionException:
                try:
                    parsed_formula = self.logic_parser.parse(formula)
                except Exception as e:
                    print("Error: %s" % e)

            if background_knowledge:
                background_knowledge = AndExpression(background_knowledge, parsed_formula)
            else:
                background_knowledge = parsed_formula

        if verbose:
            print("Generated background knowledge:\n%s" % background_knowledge)

        return background_knowledge

    def parse_new(self, discourse, expression_str):
        """parse the new expression and make sure that it has unique variables"""
        expression = self.parse(expression_str, utter=False)
        for ref in set(expression.get_refs(True)) & set(discourse.get_refs(True)):
            newref = DrtVariableExpression(unique_variable(ref))
            expression = expression.replace(ref, newref, True)
        return expression

    def interpret_new(self, discourse, expression, background=None, verbose=True):
        """Interprets a new expression with respect to some previous discourse
        and background knowledge. The function first generates relevant background
        knowledge and then performs inference check on readings generated by
        the resolve() method. It returns a list of admissible interpretations in
        the form of DRSs."""
        try:
            if discourse:
                new_discourse = (NewInfoDRS([], [expression]) + discourse).simplify()
            else:
                new_discourse = expression.simplify()

            if background:
                background_knowledge = self.collect_background(new_discourse, background, verbose)
            else:
                background_knowledge = None

            #
            return new_discourse.resolve(lambda x: inference_check(x, background_knowledge, verbose), verbose)
            #return new_discourse.resolve_anaphora()

        except IndexError:
            print("Input sentences only!")

        except ValueError as e:
            print("Error: %s" % e)

    def inference_test(self, cases, bk, verbose=True):
        for number, discourse, expression, judgement in cases:
            print("\n%s. %s %s" % (number, discourse, expression))
            interpretations, errors = self.interpret(discourse, expression, bk, verbose=True, test=True)

            for interpretation in interpretations:
                print("\nAdmissible interpretation: ", interpretation)

            if judgement:

                if not isinstance(judgement, list):
                    judgement = [judgement]

                if len(judgement) == len(errors):
                    for index, error in enumerate(errors):
                        error_message = Tester.INFERROR.get(judgement[index], False)
                        if verbose:
                            print("\nexpected error:%s" % error_message)
                            print("\nreturned error:%s" % error[1])
                        if type(error[1]) is error_message:
                            print("\nInadmissible reading %s returns as expected:\n\t%s" % (error[0], error_message.__name__))
                        else:
                            print("\n#!!!#: Inadmissible reading %s returned with unexpected error: %s" % (error[0], error[1]))
                else:
                    print("\n#!!!#: !Unexpected error! #!!!#")

            else:
                print("\nNo inadmissible readings")
