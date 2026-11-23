import sys

import astsem
import full_ast
import lexer
import vecsketch_lib as lib
from semantics_common import SemData


class Interpreter:
    def __init__(self, ast, semdata):
        self.ast = ast
        self.semdata = semdata
        self.globals = {}
        self.stack = []
        self.functions = {}
        self.window_opened = False

    def get_var(self, name):
        if self.stack:
            if name in self.stack[-1]:
                return self.stack[-1][name]
        if name in self.globals:
            return self.globals[name]
        raise NameError(f"Variable '{name}' not found.")

    def set_var(self, name, value):
        if self.stack and name in self.stack[-1]:
            self.stack[-1][name] = value
            return
        if name in self.globals:
            self.globals[name] = value
        else:
            if self.stack:
                self.stack[-1][name] = value
            else:
                self.globals[name] = value

    def ensure_window(self):
        if not self.window_opened:
            lib.window_open()
            self.window_opened = True

    def evaluate(self, node):
        if node is None:
            return None

        ntype = node.nodetype

        if ntype == "int_literal":
            return node.value
        if ntype == "string_literal":
            return node.value
        if ntype == "identifier":
            return self.get_var(node.value)

        if ntype == "shape_literal":
            coords = []
            for coord_node in node.children_coordinates:
                x = self.evaluate(coord_node.child_x)
                y = self.evaluate(coord_node.child_y)
                coords.append((x, y))
            if node.value == "+":
                return lib.create_polygon(coords)
            if len(coords) == 1:
                return lib.create_point(coords[0][0], coords[0][1])
            return lib.create_linestring(coords)

        if ntype == "expression":
            left = self.evaluate(node.child_left)
            op = node.value
            if op == "->":
                c = node.child_right
                return lib.shape_move(
                    left, self.evaluate(c.child_x), self.evaluate(c.child_y)
                )

            right = self.evaluate(node.child_right)
            if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                if op == "+":
                    return left + right
                if op == "-":
                    return left - right
                if op == "*":
                    return left * right
                if op == "/":
                    return left / right
                if op == "=":
                    return 1 if left == right else 0
                if op == "/=":
                    return 1 if left != right else 0
                if op == "<":
                    return 1 if left < right else 0

            if hasattr(left, "geom_type"):
                if op == "+":
                    return lib.shape_union(left, right)
                if op == "-":
                    return lib.shape_difference(left, right)
                if op == "*":
                    if hasattr(right, "geom_type"):
                        return lib.shape_intersection(left, right)
                    return lib.shape_scale(left, right)
                if op == "/":
                    return lib.shape_rotate(left, right)
                if op == "=":
                    return 1 if lib.shape_equals(left, right) else 0
                if op == "/=":
                    return 1 if not lib.shape_equals(left, right) else 0
                if op == "<":
                    return 1 if lib.shape_covered_by(left, right) else 0

        if ntype == "unary_expression":
            val = self.evaluate(node.child_atom)
            if hasattr(val, "geom_type"):
                if node.value == "+":
                    return lib.shape_polygonize(val)
                if node.value == "-":
                    return lib.shape_downgrade(val)
            return -val if node.value == "-" else val

        if ntype == "property_access":
            parts = node.value.split(".")
            shape = self.get_var(parts[0])
            attr = parts[1]
            if attr == "x":
                return lib.shape_xcoord(shape)
            if attr == "y":
                return lib.shape_ycoord(shape)
            b = lib.shape_bounds(shape)
            mapping = {"xmin": 0, "ymin": 1, "xmax": 2, "ymax": 3}
            return b[mapping[attr]]

        if ntype == "statement_list":
            for stmt in node.children_statements:
                self.evaluate(stmt)
            return

        if ntype == "statement":
            self.ensure_window()
            if node.value == "pause":
                lib.window_pause()
            elif node.value == "clear":
                lib.window_clear()
            return

        if ntype == "assignment":
            self.set_var(node.child_target.value, self.evaluate(node.child_source))

        if ntype == "print":
            out = []
            for item in node.children_items:
                res = self.evaluate(item)
                if hasattr(res, "geom_type"):
                    out.append(lib.shape_tostring(res))
                else:
                    out.append(str(res))
            print(" ".join(out))

        if ntype == "draw":
            self.ensure_window()
            s = self.evaluate(node.child_shape)
            c = node.child_color
            if c:
                lib.window_draw(
                    s,
                    self.evaluate(c.child_r),
                    self.evaluate(c.child_g),
                    self.evaluate(c.child_b),
                )
            else:
                lib.window_draw(s)

        if ntype == "wait":
            self.ensure_window()
            lib.window_wait(self.evaluate(node.child_expression))

        if ntype == "if":
            if self.evaluate(node.child_condition):
                self.evaluate(node.child_then)
            elif hasattr(node, "child_else"):
                self.evaluate(node.child_else)

        if ntype == "while":
            while self.evaluate(node.child_condition):
                for s in node.children_body:
                    self.evaluate(s)

        if ntype in ["function_definition", "procedure_definition"]:
            self.functions[node.value] = node

        if ntype in ["function_call", "procedure_call"]:
            f = self.functions[node.value]
            args = [self.evaluate(a) for a in node.children_arguments]
            new_scope = {form.value: val for form, val in zip(f.children_formals, args)}
            self.stack.append(new_scope)
            for v_def in f.children_local_vars:
                self.evaluate(v_def)
            res = (
                self.evaluate(f.child_body)
                if f.nodetype == "function_definition"
                else None
            )
            if f.nodetype == "procedure_definition":
                for s in f.children_statements:
                    self.evaluate(s)
                if f.child_return_val:
                    res = self.evaluate(f.child_return_val)
            self.stack.pop()
            return res

        if ntype == "variable_definition":
            self.set_var(node.value, self.evaluate(node.child_expression))

        if ntype == "program":
            for d in node.children_definitions:
                if d.nodetype in ["function_definition", "procedure_definition"]:
                    self.functions[d.value] = d
                else:
                    self.evaluate(d)
            for s in node.children_statements:
                self.evaluate(s)

        known_types = ["coordinate", "formal_arg", "type", "rgb"]
        if ntype not in known_types:
            pass

    def run(self):
        try:
            self.evaluate(self.ast)
            if self.window_opened:
                lib.window_close()
        except Exception as e:
            print(f"Runtime Error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <filename>", file=sys.stderr)
        sys.exit(1)
    data = open(sys.argv[1]).read()
    try:
        tree = full_ast.parser.parse(data, lexer=lexer.lexer)
        semdata = SemData()
        astsem.semantic_checks(tree, semdata)
        print("Program ok.")
        Interpreter(tree, semdata).run()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
