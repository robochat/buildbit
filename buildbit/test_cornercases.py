#!/usr/bin/env python
"""module of unit tests for buildbit system. This module tries to test some
corner cases, particularly related to paths including meta characters."""
import unittest2 as unittest
import bob
import fpmatch

rule = bob.Rule

crazy_path = 'f*%?[*&%]]]][[].txt'
escaped_crazy_path = 'f[*][%][?][[][*]&[%]]]]][[][[]].txt'

assert fpmatch.fnmatch(crazy_path,escaped_crazy_path)

#does buildbit work correctly on paths with metacharacters in their names/paths?



#Explicit Rules#
#explicit rules should work ok as they don't use any globbing or fpmatch functionality (?)

r1 = bob.ExplicitRule('tests/'+crazy_path,None,func = 'touch {targets}')

r2 = bob.ExplicitRule('tests/test1.txt','tests/'+crazy_path,func = 'touch {targets}')

#can buildbit find the prequisite of r2?


#MetaRules - escaped paths#
#if we want to be able to use anything other than ExplicitRule then we will need
#to escape the path's metacharacters but buildbit might then register the path
#as a wildcard or pattern path instead of an Explicit target or prequisite making
#the build graph incorrect. The issue here is paths that seem to contain wildcards
#but in fact only contain escaped wildcards (metacharacters).

#For instance, we might have rules with many targets or prerequisites where one
#is an explicit rule containing escaped metacharacters but others are true wildcard
#rules or pattern rules. Explicit targets and prerequisites are treated diferently
#from ones with wildcards/patterns and so this corrupts the buildbit system.

#pain points 
# * fpmatch.has_magic
# * does rule.__new__ chose the correct rule?
# * MetaRule.__init__ / WildSharedRule.__init__ / WildRule.__init__
# * ExplicitTargetRule.expand_wildcard
# * rule.get()

# plan
#fpmatch.has_magic should recognise when a path has_magic but only to escape metacharacters
#fpmatch needs an extra function to return the path with metacharacters escaped (only if all are escaped??)
#change fpmathc.has_magic to new code...
#testing




#cases
# 1. explicit prerequisite -> explicit target

# 2. explicit prerequisite -> wildcard target

# 3. wildcard prerequisite -> explicit target





# question: putting % char into ExplicitTargetRule prerequisites could lead to errors since glob.glob doesn't understand it ? No, if % is present then it should be a literal rather than a wildcard.

#Testing Rule#
#testing whether we get the right Rule class from Rule for rules containing metacharacters.