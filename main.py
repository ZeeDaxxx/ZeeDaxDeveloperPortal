import http.server
import socketserver
import webbrowser

PORT = 8000
DIRECTORY = "."


class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)


def run_server():
    with socketserver.TCPServer(("", PORT), CustomHTTPRequestHandler) as httpd:
        url = f"http://localhost:{PORT}"
        print(f"🚀 Roblox Developer Profile live at: {url}")
        print("Press Ctrl+C in PyCharm to stop the server.")

        webbrowser.open(url)
        httpd.serve_forever()


if __name__ == "__main__":
    run_server()