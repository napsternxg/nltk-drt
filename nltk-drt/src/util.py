import nltkfixtemporal

from nltk import load_parser
from nltk.sem.drt import AbstractDrs
from temporaldrt import DRS
import nltk.sem.drt as drt
import temporaldrt
import re
from types import LambdaType

class local_DrtParser(temporaldrt.DrtParser):
    
    def handle_DRS(self, tok, context):
        drs = drt.DrtParser.handle_DRS(self, tok, context)
        return DRS(drs.refs, drs.conds)

class Tester(object):

    EXCLUDED_NEXT = re.compile("^ha[sd]|is|not$")
    EXCLUDED = re.compile("^does|h?is|red|[a-z]+ness$")
    SUBSTITUTIONS = [
    (re.compile("^died$"), ("did", "die")),
     (re.compile("^([A-Z][a-z]+)'s?$"),   lambda m: (m.group(1), "s")),
     (re.compile("^(?P<stem>[a-z]+)s$"),  lambda m: ("does", m.group("stem"))),
     (re.compile("^([a-z]+[^cv])ed|([a-z]+[cv]e)d$"), lambda m: ("did", m.group(1) if m.group(1) else m.group(2))),
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
        for word in sentence.split():
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
        for number, sentence, expected, error in cases:
            if expected is not None:
                expected_drs = local_DrtParser().parse(expected).readings(verbose)[0]
            else:
                expected_drs = None

            drs_list = []
            readings = []
            try:
                drs_list.append(self.parse(sentence, **args))
                readings.append(drs_list[-1].readings(verbose)[0])
                if error:
                    print("%s. !error: expected %s" % (number, str(error)))
                else:
                    if readings[-1] == expected_drs:
                        print("%s. %s %s" % (number, sentence, readings[-1]))
                    else:
                        print("%s. !comparison failed %s != %s" % (number, readings[-1], expected_drs))
            except Exception, e:
                if error and isinstance(e, error):
                    #if readings[-1] == expected_drs:
                    print("%s. *%s (%s)" % (number, sentence,  e))
                    #else:
                    #    print("%s. !comparison failed %s != %s" % (number, readings[-1], expected_drs))
                else:
                    print("%s. !unexpected error: %s" % (number, e))

def main():
    tester = Tester('file:../data/grammar.fcfg', temporaldrt.DrtParser)
    sentences = ["If Mia danced Angus lived", "Bill owned Jones's picture of him"]
    for sentence in sentences:
        print tester._split(sentence)

if __name__ == '__main__':
    main()