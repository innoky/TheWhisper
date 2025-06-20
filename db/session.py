from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, and_, insert
from .models import Base, User, PseudoName, UserPseudoName
from config import DATABASE_URL
import time

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(
    bind=engine, expire_on_commit=False, class_=AsyncSession
)

async def get_or_create_user(user_id: int, username: str, firstname: str, lastname: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            return user
        user = User(
            id = user_id,
            username = username,
            firstname = firstname,
            lastname = lastname,
            balance = 50,
            is_banned = False,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        # Выдаём базовые ники
        for base_nick_id in (14, 15, 16):
            session.add(UserPseudoName(user_id=user_id, pseudo_name_id=base_nick_id))
        await session.commit()
        return user 

async def get_available_pseudo_names(user_id: int):
    async with AsyncSessionLocal() as session:
        # Получить id всех ников, которые уже есть у пользователя
        result = await session.execute(
            select(UserPseudoName.pseudo_name_id).where(UserPseudoName.user_id == user_id)
        )
        owned_ids = {row[0] for row in result.fetchall()}
        # Получить все ники, которых нет у пользователя
        result = await session.execute(
            select(PseudoName).where(~PseudoName.id.in_(owned_ids))
        )
        return result.scalars().all()

async def buy_pseudo_name(user_id: int, pseudo_name_id: int):
    async with AsyncSessionLocal() as session:
        # Проверить, есть ли у пользователя этот ник
        result = await session.execute(
            select(UserPseudoName).where(
                and_(
                    UserPseudoName.user_id == user_id,
                    UserPseudoName.pseudo_name_id == pseudo_name_id
                )
            )
        )
        if result.scalar_one_or_none():
            return False, "У вас уже есть этот ник."
        # Получить ник и пользователя
        pseudo_name = (await session.execute(
            select(PseudoName).where(PseudoName.id == pseudo_name_id)
        )).scalar_one_or_none()
        user = (await session.execute(
            select(User).where(User.id == user_id)
        )).scalar_one_or_none()
        if not pseudo_name or not user:
            return False, "Ошибка: пользователь или ник не найден."
        if user.balance is None or user.balance < pseudo_name.cost:
            return False, "Недостаточно средств на балансе."
        # Списать баланс и добавить ник
        user.balance -= pseudo_name.cost
        session.add(UserPseudoName(user_id=user_id, pseudo_name_id=pseudo_name_id))
        await session.commit()
        return True, f"Вы успешно купили ник: {pseudo_name.name}" 