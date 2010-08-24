from nltk import load_parser
from eventdrt import EventDrtParser
from util import parse
import nltkfixtemporal

def test():
    parser = load_parser('file:../data/eventdrt_test.fcfg', logic_parser=EventDrtParser())
    s1 = "Bill wants a car. Jones needs it. He wants it."
    s2 = "He invites Jones"
    s3 = "Every man wants a car. Bill needs a car"
    s4 = "Bill wants Jones. Jones needs him. He wants himself."
    s5 = "Bill wants Jones. Himself wants Jones."
    s6 = "Jones expects himself to win."
    s7 = "Bill walks. Every man needs his car."
    s8 = "Jones needs his car. Bill wants it."
    s9 = "Jones needs no car. Bill needs it."
    s10 = "Jones needs a car and he wants it."
    drs = parse(parser,s4)
    print(drs)
    drs.draw()

if __name__ == '__main__':
    test()