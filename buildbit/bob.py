#!/usr/bin/env python2
"""a simple build system inspired by gnu make"""

from orderedset import OrderedSet
#import pathlib
import os.path
import warnings
import glob
import itertools
import inspect
from types import StringTypes
from collections import Iterable
import subprocess
#from sys import maxint

import fpmatch
from utils import *

# Choose cached_property implementation
#cached_property = reify # very cool and efficient but can't reset
#cached_property = property # not strictly correct as dependency expansions shouldn't change during a build.
#cached_property = cached_property #can be reset by doing class.method.reset_cache()

warnings.filterwarnings(action='always')

# Force warnings.warn() to omit the source code line in the message
formatwarning_orig = warnings.formatwarning
#warnings.formatwarning = lambda message, category, filename, lineno, line=None: \
#    formatwarning_orig(message, category, os.path.basename(filename), lineno, line='')


class BaseRule(object):
    """Acts as a base class and contains the cached get_mtime method for getting
    a file's modification time."""
    
    #required class attribute
    #rules = {} # class level dict of target to class instances for creating a search registry.
    
    #example minimal init
    #def __init__(self,targets,func=None):
    #   self.targets = checkseq(targets) # sequence of paths (strings)
    #   if func: self.func = func
    
    @classmethod
    def get(self):
        raise NotImplementedError
    
    @classmethod
    def reset_cache(cls):
        cls.get_mtime.cache = {}
    
    def __call__(self,func):
        """a rule instance can be used as a decorator on the build recipe function.
        returns the function unchanged (so that it can be decorated by multiple rules"""
        self.func = func
        return func
    
    def __repr__(self):
        return '<%s.%s(targets=%r...) at %s>' %(self.__module__,self.__class__.__name__,self.targets,hex(id(self)))
    
    def build(self):
        raise NotImplementedError
        
    def calc_build(self):
        raise NotImplementedError
    
    @staticmethod
    @memoize
    def get_mtime(fpath):
        return os.path.getmtime(fpath)

# Explicit/Shared rules
#-------------------------------------------------------------------------------

## rules where those with multiple targets are still only run once.
##------------------------------------------------------------------------------

