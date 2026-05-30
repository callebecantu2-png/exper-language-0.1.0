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