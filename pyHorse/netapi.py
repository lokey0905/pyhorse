import io
import os
import sys
import time
import shutil
from config import *
from common import *
from inout  import InitIO, InOutException
from path   import split_path

FILE_BEGIN_TAG   = b'FILEBEG0'
FILE_END_TAG     = b'FILEEND0'
FILE_SIZE_TAG    = b'FILESIZE'
FILE_NAME_TAG    = b'FILENAME'
FILE_CONTENT_TAG = b'FILEDATA'
FILE_BLOCKS_TAG  = b'FILEBLKS'
FILE_SUCCESS_TAG = b'FILEGOOD'
FILE_FAIL_TAG    = b'FILEFAIL'
FILE_ABORT_TAG   = b'FILEABRT'
FILE_TAG_SIZE    = len(FILE_BEGIN_TAG)

class NetAPI:
    def __init__(self, iHandle=None, oHandle=None):
        if not iHandle:
            iHandle    = b''
        if not oHandle:
            oHandle    = iHandle
        self.iHandle   = InitIO(iHandle)
        self.oHandle   = InitIO(oHandle)
        self.savePath  = 'SavedFiles'
        self.maxSize   = 2147483647
        self.blockSize = 4096

    def recv_data(self):          return self.iHandle.read()
    def send_tag(self, tag):      self.oHandle.write(tag, True)
    def send_data(self, data):    self.oHandle.write(data)

    # send
    def send_file(self, path):
        fileName = os.path.abspath(path)
        fileSize = os.path.getsize(path)
        try:
            logging.debug('test for %s', fileName)
            open(fileName, 'rb')     # test if the file is accessible
        except Exception as e:
            logging.error('Exception while testing opening: %s %s', fileName, str(e))
            return None
        if fileSize > self.blockSize:
            fileTag, fileSend = (FILE_BLOCKS_TAG,  lambda: self.send_blocks(path),)
        else:
            fileTag, fileSend = (FILE_CONTENT_TAG, lambda: self.send_content(path),)
        fileInfo = [
            (FILE_BEGIN_TAG,   None),
            (FILE_NAME_TAG,    lambda: self.send_name(fileName),),
            (FILE_SIZE_TAG,    lambda: self.send_size(fileSize),),
            (fileTag,          fileSend,),
            (FILE_END_TAG,     None,),
        ]
        for tag, sendAction in fileInfo:
            backTag = None
            error = None
            try:
                self.send_tag(tag)
                logging.debug('waiting for response after send tag %s', tag)
                self.recv_data()
            except InOutException as e:
                logging.info('get tag %s', e.args[0])
                backTag = e.args[0]
            except socket.error as e:
                logging.error('Exception when send tag: %s %s', tag, str(e))
                return None
            except Exception as e:
                logging.error('Exception when send: %s %s', tag, str(e))
                error = FILE_ABORT_TAG
                break
            if error:
                self.send_tag(error)
                return False
            error = None
            if not sendAction: continue
            try:
                sendAction()
                logging.debug('wait for response after action')
                self.recv_data()
            except InOutException as e:
                logging.info('Exception when send action: %s %s', tag, e.args[0])
                backTag = e.args[0]
            except Exception as e:
                logging.error('Exception: %s', str(e))
                error = FILE_ABORT_TAG
                break
            if error:
                self.send_tag(error)
                return False
            if backTag != FILE_SUCCESS_TAG:
                return False
        return True
    def send_content(self, fileName):
        logging.debug('send content %s', fileName)
        try:
            filedata = open(fileName, 'rb').read()
            self.send_data(filedata)
        except Exception as e:
            logging.error('send_content.Exception: %s', str(e))
            raise
        return len(filedata)
    def send_success(self):       self.send_tag(FILE_SUCCESS_TAG)
    def send_fail(self):          self.send_tag(FILE_FAIL_TAG)
    def send_abort(self):         self.send_tag(FILE_ABORT_TAG)
    # receive
    def recv_file(self):
        receiver = {
            FILE_NAME_TAG:    self.recv_name,
            FILE_SIZE_TAG:    self.recv_size,
            FILE_CONTENT_TAG: self.recv_content,
            FILE_BLOCKS_TAG:  self.recv_blocks,
        }
        result  = {}
        while True:
            tag = None
            logging.debug('wait for tag')
            try:
                data        =  self.recv_data()
                if data is None: break
                continue
            except InOutException as e:
                tag         = e.args[0]
            except socket.error:
                logging.error('Exception: %s', str(e))
                raise
            except Exception as e:
                logging.error('Exception: %s', str(e))
                break
            logging.debug('get tag: %s', tag)
            if not tag: continue
            elif tag == FILE_BEGIN_TAG:
                result = {}
                logging.debug('send success after get tag')
                self.send_success()
                continue
            elif tag == FILE_END_TAG:
                logging.debug('send success after get tag')
                self.send_success()
                break
            elif tag == FILE_ABORT_TAG:
                logging.debug('abort')
                result = {}
                continue
            self.send_success()
            try:
                logging.debug('wait for receive data')
                data = receiver.get(tag, (lambda : None))()
                if data is None: break
                result[tag] = data
                logging.debug('send success after receive data')
                self.send_success()
                continue
            except InOutException as e:
                tag         = e.args[0]
                break
            except socket.error:
                raise
            except Exception as e:
                logging.error('Exception: %s', str(e))
                break
            if tag: break
            logging.debug('send fail after data')
            self.send_fail()
        if not result:
            result = None
        return result
    def recv_verify(self, result):
        essential_flag = {FILE_NAME_TAG:1,    FILE_SIZE_TAG:2,
                          FILE_CONTENT_TAG:4, FILE_BLOCKS_TAG:4}
        flag = sum([essential_flag.get(x) for x in result.keys()])
        if flag != 7: result = None
        return result
    def recv_size(self):
        size = self.recv_data()
        if not isinstance(size, int):
            raise TypeError('invalid size type %s' % type(size))
        logging.debug('filesize: %s', size)
        return size
    def recv_name(self):
        path = self.recv_data()
        if not isinstance(path, str):
            raise TypeError('invalid name type %s' % type(path))
        namelist = path.split('\t')
        if '..' in namelist:
            raise ValueError('dangerous path')
        name = os.path.join(*namelist)
        logging.debug('filename: %s', name)
        return name
    def send_blocks(self, fileName):
        logging.debug('send blocks %s', fileName)
        fp        = open(fileName, 'rb')
        blockID   = 0
        totalSize = 0
        while True:
            block      = fp.read(self.blockSize)
            if not block: break
            blockID   += 1
            self.send_data(blockID)
            self.send_data(block)
            totalSize += len(block)
            backID     = self.recv_data()
            if backID != blockID:
                self.send_fail()
                break
        self.send_data(0)
        return totalSize
    def send_size(self, n):
        return self.send_data(n)
    def send_name(self, path):
        fileName = '\t'.join(split_path(path))
        return self.send_data(fileName)
    def recv_content(self):
        data = self.recv_data()
        if not isinstance(data, bytes):
            raise TypeError('invalid content type %s' % type(data))
        return data
    def recv_blocks(self):
        totalSize   = 0
        lastBlockID = 0
        fileName = os.path.abspath(os.path.join(self.savePath, 'TEMP%x' % int(time.time())))
        dirname  = os.path.dirname(fileName)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        with open(fileName, 'wb') as fp:
            while True:
                blockID = self.recv_data()
                if not isinstance(blockID, int):
                    raise TypeError('invalid type of block id %s' % type(blockID))
                if blockID == 0:  # end of block
                    break
                if lastBlockID + 1 != blockID:
                    raise ValueError('block ID error last:%d current:%d' % (lastBlockID, blockID))
                lastBlockID = blockID
                block   = self.recv_data()
                if not isinstance(block, bytes):
                    raise TypeError('invalid type of block %s' % type(blockID))
                if len(block) + totalSize > self.maxSize:
                    raise RuntimeError('exceed max file size limit')
                fp.write(block)
                self.send_data(blockID)
        return fileName
    def close(self):
        self.iHandle.close()
        self.oHandle.close()

def save_file(fileInfo, target):
    fileName = fileInfo.get(FILE_NAME_TAG)
    fileSize = fileInfo.get(FILE_SIZE_TAG)
    content  = fileInfo.get(FILE_CONTENT_TAG)
    tempFile = fileInfo.get(FILE_BLOCKS_TAG)
    if not fileName:
        logging.debug('invalid filename: %s', fileName)
        return False
    if not fileSize:
        logging.debug('invalid filename: %d', fileSize)
        return False
    if content or tempFile:
        fullName = os.path.join(target, fileName)
        dirname  = os.path.dirname(fullName)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        if content:
            logging.debug('save content')
            if len(content) != fileSize:
                raise RuntimeError('size unmatched')
            with open(fullName, 'wb') as fp:
                fp.write(content)
        else:
            logging.debug('save blocks from %s to %s', tempFile, fullName)
            if os.path.getsize(tempFile) != fileSize:
                raise RuntimeError('size unmatched')
            shutil.move(tempFile, fullName)
        return True
    else:
        return False
