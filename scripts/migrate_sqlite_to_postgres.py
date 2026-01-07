#!/usr/bin/env python3
"""
Migra datos desde la base de datos SQLite local a Postgres (PostgREST usable sobre esta DB).

Uso:
  python3 scripts/migrate_sqlite_to_postgres.py --sqlite ./forensics.db --pg "postgresql://root:.@localhost:5433/forensics_db"

Nota: Ejecutar con la base Postgres y PostgREST corriendo (ver docker-compose.v4.4.1.yml)
"""
import argparse
import sqlite3
import sys
from sqlalchemy import create_engine, text


def dump_sqlite(sqlite_path: str) -> str:
    # Extrae esquema y datos como SQL
    con = sqlite3.connect(sqlite_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    # Obtener esquema
    cur.execute("SELECT sql FROM sqlite_master WHERE type IN ('table','index','trigger','view') AND sql NOT NULL;")
    schema_rows = [r[0] for r in cur.fetchall()]
    # Obtener tablas
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [r[0] for r in cur.fetchall()]

    inserts = []
    for t in tables:
        cur.execute(f"SELECT * FROM {t};")
        cols = [d[0] for d in cur.description]
        for row in cur.fetchall():
            values = []
            for c in cols:
                v = row[c]
                if v is None:
                    values.append('NULL')
                else:
                    values.append("'" + str(v).replace("'","''") + "'")
            inserts.append(f"INSERT INTO {t} ({', '.join(cols)}) VALUES ({', '.join(values)});")

    con.close()
    return "\n".join(schema_rows + inserts)


def migrate(sqlite_path: str, pg_uri: str):
    print(f"Conectando a Postgres en {pg_uri}")
    engine = create_engine(pg_uri)
    sql_dump = dump_sqlite(sqlite_path)

    # Ejecutar en transacción
    with engine.begin() as conn:
        # Postgres no acepta algunas sintaxis de sqlite (AUTOINCREMENT, etc.).
        # Intentaremos ejecutar el SQL simple; si falla, el usuario deberá preparar el schema manualmente.
        try:
            conn.execute(text(sql_dump))
        except Exception as e:
            print("Error aplicando dump SQL automático:", e)
            print("Sugerencia: crear esquema manualmente en Postgres y reintentar solo con datos.")
            sys.exit(1)

    print("Migración completada.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sqlite', required=True, help='Ruta al archivo SQLite')
    parser.add_argument('--pg', required=True, help='URI de Postgres (sqlalchemy)')
    args = parser.parse_args()
    migrate(args.sqlite, args.pg)


if __name__ == '__main__':
    main()
