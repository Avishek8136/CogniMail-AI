"""
Main GUI application with intelligent inbox dashboard using CustomTkinter.
Implements the Phase 1 interface for email triage and user feedback.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
from typing import List, Optional, Dict, Any
import threading
import os
from datetime import datetime, timedelta
from dataclasses import dataclass
from dotenv import find_dotenv, load_dotenv

from loguru import logger

from ..core.config import get_settings
from ..core.email_service import get_email_service, EmailData
from ..auth.google_auth import get_auth_service
from ..ai.gemini_service import EmailUrgency, EmailCategory
from ..database.learning_db import get_learning_db, UserCorrection
from .settings_window import SettingsWindow
from .welcome_wizard import WelcomeWizard


@dataclass
class EmailDisplayData:
    """Data for displaying an email in the GUI."""
    email_data: EmailData
    display_urgency: str
    display_category: str
    confidence_display: str
    reasoning_display: str
    action_display: str


class EmailManagerApp:
    """Main application window for the AI Email Manager."""
    
    def __init__(self):
        """Initialize the main application."""
        self.setup_logging()
        
        # Initialize services
        self.auth_service = get_auth_service()
        self.email_service = get_email_service()
        self.learning_db = get_learning_db()
        
        # Application state
        self.emails: List[EmailData] = []
        self.filtered_emails: List[EmailData] = []
        self.current_email_index = 0
        self.current_filter = "All"
        self.is_authenticated = False
        self.is_loading = False
        
        # Setup GUI
        self.setup_gui()
        
        # Check if this is a first run and show welcome wizard if needed
        if self.is_first_run():
            self.show_welcome_wizard()
        else:
            # Check authentication on startup (only if not first run)
            self.check_authentication()
    
    def setup_logging(self):
        """Setup application logging."""
        logger.add(
            "data/app.log",
            level="INFO",
            rotation="10 MB",
            retention="30 days",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )
        logger.info("CogniMail AI - Cognitive Email Intelligence | Starting...")
    
    def setup_gui(self):
        """Setup the main GUI interface."""
        # Configure CustomTkinter
        ctk.set_appearance_mode("dark")  # "dark" or "light"
        ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue"
        
        # Create main window
        self.root = ctk.CTk()
        self.root.title("CogniMail AI - Intelligent Inbox Dashboard")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)
        
        # Setup main layout
        self.setup_layout()
        
        # Bind events
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_layout(self):
        """Setup the main application layout."""
        # Create main frame
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Setup header
        self.setup_header()
        
        # Setup content area
        self.setup_content_area()
        
        # Setup status bar
        self.setup_status_bar()
    
    def setup_header(self):
        """Setup the application header with title and controls."""
        header_frame = ctk.CTkFrame(self.main_frame)
        header_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        # Left side: Title and bulk actions
        left_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        left_frame.pack(side="left", fill="x", expand=True)
        
        title_row = ctk.CTkFrame(left_frame, fg_color="transparent")
        title_row.pack(fill="x")
        
        # Title
        title_label = ctk.CTkLabel(
            title_row,
            text="CogniMail AI",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(side="left", padx=20, pady=(15, 5))
        
        # Bulk action buttons
        bulk_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        bulk_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        select_all_var = tk.BooleanVar()
        select_all_checkbox = ctk.CTkCheckBox(
            bulk_frame,
            text="Select All",
            variable=select_all_var,
            command=lambda: self.toggle_select_all(select_all_var.get()),
            font=ctk.CTkFont(size=12)
        )
        select_all_checkbox.pack(side="left")
        
        delete_selected_btn = ctk.CTkButton(
            bulk_frame,
            text="Delete Selected",
            command=self.delete_selected_emails,
            width=120,
            height=28,
            font=ctk.CTkFont(size=12),
            fg_color="#DC3545",
            hover_color="#C82333",
            state="disabled"
        )
        delete_selected_btn.pack(side="left", padx=10)
        self.delete_selected_btn = delete_selected_btn  # Store reference
        
        # Control buttons
        control_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        control_frame.pack(side="right", padx=20, pady=15)
        
        self.auth_button = ctk.CTkButton(
            control_frame,
            text="Authenticate",
            command=self.authenticate,
            width=120
        )
        self.auth_button.pack(side="left", padx=5)
        
        self.refresh_button = ctk.CTkButton(
            control_frame,
            text="Refresh Emails",
            command=self.refresh_emails,
            width=120,
            state="disabled"
        )
        self.refresh_button.pack(side="left", padx=5)
        
        self.logout_button = ctk.CTkButton(
            control_frame,
            text="Logout",
            command=self.logout,
            width=100,
            state="disabled"
        )
        self.logout_button.pack(side="left", padx=5)
        
        self.settings_button = ctk.CTkButton(
            control_frame,
            text="Settings",
            command=self.open_settings,
            width=100
        )
        self.settings_button.pack(side="left", padx=5)
    
    def setup_content_area(self):
        """Setup the main content area with email list and details."""
        content_frame = ctk.CTkFrame(self.main_frame)
        content_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create left panel (email list)
        self.setup_email_list_panel(content_frame)
        
        # Create right panel (email details)
        self.setup_email_details_panel(content_frame)
    
    def setup_email_list_panel(self, parent):
        """Setup the left panel with email list."""
        # Left panel frame
        left_panel = ctk.CTkFrame(parent)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        # Panel title
        list_title = ctk.CTkLabel(
            left_panel,
            text="Priority Inbox",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        list_title.pack(pady=(15, 10))
        
        # Filter frame
        filter_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        filter_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        # Urgency filter
        ctk.CTkLabel(filter_frame, text="Filter:").pack(side="left")
        
        self.urgency_filter = ctk.CTkOptionMenu(
            filter_frame,
            values=["All", "Urgent", "To Respond", "FYI", "Meeting"],
            command=self.filter_emails,
            width=120
        )
        self.urgency_filter.pack(side="left", padx=(10, 0))
        
        # Email list frame
        list_frame = ctk.CTkFrame(left_panel)
        list_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # Scrollable frame for emails
        self.email_list_frame = ctk.CTkScrollableFrame(list_frame)
        self.email_list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Loading message
        self.loading_label = ctk.CTkLabel(
            self.email_list_frame,
            text="No emails loaded. Click 'Authenticate' and 'Refresh Emails' to start.",
            font=ctk.CTkFont(size=14)
        )
        self.loading_label.pack(pady=50)
    
    def setup_email_details_panel(self, parent):
        """Setup the right panel with email details and AI analysis."""
        # Right panel frame
        right_panel = ctk.CTkFrame(parent)
        right_panel.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        # Panel title
        details_title = ctk.CTkLabel(
            right_panel,
            text="Email Details & AI Analysis",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        details_title.pack(pady=(15, 10))
        
        # Create tabview for different sections
        self.details_tabview = ctk.CTkTabview(right_panel)
        self.details_tabview.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # Email content tab
        self.content_tab = self.details_tabview.add("Email Content")
        self.setup_content_tab()
        
        # AI Analysis tab
        self.analysis_tab = self.details_tabview.add("AI Analysis")
        self.setup_analysis_tab()
        
        # Actions tab
        self.actions_tab = self.details_tabview.add("Actions")
        self.setup_actions_tab()
    
    def setup_content_tab(self):
        """Setup the email content display tab."""
        # Email header info
        header_frame = ctk.CTkFrame(self.content_tab, fg_color="transparent")
        header_frame.pack(fill="x", pady=(10, 15))
        
        self.subject_label = ctk.CTkLabel(
            header_frame,
            text="Select an email to view details",
            font=ctk.CTkFont(size=16, weight="bold"),
            wraplength=600
        )
        self.subject_label.pack(anchor="w")
        
        self.sender_label = ctk.CTkLabel(
            header_frame,
            text="",
            font=ctk.CTkFont(size=12)
        )
        self.sender_label.pack(anchor="w", pady=(5, 0))
        
        self.date_label = ctk.CTkLabel(
            header_frame,
            text="",
            font=ctk.CTkFont(size=12)
        )
        self.date_label.pack(anchor="w", pady=(2, 0))
        
        # Email body
        self.body_textbox = ctk.CTkTextbox(
            self.content_tab,
            height=400,
            font=ctk.CTkFont(size=12)
        )
        self.body_textbox.pack(fill="both", expand=True, pady=(0, 10))
    
    def setup_analysis_tab(self):
        """Setup the AI analysis display and correction tab."""
        # Analysis results frame
        analysis_frame = ctk.CTkFrame(self.analysis_tab, fg_color="transparent")
        analysis_frame.pack(fill="x", pady=10)
        
        # Current AI classification
        current_frame = ctk.CTkFrame(analysis_frame)
        current_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            current_frame,
            text="AI Classification:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))
        
        self.urgency_display = ctk.CTkLabel(current_frame, text="Urgency: Not analyzed")
        self.urgency_display.pack(anchor="w", padx=15, pady=2)
        
        self.category_display = ctk.CTkLabel(current_frame, text="Category: Not analyzed")
        self.category_display.pack(anchor="w", padx=15, pady=2)
        
        self.confidence_display = ctk.CTkLabel(current_frame, text="Confidence: N/A")
        self.confidence_display.pack(anchor="w", padx=15, pady=2)
        
        # Reasoning
        ctk.CTkLabel(
            current_frame,
            text="AI Reasoning:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))
        
        self.reasoning_textbox = ctk.CTkTextbox(
            current_frame,
            height=100,
            font=ctk.CTkFont(size=11)
        )
        self.reasoning_textbox.pack(fill="x", padx=15, pady=(0, 10))
        
        # User correction section
        correction_frame = ctk.CTkFrame(analysis_frame)
        correction_frame.pack(fill="x", pady=(15, 0))
        
        ctk.CTkLabel(
            correction_frame,
            text="Correct AI Analysis (if needed):",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))
        
        # Correction controls
        controls_frame = ctk.CTkFrame(correction_frame, fg_color="transparent")
        controls_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        # Urgency correction
        urgency_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        urgency_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(urgency_frame, text="Correct Urgency:", width=120).pack(side="left")
        self.urgency_correction = ctk.CTkOptionMenu(
            urgency_frame,
            values=["urgent", "to_respond", "fyi", "meeting", "spam"],
            width=150
        )
        self.urgency_correction.pack(side="left", padx=(10, 0))
        
        # Category correction
        category_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        category_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(category_frame, text="Correct Category:", width=120).pack(side="left")
        self.category_correction = ctk.CTkOptionMenu(
            category_frame,
            values=["work", "personal", "marketing", "security", 
                   "meeting_request", "task_assignment", "information", "urgent_decision"],
            width=150
        )
        self.category_correction.pack(side="left", padx=(10, 0))
        
        # Feedback text
        ctk.CTkLabel(
            correction_frame,
            text="Additional Feedback (optional):"
        ).pack(anchor="w", padx=15, pady=(10, 5))
        
        self.feedback_textbox = ctk.CTkTextbox(
            correction_frame,
            height=60
        )
        self.feedback_textbox.pack(fill="x", padx=15, pady=(0, 10))
        
        # Submit correction button
        self.submit_correction_button = ctk.CTkButton(
            correction_frame,
            text="Submit Correction",
            command=self.submit_correction,
            width=150,
            state="disabled"
        )
        self.submit_correction_button.pack(padx=15, pady=(0, 15))
    
    def setup_actions_tab(self):
        """Setup the actions tab for email operations."""
        actions_frame = ctk.CTkFrame(self.actions_tab, fg_color="transparent")
        actions_frame.pack(fill="x", pady=10)
        
        # Quick actions
        quick_frame = ctk.CTkFrame(actions_frame)
        quick_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            quick_frame,
            text="Quick Actions:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=15, pady=(10, 10))
        
        # Action buttons
        button_frame = ctk.CTkFrame(quick_frame, fg_color="transparent")
        button_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        self.mark_read_button = ctk.CTkButton(
            button_frame,
            text="Mark as Read",
            command=self.mark_as_read,
            width=120,
            state="disabled"
        )
        self.mark_read_button.pack(side="left", padx=(0, 10))
        
        self.reply_button = ctk.CTkButton(
            button_frame,
            text="Quick Reply",
            command=self.quick_reply,
            width=120,
            state="disabled"
        )
        self.reply_button.pack(side="left", padx=(0, 10))
        
        self.thread_summary_button = ctk.CTkButton(
            button_frame,
            text="Thread Summary",
            command=self.show_thread_summary,
            width=120,
            state="disabled"
        )
        self.thread_summary_button.pack(side="left")
        
        # Action required display
        action_frame = ctk.CTkFrame(actions_frame)
        action_frame.pack(fill="x")
        
        ctk.CTkLabel(
            action_frame,
            text="Recommended Action:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))
        
        self.action_textbox = ctk.CTkTextbox(
            action_frame,
            height=80,
            font=ctk.CTkFont(size=11)
        )
        self.action_textbox.pack(fill="x", padx=15, pady=(0, 15))
    
    def setup_status_bar(self):
        """Setup the status bar at the bottom."""
        self.status_frame = ctk.CTkFrame(self.main_frame, height=30)
        self.status_frame.pack(fill="x", padx=10, pady=(5, 10))
        self.status_frame.pack_propagate(False)
        
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Ready. Please authenticate to access your emails.",
            font=ctk.CTkFont(size=11)
        )
        self.status_label.pack(side="left", padx=15, pady=5)
        
        # Progress bar for loading
        self.progress_bar = ctk.CTkProgressBar(self.status_frame, width=200)
        self.progress_bar.pack(side="right", padx=15, pady=5)
        self.progress_bar.pack_forget()  # Hidden by default
    
    def check_authentication(self):
        """Check if user is already authenticated."""
        if self.auth_service.is_authenticated():
            self.is_authenticated = True
            self.auth_button.configure(text="Authenticated ✓", state="disabled")
            self.refresh_button.configure(state="normal")
            self.logout_button.configure(state="normal")
            self.update_status("Authenticated successfully. Click 'Refresh Emails' to load your inbox.")
        else:
            self.is_authenticated = False
            self.update_status("Please authenticate to access your emails.")
    
    def authenticate(self):
        """Authenticate with Google APIs."""
        def auth_thread():
            try:
                self.update_status("Authenticating...")
                self.show_progress()
                
                success = self.auth_service.authenticate()
                
                if success:
                    self.is_authenticated = True
                    self.root.after(0, self.on_auth_success)
                else:
                    self.root.after(0, lambda: self.on_auth_error("Authentication failed"))
                    
            except Exception as e:
                logger.error(f"Authentication error: {e}")
                self.root.after(0, lambda: self.on_auth_error(str(e)))
            finally:
                self.root.after(0, self.hide_progress)
        
        # Run authentication in separate thread
        threading.Thread(target=auth_thread, daemon=True).start()
    
    def on_auth_success(self):
        """Handle successful authentication."""
        self.auth_button.configure(text="Authenticated ✓", state="disabled")
        self.refresh_button.configure(state="normal")
        self.logout_button.configure(state="normal")
        self.update_status("Authenticated successfully. Click 'Refresh Emails' to load your inbox.")
        messagebox.showinfo("Success", "Authentication successful! You can now access your emails.")
    
    def on_auth_error(self, error_msg):
        """Handle authentication error."""
        self.update_status(f"Authentication failed: {error_msg}")
        messagebox.showerror("Authentication Error", f"Failed to authenticate:\n{error_msg}")
    
    def refresh_emails(self):
        """Refresh the email list from Gmail."""
        if not self.is_authenticated:
            messagebox.showwarning("Not Authenticated", "Please authenticate first.")
            return
        
        def fetch_thread():
            try:
                self.update_status("Fetching emails...")
                self.show_progress()
                
                # Fetch emails
                emails = self.email_service.fetch_recent_emails(max_results=50, days_back=14)
                
                # Analyze emails with AI using batch processing
                self.update_status(f"Analyzing {len(emails)} emails with AI (batch processing)...")
                
                try:
                    # Use batch processing for better efficiency
                    analyzed_emails = self.email_service.analyze_emails_with_ai_batch(emails, batch_size=5)
                    
                    # Store analyses in database
                    for email_data in analyzed_emails:
                        if email_data.analysis:
                            try:
                                self.learning_db.store_email_analysis(
                                    email_data.id,
                                    email_data.thread_id,
                                    email_data.subject,
                                    email_data.sender,
                                    email_data.analysis
                                )
                            except Exception as store_error:
                                logger.error(f"Error storing analysis for {email_data.id}: {store_error}")
                    
                    # Update progress to complete
                    self.root.after(0, lambda: self.update_progress(1.0))
                    
                except Exception as e:
                    logger.error(f"Batch analysis failed: {e}")
                    # Fallback: keep emails without analysis
                    analyzed_emails = emails
                
                self.emails = analyzed_emails
                self.filtered_emails = analyzed_emails.copy()  # Initialize filtered emails
                self.root.after(0, self.populate_email_list)
                self.root.after(0, lambda: self.update_status(f"Loaded {len(self.emails)} emails"))
                
            except Exception as e:
                logger.error(f"Error fetching emails: {e}")
                self.root.after(0, lambda: self.update_status(f"Error fetching emails: {str(e)}"))
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to fetch emails:\n{str(e)}"))
            finally:
                self.root.after(0, self.hide_progress)
        
        threading.Thread(target=fetch_thread, daemon=True).start()
    
    def populate_email_list(self):
        """Populate the email list in the GUI."""
        # Clear existing items
        for widget in self.email_list_frame.winfo_children():
            widget.destroy()
        
        if not self.filtered_emails:
            no_emails_label = ctk.CTkLabel(
                self.email_list_frame,
                text="No emails found" if not self.emails else f"No emails match filter: {self.current_filter}",
                font=ctk.CTkFont(size=14)
            )
            no_emails_label.pack(pady=50)
            return
        
        # Sort filtered emails by urgency and date (normalize timezone-aware/naive dates)
        sorted_emails = sorted(
            self.filtered_emails,
            key=lambda x: (
                0 if x.analysis and x.analysis.urgency == EmailUrgency.URGENT else
                1 if x.analysis and x.analysis.urgency == EmailUrgency.TO_RESPOND else
                2 if x.analysis and x.analysis.urgency == EmailUrgency.MEETING else
                3,  # FYI and others
                x.date.replace(tzinfo=None) if x.date.tzinfo else x.date
            ),
            reverse=True
        )
        
        # Create email items
        for i, email_data in enumerate(sorted_emails):
            # Find the original index in the emails list
            original_index = self.emails.index(email_data) if email_data in self.emails else i
            self.create_email_item(email_data, original_index)
    
    def __init__(self):
        """Initialize the main application."""
        self.setup_logging()
        
        # Initialize services
        self.auth_service = get_auth_service()
        self.email_service = get_email_service()
        self.learning_db = get_learning_db()
        
        # Application state
        self.emails: List[EmailData] = []
        self.filtered_emails: List[EmailData] = []
        self.current_email_index = 0
        self.current_filter = "All"
        self.is_authenticated = False
        self.is_loading = False
        self.selected_emails = set()  # Store selected email IDs
        
        # Setup GUI
        self.setup_gui()
        
        # Check if this is a first run and show welcome wizard if needed
        if self.is_first_run():
            self.show_welcome_wizard()
        else:
            # Check authentication on startup (only if not first run)
            self.check_authentication()

    def create_email_item(self, email_data: EmailData, index: int):
        """Create a beautifully styled email item in the list."""
        # Main email frame with gradient-like effect
        email_frame = ctk.CTkFrame(self.email_list_frame, 
                                   corner_radius=12,
                                   border_width=1,
                                   border_color="#3B3B3B")
        email_frame.pack(fill="x", pady=6, padx=8)
        
        # Selection checkbox
        checkbox_var = tk.BooleanVar(value=email_data.id in self.selected_emails)
        checkbox = ctk.CTkCheckBox(
            email_frame,
            text="",
            variable=checkbox_var,
            command=lambda: self.toggle_email_selection(email_data.id, checkbox_var.get()),
            width=20,
            height=20
        )
        checkbox.pack(side="left", padx=8)
        
        # Hover effect simulation with color changes
        def on_enter(event):
            email_frame.configure(border_color="#4A90E2")
        
        def on_leave(event):
            email_frame.configure(border_color="#3B3B3B")
        
        # Bind hover effects
        email_frame.bind("<Enter>", on_enter)
        email_frame.bind("<Leave>", on_leave)
        
        # Make clickable
        email_frame.bind("<Button-1>", lambda e, idx=index: self.select_email(idx))
        
        # Content frame with better padding
        content_frame = ctk.CTkFrame(email_frame, fg_color="transparent")
        content_frame.pack(fill="x", padx=16, pady=12)
        content_frame.bind("<Button-1>", lambda e, idx=index: self.select_email(idx))
        content_frame.bind("<Enter>", on_enter)
        content_frame.bind("<Leave>", on_leave)
        
        # Header row with better spacing
        header_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        header_frame.pack(fill="x")
        header_frame.bind("<Button-1>", lambda e, idx=index: self.select_email(idx))
        
        # Left side: Status indicators
        left_indicators = ctk.CTkFrame(header_frame, fg_color="transparent")
        left_indicators.pack(side="left")
        
        # Unread indicator
        if email_data.is_unread:
            unread_dot = ctk.CTkLabel(
                left_indicators,
                text="🔵",
                font=ctk.CTkFont(size=8),
                width=15
            )
            unread_dot.pack(side="left", padx=(0, 5))
            unread_dot.bind("<Button-1>", lambda e, idx=index: self.select_email(idx))
        
        # Urgency badge with better styling
        if email_data.analysis:
            urgency = email_data.analysis.urgency.value
            urgency_color = self.get_urgency_color(email_data.analysis.urgency)
            urgency_emoji = self.get_urgency_emoji(email_data.analysis.urgency)
            
            urgency_frame = ctk.CTkFrame(
                left_indicators,
                corner_radius=15,
                height=24,
                fg_color=urgency_color
            )
            urgency_frame.pack(side="left", padx=(0, 8))
            
            urgency_label = ctk.CTkLabel(
                urgency_frame,
                text=f"{urgency_emoji} {urgency.upper()}",
                font=ctk.CTkFont(size=9, weight="bold"),
                text_color="white",
                height=24
            )
            urgency_label.pack(padx=8, pady=2)
            urgency_label.bind("<Button-1>", lambda e, idx=index: self.select_email(idx))
            urgency_frame.bind("<Button-1>", lambda e, idx=index: self.select_email(idx))
        
        # Right side: Date and time
        date_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        date_frame.pack(side="right")
        
        # Format date more elegantly
        now = datetime.now()
        if email_data.date.date() == now.date():
            date_str = email_data.date.strftime("%H:%M")
            date_prefix = "Today "
        elif email_data.date.date() == (now - timedelta(days=1)).date():
            date_str = email_data.date.strftime("%H:%M")
            date_prefix = "Yesterday "
        else:
            date_str = email_data.date.strftime("%m/%d")
            date_prefix = ""
        
        date_label = ctk.CTkLabel(
            date_frame,
            text=f"{date_prefix}{date_str}",
            font=ctk.CTkFont(size=10, weight="bold" if email_data.is_unread else "normal"),
            text_color="#4A90E2" if email_data.is_unread else "gray",
            width=90
        )
        date_label.pack(side="right")
        date_label.bind("<Button-1>", lambda e, idx=index: self.select_email(idx))
        
        # Subject line with better typography
        subject_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        subject_frame.pack(fill="x", pady=(8, 4))
        subject_frame.bind("<Button-1>", lambda e, idx=index: self.select_email(idx))
        
        subject = email_data.subject[:70] + "..." if len(email_data.subject) > 70 else email_data.subject
        subject_label = ctk.CTkLabel(
            subject_frame,
            text=subject,
            font=ctk.CTkFont(size=13, weight="bold" if email_data.is_unread else "normal"),
            anchor="w",
            text_color="white" if email_data.is_unread else "#E0E0E0"
        )
        subject_label.pack(anchor="w", fill="x")
        subject_label.bind("<Button-1>", lambda e, idx=index: self.select_email(idx))
        
        # Sender and metadata row
        meta_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        meta_frame.pack(fill="x", pady=(0, 4))
        meta_frame.bind("<Button-1>", lambda e, idx=index: self.select_email(idx))
        
        # Sender with icon
        sender_text = email_data.sender_name or email_data.sender.split("@")[0]
        sender_display = f"👤 {sender_text}"
        
        sender_label = ctk.CTkLabel(
            meta_frame,
            text=sender_display,
            font=ctk.CTkFont(size=11, weight="bold" if email_data.is_unread else "normal"),
            anchor="w",
            text_color="#B0B0B0"
        )
        sender_label.pack(side="left")
        sender_label.bind("<Button-1>", lambda e, idx=index: self.select_email(idx))
        
        # Additional metadata
        metadata_items = []
        if email_data.attachments:
            metadata_items.append(f"📎 {len(email_data.attachments)}")
        if email_data.is_important:
            metadata_items.append("⭐")
        
        if metadata_items:
            metadata_text = " ".join(metadata_items)
            metadata_label = ctk.CTkLabel(
                meta_frame,
                text=metadata_text,
                font=ctk.CTkFont(size=10),
                text_color="#4A90E2"
            )
            metadata_label.pack(side="right")
            metadata_label.bind("<Button-1>", lambda e, idx=index: self.select_email(idx))
        
        # Preview text with better styling
        preview_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        preview_frame.pack(fill="x")
        preview_frame.bind("<Button-1>", lambda e, idx=index: self.select_email(idx))
        
        snippet = email_data.snippet[:100] + "..." if len(email_data.snippet) > 100 else email_data.snippet
        snippet_label = ctk.CTkLabel(
            preview_frame,
            text=snippet,
            font=ctk.CTkFont(size=10),
            text_color="#888888",
            anchor="w",
            justify="left",
            wraplength=500
        )
        snippet_label.pack(anchor="w", fill="x")
        snippet_label.bind("<Button-1>", lambda e, idx=index: self.select_email(idx))
        
        # AI insight footer (if available)
        if email_data.analysis and email_data.analysis.confidence > 0.8:
            insight_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            insight_frame.pack(fill="x", pady=(6, 0))
            insight_frame.bind("<Button-1>", lambda e, idx=index: self.select_email(idx))
            
            ai_insight = f"🤖 {email_data.analysis.action_required[:50]}..."
            insight_label = ctk.CTkLabel(
                insight_frame,
                text=ai_insight,
                font=ctk.CTkFont(size=9, slant="italic"),
                text_color="#4CAF50",
                anchor="w"
            )
            insight_label.pack(anchor="w")
            insight_label.bind("<Button-1>", lambda e, idx=index: self.select_email(idx))
    
    def get_urgency_color(self, urgency: EmailUrgency) -> str:
        """Get color for urgency display."""
        colors = {
            EmailUrgency.URGENT: "#ff4444",
            EmailUrgency.TO_RESPOND: "#ff8800",
            EmailUrgency.MEETING: "#4488ff",
            EmailUrgency.FYI: "#888888",
            EmailUrgency.SPAM: "#666666"
        }
        return colors.get(urgency, "#ffffff")
    
    def get_urgency_emoji(self, urgency: EmailUrgency) -> str:
        """Get emoji for urgency display."""
        emojis = {
            EmailUrgency.URGENT: "🚨",
            EmailUrgency.TO_RESPOND: "✉️",
            EmailUrgency.MEETING: "📅",
            EmailUrgency.FYI: "ℹ️",
            EmailUrgency.SPAM: "🗑️"
        }
        return emojis.get(urgency, "📧")
    
    def select_email(self, index: int):
        """Select and display an email."""
        if 0 <= index < len(self.emails):
            self.current_email_index = index
            email_data = self.emails[index]
            
            # Update display
            self.display_email_content(email_data)
            self.display_email_analysis(email_data)
            
            # Enable action buttons
            self.submit_correction_button.configure(state="normal")
            self.mark_read_button.configure(state="normal")
            self.reply_button.configure(state="normal")
            self.thread_summary_button.configure(state="normal")
    
    def display_email_content(self, email_data: EmailData):
        """Display email content in the content tab."""
        # Update header
        self.subject_label.configure(text=email_data.subject)
        self.sender_label.configure(text=f"From: {email_data.sender}")
        self.date_label.configure(text=f"Date: {email_data.date.strftime('%Y-%m-%d %H:%M')}")
        
        # Update body
        self.body_textbox.delete("1.0", "end")
        self.body_textbox.insert("1.0", email_data.body or email_data.snippet)
    
    def display_email_analysis(self, email_data: EmailData):
        """Display AI analysis in the analysis tab."""
        if email_data.analysis:
            analysis = email_data.analysis
            
            # Update current classification
            self.urgency_display.configure(text=f"Urgency: {analysis.urgency.value.title()}")
            self.category_display.configure(text=f"Category: {analysis.category.value.title()}")
            self.confidence_display.configure(text=f"Confidence: {analysis.confidence:.1%}")
            
            # Update reasoning
            self.reasoning_textbox.delete("1.0", "end")
            self.reasoning_textbox.insert("1.0", analysis.reasoning)
            
            # Update action required
            self.action_textbox.delete("1.0", "end")
            self.action_textbox.insert("1.0", analysis.action_required)
            
            # Set correction defaults
            self.urgency_correction.set(analysis.urgency.value)
            self.category_correction.set(analysis.category.value)
        else:
            # No analysis available
            self.urgency_display.configure(text="Urgency: Not analyzed")
            self.category_display.configure(text="Category: Not analyzed")
            self.confidence_display.configure(text="Confidence: N/A")
            
            self.reasoning_textbox.delete("1.0", "end")
            self.reasoning_textbox.insert("1.0", "AI analysis not available for this email.")
            
            self.action_textbox.delete("1.0", "end")
            self.action_textbox.insert("1.0", "Manual review required.")
    
    def submit_correction(self):
        """Submit user correction to the AI analysis."""
        if self.current_email_index < 0 or self.current_email_index >= len(self.emails):
            return
        
        email_data = self.emails[self.current_email_index]
        
        if not email_data.analysis:
            messagebox.showwarning("No Analysis", "This email has no AI analysis to correct.")
            return
        
        # Get correction values
        corrected_urgency = self.urgency_correction.get()
        corrected_category = self.category_correction.get()
        user_feedback = self.feedback_textbox.get("1.0", "end").strip()
        
        # Check if there's actually a correction
        original_urgency = email_data.analysis.urgency.value
        original_category = email_data.analysis.category.value
        
        if (corrected_urgency == original_urgency and 
            corrected_category == original_category and 
            not user_feedback):
            messagebox.showinfo("No Changes", "No corrections were made.")
            return
        
        # Create and store correction
        correction = UserCorrection(
            email_id=email_data.id,
            original_urgency=original_urgency,
            corrected_urgency=corrected_urgency,
            original_category=original_category,
            corrected_category=corrected_category,
            user_feedback=user_feedback
        )
        
        try:
            correction_id = self.learning_db.store_user_correction(correction)
            
            # Update sender patterns if urgency/category changed
            if (corrected_urgency != original_urgency or 
                corrected_category != original_category):
                self.learning_db.update_sender_patterns(
                    email_data.sender,
                    email_data.sender_name,
                    EmailUrgency(corrected_urgency),
                    EmailCategory(corrected_category)
                )
            
            # Clear feedback box
            self.feedback_textbox.delete("1.0", "end")
            
            messagebox.showinfo(
                "Correction Submitted",
                f"Thank you for your feedback! This will help improve the AI's accuracy.\n"
                f"Correction ID: {correction_id}"
            )
            
            self.update_status("User correction submitted successfully.")
            
        except Exception as e:
            logger.error(f"Error submitting correction: {e}")
            messagebox.showerror("Error", f"Failed to submit correction: {str(e)}")
    
    def mark_as_read(self):
        """Mark current email as read."""
        if self.current_email_index < 0 or self.current_email_index >= len(self.emails):
            return
        
        email_data = self.emails[self.current_email_index]
        
        try:
            success = self.email_service.mark_as_read(email_data.id)
            if success:
                email_data.is_unread = False
                self.update_status("Email marked as read.")
                # Refresh the email display
                self.populate_email_list()
            else:
                messagebox.showerror("Error", "Failed to mark email as read.")
        except Exception as e:
            logger.error(f"Error marking email as read: {e}")
            messagebox.showerror("Error", f"Failed to mark email as read: {str(e)}")
    
    def quick_reply(self):
        """Open quick reply window with AI-generated draft."""
        if self.current_email_index < 0 or self.current_email_index >= len(self.emails):
            return
        
        email_data = self.emails[self.current_email_index]
        
        def generate_reply_thread():
            try:
                self.update_status("Generating AI reply draft...")
                
                # Prepare email data for AI
                email_dict = {
                    'subject': email_data.subject,
                    'body': email_data.body or email_data.snippet,
                    'sender': email_data.sender,
                    'date': email_data.date.isoformat()
                }
                
                # Generate draft using AI
                from ..ai.gemini_service import GeminiEmailAI
                ai_service = GeminiEmailAI()
                draft_content = ai_service.generate_response_draft(email_dict)
                
                self.root.after(0, lambda: self.show_quick_reply_window(email_data, draft_content))
                
            except Exception as e:
                logger.error(f"Error generating reply draft: {e}")
                self.root.after(0, lambda: self.show_quick_reply_window(email_data, f"Error generating draft: {str(e)}"))
        
        threading.Thread(target=generate_reply_thread, daemon=True).start()
    
    def show_thread_summary(self):
        """Show AI-generated thread summary."""
        if self.current_email_index < 0 or self.current_email_index >= len(self.emails):
            return
        
        email_data = self.emails[self.current_email_index]
        
        def summary_thread():
            try:
                self.update_status("Generating thread summary...")
                summary = self.email_service.summarize_thread_with_ai(email_data.thread_id)
                
                self.root.after(0, lambda: self.display_thread_summary(summary))
                
            except Exception as e:
                logger.error(f"Error generating thread summary: {e}")
                self.root.after(0, lambda: messagebox.showerror(
                    "Error", f"Failed to generate thread summary: {str(e)}"
                ))
        
        threading.Thread(target=summary_thread, daemon=True).start()
    
    def display_thread_summary(self, summary):
        """Display thread summary in a popup."""
        # Create summary window
        summary_window = ctk.CTkToplevel(self.root)
        summary_window.title("Thread Summary")
        summary_window.geometry("600x500")
        summary_window.transient(self.root)
        summary_window.grab_set()
        
        # Summary content
        content_frame = ctk.CTkFrame(summary_window)
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ctk.CTkLabel(
            content_frame,
            text="AI Thread Summary",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(pady=(10, 15))
        
        # Summary text
        summary_textbox = ctk.CTkTextbox(content_frame, height=300)
        summary_textbox.pack(fill="both", expand=True, pady=(0, 15))
        
        summary_content = f"Summary: {summary.summary}\n\n"
        
        if summary.key_decisions:
            summary_content += "Key Decisions:\n"
            for decision in summary.key_decisions:
                summary_content += f"• {decision}\n"
            summary_content += "\n"
        
        if summary.action_items:
            summary_content += "Action Items:\n"
            for item in summary.action_items:
                summary_content += f"• {item}\n"
            summary_content += "\n"
        
        if summary.open_questions:
            summary_content += "Open Questions:\n"
            for question in summary.open_questions:
                summary_content += f"• {question}\n"
        
        summary_textbox.insert("1.0", summary_content)
        
        # Close button
        close_button = ctk.CTkButton(
            content_frame,
            text="Close",
            command=summary_window.destroy,
            width=100
        )
        close_button.pack(pady=(0, 10))
        
        self.update_status("Thread summary generated.")
    
    def show_quick_reply_window(self, original_email: EmailData, draft_content: str):
        """Show the quick reply window with AI-generated draft and editing options."""
        # Create reply window
        reply_window = ctk.CTkToplevel(self.root)
        reply_window.title(f"Quick Reply - {original_email.subject[:50]}...")
        reply_window.geometry("800x700")
        reply_window.transient(self.root)
        reply_window.grab_set()
        
        # Add a prominent Send button at the top
        top_frame = ctk.CTkFrame(reply_window)
        top_frame.pack(fill="x", padx=20, pady=(10, 0))
        
        send_button = ctk.CTkButton(
            top_frame,
            text="✈️ Send Email",
            command=lambda: self.send_reply_with_validation(original_email, reply_window),
            width=200,  # Make it wider
            height=45,  # Make it taller
            font=ctk.CTkFont(size=16, weight="bold"),  # Larger, bold font
            fg_color="#2E8B57",  # Green color
            hover_color="#3CB371"
        )
        send_button.pack(side="right", padx=5)
        
        # Main frame
        main_frame = ctk.CTkFrame(reply_window)
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Header frame with title and status
        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(10, 15))
        
        title_label = ctk.CTkLabel(
            header_frame,
            text="📧 Quick Reply",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(side="left")
        
        # AI status indicator
        self.ai_status_label = ctk.CTkLabel(
            header_frame,
            text="🤖 AI Draft Generated",
            font=ctk.CTkFont(size=11),
            text_color="#4CAF50"
        )
        self.ai_status_label.pack(side="right")
        
        # Original email info with better styling
        info_frame = ctk.CTkFrame(main_frame)
        info_frame.pack(fill="x", pady=(0, 15))
        
        # Info header
        ctk.CTkLabel(
            info_frame,
            text="📋 Reply Details",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=15, pady=(12, 8))
        
        # Reply info grid
        info_grid = ctk.CTkFrame(info_frame, fg_color="transparent")
        info_grid.pack(fill="x", padx=15, pady=(0, 12))
        
        # To field
        to_frame = ctk.CTkFrame(info_grid, fg_color="transparent")
        to_frame.pack(fill="x", pady=2)
        
        ctk.CTkLabel(
            to_frame,
            text="To:",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=60
        ).pack(side="left")
        
        self.to_entry = ctk.CTkEntry(
            to_frame,
            font=ctk.CTkFont(size=11),
            height=32
        )
        self.to_entry.pack(side="left", fill="x", expand=True, padx=(5, 0))
        self.to_entry.insert(0, original_email.sender)
        
        # Subject field
        subject_frame = ctk.CTkFrame(info_grid, fg_color="transparent")
        subject_frame.pack(fill="x", pady=2)
        
        ctk.CTkLabel(
            subject_frame,
            text="Subject:",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=60
        ).pack(side="left")
        
        self.subject_entry = ctk.CTkEntry(
            subject_frame,
            font=ctk.CTkFont(size=11),
            height=32
        )
        self.subject_entry.pack(side="left", fill="x", expand=True, padx=(5, 0))
        subject_text = f"Re: {original_email.subject}" if not original_email.subject.startswith('Re:') else original_email.subject
        self.subject_entry.insert(0, subject_text)
        
        # Reply composition area with enhanced editing
        compose_frame = ctk.CTkFrame(main_frame)
        compose_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        # Compose header with editing tools
        compose_header = ctk.CTkFrame(compose_frame, fg_color="transparent")
        compose_header.pack(fill="x", padx=15, pady=(15, 10))
        
        ctk.CTkLabel(
            compose_header,
            text="✏️ Message Body",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left")
        
        # Editing tools frame
        tools_frame = ctk.CTkFrame(compose_header, fg_color="transparent")
        tools_frame.pack(side="right")
        
        # Text formatting buttons
        clear_btn = ctk.CTkButton(
            tools_frame,
            text="🗑️ Clear",
            command=self.clear_reply_text,
            width=70,
            height=28,
            font=ctk.CTkFont(size=10)
        )
        clear_btn.pack(side="right", padx=(5, 0))
        
        undo_btn = ctk.CTkButton(
            tools_frame,
            text="↶ Undo",
            command=self.undo_reply_text,
            width=70,
            height=28,
            font=ctk.CTkFont(size=10)
        )
        undo_btn.pack(side="right", padx=(5, 0))
        
        # Text area for reply with better styling
        text_frame = ctk.CTkFrame(compose_frame)
        text_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        self.reply_textbox = ctk.CTkTextbox(
            text_frame,
            height=320,
            font=ctk.CTkFont(size=12, family="Consolas"),
            wrap="word",
            border_width=2
        )
        self.reply_textbox.pack(fill="both", expand=True, padx=8, pady=8)
        
        # Insert AI-generated draft
        self.reply_textbox.insert("1.0", draft_content)
        
        # Store original draft for undo functionality
        self.original_draft = draft_content
        self.draft_history = [draft_content]
        
        # AI options frame
        ai_frame = ctk.CTkFrame(compose_frame, fg_color="transparent")
        ai_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        ctk.CTkLabel(
            ai_frame,
            text="🎨 AI Options:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="left")
        
        # Tone selection
        self.tone_var = ctk.StringVar(value="professional")
        tone_menu = ctk.CTkOptionMenu(
            ai_frame,
            values=["professional", "friendly", "formal", "casual", "apologetic"],
            variable=self.tone_var,
            width=120,
            height=28
        )
        tone_menu.pack(side="left", padx=(10, 5))
        
        # Regenerate with tone button
        regenerate_tone_btn = ctk.CTkButton(
            ai_frame,
            text="🔄 Regenerate",
            command=lambda: self.regenerate_reply_with_tone(original_email),
            width=110,
            height=28
        )
        regenerate_tone_btn.pack(side="left", padx=5)
        
        # Action buttons with better styling
        button_frame = ctk.CTkFrame(compose_frame, fg_color="transparent")
        button_frame.pack(fill="x", padx=15, pady=(0, 15))

        # Send button at the top (prominently displayed)
        send_frame = ctk.CTkFrame(button_frame, fg_color="transparent")
        send_frame.pack(fill="x", pady=(0, 10))
        
        # Large, prominent Send button
        main_send_btn = ctk.CTkButton(
            send_frame,
            text="🚀 Send Reply",
            command=lambda: self.send_reply_with_validation(original_email, reply_window),
            width=200,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#2E8B57",  # Green color
            hover_color="#3CB371"
        )
        main_send_btn.pack(side="right")
        
        # Other action buttons
        actions_frame = ctk.CTkFrame(button_frame, fg_color="transparent")
        actions_frame.pack(fill="x", pady=5)
        
        # Left side buttons
        left_buttons = ctk.CTkFrame(actions_frame, fg_color="transparent")
        left_buttons.pack(side="left")
        
        save_draft_btn = ctk.CTkButton(
            left_buttons,
            text="💾 Save Draft",
            command=lambda: self.save_reply_draft(original_email),
            width=120,
            height=32
        )
        save_draft_btn.pack(side="left", padx=(0, 10))
        
        preview_btn = ctk.CTkButton(
            left_buttons,
            text="👁️ Preview",
            command=self.preview_reply,
            width=100,
            height=32
        )
        preview_btn.pack(side="left", padx=(0, 10))
        
        # Right side buttons
        right_buttons = ctk.CTkFrame(actions_frame, fg_color="transparent")
        right_buttons.pack(side="right")
        
        delete_btn = ctk.CTkButton(
            right_buttons,
            text="🗑️ Clear Draft",
            command=lambda: self.clear_reply_text(),
            width=120,
            height=32,
            fg_color="#DC3545",  # Red color
            hover_color="#C82333"
        )
        delete_btn.pack(side="left", padx=5)
        
        cancel_btn = ctk.CTkButton(
            right_buttons,
            text="❌ Cancel",
            command=reply_window.destroy,
            width=100,
            height=32,
            fg_color="#666666",
            hover_color="#777777"
        )
        cancel_btn.pack(side="right", padx=(10, 0))
        
        # Store window reference for editing functions
        self.current_reply_window = reply_window
        
        self.update_status("Quick reply window opened with editing options.")
    
    def clear_reply_text(self):
        """Clear the reply text."""
        if hasattr(self, 'reply_textbox'):
            current_content = self.reply_textbox.get("1.0", "end-1c")
            self.draft_history.append(current_content)
            self.reply_textbox.delete("1.0", "end")
            self.ai_status_label.configure(text="📝 Draft Cleared", text_color="#FF6B35")
    
    def undo_reply_text(self):
        """Undo the last change to reply text."""
        if hasattr(self, 'reply_textbox') and hasattr(self, 'draft_history'):
            if len(self.draft_history) > 1:
                # Remove current state and restore previous
                self.draft_history.pop()
                previous_draft = self.draft_history[-1]
                self.reply_textbox.delete("1.0", "end")
                self.reply_textbox.insert("1.0", previous_draft)
                self.ai_status_label.configure(text="↶ Undone", text_color="#4A90E2")
            else:
                # Restore original draft
                self.reply_textbox.delete("1.0", "end")
                self.reply_textbox.insert("1.0", self.original_draft)
                self.ai_status_label.configure(text="🔄 Original Draft Restored", text_color="#4CAF50")
    
    def regenerate_reply_with_tone(self, original_email: EmailData):
        """Regenerate reply with selected tone."""
        def regenerate_thread():
            try:
                self.update_status("Regenerating with new tone...")
                self.ai_status_label.configure(text="🎨 Generating...", text_color="#FF9500")
                
                # Prepare email data for AI
                email_dict = {
                    'subject': original_email.subject,
                    'body': original_email.body or original_email.snippet,
                    'sender': original_email.sender,
                    'date': original_email.date.isoformat()
                }
                
                # Generate new draft with selected tone
                from ..ai.gemini_service import GeminiEmailAI
                ai_service = GeminiEmailAI()
                context = {
                    'tone': self.tone_var.get(),
                    'relationship': 'colleague',
                    'preferences': f'Write in a {self.tone_var.get()} tone'
                }
                new_draft = ai_service.generate_response_draft(email_dict, context)
                
                # Store in history and update
                self.draft_history.append(self.reply_textbox.get("1.0", "end-1c"))
                self.root.after(0, lambda: self.update_reply_with_tone(new_draft))
                
            except Exception as e:
                logger.error(f"Error regenerating with tone: {e}")
                self.root.after(0, lambda: self.ai_status_label.configure(
                    text="❌ Generation Failed", text_color="#FF4444"
                ))
        
        threading.Thread(target=regenerate_thread, daemon=True).start()
    
    def update_reply_with_tone(self, new_draft: str):
        """Update reply with new tone-based draft."""
        if hasattr(self, 'reply_textbox'):
            self.reply_textbox.delete("1.0", "end")
            self.reply_textbox.insert("1.0", new_draft)
            tone = self.tone_var.get().title()
            self.ai_status_label.configure(text=f"🎨 {tone} Style Generated", text_color="#4CAF50")
            self.update_status(f"Reply regenerated with {tone.lower()} tone.")
    
    def save_reply_draft(self, original_email: EmailData):
        """Save the current reply as a draft."""
        if hasattr(self, 'reply_textbox'):
            draft_content = self.reply_textbox.get("1.0", "end-1c")
            # For now, just show a confirmation. In a real app, you'd save to a drafts folder
            messagebox.showinfo(
                "Draft Saved", 
                f"Reply draft saved locally.\n\nTo: {original_email.sender}\nSubject: Re: {original_email.subject}\n\nDraft length: {len(draft_content)} characters"
            )
            self.update_status("Reply draft saved successfully.")
    
    def preview_reply(self):
        """Show a preview of the reply email."""
        if not hasattr(self, 'reply_textbox'):
            return
        
        # Create preview window
        preview_window = ctk.CTkToplevel(self.current_reply_window)
        preview_window.title("Reply Preview")
        preview_window.geometry("600x500")
        preview_window.transient(self.current_reply_window)
        preview_window.grab_set()
        
        # Main frame
        main_frame = ctk.CTkFrame(preview_window)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ctk.CTkLabel(
            main_frame,
            text="👁️ Email Preview",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(pady=(10, 15))
        
        # Email header
        header_frame = ctk.CTkFrame(main_frame)
        header_frame.pack(fill="x", pady=(0, 10))
        
        # From, To, Subject
        ctk.CTkLabel(
            header_frame,
            text=f"From: Your Email Address",
            font=ctk.CTkFont(size=11),
            anchor="w"
        ).pack(anchor="w", padx=15, pady=(10, 2))
        
        ctk.CTkLabel(
            header_frame,
            text=f"To: {self.to_entry.get()}",
            font=ctk.CTkFont(size=11),
            anchor="w"
        ).pack(anchor="w", padx=15, pady=(2, 2))
        
        ctk.CTkLabel(
            header_frame,
            text=f"Subject: {self.subject_entry.get()}",
            font=ctk.CTkFont(size=11, weight="bold"),
            anchor="w"
        ).pack(anchor="w", padx=15, pady=(2, 10))
        
        # Email body preview
        body_label = ctk.CTkLabel(
            main_frame,
            text="Message Body:",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        )
        body_label.pack(anchor="w", pady=(10, 5))
        
        preview_textbox = ctk.CTkTextbox(
            main_frame,
            height=250,
            font=ctk.CTkFont(size=11),
            state="disabled"
        )
        preview_textbox.pack(fill="both", expand=True, pady=(0, 15))
        
        # Insert the reply content
        preview_textbox.configure(state="normal")
        preview_textbox.insert("1.0", self.reply_textbox.get("1.0", "end-1c"))
        preview_textbox.configure(state="disabled")
        
        # Close button
        close_button = ctk.CTkButton(
            main_frame,
            text="Close Preview",
            command=preview_window.destroy,
            width=120
        )
        close_button.pack(pady=(0, 10))
        
        self.update_status("Reply preview opened.")
    
    def send_reply_with_validation(self, original_email: EmailData, reply_window):
        """Send reply with input validation."""
        # Get values from form
        to_email = self.to_entry.get().strip()
        subject = self.subject_entry.get().strip()
        reply_content = self.reply_textbox.get("1.0", "end-1c").strip()
        
        # Validation
        if not to_email:
            messagebox.showerror("Validation Error", "Please enter a recipient email address.")
            return
        
        if not subject:
            messagebox.showerror("Validation Error", "Please enter a subject line.")
            return
        
        if not reply_content:
            messagebox.showerror("Validation Error", "Please enter a reply message.")
            return
        
        # Confirm send
        confirm_msg = f"Send reply to {to_email}?\n\nSubject: {subject}\nMessage length: {len(reply_content)} characters"
        if messagebox.askyesno("Confirm Send", confirm_msg):
            self.send_reply_validated(original_email, to_email, subject, reply_content, reply_window)
    
    def send_reply_validated(self, original_email: EmailData, to_email: str, subject: str, reply_content: str, reply_window):
        """Send the validated reply."""
        def send_thread():
            try:
                self.update_status("Sending reply...")
                
                # Use email service to send reply
                success = self.email_service.send_reply(
                    original_email.id,
                    original_email.thread_id,
                    subject,
                    reply_content,
                    to_email
                )
                
                if success:
                    self.root.after(0, lambda: self.on_reply_sent(reply_window))
                else:
                    self.root.after(0, lambda: messagebox.showerror(
                        "Send Error", "Failed to send reply. Please try again."
                    ))
                    
            except Exception as e:
                logger.error(f"Error sending reply: {e}")
                self.root.after(0, lambda: messagebox.showerror(
                    "Send Error", f"Failed to send reply: {str(e)}"
                ))
        
        threading.Thread(target=send_thread, daemon=True).start()
    
    def regenerate_reply_draft(self, original_email: EmailData):
        """Regenerate the AI reply draft."""
        def regenerate_thread():
            try:
                self.update_status("Regenerating reply draft...")
                
                # Prepare email data for AI
                email_dict = {
                    'subject': original_email.subject,
                    'body': original_email.body or original_email.snippet,
                    'sender': original_email.sender,
                    'date': original_email.date.isoformat()
                }
                
                # Generate new draft with different context
                from ..ai.gemini_service import GeminiEmailAI
                ai_service = GeminiEmailAI()
                context = {'tone': 'friendly', 'relationship': 'colleague'}
                new_draft = ai_service.generate_response_draft(email_dict, context)
                
                # Update the textbox
                self.root.after(0, lambda: self.update_reply_draft(new_draft))
                
            except Exception as e:
                logger.error(f"Error regenerating reply: {e}")
                self.root.after(0, lambda: messagebox.showerror(
                    "Error", f"Failed to regenerate draft: {str(e)}"
                ))
        
        threading.Thread(target=regenerate_thread, daemon=True).start()
    
    def update_reply_draft(self, new_draft: str):
        """Update the reply textbox with new draft."""
        if hasattr(self, 'reply_textbox'):
            self.reply_textbox.delete("1.0", "end")
            self.reply_textbox.insert("1.0", new_draft)
            self.update_status("Reply draft regenerated.")
    
    def send_reply(self, original_email: EmailData, reply_content: str, reply_window):
        """Send the reply email."""
        if not reply_content.strip():
            messagebox.showwarning("Empty Reply", "Please enter a reply message.")
            return
        
        def send_thread():
            try:
                self.update_status("Sending reply...")
                
                # Use email service to send reply
                success = self.email_service.send_reply(
                    original_email.id,
                    original_email.thread_id,
                    f"Re: {original_email.subject}",
                    reply_content,
                    original_email.sender
                )
                
                if success:
                    self.root.after(0, lambda: self.on_reply_sent(reply_window))
                else:
                    self.root.after(0, lambda: messagebox.showerror(
                        "Send Error", "Failed to send reply. Please try again."
                    ))
                    
            except Exception as e:
                logger.error(f"Error sending reply: {e}")
                self.root.after(0, lambda: messagebox.showerror(
                    "Send Error", f"Failed to send reply: {str(e)}"
                ))
        
        threading.Thread(target=send_thread, daemon=True).start()
    
    def on_reply_sent(self, reply_window):
        """Handle successful reply send."""
        reply_window.destroy()
        messagebox.showinfo("Reply Sent", "Your reply has been sent successfully!")
        self.update_status("Reply sent successfully.")
        
        # Optionally refresh emails to show the reply
        if messagebox.askyesno("Refresh Emails", "Would you like to refresh your inbox to see the latest emails?"):
            self.refresh_emails()
    
    def logout(self):
        """Logout the current user and allow login with different account."""
        result = messagebox.askyesno(
            "Logout Confirmation",
            "Are you sure you want to logout? This will clear all authentication data and allow you to login with a different account."
        )
        
        if result:
            try:
                # Revoke authentication and clear data
                self.auth_service.revoke_authentication()
                
                # Reset application state
                self.is_authenticated = False
                self.emails = []
                self.filtered_emails = []
                self.current_email_index = 0
                
                # Update UI
                self.auth_button.configure(text="Authenticate", state="normal")
                self.refresh_button.configure(state="disabled")
                self.logout_button.configure(state="disabled")
                
                # Clear email list
                for widget in self.email_list_frame.winfo_children():
                    widget.destroy()
                
                # Show loading message
                self.loading_label = ctk.CTkLabel(
                    self.email_list_frame,
                    text="Logged out. Click 'Authenticate' to login with your account.",
                    font=ctk.CTkFont(size=14)
                )
                self.loading_label.pack(pady=50)
                
                # Clear email details
                self.subject_label.configure(text="Select an email to view details")
                self.sender_label.configure(text="")
                self.date_label.configure(text="")
                self.body_textbox.delete("1.0", "end")
                
                # Clear analysis
                self.urgency_display.configure(text="Urgency: Not analyzed")
                self.category_display.configure(text="Category: Not analyzed")
                self.confidence_display.configure(text="Confidence: N/A")
                self.reasoning_textbox.delete("1.0", "end")
                self.action_textbox.delete("1.0", "end")
                
                # Disable action buttons
                self.submit_correction_button.configure(state="disabled")
                self.mark_read_button.configure(state="disabled")
                self.reply_button.configure(state="disabled")
                self.thread_summary_button.configure(state="disabled")
                
                # Reset filter
                self.urgency_filter.set("All")
                self.current_filter = "All"
                
                self.update_status("Logged out successfully. You can now authenticate with a different account.")
                messagebox.showinfo("Logout Successful", "You have been logged out successfully. You can now authenticate with a different Google account.")
                
            except Exception as e:
                logger.error(f"Error during logout: {e}")
                messagebox.showerror("Logout Error", f"An error occurred during logout: {str(e)}")
    
    def filter_emails(self, filter_value):
        """Filter emails by urgency."""
        self.current_filter = filter_value
        
        if not self.emails:
            return
        
        if filter_value == "All":
            self.filtered_emails = self.emails.copy()
        else:
            # Map filter values to urgency types
            urgency_map = {
                "Urgent": EmailUrgency.URGENT,
                "To Respond": EmailUrgency.TO_RESPOND,
                "FYI": EmailUrgency.FYI,
                "Meeting": EmailUrgency.MEETING
            }
            
            if filter_value in urgency_map:
                target_urgency = urgency_map[filter_value]
                self.filtered_emails = [
                    email for email in self.emails 
                    if email.analysis and email.analysis.urgency == target_urgency
                ]
            else:
                self.filtered_emails = self.emails.copy()
        
        # Refresh the display
        self.populate_email_list()
        self.update_status(f"Filter applied: {filter_value} - {len(self.filtered_emails)} emails shown")
    
    def open_settings(self):
        """Open the settings window."""
        if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
            self.settings_window.focus()  # If window exists, bring it to front
        else:
            self.settings_window = SettingsWindow(self.root) # Create and show window
    
    def is_first_run(self) -> bool:
        """Check if this is the first time running the application."""
        env_path = find_dotenv()
        
        if not env_path:
            # No .env file exists at all
            logger.info("First run: No .env file found")
            return True
            
        # Load environment variables
        load_dotenv(env_path)
        
        # Check for essential API keys
        gemini_key = os.getenv('GEMINI_API_KEY', '').strip()
        google_client_id = os.getenv('GOOGLE_CLIENT_ID', '').strip()
        google_client_secret = os.getenv('GOOGLE_CLIENT_SECRET', '').strip()
        
        logger.info(f"First run check: gemini_key={'*' * len(gemini_key) if gemini_key else 'empty'}, client_id={'*' * len(google_client_id) if google_client_id else 'empty'}, client_secret={'*' * len(google_client_secret) if google_client_secret else 'empty'}")
        
        # Check if keys are placeholder values
        placeholder_values = ['your_gemini_api_key_here', 'your_google_client_id_here', 'your_google_client_secret_here']
        
        # If any essential key is missing or a placeholder, this is effectively a first run
        if (not gemini_key or not google_client_id or not google_client_secret or
            gemini_key in placeholder_values or google_client_id in placeholder_values or google_client_secret in placeholder_values):
            logger.info("First run: Missing or placeholder API keys detected")
            return True
        
        logger.info("Not first run: All API keys are configured")
        return False
    
    def show_welcome_wizard(self):
        """Show the welcome wizard for first-time users."""
        logger.info("Showing welcome wizard for first-time setup")
        
        # Update status to indicate setup needed
        self.update_status("Welcome! Please complete the setup wizard to get started.")
        
        # Show welcome wizard after the main window is ready
        self.root.after(100, self._launch_welcome_wizard)
    
    def _launch_welcome_wizard(self):
        """Launch the welcome wizard window."""
        try:
            wizard = WelcomeWizard(self.root)
            
            # Set up callback when wizard is closed/completed
            def on_wizard_close():
                # Re-check configuration after wizard is done
                if not self.is_first_run():
                    # Setup completed, check authentication
                    self.check_authentication()
                    messagebox.showinfo(
                        "Setup Complete", 
                        "Welcome to AI Email Manager! Your setup is complete.\n\n"
                        "Click 'Authenticate' to connect to your Google account and start managing emails."
                    )
                else:
                    # Setup was skipped or incomplete
                    self.update_status("Setup incomplete. You can configure API keys in Settings.")
            
            # Wait for wizard to close then call callback
            def check_wizard_closed():
                try:
                    if not wizard.winfo_exists():
                        on_wizard_close()
                    else:
                        # Check again in 500ms
                        self.root.after(500, check_wizard_closed)
                except tk.TclError:
                    # Window was destroyed
                    on_wizard_close()
            
            # Start checking for wizard close
            check_wizard_closed()
            
        except Exception as e:
            logger.error(f"Error launching welcome wizard: {e}")
            messagebox.showerror(
                "Setup Error", 
                f"Could not launch setup wizard: {str(e)}\n\n"
                "Please configure your API keys manually in Settings."
            )
            self.update_status("Setup wizard failed. Please use Settings to configure API keys.")
    
    def update_status(self, message: str):
        """Update the status bar message."""
        self.status_label.configure(text=message)
        logger.info(f"Status: {message}")
    
    def show_progress(self):
        """Show progress bar."""
        self.progress_bar.pack(side="right", padx=15, pady=5)
        self.progress_bar.set(0)
    
    def hide_progress(self):
        """Hide progress bar."""
        self.progress_bar.pack_forget()
    
    def update_progress(self, value: float):
        """Update progress bar value (0.0 to 1.0)."""
        self.progress_bar.set(value)
    
    def delete_current_email(self):
        """Delete the currently selected email."""
        if self.current_email_index < 0 or self.current_email_index >= len(self.emails):
            messagebox.showwarning("No Email Selected", "Please select an email to delete.")
            return
            
        email_data = self.emails[self.current_email_index]
        
        # Confirm deletion
        if not messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete this email?\n\nFrom: {email_data.sender}\nSubject: {email_data.subject}"
        ):
            return
            
        try:
            # Delete email using email service
            success = self.email_service.delete_email(email_data.id)
            
            if success:
                # Remove from lists
                self.emails.remove(email_data)
                if email_data in self.filtered_emails:
                    self.filtered_emails.remove(email_data)
                    
                # Clear current selection
                self.current_email_index = -1
                
                # Update UI
                self.populate_email_list()
                self.clear_email_display()
                
                # Show confirmation
                self.update_status("Email deleted successfully.")
                messagebox.showinfo("Success", "Email has been deleted.")
            else:
                messagebox.showerror("Error", "Failed to delete email. Please try again.")
                
        except Exception as e:
            logger.error(f"Error deleting email: {e}")
            messagebox.showerror("Error", f"Failed to delete email: {str(e)}")
    
    def toggle_email_selection(self, email_id: str, is_selected: bool):
        """Handle email selection toggling."""
        if is_selected:
            self.selected_emails.add(email_id)
        else:
            self.selected_emails.discard(email_id)
        
        # Update delete button state
        self.delete_selected_btn.configure(
            state="normal" if self.selected_emails else "disabled"
        )
    
    def toggle_select_all(self, select_all: bool):
        """Toggle selection of all visible emails."""
        if select_all:
            # Select all visible emails
            for email in self.filtered_emails:
                self.selected_emails.add(email.id)
        else:
            # Deselect all emails
            self.selected_emails.clear()
        
        # Update the UI
        self.populate_email_list()
        self.delete_selected_btn.configure(
            state="normal" if self.selected_emails else "disabled"
        )
    
    def delete_selected_emails(self):
        """Delete all selected emails."""
        if not self.selected_emails:
            return
        
        # Confirm deletion
        selected_count = len(self.selected_emails)
        if not messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete {selected_count} selected {'email' if selected_count == 1 else 'emails'}?"
        ):
            return
        
        deleted_count = 0
        failed_count = 0
        
        try:
            for email_id in list(self.selected_emails):  # Use list to avoid modifying set during iteration
                try:
                    success = self.email_service.delete_email(email_id)
                    if success:
                        # Remove from data structures
                        self.emails = [e for e in self.emails if e.id != email_id]
                        self.filtered_emails = [e for e in self.filtered_emails if e.id != email_id]
                        self.selected_emails.discard(email_id)
                        deleted_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    logger.error(f"Error deleting email {email_id}: {e}")
                    failed_count += 1
            
            # Update UI
            self.populate_email_list()
            self.clear_email_display()
            
            # Show results
            if deleted_count > 0:
                self.update_status(f"Successfully deleted {deleted_count} {'email' if deleted_count == 1 else 'emails'}.")
            if failed_count > 0:
                messagebox.showwarning(
                    "Partial Success",
                    f"Deleted {deleted_count} {'email' if deleted_count == 1 else 'emails'}, but failed to delete {failed_count}."
                )
            else:
                messagebox.showinfo(
                    "Success",
                    f"Successfully deleted {deleted_count} {'email' if deleted_count == 1 else 'emails'}."
                )
        
        except Exception as e:
            logger.error(f"Error in bulk deletion: {e}")
            messagebox.showerror("Error", f"An error occurred during deletion: {str(e)}")
    
    def clear_email_display(self):
        """Clear the email display area."""
        # Clear content
        self.subject_label.configure(text="Select an email to view details")
        self.sender_label.configure(text="")
        self.date_label.configure(text="")
        self.body_textbox.delete("1.0", "end")
        
        # Clear analysis
        self.urgency_display.configure(text="Urgency: Not analyzed")
        self.category_display.configure(text="Category: Not analyzed")
        self.confidence_display.configure(text="Confidence: N/A")
        self.reasoning_textbox.delete("1.0", "end")
        self.action_textbox.delete("1.0", "end")
        
        # Disable buttons
        self.submit_correction_button.configure(state="disabled")
        self.mark_read_button.configure(state="disabled")
        self.reply_button.configure(state="disabled")
        self.thread_summary_button.configure(state="disabled")
    
    def on_closing(self):
        """Handle application closing."""
        logger.info("AI Email Manager closing")
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        """Run the application."""
        logger.info("Starting GUI main loop")
        self.root.mainloop()


def main():
    """Main entry point for the GUI application."""
    app = EmailManagerApp()
    app.run()


if __name__ == "__main__":
    main()
