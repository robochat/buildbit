#!/usr/bin/env python
"""example script for package buildbit."""

from bob import Rule as rule
import bob
from sh import touch,mkdir,ls
import os

pjoin = os.path.join


def makedir(self):
    for target in self.targets:
        mkdir('-p',target)

#make test directory
rule('tests/C',[]).func = makedir

#make test prerequisites
@rule('tests/C/*.txt',None,order_only='tests/C')
def source(self):
    touch(self.targets)

#test PatternSharedRule
@rule(['%.c','%.o'],'%.txt',shared=True)
def compile(self):
    touch([pjoin(self.extratargetpath,self.stems[0]+'.o'),
           pjoin(self.extratargetpath,self.stems[0]+'.c')])
    #self.extratargetpath - pattern rules can be applied to subdirs too, this 
    #                       attribute might sometimes be useful.
    

#This PatternRule instance should be shadowed by the PatternSharedRule
@rule(['%.c','%.o'],'%.txt',shared=False)
def compile(self):
    print "shouldn't run"
    touch(self.targets)

rule('All',PHONY=True,reqs=['tests/C/1.c','tests/C/1.o','tests/C/2.c'])



if __name__=="__main__":
    rule.main()

