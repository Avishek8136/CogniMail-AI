"""
FeedbackDialog module for user feedback and RLHF functionality.
Allows users to provide feedback on AI features for reinforcement learning.
"""

import tkinter as tk
import customtkinter as ctk
from typing import Optional, Dict, Any, Callable
import json
from loguru import logger

from ..database.advanced_db import UserFeedback


class FeedbackDialog(ctk.CTkToplevel):
    """Dialog for collecting user feedback for RLHF."""
    
    def __init__(self, parent, email_id: str = ""):
        """Initialize the feedback dialog."""
        super().__init__(parent)
        self.parent = parent
        self.email_id = email_id
        
        # Configure window
        self.title("AI Feedback")
        self.geometry("500x600")
        self.resizable(True, True)
        
        # Center on parent
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
        
        # Initialize variables
        self.feature_type = tk.StringVar(value="general")
        self.rating = tk.IntVar(value=3)
        self.ai_response_quality = tk.IntVar(value=3)
        self.user_satisfaction = tk.IntVar(value=3)
        self.feedback_text = tk.StringVar()
        self.improvement_suggestion = tk.StringVar()
        
        self.context_data = {}
        
        # Build UI
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the dialog UI."""
        # Main frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ctk.CTkLabel(
            main_frame,
            text="AI Assistant Feedback",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Description
        desc_label = ctk.CTkLabel(
            main_frame,
            text="Your feedback helps us improve the AI assistant's performance.\nPlease rate your experience and provide comments.",
            font=ctk.CTkFont(size=14),
            wraplength=400
        )
        desc_label.pack(pady=(0, 20))
        
        # Feature selection
        feature_frame = ctk.CTkFrame(main_frame)
        feature_frame.pack(fill="x", pady=10)
        
        feature_label = ctk.CTkLabel(
            feature_frame,
            text="What feature are you providing feedback on?",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        feature_label.pack(anchor="w", pady=(5, 10))
        
        # Feature options
        features = [
            ("General AI Performance", "general"),
            ("Email Analysis", "analysis"),
            ("AI Reply Generation", "reply_generation"),
            ("Email Classification", "classification"),
            ("Thread Grouping", "threading"),
            ("Urgency Detection", "urgency_detection"),
            ("Action Item Extraction", "action_items")
        ]
        
        feature_options_frame = ctk.CTkFrame(feature_frame, fg_color="transparent")
        feature_options_frame.pack(fill="x")
        
        for i, (text, value) in enumerate(features):
            rb = ctk.CTkRadioButton(
                feature_options_frame,
                text=text,
                value=value,
                variable=self.feature_type,
                font=ctk.CTkFont(size=13)
            )
            rb.grid(row=i//2, column=i%2, sticky="w", padx=10, pady=5)
        
        # Rating
        rating_frame = ctk.CTkFrame(main_frame)
        rating_frame.pack(fill="x", pady=10)
        
        rating_label = ctk.CTkLabel(
            rating_frame,
            text="How would you rate this feature? (1-5)",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        rating_label.pack(anchor="w", pady=(5, 10))
        
        # Rating buttons
        rating_options_frame = ctk.CTkFrame(rating_frame, fg_color="transparent")
        rating_options_frame.pack(fill="x")
        
        rating_labels = ["Poor", "Fair", "Good", "Very Good", "Excellent"]
        
        for i, label in enumerate(rating_labels, 1):
            rb = ctk.CTkRadioButton(
                rating_options_frame,
                text=f"{i} - {label}",
                value=i,
                variable=self.rating,
                font=ctk.CTkFont(size=13)
            )
            rb.pack(side="left", padx=10, pady=5)
        
        # AI Response Quality
        quality_frame = ctk.CTkFrame(main_frame)
        quality_frame.pack(fill="x", pady=10)
        
        quality_label = ctk.CTkLabel(
            quality_frame,
            text="How accurate was the AI's response? (1-5)",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        quality_label.pack(anchor="w", pady=(5, 10))
        
        # Quality rating
        quality_scale = ctk.CTkSlider(
            quality_frame,
            from_=1,
            to=5,
            number_of_steps=4,
            variable=self.ai_response_quality,
            width=400
        )
        quality_scale.pack(pady=5)
        
        quality_markers = ctk.CTkFrame(quality_frame, fg_color="transparent")
        quality_markers.pack(fill="x", padx=40)
        
        for i, label in enumerate(["Inaccurate", "", "Neutral", "", "Very Accurate"], 1):
            marker = ctk.CTkLabel(quality_markers, text=f"{i}{' - '+label if label else ''}")
            marker.grid(row=0, column=i-1, padx=10)
        
        # User Satisfaction
        satisfaction_frame = ctk.CTkFrame(main_frame)
        satisfaction_frame.pack(fill="x", pady=10)
        
        satisfaction_label = ctk.CTkLabel(
            satisfaction_frame,
            text="Overall satisfaction with the AI assistant",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        satisfaction_label.pack(anchor="w", pady=(5, 10))
        
        # Satisfaction rating
        satisfaction_scale = ctk.CTkSlider(
            satisfaction_frame,
            from_=1,
            to=5,
            number_of_steps=4,
            variable=self.user_satisfaction,
            width=400
        )
        satisfaction_scale.pack(pady=5)
        
        satisfaction_markers = ctk.CTkFrame(satisfaction_frame, fg_color="transparent")
        satisfaction_markers.pack(fill="x", padx=40)
        
        for i, label in enumerate(["Dissatisfied", "", "Neutral", "", "Very Satisfied"], 1):
            marker = ctk.CTkLabel(satisfaction_markers, text=f"{i}{' - '+label if label else ''}")
            marker.grid(row=0, column=i-1, padx=10)
        
        # Comments frame
        comments_frame = ctk.CTkFrame(main_frame)
        comments_frame.pack(fill="x", pady=10)
        
        # Feedback text
        feedback_label = ctk.CTkLabel(
            comments_frame,
            text="Comments about your experience:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        feedback_label.pack(anchor="w", pady=(5, 5))
        
        feedback_entry = ctk.CTkTextbox(
            comments_frame,
            height=80,
            width=400,
            font=ctk.CTkFont(size=13)
        )
        feedback_entry.pack(fill="x", pady=5)
        
        # Improvement suggestions
        improvement_label = ctk.CTkLabel(
            comments_frame,
            text="Suggestions for improvement:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        improvement_label.pack(anchor="w", pady=(10, 5))
        
        improvement_entry = ctk.CTkTextbox(
            comments_frame,
            height=80,
            width=400,
            font=ctk.CTkFont(size=13)
        )
        improvement_entry.pack(fill="x", pady=5)
        
        # Buttons
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(15, 0))
        
        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self.destroy,
            width=100,
            fg_color="#888888",
            hover_color="#666666"
        )
        cancel_button.pack(side="left", padx=10)
        
        submit_button = ctk.CTkButton(
            button_frame,
            text="Submit Feedback",
            command=lambda: self.submit_feedback(
                feedback_entry.get("1.0", "end-1c"),
                improvement_entry.get("1.0", "end-1c")
            ),
            width=150
        )
        submit_button.pack(side="right", padx=10)
    
    def submit_feedback(self, feedback_text: str, improvement_text: str):
        """Submit user feedback."""
        try:
            # Create feedback object
            feedback = UserFeedback(
                email_id=self.email_id,
                feature_type=self.feature_type.get(),
                rating=self.rating.get(),
                feedback_text=feedback_text,
                improvement_suggestion=improvement_text,
                ai_response_quality=self.ai_response_quality.get(),
                user_satisfaction=self.user_satisfaction.get(),
                context_data=json.dumps(self.context_data)
            )
            
            # Store feedback in the database
            feedback_id = self.parent.advanced_db.store_user_feedback(feedback)
            
            # Update personalization profile based on feedback
            user_email = self.parent.auth_service.get_current_user()
            if user_email:
                self.parent.advanced_db.learn_from_feedback(user_email, feedback)
            
            if feedback_id > 0:
                # Show success message
                ctk.CTkMessagebox.CTkMessagebox(
                    master=self,
                    title="Thank You",
                    message="Thank you for your feedback! It helps us improve the AI assistant.",
                    icon="check",
                    option_1="Close"
                )
                self.destroy()
            else:
                raise Exception("Failed to store feedback")
                
        except Exception as e:
            logger.error(f"Error submitting feedback: {e}")
            ctk.CTkMessagebox.CTkMessagebox(
                master=self,
                title="Error",
                message=f"Error submitting feedback: {str(e)}",
                icon="cancel",
                option_1="Close"
            )
    
    def set_context_data(self, context: Dict[str, Any]):
        """Set context data for the feedback."""
        self.context_data = context
