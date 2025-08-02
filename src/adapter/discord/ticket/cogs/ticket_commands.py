import discord
from discord import app_commands, Interaction
from discord.ext import commands
import asyncio
from src.adapter.discord.ticket.database.models import get_bot_settings
    return discord.Embed(title=title, description=description, color=discord.Color.red())
        self.bot = bot
        self.active_forms = {}

    @app_commands.command(name="ticket", description="Создать новый тикет")
    async def ticket(self, interaction: Interaction):
        settings = get_bot_settings()
        ticket_format = settings.get("ticket_format", "text")
        welcome_message = settings.get("welcome_message", "Добро пожаловать в тикет!")
        ticket_type = settings.get("ticket_type", "simple")
        forum_channel_id = int(settings.get("target_channel", 0))
        form_questions = settings.get("form_questions", "")

        if ticket_type == "form" and form_questions:
            # Запуск формы: отправить вопросы пользователю
            questions = [q.strip() for q in form_questions.split(';') if q.strip()]
            await interaction.response.send_message(embed=create_embed("Форма тикета", "Ответьте на вопросы ниже."), ephemeral=True, view=TicketFormView(questions, ticket_format, forum_channel_id, welcome_message))
            return

        # Обычный тикет
        await self.create_ticket(interaction, ticket_format, forum_channel_id, welcome_message)

    async def create_ticket(self, interaction, ticket_format, forum_channel_id, welcome_message, form_answers=None):
        if ticket_format == "forum":
            forum_channel = interaction.guild.get_channel(forum_channel_id)
            if forum_channel and isinstance(forum_channel, discord.ForumChannel):
                thread = await forum_channel.create_thread(name=f"Тикет от {interaction.user.display_name}", content=welcome_message)
                if form_answers:
                    await thread.send(embed=create_embed("Ответы пользователя", form_answers))
                await interaction.followup.send(embed=create_success_embed("Тикет создан", f"Ваш тикет: {thread.mention}"), ephemeral=True)
            else:
                await interaction.followup.send(embed=create_error_embed("Ошибка", "Канал форума не найден или не задан."), ephemeral=True)
        else:
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
            }
            category = None
            for cat in interaction.guild.categories:
                if cat.name.lower() == "tickets":
                    category = cat
                    break
            channel = await interaction.guild.create_text_channel(
                name=f"ticket-{interaction.user.display_name}",
                overwrites=overwrites,
                category=category
            )
            await channel.send(embed=create_embed("Добро пожаловать!", welcome_message))
            if form_answers:
                await channel.send(embed=create_embed("Ответы пользователя", form_answers))
            await interaction.followup.send(embed=create_success_embed("Тикет создан", f"Ваш тикет: {channel.mention}"), ephemeral=True)

    @app_commands.command(name="close-ticket", description="Закрыть текущий тикет")
    async def close_ticket(self, interaction: Interaction):
        # Проверка: команда вызывается в тикет-канале или треде
        channel = interaction.channel
        if isinstance(channel, discord.TextChannel) and channel.name.startswith("ticket-"):
            await interaction.response.send_message(embed=create_embed("Подтверждение", "Вы уверены, что хотите закрыть тикет?"), view=CloseTicketView(channel), ephemeral=True)
        elif isinstance(channel, discord.Thread) and channel.parent and isinstance(channel.parent, discord.ForumChannel):
            await interaction.response.send_message(embed=create_embed("Подтверждение", "Вы уверены, что хотите закрыть тикет?"), view=CloseTicketView(channel), ephemeral=True)
        else:
            await interaction.response.send_message(embed=create_error_embed("Ошибка", "Эта команда доступна только в тикет-канале или треде."), ephemeral=True)

class TicketFormView(discord.ui.View):
    def __init__(self, questions, ticket_format, forum_channel_id, welcome_message):
        super().__init__(timeout=None)
        self.questions = questions
        self.ticket_format = ticket_format
        self.forum_channel_id = forum_channel_id
        self.welcome_message = welcome_message
        self.answers = {}
        self.current = 0
        self.add_item(NextQuestionButton(self))

class NextQuestionButton(discord.ui.Button):
    def __init__(self, form_view):
        super().__init__(label="Ответить", style=discord.ButtonStyle.primary)
        self.form_view = form_view

    async def callback(self, interaction: Interaction):
        if self.form_view.current < len(self.form_view.questions):
            question = self.form_view.questions[self.form_view.current]
            await interaction.response.send_modal(FormAnswerModal(self.form_view, question))
        else:
            # Все вопросы заданы, создать тикет
            answers_text = "\n".join([f"**{q}**\n{self.form_view.answers.get(i, '')}" for i, q in enumerate(self.form_view.questions)])
            cog = interaction.client.get_cog("TicketCommands")
            if cog:
                await cog.create_ticket(interaction, self.form_view.ticket_format, self.form_view.forum_channel_id, self.form_view.welcome_message, answers_text)
            else:
                await interaction.response.send_message(embed=create_error_embed("Ошибка", "Команда тикетов не найдена."), ephemeral=True)

