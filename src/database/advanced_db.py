"""
Advanced database operations for follow-ups, reminders, feedback, and RLHF personalization.
Extends the learning database with enhanced tracking capabilities.
"""

import sqlite3
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
from loguru import logger

from .learning_db import get_learning_db


@dataclass
class FollowUp:
    """Represents a follow-up item."""
    id: Optional[int] = None
    email_id: str = ""
    thread_id: str = ""
    subject: str = ""
    recipient: str = ""
    follow_up_date: datetime = None
    reminder_date: datetime = None
    status: str = "pending"  # pending, completed, overdue, cancelled
    notes: str = ""
    priority: str = "medium"  # low, medium, high, urgent
    created_at: datetime = None
    updated_at: datetime = None


@dataclass
class Reminder:
    """Represents a reminder item."""
    id: Optional[int] = None
    email_id: str = ""
    thread_id: str = ""
    title: str = ""
    description: str = ""
    reminder_time: datetime = None
    status: str = "active"  # active, completed, snoozed, dismissed
    snooze_until: Optional[datetime] = None
    reminder_type: str = "followup"  # followup, deadline, meeting, custom
    created_at: datetime = None


@dataclass
class UserFeedback:
    """Represents user feedback on AI performance."""
    id: Optional[int] = None
    email_id: str = ""
    feature_type: str = ""  # analysis, reply_generation, threading, etc.
    rating: int = 0  # 1-5 scale
    feedback_text: str = ""
    improvement_suggestion: str = ""
    ai_response_quality: int = 0  # 1-5 scale
    user_satisfaction: int = 0  # 1-5 scale
    context_data: str = ""  # JSON string with context
    created_at: datetime = None


@dataclass
class PersonalizationProfile:
    """User personalization profile for RLHF."""
    id: Optional[int] = None
    user_email: str = ""
    communication_style: str = "professional"  # professional, casual, formal, friendly
    preferred_tone: str = "balanced"  # formal, casual, friendly, direct, polite
    response_length: str = "medium"  # short, medium, long
    urgency_sensitivity: float = 0.5  # 0.0 to 1.0
    category_preferences: str = ""  # JSON string
    learned_patterns: str = ""  # JSON string with learned preferences
    ai_confidence_threshold: float = 0.7  # Minimum confidence for auto-actions
    feedback_score: float = 0.0  # Average feedback score
    interaction_count: int = 0
    last_updated: datetime = None


