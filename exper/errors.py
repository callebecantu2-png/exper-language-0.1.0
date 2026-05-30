# WHILE e FOR usam exceções para controlar break/continue

class BreakException(Exception):
    pass

class ContinueException(Exception):
    pass

# para retornar de funções 

class ReturnException(Exception):
    def __init__(self, value):
        self.value = value

# para erros personalizados
class ExperError(Exception):

    def __init__(self, message, line=None, code_line=None):

        self.message = message
        self.line = line
        self.code_line = code_line

        text = ""

        if line:
            text += f"Linha {line}\n"

        if code_line:
            text += f">>> {code_line}\n"

        text += message

        super().__init__(text)