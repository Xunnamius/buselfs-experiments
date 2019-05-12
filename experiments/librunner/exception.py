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

class BadResultFileStructureError(RuntimeError):
    def __init__(self, ident, phaseState):
        assert len(phaseState) == 3

        self.message = ('Inconsistent result output for result set `{}`;'.format(ident)
            + ' delete the inconsistent results to continue (missing phases: 1={},2={},3={})'.format(
                'yes' if phaseState[0] else 'no',
                'yes' if phaseState[1] else 'no',
                'yes' if phaseState[2] else 'no'
            ))

        super().__init__(self.message)
