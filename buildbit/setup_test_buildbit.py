#!/usr/bin/env python
"""example script for package buildbit."""

from bob import Rule as rule
import bob
from sh import touch,mkdir,ls

#make test directories

def makedir(self):
    for target in self.targets:
        mkdir('-p',target)

outpath = 'tests-unittests/'

r0 = rule(outpath[:-1],None,func=makedir)
assert isinstance(r0,bob.ExplicitRule)

tmp = rule(outpath+'A',None,order_only=outpath[:-1]).func = makedir
assert (tmp is makedir)
r1 = bob.ExplicitRule.rules[outpath+'A']

r2 = rule(outpath+'B',None,order_only=outpath[:-1])
r2.func = makedir
assert isinstance(r2,bob.ExplicitRule)

###make files for dir A###

@rule(outpath+'A/test1.c',None,order_only=outpath+'A')
@rule(outpath+'A/test2',None,order_only=outpath+'A')
@rule(outpath+'A/test3.txt',None,order_only=outpath+'A')
def mytouch(self):
    touch(self.targets)
    
r3 = bob.ExplicitRule.rules[outpath+'A/test1.c']
r4 = bob.ExplicitRule.rules[outpath+'A/test2']
r5 = bob.ExplicitRule.rules[outpath+'A/test3.txt']

##one shared rule for many targets
r6 = rule([outpath+'A/test%d.c' %i for i in range(4,20)],None,shared=True,order_only=outpath+'A')
r6.func = mytouch
assert isinstance(r6,bob.ExplicitRule)

myls = "ls {reqs} > {targets}"
myls = "ls {$^} > {$@}"

##prerequisites
r7 = rule(outpath+'A/ex1.txt',[outpath+'A/test2',outpath+'A/test3.txt'],func=myls)
assert isinstance(r7,bob.ExplicitRule)

##many targets (without shared rule)
r8 = rule([outpath+'A/foo{0}'.format(i) for i in range(10)],None,order_only=outpath+'A',shared=False)
assert isinstance(r8,bob.ManyRules)

@r8
def makefile(self):
    with open(self.targets[0],'w') as fobj:
        fobj.write(str(self.targets)+'\n')

###make files for dir B###

##wildcard prerequisite (mixture of wildcards and explicit)
#unlike make, buildbit also searches the set of explicit rules for matches.
r9 = rule(outpath+'B/contentsA.txt',outpath+'A/*',order_only=outpath+'B')
r9.func = myls
assert isinstance(r9,bob.ExplicitTargetRule)

##PHONY target
rule('All',[outpath+'B/contentsA.txt',outpath+'result',outpath+'result2',outpath+'B/example4.txt',outpath+'A/test5.final'],PHONY=True) 
#didn't bother to define a build func but still works
#out of order definitions are fine

##wildcard target
r10 = rule(outpath+'B/*fa[ab]',None,func=makefile)
assert isinstance(r10,bob.WildRule)

##wildcard targets (mixture of wildcards and explicit) (not shared)
r11 = rule([outpath+'B/bar[12345].dat',outpath+'A/test3.txt'],None,
          order_only=[outpath+'A',outpath+'B'],func=makefile)#shared=False is default
assert isinstance(r11,bob.WildRule)
#should also cause a warning to appear since ExplicitRule for this target already exists.
#wildcards can be *,?,[..],[!..] just like python's fnmatch module

##wildcard targets (shared)
r12 = rule([outpath+'B/example1.txt',outpath+'B/example2.txt',outpath+'B/example?.txt'],
          [outpath+'B/bar2.dat',outpath+'B/bar4.dat'],order_only=outpath+'B',shared=True)
r12.func=mytouch
assert isinstance(r12,bob.WildSharedRule)
assert outpath+'B/example1.txt' in bob.ExplicitRule.rules

###make files for test dir###

##create a general pattern rule - can match to requested prerequisites in sub-directories too.
r13 = rule('%.o','%.c',func='touch {targets}') # using command string directly
assert isinstance(r13,bob.PatternRule)

#buildbit will create intemediate files (unlike make though it doesn't yet delete them)
r14 = rule(outpath+'result',[outpath+'A/test{0}.o'.format(i) for i in [1]+range(4,20)])
r14.func=myls
#because r2 is a shared rule, buildbit will only run the it once despite multiple requests for its targets.

##pattern rule
r15 = rule(outpath+'test%.o',outpath+'A/test%.c',order_only=[outpath+'B'])
r15.func=makefile #pattern rule

#buildbit will use the pattern rule with the closest match
r16 = rule(outpath+'result2',[outpath+'test{0}.o'.format(i) for i in range(4,20)],func=myls)

##pattern rule with wildcards
r17 = rule(outpath+'%/*est%.final',outpath+'%/test%.*',func=makefile)


## Final explicit rule depending upon wildcards and pattern rules
#r18 = rule(???)


if False: #__name__=="__main__":
    buildseq = rule.calc_build('All')
    print buildseq
    response=raw_input("run build? [(y)es/(n)o]")
    if response in ('y','yes'):
        rule.build(buildseq)
        
if __name__=="__main__":
    rule.main()
