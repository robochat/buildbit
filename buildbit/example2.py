#!/usr/bin/env python
"""example script for package buildbit."""

from bob import Rule as rule
import bob
from sh import touch,mkdir,ls

#make test directories

def makedir(self):
    for target in self.targets:
        mkdir('-p',target)

rule('tests',None,func=makedir)

rule('tests/A',None,order_only='tests').func = makedir

r1 = rule('tests/B',None,order_only='tests')
r1.func = makedir
assert isinstance(r1,bob.ExplicitRule)

###make files for dir A###

@rule('tests/A/test1.c',None,order_only='tests/A')
@rule('tests/A/test2',None,order_only='tests/A')
@rule('tests/A/test3.txt',None,order_only='tests/A')
def mytouch(self):
    touch(self.targets)
    
##one shared rule for many targets
r2 = rule(['tests/A/test%d.c' %i for i in range(4,20)],None,shared=True,order_only='tests/A')
r2.func = mytouch
assert isinstance(r2,bob.ExplicitRule)

myls = "ls {reqs} > {targets}"
myls = "ls {$^} > {$@}"

##prerequisites
r3 = rule('tests/A/ex1.txt',['tests/A/test2','tests/A/test3.txt'],func=myls)
assert isinstance(r3,bob.ExplicitRule)

##many targets (without shared rule)
r4 = rule(['tests/A/foo{0}'.format(i) for i in range(10)],None,order_only='tests/A',shared=False)
assert isinstance(r4,bob.ManyRules)

@r4
def makefile(self):
    with open(self.targets[0],'w') as fobj:
        fobj.write(str(self.targets)+'\n')

###make files for dir B###

##wildcard prerequisite (mixture of wildcards and explicit)
#unlike make, buildbit also searches the set of explicit rules for matches.
r5 = rule('tests/B/contentsA.txt','tests/A/*',order_only='tests/B')
r5.func = myls
assert isinstance(r5,bob.ExplicitTargetRule)

##PHONY target
rule('All',['tests/B/contentsA.txt','tests/result','tests/result2','tests/B/example4.txt','tests/A/test5.final'],PHONY=True) 
#didn't bother to define a build func but still works
#out of order definitions are fine

##wildcard target
r7 = rule('tests/B/*fa[ab]',None,func=makefile)
assert isinstance(r7,bob.WildRule)

##wildcard targets (mixture of wildcards and explicit) (not shared)
r8 = rule(['tests/B/bar[12345].dat','tests/A/test3.txt'],None,order_only=['tests/A','tests/B'],func=makefile)#shared=False is default
assert isinstance(r8,bob.WildRule)
#should also cause a warning to appear since ExplicitRule for this target already exists.
#wildcards can be *,?,[..],[!..] just like python's fnmatch module

##wildcard targets (shared)
r9 = rule(['tests/B/example1.txt','tests/B/example2.txt','tests/B/example?.txt'],['tests/B/bar2.dat','tests/B/bar4.dat'],order_only='tests/B',shared=True)
r9.func=mytouch
assert isinstance(r9,bob.WildSharedRule)
assert 'tests/B/example1.txt' in bob.ExplicitRule.rules

###make files for test dir###

##create a general pattern rule - can match to requested prerequisites in sub-directories too.
r10 = rule('%.o','%.c',func='touch {targets}') # using command string directly
assert isinstance(r10,bob.PatternRule)

#buildbit will create intemediate files (unlike make though it doesn't yet delete them)
rule('tests/result',['tests/A/test{0}.o'.format(i) for i in [1]+range(4,20)]).func=myls
#because r2 is a shared rule, buildbit will only run the it once despite multiple requests for its targets.

##pattern rule
rule('tests/test%.o','tests/A/test%.c',order_only=['tests/B']).func=makefile #pattern rule

#buildbit will use the pattern rule with the closest match
rule('tests/result2',['tests/test{0}.o'.format(i) for i in range(4,20)],func=myls)

##pattern rule with wildcards
r15 = rule('tests/%/*est%.final','tests/%/test%.*',func=makefile)

if False: #__name__=="__main__":
    buildseq = rule.calc_build('All')
    print buildseq
    response=raw_input("run build? [(y)es/(n)o]")
    if response in ('y','yes'):
        rule.build(buildseq)
        
if __name__=="__main__":
    rule.main()
