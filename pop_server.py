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
        self._authenticated = False
        self._username = None
        self._password = None
        self._connection = connection
        self._deleted = set()
        self._mailboxPath = None
        connection.sendall(b"+OK: POP3 server ready\n")
    
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
                if self._authenticated:
                    self.deleteMails()
                self._connection.sendall(b'+OK: POP3 server saying good-bye\n')
                self._connection.close()
                return True


            case 'USER':
                if self._authenticated:
                    self._connection.sendall(b'-ERR: Already authenticated\n')
                elif len(list) != 2:
                    self._connection.sendall(b'-ERR: USER <username> expected\n')
                else: 
                    self._username = list[1]
                    self._connection.sendall(b'+OK: send your password\n')


            case 'PASS':
                if self._authenticated:
                    self._connection.sendall(b'-ERR: already authenticated\n')
                elif len(list) != 2:
                    self._connection.sendall(b'-ERR: PASS <password> expected\n')
                else: 
                    self._password = list[1]
                    if self._password == self.getPassword(self._username):
                        self._authenticated = True
                        self._mailboxPath = f"{self._username}/my_mailbox.txt"
                        self._connection.sendall(b'+OK: Logged in\n')
                    else:
                        self._connection.sendall(b'-ERR: USER or PASS incorrect\n')


            case 'STAT':
                if not self._authenticated:
                    self._connection.sendall(b'-ERR: authenticate first\n')
                elif len(list) != 1:
                    self._connection.sendall(b'-ERR: STAT takes no arguments\n')
                else:
                    [amntMails, size] = self.getMailboxStats()
                    self._connection.sendall(f'+OK: {amntMails} {size}\n'.encode('utf-8'))


            case 'LIST':
                if not self._authenticated:
                    self._connection.sendall(b'-ERR: authenticate first\n')
                elif len(list) != 1:
                    self._connection.sendall(b'-ERR: LIST takes no arguments\n')
                else: 
                    [amntMails, size] = self.getMailboxStats()
                    emails = self.listEmails()
                    self._connection.sendall(f'+OK: {amntMails} {size}\n{emails}'.encode('utf-8'))


            case 'RETR':
                if not self._authenticated:
                    self._connection.sendall(b'-ERR: authenticate first\n')
                elif len(list) != 2:
                    self._connection.sendall(b'-ERR: RETR <emailno> expected\n')
                elif not list[1].isnumeric():
                    self._connection.sendall(b'-ERR: RETR <emailno> emailno must be number\n')
                else: 
                    emailno = int(list[1])
                    (size, email) = self.getEmailByNumber(emailno)
                    if size != None and email != None:
                        self._connection.sendall(f'+OK: {size}\n{email}\n'.encode('utf-8'))
                    else:
                        self._connection.sendall(b'-ERR: RETR <emailno> mail not found\n')

            case 'DELE':
                if not self._authenticated:
                    self._connection.sendall(b'-ERR: authenticate first\n')
                elif len(list) != 2:
                    self._connection.sendall(b'-ERR: DELE <emailno> expected\n')
                elif not list[1].isnumeric():
                    self._connection.sendall(b'-ERR: DELE <emailno> emailno must be number\n')
                else: 
                    emailno = int(list[1])
                    amntMails = self.getMailboxStats()[0]
                    if (1 <= emailno <= amntMails):
                        index = self.getEmailIndex(emailno)
                        self._deleted.add(index)
                        self._connection.sendall(f'+OK: email no {emailno} deleted\n'.encode('utf-8'))
                    else:
                        self._connection.sendall(b'-ERR: emailno not found\n')

            case 'RSET':
                if not self._authenticated:
                    self._connection.sendall(b'-ERR: authenticate first\n')
                elif len(list) != 1:
                    self._connection.sendall(b'-ERR: RSET takes no arguments\n')
                else:
                    self._deleted = set()
                    amntMails = self.getMailboxStats()[0]
                    self._connection.sendall(f'+OK: mailbox contains {amntMails} messages\n'.encode('utf-8'))
                        
            case _:
                self._connection.sendall(b'-ERR: unsupported command\n')
    
    def getMailboxStats(self):
        amntMails = 0
        mailbox = open(self._mailboxPath, "r", encoding="utf-8")
        index = 1
        for line in mailbox:
            if line.strip() == ".":
                if not index in self._deleted:
                    amntMails += 1
                index += 1
        size = os.path.getsize(self._mailboxPath)
        return [amntMails, size]
    
    def listEmails(self):
        emails = []
        mailbox = open(self._mailboxPath, "r", encoding="utf-8")
        email_data = {}
        index = 1
        for line in mailbox:
            line = line.strip()
            if line.startswith("From: "):
                email_data["from"] = line.split(": ")[1]
            elif line.startswith("Received: "):
                email_data["received"] = line.split(": ")[1]
            elif line.startswith("Subject: "):
                email_data["subject"] = line.split(": ")[1]
            elif line == ".":  # End of email
                if not index in self._deleted:
                    emails.append(email_data)
                index += 1
                email_data = {}
        output = ''
        for i, email in enumerate(emails, start=1):
            output += (f"{i}. {email.get('from', 'Unknown')} {email.get('received', 'Unknown')} {email.get('subject', 'No Subject')}\n")
        return output
    
    def getEmailByNumber(self, emailno):
        mailbox = open(self._mailboxPath, "r", encoding="utf-8")
        emails = []
        current_email = []
        index = 1
        for line in mailbox:
            if line.strip() == ".":
                if index not in self._deleted:
                    emails.append("\n".join(current_email))
                index += 1
                current_email = []
            else:
                current_email.append(line.strip())
        
        if (1 <= emailno <= len(emails)):
            email_content = emails[emailno - 1]
            email_size = len(email_content.encode("utf-8"))
            return email_size, email_content
        else:
            return None, None
        
    def getEmailIndex(self, emailno):
        delEmailList = list(self._deleted)
        addCount = 0
        for number in delEmailList:
            if number <= emailno:
                addCount += 1
        return emailno + addCount
    
    def deleteMails(self):
        mailbox = open(self._mailboxPath, "r", encoding="utf-8")
        emails = []
        current_email = []
        for line in mailbox:
            if line.strip() == ".":
                emails.append("\n".join(current_email) + "\n.")
                current_email = []
            else:
                current_email.append(line.rstrip())

        emails = [email for i, email in enumerate(emails, start=1) if i not in self._deleted]
        
        mailbox = open(self._mailboxPath, "w", encoding="utf-8")
        mailbox.write("\n".join(emails) + "\n")

def handle_client(conn, addr):
    ses = Session(conn)
    while True:
        temp = conn.recv(MESSAGE_SIZE).decode().strip()
        for line in temp.splitlines():
            quit = ses.parseCmd(line)
        if (quit):
                break

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