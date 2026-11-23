import full_ast
import lexer
from semantics_common import SemData, SymbolData, visit_tree
from syntax_common import treeprint


def check_variable_attributes(node, semdata):
    nodetype = node.nodetype
    if nodetype == "property_access":
        attribute = node.value.split(".")[-1]
        if attribute not in ["x", "y", "xmin", "xmax", "ymin", "ymax"]:
            return f"Invalid attribute '{attribute}' of variable '{node.value.split('.')[0]}'"
        else:
            return None


def check_variable_types(node, semdata):
    nodetype = node.nodetype
    if nodetype == "type":
        if node.value not in ["number", "shape"]:
            return f"Invalid type '{node.value}'"
        else:
            return None


def check_comparison_in_control_structs(node, semdata):
    nodetype = node.nodetype
    if nodetype in ["if", "while"]:
        condition = node.child_condition
        valid_comparisons = ["=", "/=", "<"]
        if not (
            condition.nodetype == "expression" and condition.value in valid_comparisons
        ):
            return f"Invalid comparison in {node.nodetype}"


def semantic_checks(tree, semdata):
    """run simple semantic checks"""

    visit_tree(tree, check_variable_attributes, None, semdata)
    visit_tree(tree, check_variable_types, None, semdata)
    visit_tree(tree, check_comparison_in_control_structs, None, semdata)


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
        print("Program ok.")
