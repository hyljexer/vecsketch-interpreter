import sys

import ply.lex

tokens = (
    "COMMENT",
    "NUMBER",
    "SHAPE",
    "DEFINE",
    "IS",
    "END",
    "RETURN",
    "DRAW",
    "CLEAR",
    "PAUSE",
    "WAIT",
    "WHILE",
    "ENDWHILE",
    "IF",
    "THEN",
    "ELSE",
    "ENDIF",
    "PRINT",
    "LPAREN",
    "RPAREN",
    "LSQUARE",
    "RSQUARE",
    "LCURLY",
    "RCURLY",
    "ASSIGN",
    "ARROW",
    "AMPERSAND",
    "COMMA",
    "COLON",
    "SEMICOLON",
    "DOT",
    "EQ",
    "NOTEQ",
    "LT",
    "PLUS",
    "MINUS",
    "MULT",
    "DIV",
    "STRING",
    "INT_LITERAL",
    "IDENT",
    "PROC_IDENT",
    "FUNC_IDENT",
)

t_NUMBER = r"number"
t_SHAPE = r"shape"
t_DEFINE = r"define"
t_IS = r"is"
t_END = r"end"
t_RETURN = r"return"

t_DRAW = r"draw"
t_CLEAR = r"clear"
t_PAUSE = r"pause"
t_WAIT = r"wait"

t_WHILE = r"while"
t_ENDWHILE = r"endwhile"
t_IF = r"if"
t_THEN = r"then"
t_ELSE = r"else"
t_ENDIF = r"endif"

t_PRINT = r"print"

t_LPAREN = r"\("
t_RPAREN = r"\)"
t_LSQUARE = r"\["
t_RSQUARE = r"\]"
t_LCURLY = r"\{"
t_RCURLY = r"\}"

t_ASSIGN = r":="
t_ARROW = r"->"
t_AMPERSAND = r"&"
t_COMMA = r","
t_COLON = r":"
t_SEMICOLON = r";"
t_DOT = r"\."
t_EQ = r"="
t_NOTEQ = r"/="
t_LT = r"<"
t_PLUS = r"\+"
t_MINUS = r"-"
t_MULT = r"\*"
t_DIV = r"/"


def t_newline(t):
    r"\n+"
    t.lexer.lineno += t.value.count("\n")


t_ignore = " \r\t"


def t_error(t):
    raise Exception(
        "Error found! Illegal character '{}' at line {}".format(
            t.value[0], t.lexer.lineno
        )
    )


def t_COMMENT(t):
    r"/%([\s\S]*?)%/"


def t_STRING(t):
    r'"[^"]*"'
    t.value = t.value.strip('"')
    return t


def t_INT_LITERAL(t):
    r"-?[0-9]+"
    t.value = int(t.value)
    if (t.value < -1e9) | (t.value > 1e9):
        raise Exception("Error found! Integer value too large", t.value)
    return t


def t_IDENT(t):
    r"[a-z][a-zA-Z0-9_]*"
    keywords = [
        "number",
        "shape",
        "define",
        "is",
        "end",
        "return",
        "draw",
        "clear",
        "pause",
        "wait",
        "while",
        "endwhile",
        "if",
        "then",
        "else",
        "endif",
        "print",
    ]
    if t.value in keywords:
        t.type = keywords[keywords.index(t.value)].upper()
    if len(t.value) > 64:
        raise Exception("Error found! Identifier is too long", t.value)
    return t


def t_PROC_IDENT(t):
    r"[A-Z][a-z0-9_]+"
    return t


def t_FUNC_IDENT(t):
    r"[A-Z]{2}[A-Z0-9_]*"
    return t


lexer = ply.lex.lex()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <filename>", file=sys.stderr)
        raise SystemExit
    else:
        with open(sys.argv[1], "r") as INFILE:
            # blindly read all to memory (what if that is a 42Gb file?)
            data = INFILE.read()

        lexer.input(data)

        while True:
            token = lexer.token()
            if token is None:
                break
            print(token)
        print("Program ok.")