class FormAnswerModal(discord.ui.Modal):
    def __init__(self, form_view, question):
        super().__init__(title="Ответ на вопрос")
        self.form_view = form_view
        self.question = question
        self.answer = discord.ui.TextInput(label=question, style=discord.TextStyle.long)
        self.add_item(self.answer)

    async def on_submit(self, interaction: Interaction):
        self.form_view.answers[self.form_view.current] = self.answer.value
        self.form_view.current += 1
        if self.form_view.current < len(self.form_view.questions):
            await interaction.response.send_message(embed=create_embed("Следующий вопрос", self.form_view.questions[self.form_view.current]), view=self.form_view, ephemeral=True)
        else:
            answers_text = "\n".join([f"**{q}**\n{self.form_view.answers.get(i, '')}" for i, q in enumerate(self.form_view.questions)])
            cog = interaction.client.get_cog("TicketCommands")
            if cog:
                await cog.create_ticket(interaction, self.form_view.ticket_format, self.form_view.forum_channel_id, self.form_view.welcome_message, answers_text)
            else:
                await interaction.response.send_message(embed=create_error_embed("Ошибка", "Команда тикетов не найдена."), ephemeral=True)

class CloseTicketView(discord.ui.View):
    def __init__(self, channel):
        super().__init__(timeout=None)
        self.channel = channel
        self.add_item(CloseTicketButton(self))

class CloseTicketButton(discord.ui.Button):
    def __init__(self, close_view):
        super().__init__(label="Закрыть тикет", style=discord.ButtonStyle.danger)
        self.close_view = close_view

    async def callback(self, interaction: Interaction):
        try:
            await self.close_view.channel.delete()
            await interaction.response.send_message(embed=create_success_embed("Тикет закрыт", "Канал удалён."), ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(embed=create_error_embed("Ошибка", f"Не удалось закрыть тикет: {str(e)}"), ephemeral=True)

async def setup(bot):
    await bot.add_cog(TicketCommands(bot))
"""Ticket commands for users and staff."""
import discord
from discord import app_commands, Interaction
from discord.ext import commands
import asyncio
from src.adapter.discord.ticket.database.models import get_bot_settings
# --- Embed helpers ---
def create_embed(title, description, color=discord.Color.blurple()):
    return discord.Embed(title=title, description=description, color=color)

class TicketCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        ticket_type = settings.get("ticket_type", "simple")
        forum_channel_id = int(settings.get("target_channel", 0))

        try:
            if ticket_format == "forum":
                forum_channel = interaction.guild.get_channel(forum_channel_id)
                if forum_channel and isinstance(forum_channel, discord.ForumChannel):
                    thread = await forum_channel.create_thread(name=f"Тикет от {interaction.user.display_name}", content=welcome_message)
                    await interaction.response.send_message(
                        embed=create_success_embed("Тикет создан", f"Ваш тикет: {thread.mention}"), ephemeral=True)
                else:
                    await interaction.response.send_message(
                        embed=create_error_embed("Ошибка", "Канал форума не найден или не задан."), ephemeral=True)
            else:
                overwrites = {
                    interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
                }
                category = None
                for cat in interaction.guild.categories:
                    if cat.name.lower() == "tickets":
                        category = cat
                        break
                channel = await interaction.guild.create_text_channel(
                    name=f"ticket-{interaction.user.display_name}",
                    overwrites=overwrites,
                    category=category
                )
                await channel.send(embed=create_embed("Добро пожаловать!", welcome_message))
                await interaction.response.send_message(
                    embed=create_success_embed("Тикет создан", f"Ваш тикет: {channel.mention}"), ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed("Ошибка", f"Не удалось создать тикет: {str(e)}"), ephemeral=True)

    @app_commands.command(name="ticket-setup", description="Панель создания тикета через кнопку")
    async def ticket_setup(self, interaction: Interaction):
        embed = discord.Embed(title="Создать тикет", description="Нажмите кнопку ниже для создания тикета.")
        view = TicketCreateView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class TicketCreateView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCreateButton())

class TicketCreateButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Создать тикет", style=discord.ButtonStyle.success)

    async def callback(self, interaction: Interaction):
        cog = interaction.client.get_cog("TicketCommands")
        if cog:
            await cog.ticket(interaction)
        else:
            await interaction.response.send_message(
                embed=create_error_embed("Ошибка", "Команда тикетов не найдена."), ephemeral=True)

