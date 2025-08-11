"""
Overdue detector for identifying and managing overdue tasks and deadlines.
Monitors emails for deadlines and tracks overdue items with escalation.
"""

import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from loguru import logger

from ..database.advanced_db import AdvancedDatabase, FollowUp
from ..core.email_service import EmailData
from ..ai.gemini_service import GeminiEmailAI


class OverdueDetector:
    """Detects and manages overdue tasks and deadlines from emails."""
    
    def __init__(self, advanced_db: Optional[AdvancedDatabase] = None,
                 ai_service: Optional[GeminiEmailAI] = None):
        """Initialize the overdue detector."""
        self.advanced_db = advanced_db or AdvancedDatabase()
        self.ai_service = ai_service or GeminiEmailAI()
        
    def extract_deadlines(self, email: EmailData) -> List[Dict]:
        """
        Extract deadlines and due dates from email content using AI.
        
        Args:
            email: Email data to analyze
            
        Returns:
            List of deadline dictionaries
        """
        try:
            # Create deadline extraction prompt
            prompt = f"""
            Analyze the following email to extract any deadlines, due dates, or time-sensitive requirements:
            
            From: {email.sender}
            Subject: {email.subject}
            Date: {email.date}
            Content: {email.content[:1500]}...
            
            Please identify any deadlines and respond in JSON format:
            {{
                "deadlines": [
                    {{
                        "description": "brief description of what's due",
                        "due_date": "YYYY-MM-DD HH:MM",
                        "urgency": "low/medium/high/critical",
                        "type": "deadline/meeting/submission/payment/response_required",
                        "confidence": 0.0-1.0
                    }}
                ]
            }}
            
            Look for patterns like:
            - "due by", "deadline", "must be completed by"
            - Specific dates and times
            - "end of day", "EOD", "COB"
            - Meeting times and dates
            - Payment due dates
            - Project milestones
            """
            
            response = self.ai_service.generate_content(prompt)
            
            try:
                result = json.loads(response)
                deadlines = result.get("deadlines", [])
                
                # Validate and parse dates
                validated_deadlines = []
                for deadline in deadlines:
                    try:
                        due_date_str = deadline.get("due_date", "")
                        if due_date_str:
                            # Try to parse the date
                            due_date = datetime.strptime(due_date_str, "%Y-%m-%d %H:%M")
                            deadline["due_date"] = due_date
                            deadline["email_id"] = email.id
                            deadline["email_subject"] = email.subject
                            deadline["email_sender"] = email.sender
                            validated_deadlines.append(deadline)
                    except ValueError:
                        # Try alternative date formats
                        try:
                            due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
                            deadline["due_date"] = due_date
                            deadline["email_id"] = email.id
                            deadline["email_subject"] = email.subject
                            deadline["email_sender"] = email.sender
                            validated_deadlines.append(deadline)
                        except ValueError:
                            logger.warning(f"Could not parse deadline date: {due_date_str}")
                            continue
                
                return validated_deadlines
                
            except json.JSONDecodeError:
                logger.warning("Failed to parse AI deadline extraction, using fallback")
                return self._fallback_deadline_extraction(email)
                
        except Exception as e:
            logger.error(f"Error extracting deadlines: {e}")
            return self._fallback_deadline_extraction(email)
    
    def _fallback_deadline_extraction(self, email: EmailData) -> List[Dict]:
        """Fallback deadline extraction using regex patterns."""
        content = email.content.lower()
        subject = email.subject.lower()
        text_to_analyze = f"{subject} {content}"
        
        deadlines = []
        
        # Common deadline patterns
        deadline_patterns = [
            r'due\s+(?:by\s+)?(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            r'deadline\s+(?:is\s+)?(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            r'must\s+be\s+(?:completed|submitted|sent)\s+by\s+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            r'(?:end\s+of\s+day|eod)\s+(?:on\s+)?(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            r'by\s+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
        ]
        
        urgency_keywords = {
            'critical': ['critical', 'asap', 'immediately', 'urgent'],
            'high': ['urgent', 'important', 'priority', 'soon'],
            'medium': ['needed', 'required', 'please'],
            'low': ['when possible', 'at your convenience']
        }
        
        for pattern in deadline_patterns:
            matches = re.finditer(pattern, text_to_analyze)
            for match in matches:
                date_str = match.group(1)
                try:
                    # Try to parse the date
                    for date_format in ['%m/%d/%Y', '%m-%d-%Y', '%d/%m/%Y', '%d-%m-%Y']:
                        try:
                            due_date = datetime.strptime(date_str, date_format)
                            if due_date.year < 100:  # Handle 2-digit years
                                due_date = due_date.replace(year=due_date.year + 2000)
                            
                            # Determine urgency
                            urgency = 'medium'
                            for level, keywords in urgency_keywords.items():
                                if any(keyword in text_to_analyze for keyword in keywords):
                                    urgency = level
                                    break
                            
                            deadlines.append({
                                'description': f'Deadline from: {email.subject[:50]}...',
                                'due_date': due_date,
                                'urgency': urgency,
                                'type': 'deadline',
                                'confidence': 0.7,
                                'email_id': email.id,
                                'email_subject': email.subject,
                                'email_sender': email.sender
                            })
                            break
                        except ValueError:
                            continue
                except Exception:
                    continue
        
        return deadlines
    
    def check_overdue_items(self) -> List[Dict]:
        """
        Check for overdue follow-ups and deadlines.
        
        Returns:
            List of overdue items with details
        """
        try:
            current_time = datetime.now()
            overdue_items = []
            
            # Get overdue follow-ups from database
            overdue_followups = self.advanced_db.get_overdue_follow_ups()
            
            for followup in overdue_followups:
                overdue_days = (current_time - followup.follow_up_date).days if followup.follow_up_date else 0
                
                # Determine escalation level based on how overdue it is
                if overdue_days <= 1:
                    escalation = "low"
                elif overdue_days <= 3:
                    escalation = "medium"  
                elif overdue_days <= 7:
                    escalation = "high"
                else:
                    escalation = "critical"
                
                overdue_items.append({
                    'type': 'followup',
                    'id': followup.id,
                    'title': f"Follow-up: {followup.subject}",
                    'description': f"Follow-up with {followup.recipient}",
                    'due_date': followup.follow_up_date,
                    'overdue_days': overdue_days,
                    'escalation': escalation,
                    'priority': followup.priority,
                    'notes': followup.notes,
                    'recipient': followup.recipient,
                    'email_id': followup.email_id
                })
            
            return overdue_items
            
        except Exception as e:
            logger.error(f"Error checking overdue items: {e}")
            return []
    
    def escalate_overdue_item(self, item: Dict) -> bool:
        """
        Escalate an overdue item based on its priority and days overdue.
        
        Args:
            item: Overdue item dictionary
            
        Returns:
            True if escalated successfully, False otherwise
        """
        try:
            overdue_days = item.get('overdue_days', 0)
            current_escalation = item.get('escalation', 'low')
            
            # Determine new escalation level
            new_escalation = current_escalation
            action_taken = False
            
            if overdue_days > 7 and current_escalation != 'critical':
                new_escalation = 'critical'
                action_taken = True
                logger.warning(f"Escalating item {item.get('id')} to CRITICAL after {overdue_days} days")
                
            elif overdue_days > 3 and current_escalation not in ['high', 'critical']:
                new_escalation = 'high'
                action_taken = True
                logger.warning(f"Escalating item {item.get('id')} to HIGH after {overdue_days} days")
                
            elif overdue_days > 1 and current_escalation not in ['medium', 'high', 'critical']:
                new_escalation = 'medium'
                action_taken = True
                logger.info(f"Escalating item {item.get('id')} to MEDIUM after {overdue_days} days")
            
            if action_taken:
                # Update escalation in database if it's a follow-up
                if item.get('type') == 'followup':
                    # Note: This would require an update escalation method in the database
                    # For now, we'll just log the escalation
                    logger.info(f"Item {item.get('id')} escalated to {new_escalation}")
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error escalating overdue item: {e}")
            return False
    
    def get_overdue_summary(self) -> Dict:
        """
        Get a summary of all overdue items.
        
        Returns:
            Dictionary with overdue statistics
        """
        try:
            overdue_items = self.check_overdue_items()
            
            # Categorize by escalation level
            escalation_counts = {
                'low': 0,
                'medium': 0, 
                'high': 0,
                'critical': 0
            }
            
            priority_counts = {
                'low': 0,
                'medium': 0,
                'high': 0,
                'urgent': 0
            }
            
            total_overdue_days = 0
            
            for item in overdue_items:
                escalation = item.get('escalation', 'low')
                if escalation in escalation_counts:
                    escalation_counts[escalation] += 1
                
                priority = item.get('priority', 'medium')
                if priority in priority_counts:
                    priority_counts[priority] += 1
                
                total_overdue_days += item.get('overdue_days', 0)
            
            average_overdue_days = total_overdue_days / len(overdue_items) if overdue_items else 0
            
            return {
                'total_overdue': len(overdue_items),
                'escalation_breakdown': escalation_counts,
                'priority_breakdown': priority_counts,
                'average_overdue_days': round(average_overdue_days, 1),
                'critical_items': escalation_counts['critical'],
                'needs_immediate_attention': escalation_counts['critical'] + escalation_counts['high']
            }
            
        except Exception as e:
            logger.error(f"Error getting overdue summary: {e}")
            return {
                'total_overdue': 0,
                'escalation_breakdown': {'low': 0, 'medium': 0, 'high': 0, 'critical': 0},
                'priority_breakdown': {'low': 0, 'medium': 0, 'high': 0, 'urgent': 0},
                'average_overdue_days': 0,
                'critical_items': 0,
                'needs_immediate_attention': 0
            }
    
    def get_statistics(self) -> Dict:
        """Get overdue detection statistics."""
        return self.get_overdue_summary()
