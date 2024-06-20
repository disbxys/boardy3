from boardy3.utils import get_logger


class DatabaseException(Exception):
    """Base class for database exceptions."""
    
    def __init__(self, msg=None) -> None:
        self.msg = msg or "An error occurred."

        super().__init__(self.msg)

        self.logger = get_logger(__name__)
        self.log_exception()

    def log_exception(self):
        self.logger.error(self.msg)


class DatabaseItemExists(DatabaseException):
    """
    Exception class for when attempting to created an item when it
    already exists in the database.
    """


class DatabaseItemDoesNotExist(DatabaseException):
    """
    Exception class for when attempting to retrieve an item when it
    does not exist in the database.
    """