import re
from .. import errors as er

def handle_while(self, lines, i):

    line = lines[i].strip()

    match = re.match(r"while\s*\((.*?)\)\s*{", line)

    if not match:
        raise er.ExperError(
            "Erro de sintaxe no while",
            self.current_line,
            self.current_code
        )

    condition = match.group(1).strip()

    block, i2 = self.get_block(lines, i)

    while self.eval_expr(condition):

        try:
            self.run("\n".join(block))

        except er.ContinueException:
            continue

        except er.BreakException:
            break

    return i2 + 1