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
            s.sendall((mail_text + "\r\n.\r\n").encode("utf-8"))
            s.recv(1024)

            s.sendall(b"QUIT\r\n")
            s.recv(1024)
            s.close()
            print("Mail sent successfully.\n")
        except Exception as e:
            print("Error sending mail:", e)

    def manage_mail(self):
        s = self.start_pop_session()

        s.sendall(b'STAT') #get the amount of emails
        stats = s.recv(1024).decode("utf-8")
        amnt = stats.split(' ')[1]
        amnt = int(amnt)

        for i in range(1, amnt + 1):
            s.sendall(f'RETR {i}'.encode('utf-8'))
            content = s.recv(1024).decode("utf-8")
            summary = summarize_mail(content)
            print(f"{i} {summary}")

        while True:
                print("\nManagement Options:")
                print("1) Get mailbox statistics")
                print("2) List statistics per mail")
                print("3) Retrieve an email")
                print("4) Delete an email")
                print("5) Reset changes")
                print("6) Save changes and quit")
                choice = input("Enter your choice: ")
                if choice == "1":
                    s.sendall(b'STAT') #get the amount of emails
                    stats = s.recv(1024).decode("utf-8")
                    print(stats)
                elif choice == "2":
                    emailno = input('What email would you like to get statistics of? (leave empty for list of all emails)\n')
                    if emailno == '':
                        s.sendall(b'LIST')
                        stats = s.recv(1024).decode("utf-8")
                        print(stats)
                    else:
                        s.sendall(f'LIST {emailno}'.encode())
                        stats = s.recv(1024).decode("utf-8")
                        print(stats)
                elif choice == "3":
                    emailno = input('What email would you like to retrieve?\n')
                    s.sendall(f'RETR {emailno}'.encode())
                    mail = s.recv(1024).decode("utf-8")
                    print(f'\n{mail}')
                elif choice == "4":
                    emailno = input('What email would you like to delete?\n')
                    s.sendall(f'DELE {emailno}'.encode())
                    response = s.recv(1024).decode("utf-8")
                    print(response)
                elif choice == "5":
                    s.sendall(b'RSET')
                    response = s.recv(1024).decode('utf-8')
                    print(response)
                elif choice == "6":
                    s.sendall(b'QUIT')
                    response = s.recv(1024).decode('utf-8')
                    print(response)
                    break
                else:
                    print("Invalid option. Please try again.")

    def search_mail(self):
        s = self.start_pop_session()

        while True:
            print("\nSearching Options:")
            print("1) Search for words/sentences")
            print("2) Search for date")
            print("3) Search for emailadress")
            print("4) Exit")
            choice = input("Enter your choice: ")
            if choice == '1':
                query = input('Enter query: ')
                self.search_query(query, s)
            elif choice == '2':
                date = input('Enter date (in MM/DD/YY): ')
                self.search_date(date, s)
            elif choice == '3':
                adress = input('Enter emailaddress: ')
                self.search_adress(adress, s)
            elif choice == '4':
                s.sendall(b'QUIT')
                s.recv(1024)
                break
            else:
                print('Invalid option. Please try again.')

    def summarize_mail(self, content):
        lines = content.split("\n")
        sender = next((line.split(": ")[1] for line in lines if line.startswith("From:")), "Unknown")
        received = next((line.split(": ")[1] + ": " + line.split(": ")[2] for line in lines if line.startswith("Received:")), "Unknown")
        subject = next((line.split(": ")[1] for line in lines if line.startswith("Subject:")), "No Subject")
        return f"From: {sender} Received: {received} Subject: {subject}"
    
    def summarize_mail_with_recipient(self, content):
        lines = content.split("\n")
        sender = next((line.split(": ")[1] for line in lines if line.startswith("From:")), "Unknown")
        recipient = next((line.split(": ")[1] for line in lines if line.startswith("To:")), "Unknown")
        received = next((line.split(": ")[1] + ": " + line.split(": ")[2] for line in lines if line.startswith("Received:")), "Unknown")
        subject = next((line.split(": ")[1] for line in lines if line.startswith("Subject:")), "No Subject")
        return f"From: {sender} To: {recipient} Received: {received} Subject: {subject}"
    
    def start_pop_session(self):
        authenticated = False
        while not authenticated:
            authenticated = self.validate_password
            if not authenticated:
                print('Username or password invalid, try again.')
                self.authenticate
        
        #start POP3 session
        s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        s.connect((self.server_ip, self.pop_port))
        greeting = s.recv(1024).decode("utf-8")
        print(greeting)
        s.sendall(f"USER {self.username}\r\n".encode('utf-8'))
        s.recv(1024) # ok message (username always ok)
        s.sendall(f"PASS {self.password}\r\n".encode('utf-8'))
        s.recv(1024) # ok message since login has been checked
        return s
    
    def search_query(self, query, s):
        s.sendall(b'STAT') #get the amount of emails
        stats = s.recv(1024).decode("utf-8")
        amnt = stats.split(' ')[1]
        amnt = int(amnt)

        for i in range(1, amnt + 1):
            s.sendall(f'RETR {i}'.encode('utf-8'))
            content = s.recv(1024).decode()
            if query in content:
                print(f'{i}. {self.summarize_mail_with_recipient(content)}')

    def search_date(self, date, s):
        s.sendall(b'STAT') #get the amount of emails
        stats = s.recv(1024).decode("utf-8")
        amnt = stats.split(' ')[1]
        amnt = int(amnt)

        for i in range(1, amnt + 1):
            s.sendall(f'RETR {i}'.encode('utf-8'))
            content = s.recv(1024).decode()
            dateline = content.split('\n')[4]
            if date in dateline:
                print(f'{i}. {self.summarize_mail_with_recipient(content)}')

    def search_adress(self, adress, s):
        s.sendall(b'STAT') #get the amount of emails
        stats = s.recv(1024).decode("utf-8")
        amnt = stats.split(' ')[1]
        amnt = int(amnt)

        for i in range(1, amnt + 1):
            s.sendall(f'RETR {i}'.encode('utf-8'))
            content = s.recv(1024).decode()
            fromLine = content.split('\n')[1]
            toLine = content.split('\n')[2]
            if adress in fromLine or adress in toLine:
                print(f'{i}. {self.summarize_mail_with_recipient(content)}')


