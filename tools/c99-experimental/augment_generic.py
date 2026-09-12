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
        raise SystemExit(f"augment_generic: {label}: expected exactly one anchor, found {count}")
    src = src.replace(old, new, 1)


replace_once(
    "generic state",
    '''\tconst Package *current_package;
\tconst Tree *current_tree;
\tString current_package_name;
} C99;''',
    '''\tconst Package *current_package;
\tconst Tree *current_tree;
\tString current_package_name;
\tstruct {
\t\tString name;
\t\tconst ProcedureExpression *procedure;
\t\tCType type;
\t} generic_instances[128];
\tSize generic_instance_count;
\tString generic_type_name;
\tCType generic_type;
} C99;''',
)

replace_once(
    "generic helpers",
    '''static Bool emit_ast_type(C99 *c, const Type *type) {''',
    '''static Bool type_identifier_name(const Type *type, String *name) {
\tif (!type || type->kind != TYPE_EXPRESSION) return false;
\tconst Expression *expression = RCAST(const ExpressionType *, type)->expression;
\tif (!expression || expression->kind != EXPRESSION_IDENTIFIER) return false;
\t*name = RCAST(const IdentifierExpression *, expression)->identifier->contents;
\treturn true;
}

static Bool generic_shape(const ProcedureExpression *procedure, String *type_name) {
\tif (!procedure || !procedure->type || procedure->type->kind != PROCEDURE_GENERIC) return false;
\tif (array_size(procedure->type->params) != 1 || array_size(procedure->type->results) != 1) return false;
\tconst Field *param = procedure->type->params[0];
\tconst Field *result = procedure->type->results[0];
\tif (!param->name || !param->type || param->type->kind != TYPE_POLY || !result->type) return false;
\tconst PolyType *poly = RCAST(const PolyType *, param->type);
\tString param_name = STRING_NIL;
\tString result_name = STRING_NIL;
\tif (!type_identifier_name(poly->type, &param_name)) return false;
\tif (!type_identifier_name(result->type, &result_name)) return false;
\tif (!string_compare(param_name, result_name)) return false;
\t*type_name = param_name;
\treturn true;
}

static const char *generic_suffix(CType type) {
\tswitch (type) {
\tcase CTYPE_BOOL: return "bool";
\tcase CTYPE_U8: return "u8";
\tcase CTYPE_U32: return "u32";
\tcase CTYPE_UINTPTR: return "uintptr";
\tdefault: return NULL;
\t}
}

static Bool generic_type_matches(const C99 *c, const Type *type) {
\tif (c->generic_type == CTYPE_UNKNOWN || !type) return false;
\tString name = STRING_NIL;
\tif (type->kind == TYPE_POLY) {
\t\tconst PolyType *poly = RCAST(const PolyType *, type);
\t\treturn type_identifier_name(poly->type, &name) && string_compare(name, c->generic_type_name);
\t}
\treturn type_identifier_name(type, &name) && string_compare(name, c->generic_type_name);
}

static Bool add_generic_instance(C99 *c, String name,
                                 const ProcedureExpression *procedure, CType type) {
\tif (!generic_suffix(type)) return unsupported(c, "generic concrete type");
\tfor (Size i = 0; i < c->generic_instance_count; i++) {
\t\tif (c->generic_instances[i].procedure == procedure && c->generic_instances[i].type == type) return true;
\t}
\tif (c->generic_instance_count >= sizeof c->generic_instances / sizeof *c->generic_instances) {
\t\treturn unsupported(c, "generic specialization capacity");
\t}
\tc->generic_instances[c->generic_instance_count].name = name;
\tc->generic_instances[c->generic_instance_count].procedure = procedure;
\tc->generic_instances[c->generic_instance_count].type = type;
\tc->generic_instance_count++;
\treturn true;
}

static Bool discover_generic_expression(C99 *c, const Expression *expression);
static Bool discover_generic_statement(C99 *c, const Statement *statement);

static Bool discover_generic_tuple(C99 *c, const TupleExpression *tuple) {
\tif (!tuple) return true;
\tconst Size n = array_size(tuple->expressions);
\tfor (Size i = 0; i < n; i++) if (!discover_generic_expression(c, tuple->expressions[i])) return false;
\treturn true;
}

static Bool discover_generic_expression(C99 *c, const Expression *expression) {
\tif (!expression) return true;
\tswitch (expression->kind) {
\tcase EXPRESSION_TUPLE:
\t\treturn discover_generic_tuple(c, RCAST(const TupleExpression *, expression));
\tcase EXPRESSION_UNARY:
\t\treturn discover_generic_expression(c, RCAST(const UnaryExpression *, expression)->operand);
\tcase EXPRESSION_BINARY: {
\t\tconst BinaryExpression *e = RCAST(const BinaryExpression *, expression);
\t\treturn discover_generic_expression(c, e->lhs) && discover_generic_expression(c, e->rhs);
\t}
\tcase EXPRESSION_TERNARY: {
\t\tconst TernaryExpression *e = RCAST(const TernaryExpression *, expression);
\t\treturn discover_generic_expression(c, e->on_true) &&
\t\t       discover_generic_expression(c, e->cond) &&
\t\t       discover_generic_expression(c, e->on_false);
\t}
\tcase EXPRESSION_CAST:
\t\treturn discover_generic_expression(c, RCAST(const CastExpression *, expression)->expression);
\tcase EXPRESSION_SELECTOR: {
\t\tconst SelectorExpression *e = RCAST(const SelectorExpression *, expression);
\t\treturn !e->operand || discover_generic_expression(c, e->operand);
\t}
\tcase EXPRESSION_CALL: {
\t\tconst CallExpression *call = RCAST(const CallExpression *, expression);
\t\tif (call->operand->kind == EXPRESSION_IDENTIFIER) {
\t\t\tconst Identifier *identifier = RCAST(const IdentifierExpression *, call->operand)->identifier;
\t\t\tconst SemSymbol *symbol = sema_lookup(&c->sema, identifier->contents);
\t\t\tif (symbol && symbol->procedure && symbol->procedure->type->kind == PROCEDURE_GENERIC) {
\t\t\t\tString type_name = STRING_NIL;
\t\t\t\tif (!generic_shape(symbol->procedure, &type_name)) return unsupported(c, "generic procedure shape");
\t\t\t\tif (array_size(call->arguments) != 1) return unsupported(c, "generic argument count");
\t\t\t\tCType type = sema_infer_expression(&c->sema, call->arguments[0]->value);
\t\t\t\tif (type == CTYPE_UNKNOWN) return unsupported(c, "generic argument inference");
\t\t\t\tif (!add_generic_instance(c, identifier->contents, symbol->procedure, type)) return false;
\t\t\t}
\t\t}
\t\tif (!discover_generic_expression(c, call->operand)) return false;
\t\tconst Size n = array_size(call->arguments);
\t\tfor (Size i = 0; i < n; i++) if (!discover_generic_expression(c, call->arguments[i]->value)) return false;
\t\treturn true;
\t}
\tcase EXPRESSION_ASSERTION:
\t\treturn discover_generic_expression(c, RCAST(const AssertionExpression *, expression)->operand);
\tcase EXPRESSION_INDEX: {
\t\tconst IndexExpression *e = RCAST(const IndexExpression *, expression);
\t\treturn discover_generic_expression(c, e->operand) &&
\t\t       discover_generic_expression(c, e->lhs) &&
\t\t       (!e->rhs || discover_generic_expression(c, e->rhs));
\t}
\tcase EXPRESSION_SLICE: {
\t\tconst SliceExpression *e = RCAST(const SliceExpression *, expression);
\t\treturn discover_generic_expression(c, e->operand) &&
\t\t       (!e->lhs || discover_generic_expression(c, e->lhs)) &&
\t\t       (!e->rhs || discover_generic_expression(c, e->rhs));
\t}
\tcase EXPRESSION_COMPOUND_LITERAL: {
\t\tconst CompoundLiteralExpression *e = RCAST(const CompoundLiteralExpression *, expression);
\t\tconst Size n = array_size(e->fields);
\t\tfor (Size i = 0; i < n; i++) if (e->fields[i]->value && !discover_generic_expression(c, e->fields[i]->value)) return false;
\t\treturn true;
\t}
\tcase EXPRESSION_PROCEDURE: case EXPRESSION_TYPE: case EXPRESSION_LITERAL:
\tcase EXPRESSION_IDENTIFIER: case EXPRESSION_CONTEXT: case EXPRESSION_UNDEFINED:
\tcase EXPRESSION_PROCEDURE_GROUP:
\t\treturn true;
\t}
\treturn true;
}

static Bool discover_generic_statement(C99 *c, const Statement *statement) {
\tif (!statement) return true;
\tswitch (statement->kind) {
\tcase STATEMENT_BLOCK: {
\t\tconst BlockStatement *block = RCAST(const BlockStatement *, statement);
\t\tconst Size mark = c->sema.local_count;
\t\tconst Size n = array_size(block->statements);
\t\tfor (Size i = 0; i < n; i++) if (!discover_generic_statement(c, block->statements[i])) return false;
\t\tc->sema.local_count = mark;
\t\treturn true;
\t}
\tcase STATEMENT_EXPRESSION:
\t\treturn discover_generic_expression(c, RCAST(const ExpressionStatement *, statement)->expression);
\tcase STATEMENT_ASSIGNMENT: {
\t\tconst AssignmentStatement *s = RCAST(const AssignmentStatement *, statement);
\t\treturn discover_generic_tuple(c, s->lhs) && discover_generic_tuple(c, s->rhs);
\t}
\tcase STATEMENT_DECLARATION: {
\t\tconst DeclarationStatement *s = RCAST(const DeclarationStatement *, statement);
\t\tif (s->values && !discover_generic_tuple(c, s->values)) return false;
\t\tif (s->values && array_size(s->names) == 1 && array_size(s->values->expressions) == 1) {
\t\t\tCType type = s->type ? sema_type_from_ast(s->type)
\t\t\t                    : sema_infer_expression(&c->sema, s->values->expressions[0]);
\t\t\tif (type != CTYPE_UNKNOWN && !sema_add_local(&c->sema, s->names[0]->contents, type)) return false;
\t\t}
\t\treturn true;
\t}
\tcase STATEMENT_IF: {
\t\tconst IfStatement *s = RCAST(const IfStatement *, statement);
\t\treturn (!s->init || discover_generic_statement(c, s->init)) &&
\t\t       discover_generic_expression(c, s->cond) &&
\t\t       discover_generic_statement(c, RCAST(const Statement *, s->body)) &&
\t\t       (!s->elif || discover_generic_statement(c, RCAST(const Statement *, s->elif)));
\t}
\tcase STATEMENT_WHEN: {
\t\tconst WhenStatement *s = RCAST(const WhenStatement *, statement);
\t\treturn discover_generic_expression(c, s->cond) &&
\t\t       discover_generic_statement(c, RCAST(const Statement *, s->body)) &&
\t\t       (!s->elif || discover_generic_statement(c, RCAST(const Statement *, s->elif)));
\t}
\tcase STATEMENT_RETURN:
\t\treturn discover_generic_tuple(c, RCAST(const ReturnStatement *, statement)->result);
\tcase STATEMENT_FOR: {
\t\tconst ForStatement *s = RCAST(const ForStatement *, statement);
\t\treturn (!s->init || discover_generic_statement(c, s->init)) &&
\t\t       (!s->cond || discover_generic_expression(c, s->cond)) &&
\t\t       discover_generic_statement(c, RCAST(const Statement *, s->body)) &&
\t\t       (!s->post || discover_generic_statement(c, s->post));
\t}
\tcase STATEMENT_SWITCH: {
\t\tconst SwitchStatement *s = RCAST(const SwitchStatement *, statement);
\t\tif (s->init && !discover_generic_statement(c, s->init)) return false;
\t\tif (s->cond && !discover_generic_expression(c, s->cond)) return false;
\t\tconst Size n = array_size(s->clauses);
\t\tfor (Size i = 0; i < n; i++) {
\t\t\tconst CaseClause *clause = s->clauses[i];
\t\t\tif (clause->expressions && !discover_generic_tuple(c, clause->expressions)) return false;
\t\t\tconst Size m = array_size(clause->statements);
\t\t\tfor (Size j = 0; j < m; j++) if (!discover_generic_statement(c, clause->statements[j])) return false;
\t\t}
\t\treturn true;
\t}
\tcase STATEMENT_DEFER:
\t\treturn discover_generic_statement(c, RCAST(const DeferStatement *, statement)->statement);
\tcase STATEMENT_USING:
\t\treturn discover_generic_tuple(c, RCAST(const UsingStatement *, statement)->list);
\tcase STATEMENT_EMPTY: case STATEMENT_IMPORT: case STATEMENT_BRANCH:
\tcase STATEMENT_FOREIGN_BLOCK: case STATEMENT_FOREIGN_IMPORT: case STATEMENT_PACKAGE:
\t\treturn true;
\t}
\treturn true;
}

static Bool discover_generic_instances(C99 *c, BuildContext *build) {
\tconst Size n_work = array_size(build->work);
\tfor (Size w = 0; w < n_work; w++) {
\t\tBuildWork *work = build->work[w];
\t\tTree *tree = work->tree;
\t\tc->current_package = work->package;
\t\tc->current_tree = tree;
\t\tc->current_package_name = tree_package_name(tree);
\t\tconst Size n = array_size(tree->statements);
\t\tfor (Size i = 0; i < n; i++) {
\t\t\tconst Statement *statement = tree->statements[i];
\t\t\tif (statement->kind != STATEMENT_DECLARATION) continue;
\t\t\tconst DeclarationStatement *declaration = RCAST(const DeclarationStatement *, statement);
\t\t\tif (!declaration->values || array_size(declaration->values->expressions) != 1) continue;
\t\t\tconst Expression *value = declaration->values->expressions[0];
\t\t\tif (value->kind != EXPRESSION_PROCEDURE) continue;
\t\t\tconst ProcedureExpression *procedure = RCAST(const ProcedureExpression *, value);
\t\t\tif (procedure->type->kind == PROCEDURE_GENERIC) continue;
\t\t\tsema_begin_procedure(&c->sema, procedure);
\t\t\tif (!discover_generic_statement(c, RCAST(const Statement *, procedure->body))) return false;
\t\t}
\t}
\tc->sema.local_count = 0;
\treturn true;
}

static Bool emit_ast_type(C99 *c, const Type *type) {''',
)

