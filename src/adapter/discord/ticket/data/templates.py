"""Template data and examples for the ticket system."""

from typing import Dict, List

# Default welcome messages for different ticket types
DEFAULT_WELCOME_MESSAGES = {
    "simple": "🎫 **Добро пожаловать в ваш тикет!**\n\nОпишите вашу проблему или вопрос, и наша команда поддержки поможет вам как можно скорее.\n\n**Правила:**\n• Будьте вежливы и терпеливы\n• Предоставьте как можно больше деталей\n• Не спамьте сообщениями",
    "form": "📝 **Спасибо за обращение!**\n\nВаша форма была успешно отправлена нашей команде поддержки. Мы рассмотрим ваш запрос и свяжемся с вами в ближайшее время."
}

# Example form questions for different purposes
EXAMPLE_FORM_QUESTIONS = {
    "support": [
        "Как вас зовут?",
        "Опишите вашу проблему подробно",
        "Когда впервые возникла эта проблема?",
        "Какие действия вы уже предпринимали для решения?",
        "Какой у вас приоритет этого запроса? (Низкий/Средний/Высокий)"
    ],
    "bug_report": [
        "Как называется найденная ошибка?",
        "Опишите шаги для воспроизведения ошибки",
        "Что должно было произойти?",
        "Что произошло на самом деле?",
        "В какой среде вы обнаружили ошибку? (ОС, браузер, версия и т.д.)"
    ],
    "feature_request": [
        "Как называется предлагаемая функция?",
        "Опишите функцию подробно",
        "Зачем нужна эта функция?",
        "Как эта функция должна работать?",
        "Есть ли альтернативные решения, которые вы рассматривали?"
    ],
    "application": [
        "Как вас зовут?",
        "Сколько вам лет?",
        "Расскажите о себе",
        "Почему вы хотите присоединиться к нашему сообществу?",
        "Есть ли у вас опыт модерации или администрирования?"
    ]
}

# Error messages
ERROR_MESSAGES = {
    "not_configured": "❌ **Система тикетов не настроена**\n\nСистема тикетов не была настроена для этого сервера. Обратитесь к администратору.",
    "no_permissions": "❌ **Недостаточно прав**\n\nУ вас нет прав для выполнения этого действия.",
    "invalid_channel": "❌ **Неверный канал**\n\nЭта команда может использоваться только в каналах тикетов.",
    "form_timeout": "⏰ **Время истекло**\n\nВремя заполнения формы истекло. Пожалуйста, начните заново.",
    "already_has_ticket": "⚠️ **У вас уже есть тикет**\n\nВы можете иметь только один активный тикет одновременно.",
    "bot_missing_permissions": "❌ **Недостаточно прав у бота**\n\nУ бота недостаточно прав для выполнения этого действия. Проверьте права в настройках сервера."
}

# Success messages
SUCCESS_MESSAGES = {
    "ticket_created": "✅ **Тикет создан**\n\nВаш тикет был успешно создан!",
    "ticket_closed": "🔒 **Тикет закрыт**\n\nТикет был успешно закрыт.",
    "settings_updated": "⚙️ **Настройки обновлены**\n\nНастройки системы тикетов были успешно обновлены.",
    "co_owner_added": "👑 **Совладелец добавлен**\n\nПользователь был успешно добавлен как совладелец.",
    "role_added": "🎭 **Роль добавлена**\n\nРоль была добавлена к системе тикетов."
}

# Help text for commands
HELP_TEXT = {
    "setup": """
**Настройка системы тикетов**

Используйте команду `/ticket-setup` для настройки системы тикетов:

**Параметры:**
• `ticket_type` - Тип тикетов (simple/form)
• `welcome_message` - Приветственное сообщение
• `target_channel` - Канал для форм (только для типа form)

**Пример:**
`/ticket-setup ticket_type:simple welcome_message:Добро пожаловать!`
""",
    "questions": """
**Настройка вопросов формы**

Используйте команду `/ticket-questions` для настройки вопросов:

**Формат:**
Вопросы разделяются точкой с запятой (;)
Максимум 10 вопросов

**Пример:**
`/ticket-questions questions:Как вас зовут?;Опишите проблему;Когда это произошло?`
""",
    "roles": """
**Управление ролями доступа**

Используйте команду `/ticket-roles` для управления ролями:

**Действия:**
• `add` - Добавить роль
• `remove` - Удалить роль

**Пример:**
`/ticket-roles action:add role:@Модераторы`
"""
}


def get_default_welcome_message(ticket_type: str) -> str:
    """Get default welcome message for ticket type."""
    return DEFAULT_WELCOME_MESSAGES.get(ticket_type, DEFAULT_WELCOME_MESSAGES["simple"])


def get_example_questions(category: str) -> List[str]:
    """Get example questions for a category."""
    return EXAMPLE_FORM_QUESTIONS.get(category, EXAMPLE_FORM_QUESTIONS["support"])


def get_error_message(error_type: str) -> str:
    """Get error message by type."""
    return ERROR_MESSAGES.get(error_type, "❌ Произошла неизвестная ошибка.")


def get_success_message(success_type: str) -> str:
    """Get success message by type."""
    return SUCCESS_MESSAGES.get(success_type, "✅ Операция выполнена успешно.")


def get_help_text(topic: str) -> str:
    """Get help text for a topic."""
    return HELP_TEXT.get(topic, "Справка недоступна для этой темы.")
