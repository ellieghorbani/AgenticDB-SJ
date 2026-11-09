#!/usr/bin/env python3
"""Build pgvector embeddings from real AgenticDB-SJ source records."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row

from app.core.config import get_settings
from app.copilot.embeddings import SentenceTransformerEmbeddingProvider


@dataclass(frozen=True, slots=True)
class SourceDocument:
    entity_type: str
    entity_id: str
    title: str
    source_text: str
    metadata: dict[str, Any]
    source_id: int | None

    @property
    def source_text_hash(self) -> str:
        return hashlib.sha256(self.source_text.encode("utf-8")).hexdigest()


def _parts(*values: str | None) -> str:
    return " ".join(value.strip() for value in values if value and value.strip())


def fetch_documents(connection: psycopg.Connection) -> list[SourceDocument]:
    documents: list[SourceDocument] = []

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                facility_id,
                park_name,
                address,
                park_type_code,
                park_class_code,
                subclass_code,
                current_status,
                all_acres,
                owner,
                name_alias,
                planning_area,
                specific_plan_area,
                source_id
            FROM core.parks
            ORDER BY facility_id
            """
        )
        for row in cursor.fetchall():
            source_text = _parts(
                f"Park feature name: {row['park_name']}.",
                f"Address: {row['address']}." if row["address"] else None,
                f"Park type code: {row['park_type_code']}.",
                f"Park class code: {row['park_class_code']}.",
                (
                    f"Subclass code: {row['subclass_code']}."
                    if row["subclass_code"]
                    else None
                ),
                f"Current status: {row['current_status']}.",
                f"Planning area: {row['planning_area']}."
                if row["planning_area"]
                else None,
                f"Specific plan area: {row['specific_plan_area']}."
                if row["specific_plan_area"]
                else None,
                f"Owner: {row['owner']}." if row["owner"] else None,
                f"Alias: {row['name_alias']}." if row["name_alias"] else None,
                f"Area: {row['all_acres']} acres."
                if row["all_acres"] is not None
                else None,
            )
            documents.append(
                SourceDocument(
                    entity_type="park",
                    entity_id=str(row["facility_id"]),
                    title=str(row["park_name"]),
                    source_text=source_text,
                    metadata={
                        "current_status": row["current_status"],
                        "park_type_code": row["park_type_code"],
                        "park_class_code": row["park_class_code"],
                        "subclass_code": row["subclass_code"],
                        "planning_area": row["planning_area"],
                        "address": row["address"],
                    },
                    source_id=int(row["source_id"]),
                )
            )

        cursor.execute(
            """
            SELECT
                s.cds_code,
                s.school_name,
                s.district_name,
                s.city,
                s.education_level_code,
                s.education_level_name,
                s.grades_offered,
                s.grades_served,
                s.education_option_name,
                sn.neighborhood_id,
                sn.neighborhood_name,
                s.source_id
            FROM app.san_jose_active_schools_spatial AS sn
            JOIN core.schools AS s
              ON s.cds_code = sn.cds_code
            ORDER BY s.cds_code
            """
        )
        for row in cursor.fetchall():
            source_text = _parts(
                f"School name: {row['school_name']}.",
                f"District: {row['district_name']}.",
                f"Education level: {row['education_level_name']}."
                if row["education_level_name"]
                else None,
                f"Education level code: {row['education_level_code']}."
                if row["education_level_code"]
                else None,
                f"Grades offered: {row['grades_offered']}."
                if row["grades_offered"]
                else None,
                f"Grades served: {row['grades_served']}."
                if row["grades_served"]
                else None,
                f"Education option: {row['education_option_name']}."
                if row["education_option_name"]
                else None,
                f"Neighborhood: {row['neighborhood_name']}.",
                f"City: {row['city']}." if row["city"] else None,
            )
            documents.append(
                SourceDocument(
                    entity_type="school",
                    entity_id=str(row["cds_code"]).strip(),
                    title=str(row["school_name"]),
                    source_text=source_text,
                    metadata={
                        "district_name": row["district_name"],
                        "education_level_code": row["education_level_code"],
                        "education_level_name": row["education_level_name"],
                        "grades_served": row["grades_served"],
                        "neighborhood_id": row["neighborhood_id"],
                        "neighborhood_name": row["neighborhood_name"],
                        "city": row["city"],
                    },
                    source_id=int(row["source_id"]),
                )
            )

        cursor.execute(
            """
            SELECT
                enterprise_id,
                neighborhood_name,
                source_method,
                notes,
                geom_repaired,
                source_id
            FROM core.neighborhoods
            ORDER BY enterprise_id
            """
        )
        for row in cursor.fetchall():
            source_text = _parts(
                f"San Jose neighborhood name: {row['neighborhood_name']}.",
                f"Source method: {row['source_method']}."
                if row["source_method"]
                else None,
                f"Source notes: {row['notes']}." if row["notes"] else None,
                (
                    "The source boundary geometry was deterministically repaired."
                    if row["geom_repaired"]
                    else "The source boundary geometry did not require repair."
                ),
            )
            documents.append(
                SourceDocument(
                    entity_type="neighborhood",
                    entity_id=str(row["enterprise_id"]),
                    title=str(row["neighborhood_name"]),
                    source_text=source_text,
                    metadata={
                        "neighborhood_name": row["neighborhood_name"],
                        "geom_repaired": bool(row["geom_repaired"]),
                    },
                    source_id=int(row["source_id"]),
                )
            )

    return documents