async def setup(bot):
    await bot.add_cog(TicketCommands(bot))
                ),
                ephemeral=True
            )
            return
        
        # Check if user already has an active ticket
        user_id = interaction.user.id
        if user_id in self.active_forms:
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Form in Progress",
                    "You already have an active form session. Please complete it first."
                ),
                ephemeral=True
            )
            return
        
        try:
            if settings.ticket_type == TicketType.SIMPLE:
                await self._create_simple_ticket(interaction, settings)
            else:  # FORM
                await self._create_form_ticket(interaction, settings)
                
        except Exception as e:
            await interaction.followup.send(
                embed=create_error_embed(
                    "Ticket Creation Failed",
                    f"An error occurred while creating your ticket: {str(e)}"
                ),
                ephemeral=True
            )
    
    async def _create_simple_ticket(self, interaction, settings):
        """Create a simple ticket with a private channel."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            channel, ticket = await self.ticket_service.create_simple_ticket(
                interaction.guild,
                interaction.user,
                settings
            )
            
            # Send welcome message to ticket channel
            welcome_embed = create_embed(
                "🎫 Ticket Created",
                settings.welcome_message
            )
            welcome_embed.add_field(
                name="Ticket Information",
                value=f"**Created by:** {interaction.user.mention}\n"
                      f"**Ticket ID:** {ticket.id}\n"
                      f"**Created:** <t:{int(discord.utils.utcnow().timestamp())}:F>",
                inline=False
            )
            
            # Add close button
            view = TicketCloseView(self.ticket_service)
            await channel.send(embed=welcome_embed, view=view)
            
            # Notify user
            await interaction.followup.send(
                embed=create_success_embed(
                    "Ticket Created",
                    f"Your ticket has been created: {channel.mention}"
                ),
                ephemeral=True
            )
            
        except discord.Forbidden:
            await interaction.followup.send(
                embed=create_error_embed(
                    "Permission Error",
                    "I don't have permission to create channels in this server."
                ),
                ephemeral=True
            )
        except Exception as e:
            raise e
    
    async def _create_form_ticket(self, interaction, settings):
        """Create a form ticket by collecting responses."""
        # Get form questions
        questions = await self.ticket_service.get_form_questions(interaction.guild.id)
        if not questions:
            await interaction.response.send_message(
                embed=create_error_embed(
                    "No Questions Configured",
                    "No form questions have been configured. Please contact an administrator."
                ),
                ephemeral=True
            )
            return
        
        await interaction.response.send_message(
            embed=create_embed(
                "📝 Ticket Form",
                f"I'll ask you {len(questions)} questions. Please answer each one.\n"
                f"You have {Settings.FORM_TIMEOUT_SECONDS // 60} minutes to complete the form."
            ),
            ephemeral=True
        )
        
        # Mark user as having active form
        self.active_forms[interaction.user.id] = True
        
        try:
            responses = []
            
            for question in questions:
                # Ask question
                question_embed = create_embed(
                    f"Question {question.order}/{len(questions)}",
                    question.text
                )
                
                await interaction.followup.send(embed=question_embed, ephemeral=True)
                
                # Wait for response
                def check(m):
                    return (m.author.id == interaction.user.id and 
                           isinstance(m.channel, discord.DMChannel))
                
                try:
                    # Try to get response via DM first
                    dm_sent = await send_dm_safely(
                        interaction.user,
                        create_embed(
                            f"Question {question.order}/{len(questions)}",
                            f"{question.text}\n\n*Please respond to this message.*"
                        )
                    )
                    
                    if dm_sent:
                        response_msg = await self.bot.wait_for(
                            'message',
                            check=check,
                            timeout=Settings.FORM_TIMEOUT_SECONDS
                        )
                    else:
                        # Fallback: wait for response in any channel
                        def fallback_check(m):
                            return m.author.id == interaction.user.id
                        
                        await interaction.followup.send(
                            embed=create_embed(
                                "DM Failed",
                                "I couldn't send you a DM. Please respond here."
                            ),
                            ephemeral=True
                        )
                        
                        response_msg = await self.bot.wait_for(
                            'message',
                            check=fallback_check,
                            timeout=Settings.FORM_TIMEOUT_SECONDS
                        )
                    
                    # Store response
                    responses.append(FormResponse(
                        question_order=question.order,
                        question_text=question.text,
                        response_text=response_msg.content
                    ))
                    
                except asyncio.TimeoutError:
                    await interaction.followup.send(
                        embed=create_error_embed(
                            "Form Timeout",
                            "You took too long to respond. Please start over."
                        ),
                        ephemeral=True
                    )
                    return
            
            # Create ticket and save responses
            ticket = await self.ticket_service.create_form_ticket(
                interaction.guild,
                interaction.user,
                settings,
                responses
            )
            
            # Send responses to target channel
            if settings.target_channel_id:
                target_channel = interaction.guild.get_channel(settings.target_channel_id)
                if target_channel:
                    response_embed = create_form_responses_embed(interaction.user, responses)
                    response_embed.add_field(
                        name="Ticket ID",
                        value=str(ticket.id),
                        inline=True
                    )
                    
                    await target_channel.send(embed=response_embed)
            
            # Notify user
            await interaction.followup.send(
                embed=create_success_embed(
                    "Form Submitted",
                    f"Your ticket form has been submitted successfully!\n**Ticket ID:** {ticket.id}"
                ),
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.followup.send(
                embed=create_error_embed(
                    "Form Error",
                    f"An error occurred while processing your form: {str(e)}"
                ),
                ephemeral=True
            )
        finally:
            # Remove from active forms
            self.active_forms.pop(interaction.user.id, None)
    
    @app_commands.command(
        name="close-ticket",
        description="Close the current ticket (staff only)"
    )
    async def close_ticket_command(self, interaction: discord.Interaction):
        """Close a ticket channel."""
        if not interaction.guild:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "This command can only be used in a server."),
                ephemeral=True
            )
            return
        
        # Check if this is a ticket channel
        ticket = await self.ticket_service.get_ticket_by_channel(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Not a Ticket",
                    "This command can only be used in ticket channels."
                ),
                ephemeral=True
            )
            return
        
        # Check permissions (staff roles or ticket owner)
        is_authorized = await self.ticket_service.is_authorized(interaction.guild, interaction.user)
        ticket_roles = await self.ticket_service.get_ticket_roles(interaction.guild.id)
        
        has_ticket_role = any(
            role.id in [tr.role_id for tr in ticket_roles]
            for role in interaction.user.roles
        )
        
        is_ticket_owner = ticket.user_id == interaction.user.id
        
        if not (is_authorized or has_ticket_role or is_ticket_owner):
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Access Denied",
                    "You don't have permission to close this ticket."
                ),
                ephemeral=True
            )
            return
        
        # Close ticket
        view = TicketCloseConfirmView(self.ticket_service, ticket)
        await interaction.response.send_message(
            embed=create_embed(
                "Close Ticket",
                "Are you sure you want to close this ticket?"
            ),
            view=view,
            ephemeral=True
        )


class TicketCloseView(discord.ui.View):
    """View with close ticket button."""
    
    def __init__(self, ticket_service):
        super().__init__(timeout=None)
        self.ticket_service = ticket_service
    
    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.danger,
        emoji="🔒"
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Close ticket button handler."""
        # Check permissions
        ticket = await self.ticket_service.get_ticket_by_channel(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "Ticket not found."),
                ephemeral=True
            )
            return
        
        is_authorized = await self.ticket_service.is_authorized(interaction.guild, interaction.user)
        ticket_roles = await self.ticket_service.get_ticket_roles(interaction.guild.id)
        
        has_ticket_role = any(
            role.id in [tr.role_id for tr in ticket_roles]
            for role in interaction.user.roles
        )
        
        is_ticket_owner = ticket.user_id == interaction.user.id
        
        if not (is_authorized or has_ticket_role or is_ticket_owner):
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Access Denied",
                    "You don't have permission to close this ticket."
                ),
                ephemeral=True
            )
            return
        
        # Confirm close
        view = TicketCloseConfirmView(self.ticket_service, ticket)
        await interaction.response.send_message(
            embed=create_embed(
                "Close Ticket",
                "Are you sure you want to close this ticket?"
            ),
            view=view,
            ephemeral=True
        )


