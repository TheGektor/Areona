"""Ticket commands for users and staff."""

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from typing import List
from ..domain.entities import TicketType, FormResponse
from ..utils.helpers import (
    create_success_embed, create_error_embed, create_embed,
    create_form_responses_embed, send_dm_safely
)
from ..config.settings import Settings


class TicketCommands(commands.Cog):
    """Commands for ticket creation and management."""
    
    def __init__(self, bot):
        self.bot = bot
        self.ticket_service = bot.ticket_service
        self.active_forms = {}  # Track active form sessions
    
    @app_commands.command(
        name="ticket",
        description="Create a new ticket"
    )
    async def create_ticket(self, interaction: discord.Interaction):
        """Create a new ticket."""
        if not interaction.guild:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "This command can only be used in a server."),
                ephemeral=True
            )
            return
        
        # Get guild settings
        settings = await self.ticket_service.get_guild_settings(interaction.guild.id)
        if not settings:
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Not Configured",
                    "The ticket system has not been configured for this server. "
                    "Please contact an administrator."
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
