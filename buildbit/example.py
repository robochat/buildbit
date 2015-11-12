#!/usr/bin/env python
"""example script for package buildbit."""
from bob import Rule as rule
import bob
from sh import touch

r1 = rule('tests/test1.txt',None)
r2 = rule('tests/test2.txt',None)
r3 = rule('tests/test3.txt',None)

@rule('tests/ex1.txt','tests/test*.txt')
@rule('tests/ex%.txt','tests/test%.txt')
def mytouch(self):
    touch(self.targets)

for r in r1,r2,r3:
    r.func = mytouch

if __name__=="__main__":
    rule.main()

# Can easily run buildbit from within script. 
if False: #__name__=="__main__":
    buildseq = rule.calc_build('All')
    print buildseq
    response=raw_input("run build? [(y)es/(n)o]")
    if response in ('y','yes'):
        rule.build(buildseq)
