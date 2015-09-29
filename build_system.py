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

def checksingleinput(val):
    """checks that input is not a sequence"""
    if isinstance(val,StringTypes): pass
    elif isinstance(val,Iterable): raise InputError("input should not be a sequence: %r" %val)
    return val

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

def ruleglob1(pat,seq):
    """searches explicit rules for matching file path patterns, returns any matches
    """
    ??
    return ??

    
class Build(object):
    explicit_rules={}
    pattern_rules={}
    PHONY=[] # list of phony targets
    
    buildorder=OrderedSet() #recipe for building target.
    _uptodate=set() #working variable: rules that have been processed and found up to date
    
    @class_method
    def find_target(cls,target):
        """retrieve the best matched rule from the rule set. Target should be explicit
        expansion of dep wildcards is handled elsewhere (by the rules themselves)"""
        #explicit rules
        if target in cls.explicit_rules:
            return cls.explicit_rules[target]
        #pattern rules
        matches = [target for target,rule in cls.pattern_rules.items() if rule.ismatch(target)]
        if len(matches)==1:
            return cls.pattern_rules[target].specialise(target)
        eif len(matches)==0:
            raise InputError("No target found for %r" %target)
        else: #choose between matching targets
            
            return
        #this should never run
        raise LogicError("No target found for %r" %target)
    
    @class_method
    def calc_build(cls,target):
        """recursively calculate the steps needed to build for this 
        target. The resulting recipe is stored in cls.buildorder"""
        #clear working variables
        cls.buildorder = OrderedSet()
        cls._uptodate = set()
        rebuild = cls._calc_build(target)
        return rebuild
    
    @class_method
    def _calc_build(cls,target):
        """recursively calculate the steps needed to build for this 
        target. The resulting recipe is stored in cls.buildorder"""
        targetp = pathlib.Path(target)
        target_exists = targetp.exists()
        must_build = (target in cls.PHONY) or not target_exists
        
        trgrule = cls.raw_graph.get(target,None) #search for rule - pattern matching??
        
        if not target_exists and not trgrule:
            raise InputError("No target or file found for %r" %target) 
        elif target_exists and not trgrule:
            rebuild = False # source files never need to be built
        elif trgrule in cls.buildorder: # optimisation
            rebuild = True # already processed this rule and needs rebuilding
        elif trgrule in cls._uptodate: # optimisation
            if must_build:
                cls._uptodate.remove(trgrule) # correction
                rebuild = True
            else:
                rebuild = False # already seen and up to date
        else:
            rebuild = False
            
            for dep in trgrule.order_only:
                if not pathlib.Path(dep).is_file():
                    rebuild |= cls._calc_build(dep)
            
            deps = trgrule.deps
            for dep in deps:
                rebuild |= cls._calc_build(dep)
            
            if must_build:
                rebuild = True
            elif rebuild == False: #check modification dates
                target_mtime = targetp.lstat().st_mtime
                rebuild = any(pathlib.Path(dep).lstat().st_mtime > target_mtime 
                              for dep in deps)
                #lstat() method looks dangerous but logically if a dep doesn't exist
                #or is a phony target then this code path shouldn't run anyway.
        
        if rebuild:
            cls.buildorder.add(trgrule)
        else:
            cls._uptodate.add(trgrule)
        
        return rebuild
    
    @class_method
    def build(cls):
        for rule in cls.buildorder:
            rule.build()


class ExplicitRule():
    """no wildcards or patterns in the targets or dependencies.
    Any wildcards in the dependencies are evaluated at instantiation time
    """
    def __init__(self,targets,deps,order_only,func):
        self.targets = checkinput(targets) # single target or multiple targets?
        self.deps = checkinput(deps)
        self.order_only = checkinput(order_only)
        self.all_deps = ?
        self.changed_deps = ?
        self.func = func

class MetaRule():
    ?



class SingleTargetRule(?Build):
    """This rule implements a single target with multiple dependencies. The dependencies
    can contain wildcards. However, it accepts """
    def __init__(self,targets,deps,order_only=None,func=None):
        self.targets = checksingleinput(target)
        self._deps = checkinput(deps)
        self._order_only = checkinput(order_only)
        if func: self.func = func
        
        #add rule to build
        if target is pattern?:
            self.pattern_graph[target] = self
        else:
            self.explicit_graph[target] = self
        
    
    def __call__(self,func):
        self.func = func
        return func
    
    
    def ismatch(self,target):
        """For pattern rules (including wildcards), need to check if rule is a
        match"""
        return ?
        
    def specialise(self,target):
        """For pattern rules, need to be able to create an explicit version of
        the rule for the chosen target"""
        #find pattern match
        
        #substitute into dep list
        
        return newruleinstance #explicit target
    
    def build(self):
        if hasattr(self,'func'): self.func(self)
        
    def expand_wildcards(self,seq):
        """expands wildcards in the dep names using the glob module to
        search the file system and ??an altered glob module?? to search
        the explicit rules."""
        def expand(fpath):
            matches = glob.glob(fpath) + ruleglob1(fpath,self.explicit_rules.keys())
            if len(matches) == 0: raise InputError("No matching file or rule found for %r",fpath)
            return dedup(matches)
        return itertools.chain(*(expand(fpath) for fpath in seq))
        
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


class SharedRule(?Build):
    """This rule implements a single target with multiple dependencies. The dependencies
    can contain wildcards"""
    def __init__(self,targets,deps,order_only=None,func=None):
        self.target = checksingleinput(target)
        self._deps = checkinput(deps)
        self._order_only = checkinput(order_only)
        if func: self.func = func
        
        #add rule to build
        for target in targets:
            if target is pattern?:
                self.pattern_graph[target] = self
            else:
                self.explicit_graph[target] = self
            
            if target in raw_graph:
                warnings.warn('Make takes the last defined rule for each target. Overwriting the rule for %r' %target)
            raw_graph[target] = self


class SingleTargetPatternRule(?Build):
    def __init__():
        
        
    def specialise(self,target):

    
    

 
def rule(targets,deps,order_only=None,func=None):
    """This is the general rule decorator. It should create the appropriate flavour of 
    rule from the inputs"""
    for target in targets:
        SingleTargetRule(target,deps,order_only,func):
    ?
    ?
    return chosenrule

def sharedrule(targets,deps,order_only=None,func=None):
    """This is the rule decorator with multiple targets but which should only be run 
    a single time to create all of the targets. It should create the appropriate flavour
    of rule from the inputs"""
    ?
    ?
    ?
    return chosenrule




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