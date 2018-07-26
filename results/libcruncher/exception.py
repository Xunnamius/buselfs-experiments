"""All of libcruncher's exceptions are defined in this module"""

class ResultPropertyAttributeError(AttributeError):
    def __init__(self, resultPropertyName='?'):
        self.message = 'invalid result property "{}"'.format(resultPropertyName)
        self.resultPropertyName = resultPropertyName
        super().__init__(self.message)

class EmptyResultsSubsetError(RuntimeError):
    def __init__(self):
        self.message = 'inclusion/exclusion procedure returned an empty set (bad include props?)'
        super().__init__(self.message)

class InvalidPathError(RuntimeError):
    def __init__(self, path):
        self.message = '"{}" is not a valid results path'.format(path)
        super().__init__(self.message)

class FilenameTranslationError(RuntimeError):
    def __init__(self, filename):
        self.message = 'failed to translate file name "{}" to ResultProperties object'.format(filename)
        super().__init__(self.message)

class SudoRequired(RuntimeError):
    def __init__(self):
        self.message = 'this script must be run as the root user / with sudo permissions'
        super().__init__(self.message)
