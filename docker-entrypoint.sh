#!/bin/sh
set -e
if [ -n "$DB_HOST" ]; then
    echo "Esperando la base de datos..."
    until python -c "import MySQLdb, os; MySQLdb.connect(host=os.environ['DB_HOST'], user=os.environ['DB_USER'], passwd=os.environ['DB_PASSWORD'], db=os.environ['DB_NAME'])" 2>/dev/null; do
        sleep 2
    done
fi
python manage.py migrate --noinput
python manage.py collectstatic --noinput -v 0
if [ "$APP_DEMO" = "true" ]; then
    python manage.py datos_demo
fi
exec "$@"
