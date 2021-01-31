from __future__ import annotations

import collections
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

    def parse(self, reader, remainder):
        return remainder.pop(0)

    def pack(self, value):
        return (value,), []


class MultiParameter(Parameter):
    def __init__(self, code: str, size: Optional[int] = None):
        super().__init__(code)
        self.size = size if size is not None else len(code)

    def parse(self, reader, remainder):
        values = remainder[:self.size]
        del remainder[:self.size]
        return values

    def pack(self, value):
        return value, []


class UnicodeParameter(Parameter):
    def __init__(self, code: str):
        super().__init__(code)

    def parse(self, reader, remainder):
        size = super().parse(reader, remainder)
        return reader.get_bytes(size).decode()

    def pack(self, value):
        value = value.encode()
        return (len(value),), [value]


P_BOOL = Parameter('?')

P_BYTE = Parameter('b')
P_UBYTE = Parameter('B')
P_SHORT = Parameter('h')
P_USHORT = Parameter('H')
P_INT = Parameter('i')
P_UINT = Parameter('I')
P_LONG = Parameter('l')
P_ULONG = Parameter('L')
P_2LONG = Parameter('q')
P_U2LONG = Parameter('Q')

P_HALFFLOAT = Parameter('e')
P_FLOAT = Parameter('f')
P_DOUBLE = Parameter('d')

P_UNICODE_BYTE = UnicodeParameter('B')
P_UNICODE_SHORT = UnicodeParameter('H')
P_UNICODE_INT = UnicodeParameter('I')
P_UNICODE_LONG = UnicodeParameter('L')
P_UNICODE_2LONG = UnicodeParameter('Q')


class Command:
    def __init__(self, command_id: int, command_name: str, **parameters: Parameter):
        self.command_id = command_id
        self.command_name = command_name
        self.parameters = parameters

        self.struct_format = self.compile_parameters()

        fields = ['command_id'] + list(self.parameters)
        self.factory = collections.namedtuple(self.command_name, fields)

    def __call__(self, **kw):
        return self.factory(self.command_id, **kw)

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
        struct_args = list(self.struct_format.unpack(initial_bytes))
        return self.factory(
            self.command_id,
            *(
                p.parse(reader, struct_args)
                for p in self.parameters.values()
            )
        )


class StructReader(SocketReader):
    def __init__(self, sock: socket.socket, commands: list[Command], max_id: Optional[int] = None):
        self.sock = sock
        self.commands = {c.command_id: c for c in commands}
        max_id = max_id or max(self.commands)
        self.id_format = struct.Struct(get_id_code(max_id))

    @classmethod
    def get_factory(cls, commands, max_id=None):
        def get_struct_reader(sock):
            return cls(sock, commands, max_id)

        return get_struct_reader

    def __next__(self):
        command_id, = self.id_format.unpack(self.get_bytes(self.id_format.size))
        return self.commands[command_id].deserialize(self)

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
    def __init__(self, sock: socket.socket, commands: list[Command], max_id: Optional[int] = None):
        self.sock = sock
        self.commands = {c.command_id: c for c in commands}
        max_id = max_id or max(self.commands)
        self.id_format = struct.Struct(get_id_code(max_id))

    @classmethod
    def get_factory(cls, commands, max_id=None):
        def get_struct_writer(sock):
            return cls(sock, commands, max_id)

        return get_struct_writer

    def send(self, message):
        command_id = message[0]
        packed = self.commands[command_id].serialize(message)
        self.sock.sendall(self.id_format.pack(command_id))
        self.sock.sendall(packed)

    def close(self):
        self.sock.close()
