"""All of librunner's exceptions are defined in this module"""

class CommandExecutionError(RuntimeError):
    def __init__(self, message, exitcode='?'):
        self.message = message or 'non-zero error code encountered ({})'.format(exitcode)
        self.exitcode = 256 if exitcode == '?' else exitcode
        super().__init__(message)

class TaskError(RuntimeError):
    def __init__(self, message):
        self.message = message
        super().__init__(message)

class ExperimentError(RuntimeError):
    def __init__(self, message):
        self.message = message
        super().__init__(message)
