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
import tkinter as tk
from tkinter import messagebox, scrolledtext
import tkinter.font as tkFont
import socket

class MailClient:
    
    def __init__(self, server_ip, smtp_port, pop_port):
        self.server_ip = server_ip
        self.smtp_port = smtp_port
        self.pop_port = pop_port

    def validate_password(self) -> bool:
        s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        s.connect((self.server_ip, self.pop_port))
        s.recv(1024)  # greeting
        s.sendall(f"USER {self.username}\r\n".encode('utf-8'))
        s.recv(1024) # ok message (username always ok)
        s.sendall(f"PASS {self.password}\r\n".encode('utf-8'))
        auth_resp = s.recv(1024).decode('utf-8').strip() # logged in or not message
        s.sendall("QUIT".encode('utf-8'))
        s.recv(1024) # goodbye message
        return auth_resp.startswith("+OK")

    def authenticate(self) -> None:
        while True:
            self.username = input('Enter your swmgmail username: ')
            self.password = input('Enter your swmgmail password: ')
            if self.validate_password():
                print("You're now logged in")
                return
            print("Incorrect username or password!")
    
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
        if "@" not in email or len(email.split("@")) != 2:
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
        if mail_from.split("@")[0] != self.username or mail_from.split("@")[1] != "swmgmail.com":
            print("Can't send mails from other email address")
            return
        rcpt_to = lines[1][4:]
        if rcpt_to.split("@")[1] != "swmgmail.com":
            print("Can currently only send emails to other swmgmail accounts")
            return

        try:
            s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            s.connect((self.server_ip, self.smtp_port))
            s.recv(1024) # ready message

            # SMTP dialogue
            s.sendall(b"HELO client\r\n")
            s.recv(1024)

            # Extract sender and recipient from mail text
            s.sendall(f"MAIL FROM:<{mail_from}>\r\n".encode())
            s.recv(1024)

            s.sendall(f"RCPT TO:<{rcpt_to}>\r\n".encode())
            response = s.recv(1024).decode("utf-8").strip()
            if response.startswith("550"):
                print("Receiver doesn't exist")
                s.sendall(b"QUIT\r\n")
                s.recv(1024)
                s.close()
                return

            s.sendall(b"DATA\r\n")
            s.recv(1024)

            # Send the mail text followed by the termination sequence
            s.sendall((mail_text + "\r\n.\r\n").encode())
            s.recv(1024)

            s.sendall(b"QUIT\r\n")
            s.recv(1024)
            s.close()
            print("Mail sent successfully.\n")
        except Exception as e:
            print("Error sending mail:", e)

    def manage_mail(self):
        raise Exception("Not yet implemented")

    def search_mail(self):
        raise Exception("Not yet implemented")


