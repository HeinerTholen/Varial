import re
import functools
import collections
import wrappers

class History(object):
    """
    Tracking of operations provenance.

    >>> h = History("some_op")
    >>> print str(h)
    some_op()
    >>> h.add_args(["w1", "w2"])
    >>> print str(h)
    some_op(
        w1,
        w2
    )
    >>> h.add_kws({"a_keyword": "a_value"})
    >>> print str(h)
    some_op(
        w1,
        w2,
        {'a_keyword': 'a_value'}
    )
    >>> h
    some_op(w1,w2,{'a_keyword':'a_value'})
    >>> h.add_args([History("another_op")])
    >>> print str(h)
    some_op(
        another_op(),
        {'a_keyword': 'a_value'}
    )
    """
    def __init__(self, operation):
        self.op = str(operation)
        self.args = None
        self.kws  = None

    def __str__(self):
        string = ""
        if self.args:
            for arg in self.args:
                if len(string):
                    string += ",\n"
                string += "    "
                string += str(arg).replace("\n", "\n    ")
        if self.kws:
            string += ",\n    "
            string += str(self.kws)
        if string:
            return self.op + "(\n" + string + "\n)"
        else:
            return self.op + "()"

    def __repr__(self):
        pat = re.compile(r'\s+')
        return pat.sub('', str(self))

    def add_args(self, args):
        self.args = args

    def add_kws(self, kws):
        self.kws = kws


def gen_catch_history(wrps, list_of_histories):
    """
    'Pass through' generator.
    """
    for wrp in wrps:
        if hasattr(wrp, "history"):
            list_of_histories.append(wrp.history)
        yield wrp

def track_history(func):
    """
    Python decorator for Wrapper operations.
    """
    @functools.wraps(func)
    def decorator(*args, **kws):
        history = History(func.__name__)
        if len(args):
            candidate = args[0]
            if isinstance(candidate, wrappers.Wrapper):
                history.add_args([candidate.history])
            if isinstance(candidate, collections.Iterable):
                args = list(args)
                list_of_histories = []
                args[0] = gen_catch_history(candidate, list_of_histories)
                history.add_args(list_of_histories)
        if len(kws):
            history.add_kws(kws)
        ret = func(*args, **kws)
        ret.history = history
        return ret
    return decorator


if __name__ == "__main__":
    import doctest
    doctest.testmod()


