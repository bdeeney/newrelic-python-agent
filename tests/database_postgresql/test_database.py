import postgresql.driver.dbapi20

import pwd
import os

from newrelic.agent import (background_task, current_transaction,
    transient_function_wrapper)

from newrelic.common.object_wrapper import resolve_path

USER = pwd.getpwuid(os.getuid()).pw_name

DATABASE_NAME = os.environ.get('TDDIUM_DB_PG_NAME', USER)
DATABASE_USER = os.environ.get('TDDIUM_DB_PG_USER', USER)
DATABASE_PASSWORD = os.environ.get('TDDIUM_DB_PG_PASSWORD')
DATABASE_HOST = os.environ.get('TDDIUM_DB_PG_HOST', 'localhost')
DATABASE_PORT = int(os.environ.get('TDDIUM_DB_PG_PORT', '5432'))

@transient_function_wrapper('newrelic.api.database_trace',
        'DatabaseTrace.__init__')
def validate_database_trace_inputs(wrapped, instance, args, kwargs):
    def _bind_params(transaction, sql, dbapi2_module=None,
            connect_params=None, cursor_params=None, execute_params=None):
        return (transaction, sql, dbapi2_module, connect_params,
                cursor_params, execute_params)

    (transaction, sql, dbapi2_module, connect_params,
            cursor_params, execute_params) = _bind_params(*args, **kwargs)

    assert hasattr(dbapi2_module, 'connect')

    assert connect_params is None or isinstance(connect_params, tuple)

    if connect_params is not None:
        assert len(connect_params) == 2
        assert isinstance(connect_params[0], tuple)
        assert isinstance(connect_params[1], dict)

    assert cursor_params is None or isinstance(cursor_params, tuple)

    if cursor_params is not None:
        assert len(cursor_params) == 2
        assert isinstance(cursor_params[0], tuple)
        assert isinstance(cursor_params[1], dict)

    assert execute_params is None or isinstance(execute_params, tuple)

    return wrapped(*args, **kwargs)

@background_task()
@validate_database_trace_inputs
def test_execute_via_cursor():
    with postgresql.driver.dbapi20.connect(database=DATABASE_NAME,
            user=DATABASE_USER, password=DATABASE_PASSWORD,
            host=DATABASE_HOST, port=DATABASE_PORT) as connection:

        cursor = connection.cursor()

        cursor.execute("""drop table if exists database_postgresql""")

        cursor.execute("""create table database_postgresql """
                """(a integer, b real, c text)""")

        cursor.executemany("""insert into database_postgresql """
                """values (%s, %s, %s)""", [(1, 1.0, '1.0'),
                (2, 2.2, '2.2'), (3, 3.3, '3.3')])

        cursor.execute("""select * from database_postgresql""")

        for row in cursor: pass

        cursor.execute("""update database_postgresql set a=%s, b=%s, """
                """c=%s where a=%s""", (4, 4.0, '4.0', 1))

        cursor.execute("""delete from database_postgresql where a=2""")

        connection.commit()

        cursor.callproc('now', ())
        cursor.callproc('pg_sleep', (0.25,))

        connection.rollback()
        connection.commit()
