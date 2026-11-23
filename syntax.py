import ply.lex
import ply.yacc

import lexer
from syntax_common import debug_parsetree, treeprint

tokens = lexer.tokens


def p_program(p):
    "program : opt_definitions_list statement_list"
    debug_parsetree(p)


def p_definitions(p):
    """definitions : function_definition
    | procedure_definition
    | variable_definition"""
    debug_parsetree(p)


def p_variable_definition(p):
    "variable_definition : type IDENT EQ rvalue"
    debug_parsetree(p)


def p_type(p):
    """type : IDENT
    | SHAPE
    | NUMBER"""
    debug_parsetree(p)


def p_rvalue(p):
    """rvalue : expression
    | opt_plus coordinate_list"""
    debug_parsetree(p)


def p_coordinate_list(p):
    """coordinate_list : coordinate_list MINUS coordinate
    | coordinate"""
    debug_parsetree(p)


def p_coordinate(p):
    "coordinate : LSQUARE expression COMMA expression RSQUARE"
    debug_parsetree(p)


def p_function_definition(p):
    "function_definition : DEFINE FUNC_IDENT LCURLY opt_formals RCURLY RETURN type opt_variable_definitions IS rvalue END"
    debug_parsetree(p)


def p_procedure_definition(p):
    "procedure_definition : DEFINE PROC_IDENT LSQUARE opt_formals RSQUARE opt_variable_definitions IS statement_list opt_return_stmt END"
    debug_parsetree(p)


def p_formals(p):
    """formals : formals SEMICOLON formal_arg
    | formal_arg"""
    debug_parsetree(p)


def p_formal_arg(p):
    "formal_arg : IDENT COLON type"
    debug_parsetree(p)


def p_arguments(p):
    """arguments : arguments COMMA expression
    | expression"""
    debug_parsetree(p)


def p_assignment(p):
    """assignment : lvalue ASSIGN rvalue
    | lvalue ASSIGN procedure_call"""
    debug_parsetree(p)


def p_lvalue(p):
    "lvalue : IDENT"
    debug_parsetree(p)


def p_procedure_call(p):
    "procedure_call : PROC_IDENT LPAREN opt_arguments RPAREN"
    debug_parsetree(p)


def p_print_statement(p):
    "print_statement : PRINT print_item_list"
    debug_parsetree(p)


def p_print_item_list(p):
    """print_item_list : print_item_list AMPERSAND print_item
    | print_item"""
    debug_parsetree(p)


def p_print_item(p):
    """print_item : STRING
    | expression"""
    debug_parsetree(p)


def p_statement(p):
    """statement : procedure_call
    | assignment
    | print_statement
    | IF expression THEN statement_list ENDIF
    | IF expression THEN statement_list ELSE statement_list ENDIF
    | WHILE expression IS statement_list ENDWHILE
    | CLEAR
    | PAUSE
    | WAIT expression
    | DRAW expression opt_rgb"""
    debug_parsetree(p)


def p_rgb(p):
    "rgb : LPAREN expression COMMA expression COMMA expression RPAREN"
    debug_parsetree(p)


def p_expression(p):
    """expression : simple_expr
    | expression EQ simple_expr
    | expression NOTEQ simple_expr
    | expression LT simple_expr"""
    debug_parsetree(p)


def p_simple_expr(p):
    """simple_expr : term
    | simple_expr PLUS term
    | simple_expr MINUS term
    | simple_expr ARROW coordinate"""
    debug_parsetree(p)


def p_term(p):
    """term : factor
    | term MULT factor
    | term DIV factor"""
    debug_parsetree(p)


def p_factor(p):
    """factor : atom
    | PLUS atom
    | MINUS atom"""
    debug_parsetree(p)


def p_atom(p):
    """atom : INT_LITERAL
    | IDENT
    | IDENT DOT IDENT
    | function_call
    | LPAREN expression RPAREN"""
    debug_parsetree(p)


def p_function_call(p):
    "function_call : FUNC_IDENT LPAREN opt_arguments RPAREN"
    debug_parsetree(p)


# --- Helper Rules (These can be at the bottom) ---


def p_opt_definitions_list(p):
    """opt_definitions_list : opt_definitions_list definitions
    | empty"""
    debug_parsetree(p)


def p_statement_list(p):
    """statement_list : statement_list statement
    | statement"""
    debug_parsetree(p)


def p_opt_variable_definitions(p):
    """opt_variable_definitions : opt_variable_definitions variable_definition
    | empty"""
    debug_parsetree(p)


def p_opt_formals(p):
    """opt_formals : formals
    | empty"""
    debug_parsetree(p)


def p_opt_arguments(p):
    """opt_arguments : arguments
    | empty"""
    debug_parsetree(p)


def p_opt_plus(p):
    """opt_plus : PLUS
    | empty"""
    debug_parsetree(p)


def p_opt_return_stmt(p):
    """opt_return_stmt : RETURN expression
    | empty"""
    debug_parsetree(p)


def p_opt_rgb(p):
    """opt_rgb : rgb
    | empty"""
    debug_parsetree(p)


def p_empty(p):
    "empty :"
    pass
    debug_parsetree(p)


def p_error(p):
    print("Error found! Syntax error @", p)
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
        print("Program ok.")
