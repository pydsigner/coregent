import argparse

from coregent.net.client import Client
from coregent.net.json import JSONReader, JSONWriter


class ConsoleClient(Client):
    """
    An example CLI Client, capable of sending and receiving simple chat
    messages and logging raw messages of other types.
    """

    reader_factory = JSONReader
    writer_factory = JSONWriter

    def __init__(self, conn_info):
        super().__init__(conn_info, self.display_message)

    def display_message(self, message):
        """
        Display a single Python dictionary pre-decoded from JSON.
        """
        if message['type'] != 'chat':
            print(f'Unknown message: {message}')

        if message['source'] == 'server':
            print(f'!! {message["msg"]}')
        else:
            print(f'{message["user"]}: {message["msg"]}')

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

            self.send_message({
                'type': 'chat',
                'msg': message
            })


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--hostname', default='localhost')
    parser.add_argument('-p', '--port', type=int, default=40001)
    args = parser.parse_args()

    ConsoleClient((args.hostname, args.port)).run()
