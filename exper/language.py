import re
import os
import time

from . import handles as hds
from . import debug as dbg
from . import errors as er
from . import utils

# ================= LINGUAGEM =================
class Exper:
    def __init__(self):
        self.vars = {}
        self.functions = {}
        self.structs = {}

    handle_if = hds.handle_if
    handle_for = hds.handle_for
    handle_while = hds.handle_while
    handle_function = hds.handle_function
    handle_struct = hds.handle_struct

    # -------- EXPRESSÕES --------
    def eval_expr(self, expr):
        expr = expr.strip()
        original_expr = expr
        dbg.debug("Evaluating:", expr)

        # -------- STRING COM INTERPOLAÇÃO MELHORADA --------
        if (expr.startswith('"') and expr.endswith('"')) or (expr.startswith("'") and expr.endswith("'")):
            string = expr[1:-1]

            def replace_var(match):
                inner = match.group(1)

                try:
                    return str(self.eval_expr(inner))
                except:
                    return match.group(0)

            # suporta QUALQUER expressão dentro {}
            while True:
                new_string = re.sub(r"\{([^{}]+)\}", replace_var, string)
                if new_string == string:
                    break
                string = new_string

            return string
        
        # evita eval quebrar com variáveis simples
        if expr in self.vars:
            return self.vars[expr]  
        
        # -------- OBJ.ATRIBUTO --------
        match = re.fullmatch(
            r"(\w+)\.(\w+)",
            expr
        )

        if match:

            obj = match.group(1)
            field = match.group(2)

            if obj in self.vars:

                value = self.vars[obj]

                if isinstance(value, dict):

                    if field in value:
                        return value[field]
        
        
        # console.input()
        if expr.startswith("console.input("):
            return self.call_function(expr)
        
        # int()
        if expr.startswith("int("):
            return self.call_function(expr)

        # float()
        if expr.startswith("float("):
            return self.call_function(expr)

        # str()
        if expr.startswith("str("):
            return self.call_function(expr)
        
        # -------- ANY --------
        match = re.fullmatch(r"any\((.*)\)", expr)

        if match:
            val = self.eval_expr(match.group(1))
            return any(val)

        # -------- ALL --------
        match = re.fullmatch(r"all\((.*)\)", expr)

        if match:
            val = self.eval_expr(match.group(1))
            return all(val)

        # -------- MULTI IN --------
        match = re.fullmatch(r"(\[.*\])\s+in\s+(.+)", expr)

        if match:
            left_expr = match.group(1)
            right_expr = match.group(2)

            left = self.eval_expr(left_expr)
            right = self.eval_expr(right_expr)

            result = []

            for item in left:
                result.append(item in right)

            dbg.debug("MULTI IN ->", result)

            return result

        # -------- IN NORMAL --------
        match = re.fullmatch(r"(.+?)\s+in\s+(.+)", expr)

        if match:
            left = self.eval_expr(match.group(1))
            right = self.eval_expr(match.group(2))

            result = left in right

            dbg.debug("IN ->", result)

            return result

        expr = utils.safe_replace(self, expr)

        dbg.debug("Depois do safe replace:", expr)

        # -------- .length --------
        expr = re.sub(
            r"([a-zA-Z_]\w*|\[[^\]]*\]|\([^\)]*\))\.length",
            r"len(\1)",
            expr
        )

        # -------- INDEX --------
        match = re.fullmatch(r"(\w+)\[(.*)\]", expr)
        if match:
            var = match.group(1)
            index = self.eval_expr(match.group(2))
            return self.vars[var][index]

        # -------- STRING METHODS --------
        for pattern, func in [
            (r"(.+)\.trim\(\)", lambda v: str(v).strip()),
            (r"(.+)\.upper\(\)", lambda v: str(v).upper()),
            (r"(.+)\.lower\(\)", lambda v: str(v).lower()),
            (r"(.+)\.capitalize\(\)", lambda v: str(v).capitalize()),
        ]:
            m = re.fullmatch(pattern, expr)
            if m:
                return func(self.eval_expr(m.group(1)))

        # replace
        m = re.fullmatch(r"(.+)\.replace\((.*),(.*)\)", expr)
        if m:
            v = self.eval_expr(m.group(1))
            a = self.eval_expr(m.group(2))
            b = self.eval_expr(m.group(3))
            return str(v).replace(a, b)

        # split
        m = re.fullmatch(r"(.+)\.split\((.*)\)", expr)
        if m:
            v = self.eval_expr(m.group(1))
            sep = self.eval_expr(m.group(2))
            return str(v).split(sep)

        # join
        m = re.fullmatch(r"(.+)\.join\((.*)\)", expr)
        if m:
            iterable = self.eval_expr(m.group(1))
            sep = self.eval_expr(m.group(2))
            return str(sep).join(map(str, iterable))
        
        # -------- console.input dentro de expressão --------
        match = re.fullmatch(r"console\.input\((.*)\)", expr)
        if match:
            content = match.group(1)
            prompt = self.eval_expr(content) if content else ""
            result = input(prompt)
            dbg.debug("INPUT ->", result)
            return result
        
        expr = expr.replace("xor", " ^")
        expr = expr.replace("&&", " and ")
        expr = expr.replace("||", " or ")
        expr = re.sub(r"!\s*(?!=)", " not ", expr)
        
        # any(...)
        if expr.startswith("any("):
            return self.call_function(expr)

        # all(...)
        if expr.startswith("all("):
            return self.call_function(expr)
        
        # -------- FUNCTION CALL --------
        match = re.fullmatch(r"(\w+)\((.*)\)", expr)

        if match:

            name = match.group(1)

            args_raw = match.group(2).strip()

            # ignora builtins
            builtins = [
                "int",
                "float",
                "str",
                "any",
                "all",
                "console"
            ]

            if name not in builtins and name in self.functions:

                func = self.functions[name]

                params = func["params"]
                defaults = func["defaults"]
                block = func["block"]

                positional_args = []
                named_args = {}

                # ===== ARGUMENTOS =====
                if args_raw:

                    raw_args = [a.strip() for a in utils.split_args(args_raw)]

                    for arg in raw_args:

                        # nomeado
                        if "=" in arg:

                            k, v = arg.split("=", 1)

                            named_args[k.strip()] = self.eval_expr(v.strip())

                        else:
                            positional_args.append(
                                self.eval_expr(arg)
                            )

                # ===== ESCOPO =====
                old_vars = self.vars.copy()

                # ===== PARÂMETROS =====
                pos_index = 0

                for p in params:

                    # argumento nomeado
                    if p in named_args:

                        self.vars[p] = named_args[p]

                    # argumento posicional
                    elif pos_index < len(positional_args):

                        self.vars[p] = positional_args[pos_index]
                        pos_index += 1

                    # valor padrão
                    elif p in defaults:

                        self.vars[p] = self.eval_expr(defaults[p])

                    else:
                        raise er.ExperError(
                            f"Parâmetro obrigatório faltando: {p}",
                            self.current_line,
                            self.current_code
                        )

                try:
                    self.run("\n".join(block))

                except er.ReturnException as r:

                    self.vars = old_vars

                    return r.value

                self.vars = old_vars

                return None
            
        # -------- FUNCTIONS INSIDE EXPRESSIONS --------
        while True:

            found = False

            for name in self.functions:

                search = f"{name}("

                start = expr.find(search)

                if start == -1:
                    continue

                # ===== PEGA ARGUMENTOS =====
                pos = start + len(search)

                depth = 1

                args_raw = ""

                while pos < len(expr):

                    char = expr[pos]

                    if char == "(":
                        depth += 1

                    elif char == ")":
                        depth -= 1

                        if depth == 0:
                            break

                    args_raw += char
                    pos += 1

                full_call = expr[start:pos+1]

                positional_args = []
                named_args = {}

                # ===== PARSE ARGUMENTOS =====
                if args_raw.strip():

                    raw_args = []
                    current = ""
                    depth2 = 0
                    in_string = False
                    quote = ""

                    for c in args_raw:

                        if c in ['"', "'"]:

                            if not in_string:
                                in_string = True
                                quote = c

                            elif quote == c:
                                in_string = False

                        if not in_string:

                            if c in "([{":
                                depth2 += 1

                            elif c in ")]}":
                                depth2 -= 1

                            elif c == "," and depth2 == 0:
                                raw_args.append(current.strip())
                                current = ""
                                continue

                        current += c

                    if current.strip():
                        raw_args.append(current.strip())

                    for arg in raw_args:

                        if "=" in arg:

                            k, v = arg.split("=", 1)

                            named_args[k.strip()] = self.eval_expr(v.strip())

                        else:

                            positional_args.append(
                                self.eval_expr(arg)
                            )

                func = self.functions[name]

                params = func["params"]
                defaults = func["defaults"]

                old_vars = self.vars.copy()

                pos_index = 0

                for p in params:

                    if p in named_args:

                        self.vars[p] = named_args[p]

                    elif pos_index < len(positional_args):

                        self.vars[p] = positional_args[pos_index]
                        pos_index += 1

                    elif p in defaults:

                        self.vars[p] = self.eval_expr(defaults[p])

                    else:
                        raise er.ExperError(
                            f"Parâmetro obrigatório faltando: {p}",
                            self.current_line,
                            self.current_code
                        )

                value = None

                try:
                    self.run("\n".join(func["block"]))

                except er.ReturnException as r:
                    value = r.value

                self.vars = old_vars

                expr = expr.replace(
                    full_call,
                    repr(value),
                    1
                )

                dbg.debug("FUNCTION REPLACED ->", expr)

                found = True
                break

            if not found:
                break

        expr = utils.fix_string_concat(expr)

        # -------- STRUCT INSTANCE --------
        match = re.fullmatch(
            r"(\w+)\(\)",
            expr
        )

        if match:

            name = match.group(1)

            if name in self.structs:

                obj = {
                    "__struct__": name
                }

                for field in self.structs[name]["fields"]:

                    if field in self.structs[name]["defaults"]:

                        obj[field] = self.eval_expr(
                            self.structs[name]["defaults"][field]
                        )

                    else:

                        obj[field] = None

                return obj

        expr = re.sub(
            r"\b([a-zA-Z_]\w*)\.([a-zA-Z_]\w*)\b",
            utils.replace_property(self),
            expr
        )

        try:
            return eval(expr)
        except Exception as e:
            raise er.ExperError(
                f"Erro na expressão: {original_expr}\nErro: {e}",
                self.current_line,
                self.current_code
            )

    # -------- FUNÇÕES --------
    def call_function(self, line):

        # any(lista)
        match = re.fullmatch(r"any\((.*)\)", line)
        if match:
            val = self.eval_expr(match.group(1))
            return any(val)

        # all(lista)
        match = re.fullmatch(r"all\((.*)\)", line)
        if match:
            val = self.eval_expr(match.group(1))
            return all(val)

        # console.log
        if re.fullmatch(r"console\.log\((.*)\)", line):
            val = self.eval_expr(re.search(r"\((.*)\)", line).group(1))
            print(val)
            return True

        # clear
        if line == "console.clear()":
            os.system("cls" if os.name == "nt" else "clear")
            return True

        # input
        if re.fullmatch(r"console\.input\((.*)\)", line):
            prompt = self.eval_expr(re.search(r"\((.*)\)", line).group(1))
            return input(prompt)

        # sleep
        if re.fullmatch(r"sleep\((.*)\)", line):
            ms = self.eval_expr(re.search(r"\((.*)\)", line).group(1))
            time.sleep(ms / 1000)
            return True

        # conversões
        for f in ["int", "float", "str"]:
            if re.fullmatch(rf"{f}\((.*)\)", line):
                val = self.eval_expr(re.search(r"\((.*)\)", line).group(1))
                return eval(f)(val)

        # -------- LISTA --------
        m = re.fullmatch(r"(\w+)\.append\((.*)\)", line)
        if m:
            self.vars[m.group(1)].append(self.eval_expr(m.group(2)))
            return True

        m = re.fullmatch(r"(\w+)\.pop\((.*)\)", line)
        if m:
            return self.vars[m.group(1)].pop(self.eval_expr(m.group(2)))

        m = re.fullmatch(r"(\w+)\.remove\((.*)\)", line)
        if m:
            self.vars[m.group(1)].remove(self.eval_expr(m.group(2)))
            return True

        m = re.fullmatch(r"(\w+)\.insert\((.*),(.*)\)", line)
        if m:
            self.vars[m.group(1)].insert(
                self.eval_expr(m.group(2)),
                self.eval_expr(m.group(3))
            )
            return True

        return False

    # -------- BLOCO --------
    def get_block(self, lines, i):
        block = []
        i += 1
        braces = 1

        while i < len(lines):
            line = lines[i].strip()
            braces += line.count("{")
            braces -= line.count("}")

            if braces == 0:
                break

            block.append(line)
            i += 1

        return block, i

    # -------- RUN --------
    def run(self, code):
        lines = code.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i].strip()
            self.current_line = i + 1
            self.current_code = line

            dbg.debug(f"Linha {i} -> {repr(line)}")

            if not line or line.startswith("#"):
                i += 1
                continue

            # del variável
            if line.startswith("del "):

                name = line[4:].strip()

                if name in self.vars:
                    del self.vars[name]

                else:
                    raise er.ExperError(
                        f"Variável '{name}' não existe",
                        self.current_line,
                        self.current_code
                    )

                i += 1
                continue

            # delete função
            if line.startswith("delete "):

                name = line[7:].strip()

                if name in self.functions:
                    del self.functions[name]

                else:
                    raise er.ExperError(
                        f"Função '{name}' não existe",
                        self.current_line,
                        self.current_code
                    )

                i += 1
                continue

            # ++
            m = re.match(r"(\w+)\+\+$", line)

            if m:

                name = m.group(1)

                self.vars[name] += 1

                i += 1
                continue

            # --
            m = re.match(r"(\w+)--$", line)

            if m:

                name = m.group(1)

                self.vars[name] -= 1

                i += 1
                continue

            # return
            if line.startswith("return"):

                expr = line[len("return"):].strip()

                value = self.eval_expr(expr) if expr else None

                raise er.ReturnException(value)
            
            # for
            if line.startswith("for"):
                i = self.handle_for(lines, i)
                continue
            
            # while
            if line.startswith("while"):
                i = self.handle_while(lines, i)
                continue

            if line.startswith("fn"):
                i = self.handle_function(lines, i)
                continue
            
            if line.startswith("struct"):
                i = self.handle_struct(lines, i)
                continue
            
            # if
            if (
                line.startswith("if") or
                line.startswith("elif") or
                line.startswith("else")
            ):
                i = self.handle_if(lines, i)
                continue
            
            # break
            if line == "break":
                raise er.BreakException()

            # continue
            if line == "continue":
                raise er.ContinueException()

            # atribuição lista
            if re.match(r"\w+\[.*\]\s*=", line):
                var, val = line.split("=", 1)
                name = var[:var.index("[")]
                idx = self.eval_expr(var[var.index("[")+1:var.index("]")])
                self.vars[name][idx] = self.eval_expr(val)
                i += 1
                continue

            # +=
            m = re.match(r"(\w+)\s*\+=\s*(.+)", line)

            if m:
                name = m.group(1)
                value = self.eval_expr(m.group(2))

                self.vars[name] += value

                i += 1
                continue

            # -=
            m = re.match(r"(\w+)\s*-=\s*(.+)", line)

            if m:
                name = m.group(1)
                value = self.eval_expr(m.group(2))

                self.vars[name] -= value

                i += 1
                continue

            # **=
            m = re.match(r"(\w+)\s*\*\*=\s*(.+)", line)

            if m:
                name = m.group(1)
                value = self.eval_expr(m.group(2))

                self.vars[name] **= value

                i += 1
                continue

            # *=
            m = re.match(r"(\w+)\s*\*=\s*(.+)", line)

            if m:
                name = m.group(1)
                value = self.eval_expr(m.group(2))

                self.vars[name] *= value

                i += 1
                continue

            # //=
            m = re.match(r"(\w+)\s*//=\s*(.+)", line)

            if m:
                name = m.group(1)
                value = self.eval_expr(m.group(2))

                self.vars[name] //= value

                i += 1
                continue

            # /=
            m = re.match(r"(\w+)\s*/=\s*(.+)", line)

            if m:
                name = m.group(1)
                value = self.eval_expr(m.group(2))

                self.vars[name] /= value

                i += 1
                continue

            # %=
            m = re.match(r"(\w+)\s*%=\s*(.+)", line)

            if m:
                name = m.group(1)
                value = self.eval_expr(m.group(2))

                self.vars[name] %= value

                i += 1
                continue

            # &=
            m = re.match(r"(\w+)\s*&=\s*(.+)", line)

            if m:
                name = m.group(1)
                value = self.eval_expr(m.group(2))

                self.vars[name] &= value

                i += 1
                continue

            # |=
            m = re.match(r"(\w+)\s*\|=\s*(.+)", line)

            if m:
                name = m.group(1)
                value = self.eval_expr(m.group(2))

                self.vars[name] |= value

                i += 1
                continue

            # ^=
            m = re.match(r"(\w+)\s*\^=\s*(.+)", line)

            if m:
                name = m.group(1)
                value = self.eval_expr(m.group(2))

                self.vars[name] ^= value

                i += 1
                continue

            # <<=
            m = re.match(r"(\w+)\s*<<=\s*(.+)", line)

            if m:
                name = m.group(1)
                value = self.eval_expr(m.group(2))

                self.vars[name] <<= value

                i += 1
                continue

            # >>=
            m = re.match(r"(\w+)\s*>>=\s*(.+)", line)

            if m:
                name = m.group(1)
                value = self.eval_expr(m.group(2))

                self.vars[name] >>= value

                i += 1
                continue

            # variável normal
            assign_index = -1

            depth = 0
            in_string = False
            quote = ""

            for idx, c in enumerate(line):

                # strings
                if c in ['"', "'"]:

                    if not in_string:
                        in_string = True
                        quote = c

                    elif quote == c:
                        in_string = False

                if in_string:
                    continue

                # profundidade
                if c in "([{":
                    depth += 1

                elif c in ")]}":
                    depth -= 1

                # "=" principal
                elif (
                    c == "=" and
                    depth == 0 and
                    not (
                        idx > 0 and line[idx-1] in "!<>="
                    )
                ):
                    assign_index = idx
                    break
            
            # -------- OBJ.FIELD = --------
            match = re.match(
                r"(\w+)\.(\w+)\s*=\s*(.+)",
                line
            )

            if match:

                obj = match.group(1)
                field = match.group(2)
                value = match.group(3)

                if obj not in self.vars:
                    raise Exception(
                        f"Objeto '{obj}' não existe"
                    )

                self.vars[obj][field] = self.eval_expr(value)

                i += 1
                continue

            if assign_index != -1:

                var = line[:assign_index]
                val = line[assign_index+1:]

                val = val.strip()

                # ===== MULTILINHA =====
                if (
                    val == "{" or
                    val == "[" or
                    val == "("
                ):

                    open_char = val
                    close_char = {
                        "{": "}",
                        "[": "]",
                        "(": ")"
                    }[open_char]

                    full_value = val + "\n"

                    count = 1
                    i += 1

                    while i < len(lines):

                        current = lines[i]

                        count += current.count(open_char)
                        count -= current.count(close_char)

                        full_value += current + "\n"

                        if count == 0:
                            break

                        i += 1

                    val = full_value.strip()

                self.vars[var.strip()] = self.eval_expr(val)

                i += 1
                continue

            if self.call_function(line):
                i += 1
                continue

            # chamada de função solta
            if re.fullmatch(r"\w+\(.*\)", line):

                self.eval_expr(line)

                i += 1
                continue

            raise er.ExperError(
                f"Erro de sintaxe: {line}",
                self.current_line,
                self.current_code
            )
        