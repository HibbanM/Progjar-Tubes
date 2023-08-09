import socket
import threading
import os
import struct


groups = {}
group_files = {}

def handle_client(client_socket, address):
    try:
        username = client_socket.recv(8192).decode('utf-8')
        clients[username] = client_socket
        print(f"{username} connected from {address[0]}:{address[1]}")

        while True:
            data = client_socket.recv(8192)
            if not data:
                break
            message = data.decode('utf-8')
            print(f"Received from {username}: {message}")

            if message.startswith("@unicast"):
                recipient, message_body = message.split(' ', 2)[1], message.split(' ', 2)[2]
                if recipient in clients:
                    send_message(clients[recipient], f"(Unicast) {username}: {message_body}")
            elif message.startswith("@multicast"):
                message_body = message.split(' ', 1)[1]
                for client in clients.values():
                    if client != client_socket:
                        send_message(client, f"(Multicast) {username}: {message_body}")
            elif message.startswith("@broadcast"):
                broadcast(f"(Broadcast) {username}: {message}")
            elif message.startswith("@file_unicast"):
                recipient, file_name, file_size = message.split(' ', 3)[1], message.split(' ', 3)[2], int(message.split(' ', 3)[3])
                if recipient in clients:
                    receive_file(client_socket, username, recipient, file_name, file_size)
            elif message.startswith("@file_multicast"):
                file_name, file_size = message.split(' ', 2)[1], int(message.split(' ', 2)[2])
                for client in clients.values():
                    if client != client_socket:
                        send_file(client, username, file_name, file_size)
            elif message.startswith("@file_broadcast"):
                file_name, file_size = message.split(' ', 2)[1], int(message.split(' ', 2)[2])
                broadcast_file(username, file_name, file_size)
            elif message.startswith("@group_create"):
                group_name = message.split(' ', 1)[1]
                create_group(username, group_name)
            elif message.startswith("@group_add"):
                group_name, members = message.split(' ', 2)[1], message.split(' ', 2)[2]
                add_members_to_group(username, group_name, members)
            elif message.startswith("@group_message"):
                group_name, msg_body = message.split(' ', 2)[1], message.split(' ', 2)[2]
                send_group_message(group_name, username, msg_body)
            elif message.startswith("@file_group"):
                group_name, file_name, file_size = message.split(' ', 3)[1], message.split(' ', 3)[2], int(message.split(' ', 3)[3])
                receive_group_file(client_socket, username, group_name, file_name, file_size)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        client_socket.close()
        del clients[username]

def broadcast(message):
    for client in clients.values():
        client.send(message.encode('utf-8'))

def broadcast_file(sender, file_name, file_size):
    with open(file_name, "rb") as file:
        data = file.read(8192)
        while data:
            broadcast_file_data(sender, file_name, data)
            data = file.read(8192)

def broadcast_file_data(sender, file_name, data):
    for client in clients.values():
        if client != clients[sender]:
            client.send(f"@file {sender} {file_name} {len(data)}".encode('utf-8'))
            client.send(data)

def send_message(client_socket, message):
    client_socket.send(message.encode('utf-8'))

def send_file(client_socket, sender, file_name, file_size):
    client_socket.send(f"@file {sender} {file_name} {file_size}".encode('utf-8'))
    with open(file_name, "rb") as file:
        data = file.read(8192)
        while data:
            client_socket.send(data)
            data = file.read(8192)
    print(f"File {file_name} sent to {client_socket.getpeername()}")

def receive_file(sender_socket, sender, recipient, file_name, file_size):
    with open(file_name, "wb") as file:
        remaining_size = file_size
        while remaining_size > 0:
            data = sender_socket.recv(min(remaining_size, 8192))
            if not data:
                break
            file.write(data)
            remaining_size -= len(data)
    print(f"File {file_name} received from {sender} for {recipient}")

def create_group(creator, group_name):
    groups[group_name] = [creator]
    send_message(clients[creator], f"Group '{group_name}' created successfully!")

def add_members_to_group(creator, group_name, members):
    if group_name in groups:
        members_list = members.split(',')
        for member in members_list:
            if member.strip() in clients and member.strip() not in groups[group_name]:
                groups[group_name].append(member.strip())
                send_message(clients[creator], f"Added '{member.strip()}' to group '{group_name}'")
            else:
                send_message(clients[creator], f"Failed to add '{member.strip()}' to group '{group_name}': User not found or already in the group.")
    else:
        send_message(clients[creator], f"Failed to add members to group '{group_name}': Group not found.")

def send_group_message(group_name, sender, message):
    if group_name in groups:
        members = groups[group_name]
        for member in members:
            if member != sender and member in clients:
                send_message(clients[member], f"(Group '{group_name}') {sender}: {message}")
    else:
        send_message(clients[sender], f"Group '{group_name}' not found.")

def receive_group_file(client_socket, sender, group_name, file_name, file_size):
    with open(file_name, "wb") as file:
        remaining_size = file_size
        while remaining_size > 0:
            data = client_socket.recv(min(remaining_size, 8192))
            if not data:
                break
            file.write(data)
            remaining_size -= len(data)
    print(f"File {file_name} received from {sender} in group '{group_name}'")

HOST = '10.217.20.148'
PORT = 8900

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen(5)
print("Server listening on {}:{}".format(HOST, PORT))

clients = {}

while True:
    client_socket, client_address = server.accept()
    print("Accepted connection from {}:{}".format(client_address[0], client_address[1]))

    client_handler = threading.Thread(target=handle_client, args=(client_socket, client_address))
    client_handler.start()
