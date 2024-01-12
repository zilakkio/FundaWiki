import string


replacements = {
    ".": "`.",
    "/": "`/"
}


def tokenize(text):
    text = text.replace("<br>", '`')
    tokens = []
    in_brackets = False
    curr_token = []
    pre_tokens = []

    # Split text while preserving punctuation and spaces
    token = ""
    for char in text:
        if char in string.whitespace:
            if token:
                pre_tokens.append(token)
                token = ""
            pre_tokens.append(char)
        elif char in string.punctuation and char != "-":
            if token:
                pre_tokens.append(token)
                token = ""
            pre_tokens.append(char)
        else:
            token += char
    if token:
        pre_tokens.append(token)

    # Process tokens with respect to brackets
    for pre_token in pre_tokens:
        if in_brackets:
            curr_token.append(pre_token)
            if "]" in pre_token:
                in_brackets = False
                tokens.append("".join(curr_token))
                curr_token = []
        else:
            if "[" in pre_token:
                in_brackets = True
                curr_token.append(pre_token)
            else:
                tokens.append(pre_token)

    new_tokens = []
    for t in tokens:
        if t == '`':
            new_tokens.append("<br>")
        else:
            new_tokens.append(t)
    return new_tokens
