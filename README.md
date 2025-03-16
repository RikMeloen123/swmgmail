# SWMGMail

This project implements a simple mail system consisting of an SMTP server, a POP3 server, and a graphical mail client. The system allows users to send, receive, search, and manage emails using a local mail server.

## Features

### Mail Client (`mail_client.py`)
- **Send Emails**: Compose and send emails using the SMTP protocol.
- **Receive Emails**: Connect to the POP3 server to fetch received emails.
- **Search Emails**: Search emails by sender, subject, or time.
- **Manage Emails**: List received emails, read messages, and delete emails.
- **Graphical Interface**: A user-friendly Tkinter-based GUI for ease of use.

### SMTP Server (`mailserver_smtp.py`)
- **Handle Email Sending**: Receives emails from clients and stores them in user mailboxes.
- **User Validation**: Ensures that recipients exist before accepting emails.
- **Multi-Threaded**: Supports multiple simultaneous connections.

### POP3 Server (`pop_server.py`)
- **User Authentication**: Validates users against a stored credential file (`userinfo.txt`).
- **Retrieve Emails**: Allows users to list, read, and delete emails from their mailbox.
- **Supports POP3 Commands**: Implements `STAT`, `LIST`, `RETR`, `DELE`, `RSET`, and `QUIT` commands.
- **Concurrent Clients**: Handles multiple client connections using threading.

## Installation & Usage

### Prerequisites
- Python 3.x
- Tkinter (included in standard Python installations)
- Socket library (included in Python standard library)

### Running the Servers

Start the SMTP and POP3 servers before launching the client:

```bash
python mailserver_smtp.py 2525
python pop_server.py 1100
```

### Running the Mail Client

The mail client requires the mail server's IP address as an argument:

```bash
python mail_client.py <server_IP>
```

Replace `<server_IP>` with the actual IP address of the machine running the mail servers, (or localhost for a local server).

## File Structure

```
├── mail_client.py         # GUI-based mail client
├── mailserver_smtp.py     # SMTP server implementation
├── pop_server.py          # POP3 server implementation
├── userinfo.txt           # Stores usernames and passwords
└── <username>/my_mailbox.txt  # Stores emails per user
```

## Future Enhancements
- Add support for emails to different email addresses.
- Improve error handling and security.
- Add support for encryption (TLS/SSL).

