"""
Follow-up manager for tracking and managing email follow-ups.
Uses AI to determine follow-up requirements and optimal timing.
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from loguru import logger

from ..database.advanced_db import AdvancedDatabase, FollowUp
from ..core.email_service import EmailData
from ..ai.gemini_service import GeminiEmailAI


class FollowupManager:
    """Manages follow-up tracking and scheduling for emails."""
    
    def __init__(self, advanced_db: Optional[AdvancedDatabase] = None, 
                 ai_service: Optional[GeminiEmailAI] = None):
        """Initialize the follow-up manager."""
        self.advanced_db = advanced_db or AdvancedDatabase()
        self.ai_service = ai_service or GeminiEmailAI()
        
    def analyze_followup_requirements(self, email: EmailData) -> Dict:
        """
        Analyze if an email requires follow-up using AI.
        
        Args:
            email: Email data to analyze
            
        Returns:
            Dictionary with follow-up analysis results
        """
        try:
            # Create analysis prompt
            prompt = f"""
            Analyze the following email to determine if it requires follow-up action:
            
            From: {email.sender}
            Subject: {email.subject}
            Content: {email.content[:1000]}...
            
            Please analyze and respond in JSON format with:
            {{
                "requires_followup": true/false,
                "urgency": "low/medium/high/urgent",
                "suggested_days": number of days to wait before following up,
                "reason": "explanation of why follow-up is needed",
                "followup_type": "response_required/deadline_tracking/relationship_maintenance/project_update/meeting_scheduling"
            }}
            
            Consider factors like:
            - Questions that need answers
            - Pending decisions or approvals
            - Project deadlines mentioned
            - Meeting requests
            - Important relationships
            """
            
            response = self.ai_service.generate_content(prompt)
            
            # Parse the JSON response
            try:
                analysis = json.loads(response)
                return analysis
            except json.JSONDecodeError:
                # Fallback analysis if JSON parsing fails
                logger.warning("Failed to parse AI follow-up analysis, using fallback")
                return self._fallback_followup_analysis(email)
                
        except Exception as e:
            logger.error(f"Error analyzing follow-up requirements: {e}")
            return self._fallback_followup_analysis(email)
    
    def _fallback_followup_analysis(self, email: EmailData) -> Dict:
        """Fallback follow-up analysis using keyword detection."""
        content_lower = email.content.lower()
        subject_lower = email.subject.lower()
        
        # Check for follow-up indicators
        followup_keywords = [
            'please respond', 'get back to', 'let me know', 'waiting for',
            'deadline', 'due date', 'follow up', 'follow-up', 'meeting',
            'schedule', 'confirm', 'approval', 'decision', 'feedback'
        ]
        
        urgent_keywords = [
            'urgent', 'asap', 'immediately', 'deadline', 'critical',
            'important', 'priority', 'time-sensitive'
        ]
        
        requires_followup = any(keyword in content_lower or keyword in subject_lower 
                              for keyword in followup_keywords)
        
        is_urgent = any(keyword in content_lower or keyword in subject_lower 
                       for keyword in urgent_keywords)
        
        if requires_followup:
            urgency = "urgent" if is_urgent else "medium"
            suggested_days = 1 if is_urgent else 3
            return {
                "requires_followup": True,
                "urgency": urgency,
                "suggested_days": suggested_days,
                "reason": "Contains follow-up indicators",
                "followup_type": "response_required"
            }
        
        return {
            "requires_followup": False,
            "urgency": "low",
            "suggested_days": 7,
            "reason": "No clear follow-up indicators",
            "followup_type": "none"
        }
    
    def create_followup(self, email: EmailData, analysis: Dict = None) -> int:
        """
        Create a follow-up item for an email.
        
        Args:
            email: Email data
            analysis: Follow-up analysis results (optional)
            
        Returns:
            Follow-up ID if created successfully, -1 otherwise
        """
        try:
            if not analysis:
                analysis = self.analyze_followup_requirements(email)
            
            if not analysis.get("requires_followup", False):
                logger.info(f"No follow-up required for email {email.id}")
                return -1
            
            # Calculate follow-up and reminder dates
            suggested_days = analysis.get("suggested_days", 3)
            followup_date = datetime.now() + timedelta(days=suggested_days)
            reminder_date = followup_date - timedelta(days=1)  # Remind 1 day before
            
            # Create follow-up object
            followup = FollowUp(
                email_id=email.id,
                thread_id=email.thread_id,
                subject=email.subject,
                recipient=email.sender,
                follow_up_date=followup_date,
                reminder_date=reminder_date,
                status="pending",
                notes=analysis.get("reason", ""),
                priority=analysis.get("urgency", "medium"),
                created_at=datetime.now()
            )
            
            # Store in database
            followup_id = self.advanced_db.create_follow_up(followup)
            
            if followup_id > 0:
                logger.info(f"Created follow-up {followup_id} for email {email.id}")
            
            return followup_id
            
        except Exception as e:
            logger.error(f"Error creating follow-up: {e}")
            return -1
    
    def get_pending_followups(self) -> List[FollowUp]:
        """Get all pending follow-ups."""
        return self.advanced_db.get_pending_follow_ups()
    
    def get_overdue_followups(self) -> List[FollowUp]:
        """Get overdue follow-ups."""
        return self.advanced_db.get_overdue_follow_ups()
    
    def complete_followup(self, followup_id: int, notes: str = "") -> bool:
        """
        Mark a follow-up as completed.
        
        Args:
            followup_id: ID of the follow-up
            notes: Optional completion notes
            
        Returns:
            True if successful, False otherwise
        """
        return self.advanced_db.update_follow_up_status(followup_id, "completed")
    
    def snooze_followup(self, followup_id: int, days: int) -> bool:
        """
        Snooze a follow-up for specified days.
        
        Args:
            followup_id: ID of the follow-up
            days: Number of days to snooze
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the follow-up
            followups = self.get_pending_followups()
            target_followup = next((f for f in followups if f.id == followup_id), None)
            
            if not target_followup:
                return False
            
            # Update follow-up date
            new_followup_date = datetime.now() + timedelta(days=days)
            target_followup.follow_up_date = new_followup_date
            target_followup.reminder_date = new_followup_date - timedelta(days=1)
            
            # This would require an update method in the database
            # For now, we'll just log it
            logger.info(f"Snoozed follow-up {followup_id} for {days} days")
            return True
            
        except Exception as e:
            logger.error(f"Error snoozing follow-up: {e}")
            return False
    
    def get_statistics(self) -> Dict:
        """Get follow-up statistics."""
        try:
            pending = self.get_pending_followups()
            overdue = self.get_overdue_followups()
            
            return {
                "total_pending": len(pending),
                "overdue_count": len(overdue),
                "high_priority": len([f for f in pending if f.priority in ["high", "urgent"]]),
                "due_today": len([f for f in pending if f.follow_up_date and 
                                f.follow_up_date.date() == datetime.now().date()]),
                "due_this_week": len([f for f in pending if f.follow_up_date and 
                                    f.follow_up_date < datetime.now() + timedelta(days=7)])
            }
            
        except Exception as e:
            logger.error(f"Error getting follow-up statistics: {e}")
            return {
                "total_pending": 0,
                "overdue_count": 0,
                "high_priority": 0,
                "due_today": 0,
                "due_this_week": 0
            }
