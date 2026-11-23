import full_ast
import lexer
import simple_semantics_check
from semantics_common import SemData, SymbolData, visit_tree
from syntax_common import get_childvars, treeprint

# PASS 1 - Collect function and procedure signatures


def collect_signatures(node, semdata):
    """Gathers Function and Procedure names so they can be called before definition."""
    nodetype = node.nodetype
    if nodetype in ["function_definition", "procedure_definition"]:
        name = node.value
        if name in semdata.symtbl:
            return f"Redefined name '{name}'"

        # Store as function/procedure in symbol table
        semdata.symtbl[name] = SymbolData(nodetype, node)
    return None


# PASS 2 - Check for recursion


def check_for_recursion_cycles(node, semdata):
    if node.nodetype != "program":
        return None

    call_graph = {}
    for name, symbol in semdata.symtbl.items():
        if symbol.symtype == "function_definition":
            called_functions = set()

            def find_calls(n):
                if n.nodetype == "function_call":
                    called_functions.add(n.value)
                for _, child in get_childvars(n):
                    if isinstance(child, list):
                        for c in child:
                            if c:
                                find_calls(c)
                    elif child:
                        find_calls(child)

            find_calls(symbol.defnode.child_body)
            call_graph[name] = called_functions

    visited = set()
    on_stack = []

    def detect_cycle(u):
        visited.add(u)
        on_stack.append(u)
        for v in call_graph.get(u, []):
            if v in call_graph:
                if v in on_stack:
                    path = on_stack[on_stack.index(v) :] + [v]
                    return " -> ".join(path)
                if v not in visited:
                    res = detect_cycle(v)
                    if res:
                        return res
        on_stack.pop()
        return None

    for func_name in call_graph:
        if func_name not in visited:
            cycle_path = detect_cycle(func_name)
            if cycle_path:
                return f"Recursion detected in function definitions: {cycle_path}"

    return None


# PASS 3 - Variables, scopes and call details


def handle_definitions(node, semdata):
    nodetype = node.nodetype

    # Track current context
    if nodetype in ["function_definition", "procedure_definition"]:
        semdata.current_context = node
        semdata.block_locals = []

    # Add Variables
    if nodetype == "variable_definition":
        var_name = node.value
        if var_name in semdata.symtbl:
            return f"Redefined variable '{var_name}'"

        symtype = "local_variable" if semdata.current_context else "global_variable"
        symdata = SymbolData(symtype, node)
        semdata.symtbl[var_name] = symdata
        if semdata.current_context:
            semdata.block_locals.append(var_name)

    # Add Parameters
    if nodetype == "formal_arg":
        param_name = node.value
        if param_name in semdata.symtbl:
            return f"Parameter '{param_name}' conflicts with existing definition"

        symdata = SymbolData("parameter", node)
        semdata.symtbl[param_name] = symdata
        semdata.block_locals.append(param_name)

    return None


def cleanup_scope(node, semdata):
    if node.nodetype in ["function_definition", "procedure_definition"]:
        for local_name in semdata.block_locals:
            if local_name in semdata.symtbl:
                del semdata.symtbl[local_name]
        semdata.current_context = None
    return None


def check_identifier_usage(node, semdata):
    nodetype = node.nodetype

    if nodetype in ["identifier", "function_call", "procedure_call"]:
        name = node.value

        if name not in semdata.symtbl:
            if nodetype == "identifier":
                return f"Undefined variable '{name}'"
            else:
                return f"Undefined function or procedure '{name}'"

    return None


def check_call_details(node, semdata):

    def verify_no_return_in_list(stmt_list):
        for stmt in stmt_list:
            if stmt.nodetype == "procedure_call":
                symbol = semdata.symtbl.get(stmt.value)
                if symbol and symbol.defnode.child_return_val is not None:
                    return f"Procedure '{stmt.value}' returns a value and must be used in an assignment"
        return None

    if node.nodetype == "program":
        err = verify_no_return_in_list(node.children_statements)
        if err:
            return err
    elif node.nodetype == "statement_list":
        err = verify_no_return_in_list(node.children_statements)
        if err:
            return err

    if node.nodetype == "assignment":
        source = node.child_source
        if source.nodetype == "procedure_call":
            symbol = semdata.symtbl.get(source.value)
            if symbol and symbol.defnode.child_return_val is None:
                return f"Procedure '{source.value}' does not return a value"

    if node.nodetype in ["function_call", "procedure_call"]:
        symbol = semdata.symtbl.get(node.value)
        if symbol:
            expected = len(symbol.defnode.children_formals)
            actual = len(node.children_arguments)
            if expected != actual:
                return f"'{node.value}' expects {expected} args, got {actual}"
    return None


def print_symbol_table(semdata, title):
    """Print the symbol table in semantic data

    Parameters:
    semdata: A SemData data structure containing semantic data
    title: String printed at the beginning
    """
    print(title)
    for name, data in semdata.symtbl.items():
        print(name, ":")
        for attr, value in vars(data).items():
            printvalue = value
            if hasattr(value, "nodetype"):  # If the value seems to be a ASTnode
                printvalue = value.nodetype
                if hasattr(value, "lineno"):
                    printvalue = printvalue + ", line " + str(value.lineno)
            print("  ", attr, "=", printvalue)


def validation_pass(node, semdata):
    err = handle_definitions(node, semdata)
    if err:
        return err

    err = check_identifier_usage(node, semdata)
    if err:
        return err

    err = check_call_details(node, semdata)
    if err:
        return err

    return None


def semantic_checks(tree, semdata):
    """run all semantic checks"""
    semdata.current_context = None
    semdata.block_locals = []
    simple_semantics_check.semantic_checks(tree, semdata)
    visit_tree(tree, before_func=collect_signatures, semdata=semdata)
    visit_tree(tree, before_func=check_for_recursion_cycles, semdata=semdata)

    visit_tree(
        tree,
        before_func=validation_pass,
        after_func=cleanup_scope,
        semdata=semdata,
    )


parser = full_ast.parser

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <filename>", file=sys.stderr)
        raise SystemExit
    else:
        data = open(sys.argv[1]).read()
        ast_tree = parser.parse(data, lexer=lexer.lexer, debug=False)
        treeprint(ast_tree)  # Just for debugging

        semdata = SemData()
        semantic_checks(ast_tree, semdata)
        print_symbol_table(semdata, "Symbol table:")  # Just for debugging
        print("Program ok.")