def main() -> None:
    settings = get_settings()
    connection = psycopg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        dbname=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password.get_secret_value(),
        connect_timeout=settings.database_connect_timeout_seconds,
        application_name="agenticdb_sj_day10_embeddings",
        row_factory=dict_row,
        autocommit=True,
    )
    register_vector(connection)

    run_id: int | None = None
    try:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO semantic.embedding_runs (
                        embedding_model,
                        embedding_dimensions,
                        status
                    )
                    VALUES (%s, %s, 'running')
                    RETURNING embedding_run_id
                    """,
                    (
                        settings.embedding_model_name,
                        settings.embedding_dimensions,
                    ),
                )
                row = cursor.fetchone()
                assert row is not None
                run_id = int(row["embedding_run_id"])

        documents = fetch_documents(connection)
        expected_counts = {
            "park": 611,
            "school": 220,
            "neighborhood": 297,
        }
        actual_counts = {
            entity_type: sum(
                document.entity_type == entity_type for document in documents
            )
            for entity_type in expected_counts
        }
        if actual_counts != expected_counts:
            raise RuntimeError(
                f"source snapshot mismatch: expected {expected_counts}, "
                f"received {actual_counts}"
            )

        provider = SentenceTransformerEmbeddingProvider(
            settings.embedding_model_name,
            settings.embedding_dimensions,
            device=settings.embedding_device,
            batch_size=settings.embedding_batch_size,
        )
        print(
            f"Encoding {len(documents)} real source-derived documents with "
            f"{settings.embedding_model_name}..."
        )
        vectors = provider.encode_documents(
            [document.source_text for document in documents]
        )

        rows = [
            (
                document.entity_type,
                document.entity_id,
                document.title,
                document.source_text,
                document.source_text_hash,
                json.dumps(document.metadata, sort_keys=True),
                settings.embedding_model_name,
                settings.embedding_dimensions,
                vectors[index],
                document.source_id,
            )
            for index, document in enumerate(documents)
        ]

        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM semantic.entity_documents WHERE embedding_model = %s",
                    (settings.embedding_model_name,),
                )
                cursor.executemany(
                    """
                    INSERT INTO semantic.entity_documents (
                        entity_type,
                        entity_id,
                        title,
                        source_text,
                        source_text_hash,
                        metadata,
                        embedding_model,
                        embedding_dimensions,
                        embedding,
                        source_id
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s
                    )
                    ON CONFLICT (entity_type, entity_id, embedding_model)
                    DO UPDATE SET
                        title = EXCLUDED.title,
                        source_text = EXCLUDED.source_text,
                        source_text_hash = EXCLUDED.source_text_hash,
                        metadata = EXCLUDED.metadata,
                        embedding_dimensions = EXCLUDED.embedding_dimensions,
                        embedding = EXCLUDED.embedding,
                        source_id = EXCLUDED.source_id,
                        updated_at = now()
                    """,
                    rows,
                )
                cursor.execute(
                    """
                    UPDATE semantic.embedding_runs
                    SET completed_at = now(),
                        source_document_count = %s,
                        embedded_document_count = %s,
                        status = 'succeeded'
                    WHERE embedding_run_id = %s
                    """,
                    (len(documents), len(rows), run_id),
                )

        print("Day 10 embeddings loaded successfully")
        print(f"  parks: {actual_counts['park']}")
        print(f"  schools: {actual_counts['school']}")
        print(f"  neighborhoods: {actual_counts['neighborhood']}")
        print(f"  total: {len(documents)}")
    except Exception as exc:
        if run_id is not None:
            try:
                with connection.transaction():
                    connection.execute(
                        """
                        UPDATE semantic.embedding_runs
                        SET completed_at = now(),
                            status = 'failed',
                            error_message = %s
                        WHERE embedding_run_id = %s
                        """,
                        (str(exc), run_id),
                    )
            except Exception:
                pass
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
