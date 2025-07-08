from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def build_market_keyboard(pseudos, page=0):
    NICKS_PER_PAGE = 5
    start = page * NICKS_PER_PAGE
    end = start + NICKS_PER_PAGE
    page_nicks = pseudos[start:end]
    kb = [
        [InlineKeyboardButton(text=f"{p['pseudo']} ({p['price']} т.)", callback_data=f"market_buy_{p['id']}")]
        for p in page_nicks if p.get('is_available', True)
    ]
    nav = []
    if start > 0:
        nav.append(InlineKeyboardButton(text="<<", callback_data=f"market_page_{page-1}"))
    if end < len(pseudos):
        nav.append(InlineKeyboardButton(text=">>", callback_data=f"market_page_{page+1}"))
    if nav:
        kb.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=kb)

def build_nick_choice_keyboard(pseudo_names, page=0):
    """
    Создает клавиатуру для выбора ника в комментариях
    pseudo_names: список кортежей (id, name)
    """
    NICKS_PER_PAGE = 5
    start = page * NICKS_PER_PAGE
    end = start + NICKS_PER_PAGE
    page_nicks = pseudo_names[start:end]
    
    kb = [
        [InlineKeyboardButton(text=name, callback_data=f"choose_nick_{nick_id}")]
        for nick_id, name in page_nicks
    ]
    
    nav = []
    if start > 0:
        nav.append(InlineKeyboardButton(text="<<", callback_data=f"nickpage_{page-1}"))
    if end < len(pseudo_names):
        nav.append(InlineKeyboardButton(text=">>", callback_data=f"nickpage_{page+1}"))
    if nav:
        kb.append(nav)
    
    return InlineKeyboardMarkup(inline_keyboard=kb)

cancel_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Отмена")]],
    resize_keyboard=True
)