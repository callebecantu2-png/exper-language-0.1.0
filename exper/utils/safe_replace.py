import re

def safe_replace(self, expr):
    result = ""
    in_string = False
    quote = ""

    i = 0
    while i < len(expr):
        char = expr[i]

        if char in ["'", '"']:
            if not in_string:
                in_string = True
                quote = char
            elif quote == char:
                in_string = False

            result += char
            i += 1
            continue

        if not in_string and re.match(r"[a-zA-Z_]", char):
            j = i
            while j < len(expr) and re.match(r"\w", expr[j]):
                j += 1

            var = expr[i:j]

            # palavras reservadas booleanas/lógicas
            if var in ["True", "False", "and", "or", "not"]:
                result += var
                i = j
                continue

            if var in self.vars and not in_string:

                # não substituir em acessos tipo pessoa.nome
                if j < len(expr) and expr[j] == ".":
                    result += var

                else:

                    val = self.vars[var]

                    if isinstance(val, str):
                        result += f'"{val}"'
                    else:
                        result += str(val)
            else:
                result += var

            i = j
        else:
            result += char
            i += 1

    return result