"""Symbol extraction and hashing via tree-sitter.

Supported languages at launch: Python, TypeScript/TSX, JavaScript/JSX, Go.
A symbol is a top-level function/class or a method, addressed by its
qualified name (e.g. ``LoginService.authenticate``). The body hash is a
sha256 of the normalized source of the symbol node (comments stripped,
whitespace collapsed) so formatters do not produce false "stale" flags.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from tree_sitter_language_pack import get_parser

EXT_TO_LANG = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".go": "go",
}

# node types that define named symbols, per language
DEFINITION_TYPES = {
    "python": {"function_definition", "class_definition"},
    "typescript": {"function_declaration", "class_declaration", "method_definition",
                   "lexical_declaration", "interface_declaration", "enum_declaration"},
    "tsx": {"function_declaration", "class_declaration", "method_definition",
            "lexical_declaration", "interface_declaration", "enum_declaration"},
    "javascript": {"function_declaration", "class_declaration", "method_definition",
                   "lexical_declaration"},
    "go": {"function_declaration", "method_declaration", "type_declaration"},
}

COMMENT_TYPES = {"comment", "line_comment", "block_comment"}

KIND_MAP = {
    "function_definition": "function",
    "function_declaration": "function",
    "class_definition": "class",
    "class_declaration": "class",
    "method_definition": "method",
    "method_declaration": "method",
    "interface_declaration": "interface",
    "enum_declaration": "enum",
    "type_declaration": "type",
    "lexical_declaration": "const",
}


@dataclass
class Symbol:
    qualified_name: str
    kind: str
    body_hash: str
    start_line: int
    end_line: int


def language_for(path: str) -> Optional[str]:
    return EXT_TO_LANG.get(Path(path).suffix)


def _node_name(node, lang: str) -> Optional[str]:
    name_node = node.child_by_field_name("name")
    if name_node is not None:
        return name_node.text.decode()
    if node.type == "lexical_declaration":
        # const foo = () => {...} — take the first declarator's name
        for child in node.named_children:
            if child.type == "variable_declarator":
                n = child.child_by_field_name("name")
                if n is not None:
                    return n.text.decode()
    if lang == "go" and node.type == "method_declaration":
        n = node.child_by_field_name("name")
        if n is not None:
            return n.text.decode()
    if lang == "go" and node.type == "type_declaration":
        for child in node.named_children:
            if child.type == "type_spec":
                n = child.child_by_field_name("name")
                if n is not None:
                    return n.text.decode()
    return None


def _go_receiver(node) -> Optional[str]:
    recv = node.child_by_field_name("receiver")
    if recv is None:
        return None
    text = recv.text.decode()
    m = re.search(r"\*?\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)?\s*$", text)
    return m.group(1) if m else None


def _strip_comments(node, source: bytes, extra_spans: list[tuple[int, int]] | None = None) -> str:
    """Source of the node with comment nodes (and extra spans) removed."""
    spans: list[tuple[int, int]] = list(extra_spans or [])

    def collect(n):
        if n.type in COMMENT_TYPES:
            spans.append((n.start_byte, n.end_byte))
            return
        for child in n.children:
            collect(child)

    collect(node)
    spans.sort()
    text = source[node.start_byte:node.end_byte]
    offset = node.start_byte
    if spans:
        parts = []
        cursor = 0
        for start, end in spans:
            parts.append(text[cursor:start - offset])
            cursor = end - offset
        parts.append(text[cursor:])
        text = b"".join(parts)
    return text.decode(errors="replace")


def _normalize(code: str) -> str:
    code = re.sub(r"\s+", " ", code).strip()
    # drop spaces adjacent to punctuation so formatters can't cause false "stale"
    code = re.sub(r" ?([^\w\s]) ?", r"\1", code)
    return code


def _hash_body(node, source: bytes, lang: str) -> str:
    extra_spans = []
    name_node = node.child_by_field_name("name")
    if name_node is None and node.type == "lexical_declaration":
        for child in node.named_children:
            if child.type == "variable_declarator":
                n = child.child_by_field_name("name")
                if n is not None:
                    name_node = n
                    break
    elif name_node is None and lang == "go" and node.type == "method_declaration":
        n = node.child_by_field_name("name")
        if n is not None:
            name_node = n
    elif name_node is None and lang == "go" and node.type == "type_declaration":
        for child in node.named_children:
            if child.type == "type_spec":
                n = child.child_by_field_name("name")
                if n is not None:
                    name_node = n
                    break

    if name_node is not None:
        extra_spans.append((name_node.start_byte, name_node.end_byte))

    normalized = _normalize(_strip_comments(node, source, extra_spans=extra_spans))
    return hashlib.sha256(normalized.encode()).hexdigest()


def extract_symbols(path: Path, rel_path: str) -> list[Symbol]:
    """Extract all named symbols with body hashes from a source file."""
    lang = language_for(rel_path)
    if lang is None or not path.exists():
        return []
    source = path.read_bytes()
    parser = get_parser(lang)
    tree = parser.parse(source)
    definitions = DEFINITION_TYPES[lang]
    symbols: list[Symbol] = []

    def walk(node, scope: list[str]):
        for child in node.children:
            if child.type in definitions:
                name = _node_name(child, lang)
                if name:
                    if lang == "go" and child.type == "method_declaration":
                        receiver = _go_receiver(child)
                        qualified = f"{receiver}.{name}" if receiver else name
                    else:
                        qualified = ".".join([*scope, name])
                    symbols.append(Symbol(
                        qualified_name=qualified,
                        kind=KIND_MAP.get(child.type, child.type),
                        body_hash=_hash_body(child, source, lang),
                        start_line=child.start_point[0] + 1,
                        end_line=child.end_point[0] + 1,
                    ))
                    walk(child, [*scope, name] if name else scope)
                    continue
            walk(child, scope)

    walk(tree.root_node, [])
    return symbols


def find_symbol(path: Path, rel_path: str, qualified_name: str) -> Optional[Symbol]:
    for sym in extract_symbols(path, rel_path):
        if sym.qualified_name == qualified_name:
            return sym
    return None


def find_by_body_hash(path: Path, rel_path: str, body_hash: str) -> Optional[Symbol]:
    """Locate a (possibly renamed) symbol by its identical body hash."""
    for sym in extract_symbols(path, rel_path):
        if sym.body_hash == body_hash:
            return sym
    return None
