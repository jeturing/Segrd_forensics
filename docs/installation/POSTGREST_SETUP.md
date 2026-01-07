# ✅ PostgREST + Postgres (modo panel de mantenimiento)

## Requisitos
- Docker y docker-compose activos
- Puerto 5433 libre (Postgres local) y 3000 libre (PostgREST)

## Pasos rápidos
1. Levanta Postgres y PostgREST (compose v4.4.1):
   ```bash
   docker compose -f docker-compose.v4.4.1.yml up -d pg_local_db postgrest
   ```
2. Variables (ya incluidas en `config/tools.env`):
   - `DB_MODE=sqlite|postgrest`
   - `POSTGREST_URL=http://localhost:3000`
   - `POSTGRES_HOST=localhost`
   - `POSTGRES_PORT=5433`
   - `POSTGRES_DB=forensics_db`
   - `POSTGRES_USER=root`
   - `POSTGRES_PASSWORD=.`
3. Migrar SQLite → Postgres (opcional manual):
   ```bash
   python3 scripts/migrate_sqlite_to_postgres.py \
     --sqlite ./forensics.db \
     --pg "postgresql://root:.@localhost:5433/forensics_db"
   ```
4. Cambiar modo desde el Panel de Mantenimiento (`🔧 Acciones de Mantenimiento`):
   - Botón `Usar PostgREST (PG)` → guarda selección en `config/db_mode.json`
   - Botón `Usar SQLite local` para volver
   - Botón `Migrar SQLite → PG` ejecuta script de migración

## Notas
- El backend sigue usando `DATABASE_URL`; el modo guardado se expone vía API (`/api/v41/system/db-mode`) y se usa para estadísticas y acciones del panel.
- Dependencia nueva: `psycopg2-binary` en `requirements.txt`.
- El servicio PostgREST lee `forensics_db` con usuario `root` y clave `.` (punto).
