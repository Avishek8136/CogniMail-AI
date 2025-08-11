"""
Task management panel for the GUI.
Provides interface for follow-ups, overdue items, and reminders.
"""

import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from loguru import logger

from ..tasks import FollowupManager, OverdueDetector, ReminderSystem
from ..database.advanced_db import AdvancedDatabase, FollowUp, Reminder
from .feedback_dialog import FeedbackDialog


class TaskPanel(ctk.CTkFrame):
    """Task management panel widget."""
    
    def __init__(self, parent, **kwargs):
        """Initialize the task panel."""
        super().__init__(parent, **kwargs)
        
        # Initialize services
        self.advanced_db = AdvancedDatabase()
        self.followup_manager = FollowupManager(self.advanced_db)
        self.overdue_detector = OverdueDetector(self.advanced_db)
        self.reminder_system = ReminderSystem(self.advanced_db)
        
        # Current data
        self.followups: List[FollowUp] = []
        self.overdue_items: List[Dict] = []
        self.reminders: List[Reminder] = []
        
        # Setup UI
        self.setup_ui()
        
        # Load initial data
        self.refresh_all_data()
    
    def setup_ui(self):
        """Setup the task panel UI."""
        # Panel title
        title_label = ctk.CTkLabel(
            self,
            text="Task Management",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(pady=(10, 5))
        
        # Refresh button
        refresh_button = ctk.CTkButton(
            self,
            text="Refresh",
            command=self.refresh_all_data,
            width=100
        )
        refresh_button.pack(pady=5)
        
        # Create tabview for different task types
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Follow-ups tab
        self.followups_tab = self.tabview.add("Follow-ups")
        self.setup_followups_tab()
        
        # Overdue tab
        self.overdue_tab = self.tabview.add("Overdue")
        self.setup_overdue_tab()
        
        # Reminders tab
        self.reminders_tab = self.tabview.add("Reminders")
        self.setup_reminders_tab()
        
        # Statistics tab
        self.stats_tab = self.tabview.add("Statistics")
        self.setup_statistics_tab()
    
    def setup_followups_tab(self):
        """Setup the follow-ups tab."""
        # Header with count
        self.followups_header = ctk.CTkLabel(
            self.followups_tab,
            text="Pending Follow-ups (0)",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.followups_header.pack(pady=(10, 5))
        
        # Scrollable frame for follow-ups
        self.followups_frame = ctk.CTkScrollableFrame(
            self.followups_tab,
            height=300
        )
        self.followups_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Controls frame
        followups_controls = ctk.CTkFrame(self.followups_tab)
        followups_controls.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkButton(
            followups_controls,
            text="Mark All Completed",
            command=self.mark_all_followups_completed,
            width=150
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            followups_controls,
            text="Export List",
            command=self.export_followups,
            width=100
        ).pack(side="left", padx=5)
    
    def setup_overdue_tab(self):
        """Setup the overdue items tab."""
        # Header with count and alert
        self.overdue_header = ctk.CTkLabel(
            self.overdue_tab,
            text="Overdue Items (0)",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="orange"
        )
        self.overdue_header.pack(pady=(10, 5))
        
        # Alert frame for critical items
        self.alert_frame = ctk.CTkFrame(self.overdue_tab, fg_color="dark red")
        self.alert_frame.pack(fill="x", padx=10, pady=5)
        
        self.alert_label = ctk.CTkLabel(
            self.alert_frame,
            text="No critical overdue items",
            font=ctk.CTkFont(size=12),
            text_color="white"
        )
        self.alert_label.pack(pady=5)
        
        # Scrollable frame for overdue items
        self.overdue_frame = ctk.CTkScrollableFrame(
            self.overdue_tab,
            height=250
        )
        self.overdue_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Controls frame
        overdue_controls = ctk.CTkFrame(self.overdue_tab)
        overdue_controls.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkButton(
            overdue_controls,
            text="Escalate All",
            command=self.escalate_all_overdue,
            width=120
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            overdue_controls,
            text="Generate Report",
            command=self.generate_overdue_report,
            width=120
        ).pack(side="left", padx=5)
    
    def setup_reminders_tab(self):
        """Setup the reminders tab."""
        # Header with count
        self.reminders_header = ctk.CTkLabel(
            self.reminders_tab,
            text="Active Reminders (0)",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.reminders_header.pack(pady=(10, 5))
        
        # Scrollable frame for reminders
        self.reminders_frame = ctk.CTkScrollableFrame(
            self.reminders_tab,
            height=300
        )
        self.reminders_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Controls frame
        reminders_controls = ctk.CTkFrame(self.reminders_tab)
        reminders_controls.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkButton(
            reminders_controls,
            text="Snooze All (1hr)",
            command=lambda: self.snooze_all_reminders(60),
            width=120
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            reminders_controls,
            text="Dismiss All",
            command=self.dismiss_all_reminders,
            width=100
        ).pack(side="left", padx=5)
    
    def setup_statistics_tab(self):
        """Setup the statistics tab."""
        # Statistics display
        self.stats_frame = ctk.CTkScrollableFrame(
            self.stats_tab,
            height=350
        )
        self.stats_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Refresh stats button
        ctk.CTkButton(
            self.stats_tab,
            text="Refresh Statistics",
            command=self.refresh_statistics,
            width=150
        ).pack(pady=5)
    
    def refresh_all_data(self):
        """Refresh all task data."""
        try:
            # Load follow-ups
            self.followups = self.followup_manager.get_pending_followups()
            
            # Load overdue items
            self.overdue_items = self.overdue_detector.check_overdue_items()
            
            # Load reminders
            self.reminders = self.reminder_system.get_due_reminders()
            
            # Update UI
            self.update_followups_display()
            self.update_overdue_display()
            self.update_reminders_display()
            self.refresh_statistics()
            
            logger.info("Task data refreshed successfully")
            
        except Exception as e:
            logger.error(f"Error refreshing task data: {e}")
            messagebox.showerror("Error", f"Failed to refresh task data: {str(e)}")
    
    def update_followups_display(self):
        """Update the follow-ups display."""
        # Clear existing widgets
        for widget in self.followups_frame.winfo_children():
            widget.destroy()
        
        # Update header
        count = len(self.followups)
        self.followups_header.configure(text=f"Pending Follow-ups ({count})")
        
        if not self.followups:
            no_items_label = ctk.CTkLabel(
                self.followups_frame,
                text="No pending follow-ups",
                text_color="gray"
            )
            no_items_label.pack(pady=20)
            return
        
        # Display follow-ups
        for followup in self.followups:
            self.create_followup_widget(followup)
    
    def create_followup_widget(self, followup: FollowUp):
        """Create a widget for a follow-up item."""
        # Main frame for this follow-up
        item_frame = ctk.CTkFrame(self.followups_frame)
        item_frame.pack(fill="x", padx=5, pady=5)
        
        # Priority indicator
        priority_colors = {
            "low": "green",
            "medium": "orange", 
            "high": "red",
            "urgent": "dark red"
        }
        
        priority_frame = ctk.CTkFrame(
            item_frame, 
            fg_color=priority_colors.get(followup.priority, "gray"),
            width=5
        )
        priority_frame.pack(side="left", fill="y", padx=(5, 10))
        
        # Content frame
        content_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        content_frame.pack(side="left", fill="both", expand=True, padx=5)
        
        # Subject and recipient
        title_text = f"{followup.subject[:50]}..." if len(followup.subject) > 50 else followup.subject
        title_label = ctk.CTkLabel(
            content_frame,
            text=title_text,
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        )
        title_label.pack(fill="x")
        
        recipient_label = ctk.CTkLabel(
            content_frame,
            text=f"To: {followup.recipient}",
            font=ctk.CTkFont(size=10),
            text_color="gray",
            anchor="w"
        )
        recipient_label.pack(fill="x")
        
        # Due date
        if followup.follow_up_date:
            due_date_str = followup.follow_up_date.strftime("%Y-%m-%d %H:%M")
            days_until = (followup.follow_up_date - datetime.now()).days
            
            if days_until < 0:
                due_text = f"Due: {due_date_str} (OVERDUE)"
                due_color = "red"
            elif days_until == 0:
                due_text = f"Due: {due_date_str} (TODAY)"
                due_color = "orange"
            else:
                due_text = f"Due: {due_date_str} ({days_until} days)"
                due_color = "white"
            
            due_label = ctk.CTkLabel(
                content_frame,
                text=due_text,
                font=ctk.CTkFont(size=10),
                text_color=due_color,
                anchor="w"
            )
            due_label.pack(fill="x")
        
        # Notes
        if followup.notes:
            notes_text = followup.notes[:100] + "..." if len(followup.notes) > 100 else followup.notes
            notes_label = ctk.CTkLabel(
                content_frame,
                text=f"Notes: {notes_text}",
                font=ctk.CTkFont(size=9),
                text_color="light gray",
                anchor="w"
            )
            notes_label.pack(fill="x")
        
        # Action buttons
        buttons_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        buttons_frame.pack(side="right", padx=5)
        
        complete_btn = ctk.CTkButton(
            buttons_frame,
            text="Complete",
            command=lambda: self.complete_followup(followup.id),
            width=80,
            height=25,
            font=ctk.CTkFont(size=10)
        )
        complete_btn.pack(pady=2)
        
        snooze_btn = ctk.CTkButton(
            buttons_frame,
            text="Snooze",
            command=lambda: self.snooze_followup_dialog(followup),
            width=80,
            height=25,
            font=ctk.CTkFont(size=10)
        )
        snooze_btn.pack(pady=2)
    
    def update_overdue_display(self):
        """Update the overdue items display."""
        # Clear existing widgets
        for widget in self.overdue_frame.winfo_children():
            widget.destroy()
        
        # Update header and alert
        count = len(self.overdue_items)
        critical_count = sum(1 for item in self.overdue_items if item.get('escalation') == 'critical')
        
        self.overdue_header.configure(text=f"Overdue Items ({count})")
        
        if critical_count > 0:
            self.alert_label.configure(
                text=f"⚠️ {critical_count} CRITICAL overdue items need immediate attention!",
                text_color="white"
            )
            self.alert_frame.configure(fg_color="dark red")
        else:
            self.alert_label.configure(
                text="No critical overdue items",
                text_color="light gray"
            )
            self.alert_frame.configure(fg_color="gray")
        
        if not self.overdue_items:
            no_items_label = ctk.CTkLabel(
                self.overdue_frame,
                text="No overdue items! 🎉",
                text_color="green",
                font=ctk.CTkFont(size=14)
            )
            no_items_label.pack(pady=20)
            return
        
        # Display overdue items
        for item in self.overdue_items:
            self.create_overdue_widget(item)
    
    def create_overdue_widget(self, item: Dict):
        """Create a widget for an overdue item."""
        # Main frame
        item_frame = ctk.CTkFrame(self.overdue_frame)
        item_frame.pack(fill="x", padx=5, pady=5)
        
        # Escalation indicator
        escalation_colors = {
            "low": "green",
            "medium": "orange",
            "high": "red", 
            "critical": "dark red"
        }
        
        escalation_frame = ctk.CTkFrame(
            item_frame,
            fg_color=escalation_colors.get(item.get('escalation'), "gray"),
            width=5
        )
        escalation_frame.pack(side="left", fill="y", padx=(5, 10))
        
        # Content frame
        content_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        content_frame.pack(side="left", fill="both", expand=True, padx=5)
        
        # Title
        title_label = ctk.CTkLabel(
            content_frame,
            text=item.get('title', 'Unknown Item'),
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        )
        title_label.pack(fill="x")
        
        # Overdue info
        overdue_days = item.get('overdue_days', 0)
        escalation = item.get('escalation', 'low').upper()
        
        overdue_label = ctk.CTkLabel(
            content_frame,
            text=f"Overdue: {overdue_days} days | Escalation: {escalation}",
            font=ctk.CTkFont(size=10),
            text_color="orange",
            anchor="w"
        )
        overdue_label.pack(fill="x")
        
        # Description
        if item.get('description'):
            desc_text = item['description'][:80] + "..." if len(item['description']) > 80 else item['description']
            desc_label = ctk.CTkLabel(
                content_frame,
                text=desc_text,
                font=ctk.CTkFont(size=9),
                text_color="light gray",
                anchor="w"
            )
            desc_label.pack(fill="x")
        
        # Action buttons
        buttons_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        buttons_frame.pack(side="right", padx=5)
        
        resolve_btn = ctk.CTkButton(
            buttons_frame,
            text="Resolve",
            command=lambda: self.resolve_overdue_item(item),
            width=80,
            height=25,
            font=ctk.CTkFont(size=10)
        )
        resolve_btn.pack(pady=2)
        
        escalate_btn = ctk.CTkButton(
            buttons_frame,
            text="Escalate",
            command=lambda: self.escalate_overdue_item(item),
            width=80,
            height=25,
            font=ctk.CTkFont(size=10)
        )
        escalate_btn.pack(pady=2)
    
    def update_reminders_display(self):
        """Update the reminders display."""
        # Clear existing widgets
        for widget in self.reminders_frame.winfo_children():
            widget.destroy()
        
        # Update header
        count = len(self.reminders)
        self.reminders_header.configure(text=f"Active Reminders ({count})")
        
        if not self.reminders:
            no_items_label = ctk.CTkLabel(
                self.reminders_frame,
                text="No active reminders",
                text_color="gray"
            )
            no_items_label.pack(pady=20)
            return
        
        # Display reminders
        for reminder in self.reminders:
            self.create_reminder_widget(reminder)
    
    def create_reminder_widget(self, reminder: Reminder):
        """Create a widget for a reminder."""
        # Main frame
        item_frame = ctk.CTkFrame(self.reminders_frame)
        item_frame.pack(fill="x", padx=5, pady=5)
        
        # Type indicator
        type_colors = {
            "meeting": "blue",
            "deadline": "red",
            "followup": "orange",
            "important_email": "purple",
            "custom": "gray"
        }
        
        type_frame = ctk.CTkFrame(
            item_frame,
            fg_color=type_colors.get(reminder.reminder_type, "gray"),
            width=5
        )
        type_frame.pack(side="left", fill="y", padx=(5, 10))
        
        # Content frame
        content_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        content_frame.pack(side="left", fill="both", expand=True, padx=5)
        
        # Title
        title_label = ctk.CTkLabel(
            content_frame,
            text=reminder.title,
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        )
        title_label.pack(fill="x")
        
        # Type and time
        if reminder.reminder_time:
            time_str = reminder.reminder_time.strftime("%Y-%m-%d %H:%M")
            type_label = ctk.CTkLabel(
                content_frame,
                text=f"Type: {reminder.reminder_type.title()} | Due: {time_str}",
                font=ctk.CTkFont(size=10),
                text_color="gray",
                anchor="w"
            )
            type_label.pack(fill="x")
        
        # Description
        if reminder.description:
            desc_text = reminder.description[:100] + "..." if len(reminder.description) > 100 else reminder.description
            desc_label = ctk.CTkLabel(
                content_frame,
                text=desc_text,
                font=ctk.CTkFont(size=9),
                text_color="light gray",
                anchor="w"
            )
            desc_label.pack(fill="x")
        
        # Action buttons
        buttons_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        buttons_frame.pack(side="right", padx=5)
        
        dismiss_btn = ctk.CTkButton(
            buttons_frame,
            text="Dismiss",
            command=lambda: self.dismiss_reminder(reminder.id),
            width=80,
            height=25,
            font=ctk.CTkFont(size=10)
        )
        dismiss_btn.pack(pady=2)
        
        snooze_btn = ctk.CTkButton(
            buttons_frame,
            text="Snooze",
            command=lambda: self.snooze_reminder_dialog(reminder),
            width=80,
            height=25,
            font=ctk.CTkFont(size=10)
        )
        snooze_btn.pack(pady=2)
    
    def refresh_statistics(self):
        """Refresh the statistics display."""
        # Clear existing widgets
        for widget in self.stats_frame.winfo_children():
            widget.destroy()
        
        try:
            # Get statistics from all services
            followup_stats = self.followup_manager.get_statistics()
            overdue_stats = self.overdue_detector.get_statistics()
            reminder_stats = self.reminder_system.get_statistics()
            
            # Display statistics
            self.create_stats_section("Follow-up Statistics", followup_stats)
            self.create_stats_section("Overdue Statistics", overdue_stats)
            self.create_stats_section("Reminder Statistics", reminder_stats)
            
        except Exception as e:
            logger.error(f"Error refreshing statistics: {e}")
            error_label = ctk.CTkLabel(
                self.stats_frame,
                text=f"Error loading statistics: {str(e)}",
                text_color="red"
            )
            error_label.pack(pady=20)
    
    def create_stats_section(self, title: str, stats: Dict):
        """Create a statistics section."""
        # Section title
        title_label = ctk.CTkLabel(
            self.stats_frame,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Stats frame
        section_frame = ctk.CTkFrame(self.stats_frame)
        section_frame.pack(fill="x", padx=10, pady=5)
        
        # Display stats
        for key, value in stats.items():
            if isinstance(value, dict):
                # Nested statistics
                sub_title = ctk.CTkLabel(
                    section_frame,
                    text=f"{key.replace('_', ' ').title()}:",
                    font=ctk.CTkFont(size=12, weight="bold")
                )
                sub_title.pack(anchor="w", padx=10, pady=(5, 2))
                
                for sub_key, sub_value in value.items():
                    stat_label = ctk.CTkLabel(
                        section_frame,
                        text=f"  {sub_key.replace('_', ' ').title()}: {sub_value}",
                        font=ctk.CTkFont(size=10)
                    )
                    stat_label.pack(anchor="w", padx=20, pady=1)
            else:
                # Simple statistics
                stat_label = ctk.CTkLabel(
                    section_frame,
                    text=f"{key.replace('_', ' ').title()}: {value}",
                    font=ctk.CTkFont(size=11)
                )
                stat_label.pack(anchor="w", padx=10, pady=2)
    
    # Action methods
    def complete_followup(self, followup_id: int):
        """Mark a follow-up as completed."""
        try:
            success = self.followup_manager.complete_followup(followup_id)
            if success:
                messagebox.showinfo("Success", "Follow-up marked as completed!")
                self.refresh_all_data()
            else:
                messagebox.showerror("Error", "Failed to complete follow-up.")
        except Exception as e:
            logger.error(f"Error completing follow-up: {e}")
            messagebox.showerror("Error", f"Failed to complete follow-up: {str(e)}")
    
    def snooze_followup_dialog(self, followup: FollowUp):
        """Show snooze dialog for follow-up."""
        dialog = ctk.CTkInputDialog(
            text="Enter days to snooze:",
            title="Snooze Follow-up"
        )
        days = dialog.get_input()
        
        if days and days.isdigit():
            try:
                success = self.followup_manager.snooze_followup(followup.id, int(days))
                if success:
                    messagebox.showinfo("Success", f"Follow-up snoozed for {days} days!")
                    self.refresh_all_data()
                else:
                    messagebox.showerror("Error", "Failed to snooze follow-up.")
            except Exception as e:
                logger.error(f"Error snoozing follow-up: {e}")
                messagebox.showerror("Error", f"Failed to snooze follow-up: {str(e)}")
    
    def resolve_overdue_item(self, item: Dict):
        """Resolve an overdue item."""
        try:
            if item.get('type') == 'followup' and item.get('id'):
                success = self.followup_manager.complete_followup(item['id'])
                if success:
                    messagebox.showinfo("Success", "Overdue item resolved!")
                    self.refresh_all_data()
                else:
                    messagebox.showerror("Error", "Failed to resolve overdue item.")
            else:
                messagebox.showinfo("Info", "Item marked as resolved (manual tracking).")
                self.refresh_all_data()
        except Exception as e:
            logger.error(f"Error resolving overdue item: {e}")
            messagebox.showerror("Error", f"Failed to resolve item: {str(e)}")
    
    def escalate_overdue_item(self, item: Dict):
        """Escalate an overdue item."""
        try:
            success = self.overdue_detector.escalate_overdue_item(item)
            if success:
                messagebox.showinfo("Success", "Item escalated successfully!")
                self.refresh_all_data()
            else:
                messagebox.showinfo("Info", "Item already at maximum escalation level.")
        except Exception as e:
            logger.error(f"Error escalating overdue item: {e}")
            messagebox.showerror("Error", f"Failed to escalate item: {str(e)}")
    
    def dismiss_reminder(self, reminder_id: int):
        """Dismiss a reminder."""
        try:
            success = self.reminder_system.dismiss_reminder(reminder_id)
            if success:
                messagebox.showinfo("Success", "Reminder dismissed!")
                self.refresh_all_data()
            else:
                messagebox.showerror("Error", "Failed to dismiss reminder.")
        except Exception as e:
            logger.error(f"Error dismissing reminder: {e}")
            messagebox.showerror("Error", f"Failed to dismiss reminder: {str(e)}")
    
    def snooze_reminder_dialog(self, reminder: Reminder):
        """Show snooze dialog for reminder."""
        # Get smart snooze suggestions
        suggestions = self.reminder_system.get_smart_snooze_suggestions(reminder)
        
        # Create simple dialog for now
        dialog = ctk.CTkInputDialog(
            text="Enter minutes to snooze:",
            title="Snooze Reminder"
        )
        minutes = dialog.get_input()
        
        if minutes and minutes.isdigit():
            try:
                success = self.reminder_system.snooze_reminder(reminder.id, int(minutes))
                if success:
                    messagebox.showinfo("Success", f"Reminder snoozed for {minutes} minutes!")
                    self.refresh_all_data()
                else:
                    messagebox.showerror("Error", "Failed to snooze reminder.")
            except Exception as e:
                logger.error(f"Error snoozing reminder: {e}")
                messagebox.showerror("Error", f"Failed to snooze reminder: {str(e)}")
    
    # Bulk action methods
    def mark_all_followups_completed(self):
        """Mark all follow-ups as completed."""
        if not self.followups:
            messagebox.showinfo("Info", "No follow-ups to complete.")
            return
        
        result = messagebox.askyesno(
            "Confirm", 
            f"Mark all {len(self.followups)} follow-ups as completed?"
        )
        
        if result:
            completed_count = 0
            for followup in self.followups:
                try:
                    if self.followup_manager.complete_followup(followup.id):
                        completed_count += 1
                except Exception as e:
                    logger.error(f"Error completing follow-up {followup.id}: {e}")
            
            messagebox.showinfo("Success", f"Completed {completed_count} follow-ups!")
            self.refresh_all_data()
    
    def escalate_all_overdue(self):
        """Escalate all overdue items."""
        if not self.overdue_items:
            messagebox.showinfo("Info", "No overdue items to escalate.")
            return
        
        escalated_count = 0
        for item in self.overdue_items:
            try:
                if self.overdue_detector.escalate_overdue_item(item):
                    escalated_count += 1
            except Exception as e:
                logger.error(f"Error escalating item: {e}")
        
        messagebox.showinfo("Success", f"Escalated {escalated_count} items!")
        self.refresh_all_data()
    
    def snooze_all_reminders(self, minutes: int):
        """Snooze all reminders."""
        if not self.reminders:
            messagebox.showinfo("Info", "No reminders to snooze.")
            return
        
        snoozed_count = 0
        for reminder in self.reminders:
            try:
                if self.reminder_system.snooze_reminder(reminder.id, minutes):
                    snoozed_count += 1
            except Exception as e:
                logger.error(f"Error snoozing reminder {reminder.id}: {e}")
        
        messagebox.showinfo("Success", f"Snoozed {snoozed_count} reminders!")
        self.refresh_all_data()
    
    def dismiss_all_reminders(self):
        """Dismiss all reminders."""
        if not self.reminders:
            messagebox.showinfo("Info", "No reminders to dismiss.")
            return
        
        result = messagebox.askyesno(
            "Confirm",
            f"Dismiss all {len(self.reminders)} reminders?"
        )
        
        if result:
            dismissed_count = 0
            for reminder in self.reminders:
                try:
                    if self.reminder_system.dismiss_reminder(reminder.id):
                        dismissed_count += 1
                except Exception as e:
                    logger.error(f"Error dismissing reminder {reminder.id}: {e}")
            
            messagebox.showinfo("Success", f"Dismissed {dismissed_count} reminders!")
            self.refresh_all_data()
    
    def export_followups(self):
        """Export follow-ups list."""
        try:
            # Simple export to show the concept
            export_data = []
            for followup in self.followups:
                export_data.append({
                    'Subject': followup.subject,
                    'Recipient': followup.recipient,
                    'Due Date': followup.follow_up_date.isoformat() if followup.follow_up_date else '',
                    'Priority': followup.priority,
                    'Status': followup.status,
                    'Notes': followup.notes
                })
            
            # For now, just show count
            messagebox.showinfo("Export", f"Would export {len(export_data)} follow-ups to CSV")
            
        except Exception as e:
            logger.error(f"Error exporting follow-ups: {e}")
            messagebox.showerror("Error", f"Failed to export follow-ups: {str(e)}")
    
    def generate_overdue_report(self):
        """Generate overdue items report."""
        try:
            overdue_summary = self.overdue_detector.get_overdue_summary()
            
            report = f"""Overdue Items Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

Total Overdue Items: {overdue_summary['total_overdue']}
Critical Items: {overdue_summary['critical_items']}
Need Immediate Attention: {overdue_summary['needs_immediate_attention']}
Average Days Overdue: {overdue_summary['average_overdue_days']}

Escalation Breakdown:
- Low: {overdue_summary['escalation_breakdown']['low']}
- Medium: {overdue_summary['escalation_breakdown']['medium']}
- High: {overdue_summary['escalation_breakdown']['high']}
- Critical: {overdue_summary['escalation_breakdown']['critical']}
"""
            
            # Show report in a dialog
            dialog = ctk.CTkToplevel()
            dialog.title("Overdue Report")
            dialog.geometry("400x500")
            
            report_text = ctk.CTkTextbox(dialog, height=400, width=350)
            report_text.pack(padx=20, pady=20)
            report_text.insert("0.0", report)
            
            close_btn = ctk.CTkButton(dialog, text="Close", command=dialog.destroy)
            close_btn.pack(pady=10)
            
        except Exception as e:
            logger.error(f"Error generating overdue report: {e}")
            messagebox.showerror("Error", f"Failed to generate report: {str(e)}")