class TicketCloseConfirmView(discord.ui.View):
    """Confirmation view for closing tickets."""
    
    def __init__(self, ticket_service, ticket):
        super().__init__(timeout=60)
        self.ticket_service = ticket_service
        self.ticket = ticket
    
    @discord.ui.button(
        label="Yes, Close",
        style=discord.ButtonStyle.danger,
        emoji="✅"
    )
    async def confirm_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm ticket closure."""
        try:
            closed_ticket = await self.ticket_service.close_ticket(interaction.channel.id)
            if closed_ticket:
                await interaction.response.send_message(
                    embed=create_success_embed(
                        "Ticket Closed",
                        f"This ticket has been closed by {interaction.user.mention}.\n"
                        "The channel will be deleted in 10 seconds."
                    )
                )
                
                # Delete channel after delay
                await asyncio.sleep(10)
                await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")
            else:
                await interaction.response.send_message(
                    embed=create_error_embed("Error", "Failed to close ticket."),
                    ephemeral=True
                )
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed("Error", f"An error occurred: {str(e)}"),
                ephemeral=True
            )
    
    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.secondary,
        emoji="❌"
    )
    async def cancel_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel ticket closure."""
        await interaction.response.send_message(
            embed=create_embed("Cancelled", "Ticket closure cancelled."),
            ephemeral=True
        )
        self.stop()


async def setup(bot):
    """Setup function for the cog."""
    await bot.add_cog(TicketCommands(bot))