replace_once(
    "specialized AST type",
    '''static Bool emit_ast_type(C99 *c, const Type *type) {
\tif (!type) return unsupported(c, "missing type");

\tCType primitive = sema_type_from_ast(type);''',
    '''static Bool emit_ast_type(C99 *c, const Type *type) {
\tif (!type) return unsupported(c, "missing type");
\tif (generic_type_matches(c, type)) {
\t\tconst char *name = sema_c_type_name(c->generic_type);
\t\tif (!name) return unsupported(c, "generic C type");
\t\tfputs(name, c->out);
\t\treturn true;
\t}

\tCType primitive = sema_type_from_ast(type);''',
)

replace_once(
    "generic call lowering",
    '''static Bool emit_call(C99 *c, const CallExpression *call) {
\tif (call->operand->kind == EXPRESSION_IDENTIFIER) {''',
    '''static Bool emit_call(C99 *c, const CallExpression *call) {
\tif (call->operand->kind == EXPRESSION_IDENTIFIER) {
\t\tconst Identifier *identifier = RCAST(const IdentifierExpression *, call->operand)->identifier;
\t\tconst SemSymbol *symbol = sema_lookup(&c->sema, identifier->contents);
\t\tif (symbol && symbol->procedure && symbol->procedure->type->kind == PROCEDURE_GENERIC) {
\t\t\tString type_name = STRING_NIL;
\t\t\tif (!generic_shape(symbol->procedure, &type_name)) return unsupported(c, "generic procedure shape");
\t\t\tif (array_size(call->arguments) != 1) return unsupported(c, "generic argument count");
\t\t\tCType type = sema_infer_expression(&c->sema, call->arguments[0]->value);
\t\t\tconst char *suffix = generic_suffix(type);
\t\t\tif (!suffix) return unsupported(c, "generic call concrete type");
\t\t\tfprintf(c->out, "%.*s__%s(", SFMT(identifier->contents), suffix);
\t\t\tif (!emit_expression(c, call->arguments[0]->value)) return false;
\t\t\tfputc(')', c->out);
\t\t\treturn true;
\t\t}
\t}

\tif (call->operand->kind == EXPRESSION_IDENTIFIER) {''',
)

