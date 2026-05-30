import re
from .debug import *
from . import errors as er

# -------- EXPRESSÕES --------
def eval_expr(self, expr):
    expr = expr.strip()
    original_expr = expr
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

    debug("Depois do safe replace:", expr)

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
        
    def replace_property(match):
        
        obj = match.group(1)
        field = match.group(2)

        if obj in self.vars:

            value = self.vars[obj]

            if isinstance(value, dict):

                if field in value:

                    v = value[field]

                    if isinstance(v, str):
                        return repr(v)

                    return str(v)

        return match.group(0)

    expr = re.sub(
        r"\b([a-zA-Z_]\w*)\.([a-zA-Z_]\w*)\b",
        replace_property,
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