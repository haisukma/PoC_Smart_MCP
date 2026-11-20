import ast
import builtins

ALLOWED_IMPORTS = {
    "pandas",
    "numpy",
    "math",
    "statistics",
    "datetime",
}

def restricted_import(
    name,
    globals=None,
    locals=None,
    fromlist=(),
    level=0
):
    if level != 0:
        raise ImportError("Relative import tidak diizinkan.")

    root_module = name.split(".")[0]
    if root_module not in ALLOWED_IMPORTS:
        raise ImportError(f"Library '{root_module}' tidak diizinkan")

    return builtins.__import__(name, globals, locals, fromlist, level)

def get_restricted_builtins():
    allowed_builtins = builtins.__dict__.copy()
    allowed_builtins["__import__"] = restricted_import
    return allowed_builtins

BLOCKED_IMPORTS = {
    "os",
    "sys",
    "subprocess",
    "socket",
    "shutil",
    "ctypes",
    "importlib",
    "pickle",
}

BLOCKED_CALLS = {
    "open",
    "eval",
    "exec",
    "compile",
    "input",
    "__import__",
    "getattr",
    "setattr",
    "delattr",
}

MAX_CODE_LENGTH = 5_000

class CodeValidator(ast.NodeVisitor):
    def visit_Import(self, node):
        for alias in node.names:
            root = alias.name.split(".")[0]

            if root not in ALLOWED_IMPORTS:
                raise ValueError(f"Import tidak diizinkan: {root}"
)

        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.level != 0:
            raise ValueError("Relative import tidak diizinkan")

        if node.module:
            root = node.module.split(".")[0]

            if root not in ALLOWED_IMPORTS:
                raise ValueError(f"Import tidak diizinkan: {root}")

        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id in BLOCKED_CALLS:
                raise ValueError(f"Fungsi tidak diizinkan: {node.func.id}")

        self.generic_visit(node)

    def visit_Attribute(self, node):
        if node.attr.startswith("__"):
            raise ValueError(f"Akses atribut tidak diizinkan: {node.attr}")

        self.generic_visit(node)

def validate_code(code: str):
    if not isinstance(code, str):
        raise ValueError("Kode harus berupa string.")

    if len(code) > MAX_CODE_LENGTH:
        raise ValueError("Kode terlalu panjang.")

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise ValueError(
            f"Syntax error pada kode: {exc}"
        ) from exc

    CodeValidator().visit(tree)

    return True
