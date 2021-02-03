from __future__ import annotations

import argparse
import socket
import time
import _thread
from typing import Union

import coregent.net.struct as sn
from coregent.net.client import Client
from coregent.net.core import get_server_socket


M_CONNECT = sn.Message(
    1, 'Connect',
    user=sn.P_UNICODE8
)
M_WELCOME = sn.Message(
    2, 'Welcome',
    time=sn.P_DOUBLE,
    msg=sn.P_UNICODE32
)
M_DISCONNECT = sn.Message(
    3, 'Disconnect',
    user=sn.P_UNICODE8
)
M_CLIENT_CHAT = sn.Message(
    1000, 'ClientChat',
    msg=sn.P_UNICODE32
)
M_SERVER_CHAT = sn.Message(
    1001, 'ServerChat',
    time=sn.P_DOUBLE,
    source=sn.P_UNICODE8,
    msg=sn.P_UNICODE32
)
MESSAGE_TYPES = [M_CONNECT, M_WELCOME, M_DISCONNECT, M_CLIENT_CHAT, M_SERVER_CHAT]

get_struct_reader = sn.StructReader.get_factory(MESSAGE_TYPES)
get_struct_writer = sn.StructWriter.get_factory(MESSAGE_TYPES)


class StructClient(Client):
    reader_factory = staticmethod(get_struct_reader)
    writer_factory = staticmethod(get_struct_writer)

    def __init__(self, conn_info: Union[tuple[str, int], tuple[str, int, socket.AddressFamily]]):
        super().__init__(conn_info, self.display_message)

    def display_message(self, message):
        if message.message_id == M_WELCOME.message_id:
            print(f'({message.time}) MOTD: {message.msg}')
        elif message.message_id == M_CONNECT.message_id:
            print(f'* {message.user} has joined the chat')
        elif message.message_id == M_DISCONNECT.message_id:
            print(f'* {message.user} has left the chat')
        elif message.message_id == M_SERVER_CHAT.message_id:
            if message.source == 'server':
                print(f'!! ({message.time}) {message.msg}')
            else:
                print(f'({message.time}) {message.source}: {message.msg}')
        else:
            print(f'Unknown message: {message}')

    def run(self):
        """
        Connect to the configured server and run the interactive mainloop.
        """
        self.start()

        while True:
            message = input(' -> ')
            if message.lower().startswith('bye'):
                self.close()
                break

            self.send_message(
                M_CLIENT_CHAT(
                    msg=message
                )
            )


class StructServer:
    """
    A basic matchmaking server which populates players into matches in order
    of connection.
    """

    def __init__(self, hostname, port):
        self.hostname = hostname
        self.port = port
        self.player_map = {}
        self.queue_lock = _thread.allocate_lock()

    def run(self):
        server_socket = get_server_socket(self.hostname, self.port)

        # how many people can be in queue
        server_socket.listen(2)
        server_socket.settimeout(0.5)

        while True:
            try:
                conn, address = server_socket.accept()  # accept new connection
            except socket.timeout:
                continue

            print(f'Connection from: {address}')
            _thread.start_new_thread(self.handle_connection, (conn,))

    def handle_connection(self, conn):
        reader = get_struct_reader(conn)
        writer = get_struct_writer(conn)

        username = self.authenticate_user(reader, writer)

        # Clean up if authentication fails.
        if username is None:
            reader.close()
            writer.close()
            return

        self.queue_user(username, writer)

        # Wait for a game to start
        self.run_user_mainloop(username, reader, writer)

    def authenticate_user(self, reader, writer):
        writer.send(
            M_WELCOME(
                time=time.time(),
                msg=f'Players currently connected: {", ".join(self.player_map)}'
            )
        )
        writer.send(
            M_SERVER_CHAT(
                time=time.time(),
                source='server',
                msg=f'Send me your username'
            )
        )

        username_msg = next(reader)
        if not username_msg:
            return

        assert username_msg.message_id == M_CLIENT_CHAT.message_id
        username = username_msg.msg

        if username in self.player_map:
            writer.send(
                M_SERVER_CHAT(
                    time=time.time(),
                    source='server',
                    msg=f'Username taken'
                )
            )
            return
        return username

    def queue_user(self, username, writer):
        with self.queue_lock:
            self.player_map[username] = writer

            print(f'added player {username}')

        self.player_connected(username)

    def run_user_mainloop(self, username, reader, writer):
        try:
            for message in reader:
                self.player_message(username, message)
        finally:
            self.player_map.pop(username)
            self.player_disconnected(username)

    def player_connected(self, username):
        self.forward_message(
            username,
            M_CONNECT(
                user=username
            )
        )

    def player_disconnected(self, username):
        self.forward_message(
            username,
            M_DISCONNECT(
                user=username
            )
        )

    def player_message(self, username, message):
        if message.message_id != M_CLIENT_CHAT.message_id:
            print(f'Unexpected message: {message}')

        self.forward_message(
            username,
            M_SERVER_CHAT(
                time=time.time(),
                source=username,
                msg=message.msg
            )
        )

    def forward_message(self, username, message):
        for player in list(self.player_map):
            if player != username:
                self.send_message(player, message)

    def send_message(self, player, message):
        self.player_map[player].send(message)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--server', action='store_true')
    parser.add_argument('-n', '--hostname', default='localhost')
    parser.add_argument('-p', '--port', type=int, default=40001)
    args = parser.parse_args()

    if args.server:
        StructServer(args.hostname, args.port).run()
    else:
        StructClient((args.hostname, args.port)).run()
