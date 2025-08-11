"""
Gmail service for fetching, processing, and managing emails.
Integrates with the Gmail API to provide core email functionality.
"""

import base64
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import html2text
import re

from googleapiclient.errors import HttpError
from loguru import logger

from ..auth.google_auth import get_auth_service
from ..ai.gemini_service import GeminiEmailAI, EmailAnalysis, ThreadSummary
from ..database.learning_db import get_learning_db


@dataclass
class EmailData:
    """Structured email data."""
    id: str
    thread_id: str
    subject: str
    sender: str
    sender_name: str
    recipient: str
    date: datetime
    body: str
    snippet: str
    labels: List[str]
    is_unread: bool
    is_important: bool
    attachments: List[Dict] = None
    analysis: Optional[EmailAnalysis] = None


class EmailService:
    """Service for managing Gmail operations and AI-powered email processing."""
    
    def __init__(self):
        """Initialize the email service."""
        self.auth_service = get_auth_service()
        self.ai_service = None  # Will be initialized when needed
        self._gmail_service = None
        self.learning_db = get_learning_db()
    
    def _get_gmail_service(self):
        """Get the Gmail API service."""
        if self._gmail_service is None:
            self._gmail_service = self.auth_service.get_gmail_service()
        return self._gmail_service
    
    def _get_ai_service(self) -> GeminiEmailAI:
        """Get the AI service, initializing if needed."""
        if self.ai_service is None:
            try:
                self.ai_service = GeminiEmailAI()
            except Exception as e:
                logger.error(f"Failed to initialize AI service: {e}")
                raise
        return self.ai_service
    
    def fetch_recent_emails(self, max_results: int = 50, days_back: int = 7) -> List[EmailData]:
        """
        Intelligently fetch recent emails, combining stored emails with new ones from Gmail.
        
        Args:
            max_results: Maximum number of emails to return
            days_back: How many days back to search
        
        Returns:
            List of EmailData objects with AI analysis
        """
        try:
            # First, get stored emails from database
            stored_emails = self._get_stored_emails_with_analysis(max_results, days_back)
            
            # Get set of stored email IDs to avoid duplicates
            stored_email_ids = self.learning_db.get_stored_email_ids(days_back)
            
            # Fetch new emails from Gmail API
            new_emails = self._fetch_new_emails_from_gmail(max_results, days_back, stored_email_ids)
            
            # Store new emails in database
            for email_data in new_emails:
                self.learning_db.store_email(email_data)
            
            # Combine stored and new emails
            all_emails = stored_emails + new_emails
            
            # Sort by date (most recent first) and limit results
            all_emails.sort(key=lambda x: x.date.replace(tzinfo=None) if x.date.tzinfo else x.date, reverse=True)
            final_emails = all_emails[:max_results]
            
            logger.info(f"Loaded {len(stored_emails)} stored emails and fetched {len(new_emails)} new emails")
            logger.info(f"Returning {len(final_emails)} total emails")
            
            return final_emails
            
        except Exception as e:
            logger.error(f"Error in intelligent email fetching: {e}")
            # Fallback to traditional fetch if smart fetch fails
            logger.info("Falling back to traditional email fetch")
            return self._fetch_emails_traditional(max_results, days_back)
    
    def _get_stored_emails_with_analysis(self, max_results: int, days_back: int) -> List[EmailData]:
        """
        Get stored emails from database and convert to EmailData objects with analysis.
        
        Args:
            max_results: Maximum number of emails to return
            days_back: How many days back to search
        
        Returns:
            List of EmailData objects with analysis attached
        """
        stored_email_dicts = self.learning_db.get_stored_emails(max_results, days_back)
        email_objects = []
        
        for email_dict in stored_email_dicts:
            try:
                # Convert database dict to EmailData object
                # Handle date conversion (ensure it's a datetime object)
                email_date = email_dict['date']
                if isinstance(email_date, str):
                    try:
                        # Try multiple date parsing approaches
                        try:
                            from dateutil import parser
                            email_date = parser.parse(email_date)
                        except ImportError:
                            # Fallback if dateutil is not available
                            email_date = datetime.fromisoformat(email_date.replace('Z', '+00:00'))
                    except:
                        # If all parsing fails, use current time
                        email_date = datetime.now()
                elif email_date is None:
                    email_date = datetime.now()
                
                # Normalize timezone-aware to timezone-naive for consistency
                if hasattr(email_date, 'tzinfo') and email_date.tzinfo is not None:
                    email_date = email_date.replace(tzinfo=None)
                
                email_data = EmailData(
                    id=email_dict['email_id'],
                    thread_id=email_dict['thread_id'],
                    subject=email_dict['subject'],
                    sender=email_dict['sender'],
                    sender_name=email_dict['sender_name'],
                    recipient=email_dict['recipient'],
                    date=email_date,
                    body=email_dict['body'],
                    snippet=email_dict['snippet'],
                    labels=email_dict['labels'],
                    is_unread=email_dict['is_unread'],
                    is_important=email_dict['is_important'],
                    attachments=email_dict['attachments'] or []
                )
                
                # Try to get existing analysis for this email
                email_with_analysis = self.learning_db.get_email_with_analysis(email_dict['email_id'])
                if email_with_analysis and email_with_analysis.get('urgency'):
                    # Reconstruct EmailAnalysis object
                    from ..ai.gemini_service import EmailUrgency, EmailCategory
                    try:
                        analysis = EmailAnalysis(
                            urgency=EmailUrgency(email_with_analysis['urgency']),
                            category=EmailCategory(email_with_analysis['category']),
                            confidence=email_with_analysis['confidence'],
                            reasoning=email_with_analysis['reasoning'],
                            action_required=email_with_analysis['action_required'],
                            key_points=email_with_analysis['key_points'] or []
                        )
                        email_data.analysis = analysis
                    except (ValueError, KeyError) as e:
                        logger.warning(f"Could not reconstruct analysis for email {email_dict['email_id']}: {e}")
                
                email_objects.append(email_data)
                
            except Exception as e:
                logger.warning(f"Could not convert stored email to EmailData: {e}")
                continue
        
        logger.debug(f"Converted {len(email_objects)} stored emails to EmailData objects")
        return email_objects
    
    def _fetch_new_emails_from_gmail(self, max_results: int, days_back: int, 
                                   stored_email_ids: set) -> List[EmailData]:
        """
        Fetch only new emails from Gmail that aren't already stored.
        
        Args:
            max_results: Maximum number of emails to fetch
            days_back: How many days back to search
            stored_email_ids: Set of email IDs already in database
        
        Returns:
            List of new EmailData objects
        """
        try:
            service = self._get_gmail_service()
            
            # Calculate date range
            after_date = datetime.now() - timedelta(days=days_back)
            after_timestamp = int(after_date.timestamp())
            
            # Search query - fetch more than needed since some will be filtered out
            query = f'after:{after_timestamp}'
            
            # Get message list
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results * 2  # Fetch more to account for filtering
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                logger.info("No new emails found in Gmail")
                return []
            
            # Filter out emails we already have and fetch details for new ones
            new_emails = []
            fetched_count = 0
            
            for msg in messages:
                if msg['id'] in stored_email_ids:
                    continue  # Skip emails we already have
                
                if fetched_count >= max_results:
                    break  # Don't fetch more than needed
                
                try:
                    email_data = self._fetch_email_details(msg['id'])
                    if email_data:
                        new_emails.append(email_data)
                        fetched_count += 1
                except Exception as e:
                    logger.warning(f"Failed to fetch new email {msg['id']}: {e}")
                    continue
            
            logger.info(f"Fetched {len(new_emails)} new emails from Gmail")
            return new_emails
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching new emails: {e}")
            return []
    
    def _fetch_emails_traditional(self, max_results: int, days_back: int) -> List[EmailData]:
        """
        Traditional email fetch as fallback (original implementation).
        
        Args:
            max_results: Maximum number of emails to fetch
            days_back: How many days back to search
        
        Returns:
            List of EmailData objects
        """
        try:
            service = self._get_gmail_service()
            
            # Calculate date range
            after_date = datetime.now() - timedelta(days=days_back)
            after_timestamp = int(after_date.timestamp())
            
            # Search query
            query = f'after:{after_timestamp}'
            
            # Get message list
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                logger.info("No recent emails found")
                return []
            
            # Fetch detailed email data
            emails = []
            for msg in messages:
                try:
                    email_data = self._fetch_email_details(msg['id'])
                    if email_data:
                        emails.append(email_data)
                except Exception as e:
                    logger.warning(f"Failed to fetch email {msg['id']}: {e}")
                    continue
            
            logger.info(f"Fetched {len(emails)} emails successfully (traditional)")
            return emails
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            raise
    
    def _fetch_email_details(self, message_id: str) -> Optional[EmailData]:
        """
        Fetch detailed information for a specific email.
        
        Args:
            message_id: Gmail message ID
        
        Returns:
            EmailData object or None if failed
        """
        try:
            service = self._get_gmail_service()
            
            # Get message details
            message = service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Extract headers
            headers = {h['name']: h['value'] for h in message['payload']['headers']}
            
            # Extract basic info
            subject = headers.get('Subject', 'No Subject')
            sender = headers.get('From', 'Unknown Sender')
            sender_name = self._extract_sender_name(sender)
            recipient = headers.get('To', '')
            date_str = headers.get('Date', '')
            
            # Parse date
            try:
                date = email.utils.parsedate_to_datetime(date_str)
            except:
                date = datetime.now()
            
            # Extract body
            body = self._extract_body(message['payload'])
            
            # Extract labels and flags
            labels = message.get('labelIds', [])
            is_unread = 'UNREAD' in labels
            is_important = 'IMPORTANT' in labels
            
            # Create email data object
            email_data = EmailData(
                id=message_id,
                thread_id=message['threadId'],
                subject=subject,
                sender=sender,
                sender_name=sender_name,
                recipient=recipient,
                date=date,
                body=body,
                snippet=message.get('snippet', ''),
                labels=labels,
                is_unread=is_unread,
                is_important=is_important,
                attachments=self._extract_attachments(message['payload'])
            )
            
            return email_data
            
        except Exception as e:
            logger.error(f"Failed to fetch email details for {message_id}: {e}")
            return None
    
    def _extract_sender_name(self, sender: str) -> str:
        """Extract sender name from email address string."""
        # Handle formats like "John Doe <john@example.com>" or "john@example.com"
        match = re.match(r'^([^<]+)<([^>]+)>$', sender.strip())
        if match:
            return match.group(1).strip().strip('"')
        return sender.split('@')[0] if '@' in sender else sender
    
    def _extract_body(self, payload: Dict) -> str:
        """Extract email body from payload."""
        body = ""
        
        if 'parts' in payload:
            # Multipart message
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        data = part['body']['data']
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
                        break
                elif part['mimeType'] == 'text/html':
                    if 'data' in part['body']:
                        data = part['body']['data']
                        html_body = base64.urlsafe_b64decode(data).decode('utf-8')
                        # Convert HTML to text
                        h = html2text.HTML2Text()
                        h.ignore_links = True
                        body = h.handle(html_body)
        else:
            # Single part message
            if payload['mimeType'] == 'text/plain':
                if 'data' in payload['body']:
                    data = payload['body']['data']
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
            elif payload['mimeType'] == 'text/html':
                if 'data' in payload['body']:
                    data = payload['body']['data']
                    html_body = base64.urlsafe_b64decode(data).decode('utf-8')
                    h = html2text.HTML2Text()
                    h.ignore_links = True
                    body = h.handle(html_body)
        
        return body.strip() if body else ""
    
    def _extract_attachments(self, payload: Dict) -> List[Dict]:
        """Extract attachment information from email payload."""
        attachments = []
        
        def extract_from_parts(parts):
            for part in parts:
                if part.get('filename'):
                    attachments.append({
                        'filename': part['filename'],
                        'mime_type': part['mimeType'],
                        'size': part['body'].get('size', 0),
                        'attachment_id': part['body'].get('attachmentId')
                    })
                if 'parts' in part:
                    extract_from_parts(part['parts'])
        
        if 'parts' in payload:
            extract_from_parts(payload['parts'])
        
        return attachments
    
    def analyze_email_with_ai(self, email_data: EmailData) -> EmailData:
        """
        Analyze an email using AI and update the email data with results.
        
        Args:
            email_data: EmailData object to analyze
        
        Returns:
            Updated EmailData object with AI analysis
        """
        try:
            ai_service = self._get_ai_service()
            
            # Prepare email data for AI analysis
            ai_input = {
                'subject': email_data.subject,
                'body': email_data.body,
                'sender': email_data.sender,
                'date': email_data.date.isoformat(),
                'thread_id': email_data.thread_id
            }
            
            # Perform AI analysis
            analysis = ai_service.analyze_email(ai_input)
            email_data.analysis = analysis
            
            logger.debug(f"AI analysis completed for email {email_data.id}")
            return email_data
            
        except Exception as e:
            logger.error(f"AI analysis failed for email {email_data.id}: {e}")
            return email_data
    
    def analyze_emails_with_ai_batch(self, emails: List[EmailData], batch_size: int = 5) -> List[EmailData]:
        """
        Analyze multiple emails using AI in batches for improved efficiency.
        
        Args:
            emails: List of EmailData objects to analyze
            batch_size: Number of emails to analyze in each batch
        
        Returns:
            List of EmailData objects with AI analysis attached
        """
        try:
            ai_service = self._get_ai_service()
            
            # Prepare emails for batch analysis - only analyze those without existing analysis
            emails_to_analyze = []
            email_indices = []  # Track which emails need analysis
            
            for i, email_data in enumerate(emails):
                if not email_data.analysis:  # Only analyze if no existing analysis
                    # Prepare email data for AI analysis
                    ai_input = {
                        'subject': email_data.subject,
                        'body': email_data.body,
                        'sender': email_data.sender,
                        'date': email_data.date.isoformat(),
                        'thread_id': email_data.thread_id
                    }
                    emails_to_analyze.append(ai_input)
                    email_indices.append(i)
            
            if not emails_to_analyze:
                logger.info("All emails already have analysis, skipping batch analysis")
                return emails
            
            logger.info(f"Starting batch analysis of {len(emails_to_analyze)} emails")
            
            # Perform batch analysis
            analyses = ai_service.analyze_emails_batch(emails_to_analyze, batch_size)
            
            # Attach analyses to corresponding emails
            for i, analysis in enumerate(analyses):
                if i < len(email_indices):
                    original_index = email_indices[i]
                    emails[original_index].analysis = analysis
            
            logger.info(f"Completed batch analysis of {len(analyses)} emails")
            return emails
            
        except Exception as e:
            logger.error(f"Batch AI analysis failed: {e}")
            # Fall back to individual analysis for emails without analysis
            for email_data in emails:
                if not email_data.analysis:
                    try:
                        analyzed_email = self.analyze_email_with_ai(email_data)
                        email_data.analysis = analyzed_email.analysis
                    except Exception as individual_error:
                        logger.error(f"Individual analysis also failed for {email_data.id}: {individual_error}")
            return emails
    
    def fetch_thread_emails(self, thread_id: str) -> List[EmailData]:
        """
        Fetch all emails in a thread.
        
        Args:
            thread_id: Gmail thread ID
        
        Returns:
            List of EmailData objects in chronological order
        """
        try:
            service = self._get_gmail_service()
            
            # Get thread details
            thread = service.users().threads().get(
                userId='me',
                id=thread_id,
                format='full'
            ).execute()
            
            emails = []
            for message in thread['messages']:
                email_data = self._parse_message_from_thread(message)
                if email_data:
                    emails.append(email_data)
            
            # Sort by date
            emails.sort(key=lambda x: x.date.replace(tzinfo=None) if x.date.tzinfo else x.date)
            
            logger.info(f"Fetched {len(emails)} emails from thread {thread_id}")
            return emails
            
        except Exception as e:
            logger.error(f"Failed to fetch thread {thread_id}: {e}")
            return []
    
    def _parse_message_from_thread(self, message: Dict) -> Optional[EmailData]:
        """Parse a message from a thread response."""
        try:
            # Extract headers
            headers = {h['name']: h['value'] for h in message['payload']['headers']}
            
            # Extract basic info
            subject = headers.get('Subject', 'No Subject')
            sender = headers.get('From', 'Unknown Sender')
            sender_name = self._extract_sender_name(sender)
            recipient = headers.get('To', '')
            date_str = headers.get('Date', '')
            
            # Parse date
            try:
                date = email.utils.parsedate_to_datetime(date_str)
            except:
                date = datetime.now()
            
            # Extract body
            body = self._extract_body(message['payload'])
            
            # Extract labels and flags
            labels = message.get('labelIds', [])
            is_unread = 'UNREAD' in labels
            is_important = 'IMPORTANT' in labels
            
            return EmailData(
                id=message['id'],
                thread_id=message['threadId'],
                subject=subject,
                sender=sender,
                sender_name=sender_name,
                recipient=recipient,
                date=date,
                body=body,
                snippet=message.get('snippet', ''),
                labels=labels,
                is_unread=is_unread,
                is_important=is_important,
                attachments=self._extract_attachments(message['payload'])
            )
            
        except Exception as e:
            logger.error(f"Failed to parse message from thread: {e}")
            return None
    
    def summarize_thread_with_ai(self, thread_id: str) -> ThreadSummary:
        """
        Generate an AI summary of an email thread.
        
        Args:
            thread_id: Gmail thread ID
        
        Returns:
            ThreadSummary object
        """
        try:
            # Fetch all emails in thread
            emails = self.fetch_thread_emails(thread_id)
            
            if not emails:
                return ThreadSummary(
                    summary="No emails found in thread",
                    key_decisions=[],
                    action_items=[],
                    open_questions=[],
                    participants=[]
                )
            
            # Prepare data for AI
            ai_input = []
            for email_data in emails:
                ai_input.append({
                    'subject': email_data.subject,
                    'body': email_data.body,
                    'sender': email_data.sender,
                    'date': email_data.date.isoformat()
                })
            
            # Generate AI summary
            ai_service = self._get_ai_service()
            summary = ai_service.summarize_thread(ai_input)
            
            logger.info(f"Thread summary generated for {thread_id}")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to summarize thread {thread_id}: {e}")
            return ThreadSummary(
                summary=f"Error generating summary: {str(e)}",
                key_decisions=[],
                action_items=[],
                open_questions=[],
                participants=[]
            )
    
    def send_email(self, to: str, subject: str, body: str, 
                   reply_to_message_id: Optional[str] = None) -> bool:
        """
        Send an email via Gmail API.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body
            reply_to_message_id: If replying, the original message ID
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            service = self._get_gmail_service()
            
            # Create message
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            
            # If replying, add reference headers
            if reply_to_message_id:
                # Get original message to extract Message-ID and References
                original = service.users().messages().get(
                    userId='me',
                    id=reply_to_message_id,
                    format='full'
                ).execute()
                
                original_headers = {h['name']: h['value'] 
                                  for h in original['payload']['headers']}
                
                message_id = original_headers.get('Message-ID')
                if message_id:
                    message['In-Reply-To'] = message_id
                    message['References'] = message_id
                
                # Update subject with Re: if not already present
                if not subject.startswith('Re:'):
                    message['subject'] = f"Re: {subject}"
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')
            
            # Send message
            send_result = service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            logger.info(f"Email sent successfully. Message ID: {send_result['id']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def mark_as_read(self, message_id: str) -> bool:
        """Mark an email as read in Gmail and update database."""
        try:
            service = self._get_gmail_service()
            
            service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            
            # Also update in database if email is stored there
            try:
                self.learning_db.update_email_status(message_id, is_unread=False)
            except Exception as db_e:
                logger.warning(f"Failed to update email status in database: {db_e}")
            
            logger.debug(f"Marked email {message_id} as read")
            return True
            
        except Exception as e:
            logger.error(f"Failed to mark email {message_id} as read: {e}")
            return False
    
    def send_reply(self, original_message_id: str, thread_id: str, 
                   subject: str, body: str, to: str) -> bool:
        """
        Send a reply to an email.
        
        Args:
            original_message_id: ID of the original message being replied to
            thread_id: Thread ID for the conversation
            subject: Reply subject
            body: Reply body content
            to: Recipient email address
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            service = self._get_gmail_service()
            
            # Get original message to extract headers
            original = service.users().messages().get(
                userId='me',
                id=original_message_id,
                format='full'
            ).execute()
            
            original_headers = {h['name']: h['value'] 
                              for h in original['payload']['headers']}
            
            # Create reply message
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject if subject.startswith('Re:') else f"Re: {subject}"
            
            # Add reply headers
            message_id = original_headers.get('Message-ID')
            if message_id:
                message['In-Reply-To'] = message_id
                
                # Handle References header
                references = original_headers.get('References', '')
                if references:
                    message['References'] = f"{references} {message_id}"
                else:
                    message['References'] = message_id
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')
            
            # Send reply with thread ID
            send_result = service.users().messages().send(
                userId='me',
                body={
                    'raw': raw_message,
                    'threadId': thread_id
                }
            ).execute()
            
            logger.info(f"Reply sent successfully. Message ID: {send_result['id']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send reply: {e}")
            return False
    
    def add_label(self, message_id: str, label: str) -> bool:
        """Add a label to an email."""
        try:
            service = self._get_gmail_service()
            
            service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': [label]}
            ).execute()
            
            logger.debug(f"Added label {label} to email {message_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add label {label} to email {message_id}: {e}")
            return False
    
    def delete_email(self, message_id: str) -> bool:
        """Delete an email from Gmail and update database."""
        try:
            service = self._get_gmail_service()
            
            # Move to trash using TRASH label
            service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': ['TRASH']}
            ).execute()
            
            # Also remove from database if email is stored there
            try:
                self.learning_db.delete_email(message_id)
            except Exception as db_e:
                logger.warning(f"Failed to delete email from database: {db_e}")
            
            logger.info(f"Deleted email {message_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete email {message_id}: {e}")
            return False


# Global email service instance
_email_service = None

def get_email_service() -> EmailService:
    """Get the global email service instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
