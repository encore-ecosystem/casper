class Client:
    def __init__(self, server_ip: str, server_port: str):
        self.server_ip   = server_ip
        self.server_port = server_port


__all__ = [
    'Client',
]