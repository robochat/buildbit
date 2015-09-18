#!/usr/bin/env python2
"""a simple build system inspired by gnu make"""

"""
#TO DO
 - file path stuff
 - unit test
 - wildcards in deps
 - wildcards in targets
 - multiple targets - semantics, a rule makes all of the targets? or just the one that asked for it?
 - patterns
 - defaults: PHONY, patterns
 - enviroment variables (dict on make class?)
 - shortcuts for rules with simple shell command recipes
"""
from orderedset import OrderedSet
import pathlib
from collections import Iterable
from types import StringTypes
import warnings
import glob
import itertools

def checkinput(val):
    """replaces None with an empty tuple and wraps
    non-iterable values into a tuple too."""
    if not val: val = tuple()
    elif isinstance(val,StringTypes): val = (val,)
    elif not isinstance(val,Iterable): val = (val,)
    return val

def dedup(seq):
    """deduplicate a list while keeping the original order"""
    seen = set()
    seen_add = seen.add
    return [ x for x in seq if not (x in seen or seen_add(x))]

def translate(pat):
    """Translate a shell PATTERN to a regular expression.

    There is no way to quote meta-characters.
    
    This is lifted from the fnmatch.py module with an extra case for pattern rules
    Each % is treated as a wildcard inside a group.
    """

    i, n = 0, len(pat)
    res = ''
    while i < n:
        c = pat[i]
        i = i+1
        if c == '*':
            res = res + '.*'
        elif c == '%':
            res = res + '(.*)'
        elif c == '?':
            res = res + '.'
        elif c == '[':
            j = i
            if j < n and pat[j] == '!':
                j = j+1
            if j < n and pat[j] == ']':
                j = j+1
            while j < n and pat[j] != ']':
                j = j+1
            if j >= n:
                res = res + '\\['
            else:
                stuff = pat[i:j].replace('\\','\\\\')
                i = j+1
                if stuff[0] == '!':
                    stuff = '^' + stuff[1:]
                elif stuff[0] == '^':
                    stuff = '\\' + stuff
                res = '%s[%s]' % (res, stuff)
        else:
            res = res + re.escape(c)
    return res + '\Z(?ms)'


class Make(object):
    def __init__(self):
        self.raw_graph={}
        self.PHONY=[] # list of phony targets
        
        self.buildorder=OrderedSet() #recipe for building target.
        self._uptodate=set() #working variable: rules that have been processed and found up to date
        
    
    def rulefactory(self0):
        """Generates the rule decorator"""
        #--------------------------------------------------------
        class Rule(object):
            def __init__(self,targets,deps,order_only=None):
                self._make = self0 #reference to Make instance
                self.targets = checkinput(targets)
                self._deps = checkinput(deps)
                self._order_only = checkinput(order_only)
                
                #add rule to build
                raw_graph = self._make.raw_graph
                for target in targets:
                    if target in raw_graph:
                        warnings.warn('Make takes the last defined rule for each target. Overwriting the rule for %r' %target)
                    raw_graph[target] = self
                
            def __call__(self,func):
                self.func = func
                return func
                        
            def build(self):
                if hasattr(self,'func'): self.func(self)
                
            def expand_wildcards(self,seq):
                """expands wildcards in the dep names using the glob module"""
                return itertools.chain(glob.glob(i) for i in seq)
            
            @property
            def target(self):
                """Returns the target name. If there are multiple targets then
                the name of the target that was selected will be returned."""
                #This requires changes to the program structure. It might also
                #lead to inefficiencies
            
            @property
            def deps(self):
                """prerequisite list with any duplicate entries eliminated
                and wildcards expanded"""
                seq = tuple(self.expand_wildcards(self._deps))
                return dedup(seq)
            
            @property
            def order_only(self):
                """order only prerequisite list with duplicate entries eliminated
                including those from the deps list and wildcards expanded."""
                seq = tuple(self.expand_wildcards(self._order_only))
                seq2 = dedup(seq)
                #eliminate any entries already in deps
                pass
                return seq2
            
            @property
            def all_deps(self):
                """returns prerequisite list including duplicate entries and
                with wildcards expanded"""
                seq = tuple(self.expand_wildcards(self._deps))
                return seq
            
            @property
            def changed_deps(self):
                """returns only those dependencies that have changed in the prerequisite 
                list with wildcards expanded"""
                seq = tuple(self.expand_wildcards(self._deps))
                #check modification times against target modification time
                pass
                
            def __repr__(self):
                return repr(self.targets)+':'+repr(self.deps)+'|'+repr(self.order_only)
        #-------------------------------------------------------
        return Rule
    
    def calc_build(self,target):
        """recursively calculate the steps needed to build for this 
        target. The resulting recipe is stored in self.buildorder"""
        #clear working variables
        self.buildorder = OrderedSet()
        self._uptodate = set()
        rebuild = self._calc_build(target)
        return rebuild
        
    def _calc_build(self,target):
        """recursively calculate the steps needed to build for this 
        target. The resulting recipe is stored in self.buildorder"""
        targetp = pathlib.Path(target)
        target_exists = targetp.exists()
        must_build = (target in self.PHONY) or not target_exists
        
        trgrule = self.raw_graph.get(target,None) #search for rule - pattern matching??
        
        if not target_exists and not trgrule:
            raise InputError("No target or file found for %r" %target) 
        elif target_exists and not trgrule:
            rebuild = False # source files never need to be built
        elif trgrule in self.buildorder: # optimisation
            rebuild = True # already processed this rule and needs rebuilding
        elif trgrule in self._uptodate: # optimisation
            if must_build:
                self._uptodate.remove(trgrule) # correction
                rebuild = True
            else:
                rebuild = False # already seen and up to date
        else:
            rebuild = False
            
            for dep in trgrule.order_only:
                if not pathlib.Path(dep).is_file():
                    rebuild |= self._calc_build(dep)
            
            deps = trgrule.deps
            for dep in deps:
                rebuild |= self._calc_build(dep)
            
            if must_build:
                rebuild = True
            elif rebuild == False: #check modification dates
                target_mtime = targetp.lstat().st_mtime
                rebuild = any(pathlib.Path(dep).lstat().st_mtime > target_mtime 
                              for dep in deps)
                #lstat() method looks dangerous but logically if a dep doesn't exist
                #or is a phony target then this code path shouldn't run anyway.
        
        if rebuild:
            self.buildorder.add(trgrule)
        else:
            self._uptodate.add(trgrule)
        
        return rebuild
    
    def build(self):
        for rule in self.buildorder:
            rule.build()




build = Make()
rule = build.rulefactory()
    

@rule(['test1.txt'],[])
def test1(self):
    #print targets
    print self.deps
    print self.order_only
    print 'hello'


@rule(['test2.txt'],['test1.txt'])
def test2(self):
    print 'hello hello'


@rule(['test3.txt','test4.txt'],['test2.txt','test1.txt'])
def test3(self):
    print 'goodbye',
    print self.targets
    
    
"""
Design Questions

Each feature seems to raise a question.

multiple targets: Does this mean that one run of the recipe makes all of the targets? Or
    does it mean that the recipe varies depending upon the target requested. Make choses
    the second option since we can use $@ to get the requested target name and hence make
    the recipe dependent upon the name. However, the second option could lead to the same
    recipe being unnecessarily run multiple times. Currently this system uses the first
    option.
    
wildcard targets: Basically has the same problem as the multiple targets case.

wildcard prerequisites: When do we look for files that match the rules? Before the build has
    started. After any order_only rules have run? Just before the rule is due to run - except
    how can we sort out the build order in this case?

"""