import ast
import importlib.util
import os
import sys
from pathlib import Path

ROUTE_DECORATOR_NAMES = {
    "get",
    "post",
    "put",
    "delete",
    "patch",
    "options",
    "head",
    "websocket",
    "route",
    "on_event",
}


def iter_python_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            path = Path(dirpath) / filename
            try:
                rel_parts = path.relative_to(root).parts
            except ValueError:
                rel_parts = path.parts
            if "alembic" in rel_parts and "versions" in rel_parts:
                continue
            yield path


def module_name_from_path(root, path):
    rel = path.relative_to(root)
    parts = list(rel.parts)
    if not parts:
        return ""
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1][:-3]
    return ".".join(part for part in parts if part)


def attach_parents(tree):
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            setattr(child, "_parent", parent)


def extract_target_names(target):
    names = []
    if isinstance(target, ast.Name):
        names.append(target.id)
    elif isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            names.extend(extract_target_names(elt))
    return names


def resolve_attribute_chain(node):
    attrs = []
    current = node
    while isinstance(current, ast.Attribute):
        attrs.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        attrs.reverse()
        return current.id, attrs
    return None, []


def package_name(module_name, module_index):
    if not module_name:
        return None
    info = module_index.get(module_name)
    if info and info.get("is_package"):
        return module_name
    head, _, _ = module_name.rpartition(".")
    return head or None


def resolve_import_module(current_module, level, module, module_index):
    if level == 0:
        return module or ""
    package = package_name(current_module, module_index)
    if not package:
        return module or ""
    relative = "." * level + (module or "")
    try:
        return importlib.util.resolve_name(relative, package)
    except ImportError:
        return module or ""


def resolve_alias_target(module_name, symbol_name, alias_registry):
    visited = set()
    current = (module_name, symbol_name)
    while current in alias_registry and current not in visited:
        visited.add(current)
        current = alias_registry[current]
    return current


