// client.c - RFMP C client (non-secure, openRead only) for Windows
// Stage 4: connect, setup phase (SS/CC), openRead, then the closing phase (End)
#include <stdio.h>
#include <string.h>
#include <winsock2.h>
#include <ws2tcpip.h>

#define PORT "8888"
#define BUFFER_SIZE 4096

// Checks the server's final reply after a command (SC = success, EE = error)
void check_final_response(const char *reply) {
    if (strcmp(reply, "(SC)") == 0) {
        printf("Server confirmed: success\n");
    } else if (strncmp(reply, "(EE,", 4) == 0) {
        printf("Server error: %s\n", reply);
    } else {
        printf("Unexpected reply: %s\n", reply);
    }
}

int main() {
    WSADATA wsa;
    SOCKET s;
    struct addrinfo hints, *result;
    struct sockaddr_in *addr;
    char host[256];
    char filename[256];
    char packet[512];
    char buffer[BUFFER_SIZE];
    int received;

    // Start Winsock (needed on Windows before using sockets)
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        printf("Winsock failed to start\n");
        return 1;
    }

    // Look up this computer's name the same way the Python server does (IPv4, TCP)
    gethostname(host, sizeof(host));
    memset(&hints, 0, sizeof(hints));
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_STREAM;
    if (getaddrinfo(host, PORT, &hints, &result) != 0) {
        printf("Could not find the server host\n");
        WSACleanup();
        return 1;
    }

    addr = (struct sockaddr_in *)result->ai_addr;
    printf("Trying %s on port %s\n", inet_ntoa(addr->sin_addr), PORT);

    // Create a TCP socket
    s = socket(result->ai_family, result->ai_socktype, result->ai_protocol);
    if (s == INVALID_SOCKET) {
        printf("Could not create socket\n");
        WSACleanup();
        return 1;
    }

    // Connect to the server
    if (connect(s, result->ai_addr, (int)result->ai_addrlen) == SOCKET_ERROR) {
        printf("Could not connect (error %d). Is the server running?\n", WSAGetLastError());
        closesocket(s);
        WSACleanup();
        return 1;
    }
    printf("Connected to the server\n");
    freeaddrinfo(result);

    // ---------- SETUP PHASE ----------
    // Start packet: protocol RFMP, version v1.0, 0 = no security
    strcpy(packet, "(SS,RFMP,v1.0,0)");
    send(s, packet, strlen(packet), 0);

    // Wait for the server's reply, which should be (CC)
    received = recv(s, buffer, BUFFER_SIZE - 1, 0);
    if (received <= 0) {
        printf("No reply from the server\n");
        closesocket(s);
        WSACleanup();
        return 1;
    }
    buffer[received] = '\0';

    if (strcmp(buffer, "(CC)") != 0) {
        printf("Expected (CC), got: %s\n", buffer);
        closesocket(s);
        WSACleanup();
        return 1;
    }
    printf("Server confirmed the connection\n");

    // ---------- OPERATION PHASE: openRead ----------
    printf("File name to read: ");
    fgets(filename, sizeof(filename), stdin);
    filename[strcspn(filename, "\n")] = '\0';     // remove the newline from fgets

    // Command packet: (CM,openRead,filename)
    sprintf(packet, "(CM,openRead,%s)", filename);
    send(s, packet, strlen(packet), 0);

    // The server answers with a Data Packet (DP) or an Exception packet (EE)
    received = recv(s, buffer, BUFFER_SIZE - 1, 0);
    if (received > 0) {
        buffer[received] = '\0';

        if (strncmp(buffer, "(DP,", 4) == 0) {
            int got_sc = 0;

            // TCP can deliver "(DP,text)(SC)" in one recv, so check for that first
            if (received >= 4 && strcmp(buffer + received - 4, "(SC)") == 0) {
                received = received - 4;      // cut the (SC) off the end
                buffer[received] = '\0';
                got_sc = 1;
            }

            // Print what is between "(DP," and the final ")"
            buffer[received - 1] = '\0';
            printf("----- file contents -----\n%s\n", buffer + 4);

            if (got_sc) {
                printf("Server confirmed: success\n");
            } else {
                // The (SC) came separately, so receive it now
                received = recv(s, buffer, BUFFER_SIZE - 1, 0);
                if (received > 0) {
                    buffer[received] = '\0';
                    check_final_response(buffer);
                } else {
                    printf("No final reply from the server\n");
                }
            }
        } else if (strncmp(buffer, "(EE,", 4) == 0) {
            printf("Server error: %s\n", buffer);
        } else {
            printf("Unexpected reply: %s\n", buffer);
        }
    } else {
        printf("No reply from the server\n");
    }

    // ---------- CLOSING PHASE ----------
    // Tell the server we are finished
    strcpy(packet, "(End)");
    send(s, packet, strlen(packet), 0);
    printf("Sent (End), connection closed\n");

    closesocket(s);
    WSACleanup();
    return 0;
}