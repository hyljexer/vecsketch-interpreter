import full_ast
import lexer
import simple_semantics_check
from semantics_common import SemData, SymbolData, visit_tree
from syntax_common import get_childvars, treeprint


def get_type(node, semdata):
    if node is None:
        return None

    nt = node.nodetype

    if nt == "int_literal":
        return "number"
    if nt == "shape_literal":
        return "shape"
    if nt == "string_literal":
        return "string"

    if nt == "identifier":
        sym = semdata.symtbl.get(node.value)
        return getattr(sym, "datatype", None) if sym else None

    if nt == "property_access":
        return "number"

    if nt == "function_call":
        sym = semdata.symtbl.get(node.value)
        if sym and hasattr(sym.defnode, "child_return_type"):
            return sym.defnode.child_return_type.value
        return None

    if nt == "procedure_call":
        sym = semdata.symtbl.get(node.value)
        return getattr(sym, "datatype", None) if sym else None

    if nt == "expression":
        op = node.value
        if op in ["=", "/=", "<"]:
            return "number"
        return get_type(node.child_left, semdata)

    if nt == "unary_expression":
        return get_type(node.child_atom, semdata)

    return None


def collect_signatures(node, semdata):
    if node.nodetype in ["function_definition", "procedure_definition"]:
        name = node.value
        if name in semdata.symtbl:
            return f"Redefined name '{name}'"
        sym = SymbolData(node.nodetype, node)
        if node.nodetype == "function_definition":
            sym.datatype = node.child_return_type.value
        semdata.symtbl[name] = sym
    return None


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
                return f"Recursion detected: {cycle_path}"
    return None


def handle_definitions(node, semdata):
    nodetype = node.nodetype

    if nodetype in ["function_definition", "procedure_definition"]:
        semdata.current_context = node
        semdata.block_locals = {}

    if nodetype == "variable_definition":
        var_name = node.value
        declared_type = node.child_type.value

        if semdata.current_context:
            if var_name in [
                n for n in semdata.block_locals if semdata.block_locals[n] is None
            ]:
                return f"Redefined local variable '{var_name}'"
        elif var_name in semdata.symtbl:
            return f"Redefined global variable '{var_name}'"

        init_type = get_type(node.child_expression, semdata)
        if init_type and init_type != declared_type:
            return f"Variable '{var_name}' initialized with wrong type (expected {declared_type}, got {init_type})"

        sym = SymbolData(
            "local_variable" if semdata.current_context else "global_variable", node
        )
        sym.datatype = declared_type

        if semdata.current_context:
            semdata.block_locals[var_name] = semdata.symtbl.get(var_name)
        semdata.symtbl[var_name] = sym

    if nodetype == "formal_arg":
        name = node.value
        dtype = node.child_type.value
        sym = SymbolData("parameter", node)
        sym.datatype = dtype
        semdata.block_locals[name] = semdata.symtbl.get(name)
        semdata.symtbl[name] = sym

    if nodetype == "procedure_definition":
        if node.child_return_val:
            semdata.symtbl[node.value].datatype = get_type(
                node.child_return_val, semdata
            )

    return None


def type_validation(node, semdata):
    nt = node.nodetype

    if nt == "assignment":
        target_t = get_type(node.child_target, semdata)
        source_t = get_type(node.child_source, semdata)
        if target_t and source_t and target_t != source_t:
            return f"Type mismatch: cannot assign {source_t} to {target_t}"

    if nt == "property_access":
        var_name = node.value.split(".")[0]
        sym = semdata.symtbl.get(var_name)
        if sym and sym.datatype != "shape":
            return f"Property error: '{var_name}' is not a shape"

    if nt == "wait":
        if get_type(node.child_expression, semdata) != "number":
            return "Wait statement requires a number"
    if nt == "draw":
        if get_type(node.child_shape, semdata) != "shape":
            return "Draw statement requires a shape"
        if node.child_color:
            if any(
                get_type(c, semdata) != "number"
                for c in [
                    node.child_color.child_r,
                    node.child_color.child_g,
                    node.child_color.child_b,
                ]
            ):
                return "RGB color components must be numbers"

    if nt == "expression":
        lt = get_type(node.child_left, semdata)
        rt = get_type(node.child_right, semdata)
        op = node.value
        if lt == "shape" and op in ["+", "-", "="] and rt != "shape":
            return f"Operator '{op}' on shape requires another shape"
        if lt == "number" and op in ["+", "-"] and rt != "number":
            return f"Operator '{op}' on number requires another number"

    if nt in ["function_call", "procedure_call"]:
        sym = semdata.symtbl.get(node.value)
        if sym:
            formals = sym.defnode.children_formals
            actuals = node.children_arguments
            if len(formals) == len(actuals):
                for f, a in zip(formals, actuals):
                    ft = f.child_type.value
                    at = get_type(a, semdata)
                    if at and ft != at:
                        return f"Arg mismatch: '{node.value}' expects {ft}, got {at}"

    if nt == "function_definition":
        declared = node.child_return_type.value
        actual = get_type(node.child_body, semdata)
        if actual and declared != actual:
            return f"Function '{node.value}' returns {actual}, but declared {declared}"

    return None


def cleanup_scope(node, semdata):
    if node.nodetype in ["function_definition", "procedure_definition"]:
        for name, old_sym in semdata.block_locals.items():
            if old_sym is None:
                if name in semdata.symtbl:
                    del semdata.symtbl[name]
            else:
                semdata.symtbl[name] = old_sym
        semdata.current_context = None
    return None


def check_identifier_usage(node, semdata):
    if node.nodetype in ["identifier", "function_call", "procedure_call"]:
        if node.value not in semdata.symtbl:
            return f"Undefined '{node.value}'"
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


def semantic_checks(tree, semdata):
    semdata.current_context = None
    semdata.block_locals = {}

    simple_semantics_check.semantic_checks(tree, semdata)

    visit_tree(tree, before_func=collect_signatures, semdata=semdata)
    visit_tree(tree, before_func=check_for_recursion_cycles, semdata=semdata)

    def combined_pass(n, s):
        err = handle_definitions(n, s)
        if err:
            return err
        err = check_identifier_usage(n, s)
        if err:
            return err
        err = check_call_details(n, s)
        if err:
            return err

        err = type_validation(n, s)
        if err:
            return err

    visit_tree(
        tree, before_func=combined_pass, after_func=cleanup_scope, semdata=semdata
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
        # treeprint(ast_tree)  # Just for debugging

        semdata = SemData()
        semantic_checks(ast_tree, semdata)
        # print_symbol_table(semdata, "Symbol table:")  # Just for debugging
        print("Program ok.")
