
def parse(parser, text, show_interim = True):
    sentences = text.split('.')
    drs = None
    for sentence in sentences:
        sentence = sentence.lstrip()
        if sentence:
            trees = parser.nbest_parse(sentence.split())
            new_drs = trees[0].node['SEM'].simplify()
            if show_interim:
                print(new_drs)
            if drs:
                drs = (drs + new_drs).simplify()
            else:
                drs = new_drs

    if show_interim:
        print drs
    return drs.resolve()