from nltk import load_parser
import temporaldrt

parser = load_parser('file:../data/emmastest.fcfg', logic_parser=temporaldrt.DrtParser())

def test (sentence):
    tree = parser.nbest_parse(sentence.split())[0]
    print '==========================', sentence , '=========================='
    #print '========================== Tree node'
    #print tree.node
    #a = tree.node['SEM']
    print '========================== Tree node SEM, simplified'
    a = tree.node['SEM'].simplify()
    print a
    a.resolve()
    print "========================== The same SEM, resolved"
    print a
    print "\n\n"
    a.draw()

sentences = ['The boy marries a girl', # works, but! see 'The boy marries the girl'
             'A boy marries the girl', # works, but! see 'The boy marries the girl'
             'The boy marries the girl', # This doesn't work.
                        # It introduces z1 for both the boy and the girl. 
                        # It should rename the variable at some point before resolve() is called.
             'Every boy marries the girl' # This seems to work.
                        # Although it has all three types of accomodations: local, intermediate, global.
             ]

for sentence in sentences: test(sentence)