class MailClientGUI:
    def __init__(self, root, server_ip, smtp_port, pop_port):
        self.root = root
        self.root.title("Mail Client")
        self.root.geometry("400x400")  # Set default window size
        self.root.configure(bg="#f0f0f0")  # Light background

        self.server_ip = server_ip
        self.smtp_port = smtp_port
        self.pop_port = pop_port
        
        self.username = tk.StringVar()
        self.password = tk.StringVar()

        self.default_font = tkFont.Font(family="Arial", size=16)
        
        self.create_login_screen()
    
    def create_login_screen(self):
        self.clear_screen()
        frame = tk.Frame(self.root, padx=20, pady=20, bg="#f0f0f0")
        frame.pack(expand=True)
        
        tk.Label(frame, text="Username:", font=self.default_font, bg="#f0f0f0").pack(anchor="w")
        tk.Entry(frame, textvariable=self.username, font=self.default_font).pack(fill="x", pady=5)
        
        tk.Label(frame, text="Password:", font=self.default_font, bg="#f0f0f0").pack(anchor="w")
        tk.Entry(frame, textvariable=self.password, show="*", font=self.default_font).pack(fill="x", pady=5)
        
        tk.Button(frame, text="Login", font=self.default_font, command=self.authenticate, bg="#4CAF50", fg="white").pack(pady=10)
    
    def authenticate(self):
        username = self.username.get()
        password = self.password.get()
        
        if self.validate_password(username, password):
            messagebox.showinfo("Login", "You're now logged in")
            self.create_main_menu()
        else:
            messagebox.showerror("Login Failed", "Incorrect username or password!")
    
    def validate_password(self, username, password) -> bool:
        try:
            s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            s.connect((self.server_ip, self.pop_port))
            s.recv(1024)
            s.sendall(f"USER {username}\r\n".encode('utf-8'))
            s.recv(1024)
            s.sendall(f"PASS {password}\r\n".encode('utf-8'))
            auth_resp = s.recv(1024).decode('utf-8').strip()
            s.sendall(b"QUIT\r\n")
            s.recv(1024)
            return auth_resp.startswith("+OK")
        except Exception:
            return False
    
    def create_main_menu(self):
        self.clear_screen()
        frame = tk.Frame(self.root, padx=20, pady=20, bg="#f0f0f0")
        frame.pack(expand=True)
        
        tk.Button(frame, text="Send Mail", font=self.default_font, command=self.create_mail_screen, bg="#2196F3", fg="white").pack(pady=10, fill="x")
        tk.Button(frame, text="Exit", font=self.default_font, command=self.root.quit, bg="#f44336", fg="white").pack(pady=10, fill="x")
    
    def create_mail_screen(self):
        self.clear_screen()
        frame = tk.Frame(self.root, padx=20, pady=20, bg="#f0f0f0")
        frame.pack(expand=True)
        
        tk.Label(frame, text="From:", font=self.default_font, bg="#f0f0f0").pack(anchor="w")
        self.sender_entry = tk.Entry(frame, font=self.default_font)
        self.sender_entry.pack(fill="x", pady=5)
        
        tk.Label(frame, text="To:", font=self.default_font, bg="#f0f0f0").pack(anchor="w")
        self.recipient_entry = tk.Entry(frame, font=self.default_font)
        self.recipient_entry.pack(fill="x", pady=5)
        
        tk.Label(frame, text="Subject:", font=self.default_font, bg="#f0f0f0").pack(anchor="w")
        self.subject_entry = tk.Entry(frame, font=self.default_font)
        self.subject_entry.pack(fill="x", pady=5)
        
        tk.Label(frame, text="Message:", font=self.default_font, bg="#f0f0f0").pack(anchor="w")
        self.message_text = scrolledtext.ScrolledText(frame, height=6, font=self.default_font)
        self.message_text.pack(fill="both", pady=5)
        
        tk.Button(frame, text="Send", font=self.default_font, command=self.send_mail, bg="#4CAF50", fg="white").pack(pady=5, fill="x")
        tk.Button(frame, text="Back", font=self.default_font, command=self.create_main_menu, bg="#9E9E9E", fg="white").pack(pady=5, fill="x")
    
    def send_mail(self):
        mail_from = self.sender_entry.get()
        rcpt_to = self.recipient_entry.get()
        subject = self.subject_entry.get()
        message_body = self.message_text.get("1.0", tk.END).strip()
        
        if not mail_from or not rcpt_to or not subject or not message_body:
            messagebox.showerror("Error", "All fields must be filled out.")
            return
        
        try:
            s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            s.connect((self.server_ip, self.smtp_port))
            s.recv(1024)
            s.sendall(b"HELO client\r\n")
            s.recv(1024)
            
            s.sendall(f"MAIL FROM:<{mail_from}>\r\n".encode())
            s.recv(1024)
            s.sendall(f"RCPT TO:<{rcpt_to}>\r\n".encode())
            response = s.recv(1024).decode("utf-8").strip()
            if response.startswith("550"):
                messagebox.showerror("Error", "Receiver doesn't exist")
                s.sendall(b"QUIT\r\n")
                s.recv(1024)
                s.close()
                return
            
            s.sendall(b"DATA\r\n")
            s.recv(1024)
            mail_text = f"From: {mail_from}\r\nTo: {rcpt_to}\r\nSubject: {subject}\r\n\r\n{message_body}\r\n.\r\n"
            s.sendall(mail_text.encode())
            s.recv(1024)
            s.sendall(b"QUIT\r\n")
            s.recv(1024)
            s.close()
            
            messagebox.showinfo("Success", "Mail sent successfully.")
            self.create_main_menu()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send mail: {e}")
    
    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()




def main():
    if len(sys.argv) != 2:
        print("Usage: python mail_client.py <server_IP>")
        sys.exit(1)
    
    server_ip = sys.argv[1]
    smtp_port = 2525
    pop_port = 1100
    
    root = tk.Tk()
    app = MailClientGUI(root, server_ip, smtp_port, pop_port)
    root.mainloop()

if __name__ == "__main__":
    main()
    