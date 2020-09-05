import os
import stat
from common import *

def split_path(path):
    result = []
    while True:
        head, tail = os.path.split(path)
        if tail:
            result.insert(0, tail)
            path = head
        else:
            head = head.strip('/:\\')
            if head: result.insert(0, head)
            break
    return result

def scan_dir(path):
    try:
        if not isinstance(path, str): return
        if not os.path.exists(path):  return
        st = os.stat(path)
        if not(st.st_mode & stat.S_IRUSR):
            return
        if os.path.isdir(path):
            fileList = os.listdir(path)
        else:
            yield path
            return
    except Exception as e:
        logging.debug('Exception: %s %s, abort', path, str(e))
        return
    for name in fileList:
        fullpath = os.path.join(path, name)
        yield from scan_dir(fullpath)  # Python3

if __name__ == '__main__':
    print(split_path('/home/trojan/source_code/server.py'))
