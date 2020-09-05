import sys
import logging
# logging.basicConfig(level=logging.DEBUG)

class Output:
    def __init__(self, mode=True):
        self.silentMode = mode
    def __call__(self, *args, **kwargs):
        if not self.silentMode:
            print(*args, **kwargs)
            sys.stdout.flush()
    def set(self, mode):
        self.silentMode = mode

def thread_refresh(threads, result=None):
    if not result:
        result = []
    elif not isinstance(result, (list, tuple)):
        result = [result]
    for thread in threads:
        if isinstance(thread, (list, tuple)):
            result = thread_refresh(thread, result)
            continue
        thread.join(0.1)
        if thread.is_alive():
            result.append(thread)
    return result

