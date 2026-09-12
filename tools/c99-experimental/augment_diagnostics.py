#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit(f"usage: {sys.argv[0]} path/to/src/c99.c")

path = Path(sys.argv[1])
src = path.read_text()
old = '''\tCType result = sema_procedure_result(procedure);
\tconst char *result_name = sema_c_type_name(result);
\tif (!result_name) return unsupported(c, "procedure result type");
\tfputs(result_name, c->out);'''
new = '''\tCType result = sema_procedure_result(procedure);
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
\tfputs(result_name, c->out);'''
count = src.count(old)
if count != 1:
    raise SystemExit(f"augment_diagnostics: expected 1 result-type anchor, found {count}")
path.write_text(src.replace(old, new, 1))
print("augment_diagnostics: procedure result failures now name the offending AST")
