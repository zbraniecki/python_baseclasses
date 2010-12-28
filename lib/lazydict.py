'''
LazyDict is a subclass of a dict that can additionally store
items in a form of a stub that is expanded on the first call.

Such class may be useful in all cases where dictionary items
are expensive to initialize and on average an application
is using only some of the elements of the dictionary.

Example:

    def resolver(self, key, *args, **kwargs):
        print("resolving")
        table = kwargs.pop('table', None)
        return QueryValue(table=table)

    d = LazyDict({'a': 1})
    d.set_stub('b', resolver, table='items')
    
    print(len(d))                    # 2
    x = d['b']                       # resolving
    x2 = d['b']                      #
    print(isinstance(x2, QueryValue) # True

'''
from functools import partial
from collections import MutableMapping, ItemsView, ValuesView

__all__ = ["LazyDict",]

class LazyItemsView(ItemsView):

    def __iter__(self):
        self._mapping.resolve()
        for key in self._mapping:
            yield (key, self._mapping[key])


class LazyValuesView(ValuesView):

    def __iter__(self):
        self._mapping.resolve()
        for key in self._mapping:
            yield self._mapping[key]


class LazyDict(dict):
    _resolver = None

    def __init__(self, *args, **kwargs):
        super(LazyDict, self).__init__(*args, **kwargs)
        self._stubs = {}

    def __cmp__(self, other):
        self.resolve()
        return dict.__cmp__(self, other)

    def __eq__(self, other):
        self.resolve()
        return dict.__eq__(self, other)

    def __len__(self):
        return dict.__len__(self)+len(self._stubs)

    def __setitem__(self, key, item, dict_setitem=dict.__setitem__):
        if key in self._stubs:
            del self._stubs[key]
        dict_setitem(self, key, item)

    def __delitem__(self, key):
        try:
            del self._stubs[key]
        except KeyError:
            dict.__delitem__(self, key)

    def __missing__(self, key):
        try:
            stub = self._stubs.pop(key)
        except KeyError:
            raise KeyError(key)
        self[key] = s = stub()
        return s

    def __contains__(self, key):
        return dict.__contains__(self, key) or key in self._stubs

    def __iter__(self):
        for key in dict.keys(self):
            yield key
        for key in self._stubs.keys():
            yield key

    def clear(self):
        self._stubs.clear()
        dict.clear(self)

    def copy(self):
        x = self.__class__(self)
        x._stubs = self._stubs.copy()
        return x

    get = MutableMapping.get
    keys = MutableMapping.keys
    update = MutableMapping.update
    popitem = MutableMapping.popitem
    setdefault = MutableMapping.setdefault
    __repr__ = MutableMapping.__repr__


    def items(self):
        return LazyItemsView(self)

    def values(self):
        return LazyValuesView(self)

    __marker = object()
    def pop(self, key, default=__marker):
        try:
            value = self[key]
        except KeyError:
            if default is self.__marker:
                raise
            return default
        else:
            del self[key]
            return value

    def set_stub(self, key, rslv=None, *args, **kwargs):
        """
        Adds a stub of an element. It takes a callable rslv
        that will be called when the item is requested
        for the first time.

        If rslv is None, LazyDict will try to use default resolver
        provided by set_default_resolver.
        """
        if key in dict.keys(self):
            dict.__delitem__(self, key)
        self._stubs[key] = partial(rslv if rslv else self._resolver,
                                   key, *args, **kwargs)

    def resolve(self):
        """
        Resolves all stubs
        """
        try:
            while True:
                k,v = self._stubs.popitem()
                self[k] = v()
        except KeyError:
            pass

    def set_resolver(self, resolver):
        """
        Sets the default stub resolver
        """
        self._resolver = resolver


class LazyDictDebug(LazyDict):
    def __init__(self, *args, **kwargs):
        super(LazyDictDebug, self).__init__(*args, **kwargs)
        self.stats = {'realitems': 0, 'stubs': 0, 'resolved': 0}
        self.timers = {}

    def set_stub(self, key, resolver, *args, **kwargs):
        self.stats['stubs']+=1
        LazyDict.set_stub(self, key, resolver, *args, **kwargs)

    def __missing__(self, key):
        self.stats['resolved']+=1
        #start = timer()
        LazyDict.__missing__(self, key)
        #stop = timer()
        #self.timers[key] = stop-start

