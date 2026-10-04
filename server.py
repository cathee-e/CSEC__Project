import socket
import threading
import subprocess
import os

# Import the cryptography functions used for secure communication.
from crypto_module import rsa_generate_keypair, rsa_decrypt, encrypt, decrypt


# --------------------------------------------------
# ERROR HANDLING
# --------------------------------------------------

def send_error(client_socket, error_code, description):
    # Build an EE (Error) packet and send it to the client.
    error_packet = "(EE," + str(error_code) + "," + description + ")"
    client_socket.send(error_packet.encode("utf-8"))
    print("Sent:", error_packet)


# --------------------------------------------------
# CLIENT HANDLER
# --------------------------------------------------

def handle_client(client_socket, address):
    print("Handling client:", address)

    # These remain empty for non-secure communication.
    # In secure mode they store the chosen algorithm and session key.
    algorithm = ""
    session_key = ""

    # --------------------------------------------------
    # SETUP PHASE
    # --------------------------------------------------

    # Receive the client's Start Session packet.
    data = client_socket.recv(1024)

    if not data:
        print("Client disconnected during setup:", address)
        return

    message = data.decode("utf-8")
    print("Received:", message)

    # RFMP packets are surrounded by one pair of parentheses.
    # [1:-1] removes exactly those outer characters.
    packet = message[1:-1].split(",")

    print("Packet fields:", packet)

    # A valid SS packet must contain four fields:
    # SS, RFMP, version, secure mode
    if len(packet) != 4:
        send_error(client_socket, 4, "Invalid packet")
        return

    if packet[0] != "SS" or packet[1] != "RFMP" or packet[2] != "v1.0":
        send_error(client_socket, 4, "Invalid start packet")
        return

    print("Valid RFMP start packet received")

    secure_mode = packet[3]

    # -------------------------
    # NON-SECURE SETUP
    # -------------------------

    if secure_mode == "0":
        print("Non-secure communication requested")

        # No public key is required for a non-secure connection.
        confirmation = "(CC)"
        client_socket.send(confirmation.encode("utf-8"))

        print("Sent:", confirmation)

    # -------------------------
    # SECURE SETUP
    # -------------------------

    elif secure_mode == "1":
        print("Secure communication requested")

        try:
            # Generate a separate RSA key pair for this connection.
            public_key, private_key = rsa_generate_keypair()

            print("RSA key pair generated")

            # The client needs the server's public key so it can
            # securely encrypt the session key.
            confirmation = "(CC," + public_key + ")"
            client_socket.send(confirmation.encode("utf-8"))

            print("Sent:", confirmation)

            # Wait for the client's Encryption Configuration packet.
            data = client_socket.recv(4096)

            if not data:
                print("Client disconnected during secure setup")
                return

            ec_message = data.decode("utf-8")
            print("Received:", ec_message)

            # EC packet format:
            # (EC,algorithm,encrypted_session_key,username:public_key)
            ec_packet = ec_message[1:-1].split(",", 3)

            if len(ec_packet) != 4 or ec_packet[0] != "EC":
                send_error(
                    client_socket,
                    4,
                    "Invalid EC packet"
                )
                return

            algorithm = ec_packet[1]
            encrypted_session_key = ec_packet[2]

            # The project supports AES and Caesar encryption.
            if algorithm != "AES" and algorithm != "CAESAR":
                send_error(
                    client_socket,
                    4,
                    "Invalid encryption algorithm"
                )
                return

            # The client encrypted the session key using our public key.
            # Only the matching private key can decrypt it.
            session_key = rsa_decrypt(
                encrypted_session_key,
                private_key
            )

            print("Secure setup complete")
            print("Algorithm:", algorithm)

        except Exception as e:
            print("Secure setup error:", e)

            send_error(
                client_socket,
                4,
                "Secure setup failed"
            )
            return

    else:
        send_error(
            client_socket,
            4,
            "Invalid security option"
        )
        return

    # --------------------------------------------------
    # OPERATION PHASE
    # --------------------------------------------------

    while True:
        data = client_socket.recv(1024)

        # recv() returning no data means the client disconnected.
        if not data:
            print("Client disconnected:", address)
            break

        message = data.decode("utf-8")
        print("Received:", message)

        # --------------------------------------------------
        # CLOSING PHASE
        # --------------------------------------------------

        if message == "(End)":
            print("Client ended the connection:", address)
            break

        # CM packet format:
        # (CM,command_type,arguments)
        #
        # split(",", 2) is important because the arguments themselves
        # may contain additional characters.
        command_packet = message[1:-1].split(",", 2)

        if len(command_packet) != 3:
            send_error(
                client_socket,
                4,
                "Invalid packet"
            )
            continue

        packet_type = command_packet[0]
        command_type = command_packet[1]
        arguments = command_packet[2]

        if packet_type != "CM":
            send_error(
                client_socket,
                4,
                "Invalid packet type"
            )
            continue

        # --------------------------------------------------
        # PROMPT COMMANDS
        # --------------------------------------------------

        if command_type == "prompt":
            print("Executing command:", arguments)

            parts = arguments.split()

            if len(parts) == 0:
                send_error(
                    client_socket,
                    3,
                    "No command provided"
                )
                continue

            command = parts[0].lower()

            # Six required command names plus five additional
            # commands supported by this server.
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

            if command not in allowed_commands:
                send_error(
                    client_socket,
                    1,
                    "Unknown command"
                )
                continue

            try:
                # cd must be handled separately because changing
                # directories affects the Python server process itself.
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

                    print("Changed directory to:", os.getcwd())
                    print("Sent:", success_packet)

                else:
                    # Execute the other approved commands through
                    # the operating system shell.
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

        # --------------------------------------------------
        # OPEN READ
        # --------------------------------------------------

        elif command_type == "openRead":
            print("openRead requested for:", arguments)

            try:
                # Read the requested file.
                with open(arguments, "r") as file:
                    file_contents = file.read()

                print("File read successfully")

                # Secure connections encrypt the file before it
                # travels across the network.
                if secure_mode == "1":
                    file_contents = encrypt(
                        file_contents,
                        algorithm,
                        session_key
                    )

                # Send the file contents in a Data Packet.
                data_packet = "(DP," + file_contents + ")"

                client_socket.send(
                    data_packet.encode("utf-8")
                )

                print("Sent file contents")

                # Tell the client that openRead completed successfully.
                success_packet = "(SC)"
                client_socket.send(
                    success_packet.encode("utf-8")
                )

                print("Sent:", success_packet)

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

        # --------------------------------------------------
        # OPEN WRITE
        # --------------------------------------------------

        elif command_type == "openWrite":
            print("openWrite requested for:", arguments)

            filename = arguments

            try:
                # First tell the client that the server is ready
                # to receive the Data Packet.
                success_packet = "(SC)"

                client_socket.send(
                    success_packet.encode("utf-8")
                )

                print("Sent:", success_packet)

                # Receive the DP packet containing the file contents.
                data = client_socket.recv(4096)

                if not data:
                    print("Client disconnected")
                    break

                data_message = data.decode("utf-8")
                print("Received:", data_message)

                if not data_message.startswith("(DP,"):
                    send_error(
                        client_socket,
                        4,
                        "Expected DP packet"
                    )
                    continue

                # Remove "(DP," and the final ")".
                file_contents = data_message[4:-1]

                # In secure mode the client encrypted the contents,
                # so decrypt them before writing the file.
                if secure_mode == "1":
                    file_contents = decrypt(
                        file_contents,
                        algorithm,
                        session_key
                    )

                with open(filename, "w") as file:
                    file.write(file_contents)

                print(
                    "File written successfully:",
                    filename
                )

                # Confirm that the file was successfully written.
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

    print("Finished handling client:", address)


