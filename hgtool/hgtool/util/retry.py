import time
import random
from functools import wraps
from contextlib import contextmanager
import logging
log = logging.getLogger(__name__)


def retry(action, attempts=5, sleeptime=60, max_sleeptime=5 * 60,
          retry_exceptions=(Exception,), cleanup=None, args=(), kwargs={}):
    """Call `action' a maximum of `attempts' times until it succeeds,
        defaulting to 5. `sleeptime' is the number of seconds to wait
        between attempts, defaulting to 60 and doubling each retry attempt, to
        a maximum of `max_sleeptime'.  `retry_exceptions' is a tuple of
        Exceptions that should be caught. If exceptions other than those
        listed in `retry_exceptions' are raised from `action', they will be
        raised immediately. If `cleanup' is provided and callable it will
        be called immediately after an Exception is caught. No arguments
        will be passed to it. If your cleanup function requires arguments
        it is recommended that you wrap it in an argumentless function.
        `args' and `kwargs' are a tuple and dict of arguments to pass onto
        to `callable'"""
    assert callable(action)
    assert not cleanup or callable(cleanup)
    if max_sleeptime < sleeptime:
        log.debug("max_sleeptime %d less than sleeptime %d" % (
            max_sleeptime, sleeptime))
    n = 1
    while n <= attempts:
        try:
            log.info("retry: Calling %s with args: %s, kwargs: %s, "
                     "attempt #%d" % (action.__name__, str(args), str(kwargs), n))
            return action(*args, **kwargs)
        except retry_exceptions:
            log.debug("retry: Caught exception: ", exc_info=True)
            if cleanup:
                cleanup()
            if n == attempts:
                log.info("retry: Giving up on %s" % action)
                raise
            if sleeptime > 0:
                log.info("retry: Failed, sleeping %d seconds before retrying" %
                         sleeptime)
                time.sleep(sleeptime)
                sleeptime = sleeptime * 2
                if sleeptime > max_sleeptime:
                    sleeptime = max_sleeptime
            continue
        finally:
            n += 1


def retriable(*retry_args, **retry_kwargs):
    ''' A decorator for retry(). Example usage:
    @retriable()
    def foo()
        ...

    @retriable(attempts=100, sleeptime=10)
    def bar():
        ...
    '''

    def _retriable_factory(func):
        @wraps(func)
        def _retriable_wrapper(*args, **kwargs):
            return retry(func, args=args, kwargs=kwargs, *retry_args,
                         **retry_kwargs)
        return _retriable_wrapper
    return _retriable_factory


@contextmanager
def retrying(func, *retry_args, **retry_kwargs):
    @wraps(func)
    def retry_it(*args, **kwargs):
        return retry(func, args=args, kwargs=kwargs, *retry_args,
                     **retry_kwargs)
    yield retry_it


def retrier(attempts=5, sleeptime=10, max_sleeptime=300, sleepscale=1.5, jitter=1):
    for _ in range(attempts):
        log.debug("attempt %i/%i", _ + 1, attempts)
        yield
        if jitter:
            sleeptime += random.randint(-jitter, jitter)
        if _ == attempts - 1:
            # Don't need to sleep the last time
            break
        log.debug("sleeping for %.2fs (attempt %i/%i)", sleeptime, _ + 1, attempts)
        time.sleep(sleeptime)
        sleeptime *= sleepscale
        if sleeptime > max_sleeptime:
            sleeptime = max_sleeptime
