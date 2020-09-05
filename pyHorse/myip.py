import urllib.request

def myip_wan():
    url = 'http://bot.whatismyipaddress.com'
    ip  = None
    with urllib.request.urlopen(url) as fp:
        ip  = fp.read()
        if isinstance(ip, bytes):
            ip = ip.decode('utf-8')
    return ip

def myip_lan():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 53))
    ip = s.getsockname()[0]
    s.close()
    return ip

if __name__ == '__main__':
    ip = myip_wan()
    print(ip)
    ip = myip_lan()
    print(ip)
