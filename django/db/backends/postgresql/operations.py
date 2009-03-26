import re

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.backends import BaseDatabaseOperations

server_version_re = re.compile(r'PostgreSQL (\d{1,2})\.(\d{1,2})\.?(\d{1,2})?')

# This DatabaseOperations class lives in here instead of base.py because it's
# used by both the 'postgresql' and 'postgresql_psycopg2' backends.

class DatabaseOperations(BaseDatabaseOperations):
    def __init__(self):
        self._postgres_version = None

    def _get_postgres_version(self):
        if self._postgres_version is None:
            from django.db import connection
            cursor = connection.cursor()
            cursor.execute("SELECT version()")
            version_string = cursor.fetchone()[0]
            m = server_version_re.match(version_string)
            if not m:
                raise Exception('Unable to determine PostgreSQL version from version() function string: %r' % version_string)
            self._postgres_version = [int(val) for val in m.groups() if val]
        return self._postgres_version
    postgres_version = property(_get_postgres_version)

    def date_extract_sql(self, lookup_type, field_name):
        # http://www.postgresql.org/docs/8.0/static/functions-datetime.html#FUNCTIONS-DATETIME-EXTRACT
        if lookup_type == 'week_day':
            # Using EXTRACT(), PostgreSQL days are indexed as Sunday=0, Saturday=6.
            # If we instead us TO_CHAR, they're indexed with Sunday=1, Saturday=7
            return "TO_CHAR(%s, 'D')" % field_name
        else:
            return "EXTRACT('%s' FROM %s)" % (lookup_type, field_name)

    def date_trunc_sql(self, lookup_type, field_name):
        # http://www.postgresql.org/docs/8.0/static/functions-datetime.html#FUNCTIONS-DATETIME-TRUNC
        return "DATE_TRUNC('%s', %s)" % (lookup_type, field_name)

    def deferrable_sql(self):
        return " DEFERRABLE INITIALLY DEFERRED"

    def lookup_cast(self, lookup_type):
        lookup = '%s'

        # Cast text lookups to text to allow things like filter(x__contains=4)
        if lookup_type in ('iexact', 'contains', 'icontains', 'startswith',
                           'istartswith', 'endswith', 'iendswith'):
            lookup = "%s::text"

        # Use UPPER(x) for case-insensitive lookups; it's faster.
        if lookup_type in ('iexact', 'icontains', 'istartswith', 'iendswith'):
            lookup = 'UPPER(%s)' % lookup

        return lookup

    def field_cast_sql(self, db_type):
        if db_type == 'inet':
            return 'HOST(%s)'
        return '%s'

    def last_insert_id(self, cursor, table_name, pk_name):
        cursor.execute("SELECT CURRVAL('\"%s_%s_seq\"')" % (table_name, pk_name))
        return cursor.fetchone()[0]

    def no_limit_value(self):
        return None

    def quote_name(self, name):
        if name.startswith('"') and name.endswith('"'):
            return name # Quoting once is enough.
        return '"%s"' % name

    def sql_flush(self, style, tables, sequences):
        if tables:
            if self.postgres_version[0] >= 8 and self.postgres_version[1] >= 1:
                # Postgres 8.1+ can do 'TRUNCATE x, y, z...;'. In fact, it *has to*
                # in order to be able to truncate tables referenced by a foreign
                # key in any other table. The result is a single SQL TRUNCATE
                # statement.
                sql = ['%s %s;' % \
                    (style.SQL_KEYWORD('TRUNCATE'),
                     style.SQL_FIELD(', '.join([self.quote_name(table) for table in tables]))
                )]
            else:
                # Older versions of Postgres can't do TRUNCATE in a single call, so
                # they must use a simple delete.
                sql = ['%s %s %s;' % \
                        (style.SQL_KEYWORD('DELETE'),
                         style.SQL_KEYWORD('FROM'),
                         style.SQL_FIELD(self.quote_name(table))
                         ) for table in tables]

            # 'ALTER SEQUENCE sequence_name RESTART WITH 1;'... style SQL statements
            # to reset sequence indices
            for sequence_info in sequences:
                table_name = sequence_info['table']
                column_name = sequence_info['column']
                if column_name and len(column_name) > 0:
                    sequence_name = '%s_%s_seq' % (table_name, column_name)
                else:
                    sequence_name = '%s_id_seq' % table_name
                sql.append("%s setval('%s', 1, false);" % \
                    (style.SQL_KEYWORD('SELECT'),
                    style.SQL_FIELD(self.quote_name(sequence_name)))
                )
            return sql
        else:
            return []

    def sequence_reset_sql(self, style, model_list):
        from django.db import models
        output = []
        qn = self.quote_name
        for model in model_list:
            # Use `coalesce` to set the sequence for each model to the max pk value if there are records,
            # or 1 if there are none. Set the `is_called` property (the third argument to `setval`) to true
            # if there are records (as the max pk value is already in use), otherwise set it to false.
            for f in model._meta.local_fields:
                if isinstance(f, models.AutoField):
                    output.append("%s setval('%s', coalesce(max(%s), 1), max(%s) %s null) %s %s;" % \
                        (style.SQL_KEYWORD('SELECT'),
                        style.SQL_FIELD(qn('%s_%s_seq' % (model._meta.db_table, f.column))),
                        style.SQL_FIELD(qn(f.column)),
                        style.SQL_FIELD(qn(f.column)),
                        style.SQL_KEYWORD('IS NOT'),
                        style.SQL_KEYWORD('FROM'),
                        style.SQL_TABLE(qn(model._meta.db_table))))
                    break # Only one AutoField is allowed per model, so don't bother continuing.
            for f in model._meta.many_to_many:
                output.append("%s setval('%s', coalesce(max(%s), 1), max(%s) %s null) %s %s;" % \
                    (style.SQL_KEYWORD('SELECT'),
                    style.SQL_FIELD(qn('%s_id_seq' % f.m2m_db_table())),
                    style.SQL_FIELD(qn('id')),
                    style.SQL_FIELD(qn('id')),
                    style.SQL_KEYWORD('IS NOT'),
                    style.SQL_KEYWORD('FROM'),
                    style.SQL_TABLE(qn(f.m2m_db_table()))))
        return output

    def savepoint_create_sql(self, sid):
        return "SAVEPOINT %s" % sid

    def savepoint_commit_sql(self, sid):
        return "RELEASE SAVEPOINT %s" % sid

    def savepoint_rollback_sql(self, sid):
        return "ROLLBACK TO SAVEPOINT %s" % sid

    def prep_for_iexact_query(self, x):
        return x

    def check_aggregate_support(self, aggregate):
        """Check that the backend fully supports the provided aggregate.

        The implementation of population statistics (STDDEV_POP and VAR_POP)
        under Postgres 8.2 - 8.2.4 is known to be faulty. Raise
        NotImplementedError if this is the database in use.
        """
        if aggregate.sql_function == 'STDDEV_POP' or aggregate.sql_function == 'VAR_POP':
            if self.postgres_version[0] == 8 and self.postgres_version[1] == 2 and self.postgres_version[2] <= 4:
                raise NotImplementedError('PostgreSQL 8.2 to 8.2.4 is known to have a faulty implementation of %s. Please upgrade your version of PostgreSQL.' % aggregate.sql_function)
    
    def _calculate_fulltext_weights(self, fields):
        weights = []
        for f in fields:
            if f.search_weight not in weights:
                weights.append(f.search_weight)
        if len(weights) > 4:
            raise ImproperlyConfigured('PostgreSQL only supports at most four different search weights on a model.')
        if len(weights) < 4:
            for w in [0.1, 0.2, 0.4, 1.0]:
                if w not in weights:
                    weights.append(w)
                    if len(weights) == 4:
                        break
        weights.sort() # This puts smallest as D, the default
        return weights
        
    def _fulltext_weights_to_letters(self, fields):
        weights = self._calculate_fulltext_weights(fields)
        return {weights[0]: 'D', weights[1]: 'C', weights[2]: 'B', weights[3]: 'A'}
    
    def fulltext_tsvector_sql(self, fields, table=None):
        qn = self.quote_name
        lang = settings.DATABASE_OPTIONS.get('search_language', 'english')
        tsvector_pattern = "to_tsvector('%(lang)s', %(col)s)"
        # __search lookup, maybe needs a separate method?
        if isinstance(fields, str):
            return tsvector_pattern % {
                'col': qn(fields),
                'lang': lang,}
        if len(fields) > 1:
            tsvector_pattern = "setweight(to_tsvector('%(lang)s', coalesce(%(col)s, '')), '%(rank)s')"
        if table is None:
            column_pattern = '%s'
        else:
            column_pattern = '%s.%%s' % qn(table)
        weights = self._fulltext_weights_to_letters(fields)
        tsvector = ' || '.join([tsvector_pattern % {
                'col': column_pattern % qn(f.column),
                # search_language does not work with qn() - it adds double 
                # quotes
                'lang': lang,
                'rank': weights[f.search_weight],
            } for f in fields])
        if len(fields) > 1:
            # The tsvectors joined with || need to be grouped
            tsvector = '(%s)' % tsvector
        return tsvector
        
    def fulltext_search_sql(self, fields, table=None):
        return 'to_tsquery(%%s) @@ %s' % self.fulltext_tsvector_sql(fields, table)
    
    def fulltext_relevance_sql(self, fields, table=None):
        weights = self._calculate_fulltext_weights(fields)
        return "ts_rank('{%.2f, %.2f, %.2f, %.2f}', %s, to_tsquery(%%s), 32)" \
               % (tuple(weights) + (self.fulltext_tsvector_sql(fields, table),))
                    
    def fulltext_prepare_queries(self, queries):
        """
        Given a list of search queries, returns a single query string.
        
        This is primarily for joining the queries using AND statements, but 
        could also be used for processing the query itself.
        """
        # TODO: this should be better
        return ' & '.join([' & '.join(q.split()) for q in queries])
        