# --------------------------------------------------
# SAFE CLIENT WRAPPER
# --------------------------------------------------

def safe_handle_client(client_socket, address):
    """
    Runs handle_client safely.

    If a client closes unexpectedly, ConnectionResetError or
    BrokenPipeError may occur. Catching them prevents an unnecessary
    traceback from appearing while the server continues running.

    finally guarantees that the socket is closed when this client's
    thread finishes.
    """
    try:
        handle_client(client_socket, address)

    except (ConnectionResetError, BrokenPipeError):
        print("Connection lost:", address)

    finally:
        client_socket.close()
        print("Connection closed:", address)


# --------------------------------------------------
# SERVER SETUP
# --------------------------------------------------

# Create the TCP server socket.
server_socket = socket.socket(
    socket.AF_INET,
    socket.SOCK_STREAM
)

host = socket.gethostname()
port = 8888

# Allow the port to be reused quickly after restarting the server.
# This helps avoid "address already in use" errors during testing.
server_socket.setsockopt(
    socket.SOL_SOCKET,
    socket.SO_REUSEADDR,
    1
)

# Bind the socket to this computer and port.
server_socket.bind((host, port))

# Allow incoming client connections.
server_socket.listen(5)

print("Server is listening on port " + str(port))


# --------------------------------------------------
# ACCEPT CLIENTS
# --------------------------------------------------

while True:
    # Wait until a client connects.
    client_socket, address = server_socket.accept()

    print("Client connected:", address)

    # Every client gets its own thread, allowing the server
    # to handle multiple clients at the same time.
    client_thread = threading.Thread(
        target=safe_handle_client,
        args=(client_socket, address)
    )

    client_thread.start()