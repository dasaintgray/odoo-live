from datetime import datetime
import sys
sys.path.append("./")
from signalrcore.hub_connection_builder import HubConnectionBuilder
import logging
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)

def input_with_default(input_text, default_value):
    value = input(input_text.format(default_value))
    return default_value if value is None or value.strip() == "" else value

def access_token():
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJodHRwOi8vc2NoZW1hcy54bWxzb2FwLm9yZy93cy8yMDA1LzA1L2lkZW50aXR5L2NsYWltcy9naXZlbm5hbWUiOiJBZG1pbmlzdHJhdG9yIiwiaHR0cDovL3NjaGVtYXMueG1sc29hcC5vcmcvd3MvMjAwNS8wNS9pZGVudGl0eS9jbGFpbXMvbmFtZSI6ImFkbWluIiwiaHR0cDovL3NjaGVtYXMueG1sc29hcC5vcmcvd3MvMjAwNS8wNS9pZGVudGl0eS9jbGFpbXMvbmFtZWlkZW50aWZpZXIiOiIxNDFlYWU1MC0zN2FmLTQ4ZGEtOWRiMS0wNzczYzNmYTU4YjYiLCJuYmYiOjE2NDg3OTc3NzEsImV4cCI6MTY0ODg4NDE3MSwiaXNzIjoiY2lyY3VpdG1pbmR6LmNvbSIsImF1ZCI6ImNpcmN1aXRtaW5kei5jb20ifQ.A-iQxPivKC_trBaIZJdu-rIXn14b0I1Ozx4xP7u02I0"

server_url = input_with_default('Enter your server url(default: {0}): ', "https://cargo-chatsupport.circuitmindz.com/chathub")
username = input_with_default('Enter your username (default: {0}): ', "jtecson")
hub_connection = HubConnectionBuilder()\
    .with_url(
        server_url,
        options={
            "access_token_factory": lambda: access_token(),
            }
    ).with_automatic_reconnect({
            "type": "interval",
            "keep_alive_interval": 3,
            "intervals": [1, 3, 5, 6, 7, 87, 3]}).build()

hub_connection.on_open(lambda: print("FUCKING OPENING"))
hub_connection.on_close(lambda: print("FUCKING CLOSING"))
hub_connection.on_reconnect(lambda: print("FUCKING RECONNECTING"))
hub_connection.on("ReceiveMessage", print)
hub_connection.start()
hub_connection.send("JoinChat", [username])
message = None
# Do login
while message != "exit()":
    message = input(">> ")
    if message is not None and message != "" and message != "exit()":
        message += " - " + str(datetime.now().date()) + " " + str(datetime.now().time())
        while message:
            message += '*'
            hub_connection.send("SendMessage", [username, message])

hub_connection.stop()
sys.exit(0)