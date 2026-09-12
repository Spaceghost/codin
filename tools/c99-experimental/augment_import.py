#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit(f"usage: {sys.argv[0]} path/to/src/c99.c")

path = Path(sys.argv[1])
src = path.read_text()


def replace_count(label: str, old: str, new: str, expected: int) -> None:
    global src
    count = src.count(old)
    if count != expected:
        raise SystemExit(f"augment_import: {label}: expected {expected} anchors, found {count}")
    src = src.replace(old, new)


def replace_once(label: str, old: str, new: str) -> None:
    replace_count(label, old, new, 1)


replace_once(
    "package state",
    '''\tC99UnionLocal union_locals[128];
\tSize union_local_count;
} C99;''',
    '''\tC99UnionLocal union_locals[128];
\tSize union_local_count;
\tconst Package *root_package;
\tconst Package *current_package;
\tconst Tree *current_tree;
\tString current_package_name;
} C99;''',
)

replace_once(
    "package helpers",
    '''static Bool emit_identifier(C99 *c, const Identifier *identifier) {''',
    '''static String tree_package_name(const Tree *tree) {
\tif (!tree || !array_size(tree->statements)) return STRING_NIL;
\tconst Statement *statement = tree->statements[0];
\tif (statement->kind != STATEMENT_PACKAGE) return STRING_NIL;
\treturn RCAST(const PackageStatement *, statement)->name;
}

static Bool import_alias_matches(const C99 *c, String name) {
\tif (!c->current_tree) return false;
\tconst Size n_imports = array_size(c->current_tree->imports);
\tfor (Size i = 0; i < n_imports; i++) {
\t\tconst ImportStatement *import = c->current_tree->imports[i];
\t\tif (import->name.length && string_compare(import->name, name)) return true;
\t}
\treturn false;
}

static Bool emit_declaration_name(C99 *c, const Identifier *identifier) {
\tif (c->current_package && c->root_package && c->current_package != c->root_package) {
\t\tfprintf(c->out, "%.*s__%.*s", SFMT(c->current_package_name), SFMT(identifier->contents));
\t} else {
\t\tfprintf(c->out, "%.*s", SFMT(identifier->contents));
\t}
\treturn true;
}

static Bool emit_identifier(C99 *c, const Identifier *identifier) {''',
)

replace_once(
    "import selector lowering",
    '''\t\tif (selector->operand->kind == EXPRESSION_IDENTIFIER) {
\t\t\tconst Identifier *type_name =
\t\t\t\tRCAST(const IdentifierExpression *, selector->operand)->identifier;
\t\t\tconst Type *named_type = sema_lookup_named_type(&c->sema, type_name->contents);''',
    '''\t\tif (selector->operand->kind == EXPRESSION_IDENTIFIER) {
\t\t\tconst Identifier *type_name =
\t\t\t\tRCAST(const IdentifierExpression *, selector->operand)->identifier;
\t\t\tif (import_alias_matches(c, type_name->contents)) {
\t\t\t\tfprintf(c->out, "%.*s__%.*s",
\t\t\t\t        SFMT(type_name->contents), SFMT(selector->identifier->contents));
\t\t\t\treturn true;
\t\t\t}
\t\t\tconst Type *named_type = sema_lookup_named_type(&c->sema, type_name->contents);''',
)

replace_count(
    "procedure declaration names",
    '''\tif (!emit_procedure_result_type(c, name, procedure)) return false;
\tfprintf(c->out, " %.*s(", SFMT(name->contents));
\tif (!emit_parameters(c, procedure)) return false;''',
    '''\tif (!emit_procedure_result_type(c, name, procedure)) return false;
\tfputc(' ', c->out);
\tif (!emit_declaration_name(c, name)) return false;
\tfputc('(', c->out);
\tif (!emit_parameters(c, procedure)) return false;''',
    2,
)

replace_once(
    "work package context",
    '''\tfor (Size w = 0; w < n_work; w++) {
\t\tTree *tree = build->work[w]->tree;
\t\tconst Size n_statements = array_size(tree->statements);''',
    '''\tfor (Size w = 0; w < n_work; w++) {
\t\tBuildWork *work = build->work[w];
\t\tTree *tree = work->tree;
\t\tc->current_package = work->package;
\t\tc->current_tree = tree;
\t\tc->current_package_name = tree_package_name(tree);
\t\tconst Size n_statements = array_size(tree->statements);''',
)

replace_once(
    "root package state",
    '''\tc.union_local_count = 0;
\tsema_init(&c.sema);''',
    '''\tc.union_local_count = 0;
\tc.root_package = array_size(build->project.packages) ? build->project.packages[0] : NULL;
\tc.current_package = NULL;
\tc.current_tree = NULL;
\tc.current_package_name = STRING_NIL;
\tsema_init(&c.sema);''',
)

path.write_text(src)
print("augment_import: explicit import aliases + package-qualified symbols applied")
