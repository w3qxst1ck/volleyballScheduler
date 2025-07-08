from typing import Any, List

from aiogram import Router, types, F, Bot
from aiogram.enums import ParseMode
from aiogram.filters import or_f
from aiogram.fsm.context import FSMContext

from database.schemas import TeamUsers, User, Tournament, TournamentTeams
from logger import logger
from routers.middlewares import CheckPrivateMessageMiddleware, DatabaseMiddleware
from routers import keyboards as kb, messages as ms
from routers.fsm_states import RegNewTeamFSM
from database.orm import AsyncOrm
from routers import utils
from routers.utils import calculate_team_points, convert_date_named_month
from settings import settings

router = Router()
router.message.middleware.register(CheckPrivateMessageMiddleware())
router.callback_query.middleware.register(CheckPrivateMessageMiddleware())
router.message.middleware.register(DatabaseMiddleware())
router.callback_query.middleware.register(DatabaseMiddleware())


@router.callback_query(F.data.split("_")[0] == "pay-for-team")
async def payment_message(callback: types.CallbackQuery, session: Any) -> None:
    """Отправка сообщения об условиях оплаты"""
    team_id = int(callback.data.split("_")[1])
    tournament_id = int(callback.data.split("_")[2])

    team: TeamUsers = await AsyncOrm.get_team(team_id, session)
    tournament: Tournament = await AsyncOrm.get_tournament_by_id(tournament_id, session)

    msg = ms.invoice_message_for_team(tournament, team.reserve)
    keyboard = kb.payment_tournament_confirm_keyboard(team_id, tournament_id, team.reserve)

    await callback.message.edit_text(msg, reply_markup=keyboard.as_markup())




