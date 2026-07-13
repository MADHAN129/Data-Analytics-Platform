import re


def friendly_error(raw: str) -> str:
    if not raw:
        return "Unknown error occurred."

    patterns = [
        (r"Network is unreachable", "Unable to reach the server. Check that the host and port are correct and the database is running."),
        (r"Connection refused", "Connection was refused. The server may not be running or a firewall is blocking access."),
        (r"timed ?out", "Connection timed out. The server is not responding — it may be overloaded or unreachable."),
        (r"connectTimeoutMS|socketTimeoutMS|Timeout", "Connection timed out. The server is not responding — it may be overloaded or unreachable."),
        (r"Access denied|Login failed|Authentication failed|Login incorrect", "Login failed. Please verify your username and password."),
        (r"Unknown database|database.*does not exist|doesn't exist", "The specified database was not found. Check the database name."),
        (r"Can't connect to.*MySQL", "Unable to connect to the MySQL server. Verify the host and port."),
        (r"could not connect to server", "Unable to connect to the database server. Verify the host and port."),
        (r"Topology Description|ServerDescription|AutoReconnect", "Cannot reach the database server. It may be offline or the connection details are wrong."),
        (r"password authentication failed|no password supplied", "Login failed. Please verify your username and password."),
        (r"does not exist", "The specified resource was not found."),
        (r"1065|Query was empty", "The generated SQL query was empty. Please try rephrasing your question."),
    ]

    for pattern, message in patterns:
        if re.search(pattern, raw, re.IGNORECASE):
            return message

    cleaned = re.sub(r"\s+", " ", raw).strip()
    if len(cleaned) > 200:
        cleaned = cleaned[:200] + "..."
    return cleaned
