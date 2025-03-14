import socket
import sys

MESSAGE_SIZE = 1024

def main():
    if len(sys.argv) != 2:
        print("Usage: python mail_client.py <server_IP>")
        sys.exit(1)
    server_ip = sys.argv[1]
    smtp_port = 2525
    pop_port = 1101
    s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM) 
    s.connect((server_ip, pop_port))

    #initial hello from server
    message = s.recv(MESSAGE_SIZE).decode()
    print(message)

    #get username, send to server, and wait for response
    while True:
        temp = input()
        if temp != "":
            s.sendall(temp.encode())
            response = s.recv(MESSAGE_SIZE).decode()
            print(response)
        
    

if __name__ == "__main__":
    main()