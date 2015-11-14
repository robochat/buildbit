import re
import os.path
import imp

def translate(pat):
    """Translate a shell PATTERN to a regular expression.

    There is no way to quote meta-characters.
    """
    i, n = 0, len(pat)
    res = ''
    wildcard = '[^/]*' if os.path.sep is '/' else '[^/'+re.escape(os.path.sep)+']*'
    while i < n:
        c = pat[i]
        i = i+1
        if c == '*':
            res = res + wildcard
        elif c == '?':
            res = res + wildcard
        elif c == '%':
            res = res + '('+wildcard+')'
        elif c == '[':
            j = i
            if j < n and pat[j] == '!':
                j = j+1
            if j < n and pat[j] == ']':
                j = j+1
            #corner cases:
              #[] or [!] treated as literals if no later closing bracket found, 
              #if a later closing bracket is found then ']' is included in the choice set.
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


# Bring in fnmatches other functions
_fpmatch = imp.load_module('_fpmatch', *imp.find_module('fnmatch'))
_fpmatch.translate = translate #monkey patch!
from _fpmatch import *



def precompile(pat):
    """pre-compile the glob pattern into a compiled regular expression"""
    regex = translate(os.path.normcase(pat))
    return re.compile(regex)

def strip_specials(pat):
    """Strip all the special characters from a pattern. This will be used to 
    find the best match when there are multiple matching patterns.
    """
    i, n = 0, len(pat)
    res = ''
    while i < n:
        c = pat[i]
        i = i+1
        if c == '*':
            pass
        elif c == '?':
            pass
        elif c == '%':
            pass
        elif c == '[':
            j = i
            if j+1 < n and pat[j+1] == ']' and pat[j] != '!': #special case to escape (a set with only one item)
                res = res + pat[j]
                i = i+2
                continue
            if j < n and pat[j] == '!':
                j = j+1
            if j < n and pat[j] == ']':
                j = j+1
            #corner cases:
              #[] or [!] treated as literals if no later closing bracket found, 
              #otherwise ']' is included in the set of choices.
            while j < n and pat[j] != ']':
                j = j+1
            if j >= n:
                res = res + '[' #another corner case for when no close bracket is found.
            else:
                i = j+1
        else:
            res += c
    return res


meta_check = re.compile('[*?%[]') 

def has_meta(s):
    return magic_check.search(s) is not None

def has_magic(s):
    """tests whether a string contains unescaped metacharacters. This tests for the
    presence of *?% characters and any sets [...] or [!...] with the exception of
    sets that contain only a single entry (which is the only way of escaping the
    metacharacters)."""
    i, n = 0, len(s)
    res = False
    while i < n:
        c = s[i]
        i = i+1
        if c in ('*','?','%'):
            res = True
        elif c == '[':
            j = i
            if j+1 < n and s[j+1] == ']' and s[j] != '!': #special case to escape (a set with only one item)
                i = i+2
                continue
            if j < n and s[j] == '!':
                j = j+1
            if j < n and s[j] == ']':
                j = j+1
            #corner cases:
            #[] or [!] treated as literals if no later closing bracket found, 
            #otherwise ']' is included in the set of choices.
            while j < n and s[j] != ']':
                j = j+1
            if j >= n:
                pass #corner case for when no close bracket is found.
            else:
                i = j+1
                res = True
    return res

def has_pattern(s):
    """find if glob  has a rule pattern (%) wildcard.
    """
    i, n = 0, len(s)
    res = False
    while i < n:
        c = s[i]
        i = i+1
        if c == '%':
            res = True
        elif c == '[':
            j = i
            while j < n and s[j] != ']':
                j = j+1
            if j >= n:
                pass #bracket never closed so treating [ as a literal
            else:
                i = j+1
    return res


def only_explicit_paths(seq):
    return [strip_specials(path) for path in seq if not has_magic(path)]

def only_wild_paths(seq):
    return [path for path in seq if has_magic(path)]