import socket
import threading
import subprocess
import os


def send_error(client_socket, error_code, description):
    error_packet = "(EE," + str(error_code) + "," + description + ")"
    client_socket.send(error_packet.encode("utf-8"))
    print("Sent:", error_packet)


def handle_client(client_socket, address):
    print("Handling client:", address)

    # Receive the start packet from the client
    data = client_socket.recv(1024)

    # Convert bytes into a string
    message = data.decode("utf-8")

    print("Received:", message)

    # Separate the packet into its fields
    packet = message.strip("()").split(",")

    print("Packet fields:", packet)

    # Check that the start packet has exactly four fields
    if len(packet) != 4:
        send_error(client_socket, 4, "Invalid packet")
        client_socket.close()
        return

    # Check that this is a valid RFMP start packet
    if packet[0] != "SS" or packet[1] != "RFMP" or packet[2] != "v1.0":
        send_error(client_socket, 4, "Invalid start packet")
        client_socket.close()
        return

    print("Valid RFMP start packet received")

    secure_mode = packet[3]

    # Non-secure setup
    if secure_mode == "0":
        print("Non-secure communication requested")

        confirmation = "(CC)"
        client_socket.send(confirmation.encode("utf-8"))

        print("Sent:", confirmation)

    # Secure setup will be connected to the crypto module later
    elif secure_mode == "1":
        print("Secure communication requested")
        print("Secure setup will be integrated with the crypto module")

    else:
        send_error(client_socket, 4, "Invalid security option")
        client_socket.close()
        return

    # -------------------------
    # OPERATION PHASE
    # -------------------------
    while True:
        data = client_socket.recv(1024)

        # If no data arrives, the client disconnected
        if not data:
            print("Client disconnected:", address)
            break

        message = data.decode("utf-8")
        print("Received:", message)

        # -------------------------
        # CLOSING PHASE
        # -------------------------
        if message == "(End)":
            print("Client ended the connection:", address)
            break

        # Separate the command packet into:
        # packet type, command type, arguments
        command_packet = message.strip("()").split(",", 2)

        # A CM packet should contain exactly three fields
        if len(command_packet) != 3:
            send_error(client_socket, 4, "Invalid packet")
            continue

        packet_type = command_packet[0]
        command_type = command_packet[1]
        arguments = command_packet[2]

        # Make sure this is a Command Message packet
        if packet_type != "CM":
            send_error(client_socket, 4, "Invalid packet type")
            continue

        # -------------------------
        # PROMPT COMMANDS
        # -------------------------
        if command_type == "prompt":
            print("Executing command:", arguments)

            # Separate the command from its arguments
            parts = arguments.split()

            if len(parts) == 0:
                send_error(client_socket, 3, "No command provided")
                continue

            command = parts[0].lower()

            # Commands the server is allowed to execute
            allowed_commands = [
                "mkdir",
                "cd",
                "rmdir",
                "rd",
                "del",
                "ren",
                "dir",
                "type",
                "copy",
                "move",
                "echo"
            ]

            # Reject commands that are not approved
            if command not in allowed_commands:
                send_error(client_socket, 1, "Unknown command")
                continue

            try:
                # cd needs special handling because the server itself
                # must change its current working directory
                if command == "cd":
                    if len(parts) < 2:
                        send_error(
                            client_socket,
                            3,
                            "Directory name required"
                        )
                        continue

                    directory = " ".join(parts[1:])

                    os.chdir(directory)

                    success_packet = "(SC)"
                    client_socket.send(
                        success_packet.encode("utf-8")
                    )

                    print(
                        "Changed directory to:",
                        os.getcwd()
                    )
                    print("Sent:", success_packet)

                # Run all other approved commands
                else:
                    result = subprocess.run(
                        arguments,
                        shell=True,
                        capture_output=True,
                        text=True
                    )

                    if result.returncode == 0:
                        success_packet = "(SC)"
                        client_socket.send(
                            success_packet.encode("utf-8")
                        )

                        print("Command successful")
                        print("Sent:", success_packet)

                    else:
                        send_error(
                            client_socket,
                            3,
                            "Operation failed"
                        )

            except FileNotFoundError:
                send_error(
                    client_socket,
                    2,
                    "File or directory not found"
                )

            except PermissionError:
                send_error(
                    client_socket,
                    3,
                    "Permission denied"
                )

            except Exception as e:
                print("Command error:", e)

                send_error(
                    client_socket,
                    3,
                    "Operation failed"
                )

        elif command_type == "openRead":
            print("openRead requested for:", arguments)

            try:
                # Open the requested file in read mode
                with open(arguments, "r") as file:
                    file_contents = file.read()

                print("File read successfully")

                # Send the file contents in a Data Packet
                data_packet = "(DP," + file_contents + ")"

                client_socket.send(
                    data_packet.encode("utf-8")
                )

                print("Sent file contents")

            

            except FileNotFoundError:
                send_error(
                    client_socket,
                    2,
                    "File not found"
                )

            except PermissionError:
                send_error(
                    client_socket,
                    3,
                    "Permission denied"
                )

            except Exception as e:
                print("openRead error:", e)

                send_error(
                    client_socket,
                    3,
                    "Unable to read file"
                )

        elif command_type == "openWrite":
            print("openWrite requested for:", arguments)

            filename = arguments

            try:
                # First confirm that the server is ready
                success_packet = "(SC)"
                client_socket.send(
                    success_packet.encode("utf-8")
                )

                print("Sent:", success_packet)

                # Now wait for the Data Packet
                data = client_socket.recv(4096)

                if not data:
                    print("Client disconnected")
                    break

                data_message = data.decode("utf-8")

                print("Received:", data_message)

                # Make sure the next packet is a DP packet
                if not data_message.startswith("(DP,"):
                    send_error(
                        client_socket,
                        4,
                        "Expected DP packet"
                    )
                    continue

                # Remove "(DP," from the beginning
                # and ")" from the end
                file_contents = data_message[4:-1]

                # Open/create the file in write mode
                with open(filename, "w") as file:
                    file.write(file_contents)

                print(
                    "File written successfully:",
                    filename
                )

                # Tell the client that writing succeeded
                success_packet = "(SC)"

                client_socket.send(
                    success_packet.encode("utf-8")
                )

                print("Sent:", success_packet)

            except PermissionError:
                send_error(
                    client_socket,
                    3,
                    "Permission denied"
                )

            except Exception as e:
                print("openWrite error:", e)

                send_error(
                    client_socket,
                    3,
                    "Unable to write file"
                )
        else:
            send_error(
                client_socket,
                1,
                "Unknown command type"
            )

    # This happens only after the operation loop ends
    client_socket.close()
    print("Connection closed:", address)


# -------------------------
# SERVER SETUP
# -------------------------

# Create the server socket
server_socket = socket.socket(
    socket.AF_INET,
    socket.SOCK_STREAM
)

# Get the name of this computer
host = socket.gethostname()

# Port number the server will listen on
port = 8888

# Connect the socket to the host and port
server_socket.bind((host, port))

# Start listening for clients
server_socket.listen(5)

print("Server is listening on port " + str(port))


# -------------------------
# ACCEPT CLIENTS
# -------------------------

while True:
    # Wait for a client to connect
    client_socket, address = server_socket.accept()

    print("Client connected:", address)

    # Create a separate thread for this client
    client_thread = threading.Thread(
        target=handle_client,
        args=(client_socket, address)
    )

    # Start the client's thread
    client_thread.start()