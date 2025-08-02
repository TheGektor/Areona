import discord
from discord import app_commands, Interaction
from discord.ext import commands
from src.adapter.discord.ticket.database.models import save_bot_settings, get_bot_settings

SETTINGS_CATEGORIES = [
    ("Тикеты", "ticket")
]

class SettingsPanel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="settings-panel", description="Открыть визуальную панель настройки бота в выбранном канале.")
    @app_commands.describe(channel="Канал для панели настройки")
    async def settings_panel(self, interaction: Interaction, channel: discord.TextChannel):
        embed = discord.Embed(title="Панель настройки бота", description="Выберите категорию для изменения настроек.")
        for name, key in SETTINGS_CATEGORIES:
            embed.add_field(name=name, value=f"Нажмите кнопку ниже, чтобы изменить {name}", inline=False)
        view = SettingsPanelView()
        await channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"Панель настройки отправлена в {channel.mention}", ephemeral=True)

class SettingsPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for name, key in SETTINGS_CATEGORIES:
            self.add_item(SettingsCategoryButton(name, key))

class SettingsCategoryButton(discord.ui.Button):
    def __init__(self, label, category_key):
        super().__init__(label=label, style=discord.ButtonStyle.primary, custom_id=f"settings_{category_key}")
        self.category_key = category_key

    async def callback(self, interaction: Interaction):
        # Открытие каталога настроек тикетов
        await interaction.response.send_message(embed=ticket_settings_embed(), ephemeral=True, view=TicketSettingsView())

def ticket_settings_embed():
    settings = get_bot_settings()
    embed = discord.Embed(title="Настройки тикетов", description="Измените параметры тикетов.")
    embed.add_field(name="Формат тикета", value=settings.get("ticket_format", "text"), inline=False)
    embed.add_field(name="Тип тикета", value=settings.get("ticket_type", "simple"), inline=False)
    embed.add_field(name="Приветствие", value=settings.get("welcome_message", "Не задано"), inline=False)
    embed.add_field(name="Канал для форм", value=settings.get("target_channel", "Не задан"), inline=False)
    return embed

class TicketSettingsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketFormatDropdown())
        self.add_item(TicketTypeDropdown())
        self.add_item(EditWelcomeButton())
        self.add_item(EditQuestionsButton())
class EditQuestionsButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Изменить вопросы формы", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: Interaction):
        await interaction.response.send_modal(QuestionsModal())

class QuestionsModal(discord.ui.Modal, title="Вопросы для формы"):
    questions = discord.ui.TextInput(
        label="Вопросы (через ;)",
        style=discord.TextStyle.long,
        placeholder="Пример: Как вас зовут?;Опишите проблему;Когда это произошло?"
    )

    async def on_submit(self, interaction: Interaction):
        from src.adapter.discord.ticket.database.models import save_bot_settings
        # Ограничение: максимум 10 вопросов
        questions_list = [q.strip() for q in self.questions.value.split(';') if q.strip()][:10]
        save_bot_settings(form_questions=';'.join(questions_list))
        await interaction.response.send_message("Вопросы формы обновлены!", ephemeral=True)
class TicketFormatDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Текстовый", value="text", description="Приватный канал для тикета"),
            discord.SelectOption(label="Форум", value="forum", description="Пост/тема в Forum Channel")
        ]
        super().__init__(placeholder="Выберите формат тикета...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: Interaction):
        save_bot_settings(ticket_format=self.values[0])
        await interaction.response.send_message(f"Формат тикета изменён на: {self.values[0]}", ephemeral=True)
class EditWelcomeButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Изменить приветствие", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: Interaction):
        await interaction.response.send_modal(WelcomeMessageModal())

class TicketTypeDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Simple", value="simple", description="Простой тикет"),
            discord.SelectOption(label="Form", value="form", description="Тикет-форма")
        ]
        super().__init__(placeholder="Выберите тип тикета...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: Interaction):
        save_bot_settings(ticket_type=self.values[0])
        await interaction.response.send_message(f"Тип тикета изменён на: {self.values[0]}", ephemeral=True)

class WelcomeMessageModal(discord.ui.Modal, title="Изменить приветствие"):
    welcome_message = discord.ui.TextInput(
        label="Приветственное сообщение",
        style=discord.TextStyle.long,
        placeholder="Пример: Добро пожаловать! Опишите вашу проблему."
    )

    async def on_submit(self, interaction: Interaction):
        save_bot_settings(welcome_message=self.welcome_message.value)
        await interaction.response.send_message("Приветствие обновлено!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(SettingsPanel(bot))
