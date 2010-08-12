from nltk import load_parser
from focusdrt import FocusDrtParser
import nltkfix
from util import parse

def test():
    parser = load_parser('file:../data/focusdrt_test.fcfg', logic_parser=FocusDrtParser())
    s1 = "He wants a car. Jones needs it."
    s2 = "He invites Jones."
    drs = parse(parser,s2)
    print(drs)
    drs.draw()

if __name__ == '__main__':
    test()