"""
pop_server.py
-------------
A simple concurrent POP3 server that authenticates users using a local 'userinfo.txt'
file and allows mail retrieval/deletion from the mailbox (./<username>/my_mailbox.txt).
Supported commands (after authentication): STAT, LIST, RETR <msg>, DELE <msg>, RSET, QUIT.
Usage: python pop_server.py <POP3_port>
"""

import socket
import threading
import sys
import os

MESSAGE_SIZE = 1024

class Session:
    def __init__(self, connection):
        self._username = None
        self._password = None
        self._connection = connection
        self._deleted = set()
        connection.sendall(b"+OK: POP3 server ready\n")
    
    def authenticate(self):
        #get username and password
        while True:
            temp = self._connection.recv(MESSAGE_SIZE).decode()
            userCmd = self.parseCmd(temp)
            if (userCmd == None): continue
            cmd = userCmd[0]
            if (cmd == 'USER'):
                username = userCmd[1]
                password = self.getPassword(username)
                self._username = username
                self._connection.sendall(b'+OK: send your password')
                temp = self._connection.recv(MESSAGE_SIZE).decode()
                passCmd = self.parseCmd(temp)
                if (passCmd == None): continue
                cmd = passCmd[0]
                if (cmd == 'PASS'):
                    passAttempt = passCmd[1]
                    if passAttempt != password:
                        self._connection.sendall(b'-ERR: USER or PASS incorrect')
                        continue
                    else:
                        self._password = passAttempt
                        self._connection.sendall(b'+OK: Logged in')
                        break
                else:
                    self._connection.sendall(b'-ERR: PASS <password> expected.')
                    continue
            else:
                self._connection.sendall(b'-ERR: USER <username> expected.')
                continue
    
    def handleTransaction(self, parsedCmd):
        if parsedCmd == None: return
        cmd = parsedCmd[0]
        match cmd:
            case 'STAT':
                [amntMails, size] = self.getMailboxStats()
                self._connection.sendall(f'+OK: {amntMails} {size}'.encode())
            case 'LIST':
                [amntMails, size] = self.getMailboxStats()
                emails = self.listEmails()
                self._connection.sendall(f'+OK: {amntMails} {size}\n{emails}'.encode())
            case 'RETR':
                emailno = parsedCmd[1]


    
    def getPassword(self, username):
        file = open('userinfo.txt', "r")
        for line in file:
            parts = line.strip().split(maxsplit=1)  # Split into username and password
            if len(parts) == 2 and parts[0] == username:
                return parts[1]  # Return the password
        return None
    
    def parseCmd(self, input):
        list = input.split(" ")
        cmd = list[0]
        match cmd:
            case 'QUIT':
                self._connection.sendall(b'+OK: POP3 server saying good-bye')
                self._connection.close()
                return ['QUIT']
            case 'USER':
                if len(list) != 2:
                    self._connection.sendall(b'-ERR: USER <username> expected')
                else: return list
            case 'PASS':
                if len(list) != 2:
                    self._connection.sendall(b'-ERR: PASS <password> expected')
                else: return list
            case 'STAT':
                if len(list) != 1:
                    self._connection.sendall(b'-ERR: STAT takes no arguments')
                else: return list
            case 'LIST':
                if len(list) != 1:
                    self._connection.sendall(b'-ERR: LIST takes no arguments')
                else: return list
            case 'RETR':
                if len(list) != 2:
                    self._connection.sendall(b'-ERR: RETR <emailno> expected')
                elif not list[1].isnumeric():
                    self._connection.sendall(b'-ERR: RETR <emailno> emailno must be number')
                else: return list
            case _:
                self._connection.sendall(b'-ERR: unsupported command')
    
    def getMailboxStats(self):
        amntMails = 0
        path = f"{self._username}/my_mailbox.txt"
        mailbox = open(path, "r", encoding="utf-8")
        for line in mailbox:
            if line.strip() == ".":
                amntMails += 1
        size = os.path.getsize(path)
        return [amntMails, size]
    
    def listEmails(self):
        emails = []
        mailbox = open(f"{self._username}/my_mailbox.txt", "r", encoding="utf-8")
        email_data = {}
        for line in mailbox:
            line = line.strip()
            if line.startswith("From: "):
                email_data["from"] = line.split(": ")[1]
            elif line.startswith("Received: "):
                email_data["received"] = line.split(": ")[1]
            elif line.startswith("Subject: "):
                email_data["subject"] = line.split(": ")[1]
            elif line == ".":  # End of email
                emails.append(email_data)
                email_data = {}
        output = ''
        for i, email in enumerate(emails, start=1):
            output += (f"{i}. {email.get('from', 'Unknown')} {email.get('received', 'Unknown')} {email.get('subject', 'No Subject')}\n")
        return output




def handle_client(conn, addr):
    ses = Session(conn)
    ses.authenticate()
    while True:
        temp = conn.recv(MESSAGE_SIZE).decode()
        ses.handleTransaction(ses.parseCmd(temp))

def main():
    if len(sys.argv) != 2:
        print("Usage: python pop_server.py <POP3_port>")
        sys.exit(1)
    port = int(sys.argv[1])
    server_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    server_socket.bind(("", port))
    server_socket.listen(5)
    print(f"POP3 Server running on port {port}...")
    while True:
        c, addr = server_socket.accept()
        print(f"POP3 connection established with {addr}")
        threading.Thread(target=handle_client, args=(c, addr)).start()

if __name__ == "__main__":
    main()