class ExplicitRule(BaseRule):
    """A multiple target, multiple prerequisite rule that will only run
    once no matter how many of the specified targets are required. There
    shouldn't be any wildcards in the targets and reqs lists. reqs can
    contain duplicates and be order dependent though.
    
    This class can also be used as a decorater around the desired build function.
    """
    rules = {} #target:rule dict
    
    @classmethod
    def get(cls,target,default=None):
        """Find any explicit rules for the given target."""
        return cls.rules.get(target,default)
    
    @classmethod
    def reset_cache(cls):
        for method in cls._oldest_target, cls.updated_only:
            method.reset_cache()
        #cls.calc_build.cache = {}
    
    def __init__(self,targets,reqs,order_only=None,func=None,PHONY=False,register=True):
        """targets - list of targets
        reqs - seq of prerequisites
        order_only - seq of order only prerequisites
        func - a function that should take one or no arguments. Will be
            passed this class instance when run in order to have access
            to its attributes
        PHONY - rule that should always be run (and probably won't 
            create a file with the name of the target)
        register - add new rule to class registry (normally this should be true)
        """
        self.targets = checkseq(targets)
        self.PHONY = PHONY
        self.allreqs = checkseq(reqs)
        self.reqs = dedup(self.allreqs)
        self.order_only = checkseq(order_only)
        if func: self.func = func
        #self.updated_only = self.updated_only()
        
        #Add self to class level registry
        if register:
            for target in self.targets:
                if target in self.rules:
                    warnings.warn('ExplicitRules takes the last defined rule for each target. Overwriting the rule for %r' %target,stacklevel=2)
                self.rules[target] = self
    
    def build(self):
        """run recipe"""
        if hasattr(self,'func'):
            if isinstance(self.func,StringTypes):
                cmd = self.cmd_action(self.func)
                subprocess.check_call(cmd,shell=True)
            elif isinstance(self.func,list):
                cmd = self.cmd_action(self.func)
                subprocess.check_call(cmd,shell=False)
            elif callable(self.func):
                func_argspec = inspect.getargspec(self.func)
                func_args = func_argspec[0]
                if len(func_args)==1:
                    self.func(self)
                elif len(func_args)==0:
                    self.func()
                else:
                    raise AssertionError("Unable to use a rule function that takes more than one argument. rule: %r" %self.targets)
            else:
                warnings.warn("ExplicitRule %r doesn't have a recognised type of build function attached." %self,stacklevel=2)
    
    def cmd_action(self,cmd):
        """expands the command line string using the rule's attributes"""
        #convert sequences into comma separate strings or space separated strings?
        param = {'targets':' '.join(self.targets),
                 'allreqs':' '.join(self.allreqs),
                 'reqs':' '.join(self.reqs),
                 'order_only':' '.join(self.order_only),
                 'updated_only':' '.join(self.updated_only),
                 'self':self}
        param2 = {'$@':param['targets'],
                 '$^':param['reqs'],
                 '$<':self.reqs[0] if len(self.reqs) else '',
                 '$?':param['updated_only'],
                 '$+':param['allreqs'],
                 '$|':param['order_only'],
                 }
        param.update(param2)
        if hasattr(self,'stems'): param['stems'] = self.stems
        
        if isinstance(cmd,StringTypes):
            fullcmd = cmd.format(**param)
        elif isinstance(cmd,Iterable):
            fullcmd = [part.format(**param) for part in cmd]
        return fullcmd
    
    @cached_property
    def _oldest_target(self):
        exists = os.path.exists
        ancient_epoch = 0 #unix time
        return min((self.get_mtime(target) if exists(target) else ancient_epoch) for target in self.targets )
    
    @cached_property
    def updated_only(self):
        """makes a list of the reqs which are newer than any of the targets"""
        oldest_target = self._oldest_target
        updated_reqs = [req for req in self.reqs if not os.path.exists(req) or self.get_mtime(req) > oldest_target]
        return updated_reqs
    
    #@memoize 
    def calc_build(self,_seen=None):
        """decides if it needs to be built by recursively asking it's prerequisites
        the same question.
        _seen is an internal variable (a set) for optimising the search. I'll be relying 
        on the set being a mutable container in order to not have to pass it explicitly 
        back up the call stack."""
        #There is an oportunity to optimise calculations to occur only once for rules that are called multiple
        #times by using a shared (global) buildseq + _already_seen set, or by passing those structures into
        #the calc_build method call.
        #i.e. if (self in buildseq) or (self in _already_seen): return buildseq
        #Or we can memoize this method
        
        #updated_only should be calculated during build calculation time (rather than build time) for consistancy.
        self.updated_only #force evaluation of lazy property
        
        buildseq = OrderedSet()
        _seen = set() if not _seen else _seen
        _seen.add(self) # this will also solve any circular dependency issues!
        
        for req in self.order_only:
            if not os.path.exists(req):
                reqrule = Rule.get(req,None) #super(ExplicitRule,self).get(req,None)
                if reqrule:
                    if reqrule not in _seen:
                        buildseq.update(reqrule.calc_build())
                    else:
                        warnings.warn('rule for %r has already been processed' %req,stacklevel=2)
                else:
                    warnings.warn('%r has an order_only prerequisite with no rule' %self,stacklevel=2)
        
        for req in self.reqs:
            reqrule = Rule.get(req,None) #super(ExplicitRule,self).get(req,None)
            if reqrule:
                if reqrule not in _seen:
                    buildseq.update(reqrule.calc_build())
                else:
                    warnings.warn('rule for %r has already been processed' %req,stacklevel=2)
            else: #perform checks
                try:
                    self.get_mtime(req) #get_mtime is cached to reduce number of file accesses
                except OSError as e:
                    raise AssertionError("No rule or file found for %r for targets: %r" %(req,self.targets))
            
        if len(buildseq)==0:
            if self.PHONY or any([not os.path.exists(target) for target in self.targets]):
                buildseq.add(self)
            else:
                oldest_target = self._oldest_target
                
                #Since none of the prerequisites have rules that need to update, we can assume
                #that all prerequisites should be real files (phony rules always update which
                #should skip this section of code). Hence non-existing files imply an malformed build
                #file.
                for req in self.reqs:
                    try: 
                        req_mtime = self.get_mtime(req)
                        if req_mtime > oldest_target:
                            buildseq.add(self)
                            break
                            
                    except OSError as e: 
                        raise AssertionError("A non file prerequisite was found (%r) for targets %r in wrong code path" %(req,self.targets))
        else:
            buildseq.add(self)
        
        return buildseq