replace_once(
    "generic-aware return capture",
    '''\t\tCType result = sema_procedure_result(c->current_procedure);
\t\tconst char *result_name = sema_c_type_name(result);
\t\tif (!result_name) return unsupported(c, "return capture type");''',
    '''\t\tCType result = sema_procedure_result(c->current_procedure);
\t\tif (result == CTYPE_UNKNOWN && c->generic_type != CTYPE_UNKNOWN) result = c->generic_type;
\t\tconst char *result_name = sema_c_type_name(result);
\t\tif (!result_name) return unsupported(c, "return capture type");''',
)

replace_once(
    "parameter AST type emission",
    '''\t\tconst Field *field = procedure->type->params[i];
\t\tCType type = sema_type_from_ast(field->type);
\t\tconst char *type_name = sema_c_type_name(type);
\t\tif (!type_name || !field->name) return unsupported(c, "procedure parameter type");
\t\tif (i) fputs(", ", c->out);
\t\tfprintf(c->out, "%s %.*s", type_name, SFMT(field->name->contents));''',
    '''\t\tconst Field *field = procedure->type->params[i];
\t\tif (!field->name) return unsupported(c, "procedure parameter type");
\t\tif (i) fputs(", ", c->out);
\t\tif (!emit_ast_type(c, field->type)) return false;
\t\tfprintf(c->out, " %.*s", SFMT(field->name->contents));''',
)

