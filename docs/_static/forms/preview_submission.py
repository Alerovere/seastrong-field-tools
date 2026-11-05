"""Serve this folder on localhost for the Google-authorised development origin."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import webbrowser


def main():
    folder = Path(__file__).resolve().parent
    handler = partial(SimpleHTTPRequestHandler, directory=str(folder))
    try:
        server = ThreadingHTTPServer(("127.0.0.1", 8000), handler)
    except OSError:
        raise SystemExit("La porta 8000 e gia in uso. Chiudi l'altra anteprima e riprova.")
    print("SEASTRONG: http://localhost:8000/\nLascia aperta questa finestra. Ctrl+C per chiudere.")
    webbrowser.open("http://localhost:8000/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