class ExplicitTargetRule(ExplicitRule):
    """A multiple target, multiple prerequisite rule where the targets mustn't
    contain wildcards but the reqs list can.
    """
    #rules = {} # uses ExplicitRule's rule registry to avoid having duplicate rules
    
    @classmethod
    def reset_cache(cls):
        ExplicitRule.reset_cache()
        for method in cls.allreqs, cls.reqs, cls.order_only:
            method.reset_cache()
    
    def __init__(self,targets,reqs,order_only=None,func=None,PHONY=False,register=True):
        """targets - list of targets
        reqs - seq of prerequisites
        order_only - seq of order only prerequisites
        func - a function that should take one or no arguments. Will be
            passed this class instance when run in order to have access
            to its attributes
        PHONY - rule that should always be run (and probably won't 
            create a file with the name of the target)
        register - add new rule to class registry (normally this should be true)
        """
        self.targets = checkseq(targets)
        self.PHONY = PHONY
        self._allreqs = checkseq(reqs)
        self._order_only = checkseq(order_only)
        if func: self.func = func
        #self.updated_only = self.updated_only()
        
        #Add self to class level registry
        if register:
            for target in self.targets:
                if target in self.rules:
                    warnings.warn('ExplicitRules takes the last defined rule for each target. Overwriting the rule for %r' %target,stacklevel=2)
                self.rules[target] = self
    
    #delay expansion because we can only do it after all of the build rules have been defined
    
    @cached_property
    def allreqs(self):
        return list(itertools.chain(*[self.expand_wildcard(req) for req in self._allreqs]))
    
    @cached_property
    def reqs(self):
        return dedup(self.allreqs)
    
    @cached_property
    def order_only(self):
        return list(itertools.chain(*[self.expand_wildcard(req) for req in self._order_only]))
    
    @classmethod
    def expand_wildcard(self,fpath):        
        """Uses the glob module to search the file system and an altered glob module - fpmatch
        to search the meta rules.
        """
        matches = glob.glob(fpath)
        if fpmatch.has_magic(fpath): 
            matches += fpmatch.filter(self.rules.iterkeys(),fpath)
        else: matches += [fpmatch.strip_specials(fpath)] #can still have single escaped chars in sets when magic==False
        if len(matches) == 0: raise AssertionError("No matching file or rule found for %r" %fpath)
        return dedup(matches)


# Meta/Pattern rules
#-------------------------------------------------------------------------------

