from __future__ import annotations

import collections
import itertools
import socket
import struct
from typing import Optional

from .core import SocketReader, SocketWriter


MAX_IDS = [
    (code, *struct.unpack_from(code, b'\xff' * 8))
    for code in ['!B', '!H', '!I', '!L', '!Q']
]

def get_id_code(max_id: int) -> str:
    return next(code for code, size in MAX_IDS if size > max_id)


class Parameter:
    struct_format: str = ''

    def __init__(self, code: str):
        self.struct_format = code

    def parse(self, reader, parsed_values):
        return next(parsed_values)

    def pack(self, value):
        return (value,), []


class MultiParameter(Parameter):
    def __init__(self, code: str, size: Optional[int] = None):
        super().__init__(code)
        self.size = size if size is not None else len(code)

    def parse(self, reader, parsed_values):
        return tuple(itertools.islice(parsed_values, self.size))

    def pack(self, value):
        return value, []


class UnicodeParameter(Parameter):
    def __init__(self, code: str, max_length=0):
        super().__init__(code)

        size_bits = 8 * struct.calcsize(self.struct_format)
        self.max_length = 2**size_bits - 1
        if max_length > self.max_length:
            raise ValueError(f'Targeted maximum string length ({max_length}) greater than permitted by selected format ({self.max_length})')
        if max_length:
            self.max_length = max_length

    def parse(self, reader, parsed_values):
        size = super().parse(reader, parsed_values)
        if size > self.max_length:
            raise ValueError(f'String length received ({size}) exceeds maximum for this parameter ({self.max_length})')
        return reader.get_bytes(size).decode()

    def pack(self, value):
        value = value.encode()
        size = len(value)
        if size > self.max_length:
            raise ValueError(f'String length supplied ({size}) exceeds maximum for this parameter ({self.max_length})')
        return (size,), [value]


P_BOOL = Parameter('?')

P_INT8 = Parameter('b')
P_UINT8 = Parameter('B')
P_INT16 = Parameter('h')
P_UINT16 = Parameter('H')
P_INT32 = Parameter('l')
P_UINT32 = Parameter('L')
P_INT64 = Parameter('q')
P_UINT64 = Parameter('Q')

P_FLOAT16 = Parameter('e')
P_FLOAT32 = Parameter('f')
P_DOUBLE = P_FLOAT64 = Parameter('d')

P_UNICODE8 = UnicodeParameter('B')
P_UNICODE16 = UnicodeParameter('H')
P_UNICODE32 = UnicodeParameter('L')
P_UNICODE64 = UnicodeParameter('Q')


class Message:
    def __init__(self, message_id: int, message_name: str, **parameters: Parameter):
        self.message_id = message_id
        self.message_name = message_name
        self.parameters = parameters

        self.struct_format = self.compile_parameters()

        fields = ['message_id'] + list(self.parameters)
        self.factory = collections.namedtuple(self.message_name, fields)

    def __call__(self, **kw):
        return self.factory(self.message_id, **kw)

    def __eq__(self, other):
        try:
            return self.message_id == other.message_id
        except AttributeError:
            return super().__eq__(other)

    def compile_parameters(self):
        _f = ''.join(p.struct_format for p in self.parameters.values())
        return struct.Struct('!' + _f)

    def serialize(self, instance):
        struct_args = []
        special_args = []

        for i, p in enumerate(self.parameters.values(), start=1):
            standard, special = p.pack(instance[i])
            struct_args.extend(standard)
            special_args.extend(special)

        return self.struct_format.pack(*struct_args) + b''.join(special_args)

    def deserialize(self, reader: StructReader):
        initial_bytes = reader.get_bytes(self.struct_format.size)
        struct_args = iter(self.struct_format.unpack(initial_bytes))
        return self.factory(
            self.message_id,
            *(
                p.parse(reader, struct_args)
                for p in self.parameters.values()
            )
        )


class StructReader(SocketReader):
    def __init__(self, sock: socket.socket, message_types: list[Message], max_id: Optional[int] = None):
        self.sock = sock
        self.message_types = {m.message_id: m for m in message_types}
        max_id = max_id or max(self.message_types)
        self.id_format = struct.Struct(get_id_code(max_id))

    @classmethod
    def get_factory(cls, message_types, max_id=None):
        def get_struct_reader(sock):
            return cls(sock, message_types, max_id)

        return get_struct_reader

    def __next__(self):
        message_id, = self.id_format.unpack(self.get_bytes(self.id_format.size))
        return self.message_types[message_id].deserialize(self)

    def get_bytes(self, total: int, chunk: int = 4096):
        received = 0
        parts = []
        while received < total:
            part = self.sock.recv(min(total - received, chunk))
            if not part:
                raise socket.error if received else StopIteration

            parts.append(part)
            received += len(part)

        return b''.join(parts)

    def close(self):
        self.sock.close()


class StructWriter(SocketWriter):
    def __init__(self, sock: socket.socket, message_types: list[Message], max_id: Optional[int] = None):
        self.sock = sock
        self.message_types = {m.message_id: m for m in message_types}
        max_id = max_id or max(self.message_types)
        self.id_format = struct.Struct(get_id_code(max_id))

    @classmethod
    def get_factory(cls, message_types, max_id=None):
        def get_struct_writer(sock):
            return cls(sock, message_types, max_id)

        return get_struct_writer

    def send(self, message):
        message_id = message[0]
        packed = self.message_types[message_id].serialize(message)
        self.sock.sendall(self.id_format.pack(message_id))
        self.sock.sendall(packed)

    def close(self):
        self.sock.close()
