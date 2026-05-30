def replace_property(self):
    def fn(match):
                
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
    
    return fn