class MetaRule(BaseRule):
    """The base class for rules that contain wildcards or patterns in their targets.
    This shouldn't be used directly.
    
    I have resisted the impulse to make MetaRule a descendent of ExplicitRule since it
    performs a different role. MetaRules should never be directly included in the
    build order, instead MetaRules generate Explicit rules (which are then added to the
    build order). 
    """
    # define these in each subclass. - Doing it this way allows us to define the search order hierarchy.
    #rules = {} # compiled regular expression of target: meta_rule
    #_instantiated_rules = {} # cache of instantiated explicit rules
    #_pattern_rankings = {} # registry of the 'lengths' of the wildcard targets.
    
    @classmethod
    def get(cls,target,default=None,extratargetpath=''):
        """get the best matched rule for the target from the registry of metarules
        target - target filepath string.
        default - response if no match is found.
        extratargetpath - used by PatternRule.
        """
        #optimisation
        rule = cls._instantiated_rules.get(target,None)
        if rule: 
            return rule
        #else search metarules
        matches = [regex for regex in cls.rules.keys() if regex.match(target)]
        #choose best
        if len(matches) == 1:
            match = matches[0]
        elif len(matches) > 1:
            # find longest matching pattern (explicit part only) using _pattern_rankings dict
            i = argmax(self._pattern_rankings[regex] for regex in matches)
            match = matches[i]
        else:
            match = None
        #create the desired explicit rule
        if match:
            metarule = cls.rules[match]
            fulltarget = os.path.join(extratargetpath,target)
            newrule = metarule.individuate(fulltarget,match)
            cls._instantiated_rules[fulltarget] = newrule #cache the individuated rule
            return newrule
        else:
            return default
    
    def __init__(self,targets,reqs,order_only=None,func=None,PHONY=False):
        """targets - list of targets
        reqs - seq of prerequisites
        order_only - seq of order only prerequisites
        func - a function that should take one or no arguments. Will be
            passed this class instance when run in order to have access
            to its attributes.
        """
        self.targets = checkseq(targets)
        self.PHONY = PHONY
        self.allreqs = checkseq(reqs)
        self.order_only = checkseq(order_only)
        
        self.explicit_rules = [] #each meta_rule remembers its explicit rules. 
        self._func = func
        
        #Add self to registry of rules
        wild_targets = fpmatch.only_wild_paths(targets)
        self.re_targets = [fpmatch.precompile(pattern) for pattern in wild_targets]
        for regex in self.re_targets:
            self.rules[regex] = self
        
        #calculate pattern lengths
        rankings = [len(fpmatch.strip_specials(pattern)) for pattern in wild_targets]
        for regex,rank in zip(self.re_targets,rankings):
            self._pattern_rankings[regex] = rank
    
    def individuate(self,target,regex):
        """updates the explicit rule for the target. Will raise Error
        if the target is incompatible with the metarule."""
        raise NotImplementedError
        
    def ismatch(self,target):
        """decides if the target is a match for this metarule."""
        for pattern in self.re_targets:
            if pattern.match(target):
                return True
        return (target in fpmatch.only_explicit_paths(self.targets))
    
    @property
    def func(self):
        return self._func

    #this allows us to have late binding of the build function to the rule instance
    @func.setter
    def func(self,newfunc):
        self._func = newfunc
        for explicit_rule in self.explicit_rules:
            explicit_rule.func = newfunc


## rules where those with multiple targets are still only run once.
##------------------------------------------------------------------------------

class WildSharedRule(MetaRule):
    """A multiple target, multiple prerequisite rule where the targets and the
    reqs can both contain wildcards. The rule will only run once no matter how
    many different targets ask for it to run. The targets attribute will be 
    updated to contain each target that requests it.
    """
    rules = {} # compiled regular expression of target: meta_rule
    _instantiated_rules = {} # cache of instantiated explicit rules
    _pattern_rankings = {} # registry of the 'lengths' of the wildcard targets.
    
    @classmethod
    def reset_cache(cls):
        cls._instantiated_rules = {}
    
    def __init__(self,targets,reqs,order_only=None,func=None,PHONY=False):
        """targets - list of targets
        reqs - seq of prerequisites
        order_only - seq of order only prerequisites
        func - a function that should take one or no arguments. Will be
            passed this class instance when run in order to have access
            to its attributes
        """
        super(WildSharedRule,self).__init__(targets,reqs,order_only,func,PHONY)
        #check parameters
        pass
        
        # A single ExplicitRule will shared between all targets.
        explicit_targets = fpmatch.only_explicit_paths(targets)
        self.explicit_rules = [ExplicitTargetRule(targets=explicit_targets,
                                        reqs=reqs,order_only=order_only,
                                        func=self.func,PHONY=self.PHONY)]
        #only one rule is defined but we store it in the explicitrules list for
        #compatibility with the parent object's func getter/setter descriptors.
        
        #Nb. the explicit targets are add to the ExplicitRule registry as normal.
    
    def individuate(self,target,regex):
        """updates the explicit rule for the target. Will raise an Error
        if the target is incompatible with the metarule"""
        #check target parameter
        
        
        #Adding new target to explicit rule's target attribute.
        erule = self.explicit_rules[0]
        erule.targets = dedup(erule.targets + [target])
        
        #Nb. This requested target isn't added to the ExplicitRule rule registry since 
        # that would make the build calculation order dependent/non-deterministic. 
        # Instead we add the rule to a class attribute dict (this is done by get() class method).
        
        #Last problem, old version of rule may already be in the build orderedset and I've just mutated the object?
        # python uses the id() of an object for its hash if no __hash__ method is defined, therefore the object can
        # be mutated without issue. 
        return erule


