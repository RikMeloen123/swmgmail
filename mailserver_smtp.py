import socket
import threading
import sys
import os
import datetime
from enum import Enum, auto

WRITE_MAIL_LOCK = threading.Lock()


class SMTPState(Enum):
    INIT = auto()
    HELO_DONE = auto()
    MAIL_FROM_DONE = auto()
    RCPT_TO_DONE = auto()
    DATA = auto()
    QUIT = auto()

class SMTPSession:
    """Handles a single SMTP session with a client."""
    
    def __init__(self, conn, addr):
        self.conn = conn
        self.addr = addr
        self.reset()
    
    def reset(self):
        self.state = SMTPState.INIT
        self.sender = ""
        self.recipients = []
        self.data_lines = []
    
    def send_response(self, message):
        """Sends an SMTP response to the client."""
        self.conn.sendall((message + "\r\n").encode("utf-8"))

    def handle_client(self):
        """Processes SMTP commands from the client."""
        try:
            self.send_response("220 MailServer SMTP Ready")
            
            while True:
                data = self.conn.recv(1024).decode("utf-8")
                if not data:
                    break  # Client disconnected
                
                for line in data.splitlines():
                    print(f"[{self.addr}] Received: {line}")

                    self.process_command(line.strip())

                    if self.state == SMTPState.QUIT:
                        return
        
        except Exception as e:
            print(f"Exception with client {self.addr}: {e}")
        finally:
            self.conn.close()

    def process_command(self, line):
        """Processes a single SMTP command based on session state."""
        
        if self.state == SMTPState.DATA:
            self.handle_data_body(line)
                    
        elif line.upper() == "QUIT":
            self.send_response("221 swmgmail.com closing connection")
            self.state = SMTPState.QUIT

        elif line.upper().startswith("HELO"):
            self.handle_helo(line)
        
        elif self.state == SMTPState.INIT: # Can always restart with HELO
            self.send_response("500 Error: send HELO first")
        
        elif line.upper().startswith("MAIL FROM:"):
            self.handle_mail_from(line)
        
        elif line.upper().startswith("RCPT TO:"):
            self.handle_rcpt_to(line)
        
        elif line.upper() == "DATA":
            self.handle_data_start()
        
        else:
            self.send_response("500 Error: Invalid command sequence")

    def handle_helo(self, line):
        """Handles the HELO command."""
        # clear caches
        self.reset()
        if len(line.split(" ")) != 2:
            self.send_response("501 Syntax: HELO hostname")
        else:
            self.send_response("250 OK Hello swmgmail.com")
            self.state = SMTPState.HELO_DONE

    def handle_mail_from(self, line):
        """Handles the MAIL FROM command."""
        if self.state != SMTPState.HELO_DONE:
            self.send_response("500 Error: send HELO first")
            return
        sender = extract_email(line, can_be_empty=True)
        if sender == "Invalid address":
            self.send_response("500 Error: Invalid address")
        self.sender = sender
        self.send_response("250 OK")
        self.state = SMTPState.MAIL_FROM_DONE

    def handle_rcpt_to(self, line):
        """Handles the RCPT TO command."""
        if self.state not in {SMTPState.MAIL_FROM_DONE, SMTPState.RCPT_TO_DONE}:
            self.send_response("500 Error: send MAIL FROM first")
            return
        recipient = extract_email(line)
        if recipient == "Invalid address":
            self.send_response("500 Error: Invalid address")
            return
        
        username = recipient.split("@")[0]
        domain = recipient.split("@")[1]
        if domain != "swmgmail.com" or username not in get_valid_usernames():
            self.send_response("550 5.1.1 User unknown")
            return

        self.recipients.append(recipient)
        self.send_response("250 OK")
        self.state = SMTPState.RCPT_TO_DONE

    def handle_data_start(self):
        """Handles the start of the DATA command."""
        if self.state != SMTPState.RCPT_TO_DONE:
            self.send_response("500 Error: send RCPT TO first")
            return
        self.send_response("354 End data with <CR><LF>.<CR><LF>")
        self.state = SMTPState.DATA
        self.data_lines = []

    def handle_data_body(self, line):
        """Handles the body of the email message."""
        if line == ".":
            self.finalize_message()
        else:
            self.data_lines.append(line)

    def finalize_message(self):
        """Finalizes and stores the email message."""
        timestamp = datetime.datetime.now().strftime("%m/%d/%Y : %H:%M")
        message = "".join(f"{line}\r\n" for line in self.data_lines[:3]) # First the From, To and Subject lines
        message += f"Received: {timestamp}\r\n" # Then the data line
        message += "".join(f"{line}\r\n" for line in self.data_lines[3:]) # Then the message body
        message += ".\r\n"  # End marker
        
        # Save the message to each recipient's mailbox
        for rec in self.recipients:
            username = rec.split("@")[0]
            os.makedirs(username, exist_ok=True)
            mailbox_path = os.path.join(username, "my_mailbox.txt")
            threading.Thread(target=write_message, args=(message, mailbox_path)).start()

        self.send_response("250 Mail accepted for delivery")
        
        # Reset state for new message
        self.reset()
        self.state = SMTPState.HELO_DONE

def write_message(message, mailbox_path):
    with WRITE_MAIL_LOCK:
        with open(mailbox_path, "a") as f:
            f.write(message)

def extract_email(line: str, can_be_empty=False) -> str:
    # Ensure the command contains '<' and '>'
    start = line.find('<')
    end = line.find('>')
    
    if start == -1 or end == -1 or start > end:
        return "Invalid address"
    
    # Extract the address inside angle brackets
    address = line[start + 1:end]
    
    # Check if source routing is present
    if ':' in address:
        address = address.split(':')[-1]  # Take only the mailbox after the last ':'

    if not can_be_empty and "@" not in address:
        return "Invalid address"
    
    return address


def get_valid_usernames() -> list:
    # no lock since this file is written manually
    usernames = []
    with open('userinfo.txt', "r") as f:
        content = f.read()
    for line in content.splitlines():
        usernames.append(line.split(' ')[0])
    return usernames


class SMTPServer:
    """Manages the SMTP server and client connections."""

    def __init__(self, port):
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(("", port))
        self.server_socket.listen(5)
    
    def start(self):
        """Starts the SMTP server to accept incoming connections."""
        print(f"SMTP Server running on port {self.port}...")
        try:
            while True:
                conn, addr = self.server_socket.accept()
                print(f"Connection established with {addr}")
                threading.Thread(target=self.handle_connection, args=(conn, addr)).start()
        except KeyboardInterrupt:
            print("\nShutting down the SMTP server.")
        finally:
            self.server_socket.close()

    def handle_connection(self, conn, addr):
        """Handles a new SMTP connection."""
        session = SMTPSession(conn, addr)
        session.handle_client()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python mailserver_smtp.py <port>")
        sys.exit(1)

    port = int(sys.argv[1])
    server = SMTPServer(port)
    server.start()
