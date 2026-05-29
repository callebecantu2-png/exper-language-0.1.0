import sys
import re
import os
import time

# ================= DEBUG =================
DEBUG = False

def debug(*args):
    if DEBUG:
        print("[DEBUG]:", *args)

# WHILE e FOR usam exceções para controlar break/continue

class BreakException(Exception):
    pass

class ContinueException(Exception):
    pass

# para retornar de funções 

class ReturnException(Exception):
    def __init__(self, value):
        self.value = value


# ================= LINGUAGEM =================
class Exper:
    def __init__(self):
        self.vars = {}
        self.functions = {}

    # -------- EXPRESSÕES --------
    def eval_expr(self, expr):
        expr = expr.strip()
        debug("Evaluating:", expr)

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

        # -------- SAFE REPLACE --------
        def safe_replace(expr):
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

            debug("MULTI IN ->", result)

            return result

        # -------- IN NORMAL --------
        match = re.fullmatch(r"(.+?)\s+in\s+(.+)", expr)

        if match:
            left = self.eval_expr(match.group(1))
            right = self.eval_expr(match.group(2))

            result = left in right

            debug("IN ->", result)

            return result

        expr = safe_replace(expr)

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
            debug("INPUT ->", result)
            return result
        
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

                    raw_args = [a.strip() for a in self.split_args(args_raw)]

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
                        raise Exception(
                            f"Parâmetro obrigatório faltando: {p}"
                        )

                try:
                    self.run("\n".join(block))

                except ReturnException as r:

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
                        raise Exception(
                            f"Parâmetro obrigatório faltando: {p}"
                        )

                value = None

                try:
                    self.run("\n".join(func["block"]))

                except ReturnException as r:
                    value = r.value

                self.vars = old_vars

                expr = expr.replace(
                    full_call,
                    repr(value),
                    1
                )

                debug("FUNCTION REPLACED ->", expr)

                found = True
                break

            if not found:
                break

        # -------- STRING CONCAT FIX --------
        def fix_string_concat(expr):
            parts = []
            current = ""
            in_str = False
            quote = ""

            i = 0
            while i < len(expr):
                c = expr[i]

                if c in ['"', "'"]:
                    if not in_str:
                        in_str = True
                        quote = c
                        current += c
                    elif quote == c:
                        in_str = False
                        current += c
                    else:
                        current += c
                    i += 1
                    continue

                if not in_str and expr[i:i+1] == "+":
                    parts.append(current.strip())
                    current = ""
                    i += 1
                    continue

                current += c
                i += 1

            if current:
                parts.append(current.strip())

            return "+".join(parts)

        expr = fix_string_concat(expr)

        try:
            return eval(expr)
        except Exception:
            raise Exception(f"Erro na expressão: {expr}")
        
    def split_args(self, text):
        args = []
        current = ""

        depth = 0

        in_string = False
        quote = ""

        for ch in text:

            if ch in ['"', "'"]:

                if not in_string:
                    in_string = True
                    quote = ch

                elif quote == ch:
                    in_string = False

                current += ch
                continue

            if not in_string:

                if ch in "([{":
                    depth += 1

                elif ch in ")]}":
                    depth -= 1

                elif ch == "," and depth == 0:
                    args.append(current.strip())
                    current = ""
                    continue

            current += ch

        if current.strip():
            args.append(current.strip())

        return args

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
    
    # -------- FUNCTION --------
    def handle_function(self, lines, i):

        line = lines[i].strip()

        match = re.match(r"fn\s+(\w+)\((.*?)\)\s*{", line)

        if not match:
            raise Exception("Erro de sintaxe na função")

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

    # -------- CONTROLE --------
    def handle_if(self, lines, i):

        executed = False

        while i < len(lines):

            line = lines[i].strip()

            # ================= IF / ELIF =================
            if line.startswith("if") or line.startswith("elif"):

                match = re.match(r"(if|elif)\s*\((.*)\)\s*{", line)

                if not match:
                    raise Exception("Erro de sintaxe no if")

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

    def handle_while(self, lines, i):

        line = lines[i].strip()

        match = re.match(r"while\s*\((.*?)\)\s*{", line)

        if not match:
            raise Exception("Erro de sintaxe no while")

        condition = match.group(1).strip()

        block, i2 = self.get_block(lines, i)

        while self.eval_expr(condition):

            try:
                self.run("\n".join(block))

            except ContinueException:
                continue

            except BreakException:
                break

        return i2 + 1

    def handle_for(self, lines, i):
        line = lines[i].strip()

        # ===== FOR CLÁSSICO =====
        m = re.match(r"for\s*\((.*)\)\s*{", line)
        if m:
            parts = m.group(1).split(";")

            if len(parts) != 3:
                raise Exception("Erro de sintaxe no for")

            init, cond, inc = parts

            self.run(init.strip())
            block, i2 = self.get_block(lines, i)

            while self.eval_expr(cond.strip()):

                try:
                    self.run("\n".join(block))

                except ContinueException:
                    self.run(inc.strip())
                    continue

                except BreakException:
                    break

                self.run(inc.strip())

            return i2 + 1

        # ===== FOR IN =====
        m = re.match(r"for\s+(.+)\s+in\s+(.+)\s*{", line)
        if m:
            var_part = m.group(1).strip()
            iterable = self.eval_expr(m.group(2).strip())
            block, i2 = self.get_block(lines, i)

            # 🔥 LISTA / TUPLA
            if isinstance(iterable, (list, tuple)):

                for item in iterable:
                    self.vars[var_part] = item

                    try:
                        self.run("\n".join(block))

                    except ContinueException:
                        continue

                    except BreakException:
                        break

            # 🔥 DICIONÁRIO
            elif isinstance(iterable, dict):

                # caso k:v
                if ":" in var_part:
                    parts = var_part.split(":")
                    if len(parts) != 2:
                        raise Exception("Erro no for k:v")

                    k = parts[0].strip()
                    v = parts[1].strip()

                    for key, val in iterable.items():

                        self.vars[k] = key
                        self.vars[v] = val

                        try:
                            self.run("\n".join(block))

                        except ContinueException:
                            continue

                        except BreakException:
                            break

                # caso só chave
                else:
                    for key in iterable:
                        self.vars[var_part] = key
                        self.run("\n".join(block))

            else:
                raise Exception("Tipo não iterável")

            return i2 + 1

        # ===== ERRO =====
        raise Exception("Erro de sintaxe no for")

    # -------- RUN --------
    def run(self, code):
        lines = code.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            if not line or line.startswith("//"):
                i += 1
                continue

            # del variável
            if line.startswith("del "):

                name = line[4:].strip()

                if name in self.vars:
                    del self.vars[name]

                else:
                    raise Exception(f"Variável '{name}' não existe")

                i += 1
                continue

            # delete função
            if line.startswith("delete "):

                name = line[7:].strip()

                if name in self.functions:
                    del self.functions[name]

                else:
                    raise Exception(f"Função '{name}' não existe")

                i += 1
                continue

            # return
            if line.startswith("return"):

                expr = line[len("return"):].strip()

                value = self.eval_expr(expr) if expr else None

                raise ReturnException(value)
            
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

            if (
                line.startswith("if") or
                line.startswith("elif") or
                line.startswith("else")
            ):
                i = self.handle_if(lines, i)
                continue
            
            # break
            if line == "break":
                raise BreakException()

            # continue
            if line == "continue":
                raise ContinueException()

            # atribuição lista
            if re.match(r"\w+\[.*\]\s*=", line):
                var, val = line.split("=", 1)
                name = var[:var.index("[")]
                idx = self.eval_expr(var[var.index("[")+1:var.index("]")])
                self.vars[name][idx] = self.eval_expr(val)
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

            raise Exception(f"Erro de sintaxe: {line}")


# ================= MAIN =================
def main():
    if len(sys.argv) < 2:
        print("Uso: python exper.py arquivo.exper")
        return

    file_path = sys.argv[1]

    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()

    lang = Exper()
    lang.run(code)


if __name__ == "__main__":
    main()