## rules for which those with multiple targets are shorthand for multiple individual rules.
##-----------------------------------------------------------------------------------------

class WildRule(MetaRule):
    """A meta rule that can specialise to an explicit rule. It takes wildcards and
    in the target and req lists. Multiple targets lead to individualised explicit 
    rules."""
    rules = {} # compiled regular expression of target: meta_rule
    _instantiated_rules = {} # cache of instantiated explicit rules
    _pattern_rankings = {} # registry of the 'lengths' of the wildcard targets.
    
    @classmethod
    def reset_cache(cls):
        cls._instantiated_rules = {}
    
    def __init__(self,targets,reqs,order_only=None,func=None,PHONY=False):
        """targets - list of targets
        reqs - seq of prerequisites
        order_only - seq of order only prerequisites
        func - a function that should take one or no arguments. Will be
            passed this class instance when run in order to have access
            to its attributes.
        """
        super(WildRule,self).__init__(targets,reqs,order_only,func,PHONY)
        #Check parameters
        pass
        
        #Some of the targets may be explicit, in which case we can just directly create ExplicitRules as normal
        explicit_targets = fpmatch.only_explicit_paths(targets)
        #saving references to explicit rules to allow us to have late-binding of the build func
        self.explicit_rules = [
            ExplicitTargetRule(targets=target,reqs=reqs,order_only=order_only,func=self.func,PHONY=self.PHONY)
            for target in explicit_targets]
    
    def individuate(self,target,regex):
        """creates an explicit rule for the target. Will raise an error
        if the target is incompatible with the metarule"""
        #check target
        
        #expanding wildcards in reqs        
        newrule = ExplicitTargetRule(targets=target,reqs=self.allreqs,order_only=self.order_only,
                                func=self.func,PHONY=self.PHONY,register=False)
        #we set register to false as we do not want this rule to be added to the
        #ExplicitRule registry as that would make the build order dependent.
        return newrule


