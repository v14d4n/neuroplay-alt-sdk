class NeuroPlayExceptionNotValidDevice(Exception):
    def __init__(self, message="Not a valid device"):
        super().__init__(message)
