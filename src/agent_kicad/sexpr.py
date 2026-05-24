from __future__ import annotations

Token = str
SExpr = str | list["SExpr"]


def parse_sexpr(text: str) -> list[SExpr]:
    tokens = list(_tokens(text))
    stack: list[list[SExpr]] = [[]]
    for token in tokens:
        if token == "(":
            item: list[SExpr] = []
            stack[-1].append(item)
            stack.append(item)
        elif token == ")":
            if len(stack) == 1:
                raise ValueError("unexpected closing parenthesis")
            stack.pop()
        else:
            stack[-1].append(token)
    if len(stack) != 1:
        raise ValueError("unclosed parenthesis")
    return stack[0]


def _tokens(text: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        if ch == ";":
            while i < len(text) and text[i] != "\n":
                i += 1
            continue
        if ch in "()":
            tokens.append(ch)
            i += 1
            continue
        if ch == '"':
            value, i = _quoted(text, i + 1)
            tokens.append(value)
            continue
        start = i
        while i < len(text) and not text[i].isspace() and text[i] not in "();":
            i += 1
        tokens.append(text[start:i])
    return tokens


def _quoted(text: str, i: int) -> tuple[str, int]:
    chars: list[str] = []
    while i < len(text):
        ch = text[i]
        if ch == "\\":
            if i + 1 >= len(text):
                raise ValueError("dangling escape in quoted string")
            chars.append(text[i + 1])
            i += 2
            continue
        if ch == '"':
            return "".join(chars), i + 1
        chars.append(ch)
        i += 1
    raise ValueError("unterminated quoted string")


def head(expr: SExpr) -> str | None:
    if isinstance(expr, list) and expr and isinstance(expr[0], str):
        return expr[0]
    return None


def children(expr: SExpr, name: str) -> list[list[SExpr]]:
    if not isinstance(expr, list):
        return []
    return [item for item in expr if isinstance(item, list) and head(item) == name]


def first_child(expr: SExpr, name: str) -> list[SExpr] | None:
    found = children(expr, name)
    return found[0] if found else None
