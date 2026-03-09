from collections import namedtuple
from contextlib import contextmanager
from hashlib import blake2s

def __(**kwargs):
    return kwargs

def _(**kwargs):
    return kwargs

def _t(**kwargs):
    field_keys =[ k  for k in  kwargs.keys() if k[0] != "_" ] 

    keys = tuple(sorted(field_keys))
    name = "t" + blake2s(",".join(keys).encode("utf-8"), digest_size=2).hexdigest()    

    _args =  dict([ (k,v)  for k,v in  kwargs.items() if k[0] == "_" ])
    skip_list = [] 
    for a,v in _args.items():
        if a == "_skip":
            skip_list =  v 
        if a == "_name":
            name = v 
        if a == "_rename" and  v is True :
            shouldRename = v 

            

    

    record = {}
    print(skip_list)
    for k,v in  kwargs.items():
        shouldSkip =  len(skip_list) > 0 and k in skip_list

        if k[0] == "_" : 
            continue 
        if type(v) is dict: 
            print(k , k in skip_list , shouldSkip, skip_list)
            if shouldSkip is False: 
                record[k] = _t(**v)  if v != {}  else None
            else: 
                record[k] = v 
            continue 
            
        if type(v) is list:
            arr = []
            for el in v:                 
                if type(el) is dict:
                    el = _t(**el)  if v != {}  else None
                arr.append(el)
            record[k] = arr 
            continue 

        record[k] = v 


    
    t = namedtuple(name,record.keys()) 
    return t(**record)

def meld(t :tuple) -> dict:
    return {t.k :  t.v }

def uref(ref,value,data):    
    data = data.copy()    
    d = data
    keys=ref.split(".")
    for idx,k in enumerate(keys):
        if idx == len(keys) - 1 :
            d[k]  = value 
        d = d[k]
    return data 


import inspect 
def _print(a, indent=0):
    
    if not isinstance(a, tuple):
        raise ValueError("Is not a tuple",type(a), a )
    for k ,v in a._asdict().items():
        if isinstance(v,tuple):
            print("  "*indent, f"{k}:" )
            _print(v,indent + 1 )
            continue 
        if isinstance(v,dict):
            print("  "*indent, f"{k}: {str(v)[:200]}..." )
            continue 
        if isinstance(v,list):
            print("  "*indent, f"{k}: [ " )
            for index,el in  enumerate(v):
                if isinstance (el, tuple):
                    _print(el, indent + 1 )
                else: 
                    print("  "*(indent + 1) ,f"{str(v)[:200]}..." )
            print("  "*(indent+1), "]" )
            continue         
        print("  "*indent, f"{k}: {str(v)}" )
    
    


def dict_to_namedtuple(name, d):    
    NT = namedtuple(name, d.keys())    
    return NT(**d)    


@contextmanager
def tupler(name):    
    def fn0(**kwargs):
        d = kwargs 
        NT = namedtuple(name, d.keys())    
        return NT(**d)    
    yield fn0


import re
def deref2(data,k):
    def regex_match_keys(pattern, snippet):
        # m = re.match(pattern, k, re.IGNORECASE)
        # print("pattern={pattern},text={k}" , m)
        
        return next(
            (k for k in snippet if (m := re.search(pattern, k, re.IGNORECASE))),
            None,
        )
    
    parts = k.split(".")
    current = data
    last_key = None 
    for el in parts:
        m = regex_match_keys(el,current)
        if m is None:
            with tupler("kv") as _:
                return  _( k = last_key , v  = None )
        
        el = m 
        last_key = el 
        
        current = current[el]
    with tupler("kv") as _:
        return  _( k = last_key , v  = current )
    