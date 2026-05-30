import re
from .. import errors as er

# -------- CONTROLE --------
def handle_if(self, lines, i):

    executed = False

    while i < len(lines):

        line = lines[i].strip()

        # ================= IF / ELIF =================
        if line.startswith("if") or line.startswith("elif"):

            match = re.match(r"(if|elif)\s*\((.*)\)\s*{", line)

            if not match:
                raise er.ExperError(
                    "Erro de sintaxe no if",
                    self.current_line,
                    self.current_code
                )

            condition = match.group(2)

            block, i2 = self.get_block(lines, i)

            if not executed and self.eval_expr(condition):

                executed = True

                self.run("\n".join(block))

            i = i2 + 1
            continue

        # ================= ELSE =================
        elif line.startswith("else"):

            block, i2 = self.get_block(lines, i)

            if not executed:
                self.run("\n".join(block))

            return i2 + 1

        break

    return i