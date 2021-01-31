import socket
from json import dumps as _j_dumps

from ijson import items as _ij_items

from .core import SocketReader, SocketWriter


class _SocketFile:
    def __init__(self, sock: socket.socket):
        self.sock = sock

    def read(self, chunk: int = 4096):
        return self.sock.recv(chunk).decode()


class JSONReader(SocketReader):
    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.processor = _ij_items(_SocketFile(sock), 'item')

    def __next__(self):
        return next(self.processor)

    def __iter__(self):
        yield from self.processor

    def close(self):
        self.sock.close()


class JSONWriter(SocketWriter):
    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.prefix = b'['

    def send(self, message):
        self.sock.sendall(self.prefix + _j_dumps(message).encode())
        self.prefix = b','

    def close(self):
        self.sock.sendall(b']')
        self.sock.close()
