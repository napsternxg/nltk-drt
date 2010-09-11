import nltkfixtemporal

from nltk import load_parser
from nltk.sem.drt import AbstractDrs

class ReverseIterator:
    def __init__(self, sequence):
        self.sequence = sequence
    def __iter__(self):
        i = len(self.sequence)
        while i > 0:
            i = i - 1
            yield self.sequence[i]

class Tester(object):
    def __init__(self, grammar, logic_parser):
        assert isinstance(grammar, str) and grammar.endswith('.fcfg'), \
                            "%s is not a grammar name" % grammar
        self.logic_parser = logic_parser
        self.parser = load_parser(grammar, logic_parser=self.logic_parser()) 
        
    def parse(self, text, **args):
        sentences = text.split('.')
        utter = args.get("utter", False)
        show_interim = args.get("show_interim", False)
        drs = (utter and self.logic_parser.parse('DRS([n],[])')) or []
        
        for sentence in sentences:
            sentence = sentence.lstrip()
            if sentence:
                new_words = []
                for word in sentence.split():
                    if "'" in word:
                        parts = word.split("'")
                        new_words.append(parts[0])
                        if parts[1]:
                            new_words.append(parts[1])
                    else:
                        new_words.append(word)
    
                trees = self.parser.nbest_parse(new_words)
                new_drs = trees[0].node['SEM'].simplify()
                if show_interim:
                    print(new_drs)
                if drs:
                    drs = (drs + new_drs).simplify()
                else:
                    drs = new_drs
    
        if show_interim:
            print drs
        return drs

    def test(self, cases, **args):
        for number, sentence, expected, error in cases:
            if expected is not None:
                expected_drs = self.logic_parser.parse(expected)
            else:
                expected_drs = None

            drs_list = []
            try:
                drs_list.append(self.parse(sentence, args))
                drs_list.append(drs_list[-1].resolve())
                drs_list.append(drs_list[-1].resolve())
                if error:
                    print("%s. !error: expected %s" % (number, str(error)))
                else:
                    if drs_list[-1] == expected_drs:
                        print("%s. %s %s" % (number, sentence, drs_list[-1]))
                    else:
                        print("%s. !comparison failed %s != %s" % (number, drs_list[-1], expected_drs))
            except Exception, e:
                if error and isinstance(e, error):
                    if drs_list[-1] == expected_drs:
                        print("%s. *%s %s (%s)" % (number, sentence, drs_list[-1],  e))
                    else:
                        print("%s. !comparison failed %s != %s" % (number, drs_list[-1], expected_drs))
                else:
                    print("%s. !unexpected error: %s" % (number, e))
