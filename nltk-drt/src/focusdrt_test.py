from nltk import load_parser
from focusdrt import FocusDrtParser
import nltkfix

def parse(parser, text):
    sentences = text.split('.')
    drs = None
    for sentence in sentences:
        sentence = sentence.lstrip()
        if sentence:
            trees = parser.nbest_parse(sentence.split())
            new_drs = trees[0].node['SEM'].simplify()
            print(new_drs)
            if drs:
                drs = (drs + new_drs).simplify()
            else:
                drs = new_drs

    drs = drs.resolve_anaphora()
    print(drs)
    drs.draw()

def test():
    parser = load_parser('file:../data/focusdrt-test.fcfg', logic_parser=FocusDrtParser())
    s1 = "He wants a car. Jones needs it."
    s2 = "He invites Jones."
    parse(parser,s2)

if __name__ == '__main__':
    test()