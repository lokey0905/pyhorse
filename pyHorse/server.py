import os
import socket
import threading
import platform
import logging
from config import *
from common import *
from inout  import InOutException
from netapi import NetAPI, save_file

### change banner here ###
BANNER  = b'7RJN0001 7r0j4n 53rv3r v.0.1 r313453\r\n'
BANNER += b'********************************\r\n'
BANNER += b'*** W31c0m3 70 53nd m3 f!135 ***\r\n'
BANNER += b'********************************\r\n'
##########################

MAX_CONN = 10
target_dir = save_dir.get(platform.system())

def receive_thread(conn, addr, path):
    handler     = NetAPI(conn)
    while True:
        try:
            logging.debug('start recv_file()')
            data    = handler.recv_file()
            logging.debug('return from recv_file()')
            if not data:
                logging.debug('receive_thread: no data, break')
                break
            logging.debug('verify data')
            data    = handler.recv_verify(data)
            if not data:
                logging.debug('data imcomplete')
                continue
            filename = os.path.join(path, addr[0])
            logging.debug('save to %s', filename)
            save_file(data, filename)
        except InOutException as e:
            logging.debug('receive_thread: got exception %s', e.args)
        except socket.error as e:
            logging.debug('receive_thread: got exception %s, break', e.args)
            break
        except Exception as e:
            logging.debug('receive_thread: got exception: %s, break', str(e))
            break
    logging.debug('close connection')
    conn.close()

################
# server start #
################

def server_start(addr):
    thread_flag  = True  # False if debugging
    threads      = []
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serverSocket.bind(addr)
    serverSocket.listen(5)
    while True:
        conn, addr  = serverSocket.accept()
        logging.debug('send banner')
        conn.send(BANNER + b'\0')
        if thread_flag:
            # thread
            threads = thread_refresh(threads)
            if len(threads) < MAX_CONN:
                thread = threading.Thread(target=receive_thread, \
                                          args=(conn, addr, target_dir,))
                thread.start()
                threads.append(thread)
            else:
                conn.close()
        else:
            receive_thread(conn, addr, target_dir)
    serverSocket.close()

if __name__ == '__main__':
    server_start(('', PORT, ))
