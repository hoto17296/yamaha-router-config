class Nat:
    def __init__(self, descriptor: int, type: str):
        self.descriptor = descriptor
        self.type = type
        self.commands: list[str] = [f"nat descriptor type {descriptor} {type}"]

    def add(self, command: str):
        self.commands.append(command)