class PatternRule(MetaRule):
    """A meta rule that can specialise to an explicit rule. It takes wildcards and
    patterns in the target and req lists. Multiple targets lead to individualised
    explicit rules.
    """
    rules = {}
    _instantiated_rules = {} # cache of instantiated explicit rules
    _pattern_rankings = {} # registry of the 'lengths' of the wildcard targets.

    @classmethod
    def reset_cache(cls):
        cls._instantiated_rules = {}
        
    @classmethod
    def get(cls,target,default=None):
        """get the best matched rule for the target from the registry of pattern rules
        """
        newrule = super(PatternRule,cls).get(target,None)
        if newrule is None: 
            #then do a final search of pattern rules with target's directory path removed
            targetname = os.path.basename(target)
            targetpath = os.path.dirname(target)
            newrule = super(PatternRule,cls).get(targetname,default,extratargetpath=targetpath)
        return newrule


    def __init__(self,targets,reqs,order_only=None,func=None,PHONY=False):
        """Note: All targets must have at least the same number of % wildcards as the prerequisite
        with the highest number of them."""
        super(PatternRule,self).__init__(targets,reqs,order_only,func,PHONY)
        #Check parameters - PatternRules shouldn't have any entries in self.explicit_rules
        assert all(fpmatch.has_pattern(target) for target in targets)
        #counting number of % (excluding sets)
        numpat = fpmatch.count_patterns
        assert ( max([numpat(req) for req in reqs]+[numpat(req) for req in order_only])
                 <= min(numpat(target) for target in targets) )
    
    def individuate(self,target,regex):
        """creates an explicit rule for the target. Will raise an error
        if the target is incompatible with the metarule"""
        #check regex
        assert regex in self.re_targets                
        #inplace pattern substitution
        def subst_patterns(s,patterns):
            for pattern in patterns:
                s=s.replace('%',pattern,1)
            return s
        #pattern matching, finding best match
        res =regex.match(target)
        if res:
            stems = res.groups()
            ireqs = [subst_patterns(req,stems) for req in self.allreqs]
            iorder_only = [subst_patterns(req,stems) for req in self.order_only]
        else: #try matching by basename
            res = regex.match(os.path.basename(target))
            if not res:
                raise AssertionError("target doesn't match rule pattern")
            targetpath = os.path.dirname(target)
            stems = res.groups()
            ireqs = [os.path.join(targetpath,subst_patterns(req,stems)) for req in self.allreqs]
            iorder_only = [os.path.join(targetpath,subst_patterns(req,stems)) for req in self.order_only]
        
        newrule = ExplicitTargetRule(targets=target,reqs=ireqs,order_only=iorder_only,
                                func=self.func,PHONY=self.PHONY,register=False)
        #we set register to false as we do not want this rule to be added to the
        #ExplicitRule registry as that would make the build order dependent.
        newrule.stems = stems #useful attribute
        return newrule


## build system user interface
##-----------------------------------------------------------------------------------------

class ManyRules(list):
    """subclass of list type for holding several rule instances, that can also be
    used as a decorator"""
    
    def __call__(self,func):
        for rule in self:
            rule.func = func
        return func
        
    @property
    def func(self):
        return self[0].func
        
    @func.setter
    def func(self,f):
        for rule in self:
            rule.func = f


