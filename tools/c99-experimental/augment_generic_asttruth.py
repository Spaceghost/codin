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
        raise SystemExit(f"augment_generic_asttruth: {label}: expected {expected} anchors, found {count}")
    src = src.replace(old, new)


replace_count(
    "trust TYPE_POLY instead of ProcedureKind",
    'if (!procedure || !procedure->type || procedure->type->kind != PROCEDURE_GENERIC) return false;',
    'if (!procedure || !procedure->type) return false;',
    1,
)

replace_count(
    "generic predicate helper",
    '''\t*type_name = param_name;
\treturn true;
}

static const char *generic_suffix''',
    '''\t*type_name = param_name;
\treturn true;
}

static Bool is_supported_generic(const ProcedureExpression *procedure) {
\tString name = STRING_NIL;
\treturn generic_shape(procedure, &name);
}

static const char *generic_suffix''',
    1,
)

replace_count(
    "generic call-site detection",
    'symbol && symbol->procedure && symbol->procedure->type->kind == PROCEDURE_GENERIC',
    'symbol && symbol->procedure && is_supported_generic(symbol->procedure)',
    2,
)

replace_count(
    "skip generic templates",
    'if (procedure->type->kind == PROCEDURE_GENERIC) continue;',
    'if (is_supported_generic(procedure)) continue;',
    2,
)

path.write_text(src)
print("augment_generic_asttruth: TYPE_POLY is authoritative for generic detection")
