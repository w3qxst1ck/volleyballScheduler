from datetime import datetime
from typing import List

from database import schemas

import pytz
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side

from database.schemas import User
from settings import settings


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


def convert_date(date: datetime) -> str:
    """Перевод даты в формат для вывода"""
    return date.date().strftime("%d.%m.%Y")


def convert_date_named_month(date: datetime) -> str:
    """Перевод даты в дату с месяцем прописью"""
    months = {
        1: "января",
        2: "февраля",
        3: "марта",
        4: "апреля",
        5: "мая",
        6: "июня",
        7: "июля",
        8: "августа",
        9: "сентября",
        10: "октября",
        11: "ноября",
        12: "декабря",
    }
    return f"{date.date().day} {months[date.date().month]} {date.date().strftime('%Y')}"


def convert_time(date: datetime) -> str:
    """Перевод времени в формат для вывода"""
    return date.time().strftime("%H:%M")


def is_valid_date(date: str) -> bool:
    """Проверка валидности даты"""
    try:
        result = datetime.strptime(date, "%d.%m.%Y").date()
        if result < datetime.now(tz=pytz.timezone("Europe/Moscow")).date():
            return False
    except ValueError:
        return False
    return True


def is_valid_time(time: str) -> bool:
    """Проверка валидности времени"""
    time_list = time.split(":")

    if len(time_list) != 2:
        return False

    hours = time_list[0]
    minutes = time_list[1]
    try:
        hours = int(hours)
        minutes = int(minutes)
    except ValueError:
        return False

    if hours > 24 or hours < 0:
        return False
    if minutes > 59 or minutes < 0:
        return False

    return True


def is_valid_places(places: str) -> bool:
    """Проверка валидности количества мест"""
    try:
        places = int(places)
    except ValueError:
        return False

    if places <= 0:
        return False

    return True


def is_valid_price(price: str) -> bool:
    """Проверка валидности цены"""
    try:
        price = int(price)
    except ValueError:
        return False

    if price < 0:
        return False

    return True


def get_unique_dates(dates: list[datetime]) -> dict[str:int]:
    """Выбор уникальных дат в событиях"""
    result = {}
    for date in dates:
        converted_date = convert_date(date)

        if converted_date not in result.keys():
            result[converted_date] = 1
        else:
            result[converted_date] += 1

    return result


def get_weekday_from_date(date_str: str) -> str:
    """Получение дня недели из str даты в формате DD.MM.YYYY для использования в списке событий для пользователей"""
    date = datetime.strptime(date_str, "%d.%m.%Y").date()
    weekday = settings.weekdays[datetime.weekday(date)]
    return weekday


async def write_excel_file(data: List[schemas.User]) -> None:
    """Создание файла"""
    wb = Workbook()

    # удаление лишнего листа
    del wb["Sheet"]

    # создание нового листа
    wb.create_sheet("Players", index=0)
    sheet = wb['Players']

    # настройка стилей
    font = Font(bold=True)
    align_center = Alignment(horizontal="center")
    border = Border(
        left=Side(border_style="thin", color='FF000000'),
        right=Side(border_style="thin", color='FF000000'),
        top=Side(border_style="thin", color='FF000000'),
        bottom=Side(border_style="thin", color='FF000000'),
    )

    # width
    sheet.column_dimensions["A"].width = 10
    sheet.column_dimensions["B"].width = 20
    sheet.column_dimensions["C"].width = 20
    sheet.column_dimensions["D"].width = 20

    # header
    sheet.append(["№ п/п", "Имя", "Фамилия", "Уровень"])

    # align
    sheet["A1"].alignment = align_center
    sheet["B1"].alignment = align_center
    sheet["C1"].alignment = align_center
    sheet["D1"].alignment = align_center

    # font
    sheet["A1"].font = font
    sheet["B1"].font = font
    sheet["C1"].font = font
    sheet["D1"].font = font

    # border
    sheet["A1"].border = border
    sheet["B1"].border = border
    sheet["C1"].border = border
    sheet["D1"].border = border

    for idx, user in enumerate(data, start=1):
        level = settings.levels[user.level] if user.level else "Не определен"
        sheet.append([idx, user.firstname, user.lastname, level])

        # выравнивание колонки А по центру
        a_number = f"A{idx+1}"
        sheet[a_number].alignment = align_center

        # границы ячеек
        b_number = f"B{idx+1}"
        c_number = f"C{idx+1}"
        d_number = f"D{idx+1}"
        sheet[a_number].border = border
        sheet[b_number].border = border
        sheet[c_number].border = border
        sheet[d_number].border = border

    wb.save("players/players.xlsx")
    print('DataFrame is written to Excel File successfully.')


def calculate_team_points(users: List[User], libero_id: int = None) -> int:
    """
    Подсчет количества баллов команды для турниров (берется 6 лучших игроков).
    Влияет пол игрока и его уровень.
    """
    if len(users) == 0:
        return 0

    team_points = 0

    # сортируем по уровню
    sorted_users = sorted(users, key=lambda u: u.level, reverse=True)

    # берем баллы 6 сильнейших
    for user in sorted_users[:6]:

        # если среди сильнейших есть либеро
        if user.id == libero_id:
            # случай когда кол-во человек в команде больше 6
            if len(sorted_users) > 6:
                extra_user = sorted_users[7]
                user_points = settings.user_points[extra_user.gender][extra_user.level]
                team_points += user_points

            # если кол-во меньше 6, просто не учитываем его очки
            else:
                continue
        else:
            user_points = settings.user_points[user.gender][user.level]
            team_points += user_points

    return team_points






