import abc
import collections.abc
import socket
from json import dumps as _j_dumps

from ijson import items as _ij_items


__all__ = ['get_socket_type', 'get_server_socket', 'get_client_socket',
           'SocketReader', 'SocketWriter', 'JSONReader', 'JSONWriter']


def get_socket_type(host=None, ip_type=None):
    if ip_type is not None:
        return ip_type

    if host and ':' in host:
        return socket.AF_INET6

    return socket.AF_INET


def get_server_socket(host, port, ip_type=None):
    sock = socket.socket(get_socket_type(host, ip_type))
    sock.bind((host, port))
    return sock

def get_client_socket(host, port, ip_type=None):
    sock = socket.socket(get_socket_type(host, ip_type))
    sock.connect((host, port))
    return sock


class SocketReader(collections.abc.Iterator):
    @abc.abstractmethod
    def close(self):
        ...


class SocketWriter(abc.ABC):
    @abc.abstractmethod
    def send(self, message):
        ...

    @abc.abstractmethod
    def close(self):
        ...


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
