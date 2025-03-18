"""
pop_server.py
-------------
A simple concurrent POP3 server that authenticates users using a local "userinfo.txt"
file and allows mail retrieval/deletion from the mailbox (./<username>/my_mailbox.txt).
Supported commands (after authentication): STAT, LIST, RETR <msg>, DELE <msg>, RSET, QUIT.
Usage: python pop_server.py <POP3_port>
"""

import fcntl
import socket
import threading
import sys

MESSAGE_SIZE = 1024

class Session:

    def __init__(self, connection):
        self._authenticated = False
        self._username = None
        self._password = None
        self._connection = connection
        self._deleted = set()
        self._mailbox_path = None
        connection.sendall(b"+OK: POP3 server ready\r\n")
    
    def get_password(self, username):
        with open("userinfo.txt", "r") as f:
            for line in f:
                parts = line.strip().split(maxsplit=1)  # Split into username and password
                if len(parts) == 2 and parts[0] == username:
                    return parts[1]  # Return the password
        return None
    
    def send_message(self, message):
        self._connection.sendall(f"{message}\r\n".encode("utf-8"))
    
    def handle_quit(self, command_list):
        if self._authenticated:
            self.delete_mails()
        self.send_message("+OK: POP3 server saying good-bye")
        self._connection.close()
        return True
    
    def handle_user(self, command_list):
        if self._authenticated:
            self.send_message("-ERR: Already authenticated")
        elif len(command_list) != 2:
            self.send_message("-ERR: USER <username> expected")
        else: 
            self._username = command_list[1]
            self.send_message("+OK: send your password")
    
    def handle_pass(self, command_list):
        if self._authenticated:
            self.send_message("-ERR: already authenticated")
        elif len(command_list) != 2:
            self.send_message("-ERR: PASS <password> expected")
        elif self._username is None:
            self.send_message("-ERR: USER expected first")
        else: 
            self._password = command_list[1]
            if self._password == self.get_password(self._username):
                self._authenticated = True
                self._mailbox_path = f"{self._username}/my_mailbox.txt"
                self.send_message("+OK: Logged in")
            else:
                self.send_message("-ERR: USER or PASS incorrect")
    
    def handle_stat(self, command_list):
        if not self._authenticated:
            self.send_message("-ERR: authenticate first")
            return False
        if len(command_list) != 1:
            self.send_message("-ERR: STAT takes no arguments")
        else:
            [amount_mails, size] = self.get_mailbox_stats()
            self.send_message(f"+OK: {amount_mails} {size}")
    
    def handle_list(self, command_list):
        if not self._authenticated:
            self.send_message("-ERR: authenticate first")
            return
        if len(command_list) == 1: 
            [amnt, total_size, emails] = self.list_emails()
            self.send_message(f"+OK: {amnt} Messages ({total_size} bytes)\n{emails}")
        elif len(command_list) == 2:
            [amount_mails, size] = self.get_mailbox_stats()
            emailno = command_list[1]
            if not emailno.isnumeric():
                self.send_message("-ERR: emailno must be a number")
            emailno = int(emailno)
            if not (1 <= emailno <= amount_mails):
                self.send_message("-ERR: emailno not found")
            if emailno in self._deleted:
                self.send_message("-ERR: email deleted")
            else:
                emails = self.list_emails(emailno)
                self.send_message(f"+OK:\n{emails}")
        else:
            self.send_message("-ERR: LIST [emailno] with emailno optional expected")
    
    def handle_retr(self, command_list):
        if not self._authenticated:
            self.send_message("-ERR: authenticate first")
            return
        if len(command_list) != 2:
            self.send_message("-ERR: RETR <emailno> expected")
            return
        if not command_list[1].isnumeric():
            self.send_message("-ERR: RETR <emailno> emailno must be number")
            return
        emailno = int(command_list[1])
        if emailno in self._deleted:
            self.send_message("-ERR: email marked deleted")
        else:
            (size, email) = self.get_email_by_number(emailno)
            if size != None and email != None:
                self.send_message(f"+OK: {size}\n{email}")
            else:
                self.send_message("-ERR: RETR <emailno> mail not found")
    
    def handle_dele(self, command_list):
        if not self._authenticated:
            self.send_message("-ERR: authenticate first")
            return
        if len(command_list) != 2:
            self.send_message("-ERR: DELE <emailno> expected")
            return
        if not command_list[1].isnumeric():
            self.send_message("-ERR: DELE <emailno> emailno must be number")
            return
        emailno = int(command_list[1])
        amount_mails = self.get_mailbox_stats()[0]
        if (1 <= emailno <= amount_mails):
            if emailno in self._deleted:
                self.send_message("-ERR: email already deleted")
            else:
                self._deleted.add(emailno)
                self.send_message(f"+OK: email no {emailno} deleted")
        else:
            self.send_message("-ERR: emailno not found")
    
    def handle_rset(self, command_list):
        if not self._authenticated:
            self.send_message("-ERR: authenticate first")
            return
        if len(command_list) != 1:
            self.send_message("-ERR: RSET takes no arguments")
        else:
            self._deleted = set()
            amount_mails = self.get_mailbox_stats()[0]
            self.send_message(f"+OK: mailbox contains {amount_mails} messages")
    
    def handle_command(self, input):
        command_list = input.split(" ")
        command = command_list[0]

        command_dict = {"QUIT": self.handle_quit, "USER": self.handle_user, "PASS": self.handle_pass, "STAT": self.handle_stat, "LIST": self.handle_list, "RETR": self.handle_retr, "DELE": self.handle_dele, "RSET": self.handle_rset}

        if command not in command_dict.keys():
            self.send_message("-ERR: unsupported command")
            return

        return command_dict[command](command_list)
    
    def read_mailbox(self):
        with open(self._mailbox_path, "r", encoding="utf-8") as mailbox:
            # Lock the file before reading
            fcntl.flock(mailbox, fcntl.LOCK_EX)
            try:
                return mailbox.readlines()
            finally:
                fcntl.flock(mailbox, fcntl.LOCK_UN)
    
    def get_mailbox_stats(self):
        amount_mails = 0
        index = 1
        total_size = 0
        email_size = 0
        for line in self.read_mailbox():
            email_size += len(line.encode("utf-8"))
            if line.strip() == ".":
                if index not in self._deleted:
                    amount_mails += 1
                    total_size += email_size
                email_size = 0
                index += 1
        return [amount_mails, total_size]
    
    def list_emails(self, email_number = None):
        emails = []
        current_email= []
        for line in self.read_mailbox():
            if line.strip() == ".":
                emails.append("\n".join(current_email))
                current_email = []
            else:
                current_email.append(line.strip())

        output = ""
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
    
    def get_email_by_number(self, emailno):
        emails = []
        current_email = []
        for line in self.read_mailbox():
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
    
    def delete_mails(self):
        emails = []
        current_email = []
        for line in self.read_mailbox():
            if line.strip() == ".":
                emails.append("\n".join(current_email) + "\n.")
                current_email = []
            else:
                current_email.append(line.rstrip())

        emails = [email for i, email in enumerate(emails, start=1) if i not in self._deleted]
        
        with open(self._mailbox_path, "w", encoding="utf-8") as mailbox:
            # Lock the file before writing
            fcntl.flock(mailbox, fcntl.LOCK_EX)
            try:
                mailbox.write("\n".join(emails) + "\n")
            finally:
                fcntl.flock(mailbox, fcntl.LOCK_UN)

def handle_client(conn):
    ses = Session(conn)
    while True:
        temp = conn.recv(MESSAGE_SIZE).decode().strip()
        for line in temp.splitlines():
            quit = ses.handle_command(line)
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
        threading.Thread(target=handle_client, args=(c)).start()

if __name__ == "__main__":
    main()
