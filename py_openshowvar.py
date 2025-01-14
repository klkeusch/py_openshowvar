"""
A Python port of KUKA VarProxy client (OpenShowVar).
"""

from __future__ import print_function
import os
import sys
import struct
import random
import socket
import time

from timeloop import Timeloop
from datetime import timedelta

# from rich.console import Console
# from rich.table import table

tl = Timeloop()


def cls():
    os.system('cls' if os.name == 'nt' else 'clear')


__version__ = '1.1.7'
ENCODING = 'UTF-8'

PY2 = sys.version_info[0] == 2
if PY2:
    input = raw_input


class OpenShowVar(object):
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.msg_id = random.randint(1, 100)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((self.ip, self.port))
        except socket.error:
            print('Keine Antwort erhalten.')
            pass

    def test_connection(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            ret = sock.connect_ex((self.ip, self.port))
            return ret == 0
        except socket.error:
            print('Fehler im Netzwerk-Socket')
            return False

    can_connect = property(test_connection)

    def keep_alive(self, var='$OV_PRO'):
        self.varname = var if PY2 else var.encode(ENCODING)
        debug = False
        req = self._pack_read_req()
        self._send_req(req)

    ping = property(keep_alive)

    def read(self, var, debug=True):
        if not isinstance(var, str):
            raise Exception('Variablenname ist ein String')
        else:
            self.varname = var if PY2 else var.encode(ENCODING)
        return self._read_var(debug)

    def write(self, var, value, debug=True):
        if not (isinstance(var, str) and isinstance(value, str)):
            raise Exception(
                'Variablenname und -wert müssen ein String sein.')
        self.varname = var if PY2 else var.encode(ENCODING)
        self.value = value if PY2 else value.encode(ENCODING)
        return self._write_var(debug)

    def _read_var(self, debug):
        req = self._pack_read_req()
        self._send_req(req)
        _value = self._read_rsp(debug)
        if debug:
            print(_value)
        return _value

    def _write_var(self, debug):
        req = self._pack_write_req()
        self._send_req(req)
        _value = self._read_rsp(debug)
        if debug:
            print(_value)
        return _value

    def _send_req(self, req):
        self.rsp = None
        self.sock.sendall(req)
        self.rsp = self.sock.recv(256)

    def _pack_read_req(self):
        var_name_len = len(self.varname)
        flag = 0
        req_len = var_name_len + 3

        return struct.pack(
            '!HHBH' + str(var_name_len) + 's',
            self.msg_id,
            req_len,
            flag,
            var_name_len,
            self.varname
        )

    def _pack_write_req(self):
        var_name_len = len(self.varname)
        flag = 1
        value_len = len(self.value)
        req_len = var_name_len + 3 + 2 + value_len

        return struct.pack(
            '!HHBH' + str(var_name_len) + 's' + 'H' + str(value_len) + 's',
            self.msg_id,
            req_len,
            flag,
            var_name_len,
            self.varname,
            value_len,
            self.value
        )

    def _read_rsp(self, debug=False):
        if self.rsp is None:
            return None
        var_value_len = len(self.rsp) - struct.calcsize('!HHBH') - 3
        result = struct.unpack('!HHBH' + str(var_value_len) + 's' + '3s', self.rsp)
        _msg_id, body_len, flag, var_value_len, var_value, isok = result
        if debug:
            print('[DEBUG]', result)
        if result[-1].endswith(b'\x01') and _msg_id == self.msg_id:
            self.msg_id = (self.msg_id + 1) % 65536  # format char 'H' is 2 bytes long
            return var_value

    def close(self):
        self.sock.close()


"""
First draft for a console application
"""


def run_shell(ip, port):
    # Second command line window
    os.system("start /B start cmd.exe @cmd /k ping 8.8.8.8 -t ")

    cls()
    client = OpenShowVar(ip, port)
    filename = 'kuka_py_osv_log.txt'
    filename_connection = 'kuka_py_osv_connection_log.txt'

    with open(filename, 'a') as f:
        if not client.can_connect:
            print('Verbindung konnte nicht hergestellt werden.')
            import sys
            sys.exit(-1)
        with open(filename_connection, 'a') as fc:
            client.read('$ROBNAME[]', False)
            print('\nVerbunden mit KRC: {}:{}'.format(ip, port), end=' ')
            fc.write('Verbunden mit KRC: {}:{} um {}\n'.format(ip, port, time.ctime()))

            @tl.job(interval=timedelta(seconds=25))
            def ping_robot():
                latest_ping = ('\nLetzter automatischer Ping: {}\n'.format(time.ctime()))
                client.ping
                fc.write("Automatischer Ping ausgeführt: {}\n".format(time.ctime()))
                return latest_ping

            @tl.job(interval=timedelta(seconds=10))
            def val_laser_power():
                cyclic_value = client.read("ADAPTLASERPOWER2", True)
                f.write("Abgefragte Variable: ADAPTLASERPOWER2, Wert: {} um {}\n".format(cyclic_value,
                                                                           time.ctime()))



            tl.start(block=False)

            while True:
                data = input('\n======================================================================\n'
                             '============================| Menue |=================================\n'
                             '=============| Verbunden mit KRC: {}:{} |=================\n'
                             '======================================================================\n'
                             '("var_name [, var_value]" - Abfrage Variable, var_value: Wert setzen)\n'
                             '("h" - Hilfe anzeigen)\n'
                             '("p" - Ping)\n'
                             '("pm" - Zeige letzten automatischen Ping)\n'
                             '("c" - Ausgabefenster leeren)\n'
                             '("q" - Beenden)\n'
                             '======================================================================\n'
                             'Eingabe: '.format(ip, port))

                if data.lower() == 'q':
                    print('\nVerbindung getrennt.\n')
                    fc.write("Verbindung getrennt: {}\n".format(time.ctime()))
                    client.close()
                    break
                elif data.lower() == 'c':
                    print('\nAusgabefenster leeren...\n')
                    time.sleep(1)
                    cls()
                elif data.lower() == 'h':
                    cls()
                    print('\nAbfrage von Variablen mit Eingabe von: "$OV_PRO" bzw. "SCHICHT"\n')
                    print('Setzen des Wertes einer Variable mit: "<var_name>, <var_value>", z. B. "SCHICHT, 80"\n')
                    print('Alle Vorgaenge und Werte werden in der Datei "{}"'.format(filename),
                          'im Programmordner gesichert.\n')
                    input_help = input('("b" - Beenden der Hilfe)\n')
                    if input_help.lower() == 'b':
                        cls()
                elif data.lower() == 'p':
                    print('\nPing ausgefuehrt\n')
                    fc.write("Manueller Ping ausgeführt: {}\n".format(time.ctime()))
                    client.ping
                elif data.lower() == 'pm':
                    print(ping_robot())
                else:
                    parts = data.split(',')
                    if len(parts) == 1:
                        extracted_var_value = client.read(data.strip(), True)
                        print("\nAbgefragte Variable: {}, Wert: {} um {}\n".format(parts[0], extracted_var_value,
                                                                                   time.ctime()))
                        f.write("Abgefragte Variable: {}, Wert: {} um {}\n".format(parts[0], extracted_var_value,
                                                                                   time.ctime()))
                    else:
                        print("\nWert von: {} auf{} gesetzt um {}\n".format(parts[0], parts[1], time.ctime()))
                        f.write("Wert von: {} auf{} gesetzt um {}\n".format(parts[0], parts[1], time.ctime()))
                        client.write(parts[0], parts[1].lstrip(), True)


if __name__ == '__main__':
    ip = "172.31.1.147" # input('IP-Adresse: ')
    port = "7000" # input('Port: ')
    run_shell(ip, int(port))


#table = Table(title="Star Wars Movies")

#table.add_column("Released", justify="right", style="cyan", no_wrap=True)
#table.add_column("Title", style="magenta")
#table.add_column("Box Office", justify="right", style="green")

#table.add_row("Dec 20, 2019", "Star Wars: The Rise of Skywalker", "$952,110,690")
#table.add_row("May 25, 2018", "Solo: A Star Wars Story", "$393,151,347")
#table.add_row("Dec 15, 2017", "Star Wars Ep. V111: The Last Jedi", "$1,332,539,889")
#table.add_row("Dec 16, 2016", "Rogue One: A Star Wars Story", "$1,332,439,889")

console = Console()
console.print(table)