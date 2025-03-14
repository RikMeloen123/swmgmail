#!/usr/bin/env python3
"""
mail_client.py
--------------
A client program that connects to the SMTP and POP3 servers running on the MailServer.
It provides three options:
   a) Mail Sending – composes and sends an email via the SMTP server.
   b) Mail Management – connects to the POP3 server, authenticates, and lets the user manage mails.
   c) Mail Searching – downloads emails and searches them based on keyword, time, or address.
Usage: python mail_client.py <server_IP>
For this example, default ports are assumed:
   SMTP port: 2525
   POP3 port: 1100
"""

import socket
import sys
import re

class MailClient:
    def validate_password(self) -> bool:
        # Connect and authenticate
        s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        s.connect((self.server_ip, self.pop_port))
        s.recv(1024)  # greeting
        s.sendall(f"USER {self.username}\r\n".encode('utf-8'))
        s.recv(1024)
        s.sendall(f"PASS {self.password}\r\n".encode('utf-8'))
        auth_resp = s.recv(1024).decode('utf-8').strip()
        s.sendall("QUIT".encode('utf-8'))
        s.recv(1024)
        return auth_resp.startswith("+OK")

    def authenticate(self) -> None:
        while True:
            self.username = input('Enter your swmgmail username: ')
            self.password = input('Enter your swmgmail password: ')
            if self.validate_password():
                print("You're now logged in")
                return
            print("Incorrect username or password!")
    
    def __init__(self, server_ip, smtp_port, pop_port):
        self.server_ip = server_ip
        self.smtp_port = smtp_port
        self.pop_port = pop_port
    
    def start(self):
        self.authenticate()

        while True:
            print("\nOptions:")
            print("a) Mail Sending")
            print("b) Mail Management")
            print("c) Mail Searching")
            print("d) Exit")
            choice = input("Enter your choice: ")
            if choice.lower() == "a":
                self.send_mail()
            elif choice.lower() == "b":
                self.manage_mail()
            elif choice.lower() == "c":
                self.search_mail()
            elif choice.lower() == "d":
                print("Exiting the application.")
                break
            else:
                print("Invalid option. Please try again.")
    
    def is_valid_email(self, email):
        if "@" not in email or len(email.split("@")) != 2 or email.split("@")[1] != "swmgmail.com":
            return False
        return True

    def send_mail(self):
        print("\n--- Mail Sending ---")
        print("Enter mail in the following format (end with a line containing only a '.'): \n")
        print("From: <username>@<domain>")
        print("To: <username>@<domain>")
        print("Subject: <subject (max 150 characters)>")
        print("<message body>")
        
        # Read mail lines until a line with a single dot is entered
        lines = []
        while True:
            line = input()
            if line.strip() == ".":
                break
            lines.append(line)
        mail_text = "\r\n".join(lines)
        
        # Simple format validation using regex (checking headers exist)
        if not lines[0][:6] == "From: " or not self.is_valid_email(lines[0][6:]):
            print("This is an incorrect format (missing or faulty From header)")
            return
        if not lines[1][:4] == "To: " or not self.is_valid_email(lines[1][4:]):
            print("This is an incorrect format (missing or faulty To header)")
            return
        if not lines[2][:9] == "Subject: ":
            print("This is an incorrect format (missing Subject header)")
            return
        
        mail_from = lines[0][6:]
        rcpt_to = lines[1][4:]

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.server_ip, self.smtp_port))
            recv = s.recv(1024).decode()
            print("Server:", recv.strip())

            # SMTP dialogue
            s.sendall(b"HELO client\r\n")
            s.recv(1024).decode()

            # Extract sender and recipient from mail text
            s.sendall(f"MAIL FROM: {mail_from}\r\n".encode())
            s.recv(1024).decode().strip()

            s.sendall(f"RCPT TO: {rcpt_to}\r\n".encode())
            s.recv(1024).decode().strip()

            s.sendall(b"DATA\r\n")
            s.recv(1024).decode().strip()

            # Send the mail text followed by the termination sequence
            s.sendall((mail_text + "\r\n.\r\n").encode())
            s.recv(1024).decode().strip()

            s.sendall(b"QUIT\r\n")
            s.recv(1024).decode().strip()
            s.close()
            print("Mail sent successfully.\n")
        except Exception as e:
            print("Error sending mail:", e)

    def manage_mail(self):
        print("\n--- Mail Management ---")
        username = input("Enter username: ")
        password = input("Enter password: ")
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((server_ip, pop_port))
            print("Server:", s.recv(1024).decode().strip())

            s.sendall(f"USER {username}\r\n".encode())
            print("Server:", s.recv(1024).decode().strip())

            s.sendall(f"PASS {password}\r\n".encode())
            auth_resp = s.recv(1024).decode().strip()
            print("Server:", auth_resp)
            if not auth_resp.startswith("+OK"):
                s.close()
                return

            # Retrieve mailbox list
            s.sendall(b"LIST\r\n")
            list_resp = s.recv(4096).decode().strip()
            print("\n--- Email List ---")
            print(list_resp)
            print("------------------")

            while True:
                print("\nPOP3 Options: STAT, LIST, RETR <msg>, DELE <msg>, RSET, QUIT")
                cmd = input("Enter POP3 command: ")
                s.sendall((cmd + "\r\n").encode())
                data = s.recv(4096).decode().strip()
                print("Server:", data)
                if cmd.upper() == "QUIT":
                    break
            s.close()
        except Exception as e:
            print("Error managing mail:", e)

    def search_mail(self):
        print("\n--- Mail Searching ---")
        username = input("Enter username: ")
        password = input("Enter password: ")
        try:
            # Connect and authenticate
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((server_ip, pop_port))
            s.recv(1024)  # greeting
            s.sendall(f"USER {username}\r\n".encode())
            s.recv(1024)
            s.sendall(f"PASS {password}\r\n".encode())
            auth_resp = s.recv(1024).decode().strip()
            if not auth_resp.startswith("+OK"):
                print("Authentication failed")
                s.close()
                return

            # Get list of messages
            s.sendall(b"LIST\r\n")
            list_resp = s.recv(4096).decode()
            emails = []
            # The LIST response is multi-line; now retrieve each message
            for line in list_resp.splitlines():
                if line and line[0].isdigit():
                    msg_num = line.split()[0]
                    s.sendall(f"RETR {msg_num}\r\n".encode())
                    retr_resp = s.recv(4096).decode()
                    emails.append(retr_resp)
            s.sendall(b"QUIT\r\n")
            s.close()

            print("\nSearch Options:")
            print("1) Words/sentences")
            print("2) Time (format MM/DD/YY)")
            print("3) Address")
            choice = input("Enter your search option (1, 2, or 3): ")
            query = input("Enter your search query: ")
            print("\n--- Search Results ---")
            found = False
            for email in emails:
                if query in email:
                    print(email)
                    print("------")
                    found = True
            if not found:
                print("No emails matched your query.")
            print("----------------------")
        except Exception as e:
            print("Error searching mail:", e)




def main():
    if len(sys.argv) != 2:
        print("Usage: python mail_client.py <server_IP>")
        sys.exit(1)
    server_ip = sys.argv[1]
    # For this sample, we assume fixed ports (change as needed)
    smtp_port = 2525
    pop_port = 1101

    MailClient(server_ip, smtp_port, pop_port).start()

if __name__ == "__main__":
    main()

"""
--- Sample interaction (client side) ---
Enter your choice: a
(Server connection and SMTP dialogue messages are printed here)
Mail sent successfully.

Enter your choice: b
Enter username: alice
Enter password: password1
(Server POP3 greeting and mail list is printed, then POP3 commands can be entered)

Enter your choice: d
Exiting the application.
"""
