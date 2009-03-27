from django.conf import settings
from django.db.backends.creation import BaseDatabaseCreation

class DatabaseCreation(BaseDatabaseCreation):
    # This dictionary maps Field objects to their associated MySQL column
    # types, as strings. Column-type strings can contain format strings; they'll
    # be interpolated against the values of Field.__dict__ before being output.
    # If a column type is set to None, it won't be included in the output.
    data_types = {
        'AutoField':         'integer AUTO_INCREMENT',
        'BooleanField':      'bool',
        'CharField':         'varchar(%(max_length)s)',
        'CommaSeparatedIntegerField': 'varchar(%(max_length)s)',
        'DateField':         'date',
        'DateTimeField':     'datetime',
        'DecimalField':      'numeric(%(max_digits)s, %(decimal_places)s)',
        'FileField':         'varchar(%(max_length)s)',
        'FilePathField':     'varchar(%(max_length)s)',
        'FloatField':        'double precision',
        'IntegerField':      'integer',
        'IPAddressField':    'char(15)',
        'NullBooleanField':  'bool',
        'OneToOneField':     'integer',
        'PositiveIntegerField': 'integer UNSIGNED',
        'PositiveSmallIntegerField': 'smallint UNSIGNED',
        'SlugField':         'varchar(%(max_length)s)',
        'SmallIntegerField': 'smallint',
        'TextField':         'longtext',
        'TimeField':         'time',
    }

    def sql_table_creation_suffix(self):
        suffix = []
        if settings.TEST_DATABASE_CHARSET:
            suffix.append('CHARACTER SET %s' % settings.TEST_DATABASE_CHARSET)
        if settings.TEST_DATABASE_COLLATION:
            suffix.append('COLLATE %s' % settings.TEST_DATABASE_COLLATION)
        return ' '.join(suffix)

    def sql_for_inline_foreign_key_references(self, field, known_models, style):
        "All inline references are pending under MySQL"
        return [], True
        
    def sql_for_inline_many_to_many_references(self, model, field, style):
        from django.db import models
        opts = model._meta
        qn = self.connection.ops.quote_name
        
        table_output = [
            '    %s %s %s,' %
                (style.SQL_FIELD(qn(field.m2m_column_name())),
                style.SQL_COLTYPE(models.ForeignKey(model).db_type()),
                style.SQL_KEYWORD('NOT NULL')),
            '    %s %s %s,' %
            (style.SQL_FIELD(qn(field.m2m_reverse_name())),
            style.SQL_COLTYPE(models.ForeignKey(field.rel.to).db_type()),
            style.SQL_KEYWORD('NOT NULL'))
        ]
        deferred = [
            (field.m2m_db_table(), field.m2m_column_name(), opts.db_table,
                opts.pk.column),
            (field.m2m_db_table(), field.m2m_reverse_name(),
                field.rel.to._meta.db_table, field.rel.to._meta.pk.column)
            ]
        return table_output, deferred
        
    def sql_for_fulltext_index(self, model, fields, style):
        qn = self.connection.ops.quote_name
        return (style.SQL_KEYWORD('CREATE FULLTEXT INDEX') + ' ' +
            style.SQL_TABLE(qn(self._fulltext_index_name(model, fields))) + ' ' +
            style.SQL_KEYWORD('ON') + ' ' +
            style.SQL_TABLE(qn(model._meta.db_table)) + ' ' +
            "(%s);" % style.SQL_FIELD(", ".join([qn(f.column) for f in fields])))
