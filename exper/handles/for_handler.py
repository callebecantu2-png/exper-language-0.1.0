import re
from .. import errors as er

def handle_for(self, lines, i):
    line = lines[i].strip()

    # ===== FOR CLÁSSICO =====
    m = re.match(r"for\s*\((.*)\)\s*{", line)
    if m:
        parts = m.group(1).split(";")

        if len(parts) != 3:
            raise er.ExperError(
                "Erro de sintaxe no for",
                self.current_line,
                self.current_code
            )

        init, cond, inc = parts

        self.run(init.strip())
        block, i2 = self.get_block(lines, i)

        while self.eval_expr(cond.strip()):

            try:
                self.run("\n".join(block))

            except er.ContinueException:
                self.run(inc.strip())
                continue

            except er.BreakException:
                break

            self.run(inc.strip())

        return i2 + 1