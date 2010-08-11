from nltk import load_parser
from eventdrt import EventDrtParser
from focusdrt_test import parse

def test():
    parser = load_parser('file:../data/eventdrt.fcfg', logic_parser=EventDrtParser())
    s1 = "Jeff likes Bill. He kills him."
    parse(parser,s1)

if __name__ == '__main__':
    test()