class AdvancedDatabase:
    """Advanced database operations for enhanced features."""
    
    def __init__(self, db_path: str = "data/advanced.db"):
        """Initialize the advanced database."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()
    
    def init_database(self):
        """Initialize database tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS follow_ups (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email_id TEXT NOT NULL,
                        thread_id TEXT,
                        subject TEXT NOT NULL,
                        recipient TEXT NOT NULL,
                        follow_up_date TIMESTAMP,
                        reminder_date TIMESTAMP,
                        status TEXT DEFAULT 'pending',
                        notes TEXT,
                        priority TEXT DEFAULT 'medium',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS reminders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email_id TEXT,
                        thread_id TEXT,
                        title TEXT NOT NULL,
                        description TEXT,
                        reminder_time TIMESTAMP NOT NULL,
                        status TEXT DEFAULT 'active',
                        snooze_until TIMESTAMP,
                        reminder_type TEXT DEFAULT 'custom',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_feedback (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email_id TEXT,
                        feature_type TEXT NOT NULL,
                        rating INTEGER CHECK(rating >= 1 AND rating <= 5),
                        feedback_text TEXT,
                        improvement_suggestion TEXT,
                        ai_response_quality INTEGER CHECK(ai_response_quality >= 1 AND ai_response_quality <= 5),
                        user_satisfaction INTEGER CHECK(user_satisfaction >= 1 AND user_satisfaction <= 5),
                        context_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS personalization_profiles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_email TEXT UNIQUE NOT NULL,
                        communication_style TEXT DEFAULT 'professional',
                        preferred_tone TEXT DEFAULT 'balanced',
                        response_length TEXT DEFAULT 'medium',
                        urgency_sensitivity REAL DEFAULT 0.5,
                        category_preferences TEXT DEFAULT '{}',
                        learned_patterns TEXT DEFAULT '{}',
                        ai_confidence_threshold REAL DEFAULT 0.7,
                        feedback_score REAL DEFAULT 0.0,
                        interaction_count INTEGER DEFAULT 0,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes for better performance
                conn.execute("CREATE INDEX IF NOT EXISTS idx_follow_ups_date ON follow_ups(follow_up_date)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_follow_ups_status ON follow_ups(status)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_reminders_time ON reminders(reminder_time)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_feature ON user_feedback(feature_type)")
                
                conn.commit()
                logger.info("Advanced database initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing advanced database: {e}")
            raise
    
    # Follow-up operations
    def create_follow_up(self, follow_up: FollowUp) -> int:
        """Create a new follow-up item."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO follow_ups 
                    (email_id, thread_id, subject, recipient, follow_up_date, 
                     reminder_date, status, notes, priority)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    follow_up.email_id, follow_up.thread_id, follow_up.subject,
                    follow_up.recipient, follow_up.follow_up_date,
                    follow_up.reminder_date, follow_up.status,
                    follow_up.notes, follow_up.priority
                ))
                follow_up_id = cursor.lastrowid
                conn.commit()
                logger.info(f"Created follow-up {follow_up_id}")
                return follow_up_id
                
        except Exception as e:
            logger.error(f"Error creating follow-up: {e}")
            return -1
    
    def get_pending_follow_ups(self) -> List[FollowUp]:
        """Get all pending follow-ups."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM follow_ups 
                    WHERE status IN ('pending', 'overdue')
                    ORDER BY follow_up_date ASC
                """)
                
                follow_ups = []
                for row in cursor.fetchall():
                    follow_up = FollowUp(
                        id=row['id'],
                        email_id=row['email_id'],
                        thread_id=row['thread_id'],
                        subject=row['subject'],
                        recipient=row['recipient'],
                        follow_up_date=datetime.fromisoformat(row['follow_up_date']) if row['follow_up_date'] else None,
                        reminder_date=datetime.fromisoformat(row['reminder_date']) if row['reminder_date'] else None,
                        status=row['status'],
                        notes=row['notes'] or "",
                        priority=row['priority'],
                        created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                        updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
                    )
                    follow_ups.append(follow_up)
                
                return follow_ups
                
        except Exception as e:
            logger.error(f"Error getting pending follow-ups: {e}")
            return []
    
    def get_overdue_follow_ups(self) -> List[FollowUp]:
        """Get overdue follow-ups."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                now = datetime.now()
                cursor = conn.execute("""
                    SELECT * FROM follow_ups 
                    WHERE follow_up_date < ? AND status = 'pending'
                    ORDER BY follow_up_date ASC
                """, (now,))
                
                overdue_items = []
                for row in cursor.fetchall():
                    follow_up = FollowUp(
                        id=row['id'],
                        email_id=row['email_id'],
                        thread_id=row['thread_id'],
                        subject=row['subject'],
                        recipient=row['recipient'],
                        follow_up_date=datetime.fromisoformat(row['follow_up_date']) if row['follow_up_date'] else None,
                        reminder_date=datetime.fromisoformat(row['reminder_date']) if row['reminder_date'] else None,
                        status='overdue',  # Update status
                        notes=row['notes'] or "",
                        priority=row['priority'],
                        created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                        updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
                    )
                    overdue_items.append(follow_up)
                
                # Update status in database
                if overdue_items:
                    overdue_ids = [item.id for item in overdue_items]
                    placeholders = ','.join(['?'] * len(overdue_ids))
                    conn.execute(f"""
                        UPDATE follow_ups SET status = 'overdue', updated_at = ?
                        WHERE id IN ({placeholders})
                    """, [datetime.now()] + overdue_ids)
                    conn.commit()
                
                return overdue_items
                
        except Exception as e:
            logger.error(f"Error getting overdue follow-ups: {e}")
            return []
    
    def update_follow_up_status(self, follow_up_id: int, status: str) -> bool:
        """Update follow-up status."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE follow_ups 
                    SET status = ?, updated_at = ?
                    WHERE id = ?
                """, (status, datetime.now(), follow_up_id))
                conn.commit()
                logger.info(f"Updated follow-up {follow_up_id} status to {status}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating follow-up status: {e}")
            return False
    
    # Reminder operations
    def create_reminder(self, reminder: Reminder) -> int:
        """Create a new reminder."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO reminders 
                    (email_id, thread_id, title, description, reminder_time, 
                     status, reminder_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    reminder.email_id, reminder.thread_id, reminder.title,
                    reminder.description, reminder.reminder_time,
                    reminder.status, reminder.reminder_type
                ))
                reminder_id = cursor.lastrowid
                conn.commit()
                logger.info(f"Created reminder {reminder_id}")
                return reminder_id
                
        except Exception as e:
            logger.error(f"Error creating reminder: {e}")
            return -1
    
    def get_due_reminders(self) -> List[Reminder]:
        """Get reminders that are due."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                now = datetime.now()
                cursor = conn.execute("""
                    SELECT * FROM reminders 
                    WHERE reminder_time <= ? AND status = 'active'
                    ORDER BY reminder_time ASC
                """, (now,))
                
                reminders = []
                for row in cursor.fetchall():
                    reminder = Reminder(
                        id=row['id'],
                        email_id=row['email_id'],
                        thread_id=row['thread_id'],
                        title=row['title'],
                        description=row['description'] or "",
                        reminder_time=datetime.fromisoformat(row['reminder_time']),
                        status=row['status'],
                        snooze_until=datetime.fromisoformat(row['snooze_until']) if row['snooze_until'] else None,
                        reminder_type=row['reminder_type'],
                        created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
                    )
                    reminders.append(reminder)
                
                return reminders
                
        except Exception as e:
            logger.error(f"Error getting due reminders: {e}")
            return []
    
    def snooze_reminder(self, reminder_id: int, snooze_minutes: int) -> bool:
        """Snooze a reminder for specified minutes."""
        try:
            snooze_until = datetime.now() + timedelta(minutes=snooze_minutes)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE reminders 
                    SET status = 'snoozed', snooze_until = ?
                    WHERE id = ?
                """, (snooze_until, reminder_id))
                conn.commit()
                logger.info(f"Snoozed reminder {reminder_id} until {snooze_until}")
                return True
                
        except Exception as e:
            logger.error(f"Error snoozing reminder: {e}")
            return False
    
    # Feedback operations
    def store_user_feedback(self, feedback: UserFeedback) -> int:
        """Store user feedback."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO user_feedback 
                    (email_id, feature_type, rating, feedback_text, 
                     improvement_suggestion, ai_response_quality, 
                     user_satisfaction, context_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    feedback.email_id, feedback.feature_type, feedback.rating,
                    feedback.feedback_text, feedback.improvement_suggestion,
                    feedback.ai_response_quality, feedback.user_satisfaction,
                    feedback.context_data
                ))
                feedback_id = cursor.lastrowid
                conn.commit()
                logger.info(f"Stored user feedback {feedback_id}")
                return feedback_id
                
        except Exception as e:
            logger.error(f"Error storing user feedback: {e}")
            return -1
    
    def get_feedback_analytics(self) -> Dict:
        """Get feedback analytics summary."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Overall statistics
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_feedback,
                        AVG(rating) as avg_rating,
                        AVG(ai_response_quality) as avg_ai_quality,
                        AVG(user_satisfaction) as avg_satisfaction
                    FROM user_feedback
                """)
                overall = cursor.fetchone()
                
                # Feature breakdown
                cursor = conn.execute("""
                    SELECT feature_type, COUNT(*) as count, AVG(rating) as avg_rating
                    FROM user_feedback
                    GROUP BY feature_type
                    ORDER BY count DESC
                """)
                feature_breakdown = cursor.fetchall()
                
                return {
                    'total_feedback': overall['total_feedback'],
                    'average_rating': round(overall['avg_rating'] or 0, 2),
                    'average_ai_quality': round(overall['avg_ai_quality'] or 0, 2),
                    'average_satisfaction': round(overall['avg_satisfaction'] or 0, 2),
                    'feature_breakdown': [dict(row) for row in feature_breakdown]
                }
                
        except Exception as e:
            logger.error(f"Error getting feedback analytics: {e}")
            return {}
    
    # Personalization operations
    def get_or_create_profile(self, user_email: str) -> PersonalizationProfile:
        """Get or create user personalization profile."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM personalization_profiles WHERE user_email = ?
                """, (user_email,))
                
                row = cursor.fetchone()
                if row:
                    return PersonalizationProfile(
                        id=row['id'],
                        user_email=row['user_email'],
                        communication_style=row['communication_style'],
                        preferred_tone=row['preferred_tone'],
                        response_length=row['response_length'],
                        urgency_sensitivity=row['urgency_sensitivity'],
                        category_preferences=row['category_preferences'],
                        learned_patterns=row['learned_patterns'],
                        ai_confidence_threshold=row['ai_confidence_threshold'],
                        feedback_score=row['feedback_score'],
                        interaction_count=row['interaction_count'],
                        last_updated=datetime.fromisoformat(row['last_updated']) if row['last_updated'] else None
                    )
                else:
                    # Create new profile
                    profile = PersonalizationProfile(user_email=user_email)
                    cursor = conn.execute("""
                        INSERT INTO personalization_profiles (user_email)
                        VALUES (?)
                    """, (user_email,))
                    profile.id = cursor.lastrowid
                    conn.commit()
                    logger.info(f"Created new personalization profile for {user_email}")
                    return profile
                
        except Exception as e:
            logger.error(f"Error getting/creating personalization profile: {e}")
            return PersonalizationProfile(user_email=user_email)
    
    def update_personalization_profile(self, profile: PersonalizationProfile) -> bool:
        """Update user personalization profile."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE personalization_profiles 
                    SET communication_style = ?, preferred_tone = ?, 
                        response_length = ?, urgency_sensitivity = ?,
                        category_preferences = ?, learned_patterns = ?,
                        ai_confidence_threshold = ?, feedback_score = ?,
                        interaction_count = ?, last_updated = ?
                    WHERE user_email = ?
                """, (
                    profile.communication_style, profile.preferred_tone,
                    profile.response_length, profile.urgency_sensitivity,
                    profile.category_preferences, profile.learned_patterns,
                    profile.ai_confidence_threshold, profile.feedback_score,
                    profile.interaction_count, datetime.now(),
                    profile.user_email
                ))
                conn.commit()
                logger.info(f"Updated personalization profile for {profile.user_email}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating personalization profile: {e}")
            return False
    
    def learn_from_feedback(self, user_email: str, feedback: UserFeedback) -> bool:
        """Learn from user feedback and update personalization."""
        try:
            profile = self.get_or_create_profile(user_email)
            
            # Update interaction count and feedback score
            profile.interaction_count += 1
            total_score = profile.feedback_score * (profile.interaction_count - 1) + feedback.rating
            profile.feedback_score = total_score / profile.interaction_count
            
            # Parse context data to learn patterns
            if feedback.context_data:
                try:
                    context = json.loads(feedback.context_data)
                    learned_patterns = json.loads(profile.learned_patterns) if profile.learned_patterns else {}
                    
                    # Learn from AI response quality feedback
                    if feedback.feature_type == "reply_generation" and feedback.ai_response_quality >= 4:
                        # High-rated reply, learn the tone preference
                        tone_used = context.get('tone', 'professional')
                        learned_patterns.setdefault('preferred_tones', {})[tone_used] = \
                            learned_patterns.get('preferred_tones', {}).get(tone_used, 0) + 1
                    
                    # Learn urgency sensitivity
                    if feedback.feature_type == "analysis" and 'urgency_classification' in context:
                        if feedback.rating >= 4:  # User agreed with urgency
                            urgency_context = context['urgency_classification']
                            if urgency_context == 'urgent' and feedback.rating == 5:
                                profile.urgency_sensitivity = min(1.0, profile.urgency_sensitivity + 0.1)
                            elif urgency_context == 'low' and feedback.rating == 5:
                                profile.urgency_sensitivity = max(0.0, profile.urgency_sensitivity - 0.1)
                    
                    profile.learned_patterns = json.dumps(learned_patterns)
                    
                except json.JSONDecodeError:
                    logger.warning("Failed to parse feedback context data")
            
            # Adjust AI confidence threshold based on feedback
            if feedback.user_satisfaction <= 2:
                profile.ai_confidence_threshold = min(0.9, profile.ai_confidence_threshold + 0.05)
            elif feedback.user_satisfaction >= 4:
                profile.ai_confidence_threshold = max(0.5, profile.ai_confidence_threshold - 0.02)
            
            return self.update_personalization_profile(profile)
            
        except Exception as e:
            logger.error(f"Error learning from feedback: {e}")
            return False


# Global advanced database instance
_advanced_db = None

def get_advanced_db() -> AdvancedDatabase:
    """Get the global advanced database instance."""
    global _advanced_db
    if _advanced_db is None:
        _advanced_db = AdvancedDatabase()
    return _advanced_db