class MailClientGUI:
    def __init__(self, root, server_ip, smtp_port, pop_port):
        self.root = root
        self.root.title("Mail Client")
        self.root.geometry("600x600")  # Set default window size
        self.root.configure(bg="#f0f0f0")  # Light background

        self.server_ip = server_ip
        self.smtp_port = smtp_port
        self.pop_port = pop_port
        
        self.username = tk.StringVar()
        self.password = tk.StringVar()

        self.default_font = tkFont.Font(family="Arial", size=16)

        self.pop_connection = None
        
        self.create_login_screen()
    
    def create_login_screen(self):
        self.clear_screen()
        frame = tk.Frame(self.root, padx=20, pady=20, bg="#f0f0f0")
        frame.pack(expand=True)
        
        tk.Label(frame, text="Username:", font=self.default_font, bg="#f0f0f0", fg='#000000').pack(anchor="w")
        tk.Entry(frame, textvariable=self.username, font=self.default_font).pack(fill="x", pady=5)
        
        tk.Label(frame, text="Password:", font=self.default_font, bg="#f0f0f0", fg='#000000').pack(anchor="w")
        tk.Entry(frame, textvariable=self.password, show="*", font=self.default_font).pack(fill="x", pady=5)
        
        tk.Button(frame, text="Login", font=self.default_font, command=self.authenticate, bg="#4CAF50", fg='#000000').pack(pady=10)
    
    def authenticate(self):
        username = self.username.get()
        password = self.password.get()
        
        if self.validate_password(username, password):
            messagebox.showinfo("Login", "You're now logged in")
            self.u = username
            self.p = password
            self.create_main_menu()
        else:
            messagebox.showerror("Login Failed", "Incorrect username or password!")
    
    def validate_password(self, username, password) -> bool:
        try:
            s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            s.connect((self.server_ip, self.pop_port))
            s.recv(1024)
            s.sendall(f"USER {username}".encode('utf-8'))
            s.recv(1024)
            s.sendall(f"PASS {password}".encode('utf-8'))
            auth_resp = s.recv(1024).decode('utf-8').strip()
            s.sendall(b"QUIT")
            s.recv(1024)
            return auth_resp.startswith("+OK")
        except Exception:
            return False
    
    def create_main_menu(self):
        self.clear_screen()
        frame = tk.Frame(self.root, padx=20, pady=20, bg="#f0f0f0")
        frame.pack(expand=True)
        
        tk.Button(frame, text="Send Mail", font=self.default_font, command=self.create_mail_screen, bg="#2196F3", fg='#000000').pack(pady=10, fill="x")
        tk.Button(frame, text="Mail Management", font=self.default_font, command=self.manage_mail, bg="#FF9800", fg="#000000").pack(pady=10, fill="x")
        tk.Button(frame, text="Mail Searching", font=self.default_font, command=self.search_mail, bg="#9C27B0", fg="#000000").pack(pady=10, fill="x")
        tk.Button(frame, text="Exit", font=self.default_font, command=self.root.quit, bg="#f44336", fg='#000000').pack(pady=10, fill="x")
    
    def create_mail_screen(self):
        self.clear_screen()
        frame = tk.Frame(self.root, padx=20, pady=20, bg="#f0f0f0")
        frame.pack(expand=True)
        
        tk.Label(frame, text="To:", font=self.default_font, bg="#f0f0f0", fg='#000000').pack(anchor="w")
        self.recipient_entry = tk.Entry(frame, font=self.default_font)
        self.recipient_entry.pack(fill="x", pady=5)
        
        tk.Label(frame, text="Subject:", font=self.default_font, bg="#f0f0f0", fg='#000000').pack(anchor="w")
        self.subject_entry = tk.Entry(frame, font=self.default_font)
        self.subject_entry.pack(fill="x", pady=5)
        
        tk.Label(frame, text="Message:", font=self.default_font, bg="#f0f0f0", fg='#000000').pack(anchor="w")
        self.message_text = scrolledtext.ScrolledText(frame, height=6, font=self.default_font)
        self.message_text.pack(fill="both", pady=5)
        
        tk.Button(frame, text="Send", font=self.default_font, command=self.send_mail, bg="#4CAF50", fg='#000000').pack(pady=5, fill="x")
        tk.Button(frame, text="Back", font=self.default_font, command=self.create_main_menu, bg="#9E9E9E",fg='#000000').pack(pady=5, fill="x")
    
    def manage_mail(self):
        if self.pop_connection == None:
            self.open_pop_connection()

        self.send_message('STAT') #get the amount of emails
        stats = self.pop_connection.recv(1024).decode("utf-8")
        amnt = stats.split(' ')[1]
        amnt = int(amnt)
        bytes = stats.split(' ')[2].strip('\r\n')

        self.clear_screen()
        frame = tk.Frame(self.root, padx=20, pady=20, bg="#f0f0f0")
        frame.pack(expand=True, fill="both")

        label = tk.Label(frame, text=f"Mailbox: {amnt} Messages ({bytes} Bytes)", font=self.default_font, bg="#f0f0f0", fg="#000000", wraplength=1000)
        label.pack(fill='x', expand=True)


        container = tk.Frame(frame)
        container.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(container)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(container, orient=tk.VERTICAL, command=self.canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.inner_frame = tk.Frame(self.canvas)

        self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

        self.inner_frame.bind("<Configure>", self.on_frame_configure)

        self.send_message('LIST')
        response = self.pop_connection.recv(1024).decode('utf-8')
        mails = response.split('\n')

        for mail in mails[1:]:
            number = mail.split(' ')[0]
            self.send_message(f'RETR {number}')
            content = self.pop_connection.recv(1024).decode("utf-8")
            if not content.startswith('-ERR'):
                summary = f'{number}. {summarize_mail(content)}'
                tk.Button(self.inner_frame, text=summary, font=("Arial", 12), bg="#f0f0f0", fg="#000000", wraplength=400, anchor="w", justify="left", command=lambda number=number: self.view_mail(number, lambda: self.manage_mail())).pack(fill="x", pady=2, expand=True)
        
        tk.Button(frame, text="Reset changes", font=self.default_font, command=lambda: self.reset_changes(), bg="#9E9E9E", fg="#000000").pack(pady=10, fill="x")
        tk.Button(frame, text="Save changes and exit", font=self.default_font, command=lambda: self.save_changes(), bg="#9E9E9E", fg="#000000").pack(pady=10, fill="x")
    
    def close_pop_connection(self):
        self.pop_connection.sendall(b'QUIT\r\n')
        self.pop_connection.recv(1024)
        self.pop_connection.close()
        self.pop_connection = None
    
    def open_pop_connection(self):
        self.pop_connection = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        self.pop_connection.connect((self.server_ip, self.pop_port))
        self.pop_connection.recv(1024)
        self.pop_connection.sendall(f"USER {self.u}\r\n".encode('utf-8'))
        self.pop_connection.recv(1024)
        self.pop_connection.sendall(f"PASS {self.p}\r\n".encode('utf-8'))
        self.pop_connection.recv(1024)
    
    def delete_mail(self, mail_number, callback_fn):
        open_connection = True
        if self.pop_connection is None:
            open_connection = False
            self.open_pop_connection()
        self.pop_connection.sendall(f'DELE {mail_number}'.encode('utf-8'))
        response = self.pop_connection.recv(2024).decode('utf-8')
        if response.startswith('+OK'):
            messagebox.showinfo('Delete', 'Message deleted.')
        else:
            messagebox.showinfo('Delete', 'Something went wrong')
        if not open_connection:
            self.close_pop_connection()
        callback_fn()
    
    def view_mail(self, mail_number, back_fn):
        self.clear_screen()
        frame = tk.Frame(self.root, padx=20, pady=20, bg="#f0f0f0")
        frame.pack(expand=True, fill="both")

        open_connection = True
        if self.pop_connection is None:
            open_connection = False
            self.open_pop_connection()
        self.pop_connection.sendall(f'RETR {mail_number}'.encode('utf-8'))
        content = self.pop_connection.recv(1024).decode()
        if not open_connection:
            self.close_pop_connection()
        lines = content.split('\n')
        email_content = ''

        for line in lines:
            if line.startswith('+OK'):
                bytes = line.split('+OK: ')[1]
            else:
                email_content += f'{line}\n'
        email_content += f'Amount of bytes: {bytes}\n'


        tk.Label(frame, text=email_content, font=("Arial", 12), bg="#f0f0f0", fg="#000000", wraplength=360, anchor="w", justify="left").pack(fill="x", pady=2)
        
        tk.Button(frame, text="Delete", font=self.default_font, command=lambda: self.delete_mail(mail_number, back_fn), bg="#f44336", fg="#000000").pack(pady=10, fill="x")
        tk.Button(frame, text="Back", font=self.default_font, command=back_fn, bg="#9E9E9E", fg="#000000").pack(pady=10, fill="x")
    
    def search_mail(self):
        self.clear_screen()
        frame = tk.Frame(self.root, padx=20, pady=20, bg="#f0f0f0")
        frame.pack(expand=True)
        
        tk.Label(frame, text="Search Emails (enter date as MM/DD/YYYY)", font=self.default_font, bg="#f0f0f0", fg="#000000").pack(pady=10)
        
        self.search_entry = tk.Entry(frame, font=self.default_font)
        self.search_entry.pack(fill="x", pady=5)
        
        button_frame = tk.Frame(frame, bg="#f0f0f0")
        button_frame.pack(pady=5, fill="x")

        tk.Button(button_frame, text="Search by Keyword", font=self.default_font, command=self.perform_search, bg="#4CAF50").pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(button_frame, text="Search by Date", font=self.default_font, command=self.search_by_date, bg="#2196F3").pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(button_frame, text="Search by Sender", font=self.default_font, command=self.search_by_sender, bg="#FF9800").pack(side="left", expand=True, fill="x", padx=2)
        
        self.results_box = scrolledtext.ScrolledText(frame, height=10, font=self.default_font)
        self.results_box.configure(state='disabled')
        self.results_box.pack(fill="both", pady=5)
        
        tk.Button(frame, text="Back", font=self.default_font, command=self.create_main_menu, bg="#9E9E9E").pack(pady=5, fill="x")
    
    def get_all_mails(self):
        self.open_pop_connection()
        self.pop_connection.sendall(b'STAT\r\n')
        stats = self.pop_connection.recv(1024).decode("utf-8")
        amnt = int(stats.split(' ')[1])
        
        self.all_mails = []
        for i in range(1, amnt + 1):
            self.pop_connection.sendall(f'RETR {i}\r\n'.encode('utf-8'))
            self.all_mails.append(self.pop_connection.recv(4096).decode("utf-8"))
        
        self.close_pop_connection()
    
    def get_search_query(self, query=None):
        if query is None:
            query = self.search_entry.get().strip()
        else:
            self.search_mail()
            self.search_entry.insert(0, query)
        return query

    def search_by_date(self, query=None):
        query = self.get_search_query(query)
        if not query:
            messagebox.showerror("Error", "Please enter a search query.")
            return
        self.get_all_mails()
        results = []
        for i, mail in enumerate(self.all_mails):
            dateline = mail.split('\n')[4]
            if query in dateline:
                results.append((i+1, summarize_mail(mail)))
        self.display_results(results, lambda query=query: self.search_by_date(query))

    def search_by_sender(self, query=None):
        query = self.get_search_query(query)
        if not query:
            messagebox.showerror("Error", "Please enter a search query.")
            return
        self.get_all_mails()
        results = []
        for i, mail in enumerate(self.all_mails):
            fromLine = mail.split('\n')[1]
            toLine = mail.split('\n')[2]
            if query in fromLine or query in toLine:
                results.append((i+1, summarize_mail(mail)))
        self.display_results(results, lambda query=query: self.search_by_sender(query))


    def perform_search(self, query=None):
        query = self.get_search_query(query)
        if not query:
            messagebox.showerror("Error", "Please enter a search query.")
            return
        
        self.get_all_mails()
        
        results = []
        for i, mail in enumerate(self.all_mails):
            if query.lower() in mail.lower():
                results.append((i+1, summarize_mail(mail)))
        self.display_results(results, lambda query=query: self.perform_search(query))
    
    def display_results(self, results, back_fn):
        self.results_box.configure(state='normal')
        self.results_box.delete("1.0", tk.END)
        if len(results) != 0:
            inner_frame = tk.Frame(self.results_box)
            self.results_box.window_create(tk.END, window=inner_frame)
            for i, result in results:
                tk.Button(inner_frame, text=result, font=self.default_font, command=lambda i=i: self.view_mail(i, back_fn), bg="#4CAF50").pack(pady=5, fill="x")
        else:
            self.results_box.insert(tk.END, "No emails found.")
        self.results_box.configure(state='disabled')

    def is_valid_email(self, email):
        if "@" not in email or len(email.split("@")) != 2:
            return False
        return True
    
    def send_mail(self):
        mail_from = f"{self.username.get()}@swmgmail.com"
        rcpt_to = self.recipient_entry.get()
        subject = self.subject_entry.get()
        message_body = self.message_text.get("1.0", tk.END).strip()
        
        if not rcpt_to or not subject or not message_body:
            messagebox.showerror("Error", "All fields must be filled out.")
            return
        
        if not self.is_valid_email(rcpt_to):
            messagebox.showerror("Error", "To field is not a valid email.")
            return
        
        if not rcpt_to.split("@")[1] == "swmgmail.com":
            messagebox.showerror("Error", "Can currently only send mail to other swmgmail accounts.")
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
            mail_text = f"From: {mail_from}\r\nTo: {rcpt_to}\r\nSubject: {subject}\r\n{message_body}\r\n.\r\n"
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

    def save_changes(self):
        self.close_pop_connection()
        self.create_main_menu()

    def reset_changes(self):
        self.send_message('RSET')
        self.pop_connection.recv(1024)
        self.manage_mail()

    def on_frame_configure(self, event):
        """Update scroll region when the frame size changes."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def send_message(self, message):
        try: 
            self.pop_connection.sendall(f'{message}\r\n'.encode('utf-8'))
        except:
            messagebox.showerror('Error', 'Connection timed out.')
            self.pop_connection = None
            self.create_login_screen()


def summarize_mail(content):
    lines = content.split("\n")
    sender = next((line.split(": ")[1] for line in lines if line.startswith("From:")), "Unknown")
    received = next((line.split(": ")[1] + ": " + line.split(": ")[2] for line in lines if line.startswith("Received:")), "Unknown")
    subject = next((line.split(": ")[1] for line in lines if line.startswith("Subject:")), "No Subject")
    return f"\nFrom: {sender} \nReceived: {received} \nSubject: {subject}"


def main():
    if len(sys.argv) != 2:
        print("Usage: python mail_client.py <server_IP>")
        sys.exit(1)
    
    server_ip = sys.argv[1]
    smtp_port = 2525
    pop_port = 1100
    
    root = tk.Tk()
    MailClientGUI(root, server_ip, smtp_port, pop_port)
    root.mainloop()

    """client = MailClient(server_ip, smtp_port, pop_port)
    client.start()"""

if __name__ == "__main__":
    main()
