import re
from .. import errors as er

# -------- STRUCT --------
def handle_struct(self, lines, i):

    line = lines[i].strip()

    match = re.match(
        r"struct\s+(\w+)\s*{",
        line
    )

    if not match:
        raise Exception("Erro de sintaxe na struct")

    name = match.group(1)

    block, i2 = self.get_block(lines, i)

    fields = []
    defaults = {}

    for item in block:

        item = item.strip()

        if not item:
            continue

        if "=" in item:

            campo, valor = item.split("=", 1)

            campo = campo.strip()
            valor = valor.strip()

            fields.append(campo)
            defaults[campo] = valor

        else:

            fields.append(item)

    self.structs[name] = {
        "fields": fields,
        "defaults": defaults
    }

    return i2 + 1