class Rule(BaseRule):
    """Acts as an interface to the build system through its methods.
    
    Also acts as a factory class for selecting and creating the appropriate rule 
    class to use. All rule instances can also be used as decorators around build 
    recipe functions (in this case leave func=None).
    
    parameters:
        targets - single target or sequence of targets
        reqs - single prerequisite or sequence of prerequisites
        order_only - single dependency or sequence of order only prerequisites
        func - the build function that should take one or no arguments. Will be
            passed this class instance when run in order to have access
            to its attributes. Alternatively could be a string or list of strings
            that will be directly run on the command line.
        PHONY - a phony rule always runs irrespective of file modification times
        shared - shared rules run their build function a single time for all of
            their targets.
    targets and reqs may contain glob patterns (see fnmatch and glob modules).
    They may also contain the '%' wildcard for defining pattern rules (like
    make).
    """
    searchorder = [ExplicitRule,WildSharedRule,WildRule,PatternRule]
        
    @classmethod
    def get(cls,target,default=None):
        """Searches for rule with matching target. Pattern matching is performed 
        and the best match is returned. So target must be explicit. If the target
        rule is not found, returns default."""
        for subcls in cls.searchorder:
            rule = subcls.get(target,default)
            if rule != default:
                break
        return rule 
        #AssertionError("No target found for %r" %target)
    
    @classmethod
    def allrules(cls):
        """returns all of the defined rules (Explicit and Meta), this is mostly for
        debugging and inspection purposes"""
        rules = []
        for subcls in cls.searchorder:
            rules+=subcls.rules.values()
        return dedup(rules)
    
    @classmethod
    def calc_build(cls,target):
        """calculate the build order to get system up to date"""    
        toprule = cls.get(target)
        if not toprule: raise AssertionError("No rule or file found for %r" %(target))
        build_order = toprule.calc_build()
        return build_order
    
    @classmethod
    def reset_cache(cls):
        """resets the memoize/cached_property/instantiated_rules caches"""
        for obj in [BaseRule,ExplicitTargetRule] + cls.searchorder:
            obj.reset_cache()
    
    @staticmethod
    def build(buildorder):
        for task in buildorder:
            task.build()
            
    def __new__(cls,targets,reqs,order_only=None,func=None,PHONY=False,shared=False):
        """selects and creates the appropriate rule class to use. All rule instances
        can also be used as decorators around build recipe functions (in this case
        leave func=None).
            targets - single target or sequence of targets
            reqs - single prerequisite or sequence of prerequisites
            order_only - single dependency or sequence of order only prerequisites
            func - the build function that should take one or no arguments. Will be
                passed this class instance when run in order to have access
                to its attributes.
            PHONY - a phony rule always runs irrespective of file modification times
            shared - shared rules run their build function a single time for all of
                their targets.
        targets and reqs may contain glob patterns (see fnmatch and glob modules).
        They may also contain the '%' wildcard for defining pattern rules (like
        make).
        """
        targets = checkseq(targets)
        reqs = checkseq(reqs)
        order_only = checkseq(order_only)
        
        if shared:
            if not any(fpmatch.has_magic(target) for target in targets):
                targets = [fpmatch.strip_specials(target) for target in targets]
                if not any(fpmatch.has_magic(req) for req in itertools.chain(reqs,order_only)):
                    reqs = [fpmatch.strip_specials(req) for req in reqs]
                    newrule = ExplicitRule(targets,reqs,order_only,func,PHONY)
                else:
                    newrule = ExplicitTargetRule(targets,reqs,order_only,func,PHONY)
            elif fpmatch.has_pattern(targets):
                raise AssertionError('shared pattern rule type not written yet')
            else: #wildcard targets
                newrule = WildSharedRule(targets,reqs,order_only,func,PHONY)
        else:
            if not any(fpmatch.has_magic(target) for target in targets):
                targets = [fpmatch.strip_specials(target) for target in targets]
                if not any(fpmatch.has_magic(req) for req in itertools.chain(reqs,order_only)):
                    reqs = [fpmatch.strip_specials(req) for req in reqs]
                    if len(targets)<=1:
                        newrule = ExplicitRule(targets,reqs,order_only,func,PHONY)
                    else:
                        newrule = ManyRules(ExplicitRule(target,reqs,order_only,func,PHONY) for target in targets)
                    #or maybe use WildRule??
                else:
                    if len(targets)<=1:
                        newrule = ExplicitTargetRule(targets,reqs,order_only,func,PHONY)
                    else:
                        newrule = ManyRules(ExplicitTargetRule(target,reqs,order_only,func,PHONY) for target in targets)
                    #or maybe use WildRule??
            elif any(fpmatch.has_pattern(target) for target in targets): 
                #in fact all targets should have a pattern wildcard but error checking will occur in class.
                newrule = PatternRule(targets,reqs,order_only,func,PHONY)
            else: #wildcard targets
                newrule = WildRule(targets,reqs,order_only,func,PHONY)
        
        return newrule

    @staticmethod
    def main():
        """command line interface for buildbit system"""
        import argparse

        parser = argparse.ArgumentParser(description='The buildbit build system (a python version of make)')
        parser.add_argument('target',default='All',help='select build target')
        parser.add_argument('-n','--dry-run',dest='dryrun',action='store_true',help='only print build sequence')
        args = parser.parse_args()
        
        print 'Building target:', args.target
        buildseq = Rule.calc_build(args.target)
        if args.dryrun:
            print 'Build sequence:'
            for item in buildseq: print item
        else:
            print 'Build sequence:'
            for item in buildseq: print item
            Rule.build(buildseq)

