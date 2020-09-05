import io
import socket
import struct
from common import *

class InOutException(Exception):
    pass

class INOUT:
    def __init__(self, handle):
        self.handle    = handle
        self.exceptTag = b'\\'
    def data_to_nbyte(self, n, exceptFlag=False):
        exceptTag = {False: b'', True:self.exceptTag}.get(exceptFlag, b'')
        if isinstance(n, int):
            if n < (1 << 8):    tag  = 'B'
            elif n < (1 << 16): tag  = 'H'
            elif n < (1 << 32): tag  = 'L'
            elif n < (1 << 64): tag  = 'Q'
            else:               tag  = 'U'
            if tag != 'U':
                n     = struct.pack('!' + tag, n)
                nbyte = tag.encode('utf-8') + n
            else:
                b     = bignum_to_bytes(n)
                nbyte = tag.encode('utf-8') + self.data_to_nbyte(len(b)) + b
        elif isinstance(n, bytes):
            tag, b  = 's', n
            nbyte = tag.encode('utf-8') + self.data_to_nbyte(len(b)) + b
        elif isinstance(n, str):
            tag, b  = 'c', n.encode('utf-8')
            nbyte = tag.encode('utf-8') + self.data_to_nbyte(len(b)) + b
        else:
            raise TypeError('data_to_nbyte: Invalid type: ' + type(tag))
        if exceptFlag: logging.debug('send exception: %s', nbyte)
        return exceptTag + nbyte

    def nbyte_to_data(self):
        size_info  = { 'B': 1, 'H': 2, 'L':4, 'Q':8 }
        valendata  = { 's': lambda n: n,
                       'c': lambda n: n.decode('utf-8'),
                       'U': lambda n: bytes_to_bignum(n), }
        btag       = self.read_raw(1)
        if not btag:
            return None
        exceptFlag = False
        if btag == self.exceptTag:
            exceptFlag = True
            btag       = self.read_raw(1)
        if not btag:
            return None
        tag          = btag.decode('utf-8')
        if tag in size_info:
            size         = size_info[tag]
            bnum         = b''
            while len(bnum) < size:
                bnum    += self.read_raw(size - len(bnum))
            result       = struct.unpack('!' + tag, bnum)[0]
        elif tag in valendata:
            size = self.nbyte_to_data()
            if size >= 65536:
                raise ValueError('length too long: ' + str(size))
            bstr         = b''
            while len(bstr) < size:
                bstr    += self.read_raw(size - len(bstr))
            # result       = bstr if tag == 's' else bstr.decode('utf-8')
            result       = valendata[tag](bstr)
        else:
            raise TypeError('nbyte_to_data: Invalid type: ' + tag)
        if exceptFlag:
            logging.debug('recv exception: %s', result)
            raise InOutException(result)
        return result
    def read(self):
        d = self.nbyte_to_data()
        return d
    def write(self, d, exceptFlag=False):
        byte_data = self.data_to_nbyte(d, exceptFlag)
        self.write_raw(byte_data)
    def read_raw(self, n):
        d = self.read_handle(n)
        return d
    def write_raw(self, d):
        return self.write_handle(d)
    def close(self):
        return self.close_handle()
    #
    def read_handle(self, n):
        return b''
    def write_handle(self, d):
        return len(d)
    def close_handle(self):
        return self.handle

class NetworkIO(INOUT):
    def read_handle(self, n):
        try:
            return self.handle.recv(n)
        except Exception as e:
            logging.debug('Exception: %s', str(e))
            raise
    def write_handle(self, d):
        try:
            return self.handle.send(d)
        except Exception as e:
            logging.debug('Exception: %s', str(e))
            raise
    def close_handle(self):
        pass

class FileIO(INOUT):
    def read_handle(self, n):
        return self.handle.read(n)
    def write_handle(self, d):
        return self.handle.write(d)

class StringIO(INOUT):
    def read_handle(self, n):
        data, self.handle = self.handle[:n], self.handle[n:]
        return data
    def write_handle(self, d):
        self.handle += d


def InitIO(handle):
    readers = {
        bytes:         StringIO,
        io.IOBase:     FileIO,
        socket.socket: NetworkIO,
    }
    return readers.get(type(handle), lambda n: None)(handle)

def bignum_to_bytes(n):
    result = b''
    while n > 0:
        b = n % 128
        n >>= 7
        if n:
            b += 128
        result += bytes([b])
    return result

def bytes_to_bignum(bs):
    result = 0
    exp    = 0
    for b in bs:
        n = b % 128
        result += n << exp
        exp += 7
        if b & (1 << 7) == 0:
            break
    return result

