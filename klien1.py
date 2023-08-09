import socket
import threading
import os
import struct
import math
import time

groups = {}
group_files = {}

def send_message(message):
    client_socket.send(message.encode('utf-8'))

def receive_messages():
    while True:
        try:
            data = client_socket.recv(8192)
            if not data:
                break
            message = data.decode('utf-8')
            if message.startswith("@file"):
                _, sender, file_name, file_size = message.split(' ', 3)
                file_size = int(file_size)
                receive_file(sender, file_name, file_size)
            else:
                print("\n" + message)

                if message.startswith("Group '") and message.endswith("' created successfully!"):
                    group_name = message.split("'")[1]
                    groups[group_name] = []

                elif message.startswith("Added '") and message.endswith("' to group '"):
                    group_name = message.split("'")[3]
                    member = message.split("'")[1]
                    groups[group_name].append(member)

                # Store group files information locally
                elif message.startswith("File ") and message.endswith(" received from "):
                    parts = message.split(' ')
                    group_name = parts[-2][1:-1]
                    file_name = parts[1]
                    if group_name not in group_files:
                        group_files[group_name] = []
                    group_files[group_name].append(file_name)

        except Exception as e:
            print(f"Error: {e}")
            break

def send_messages():
    while True:
        message = input()
        if message.startswith("@file_unicast"):
            _, recipient, file_path = message.split(' ', 2)
            send_file(recipient, file_path)
        elif message.startswith("@file_multicast"):
            _, file_path = message.split(' ', 1)
            send_file("multicast", file_path)
        elif message.startswith("@file_broadcast"):
            _, file_path = message.split(' ', 1)
            send_file("broadcast", file_path)
        elif message.startswith("@unicast"):
            _, recipient, msg_body = message.split(' ', 2)
            send_message(f"@unicast {recipient} {msg_body}")
        elif message.startswith("@multicast"):
            _, msg_body = message.split(' ', 1)
            send_message(f"@multicast {msg_body}")
        elif message.startswith("@broadcast"):
            client_socket.send(message.encode('utf-8'))
        elif message.startswith("@group_create"):
            _, group_name = message.split(' ', 1)
            send_message(f"@group_create {group_name}")
        elif message.startswith("@group_add"):
            _, group_name, members = message.split(' ', 2)
            send_message(f"@group_add {group_name} {members}")
        elif message.startswith("@group_message"):
            _, group_name, msg_body = message.split(' ', 2)
            send_group_message(group_name, msg_body)
        elif message.startswith("@file_group"):
            _, group_name, file_path = message.split(' ', 2)
            send_group_file(group_name, file_path)


def send_file(recipient, file_path):
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    metadata = struct.pack(f"!128si", file_name.encode('utf-8'), file_size)
    if recipient == "multicast":
        message = f"@file_multicast {file_name} {file_size}"
    elif recipient == "broadcast":
        message = f"@file_broadcast {file_name} {file_size}"
    else:
        message = f"@file_unicast {recipient} {file_name} {file_size}"
    client_socket.send(message.encode('utf-8'))
    client_socket.send(metadata)
    with open(file_path, "rb") as file:
        while True:
            data = file.read(8192)
            if not data:
                break
            client_socket.send(data)
        print(f"File {file_name} sent to {recipient}")

def receive_file(sender, file_name, file_size):
    with open(file_name, "wb") as file:
        remaining_size = file_size
        while remaining_size > 0:
            data = client_socket.recv(min(remaining_size, 8192))
            if not data:
                break
            file.write(data)
            remaining_size -= len(data)
        print(f"File {file_name} received from {sender}")



def send_group_message(group_name, message):
    if group_name in groups:
        client_socket.send(f"@group_message {group_name} {message}".encode('utf-8'))
    else:
        print(f"Group '{group_name}' not found.")

def send_group_file(group_name, file_path):
    if group_name in groups:
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        # Send file metadata (file name and size) as binary data
        metadata = struct.pack(f"!128si", file_name.encode('utf-8'), file_size)
        client_socket.send(f"@file_group {group_name}".encode('utf-8') + metadata)

        with open(file_path, "rb") as file:
            while True:
                data = file.read(8192)
                if not data:
                    break
                client_socket.send(data)

        print(f"File {file_name} sent to group '{group_name}'")
    else:
        print(f"Group '{group_name}' not found.")

HOST = '10.217.20.148'
PORT = 8900

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((HOST, PORT))
print("Connected to server")

# Memasukkan username pada awal koneksi
username = input("Enter your username: ")
client_socket.send(username.encode('utf-8'))

print("======MENU=======")
print("1. Unicast Message gunakan @unicast")
print("2. broadcast Message gunakan @broadcast")
print("3. Unicast File gunakan @file_unicast")
print("4. broadcast File gunakan @file_broadcast")
print("Untuk Melakukan Multicast lakukan langkah dibawah ini")
print("5. @group_create nama_group")
print("6. @group_add nama_group nick")
print("7. @group_message nama_group messag")
print("8. @file_group nama_group file")

receive_thread = threading.Thread(target=receive_messages)
send_thread = threading.Thread(target=send_messages)

receive_thread.start()
send_thread.start()

receive_thread.join()
send_thread.join()

client_socket.close()