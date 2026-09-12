#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit(f"usage: {sys.argv[0]} path/to/src/c99.c")

path = Path(sys.argv[1])
src = path.read_text()


def replace_once(label: str, old: str, new: str) -> None:
    global src
    count = src.count(old)
    if count != 1:
        raise SystemExit(f"augment_diagnostics: {label}: expected 1 anchor, found {count}")
    src = src.replace(old, new, 1)


replace_once(
    "named result error",
    '''\tCType result = sema_procedure_result(procedure);
\tconst char *result_name = sema_c_type_name(result);
\tif (!result_name) return unsupported(c, "procedure result type");
\tfputs(result_name, c->out);''',
    '''\tCType result = sema_procedure_result(procedure);
\tconst char *result_name = sema_c_type_name(result);
\tif (!result_name) {
\t\tconst Size n_results = array_size(procedure->type->results);
\t\tint ast_kind = -1;
\t\tif (n_results == 1 && procedure->type->results[0] && procedure->type->results[0]->type) {
\t\t\tast_kind = (int)procedure->type->results[0]->type->kind;
\t\t}
\t\tfprintf(stderr,
\t\t        "codin: c99: procedure %.*s has unsupported result: count=%zu ctype=%d ast-kind=%d\\n",
\t\t        SFMT(name->contents), (size_t)n_results, (int)result, ast_kind);
\t\treturn unsupported(c, "procedure result type");
\t}
\tfputs(result_name, c->out);''',
)

replace_once(
    "stage tracer",
    '''Bool c99_emit_build(FILE *out, BuildContext *build) {''',
    '''static void diagnostic_decimal_result(const BuildContext *build, const char *stage) {
\tconst Size n_work = array_size(build->work);
\tfor (Size w = 0; w < n_work; w++) {
\t\tconst Tree *tree = build->work[w]->tree;
\t\tconst Size n_statements = array_size(tree->statements);
\t\tfor (Size i = 0; i < n_statements; i++) {
\t\t\tif (tree->statements[i]->kind != STATEMENT_DECLARATION) continue;
\t\t\tconst DeclarationStatement *decl = RCAST(const DeclarationStatement *, tree->statements[i]);
\t\t\tif (array_size(decl->names) != 1 ||
\t\t\t    !string_compare(decl->names[0]->contents, SCLIT("decimal_size")) ||
\t\t\t    !decl->values || array_size(decl->values->expressions) != 1 ||
\t\t\t    decl->values->expressions[0]->kind != EXPRESSION_PROCEDURE) continue;
\t\t\tconst ProcedureExpression *proc = RCAST(const ProcedureExpression *, decl->values->expressions[0]);
\t\t\tconst Size n_results = array_size(proc->type->results);
\t\t\tconst Type *type = n_results == 1 ? proc->type->results[0]->type : NULL;
\t\t\tfprintf(stderr,
\t\t\t        "codin: diagnostic: decimal_size stage=%s result=%p kind=%d ctype=%d\\n",
\t\t\t        stage, (const void *)type, type ? (int)type->kind : -1,
\t\t\t        type ? (int)sema_type_from_ast(type) : -1);
\t\t}
\t}
}

Bool c99_emit_build(FILE *out, BuildContext *build) {''',
)

replace_once(
    "pipeline stages",
    '''\tc.generic_instance_count = 0;
\tc.generic_type_name = STRING_NIL;
\tc.generic_type = CTYPE_UNKNOWN;
\tsema_init(&c.sema);
\tif (!sema_collect_globals(&c.sema, build)) return false;
\tif (!discover_generic_instances(&c, build)) return false;''',
    '''\tc.generic_instance_count = 0;
\tc.generic_type_name = STRING_NIL;
\tc.generic_type = CTYPE_UNKNOWN;
\tdiagnostic_decimal_result(build, "parsed");
\tsema_init(&c.sema);
\tif (!sema_collect_globals(&c.sema, build)) return false;
\tdiagnostic_decimal_result(build, "after-sema");
\tif (!discover_generic_instances(&c, build)) return false;
\tdiagnostic_decimal_result(build, "after-generic-discovery");''',
)

path.write_text(src)
print("augment_diagnostics: tracing decimal_size result through the C99 pipeline")
