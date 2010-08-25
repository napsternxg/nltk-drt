#################################
## Demo
#################################
def test (sentence, parser, draworig = True, drawdrs=True):
    print '==========================', sentence , '=========================='
    if isinstance(sentence, list):
        tree = parser.nbest_parse(sentence.pop(0).split())[0].node['SEM']
        while sentence:
            sent = sentence.pop(0)
            tree_new = parser.nbest_parse(sent.split())[0].node['SEM']
            tree = tree + tree_new
    else: 
        tree = parser.nbest_parse(sentence.split())[0].node['SEM']
    print '========================== Tree node SEM'
    print tree
    if draworig: tree.draw()
    print '========================== Tree node SEM, simplified'
    a = tree.simplify()
    print a
    print "========================== The same SEM, resolved"
    a.resolve()
    print a
    print "\n\n"
    if drawdrs: a.draw()
    
if __name__ == '__main__':
    
    from nltk import load_parser
    import temporaldrt

    parser = load_parser('file:../data/emmastest.fcfg', logic_parser=temporaldrt.DrtParser())
    #parser = load_parser('file:../data/tenseaspect.fcfg', logic_parser=temporaldrt.DrtParser())



    sentences = ['The boy marries a girl', # works, but! see 'The boy marries the girl'
                 'A boy marries the girl', # works, but! see 'The boy marries the girl'
                 'The boy marries the girl', # This doesn't work.
                            # It introduces z for both the boy and the girl. 
                            # It should rename the variable at some point before resolve() is called.
                            # It seems that rename() gets called, but it doesn't handle free variables. Check this.
                 'Every boy marries the girl', # This seems to work.
                            # It has all three types of accomodations: local, intermediate, global.
                            # It has all three types of accomodations: local, intermediate, global.
                 ['A boy marries a girl','He walks'] # no presupposition here
                 ]
    
    for sentence in sentences[-1:]: test(sentence, parser, draworig = True, drawdrs = True)