replace_once(
    "generic instance emitter",
    '''static Bool for_each_declaration(C99 *c, BuildContext *build, int phase) {''',
    '''static Bool emit_generic_instances(C99 *c, int phase) {
\tfor (Size i = 0; i < c->generic_instance_count; i++) {
\t\tString generic_name = STRING_NIL;
\t\tconst ProcedureExpression *procedure = c->generic_instances[i].procedure;
\t\tif (!generic_shape(procedure, &generic_name)) return unsupported(c, "generic procedure shape");
\t\tconst char *type_name = sema_c_type_name(c->generic_instances[i].type);
\t\tconst char *suffix = generic_suffix(c->generic_instances[i].type);
\t\tif (!type_name || !suffix) return unsupported(c, "generic specialization type");
\t\tconst Field *param = procedure->type->params[0];
\t\tif (!param->name) return unsupported(c, "generic parameter name");

\t\tif (phase == 1) {
\t\t\tfprintf(c->out, "static %s %.*s__%s(%s %.*s);\\n",
\t\t\t        type_name, SFMT(c->generic_instances[i].name), suffix,
\t\t\t        type_name, SFMT(param->name->contents));
\t\t\tcontinue;
\t\t}

\t\tString saved_generic_name = c->generic_type_name;
\t\tCType saved_generic_type = c->generic_type;
\t\tString saved_proc_name = c->current_proc_name;
\t\tconst ProcedureExpression *saved_procedure = c->current_procedure;
\t\tc->generic_type_name = generic_name;
\t\tc->generic_type = c->generic_instances[i].type;
\t\tc->current_proc_name = c->generic_instances[i].name;
\t\tc->current_procedure = procedure;
\t\tsema_begin_procedure(&c->sema, procedure);
\t\tif (!sema_add_local(&c->sema, param->name->contents, c->generic_type)) return unsupported(c, "generic local capacity");

\t\tfprintf(c->out, "static %s %.*s__%s(%s %.*s) ",
\t\t        type_name, SFMT(c->generic_instances[i].name), suffix,
\t\t        type_name, SFMT(param->name->contents));
\t\tBool ok = emit_block(c, procedure->body);
\t\tc->generic_type_name = saved_generic_name;
\t\tc->generic_type = saved_generic_type;
\t\tc->current_proc_name = saved_proc_name;
\t\tc->current_procedure = saved_procedure;
\t\tif (!ok) return false;
\t\tfputc('\\n', c->out);
\t}
\treturn true;
}

static Bool for_each_declaration(C99 *c, BuildContext *build, int phase) {''',
)

