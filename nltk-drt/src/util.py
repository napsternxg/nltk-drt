import nltkfixtemporal

from nltk import load_parser
from nltk.sem.drt import AbstractDrs
from temporaldrt import DRS
import nltk.sem.drt as drt
import temporaldrt
import re


class local_DrtParser(temporaldrt.DrtParser):
    
    def handle_DRS(self, tok, context):
        drs = drt.DrtParser.handle_DRS(self, tok, context)
        return DRS(drs.refs, drs.conds)







class Tester(object):
    subs = [#(re.compile("^(?P<stem>[a-z]+)ed$"), lambda m: "did %s" % m.group("stem")),
            (re.compile("^([A-Z][a-z]+)'s?$"), lambda m: "%s s" % m.group(1)),
            #(re.compile("^([a-z]+)s$"), lambda m: "does %s" % m.group(1)),
            (re.compile("^owns$"), "does own"),
            (re.compile("^owned$"), "did own"),
            (re.compile("^lives$"), "does live"),
            (re.compile("^lived$"), "did live"),
            (re.compile("^died$"), "did die"),
            (re.compile("^smiled$"), "did smile"),
            (re.compile("^bought$"), "did buy"),
            (re.compile("^walked$"), "did walk"),
            (re.compile("^danced$"), "did dance"),
            (re.compile("^kissed$"), "did kiss"),
            (re.compile("^bit$"), "did bite"),
            (re.compile("^wrote$"), "did write"),
            (re.compile("^everyone$"), "every one"),
            (re.compile("^Everyone$"), "every one"),
            (re.compile("^Everything$"), "every thing"),
            (re.compile("^everything"), "every thing"),
            (re.compile("^no-one"), "no one"),
            (re.compile("^No-one$"), "no one"),
            (re.compile("^nothing$"), "no thing"),
            (re.compile("^Nothing$"), "no thing")]
    
    def __init__(self, grammar, logic_parser):
        assert isinstance(grammar, str) and grammar.endswith('.fcfg'), \
                            "%s is not a grammar name" % grammar
        self.logic_parser = logic_parser()
        self.parser = load_parser(grammar, logic_parser=self.logic_parser) 

    def parse(self, text, **args):
        sentences = text.split('.')
        utter = args.get("utter", True)
        show_interim = args.get("show_interim", False)
        drs = (utter and self.logic_parser.parse('DRS([n],[])')) or []
        
        for sentence in sentences:
            sentence = sentence.lstrip()
            if sentence:
                new_words = []
                split = sentence.split()
                for word in split:
                    is_written = False
                    if not ((split[split.index(word)-1] == 'has' or
                        split[split.index(word)-1] == 'had' or
                        (split[split.index(word)-1] == 'not' and
                        (split[split.index(word)-2] == 'has' or
                        split[split.index(word)-2] == 'had')))):
                        """should not break down past participles"""
                        
                        for pattern, repl in self.subs:
                            word_list = pattern.sub(repl, word)
                            word_list = word_list.split(" ")
                            if len(word_list)>1:
                                new_words.extend(word_list)
                                is_written = True
                                break

                    if not is_written:
                        new_words.append(word)
    
                print new_words
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
                expected_drs = local_DrtParser().parse(expected).readings()[0]
            else:
                expected_drs = None

            drs_list = []
            readings = []
            try:
                drs_list.append(self.parse(sentence, utter=True))
                readings.append(drs_list[-1].readings()[0])
                if error:
                    print("%s. !error: expected %s" % (number, str(error)))
                else:
                    if readings[-1] == expected_drs:
                        print("%s. %s %s" % (number, sentence, readings[-1]))
                    else:
                        print("%s. !comparison failed %s != %s" % (number, readings[-1], expected_drs))
            except Exception, e:
                if error and isinstance(e, error):
                    if readings[-1] == expected_drs:
                        print("%s. *%s %s (%s)" % (number, sentence, readings[-1],  e))
                    else:
                        print("%s. !comparison failed %s != %s" % (number, readings[-1], expected_drs))
                else:
                    print("%s. !unexpected error: %s" % (number, e))
