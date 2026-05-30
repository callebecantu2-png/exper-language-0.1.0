import re
from .. import errors as er

# -------- FUNCTION --------
def handle_function(self, lines, i):

    line = lines[i].strip()

    match = re.match(r"fn\s+(\w+)\((.*?)\)\s*{", line)

    if not match:
        raise er.ExperError(
            "Erro de sintaxe na função",
            self.current_line,
            self.current_code
        )

    name = match.group(1)

    params_raw = match.group(2).strip()

    params = []
    defaults = {}

    if params_raw:

        raw_params = [p.strip() for p in params_raw.split(",")]

        for p in raw_params:

            # parâmetro com valor padrão
            if "=" in p:

                pname, default = p.split("=", 1)

                pname = pname.strip()
                default = default.strip()

                params.append(pname)
                defaults[pname] = default

            else:
                params.append(p)

    block, i2 = self.get_block(lines, i)

    self.functions[name] = {
        "params": params,
        "defaults": defaults,
        "block": block
    }

    return i2 + 1