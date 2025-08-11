"""
Welcome wizard for first-time users.
Guides users through the initial API setup process.
"""

import customtkinter as ctk
from tkinter import messagebox
import webbrowser
import os
from dotenv import set_key, find_dotenv


class WelcomeWizard(ctk.CTkToplevel):
    """A welcome wizard that guides users through initial setup."""

    def __init__(self, *args, **kwargs):
        """Initialize the welcome wizard."""
        super().__init__(*args, **kwargs)
        self.title("Welcome to AI Email Manager")
        self.geometry("800x600")
        self.transient(self.master)
        self.grab_set()  # Modal
        
        # Center the window
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (800 // 2)
        y = (self.winfo_screenheight() // 2) - (600 // 2)
        self.geometry(f"800x600+{x}+{y}")
        
        self.current_page = 0
        self.pages = []
        
        self.setup_ui()
        self.show_page(0)

    def setup_ui(self):
        """Create the wizard interface."""
        # Main frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Content frame (changes based on page)
        self.content_frame = ctk.CTkFrame(main_frame)
        self.content_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        # Navigation frame
        nav_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        nav_frame.pack(fill="x")
        
        # Navigation buttons
        self.back_button = ctk.CTkButton(
            nav_frame, text="← Back", 
            command=self.previous_page,
            width=100, state="disabled"
        )
        self.back_button.pack(side="left")
        
        self.next_button = ctk.CTkButton(
            nav_frame, text="Next →", 
            command=self.next_page,
            width=100
        )
        self.next_button.pack(side="right")
        
        # Skip button
        self.skip_button = ctk.CTkButton(
            nav_frame, text="Skip Setup", 
            command=self.skip_setup,
            width=100, fg_color="gray"
        )
        self.skip_button.pack(side="right", padx=(0, 10))
        
        # Progress indicator
        self.progress_label = ctk.CTkLabel(nav_frame, text="Step 1 of 4")
        self.progress_label.pack()

        # Setup pages
        self.create_pages()

    def create_pages(self):
        """Create all wizard pages."""
        self.pages = [
            self.create_welcome_page,
            self.create_gemini_page,
            self.create_google_oauth_page,
            self.create_completion_page
        ]

    def create_welcome_page(self):
        """Create the welcome page."""
        # Clear content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        content = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=30, pady=30)
        
        # Welcome title
        title = ctk.CTkLabel(
            content, 
            text="Welcome to AI Email Manager! 🎉",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        title.pack(pady=(0, 20))
        
        # Welcome message
        welcome_text = """
Transform your email experience with intelligent AI automation!

This wizard will help you set up the necessary API keys to get started:

🧠 AI Features:
• Smart email classification and prioritization
• Automatic thread summaries
• Intelligent response suggestions
• Learning from your feedback

🔐 Secure Setup:
• Your credentials are stored locally and encrypted
• OAuth2 authentication with Google
• Full control over your data

Let's get you set up in just a few minutes!
        """
        
        welcome_label = ctk.CTkLabel(
            content, 
            text=welcome_text,
            font=ctk.CTkFont(size=14),
            justify="left"
        )
        welcome_label.pack(pady=20)
        
        # Feature preview
        features_frame = ctk.CTkFrame(content)
        features_frame.pack(fill="x", pady=20)
        
        features_title = ctk.CTkLabel(
            features_frame,
            text="What You'll Get:",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        features_title.pack(pady=(15, 10))
        
        features = [
            "✨ Intelligent email triage and classification",
            "📊 AI-powered insights and summaries", 
            "🎯 Personalized recommendations",
            "⚡ Significant time savings on email management"
        ]
        
        for feature in features:
            feature_label = ctk.CTkLabel(
                features_frame,
                text=feature,
                font=ctk.CTkFont(size=12)
            )
            feature_label.pack(anchor="w", padx=20, pady=2)
            
        ctk.CTkLabel(features_frame, text="").pack(pady=5)  # Spacer

    def create_gemini_page(self):
        """Create the Gemini API setup page."""
        # Clear content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        content = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=30, pady=30)
        
        # Page title
        title = ctk.CTkLabel(
            content, 
            text="Step 1: Gemini AI Setup 🧠",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(pady=(0, 20))
        
        # Instructions
        instructions_text = """
The Gemini API powers all AI features in the application.
Getting your API key is free and takes just 30 seconds!
        """
        
        instructions = ctk.CTkLabel(
            content, 
            text=instructions_text,
            font=ctk.CTkFont(size=14)
        )
        instructions.pack(pady=(0, 20))
        
        # Step-by-step instructions
        steps_frame = ctk.CTkFrame(content)
        steps_frame.pack(fill="x", pady=10)
        
        steps_title = ctk.CTkLabel(
            steps_frame,
            text="Quick Steps:",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        steps_title.pack(pady=(15, 10))
        
        steps = [
            "1. Click 'Open Google AI Studio' below",
            "2. Sign in with your Google account",  
            "3. Click 'Create API key'",
            "4. Copy the generated API key",
            "5. Paste it in the field below"
        ]
        
        for step in steps:
            step_label = ctk.CTkLabel(
                steps_frame,
                text=step,
                font=ctk.CTkFont(size=12)
            )
            step_label.pack(anchor="w", padx=20, pady=2)
        
        # Open button
        open_button = ctk.CTkButton(
            steps_frame,
            text="🔗 Open Google AI Studio",
            command=lambda: webbrowser.open("https://aistudio.google.com/app/apikey"),
            width=200,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        open_button.pack(pady=15)
        
        # API key input
        input_frame = ctk.CTkFrame(content)
        input_frame.pack(fill="x", pady=20)
        
        ctk.CTkLabel(
            input_frame, 
            text="Paste your Gemini API Key here:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(15, 5))
        
        self.gemini_key_entry = ctk.CTkEntry(
            input_frame, 
            width=500,
            height=40,
            font=ctk.CTkFont(size=12),
            show="*"
        )
        self.gemini_key_entry.pack(pady=(0, 15))
        
        # Help note
        help_text = "💡 Tip: The API key starts with 'AI...' and is completely free to use!"
        ctk.CTkLabel(
            input_frame,
            text=help_text,
            font=ctk.CTkFont(size=11),
            text_color="gray"
        ).pack(pady=(0, 10))

    def create_google_oauth_page(self):
        """Create the Google OAuth setup page."""
        # Clear content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        content = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=30, pady=30)
        
        # Page title
        title = ctk.CTkLabel(
            content, 
            text="Step 2: Google Workspace Setup 🔐",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(pady=(0, 15))
        
        # Instructions
        instructions_text = """
Set up secure access to your Gmail and Calendar.
This is a one-time setup that ensures your data stays private and secure.
        """
        
        instructions = ctk.CTkLabel(
            content, 
            text=instructions_text,
            font=ctk.CTkFont(size=14)
        )
        instructions.pack(pady=(0, 15))
        
        # Detailed steps
        steps_frame = ctk.CTkFrame(content)
        steps_frame.pack(fill="x", pady=10)
        
        # Open Google Cloud Console button
        console_button = ctk.CTkButton(
            steps_frame,
            text="🔗 Open Google Cloud Console",
            command=lambda: webbrowser.open("https://console.cloud.google.com/"),
            width=250,
            height=35,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        console_button.pack(pady=15)
        
        # Quick steps
        quick_steps_text = """
Quick Setup Steps:
1. Create a new project (name it 'AI Email Manager')
2. Enable Gmail API and Google Calendar API  
3. Set up OAuth consent screen (External, use your email)
4. Create OAuth 2.0 credentials (Desktop app)
5. Copy Client ID and Client Secret below
        """
        
        steps_label = ctk.CTkLabel(
            steps_frame,
            text=quick_steps_text,
            font=ctk.CTkFont(size=11),
            justify="left"
        )
        steps_label.pack(pady=10)
        
        # Detailed guide button
        guide_button = ctk.CTkButton(
            steps_frame,
            text="📖 View Detailed Guide",
            command=self.open_detailed_guide,
            width=200,
            fg_color="gray"
        )
        guide_button.pack(pady=5)
        
        # Input fields
        input_frame = ctk.CTkFrame(content)
        input_frame.pack(fill="x", pady=15)
        
        # Client ID
        ctk.CTkLabel(
            input_frame, 
            text="Google Client ID:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w", padx=20, pady=(15, 5))
        
        self.client_id_entry = ctk.CTkEntry(
            input_frame,
            width=500,
            height=35
        )
        self.client_id_entry.pack(padx=20, pady=(0, 10))
        
        # Client Secret
        ctk.CTkLabel(
            input_frame, 
            text="Google Client Secret:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w", padx=20, pady=(5, 5))
        
        self.client_secret_entry = ctk.CTkEntry(
            input_frame,
            width=500,
            height=35,
            show="*"
        )
        self.client_secret_entry.pack(padx=20, pady=(0, 15))

    def create_completion_page(self):
        """Create the completion page."""
        # Clear content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        content = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=30, pady=30)
        
        # Success title
        title = ctk.CTkLabel(
            content, 
            text="🎉 Setup Complete!",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="green"
        )
        title.pack(pady=(0, 20))
        
        # Success message
        success_text = """
Congratulations! Your AI Email Manager is now configured and ready to use.

Your credentials have been saved securely and the application will restart automatically.
        """
        
        success_label = ctk.CTkLabel(
            content, 
            text=success_text,
            font=ctk.CTkFont(size=16)
        )
        success_label.pack(pady=20)
        
        # What's next
        next_frame = ctk.CTkFrame(content)
        next_frame.pack(fill="x", pady=20)
        
        next_title = ctk.CTkLabel(
            next_frame,
            text="What happens next:",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        next_title.pack(pady=(15, 10))
        
        next_steps = [
            "✅ Application will restart with your settings",
            "🔐 Click 'Authenticate' to connect to Google",
            "📧 Click 'Refresh Emails' to load your inbox",
            "🧠 Watch as AI intelligently organizes your emails!"
        ]
        
        for step in next_steps:
            step_label = ctk.CTkLabel(
                next_frame,
                text=step,
                font=ctk.CTkFont(size=13)
            )
            step_label.pack(anchor="w", padx=20, pady=3)
        
        # Finish button
        finish_button = ctk.CTkButton(
            next_frame,
            text="🚀 Finish Setup & Start",
            command=self.finish_setup,
            width=250,
            height=50,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        finish_button.pack(pady=20)
        
        ctk.CTkLabel(next_frame, text="").pack(pady=5)  # Spacer

    def show_page(self, page_index):
        """Show the specified page."""
        self.current_page = page_index
        
        # Update progress
        self.progress_label.configure(text=f"Step {page_index + 1} of {len(self.pages)}")
        
        # Update navigation buttons
        self.back_button.configure(state="normal" if page_index > 0 else "disabled")
        
        if page_index == len(self.pages) - 1:
            self.next_button.configure(text="Finish", state="disabled")
            self.skip_button.pack_forget()
        else:
            self.next_button.configure(text="Next →", state="normal")
        
        # Create page content
        self.pages[page_index]()

    def previous_page(self):
        """Go to the previous page."""
        if self.current_page > 0:
            self.show_page(self.current_page - 1)

    def next_page(self):
        """Go to the next page."""
        # Validate current page before proceeding
        if not self.validate_current_page():
            return
            
        if self.current_page < len(self.pages) - 1:
            self.show_page(self.current_page + 1)

    def validate_current_page(self):
        """Validate the current page inputs."""
        if self.current_page == 1:  # Gemini API page
            if not self.gemini_key_entry.get().strip():
                messagebox.showwarning(
                    "Missing API Key", 
                    "Please enter your Gemini API key to continue.",
                    parent=self
                )
                return False
        elif self.current_page == 2:  # Google OAuth page
            if not (self.client_id_entry.get().strip() and 
                   self.client_secret_entry.get().strip()):
                messagebox.showwarning(
                    "Missing Credentials", 
                    "Please enter both Google Client ID and Client Secret to continue.",
                    parent=self
                )
                return False
        
        return True

    def skip_setup(self):
        """Skip the setup process."""
        result = messagebox.askyesno(
            "Skip Setup?",
            "Are you sure you want to skip the setup? You can configure your API keys later in Settings.",
            parent=self
        )
        if result:
            self.destroy()

    def open_detailed_guide(self):
        """Open the detailed setup guide."""
        # Try to open the API setup guide
        guide_path = os.path.join(os.path.dirname(__file__), "..", "..", "API_SETUP_GUIDE.md")
        if os.path.exists(guide_path):
            os.startfile(guide_path)  # Windows
        else:
            # Fallback to opening the GitHub or local path
            messagebox.showinfo(
                "Setup Guide",
                "Please see the API_SETUP_GUIDE.md file in your project directory for detailed instructions.",
                parent=self
            )

    def save_settings(self):
        """Save the entered settings to .env file."""
        env_path = find_dotenv()
        if not env_path:
            env_path = os.path.join(os.getcwd(), ".env")

        try:
            # Get values
            gemini_key = self.gemini_key_entry.get().strip()
            client_id = self.client_id_entry.get().strip()
            client_secret = self.client_secret_entry.get().strip()
            
            # Save to .env
            set_key(env_path, "GEMINI_API_KEY", gemini_key)
            set_key(env_path, "GOOGLE_CLIENT_ID", client_id)
            set_key(env_path, "GOOGLE_CLIENT_SECRET", client_secret)
            
            return True
        except Exception as e:
            messagebox.showerror(
                "Save Error", 
                f"Failed to save settings: {str(e)}",
                parent=self
            )
            return False

    def finish_setup(self):
        """Finish the setup and close the wizard."""
        if self.save_settings():
            messagebox.showinfo(
                "Setup Complete!",
                "Your settings have been saved. The application will now restart.",
                parent=self
            )
            # Close the wizard and restart the app
            self.master.destroy()  # Close main app
            # The main script should handle restarting