replace_once(
    "skip generic templates",
    '''\t\t\tif (value->kind == EXPRESSION_PROCEDURE) {
\t\t\t\tconst ProcedureExpression *procedure = RCAST(const ProcedureExpression *, value);
\t\t\t\tif (phase == 0 && !emit_multi_return_type(c, name, procedure)) return false;''',
    '''\t\t\tif (value->kind == EXPRESSION_PROCEDURE) {
\t\t\t\tconst ProcedureExpression *procedure = RCAST(const ProcedureExpression *, value);
\t\t\t\tif (procedure->type->kind == PROCEDURE_GENERIC) continue;
\t\t\t\tif (phase == 0 && !emit_multi_return_type(c, name, procedure)) return false;''',
)

replace_once(
    "generic state init",
    '''\tc.current_package_name = STRING_NIL;
\tsema_init(&c.sema);
\tif (!sema_collect_globals(&c.sema, build)) return false;''',
    '''\tc.current_package_name = STRING_NIL;
\tc.generic_instance_count = 0;
\tc.generic_type_name = STRING_NIL;
\tc.generic_type = CTYPE_UNKNOWN;
\tsema_init(&c.sema);
\tif (!sema_collect_globals(&c.sema, build)) return false;
\tif (!discover_generic_instances(&c, build)) return false;''',
)

replace_once(
    "generic phases",
    '''\tif (!for_each_declaration(&c, build, 1)) return false;
\tfputc('\\n', out);
\tif (!for_each_declaration(&c, build, 2)) return false;
\treturn c.ok;''',
    '''\tif (!for_each_declaration(&c, build, 1)) return false;
\tif (!emit_generic_instances(&c, 1)) return false;
\tfputc('\\n', out);
\tif (!for_each_declaration(&c, build, 2)) return false;
\tif (!emit_generic_instances(&c, 2)) return false;
\treturn c.ok;''',
)

path.write_text(src)
print("augment_generic: single-parameter scalar monomorphization applied")
