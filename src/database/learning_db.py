"""
Database service for storing user feedback, learning data, and email analysis history.
Implements the learning memory system for AI improvement.
"""

import sqlite3
import json
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from contextlib import contextmanager

from loguru import logger
from ..core.config import get_settings
from ..ai.gemini_service import EmailUrgency, EmailCategory, EmailAnalysis


@dataclass
class UserCorrection:
    """Represents a user correction to AI analysis."""
    id: Optional[int] = None
    email_id: str = ""
    original_urgency: str = ""
    corrected_urgency: str = ""
    original_category: str = ""
    corrected_category: str = ""
    user_feedback: str = ""
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class EmailAnalysisRecord:
    """Stored email analysis record."""
    id: Optional[int] = None
    email_id: str = ""
    thread_id: str = ""
    subject: str = ""
    sender: str = ""
    urgency: str = ""
    category: str = ""
    confidence: float = 0.0
    reasoning: str = ""
    action_required: str = ""
    key_points: str = ""  # JSON string
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class LearningDatabase:
    """Database service for AI learning and user feedback storage."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize the learning database."""
        if db_path is None:
            settings = get_settings()
            if settings:
                db_path = settings.database_path
            else:
                db_path = "data/email_manager.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._initialize_database()
        logger.info(f"Learning database initialized at {self.db_path}")
    
    def _initialize_database(self):
        """Create database tables if they don't exist."""
        with self._get_connection() as conn:
            # User corrections table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_corrections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_id TEXT NOT NULL,
                    original_urgency TEXT NOT NULL,
                    corrected_urgency TEXT NOT NULL,
                    original_category TEXT NOT NULL,
                    corrected_category TEXT NOT NULL,
                    user_feedback TEXT,
                    timestamp DATETIME NOT NULL,
                    UNIQUE(email_id, timestamp)
                )
            """)
            
            # Email analysis records table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS email_analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_id TEXT NOT NULL,
                    thread_id TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    urgency TEXT NOT NULL,
                    category TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    reasoning TEXT NOT NULL,
                    action_required TEXT NOT NULL,
                    key_points TEXT,
                    timestamp DATETIME NOT NULL,
                    UNIQUE(email_id)
                )
            """)
            
            # User preferences table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    preference_key TEXT NOT NULL UNIQUE,
                    preference_value TEXT NOT NULL,
                    timestamp DATETIME NOT NULL
                )
            """)
            
            # Sender patterns table (for learning sender importance)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sender_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_email TEXT NOT NULL,
                    sender_name TEXT,
                    typical_urgency TEXT NOT NULL,
                    typical_category TEXT NOT NULL,
                    interaction_count INTEGER DEFAULT 1,
                    last_seen DATETIME NOT NULL,
                    confidence_score REAL DEFAULT 0.5,
                    UNIQUE(sender_email)
                )
            """)
            
            # Emails table for storing actual email data
            conn.execute("""
                CREATE TABLE IF NOT EXISTS emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_id TEXT NOT NULL UNIQUE,
                    thread_id TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    sender_name TEXT,
                    recipient TEXT,
                    date DATETIME NOT NULL,
                    body TEXT,
                    snippet TEXT,
                    labels TEXT,
                    is_unread BOOLEAN DEFAULT 1,
                    is_important BOOLEAN DEFAULT 0,
                    attachments TEXT,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Thread summaries table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS thread_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id TEXT NOT NULL UNIQUE,
                    summary TEXT NOT NULL,
                    key_decisions TEXT,
                    action_items TEXT,
                    open_questions TEXT,
                    participants TEXT,
                    timestamp DATETIME NOT NULL
                )
            """)
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper error handling."""
        conn = sqlite3.connect(
            self.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def store_user_correction(self, correction: UserCorrection) -> int:
        """
        Store a user correction for learning purposes.
        
        Args:
            correction: UserCorrection object
        
        Returns:
            ID of the stored correction
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT OR REPLACE INTO user_corrections 
                (email_id, original_urgency, corrected_urgency, 
                 original_category, corrected_category, user_feedback, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                correction.email_id,
                correction.original_urgency,
                correction.corrected_urgency,
                correction.original_category,
                correction.corrected_category,
                correction.user_feedback,
                correction.timestamp
            ))
            conn.commit()
            
            correction_id = cursor.lastrowid
            logger.info(f"Stored user correction {correction_id} for email {correction.email_id}")
            return correction_id
    
    def store_email_analysis(self, email_id: str, thread_id: str, 
                           subject: str, sender: str, analysis: EmailAnalysis) -> int:
        """
        Store an email analysis record.
        
        Args:
            email_id: Email ID
            thread_id: Thread ID
            subject: Email subject
            sender: Sender email
            analysis: EmailAnalysis object
        
        Returns:
            ID of the stored analysis
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT OR REPLACE INTO email_analyses 
                (email_id, thread_id, subject, sender, urgency, category, 
                 confidence, reasoning, action_required, key_points, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                email_id,
                thread_id,
                subject,
                sender,
                analysis.urgency.value,
                analysis.category.value,
                analysis.confidence,
                analysis.reasoning,
                analysis.action_required,
                json.dumps(analysis.key_points) if analysis.key_points else None,
                datetime.now()
            ))
            conn.commit()
            
            analysis_id = cursor.lastrowid
            logger.debug(f"Stored email analysis {analysis_id} for email {email_id}")
            return analysis_id
    
    def get_sender_patterns(self, sender_email: str) -> Optional[Dict]:
        """
        Get historical patterns for a specific sender.
        
        Args:
            sender_email: Sender's email address
        
        Returns:
            Dictionary with sender patterns or None
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM sender_patterns WHERE sender_email = ?
            """, (sender_email,))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def update_sender_patterns(self, sender_email: str, sender_name: str,
                             urgency: EmailUrgency, category: EmailCategory):
        """
        Update sender patterns based on new interaction.
        
        Args:
            sender_email: Sender's email address
            sender_name: Sender's name
            urgency: Email urgency
            category: Email category
        """
        with self._get_connection() as conn:
            # Check if sender exists
            existing = self.get_sender_patterns(sender_email)
            
            if existing:
                # Update existing pattern
                new_count = existing['interaction_count'] + 1
                # Simple weighted average for confidence
                confidence = min(0.9, existing['confidence_score'] + 0.1)
                
                conn.execute("""
                    UPDATE sender_patterns 
                    SET sender_name = ?, typical_urgency = ?, typical_category = ?,
                        interaction_count = ?, last_seen = ?, confidence_score = ?
                    WHERE sender_email = ?
                """, (
                    sender_name,
                    urgency.value,
                    category.value,
                    new_count,
                    datetime.now(),
                    confidence,
                    sender_email
                ))
            else:
                # Create new pattern
                conn.execute("""
                    INSERT INTO sender_patterns 
                    (sender_email, sender_name, typical_urgency, typical_category,
                     interaction_count, last_seen, confidence_score)
                    VALUES (?, ?, ?, ?, 1, ?, 0.3)
                """, (
                    sender_email,
                    sender_name,
                    urgency.value,
                    category.value,
                    datetime.now()
                ))
            
            conn.commit()
            logger.debug(f"Updated sender patterns for {sender_email}")
    
    def get_user_corrections_for_learning(self, limit: int = 100) -> List[UserCorrection]:
        """
        Get recent user corrections for model learning.
        
        Args:
            limit: Maximum number of corrections to return
        
        Returns:
            List of UserCorrection objects
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM user_corrections 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
            
            corrections = []
            for row in cursor.fetchall():
                correction = UserCorrection(
                    id=row['id'],
                    email_id=row['email_id'],
                    original_urgency=row['original_urgency'],
                    corrected_urgency=row['corrected_urgency'],
                    original_category=row['original_category'],
                    corrected_category=row['corrected_category'],
                    user_feedback=row['user_feedback'],
                    timestamp=row['timestamp']
                )
                corrections.append(correction)
            
            return corrections
    
    def get_learning_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about learning progress.
        
        Returns:
            Dictionary with learning statistics
        """
        with self._get_connection() as conn:
            stats = {}
            
            # Total corrections
            cursor = conn.execute("SELECT COUNT(*) FROM user_corrections")
            stats['total_corrections'] = cursor.fetchone()[0]
            
            # Total analyses
            cursor = conn.execute("SELECT COUNT(*) FROM email_analyses")
            stats['total_analyses'] = cursor.fetchone()[0]
            
            # Unique senders
            cursor = conn.execute("SELECT COUNT(*) FROM sender_patterns")
            stats['unique_senders'] = cursor.fetchone()[0]
            
            # Correction accuracy (corrections where urgency/category changed)
            cursor = conn.execute("""
                SELECT COUNT(*) FROM user_corrections 
                WHERE original_urgency != corrected_urgency 
                   OR original_category != corrected_category
            """)
            stats['meaningful_corrections'] = cursor.fetchone()[0]
            
            # Average confidence
            cursor = conn.execute("SELECT AVG(confidence) FROM email_analyses")
            result = cursor.fetchone()[0]
            stats['average_confidence'] = round(result, 3) if result else 0.0
            
            # Most common urgency levels
            cursor = conn.execute("""
                SELECT urgency, COUNT(*) as count 
                FROM email_analyses 
                GROUP BY urgency 
                ORDER BY count DESC
            """)
            stats['urgency_distribution'] = dict(cursor.fetchall())
            
            return stats
    
    def store_user_preference(self, key: str, value: Any):
        """
        Store a user preference.
        
        Args:
            key: Preference key
            value: Preference value (will be JSON serialized)
        """
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_preferences 
                (preference_key, preference_value, timestamp)
                VALUES (?, ?, ?)
            """, (key, json.dumps(value), datetime.now()))
            conn.commit()
            logger.debug(f"Stored user preference: {key}")
    
    def get_user_preference(self, key: str, default: Any = None) -> Any:
        """
        Get a user preference.
        
        Args:
            key: Preference key
            default: Default value if not found
        
        Returns:
            Preference value or default
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT preference_value FROM user_preferences 
                WHERE preference_key = ?
            """, (key,))
            
            row = cursor.fetchone()
            if row:
                try:
                    return json.loads(row['preference_value'])
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in preference {key}")
                    return default
            return default
    
    def clean_old_records(self, days_to_keep: int = 90):
        """
        Clean old records from the database.
        
        Args:
            days_to_keep: Number of days of records to keep
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        with self._get_connection() as conn:
            # Clean old analyses
            cursor = conn.execute("""
                DELETE FROM email_analyses 
                WHERE timestamp < ?
            """, (cutoff_date,))
            analyses_deleted = cursor.rowcount
            
            # Clean old corrections (keep these longer)
            old_correction_cutoff = datetime.now() - timedelta(days=days_to_keep * 2)
            cursor = conn.execute("""
                DELETE FROM user_corrections 
                WHERE timestamp < ?
            """, (old_correction_cutoff,))
            corrections_deleted = cursor.rowcount
            
            conn.commit()
            
            logger.info(f"Cleaned {analyses_deleted} old analyses and "
                       f"{corrections_deleted} old corrections")
    
    def store_email(self, email_data) -> int:
        """
        Store an email in the database.
        
        Args:
            email_data: EmailData object containing email information
        
        Returns:
            ID of the stored email record
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT OR REPLACE INTO emails 
                (email_id, thread_id, subject, sender, sender_name, recipient,
                 date, body, snippet, labels, is_unread, is_important, attachments, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                email_data.id,
                email_data.thread_id,
                email_data.subject,
                email_data.sender,
                email_data.sender_name,
                email_data.recipient,
                email_data.date,
                email_data.body,
                email_data.snippet,
                json.dumps(email_data.labels) if email_data.labels else None,
                email_data.is_unread,
                email_data.is_important,
                json.dumps(email_data.attachments) if email_data.attachments else None,
                datetime.now()
            ))
            conn.commit()
            
            record_id = cursor.lastrowid
            logger.debug(f"Stored email {email_data.id} in database")
            return record_id
    
    def get_stored_emails(self, limit: int = 100, days_back: int = 30) -> List[Dict]:
        """
        Get stored emails from the database.
        
        Args:
            limit: Maximum number of emails to return
            days_back: How many days back to search
        
        Returns:
            List of email dictionaries from database
        """
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM emails 
                WHERE date >= ?
                ORDER BY date DESC
                LIMIT ?
            """, (cutoff_date, limit))
            
            emails = []
            for row in cursor.fetchall():
                email_dict = dict(row)
                # Parse JSON fields
                if email_dict['labels']:
                    email_dict['labels'] = json.loads(email_dict['labels'])
                else:
                    email_dict['labels'] = []
                    
                if email_dict['attachments']:
                    email_dict['attachments'] = json.loads(email_dict['attachments'])
                else:
                    email_dict['attachments'] = []
                    
                emails.append(email_dict)
            
            logger.debug(f"Retrieved {len(emails)} stored emails from database")
            return emails
    
    def get_latest_email_date(self) -> Optional[datetime]:
        """
        Get the date of the most recent email in the database.
        
        Returns:
            Datetime of the most recent email or None if no emails exist
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT MAX(date) FROM emails
            """)
            
            result = cursor.fetchone()[0]
            if result:
                return result
            return None
    
    def email_exists(self, email_id: str) -> bool:
        """
        Check if an email already exists in the database.
        
        Args:
            email_id: Gmail email ID
        
        Returns:
            True if email exists, False otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) FROM emails WHERE email_id = ?
            """, (email_id,))
            
            count = cursor.fetchone()[0]
            return count > 0
    
    def get_stored_email_ids(self, days_back: int = 30) -> set:
        """
        Get a set of all stored email IDs within the specified time range.
        
        Args:
            days_back: How many days back to search
        
        Returns:
            Set of email IDs that are already stored
        """
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT email_id FROM emails WHERE date >= ?
            """, (cutoff_date,))
            
            email_ids = {row[0] for row in cursor.fetchall()}
            logger.debug(f"Found {len(email_ids)} stored email IDs in database")
            return email_ids
    
    def update_email_status(self, email_id: str, is_unread: bool = None, is_important: bool = None):
        """
        Update email status flags.
        
        Args:
            email_id: Gmail email ID
            is_unread: New unread status (optional)
            is_important: New important status (optional)
        """
        updates = []
        params = []
        
        if is_unread is not None:
            updates.append("is_unread = ?")
            params.append(is_unread)
        
        if is_important is not None:
            updates.append("is_important = ?")
            params.append(is_important)
        
        if updates:
            updates.append("updated_at = ?")
            params.append(datetime.now())
            params.append(email_id)
            
            with self._get_connection() as conn:
                query = f"UPDATE emails SET {', '.join(updates)} WHERE email_id = ?"
                conn.execute(query, params)
                conn.commit()
                logger.debug(f"Updated email status for {email_id}")
    
    def get_email_with_analysis(self, email_id: str) -> Optional[Dict]:
        """
        Get a stored email with its AI analysis.
        
        Args:
            email_id: Gmail email ID
        
        Returns:
            Dictionary containing email data and analysis, or None
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT e.*, a.urgency, a.category, a.confidence, a.reasoning, 
                       a.action_required, a.key_points
                FROM emails e
                LEFT JOIN email_analyses a ON e.email_id = a.email_id
                WHERE e.email_id = ?
            """, (email_id,))
            
            row = cursor.fetchone()
            if row:
                email_dict = dict(row)
                # Parse JSON fields
                if email_dict['labels']:
                    email_dict['labels'] = json.loads(email_dict['labels'])
                else:
                    email_dict['labels'] = []
                    
                if email_dict['attachments']:
                    email_dict['attachments'] = json.loads(email_dict['attachments'])
                else:
                    email_dict['attachments'] = []
                    
                if email_dict['key_points']:
                    email_dict['key_points'] = json.loads(email_dict['key_points'])
                else:
                    email_dict['key_points'] = []
                
                return email_dict
            return None
    
    def clean_old_emails(self, days_to_keep: int = 90):
        """
        Clean old emails from the database.
        
        Args:
            days_to_keep: Number of days of emails to keep
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        with self._get_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM emails WHERE date < ?
            """, (cutoff_date,))
            emails_deleted = cursor.rowcount
            conn.commit()
            
            logger.info(f"Cleaned {emails_deleted} old emails from database")
    
    def delete_email(self, email_id: str):
        """
        Delete an email and its associated data from the database.
        
        Args:
            email_id: Gmail email ID
        """
        with self._get_connection() as conn:
            # Delete from emails table
            conn.execute("""
                DELETE FROM emails WHERE email_id = ?
            """, (email_id,))
            
            # Delete from email_analyses table
            conn.execute("""
                DELETE FROM email_analyses WHERE email_id = ?
            """, (email_id,))
            
            # Delete from user_corrections table
            conn.execute("""
                DELETE FROM user_corrections WHERE email_id = ?
            """, (email_id,))
            
            conn.commit()
            logger.debug(f"Deleted email {email_id} from database")
    
    def export_learning_data(self) -> Dict[str, Any]:
        """
        Export learning data for analysis or backup.
        
        Returns:
            Dictionary with all learning data
        """
        data = {}
        
        with self._get_connection() as conn:
            # Export corrections
            cursor = conn.execute("SELECT * FROM user_corrections")
            data['corrections'] = [dict(row) for row in cursor.fetchall()]
            
            # Export sender patterns
            cursor = conn.execute("SELECT * FROM sender_patterns")
            data['sender_patterns'] = [dict(row) for row in cursor.fetchall()]
            
            # Export preferences
            cursor = conn.execute("SELECT * FROM user_preferences")
            data['preferences'] = [dict(row) for row in cursor.fetchall()]
            
            # Export email count (not full content for privacy)
            cursor = conn.execute("SELECT COUNT(*) FROM emails")
            data['total_stored_emails'] = cursor.fetchone()[0]
            
            # Export statistics
            data['statistics'] = self.get_learning_statistics()
            data['export_timestamp'] = datetime.now().isoformat()
            
        return data


# Global database instance
_learning_db = None

def get_learning_db() -> LearningDatabase:
    """Get the global learning database instance."""
    global _learning_db
    if _learning_db is None:
        _learning_db = LearningDatabase()
    return _learning_db
