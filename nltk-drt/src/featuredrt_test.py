from nltk import load_parser
from featuredrt import DrtParser, AnaphoraResolutionException
from util import parse, test
import nltkfixtemporal

def get_refs(self, recursive=False):
    return []

from nltk.sem.drt import AbstractDrs

AbstractDrs.get_refs = get_refs

def main():
    #parser = load_parser('file:../data/test.fcfg', logic_parser=FeatureDrtParser())
    cases = [
    (1, "He wants a car. Jones needs it.", "DRS([x{sg,m},z2{sg,n},e,z5{sg,m},z4{sg,n},e06],[PRO(x), car(z2), want(e), AGENT(e,x), THEME(e,z2), Jones(z5), PRO(z4), need(e06), AGENT(e06,z5), THEME(e06,z4)])", AnaphoraResolutionException),
    (2, "He invites Jones.", "DRS([x{sg,m},z8{sg,m},e],[PRO(x), Jones(z8), invite(e), AGENT(e,x), THEME(e,z8)])", AnaphoraResolutionException),
    (3, "Jones loves Charlotte but Bill loves her and he asks himself.", "DRS([x{sg,m},z10{sg,f},e,z13{sg,m},z12{sg,f},e014,z19{sg,m},z16{sg,m},e020],[Jones(x), Charlotte(z10), love(e), AGENT(e,x), THEME(e,z10), Bill(z13), PRO(z12), love(e014), AGENT(e014,z13), THEME(e014,z12), PRO(z19), REFPRO(z16), ask(e020), AGENT(e020,z19), THEME(e020,z16)])", None),
    (4, "Jones loves Charlotte but Bill loves her and he asks him.", "DRS([x{sg,m},z24{sg,f},e,z27{sg,m},z26{sg,f},e028,z33{sg,m},z30{sg,m},e034],[Jones(x), Charlotte(z24), love(e), AGENT(e,x), THEME(e,z24), Bill(z27), PRO(z26), love(e028), AGENT(e028,z27), THEME(e028,z26), PRO(z33), PRO(z30), ask(e034), AGENT(e034,z33), THEME(e034,z30)])", None),
    (5, "Jones loves Charlotte but Bill loves her and himself asks him.", "DRS([x{sg,m},z38{sg,f},e,z41{sg,m},z40{sg,f},e042,z47{sg,m},z44{sg,m},e048],[Jones(x), Charlotte(z38), love(e), AGENT(e,x), THEME(e,z38), Bill(z41), PRO(z40), love(e042), AGENT(e042,z41), THEME(e042,z40), REFPRO(z47), PRO(z44), ask(e048), AGENT(e048,z47), THEME(e048,z44)])", AnaphoraResolutionException),
    (6, "Jones likes a picture of himself.", "DRS([x{sg,m},z53{sg,m},e,z56{sg,n},e055],[Jones(x), REFPRO(z53), relation(e), RELATING(e,z53), picture(z56), RELATED(e,z56), like(e055), AGENT(e055,x), THEME(e055,z56)])", None),
    (7, "Jones likes a picture of him.", "DRS([x{sg,m},z59{sg,m},e,z62{sg,n},e061],[Jones(x), PRO(z59), relation(e), RELATING(e,z59), picture(z62), RELATED(e,z62), like(e061), AGENT(e061,x), THEME(e061,z62)])", None),
    (8, "Bill likes Jones's picture of himself", "DRS([x{sg,m},z71{sg,m},e,z72{sg,m},e069,z65{sg,n},e070],[Bill(x), REFPRO(z71), relation(e), RELATING(e,z71), Jones(z72), possession(e069), POSSESSOR(e069,z72), POSSESSED(e069,z65), picture(z65), RELATED(e,z65), like(e070), AGENT(e070,x), THEME(e070,z65)])", None),
    (9, "Bill likes Jones's picture of him", "DRS([x{sg,m},z81{sg,m},e,z82{sg,m},e079,z75{sg,n},e080],[Bill(x), PRO(z81), relation(e), RELATING(e,z81), Jones(z82), possession(e079), POSSESSOR(e079,z82), POSSESSED(e079,z75), picture(z75), RELATED(e,z75), like(e080), AGENT(e080,x), THEME(e080,z75)])", None),
    (10, "Bill's car walks", "DRS([x{sg,m},e,z51{sg,n},e052],[Bill(x), possession(e), POSSESSOR(e,x), POSSESSED(e,z51), car(z51), walk(e052), AGENT(e052,z51)])", None)
    ]

    #test(parser, FeatureDrtParser(), cases, False)

    #print(parse(parser, "Bill's car walks"))
    #print(parse(parser, "His car walks"))

    parser = load_parser('file:../data/test.fcfg', logic_parser=DrtParser())
    drs = parse(parser, "Jones loves Charlotte but Bill loves her and he asks himself.", False)
    #print drs.resolve()
    drs.draw()

if __name__ == '__main__':
    main()