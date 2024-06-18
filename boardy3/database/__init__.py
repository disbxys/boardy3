
from sqlalchemy import Column


# This almost feels too scrappy
def column_to_int(x: Column[int]) -> int:
    return int(str(x))