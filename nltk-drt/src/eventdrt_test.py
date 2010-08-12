from nltk import load_parser
from eventdrt import EventDrtParser
from util import parse
import nltkfix

def test():
    parser = load_parser('file:../data/eventdrt_test.fcfg', logic_parser=EventDrtParser())
    s1 = "Jones needs a car. He wants it. Bill wants it. He needs it"
    s2 = "Mia ordered a five dollar shake. Vincent tasted it."
    drs = parse(parser,s1)
    print(drs)
    drs.draw()

if __name__ == '__main__':
    test()