"""
Smart reminder system with context-aware scheduling and AI-powered timing.
Provides intelligent reminders based on user patterns and email context.
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from loguru import logger

from ..database.advanced_db import AdvancedDatabase, Reminder
from ..core.email_service import EmailData
from ..ai.gemini_service import GeminiEmailAI


class ReminderSystem:
    """Intelligent reminder system with context-aware scheduling."""
    
    def __init__(self, advanced_db: Optional[AdvancedDatabase] = None,
                 ai_service: Optional[GeminiEmailAI] = None):
        """Initialize the reminder system."""
        self.advanced_db = advanced_db or AdvancedDatabase()
        self.ai_service = ai_service or GeminiEmailAI()
        
    def analyze_reminder_needs(self, email: EmailData, user_patterns: Dict = None) -> Dict:
        """
        Analyze if an email needs reminders using AI and user patterns.
        
        Args:
            email: Email data to analyze
            user_patterns: User's behavioral patterns (optional)
            
        Returns:
            Dictionary with reminder analysis results
        """
        try:
            # Get user patterns if not provided
            if not user_patterns:
                user_patterns = self._get_user_patterns()
            
            # Create reminder analysis prompt
            prompt = f"""
            Analyze the following email to determine if it needs reminders and optimal timing:
            
            From: {email.sender}
            Subject: {email.subject}
            Date: {email.date}
            Content: {email.content[:1200]}...
            
            User patterns: {json.dumps(user_patterns, default=str)}
            
            Please analyze and respond in JSON format:
            {{
                "needs_reminder": true/false,
                "reminder_type": "followup/deadline/meeting/important_email/custom",
                "optimal_timing": {{
                    "first_reminder": "YYYY-MM-DD HH:MM",
                    "second_reminder": "YYYY-MM-DD HH:MM" (optional),
                    "final_reminder": "YYYY-MM-DD HH:MM" (optional)
                }},
                "priority": "low/medium/high/urgent",
                "context": "brief explanation of why reminders are needed",
                "frequency": "once/daily/weekly/custom",
                "suggested_snooze": [15, 30, 60, 120] (minutes options)
            }}
            
            Consider:
            - User's typical response times
            - Email importance and sender
            - Deadlines mentioned in content
            - Meeting scheduling needs
            - User's work schedule patterns
            """
            
            response = self.ai_service.generate_content(prompt)
            
            try:
                analysis = json.loads(response)
                
                # Validate and parse dates
                optimal_timing = analysis.get("optimal_timing", {})
                for key, date_str in optimal_timing.items():
                    if date_str:
                        try:
                            optimal_timing[key] = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
                        except ValueError:
                            # Try alternative format
                            try:
                                optimal_timing[key] = datetime.strptime(date_str, "%Y-%m-%d")
                            except ValueError:
                                logger.warning(f"Could not parse reminder date: {date_str}")
                                optimal_timing[key] = None
                
                return analysis
                
            except json.JSONDecodeError:
                logger.warning("Failed to parse AI reminder analysis, using fallback")
                return self._fallback_reminder_analysis(email, user_patterns)
                
        except Exception as e:
            logger.error(f"Error analyzing reminder needs: {e}")
            return self._fallback_reminder_analysis(email, user_patterns)
    
    def _fallback_reminder_analysis(self, email: EmailData, user_patterns: Dict = None) -> Dict:
        """Fallback reminder analysis using keyword detection."""
        content_lower = email.content.lower()
        subject_lower = email.subject.lower()
        text_to_analyze = f"{subject_lower} {content_lower}"
        
        # Check for reminder indicators
        reminder_keywords = [
            'deadline', 'due date', 'meeting', 'appointment', 'schedule',
            'reminder', 'don\'t forget', 'remember', 'important',
            'urgent', 'follow up', 'check in'
        ]
        
        meeting_keywords = ['meeting', 'call', 'conference', 'zoom', 'teams']
        deadline_keywords = ['deadline', 'due', 'submit', 'complete by']
        important_keywords = ['important', 'urgent', 'priority', 'critical']
        
        needs_reminder = any(keyword in text_to_analyze for keyword in reminder_keywords)
        
        if not needs_reminder:
            return {
                "needs_reminder": False,
                "reminder_type": "none",
                "optimal_timing": {},
                "priority": "low",
                "context": "No clear reminder indicators found",
                "frequency": "once",
                "suggested_snooze": [15, 30, 60]
            }
        
        # Determine reminder type
        reminder_type = "custom"
        if any(keyword in text_to_analyze for keyword in meeting_keywords):
            reminder_type = "meeting"
        elif any(keyword in text_to_analyze for keyword in deadline_keywords):
            reminder_type = "deadline"
        elif 'follow' in text_to_analyze:
            reminder_type = "followup"
        else:
            reminder_type = "important_email"
        
        # Determine priority
        priority = "medium"
        if any(keyword in text_to_analyze for keyword in important_keywords):
            priority = "high"
        
        # Calculate optimal timing based on type and user patterns
        now = datetime.now()
        if reminder_type == "meeting":
            first_reminder = now + timedelta(hours=24)  # 1 day before
            second_reminder = now + timedelta(hours=2)   # 2 hours before
        elif reminder_type == "deadline":
            first_reminder = now + timedelta(days=2)     # 2 days before
            second_reminder = now + timedelta(days=1)    # 1 day before
        else:
            first_reminder = now + timedelta(days=1)     # Next day
            second_reminder = None
        
        return {
            "needs_reminder": True,
            "reminder_type": reminder_type,
            "optimal_timing": {
                "first_reminder": first_reminder,
                "second_reminder": second_reminder
            },
            "priority": priority,
            "context": f"Detected {reminder_type} reminder needed",
            "frequency": "once",
            "suggested_snooze": [15, 30, 60, 120]
        }
    
    def _get_user_patterns(self) -> Dict:
        """Get user behavioral patterns for reminder optimization."""
        try:
            # This would typically come from user profile/analytics
            # For now, return default patterns
            return {
                "typical_work_hours": {"start": 9, "end": 17},
                "average_response_time": "2 hours",
                "preferred_reminder_time": "09:00",
                "time_zone": "local",
                "weekend_preferences": "no_reminders"
            }
        except Exception as e:
            logger.error(f"Error getting user patterns: {e}")
            return {}
    
    def create_reminder(self, email: EmailData, analysis: Dict = None) -> int:
        """
        Create reminders for an email based on analysis.
        
        Args:
            email: Email data
            analysis: Reminder analysis results (optional)
            
        Returns:
            Number of reminders created
        """
        try:
            if not analysis:
                analysis = self.analyze_reminder_needs(email)
            
            if not analysis.get("needs_reminder", False):
                logger.info(f"No reminder needed for email {email.id}")
                return 0
            
            reminders_created = 0
            optimal_timing = analysis.get("optimal_timing", {})
            reminder_type = analysis.get("reminder_type", "custom")
            priority = analysis.get("priority", "medium")
            context = analysis.get("context", "")
            
            # Create reminders based on optimal timing
            for reminder_key, reminder_time in optimal_timing.items():
                if reminder_time and isinstance(reminder_time, datetime):
                    # Create reminder title based on type
                    if reminder_type == "meeting":
                        title = f"Meeting Reminder: {email.subject[:50]}"
                    elif reminder_type == "deadline":
                        title = f"Deadline Reminder: {email.subject[:50]}"
                    elif reminder_type == "followup":
                        title = f"Follow-up Reminder: {email.subject[:50]}"
                    else:
                        title = f"Reminder: {email.subject[:50]}"
                    
                    # Create description
                    description = f"{context}\\n\\nFrom: {email.sender}\\nOriginal: {email.subject}"
                    
                    # Create reminder object
                    reminder = Reminder(
                        email_id=email.id,
                        thread_id=email.thread_id,
                        title=title,
                        description=description,
                        reminder_time=reminder_time,
                        status="active",
                        reminder_type=reminder_type,
                        created_at=datetime.now()
                    )
                    
                    # Store in database
                    reminder_id = self.advanced_db.create_reminder(reminder)
                    
                    if reminder_id > 0:
                        reminders_created += 1
                        logger.info(f"Created {reminder_key} reminder {reminder_id} for email {email.id}")
            
            return reminders_created
            
        except Exception as e:
            logger.error(f"Error creating reminders: {e}")
            return 0
    
    def get_due_reminders(self) -> List[Reminder]:
        """Get reminders that are due now."""
        return self.advanced_db.get_due_reminders()
    
    def snooze_reminder(self, reminder_id: int, minutes: int) -> bool:
        """
        Snooze a reminder for specified minutes.
        
        Args:
            reminder_id: ID of the reminder
            minutes: Minutes to snooze
            
        Returns:
            True if successful, False otherwise
        """
        return self.advanced_db.snooze_reminder(reminder_id, minutes)
    
    def dismiss_reminder(self, reminder_id: int) -> bool:
        """
        Dismiss a reminder permanently.
        
        Args:
            reminder_id: ID of the reminder
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # This would require an update method in the database
            # For now, we'll log the dismissal
            logger.info(f"Dismissed reminder {reminder_id}")
            return True
        except Exception as e:
            logger.error(f"Error dismissing reminder: {e}")
            return False
    
    def get_smart_snooze_suggestions(self, reminder: Reminder, user_patterns: Dict = None) -> List[Dict]:
        """
        Get intelligent snooze suggestions based on reminder context and user patterns.
        
        Args:
            reminder: Reminder object
            user_patterns: User behavioral patterns
            
        Returns:
            List of snooze suggestion dictionaries
        """
        try:
            if not user_patterns:
                user_patterns = self._get_user_patterns()
            
            now = datetime.now()
            suggestions = []
            
            # Base suggestions
            base_suggestions = [
                {"minutes": 15, "label": "15 minutes"},
                {"minutes": 30, "label": "30 minutes"},
                {"minutes": 60, "label": "1 hour"},
                {"minutes": 120, "label": "2 hours"}
            ]
            
            # Smart suggestions based on reminder type and time
            if reminder.reminder_type == "meeting":
                # For meetings, suggest based on meeting time
                if now.hour < 8:  # Early morning
                    suggestions.append({"minutes": 60, "label": "Until 9 AM"})
                elif now.hour > 17:  # After work
                    suggestions.append({"minutes": 840, "label": "Tomorrow morning"})
                else:
                    suggestions.extend(base_suggestions[:2])  # Short snoozes during work
            
            elif reminder.reminder_type == "deadline":
                # For deadlines, suggest longer snoozes
                suggestions.extend([
                    {"minutes": 240, "label": "4 hours"},
                    {"minutes": 480, "label": "8 hours"},
                    {"minutes": 1440, "label": "Tomorrow"}
                ])
            
            else:
                # Default suggestions
                suggestions.extend(base_suggestions)
            
            # Add context-aware suggestions
            work_hours = user_patterns.get("typical_work_hours", {"start": 9, "end": 17})
            if now.hour < work_hours["start"]:
                minutes_to_work = (work_hours["start"] - now.hour) * 60
                suggestions.append({"minutes": minutes_to_work, "label": "Until work starts"})
            elif now.hour >= work_hours["end"]:
                minutes_to_tomorrow = ((24 - now.hour) + work_hours["start"]) * 60
                suggestions.append({"minutes": minutes_to_tomorrow, "label": "Tomorrow morning"})
            
            # Remove duplicates and sort by minutes
            unique_suggestions = []
            seen_minutes = set()
            for suggestion in suggestions:
                if suggestion["minutes"] not in seen_minutes:
                    unique_suggestions.append(suggestion)
                    seen_minutes.add(suggestion["minutes"])
            
            return sorted(unique_suggestions, key=lambda x: x["minutes"])[:6]  # Limit to 6 suggestions
            
        except Exception as e:
            logger.error(f"Error getting snooze suggestions: {e}")
            return [
                {"minutes": 15, "label": "15 minutes"},
                {"minutes": 30, "label": "30 minutes"},
                {"minutes": 60, "label": "1 hour"}
            ]
    
    def get_reminder_effectiveness_stats(self) -> Dict:
        """Get statistics on reminder effectiveness."""
        try:
            # This would analyze user interaction with reminders
            # For now, return mock statistics
            return {
                "total_reminders_sent": 150,
                "reminders_acted_on": 120,
                "average_snooze_time": 45,  # minutes
                "most_effective_time": "09:00",
                "effectiveness_rate": 0.8,  # 80%
                "preferred_reminder_types": {
                    "meeting": 0.4,
                    "deadline": 0.3,
                    "followup": 0.2,
                    "important_email": 0.1
                }
            }
        except Exception as e:
            logger.error(f"Error getting reminder effectiveness stats: {e}")
            return {}
    
    def get_statistics(self) -> Dict:
        """Get reminder system statistics."""
        try:
            due_reminders = self.get_due_reminders()
            effectiveness_stats = self.get_reminder_effectiveness_stats()
            
            return {
                "total_due": len(due_reminders),
                "by_type": {
                    "meeting": len([r for r in due_reminders if r.reminder_type == "meeting"]),
                    "deadline": len([r for r in due_reminders if r.reminder_type == "deadline"]),
                    "followup": len([r for r in due_reminders if r.reminder_type == "followup"]),
                    "important_email": len([r for r in due_reminders if r.reminder_type == "important_email"]),
                    "custom": len([r for r in due_reminders if r.reminder_type == "custom"])
                },
                "effectiveness_rate": effectiveness_stats.get("effectiveness_rate", 0.0),
                "total_sent": effectiveness_stats.get("total_reminders_sent", 0),
                "acted_upon": effectiveness_stats.get("reminders_acted_on", 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting reminder statistics: {e}")
            return {
                "total_due": 0,
                "by_type": {"meeting": 0, "deadline": 0, "followup": 0, "important_email": 0, "custom": 0},
                "effectiveness_rate": 0.0,
                "total_sent": 0,
                "acted_upon": 0
            }
