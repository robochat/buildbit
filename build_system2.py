#!/usr/bin/env python2
"""a simple build system inspired by gnu make"""

"""
#TO DO
 - file path stuff
 - unit test
 - wildcards in deps
 - wildcards in targets
 - patterns
 - defaults: PHONY, patterns
 - enviroment variables (dict on make class?)
 - shortcuts for rules with simple shell command recipes
"""
from orderedset import OrderedSet
import pathlib
from collections import Iterable
from types import StringTypes

def checkinput(val):
    """replaces None with an empty tuple and wraps
    non-iterable values into a tuple too."""
    if not val: val = tuple()
    elif isinstance(val,StringTypes): val = (val,)
    elif not isinstance(val,Iterable): val = (val,)
    return val



class rule(object):

    graph = {}
    build_order = orderedSet()
    _seen = set()
    
    expired = True
    rebuild = True
    changed = True
    fresh = False
    unchanged = False
    
    
    def __new__(self,targets,phony=False,*args,**kwargs):
        #selects type of rule class ??
        targets
        phony = ?
    
    def __init__(self,targets,deps,order_only=[],func=None,**kwargs):
        self.func = func # explicit
        self.builder.graph[target] = ?
    
    def __call__(self,func): #decorator
        self.func = func
        return func 
        
    def update(self):
        if func takes a single argument: func(self)
        else func()
        
        return outofdate rebuild changed
        else
        return uptodate 
    
    @property
    def deps(self):
        ?
    
    @property
    def order_only(self):
        ?
        
    @property
    def alldeps(self):