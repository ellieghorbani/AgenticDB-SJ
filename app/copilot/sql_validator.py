"""Independent SQLGlot AST validation for Day 8.

Day 7 performs template-level safety checks. Day 8 reparses the generated SQL
using the PostgreSQL dialect and independently inspects the resulting AST before
any database execution is considered.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Iterable

from sqlglot import exp, parse
from sqlglot.errors import ParseError
from sqlglot.expressions.builders import find_tables

from app.models.copilot import SchemaCatalogResponse
from app.models.sql_execution import (
    ASTValidationCheck,
    SQLValidationReport,
    SQLValidationStatus,
)
from app.models.sql_generation import (
    SQLGenerationResponse,
    SQLGenerationStatus,
    SQLParameter,
)


_FORBIDDEN_NODE_NAMES = {
    "Alter",
    "Analyze",
    "Call",
    "Command",
    "Comment",
    "Copy",
    "Create",
    "Delete",
    "Drop",
    "Execute",
    "Grant",
    "Insert",
    "Into",
    "LoadData",
    "Lock",
    "Merge",
    "Pragma",
    "Refresh",
    "Revoke",
    "Set",
    "Transaction",
    "TruncateTable",
    "Update",
    "Use",
}

_ALLOWED_FUNCTIONS = {
    "avg",
    "cast",
    "count",
    "lower",
    "max",
    "min",
    "round",
    "st_distance",
    "st_dwithin",
}

_ALLOWED_PARAMETER_TYPES = {"text", "integer", "double precision", "boolean"}
_LOCKING_PATTERN = re.compile(
    r"\bfor\s+(?:update|share|no\s+key\s+update|key\s+share)\b",
    re.IGNORECASE,
)
_COMMENT_PATTERN = re.compile(r"--|/\*|\*/")


class SQLASTValidator:
    """Validate generated SQL independently using a parsed PostgreSQL AST."""

    validator_name = "sqlglot_ast_day8"

    def __init__(self, catalog: SchemaCatalogResponse, *, max_result_rows: int = 1000):
        self.catalog = catalog
        self.max_result_rows = max_result_rows
        self._relation_lookup = {
            relation.qualified_name.lower(): relation for relation in catalog.relations
        }

    def validate(self, generation: SQLGenerationResponse) -> SQLValidationReport:
        if (
            generation.status != SQLGenerationStatus.generated
            or not generation.sql
            or not generation.sql_generated
        ):
            return SQLValidationReport(
                status=SQLValidationStatus.not_generated,
                statement_count=0,
                root_expression=None,
                checks=[
                    ASTValidationCheck(
                        name="generated_sql_present",
                        passed=False,
                        detail=(
                            "The planner/generator did not produce SQL, so execution "
                            "remains disabled."
                        ),
                    )
                ],
                warnings=list(generation.warnings),
                execution_allowed=False,
            )

        checks: list[ASTValidationCheck] = []
        sql = generation.sql.strip()
        placeholder_count = sql.count("%s")
        checks.append(
            ASTValidationCheck(
                name="placeholder_count",
                passed=placeholder_count == len(generation.parameters),
                detail=(
                    f"{placeholder_count} placeholders and "
                    f"{len(generation.parameters)} parameters were supplied."
                ),
            )
        )
        checks.append(
            ASTValidationCheck(
                name="day7_generation_checks",
                passed=(
                    bool(generation.safety_checks)
                    and all(check.passed for check in generation.safety_checks)
                ),
                detail="Every Day 7 template-level safety check must pass again.",
            )
        )
        checks.append(
            ASTValidationCheck(
                name="parameter_types",
                passed=all(
                    parameter.pg_type in _ALLOWED_PARAMETER_TYPES
                    for parameter in generation.parameters
                ),
                detail="Every bound parameter uses an approved PostgreSQL type.",
            )
        )

        if placeholder_count != len(generation.parameters):
            return self._blocked_report(
                generation,
                checks,
                warning="SQL parsing was skipped because placeholder binding was inconsistent.",
            )

        parse_sql = self._substitute_parameters_for_parsing(
            sql,
            generation.parameters,
        )
        try:
            statements = parse(parse_sql, read="postgres")
        except ParseError as exc:
            checks.append(
                ASTValidationCheck(
                    name="parse_success",
                    passed=False,
                    detail=f"SQLGlot PostgreSQL parsing failed: {exc}",
                )
            )
            return self._blocked_report(
                generation,
                checks,
                warning="The generated SQL could not be parsed as PostgreSQL.",
            )

        statements = [statement for statement in statements if statement is not None]
        checks.append(
            ASTValidationCheck(
                name="parse_success",
                passed=True,
                detail="SQLGlot parsed the generated SQL using the PostgreSQL dialect.",
            )
        )
        checks.append(
            ASTValidationCheck(
                name="single_statement",
                passed=len(statements) == 1,
                detail=f"The parser found {len(statements)} SQL statement(s).",
            )
        )
        if len(statements) != 1:
            return self._blocked_report(
                generation,
                checks,
                statement_count=len(statements),
                warning="Only one SQL statement may be executed.",
            )

        ast = statements[0]
        root_expression = type(ast).__name__
        checks.append(
            ASTValidationCheck(
                name="select_root",
                passed=isinstance(ast, exp.Select),
                detail=f"The root AST expression is {root_expression}.",
            )
        )

        forbidden_nodes = sorted(
            {
                type(node).__name__
                for node in ast.walk()
                if type(node).__name__ in _FORBIDDEN_NODE_NAMES
            }
        )
        checks.append(
            ASTValidationCheck(
                name="forbidden_ast_nodes",
                passed=not forbidden_nodes,
                detail=(
                    "No write, DDL, administrative, or execution AST nodes were found."
                    if not forbidden_nodes
                    else f"Forbidden AST nodes: {', '.join(forbidden_nodes)}"
                ),
            )
        )

        checks.append(
            ASTValidationCheck(
                name="comments_absent",
                passed=_COMMENT_PATTERN.search(sql) is None,
                detail="SQL comments are rejected to keep validation unambiguous.",
            )
        )
        checks.append(
            ASTValidationCheck(
                name="locking_clause_absent",
                passed=_LOCKING_PATTERN.search(sql) is None,
                detail="Row-locking SELECT clauses are not allowed.",
            )
        )

        tables = sorted(self._qualified_table_name(table) for table in find_tables(ast))
        unqualified_tables = sorted(table for table in tables if "." not in table)
        allowed_relations = set(self._relation_lookup)
        generated_relations = {relation.lower() for relation in generation.relations}
        actual_relations = set(tables)
        checks.append(
            ASTValidationCheck(
                name="qualified_relations",
                passed=not unqualified_tables,
                detail=(
                    "Every physical relation is schema-qualified."
                    if not unqualified_tables
                    else f"Unqualified relations: {', '.join(unqualified_tables)}"
                ),
            )
        )
        checks.append(
            ASTValidationCheck(
                name="relations_allowlisted",
                passed=actual_relations.issubset(allowed_relations),
                detail=(
                    "Every physical relation is in the curated schema allowlist."
                    if actual_relations.issubset(allowed_relations)
                    else (
                        "Unapproved relations: "
                        + ", ".join(sorted(actual_relations - allowed_relations))
                    )
                ),
            )
        )
        checks.append(
            ASTValidationCheck(
                name="relations_match_generation",
                passed=actual_relations == generated_relations,
                detail=(
                    "AST relations exactly match the relations declared by Day 7."
                    if actual_relations == generated_relations
                    else (
                        f"AST relations={sorted(actual_relations)}; "
                        f"declared={sorted(generated_relations)}."
                    )
                ),
            )
        )

        invalid_declared_columns = self._invalid_declared_columns(
            generation.source_columns
        )
        checks.append(
            ASTValidationCheck(
                name="declared_source_columns_allowlisted",
                passed=not invalid_declared_columns,
                detail=(
                    "Every Day 7 source-column declaration exists in the curated catalog."
                    if not invalid_declared_columns
                    else (
                        "Unapproved source columns: "
                        + ", ".join(invalid_declared_columns)
                    )
                ),
            )
        )

        functions = sorted(self._function_names(ast))
        unapproved_functions = sorted(set(functions) - _ALLOWED_FUNCTIONS)
        checks.append(
            ASTValidationCheck(
                name="functions_allowlisted",
                passed=not unapproved_functions,
                detail=(
                    "Every SQL function is in the Day 8 function allowlist."
                    if not unapproved_functions
                    else f"Unapproved functions: {', '.join(unapproved_functions)}"
                ),
            )
        )

        wildcards = list(ast.find_all(exp.Star))
        checks.append(
            ASTValidationCheck(
                name="wildcards_absent",
                passed=not wildcards,
                detail="Wildcard projections are not allowed in executable copilot SQL.",
            )
        )

        outer_limit = self._outer_limit(ast)
        checks.append(
            ASTValidationCheck(
                name="bounded_result",
                passed=outer_limit is not None,
                detail=(
                    f"The outer query limit is {outer_limit}."
                    if outer_limit is not None
                    else "The outer query has no explicit numeric LIMIT."
                ),
            )
        )
        checks.append(
            ASTValidationCheck(
                name="row_limit_policy",
                passed=(
                    outer_limit is not None
                    and 0 <= outer_limit <= self.max_result_rows
                ),
                detail=(
                    f"The maximum permitted row limit is {self.max_result_rows}."
                ),
            )
        )

        fingerprint = self._fingerprint(generation)
        passed = all(check.passed for check in checks)
        return SQLValidationReport(
            status=(
                SQLValidationStatus.valid
                if passed
                else SQLValidationStatus.blocked
            ),
            statement_count=1,
            root_expression=root_expression,
            relations=sorted(actual_relations),
            functions=functions,
            outer_limit=outer_limit,
            query_fingerprint=fingerprint,
            checks=checks,
            warnings=([] if passed else ["One or more independent AST checks failed."]),
            execution_allowed=passed,
        )

    def _blocked_report(
        self,
        generation: SQLGenerationResponse,
        checks: list[ASTValidationCheck],
        *,
        statement_count: int = 0,
        warning: str,
    ) -> SQLValidationReport:
        return SQLValidationReport(
            status=SQLValidationStatus.blocked,
            statement_count=statement_count,
            root_expression=None,
            checks=checks,
            warnings=[warning, *generation.warnings],
            execution_allowed=False,
        )

    @staticmethod
    def _substitute_parameters_for_parsing(
        sql: str,
        parameters: Iterable[SQLParameter],
    ) -> str:
        parts = sql.split("%s")
        parameter_list = list(parameters)
        if len(parts) - 1 != len(parameter_list):
            raise ValueError("placeholder count does not match parameter count")

        output = [parts[0]]
        for index, parameter in enumerate(parameter_list):
            output.append(SQLASTValidator._parameter_literal(parameter))
            output.append(parts[index + 1])
        return "".join(output)

    @staticmethod
    def _parameter_literal(parameter: SQLParameter) -> str:
        if parameter.pg_type == "text":
            value = str(parameter.value).replace("'", "''")
            return f"'{value}'"
        if parameter.pg_type == "boolean":
            return "TRUE" if bool(parameter.value) else "FALSE"
        if parameter.pg_type == "integer":
            return str(int(parameter.value))
        if parameter.pg_type == "double precision":
            return repr(float(parameter.value))
        raise ValueError(f"unsupported parameter type: {parameter.pg_type}")

    @staticmethod
    def _qualified_table_name(table: exp.Table) -> str:
        schema_name = str(table.db or "").lower()
        relation_name = str(table.name or "").lower()
        return (
            f"{schema_name}.{relation_name}"
            if schema_name
            else relation_name
        )

    def _invalid_declared_columns(self, columns: Iterable[str]) -> list[str]:
        invalid: list[str] = []
        for reference in columns:
            try:
                relation_name, column_name = reference.lower().rsplit(".", maxsplit=1)
            except ValueError:
                invalid.append(reference)
                continue
            relation = self._relation_lookup.get(relation_name)
            if relation is None:
                invalid.append(reference)
                continue
            allowed_columns = {column.name.lower() for column in relation.columns}
            if column_name not in allowed_columns:
                invalid.append(reference)
        return sorted(invalid)

    @staticmethod
    def _function_names(ast: exp.Expression) -> set[str]:
        names: set[str] = set()

        for function in ast.find_all(exp.Func):
            # SQLGlot includes some logical operators in the Func hierarchy.
            # AND, OR, and NOT are AST operators rather than callable SQL
            # functions, so they must not be evaluated against the function
            # allowlist.
            if isinstance(function, (exp.And, exp.Or, exp.Not)):
                continue

            sql_name_method = getattr(function, "sql_name", None)
            sql_name = sql_name_method() if callable(sql_name_method) else ""

            if sql_name and str(sql_name).upper() != "ANONYMOUS":
                names.add(str(sql_name).lower())
                continue

            name = getattr(function, "name", None)
            if name:
                names.add(str(name).lower())
            else:
                names.add(type(function).__name__.lower())

        return names

    @staticmethod
    def _outer_limit(ast: exp.Expression) -> int | None:
        limit = ast.args.get("limit")
        if limit is None:
            return None
        expression = getattr(limit, "expression", None)
        if expression is None:
            expression = limit.args.get("expression")
        value = getattr(expression, "this", None)
        try:
            return int(str(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _fingerprint(generation: SQLGenerationResponse) -> str:
        payload = {
            "sql": re.sub(r"\s+", " ", generation.sql or "").strip(),
            "parameters": [
                {
                    "position": parameter.position,
                    "name": parameter.name,
                    "value": parameter.value,
                    "pg_type": parameter.pg_type,
                }
                for parameter in generation.parameters
            ],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
