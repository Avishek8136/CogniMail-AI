"""
Settings window for API key configuration.
Allows users to enter and save their Gemini and Google API keys.
"""

import customtkinter as ctk
from tkinter import messagebox
from dotenv import set_key, get_key, find_dotenv
import os


class SettingsWindow(ctk.CTkToplevel):
    """A Toplevel window for configuring application settings."""

    def __init__(self, *args, **kwargs):
        """Initialize the settings window."""
        super().__init__(*args, **kwargs)
        self.title("Settings - API Configuration")
        self.geometry("600x400")
        self.transient(self.master)  # Keep window on top of the main app
        self.grab_set()  # Modal-like behavior

        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        """Create the user interface for the settings window."""
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        title_label = ctk.CTkLabel(
            main_frame, 
            text="API & Application Settings",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(pady=(0, 20))

        # --- Gemini API Key ---
        gemini_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        gemini_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(gemini_frame, text="Gemini API Key:", width=150).pack(side="left")
        self.gemini_api_key_entry = ctk.CTkEntry(gemini_frame, width=350, show="*")
        self.gemini_api_key_entry.pack(side="left", expand=True, fill="x")

        # --- Google Client ID ---
        client_id_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        client_id_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(client_id_frame, text="Google Client ID:", width=150).pack(side="left")
        self.google_client_id_entry = ctk.CTkEntry(client_id_frame, width=350)
        self.google_client_id_entry.pack(side="left", expand=True, fill="x")

        # --- Google Client Secret ---
        client_secret_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        client_secret_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(client_secret_frame, text="Google Client Secret:", width=150).pack(side="left")
        self.google_client_secret_entry = ctk.CTkEntry(client_secret_frame, width=350, show="*")
        self.google_client_secret_entry.pack(side="left", expand=True, fill="x")
        
        # --- Info Label ---
        info_label = ctk.CTkLabel(
            main_frame, 
            text="Saving requires an application restart to take effect.", 
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color="gray"
        )
        info_label.pack(pady=(20, 10))

        # --- Buttons ---
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(pady=20)

        self.save_button = ctk.CTkButton(
            button_frame, 
            text="Save and Close", 
            command=self.save_and_close
        )
        self.save_button.pack(side="left", padx=10)

        self.cancel_button = ctk.CTkButton(
            button_frame, 
            text="Cancel", 
            command=self.destroy, 
            fg_color="gray"
        )
        self.cancel_button.pack(side="left", padx=10)

    def load_settings(self):
        """Load existing settings from the .env file and populate entries."""
        env_path = find_dotenv()

        # If .env file doesn't exist, create it.
        if not env_path:
            env_path = os.path.join(os.getcwd(), ".env")
            open(env_path, 'a').close() 

        self.gemini_api_key_entry.insert(0, get_key(env_path, "GEMINI_API_KEY") or "")
        self.google_client_id_entry.insert(0, get_key(env_path, "GOOGLE_CLIENT_ID") or "")
        self.google_client_secret_entry.insert(0, get_key(env_path, "GOOGLE_CLIENT_SECRET") or "")

    def save_settings(self) -> bool:
        """Save the entered settings to the .env file."""
        env_path = find_dotenv()
        if not env_path:
            env_path = os.path.join(os.getcwd(), ".env")

        # Get values from entries
        gemini_key = self.gemini_api_key_entry.get()
        client_id = self.google_client_id_entry.get()
        client_secret = self.google_client_secret_entry.get()

        # Basic validation
        if not (gemini_key and client_id and client_secret):
            messagebox.showwarning(
                "Missing Information", 
                "All API keys and credentials are required for the application to function correctly.",
                parent=self
            )
            # We don't prevent saving, just warn the user

        try:
            set_key(env_path, "GEMINI_API_KEY", gemini_key)
            set_key(env_path, "GOOGLE_CLIENT_ID", client_id)
            set_key(env_path, "GOOGLE_CLIENT_SECRET", client_secret)
            return True
        except Exception as e:
            messagebox.showerror("Error Saving", f"Failed to save settings to .env file:\n{e}", parent=self)
            return False

    def save_and_close(self):
        """Save settings and then close the window."""
        if self.save_settings():
            messagebox.showinfo(
                "Settings Saved", 
                "Your settings have been saved. Please restart the application for them to take effect.",
                parent=self
            )
            self.destroy() # Close the window

