
from django.db import connection
from south.db import generic

class DatabaseOperations(generic.DatabaseOperations):

    """
    SQLite3 implementation of database operations.
    """

    # SQLite ignores foreign key constraints. I wish I could.
    supports_foreign_keys = False
    
    # You can't add UNIQUE columns with an ALTER TABLE.
    def add_column(self, table_name, name, field, *args, **kwds):
        # Run ALTER TABLE with no unique column
        unique, field._unique, field.db_index = field.unique, False, False
        # If it's not nullable, and has no default, raise an error (SQLite is picky)
        if not field.null and (not field.has_default() or field.get_default() is None):
            raise ValueError("You cannot add a null=False column without a default value.")
        generic.DatabaseOperations.add_column(self, table_name, name, field, *args, **kwds)
        # If it _was_ unique, make an index on it.
        if unique:
            self.create_index(table_name, [name], unique=True)
    
    def _alter_sqlite_table(self, table_name, orm):
        """
        Not supported under SQLite.
        """
        if not orm:
            raise NotImplementedError("SQLite does not directly support renaming columns. So inorder for this to work, you must pass the orm object as an argument.")
        model_name = table_name.replace('_', '.', 1)
        model = orm[model_name]
        if getattr(model, '_already_run_alter_schema_trick', False):
            return
        print "shit " + table_name
        temp_name = table_name + "_temporary_for_schema_change"
        self.rename_table(table_name, temp_name)
        fields = [(fld.name, fld) for fld in model._meta.fields]
        self.create_table(table_name, fields)
        columns = [fld.column for name, fld in fields]
        self.copy_data(temp_name, table_name, columns)
        self.delete_table(temp_name, cascade=False)
        model._already_run_alter_schema_trick = True
    
    def alter_column(self, table_name, name, field, orm=None, explicit_name=True):
        self._alter_sqlite_table(table_name, orm)

    def delete_column(self, table_name, column_name, orm=None):
        self._alter_sqlite_table(table_name, orm)
    
    # Nor RENAME COLUMN
    def rename_column(self, table_name, old, new):
        """
        Not supported under SQLite.
        """
        raise NotImplementedError("SQLite does not support renaming columns.")
    
    # Nor unique creation
    def create_unique(self, table_name, columns):
        """
        Not supported under SQLite.
        """
        print "WARNING: SQLite does not support adding unique constraints. Ignored."
    
    # Nor unique deletion
    def delete_unique(self, table_name, columns):
        """
        Not supported under SQLite.
        """
        print "WARNING: SQLite does not support removing unique constraints. Ignored."
    
    # No cascades on deletes
    def delete_table(self, table_name, cascade=True):
        generic.DatabaseOperations.delete_table(self, table_name, False)


    def copy_data(self, src, dst, fields):
        sql = "INSERT INTO '%s' SELECT %s FROM '%s';" % (dst, ','.join(fields), src)
        self.execute(sql)