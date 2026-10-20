
import socket
import threading
import sys

HOST = "0.0.0.0"
PORT = 5000

clients = {}
clients_lock = threading.Lock()


def send_line(sock, lock, message):
    try:
        with lock:
            sock.sendall((message + "\n").encode("utf-8"))
        return True
    except (OSError, BrokenPipeError):
        return False


def broadcast(message, exclude=None):
    with clients_lock:
        targets = list(clients.items())

    for sock, info in targets:
        if sock != exclude:
            send_line(sock, info["lock"], message)


def handle_client(conn, addr):
    reader = None
    name = None

    try:
        conn.settimeout(60)
        reader = conn.makefile("r", encoding="utf-8")
        send_line(conn, threading.Lock(), "Tu nombre:")

        name = reader.readline().strip()[:24]
        if not name:
            return

        conn.settimeout(None)
        info = {"name": name, "lock": threading.Lock()}

        with clients_lock:
            clients[conn] = info

        print(f"[+] {name} conectado desde {addr[0]}")
        broadcast(f"[*] {name} entro al chat")

        for line in reader:
            message = line.strip()
            if not message:
                continue

            if message == "/salir":
                break

            message = message[:1000]
            text = f"{name}: {message}"
            print(text)
            broadcast(text)

    except (OSError, UnicodeError):
        pass
    finally:
        if reader:
            try:
                reader.close()
            except OSError:
                pass

        with clients_lock:
            info = clients.pop(conn, None)

        conn.close()

        if info:
            print(f"[-] {info['name']} desconectado")
            broadcast(f"[*] {info['name']} salio del chat")


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server.bind((HOST, PORT))
        server.listen()
        print(f"Chat activo en el puerto {PORT}")
        print("Esperando conexiones... (Ctrl+C para cerrar)")

        while True:
            conn, addr = server.accept()
            threading.Thread(
                target=handle_client,
                args=(conn, addr),
                daemon=True
            ).start()

    except KeyboardInterrupt:
        print("\nCerrando servidor...")
    finally:
        server.close()


def start_client(ip):
    name = input("Tu nombre: ").strip()[:24]
    if not name or "\n" in name:
        print("Nombre invalido.")
        return

    try:
        sock = socket.create_connection((ip, PORT), timeout=10)
        sock.settimeout(None)
        reader = sock.makefile("r", encoding="utf-8")

        # El servidor pide el nombre antes de aceptar mensajes.
        reader.readline()
        sock.sendall((name + "\n").encode("utf-8"))

    except OSError as e:
        print(f"No se pudo conectar: {e}")
        return

    print(f"\nConectado a {ip}:{PORT}")
    print("Escribi mensajes. Usa /salir para desconectarte.\n")

    def receive():
        try:
            for line in reader:
                print("\r" + line.rstrip() + "\n> ", end="", flush=True)
        except (OSError, UnicodeError):
            pass
        finally:
            print("\nConexion cerrada.")

    threading.Thread(target=receive, daemon=True).start()

    try:
        while True:
            message = input("> ")
            sock.sendall((message + "\n").encode("utf-8"))
            if message.strip() == "/salir":
                break
    except (KeyboardInterrupt, EOFError, OSError):
        pass
    finally:
        sock.close()


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("host", "join"):
        print("Uso:")
        print("  python chat.py host")
        print("  python chat.py join IP_DEL_HOST")
        sys.exit(1)

    if sys.argv[1] == "host":
        start_server()
    elif len(sys.argv) == 3:
        start_client(sys.argv[2])
    else:
        print("Falta la IP del host.")

