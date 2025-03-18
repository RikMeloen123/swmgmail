"""
pop_server.py
-------------
A simple concurrent POP3 server that authenticates users using a local 'userinfo.txt'
file and allows mail retrieval/deletion from the mailbox (./<username>/my_mailbox.txt).
Supported commands (after authentication): STAT, LIST, RETR <msg>, DELE <msg>, RSET, QUIT.
Usage: python pop_server.py <POP3_port>
"""

import fcntl
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
        connection.sendall(b"+OK: POP3 server ready\r\n")
    
    def getPassword(self, username):
        with open('userinfo.txt', "r") as f:
            for line in f:
                parts = line.strip().split(maxsplit=1)  # Split into username and password
                if len(parts) == 2 and parts[0] == username:
                    return parts[1]  # Return the password
        return None
    
    def sendMessage(self, message):
        self._connection.sendall(f'{message}\r\n'.encode('utf-8'))
    
    def parseCmd(self, input):
        list = input.split(" ")
        cmd = list[0]
        match cmd:
            case 'QUIT':
                if self._authenticated:
                    self.deleteMails()
                self.sendMessage('+OK: POP3 server saying good-bye')
                self._connection.close()
                return True


            case 'USER':
                if self._authenticated:
                    self.sendMessage('-ERR: Already authenticated')
                elif len(list) != 2:
                    self.sendMessage('-ERR: USER <username> expected')
                else: 
                    self._username = list[1]
                    self.sendMessage('+OK: send your password')


            case 'PASS':
                if self._authenticated:
                    self.sendMessage('-ERR: already authenticated')
                elif len(list) != 2:
                    self.sendMessage('-ERR: PASS <password> expected')
                else: 
                    self._password = list[1]
                    if self._password == self.getPassword(self._username):
                        self._authenticated = True
                        self._mailboxPath = f"{self._username}/my_mailbox.txt"
                        self.sendMessage('+OK: Logged in')
                    else:
                        self.sendMessage('-ERR: USER or PASS incorrect')


            case 'STAT':
                if not self._authenticated:
                    self.sendMessage('-ERR: authenticate first')
                elif len(list) != 1:
                    self.sendMessage('-ERR: STAT takes no arguments')
                else:
                    [amntMails, size] = self.getMailBoxStats()
                    self.sendMessage(f'+OK: {amntMails} {size}')


            case 'LIST':
                if not self._authenticated:
                    self.sendMessage('-ERR: authenticate first')                    
                elif len(list) == 1: 
                    [amnt, total_size, emails] = self.listEmails()
                    self.sendMessage(f'+OK: {amnt} Messages ({total_size} bytes)\n{emails}')
                elif len(list) == 2:
                    [amntMails, size] = self.getMailBoxStats()
                    emailno = list[1]
                    if not emailno.isnumeric():
                        self.sendMessage('-ERR: emailno must be a number')
                    emailno = int(emailno)
                    if not (1 <= emailno <= amntMails):
                        self.sendMessage('-ERR: emailno not found')
                    if emailno in self._deleted:
                        self.sendMessage('-ERR: email deleted')
                    else:
                        emails = self.listEmails(emailno)
                        self.sendMessage(f'+OK:\n{emails}')
                else:
                    self.sendMessage('-ERR: LIST [emailno] with emailno optional expected')


            case 'RETR':
                if not self._authenticated:
                    self.sendMessage('-ERR: authenticate first\n')
                elif len(list) != 2:
                    self.sendMessage('-ERR: RETR <emailno> expected\n')
                elif not list[1].isnumeric():
                    self.sendMessage('-ERR: RETR <emailno> emailno must be number\n')
                else: 
                    emailno = int(list[1])
                    if emailno in self._deleted:
                        self.sendMessage('-ERR: email marked deleted')
                    else:
                        (size, email) = self.getEmailByNumber(emailno)
                        if size != None and email != None:
                            self.sendMessage(f'+OK: {size}\n{email}')
                        else:
                            self.sendMessage('-ERR: RETR <emailno> mail not found')

            case 'DELE':
                if not self._authenticated:
                    self.sendMessage('-ERR: authenticate first')
                elif len(list) != 2:
                    self.sendMessage('-ERR: DELE <emailno> expected')
                elif not list[1].isnumeric():
                    self.sendMessage('-ERR: DELE <emailno> emailno must be number')
                else: 
                    emailno = int(list[1])
                    amntMails = self.getMailBoxStats()[0]
                    if (1 <= emailno <= amntMails):
                        if emailno in self._deleted:
                            self.sendMessage('-ERR: email already deleted')
                        else:
                            self._deleted.add(emailno)
                            self.sendMessage(f'+OK: email no {emailno} deleted')
                    else:
                        self.sendMessage('-ERR: emailno not found')

            case 'RSET':
                if not self._authenticated:
                    self.sendMessage('-ERR: authenticate first')
                elif len(list) != 1:
                    self.sendMessage('-ERR: RSET takes no arguments')
                else:
                    self._deleted = set()
                    amntMails = self.getMailBoxStats()[0]
                    self.sendMessage(f'+OK: mailbox contains {amntMails} messages')
                        
            case _:
                self.sendMessage('-ERR: unsupported command')
    
    def readMailbox(self):
        with open(self._mailboxPath, "r", encoding="utf-8") as mailbox:
            # Lock the file before reading
            fcntl.flock(mailbox, fcntl.LOCK_EX)
            try:
                return mailbox.readlines()
            finally:
                fcntl.flock(mailbox, fcntl.LOCK_UN)
    
    def getAllMailboxStats(self):
        amntMails = 0
        for line in self.readMailbox():
            if line.strip() == ".":
                amntMails += 1
        size = os.path.getsize(self._mailboxPath)
        return [amntMails, size]
    
    def getMailBoxStats(self):
        amntMails = 0
        index = 1
        total_size = 0
        email_size = 0
        for line in self.readMailbox():
            email_size += len(line.encode('utf-8'))
            if line.strip() == ".":
                if index not in self._deleted:
                    amntMails += 1
                    total_size += email_size
                email_size = 0
                index += 1
        return [amntMails, total_size]
    
    def listEmails(self, email_number = None):
        emails = []
        current_email= []
        for line in self.readMailbox():
            if line.strip() == ".":
                emails.append("\n".join(current_email))
                current_email = []
            else:
                current_email.append(line.strip())

        output = ''
        if email_number is not None:
            email_size = len(emails[email_number - 1].encode("utf-8"))
            output += f"{email_number} {email_size}\n"
            return output
        else:
            amnt = 0
            total = 0
            for i, email in enumerate(emails, start=1):
                if i not in self._deleted:
                    amnt+= 1
                    email_size = len(email.encode("utf-8"))
                    total += email_size
                    output += f"{i} {email_size}\n"
            return [amnt, total, output]
    
    def getEmailByNumber(self, emailno):
        emails = []
        current_email = []
        for line in self.readMailbox():
            if line.strip() == ".":
                emails.append("\n".join(current_email))
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
        addCount = emailno
        for number in delEmailList:
            if number <= addCount:
                addCount += 1
        return addCount
    
    def deleteMails(self):
        emails = []
        current_email = []
        for line in self.readMailbox():
            if line.strip() == ".":
                emails.append("\n".join(current_email) + "\n.")
                current_email = []
            else:
                current_email.append(line.rstrip())

        emails = [email for i, email in enumerate(emails, start=1) if i not in self._deleted]
        
        with open(self._mailboxPath, "w", encoding="utf-8") as mailbox:
            # Lock the file before writing
            fcntl.flock(mailbox, fcntl.LOCK_EX)
            try:
                mailbox.write("\n".join(emails) + "\n")
            finally:
                fcntl.flock(mailbox, fcntl.LOCK_UN)

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