class Analyzer(ast.NodeVisitor):
    def __init__(self, module_name, module_index):
        self.current_module = module_name
        self.module_index = module_index
        self.functions = {}
        self.decorated_used = set()
        self.variables = {}
        self.aliases = {}
        self.name_loads = set()
        self.attr_loads = []
        self.alias_exports = {}

    def visit_FunctionDef(self, node):
        if isinstance(getattr(node, "_parent", None), ast.Module):
            self.functions.setdefault(node.name, node.lineno)
            if any(is_router_decorator(dec) for dec in node.decorator_list):
                self.decorated_used.add(node.name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        if isinstance(getattr(node, "_parent", None), ast.Module):
            self.functions.setdefault(node.name, node.lineno)
            if any(is_router_decorator(dec) for dec in node.decorator_list):
                self.decorated_used.add(node.name)
        self.generic_visit(node)

    def visit_Assign(self, node):
        if isinstance(getattr(node, "_parent", None), ast.Module):
            for target in node.targets:
                for name in extract_target_names(target):
                    self.variables.setdefault(name, node.lineno)
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        if isinstance(getattr(node, "_parent", None), ast.Module):
            for name in extract_target_names(node.target):
                self.variables.setdefault(name, node.lineno)
        self.generic_visit(node)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.name_loads.add(node.id)
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            full_name = alias.name
            alias_name = alias.asname or full_name.split(".")[0]
            if alias.asname:
                module_path = full_name
            else:
                module_path = full_name.split(".")[0]
            self.aliases[alias_name] = {"kind": "module", "module": module_path}
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        base_module = resolve_import_module(
            self.current_module, node.level or 0, node.module, self.module_index
        )
        for alias in node.names:
            if alias.name == "*":
                continue
            alias_name = alias.asname or alias.name
            candidate_module = ".".join(
                part for part in [base_module, alias.name] if part
            )
            if candidate_module in self.module_index:
                self.aliases[alias_name] = {
                    "kind": "module",
                    "module": candidate_module,
                }
            else:
                self.aliases[alias_name] = {
                    "kind": "symbol",
                    "module": base_module,
                    "name": alias.name,
                }
                if base_module:
                    self.alias_exports[alias_name] = (base_module, alias.name)
        self.generic_visit(node)

    def visit_Attribute(self, node):
        if isinstance(node.ctx, ast.Load):
            root, attrs = resolve_attribute_chain(node)
            if root and attrs:
                self.attr_loads.append((root, attrs))
        self.generic_visit(node)


def is_router_decorator(node):
    target = node
    if isinstance(node, ast.Call):
        target = node.func
    if isinstance(target, ast.Attribute):
        if target.attr in ROUTE_DECORATOR_NAMES:
            return True
    return False


def main():
    if len(sys.argv) > 1:
        root = Path(sys.argv[1]).resolve()
    else:
        root = Path.cwd()
    module_index = {}
    for path in iter_python_files(root):
        try:
            module_name = module_name_from_path(root, path)
        except ValueError:
            continue
        if not module_name:
            module_name = path.stem
        try:
            rel_parts = path.relative_to(root).parts
        except ValueError:
            rel_parts = path.parts
        module_index[module_name] = {
            "path": path,
            "is_package": path.name == "__init__.py",
            "is_test": "tests" in rel_parts,
        }
    analyzers = {}
    alias_registry = {}
    for module_name, info in module_index.items():
        path = info["path"]
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue
        attach_parents(tree)
        analyzer = Analyzer(module_name, module_index)
        analyzer.visit(tree)
        analyzers[module_name] = analyzer
        for alias_name, target in analyzer.alias_exports.items():
            alias_registry[(module_name, alias_name)] = target
    definitions = {}
    usage = {}
    for module_name, analyzer in analyzers.items():
        info = module_index[module_name]
        file_path = info["path"]
        if not info["is_test"]:
            for name, lineno in analyzer.functions.items():
                if name == "__getattr__":
                    continue
                key = (module_name, name)
                definitions[key] = {
                    "kind": "function",
                    "file": file_path,
                    "line": lineno,
                }
                usage[key] = False
            for name, lineno in analyzer.variables.items():
                if name == "__all__":
                    continue
                key = (module_name, name)
                definitions[key] = {
                    "kind": "variable",
                    "file": file_path,
                    "line": lineno,
                }
                usage[key] = False
        for name in analyzer.decorated_used:
            key = (module_name, name)
            if key in usage:
                usage[key] = True
    for module_name, analyzer in analyzers.items():
        for name in analyzer.name_loads:
            key = (module_name, name)
            if key in usage:
                usage[key] = True
        for alias_name, alias_info in analyzer.aliases.items():
            if alias_info["kind"] == "symbol":
                target = resolve_alias_target(
                    alias_info["module"], alias_info["name"], alias_registry
                )
                if alias_name in analyzer.name_loads and target in usage:
                    usage[target] = True
        for root, attrs in analyzer.attr_loads:
            alias_info = analyzer.aliases.get(root)
            if not alias_info or not attrs:
                continue
            if alias_info["kind"] == "module":
                current = alias_info["module"]
                for attr in attrs[:-1]:
                    candidate = ".".join(part for part in [current, attr] if part)
                    if candidate in module_index:
                        current = candidate
                    else:
                        current = None
                        break
                if current is None:
                    continue
                key = (current, attrs[-1])
                if key in usage:
                    usage[key] = True
            elif alias_info["kind"] == "symbol":
                target = resolve_alias_target(
                    alias_info["module"], alias_info["name"], alias_registry
                )
                if target in usage:
                    usage[target] = True
    unused = []
    for key, info in definitions.items():
        if not usage.get(key):
            unused.append(
                {
                    "kind": info["kind"],
                    "name": key[1],
                    "file": info["file"],
                    "line": info["line"],
                }
            )
    unused.sort(key=lambda item: (str(item["file"]), item["line"], item["name"]))
    if unused:
        for item in unused:
            try:
                rel_path = item["file"].resolve().relative_to(root)
            except ValueError:
                rel_path = item["file"]
            print(f"{item['kind']}\t{item['name']}\t{rel_path}:{item['line']}")
    else:
        print("No unused top-level functions or variables detected.")


if __name__ == "__main__":
    main()
