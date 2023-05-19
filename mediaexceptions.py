class InvalidFilenameFormat(Exception):
    def __init__(self, m):
        self.message = m
        super().__init__(m)
    def __str__(self):
        return self.message

class InvalidChannelCount(Exception):
    def __init__(self, m):
        self.message = m
        super().__init__(m)
    def __str__(self):
        return self.message