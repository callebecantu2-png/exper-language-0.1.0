def split_args(text):
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