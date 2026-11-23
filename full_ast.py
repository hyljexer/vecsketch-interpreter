import ply.lex
import ply.yacc

import lexer
from syntax_common import debug_parsetree, treeprint

tokens = lexer.tokens


class ASTnode:
    def __init__(self, typestr):
        self.nodetype = typestr
        # Attributes like value, lineno, child_XX, children_XX
        # will be added dynamically in p_ functions.


# ======================================
# AST Implementation
# ======================================


def p_program(p):
    "program : opt_definitions_list statement_list"
    node = ASTnode("program")
    node.children_definitions = p[1]
    # We take the list of statements from the statement_list node
    node.children_statements = p[2].children_statements
    p[0] = node


def p_statement_list(p):
    """statement_list : statement_list statement
    | statement"""
    if len(p) == 3:
        p[0] = p[1]
        p[0].children_statements.append(p[2])
    else:
        node = ASTnode("statement_list")
        node.children_statements = [p[1]]
        p[0] = node


def p_statement(p):
    """statement : procedure_call
    | assignment
    | print_statement
    | CLEAR
    | PAUSE"""
    if isinstance(p[1], ASTnode):
        p[0] = p[1]
    else:
        node = ASTnode("statement")
        node.value = p[1].lower()  # "clear" or "pause"
        node.lineno = p.lineno(1)
        p[0] = node


def p_statement_if(p):
    """statement : IF expression THEN statement_list ENDIF
    | IF expression THEN statement_list ELSE statement_list ENDIF"""
    node = ASTnode("if")
    node.child_condition = p[2]
    node.child_then = p[4]
    if len(p) == 8:
        node.child_else = p[6]
    node.lineno = p.lineno(1)
    p[0] = node


def p_statement_while(p):
    "statement : WHILE expression IS statement_list ENDWHILE"
    node = ASTnode("while")
    node.child_condition = p[2]
    node.children_body = p[4].children_statements
    node.lineno = p.lineno(1)
    p[0] = node


def p_statement_wait(p):
    "statement : WAIT expression"
    node = ASTnode("wait")
    node.child_expression = p[2]
    node.lineno = p.lineno(1)
    p[0] = node


def p_statement_draw(p):
    "statement : DRAW expression opt_rgb"
    node = ASTnode("draw")
    node.child_shape = p[2]
    node.child_color = p[3]
    node.lineno = p.lineno(1)
    p[0] = node


def p_procedure_call(p):
    "procedure_call : PROC_IDENT LPAREN opt_arguments RPAREN"
    node = ASTnode("procedure_call")
    node.value = p[1]
    node.children_arguments = p[3]
    node.lineno = p.lineno(1)
    p[0] = node


def p_assignment(p):
    """assignment : lvalue ASSIGN rvalue
    | lvalue ASSIGN procedure_call"""
    node = ASTnode("assignment")
    node.child_target = p[1]
    node.child_source = p[3]
    node.lineno = p.lineno(2)
    p[0] = node


def p_print_statement(p):
    "print_statement : PRINT print_item_list"
    node = ASTnode("print")
    node.children_items = p[2]
    node.lineno = p.lineno(1)
    p[0] = node


def p_definitions(p):
    """definitions : function_definition
    | procedure_definition
    | variable_definition"""
    p[0] = p[1]


def p_variable_definition(p):
    "variable_definition : type IDENT EQ rvalue"
    node = ASTnode("variable_definition")
    node.child_type = p[1]
    node.value = p[2]
    node.child_expression = p[4]
    node.lineno = p.lineno(2)
    p[0] = node


def p_type(p):
    """type : IDENT
    | SHAPE
    | NUMBER"""
    node = ASTnode("type")
    node.value = p[1]
    p[0] = node


def p_rvalue(p):
    """rvalue : expression
    | opt_plus coordinate_list"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        node = ASTnode("shape_literal")
        node.value = "+" if p[1] else ""
        node.children_coordinates = p[2]
        p[0] = node


def p_coordinate_list(p):
    """coordinate_list : coordinate_list MINUS coordinate
    | coordinate"""
    if len(p) == 4:
        p[0] = p[1]
        p[0].append(p[3])
    else:
        p[0] = [p[1]]


def p_coordinate(p):
    "coordinate : LSQUARE expression COMMA expression RSQUARE"
    node = ASTnode("coordinate")
    node.child_x = p[2]
    node.child_y = p[4]
    p[0] = node


def p_function_definition(p):
    "function_definition : DEFINE FUNC_IDENT LCURLY opt_formals RCURLY RETURN type opt_variable_definitions IS rvalue END"
    node = ASTnode("function_definition")
    node.value = p[2]
    node.children_formals = p[4]
    node.child_return_type = p[7]
    node.children_local_vars = p[8]
    node.child_body = p[10]
    node.lineno = p.lineno(1)
    p[0] = node


def p_procedure_definition(p):
    "procedure_definition : DEFINE PROC_IDENT LSQUARE opt_formals RSQUARE opt_variable_definitions IS statement_list opt_return_stmt END"
    node = ASTnode("procedure_definition")
    node.value = p[2]
    node.children_formals = p[4]
    node.children_local_vars = p[6]
    node.children_statements = p[8].children_statements
    node.child_return_val = p[9]
    node.lineno = p.lineno(1)
    p[0] = node


def p_formals(p):
    """formals : formals SEMICOLON formal_arg
    | formal_arg"""
    if len(p) == 4:
        p[0] = p[1]
        p[0].append(p[3])
    else:
        p[0] = [p[1]]


def p_formal_arg(p):
    "formal_arg : IDENT COLON type"
    node = ASTnode("formal_arg")
    node.value = p[1]
    node.child_type = p[3]
    p[0] = node


def p_arguments(p):
    """arguments : arguments COMMA expression
    | expression"""
    if len(p) == 4:
        p[0] = p[1]
        p[0].append(p[3])
    else:
        p[0] = [p[1]]


def p_lvalue(p):
    "lvalue : IDENT"
    node = ASTnode("identifier")
    node.value = p[1]
    node.lineno = p.lineno(1)
    p[0] = node


def p_print_item_list(p):
    """print_item_list : print_item_list AMPERSAND print_item
    | print_item"""
    if len(p) == 4:
        p[0] = p[1]
        p[0].append(p[3])
    else:
        p[0] = [p[1]]


def p_print_item(p):
    """print_item : STRING
    | expression"""
    if isinstance(p[1], str):
        node = ASTnode("string_literal")
        node.value = p[1]
        p[0] = node
    else:
        p[0] = p[1]


def p_rgb(p):
    "rgb : LPAREN expression COMMA expression COMMA expression RPAREN"
    node = ASTnode("rgb")
    node.child_r = p[2]
    node.child_g = p[4]
    node.child_b = p[6]
    p[0] = node


def p_expression(p):
    """expression : simple_expr
    | expression EQ simple_expr
    | expression NOTEQ simple_expr
    | expression LT simple_expr"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        node = ASTnode("expression")
        node.value = p[2]
        node.child_left = p[1]
        node.child_right = p[3]
        p[0] = node


