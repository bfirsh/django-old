from django.conf import settings
from django.db.backends.creation import BaseDatabaseCreation

class DatabaseCreation(BaseDatabaseCreation):
    # This dictionary maps Field objects to their associated PostgreSQL column
    # types, as strings. Column-type strings can contain format strings; they'll
    # be interpolated against the values of Field.__dict__ before being output.
    # If a column type is set to None, it won't be included in the output.
    data_types = {
        'AutoField':         'serial',
        'BooleanField':      'boolean',
        'CharField':         'varchar(%(max_length)s)',
        'CommaSeparatedIntegerField': 'varchar(%(max_length)s)',
        'DateField':         'date',
        'DateTimeField':     'timestamp with time zone',
        'DecimalField':      'numeric(%(max_digits)s, %(decimal_places)s)',
        'FileField':         'varchar(%(max_length)s)',
        'FilePathField':     'varchar(%(max_length)s)',
        'FloatField':        'double precision',
        'IntegerField':      'integer',
        'IPAddressField':    'inet',
        'NullBooleanField':  'boolean',
        'OneToOneField':     'integer',
        'PositiveIntegerField': 'integer CHECK ("%(column)s" >= 0)',
        'PositiveSmallIntegerField': 'smallint CHECK ("%(column)s" >= 0)',
        'SlugField':         'varchar(%(max_length)s)',
        'SmallIntegerField': 'smallint',
        'TextField':         'text',
        'TimeField':         'time',
    }

    def sql_table_creation_suffix(self):
        assert settings.TEST_DATABASE_COLLATION is None, "PostgreSQL does not support collation setting at database creation time."
        if settings.TEST_DATABASE_CHARSET:
            return "WITH ENCODING '%s'" % settings.TEST_DATABASE_CHARSET
        return ''
        
    def sql_for_fulltext_index(self, model, fields, style):
        qn = self.connection.ops.quote_name
        return (style.SQL_KEYWORD('CREATE INDEX') + ' ' +
            style.SQL_TABLE(qn(self._fulltext_index_name(model, fields))) + ' ' +
            style.SQL_KEYWORD('ON') + ' ' +
            style.SQL_TABLE(qn(model._meta.db_table)) + ' ' +
            style.SQL_KEYWORD('USING') + ' ' +
            'gin(%s);' % self.connection.ops.fulltext_tsvector_sql(fields))
