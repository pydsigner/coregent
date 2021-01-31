import abc
import collections.abc
import socket



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