def p_simple_expr(p):
    """simple_expr : term
    | simple_expr PLUS term
    | simple_expr MINUS term
    | simple_expr ARROW coordinate"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        node = ASTnode("expression")
        node.value = p[2]
        node.child_left = p[1]
        node.child_right = p[3]
        p[0] = node


def p_term(p):
    """term : factor
    | term MULT factor
    | term DIV factor"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        node = ASTnode("expression")
        node.value = p[2]
        node.child_left = p[1]
        node.child_right = p[3]
        p[0] = node


def p_factor(p):
    """factor : atom
    | PLUS atom
    | MINUS atom"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        node = ASTnode("unary_expression")
        node.value = p[1]
        node.child_atom = p[2]
        p[0] = node


def p_atom(p):
    """atom : INT_LITERAL
    | IDENT
    | IDENT DOT IDENT
    | function_call
    | LPAREN expression RPAREN"""
    if len(p) == 2:
        if isinstance(p[1], int):
            node = ASTnode("int_literal")
            node.value = p[1]
            p[0] = node
        elif isinstance(p[1], ASTnode):  # function_call
            p[0] = p[1]
        else:  # IDENT
            node = ASTnode("identifier")
            node.value = p[1]
            node.lineno = p.lineno(1)
            p[0] = node
    elif len(p) == 4:
        if p[1] == "(":  # ( expression )
            p[0] = p[2]
        else:  # IDENT DOT IDENT
            node = ASTnode("property_access")
            node.value = f"{p[1]}.{p[3]}"
            node.lineno = p.lineno(1)
            p[0] = node


def p_function_call(p):
    "function_call : FUNC_IDENT LPAREN opt_arguments RPAREN"
    node = ASTnode("function_call")
    node.value = p[1]
    node.children_arguments = p[3]
    node.lineno = p.lineno(1)
    p[0] = node


# ======================================
# Optional Helper Rules
# ======================================


def p_opt_definitions_list(p):
    """opt_definitions_list : opt_definitions_list definitions
    | empty"""
    if len(p) == 3:
        p[0] = p[1]
        p[0].append(p[2])
    else:
        p[0] = []


def p_opt_variable_definitions(p):
    """opt_variable_definitions : opt_variable_definitions variable_definition
    | empty"""
    if len(p) == 3:
        p[0] = p[1]
        p[0].append(p[2])
    else:
        p[0] = []


def p_opt_formals(p):
    """opt_formals : formals
    | empty"""
    p[0] = p[1] if p[1] is not None else []


def p_opt_arguments(p):
    """opt_arguments : arguments
    | empty"""
    p[0] = p[1] if p[1] is not None else []


def p_opt_plus(p):
    """opt_plus : PLUS
    | empty"""
    p[0] = p[1]  # Returns '+' or None


def p_opt_return_stmt(p):
    """opt_return_stmt : RETURN expression
    | empty"""
    p[0] = p[2] if len(p) == 3 else None


def p_opt_rgb(p):
    """opt_rgb : rgb
    | empty"""
    p[0] = p[1]


def p_empty(p):
    "empty :"
    p[0] = None


def p_error(p):
    if p:
        print(f"Error found! {p.lineno}: Syntax Error (token:'{p.value}')")
    else:
        print("Syntax Error at EOF")
    raise SystemExit


parser = ply.yacc.yacc()
if __name__ == "__main__":
    import argparse

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "-t", "--treetype", help="type of output tree (unicode/ascii/dot)"
    )
    arg_parser.add_argument("inputfilename", help="filename to process")
    ns = arg_parser.parse_args()

    outformat = "unicode"
    if ns.treetype:
        outformat = ns.treetype

    if ns.inputfilename is None:
        # user didn't provide input filename
        arg_parser.print_help()
    else:
        data = open(ns.inputfilename).read()
        result = parser.parse(data, lexer=lexer.lexer, debug=False)
        # Pretty print the resulting tree
        treeprint(result, outformat)
        # print("Program ok.")
