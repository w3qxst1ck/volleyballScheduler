from datetime import datetime
from typing import List


class FullnameException(Exception):
    """Ошибка валидации имени и фамилии"""
    pass


async def get_firstname_lastname(fullname: str) -> List[str]:
    """Проверка корректности введенного имени"""
    fullname_list = fullname.split(" ")
    try:
        firstname = fullname_list[0]
        lastname = fullname_list[1]
    except IndexError:
        raise FullnameException

    if len(fullname_list) != 2:
        raise FullnameException

    if len(firstname) < 2 or len(lastname) < 2:
        raise FullnameException

    for char in firstname:
        if char.isdigit() or not char.isalpha():
            raise FullnameException

    for char in lastname:
        if char.isdigit() or not char.isalpha():
            raise FullnameException

    return [firstname, lastname]


def convert_date(date: datetime) -> datetime.date:
    """Перевод даты в формат для вывода"""
    return date.date().strftime("%d.%m.%Y")