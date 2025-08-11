"""
AI service using Google's Gemini API for email analysis and processing.
Implements the core AI functionality for email triage, summarization, and response generation.
"""

import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import google.generativeai as genai
from loguru import logger

from ..core.config import get_settings


class EmailUrgency(Enum):
    """Email urgency classification levels."""
    URGENT = "urgent"
    TO_RESPOND = "to_respond"
    FYI = "fyi"
    MEETING = "meeting"
    SPAM = "spam"


class EmailCategory(Enum):
    """Email category classification."""
    WORK = "work"
    PERSONAL = "personal"
    MARKETING = "marketing"
    SECURITY = "security"
    MEETING_REQUEST = "meeting_request"
    TASK_ASSIGNMENT = "task_assignment"
    INFORMATION = "information"
    URGENT_DECISION = "urgent_decision"


@dataclass
class EmailAnalysis:
    """Results of AI email analysis."""
    urgency: EmailUrgency
    category: EmailCategory
    confidence: float
    reasoning: str
    action_required: str
    deadline: Optional[str] = None
    key_points: List[str] = None
    suggested_response: Optional[str] = None


@dataclass
class ThreadSummary:
    """AI-generated thread summary."""
    summary: str
    key_decisions: List[str]
    action_items: List[str]
    open_questions: List[str]
    participants: List[str]


class GeminiEmailAI:
    """AI service using Google's Gemini API for email processing."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Gemini AI service."""
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key if settings else None
        
        if not self.api_key:
            raise ValueError("Gemini API key is required")
        
        # Initialize the Gemini client
        try:
            genai.configure(api_key=self.api_key)
            # Use Gemma-3 model
            self.model = genai.GenerativeModel('gemma-3-27b-it')
            logger.info("Gemini AI service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            raise
    
    def analyze_email(self, email_data: Dict) -> EmailAnalysis:
        """
        Analyze an email and classify its urgency, category, and extract key information.
        
        Args:
            email_data: Dictionary containing email information
                       Expected keys: subject, body, sender, date, thread_id
        
        Returns:
            EmailAnalysis object with classification and reasoning
        """
        try:
            prompt = self._build_analysis_prompt(email_data)
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=1000,
                )
            )
            
            # Parse the structured response
            analysis = self._parse_analysis_response(response.text)
            
            logger.info(f"Email analyzed - Urgency: {analysis.urgency.value}, "
                       f"Category: {analysis.category.value}, "
                       f"Confidence: {analysis.confidence}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing email: {e}")
            # Return a default analysis in case of error
            return EmailAnalysis(
                urgency=EmailUrgency.FYI,
                category=EmailCategory.INFORMATION,
                confidence=0.1,
                reasoning=f"Error in analysis: {str(e)}",
                action_required="Manual review required",
                key_points=[]
            )
    
    def analyze_emails_batch(self, emails_data: List[Dict], batch_size: int = 5) -> List[EmailAnalysis]:
        """
        Analyze multiple emails in batches for improved efficiency.
        
        Args:
            emails_data: List of email dictionaries to analyze
            batch_size: Number of emails to analyze in each batch
        
        Returns:
            List of EmailAnalysis objects corresponding to input emails
        """
        all_analyses = []
        total_emails = len(emails_data)
        
        logger.info(f"Starting batch analysis of {total_emails} emails in batches of {batch_size}")
        
        for i in range(0, total_emails, batch_size):
            batch = emails_data[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_emails + batch_size - 1) // batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} emails)")
            
            try:
                batch_analyses = self._analyze_email_batch(batch)
                all_analyses.extend(batch_analyses)
                
                logger.info(f"Successfully analyzed batch {batch_num}/{total_batches}")
                
            except Exception as e:
                logger.error(f"Error analyzing batch {batch_num}: {e}")
                # Add default analyses for failed batch
                for email_data in batch:
                    default_analysis = EmailAnalysis(
                        urgency=EmailUrgency.FYI,
                        category=EmailCategory.INFORMATION,
                        confidence=0.1,
                        reasoning=f"Batch analysis failed: {str(e)}",
                        action_required="Manual review required",
                        key_points=[]
                    )
                    all_analyses.append(default_analysis)
        
        logger.info(f"Completed batch analysis of {len(all_analyses)} emails")
        return all_analyses
    
    def _analyze_email_batch(self, batch_emails: List[Dict]) -> List[EmailAnalysis]:
        """
        Analyze a batch of emails with a single AI request.
        
        Args:
            batch_emails: List of email dictionaries to analyze
        
        Returns:
            List of EmailAnalysis objects
        """
        try:
            prompt = self._build_batch_analysis_prompt(batch_emails)
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=3000,  # Increased for batch processing
                )
            )
            
            # Parse the batch response
            analyses = self._parse_batch_analysis_response(response.text, len(batch_emails))
            
            return analyses
            
        except Exception as e:
            logger.error(f"Error in batch analysis: {e}")
            # Return default analyses for all emails in batch
            return [EmailAnalysis(
                urgency=EmailUrgency.FYI,
                category=EmailCategory.INFORMATION,
                confidence=0.1,
                reasoning=f"Batch analysis error: {str(e)}",
                action_required="Manual review required",
                key_points=[]
            ) for _ in batch_emails]
    
    def summarize_thread(self, thread_emails: List[Dict]) -> ThreadSummary:
        """
        Generate a summary of an email thread.
        
        Args:
            thread_emails: List of email dictionaries in chronological order
        
        Returns:
            ThreadSummary object with key information extracted
        """
        try:
            prompt = self._build_thread_summary_prompt(thread_emails)
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=1500,
                )
            )
            
            summary = self._parse_thread_summary_response(response.text)
            
            logger.info(f"Thread summarized - {len(thread_emails)} emails processed")
            return summary
            
        except Exception as e:
            logger.error(f"Error summarizing thread: {e}")
            return ThreadSummary(
                summary=f"Error generating summary: {str(e)}",
                key_decisions=[],
                action_items=[],
                open_questions=[],
                participants=[]
            )
    
    def generate_response_draft(self, email_data: Dict, context: Dict = None) -> str:
        """
        Generate a draft response to an email.
        
        Args:
            email_data: Original email data
            context: Additional context like user preferences, relationship, etc.
        
        Returns:
            Generated response draft
        """
        try:
            prompt = self._build_response_prompt(email_data, context)
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.4,
                    max_output_tokens=800,
                )
            )
            
            draft = response.text.strip()
            
            logger.info("Response draft generated successfully")
            return draft
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return f"Error generating response: {str(e)}"
    
    def extract_meeting_details(self, email_data: Dict) -> Dict:
        """
        Extract meeting details from an email.
        
        Args:
            email_data: Email containing meeting information
        
        Returns:
            Dictionary with meeting details
        """
        try:
            prompt = self._build_meeting_extraction_prompt(email_data)
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=600,
                )
            )
            
            meeting_details = self._parse_meeting_details_response(response.text)
            
            logger.info("Meeting details extracted successfully")
            return meeting_details
            
        except Exception as e:
            logger.error(f"Error extracting meeting details: {e}")
            return {"error": str(e)}
    
    def _build_analysis_prompt(self, email_data: Dict) -> str:
        """Build the prompt for email analysis."""
        return f"""
Analyze this email and provide a structured classification:

SUBJECT: {email_data.get('subject', 'No subject')}
FROM: {email_data.get('sender', 'Unknown sender')}
DATE: {email_data.get('date', 'Unknown date')}
BODY: {email_data.get('body', 'No content')}

Please analyze and respond with EXACTLY this JSON format:
{{
    "urgency": "urgent|to_respond|fyi|meeting|spam",
    "category": "work|personal|marketing|security|meeting_request|task_assignment|information|urgent_decision",
    "confidence": 0.95,
    "reasoning": "Clear explanation of why this classification was chosen",
    "action_required": "Specific action the user should take",
    "deadline": "extracted deadline if any, null otherwise",
    "key_points": ["point 1", "point 2", "point 3"]
}}

Classification Guidelines:
- URGENT: Requires immediate action within hours, has deadlines, from VIPs, contains urgent keywords
- TO_RESPOND: Needs a response but not urgent, questions, requests
- FYI: Informational, no action required
- MEETING: Meeting invitations, calendar requests
- SPAM: Promotional, marketing, suspicious content

Focus on being accurate and explain your reasoning clearly.
"""
    
    def _build_thread_summary_prompt(self, thread_emails: List[Dict]) -> str:
        """Build prompt for thread summarization."""
        thread_text = ""
        for i, email in enumerate(thread_emails):
            thread_text += f"\n--- Email {i+1} ---\n"
            thread_text += f"From: {email.get('sender', 'Unknown')}\n"
            thread_text += f"Date: {email.get('date', 'Unknown')}\n"
            thread_text += f"Subject: {email.get('subject', 'No subject')}\n"
            thread_text += f"Content: {email.get('body', 'No content')}\n"
        
        return f"""
Analyze this email thread and provide a comprehensive summary:

{thread_text}

Please respond with EXACTLY this JSON format:
{{
    "summary": "Concise 2-3 sentence summary of the entire thread",
    "key_decisions": ["decision 1", "decision 2"],
    "action_items": ["action 1", "action 2"],
    "open_questions": ["question 1", "question 2"],
    "participants": ["person1@email.com", "person2@email.com"]
}}

Focus on extracting the most important information that would help someone quickly understand what happened in this conversation.
"""
    
    def _build_response_prompt(self, email_data: Dict, context: Dict = None) -> str:
        """Build prompt for response generation."""
        context = context or {}
        tone = context.get('tone', 'professional')
        relationship = context.get('relationship', 'colleague')
        
        return f"""
Generate a professional response to this email:

ORIGINAL EMAIL:
Subject: {email_data.get('subject', 'No subject')}
From: {email_data.get('sender', 'Unknown sender')}
Content: {email_data.get('body', 'No content')}

CONTEXT:
- Tone: {tone}
- Relationship: {relationship}
- User preferences: {context.get('preferences', 'Standard professional communication')}

Generate a draft response that:
1. Acknowledges the original message appropriately
2. Addresses key points or questions
3. Maintains the requested tone
4. Is concise but complete
5. Includes appropriate closing

Return only the email content, no additional formatting or explanations.
"""
    
    def _build_meeting_extraction_prompt(self, email_data: Dict) -> str:
        """Build prompt for meeting detail extraction."""
        return f"""
Extract meeting details from this email:

SUBJECT: {email_data.get('subject', 'No subject')}
FROM: {email_data.get('sender', 'Unknown sender')}
CONTENT: {email_data.get('body', 'No content')}

Please respond with EXACTLY this JSON format:
{{
    "title": "Meeting title",
    "date": "YYYY-MM-DD or null if not specified",
    "time": "HH:MM or null if not specified",
    "duration": "duration in minutes or null",
    "location": "location or 'virtual' or null",
    "participants": ["email1", "email2"],
    "agenda_items": ["item 1", "item 2"],
    "is_meeting_request": true,
    "requires_response": true
}}

Extract only information that is clearly stated. Use null for unclear or missing information.
"""
    
    def _build_batch_analysis_prompt(self, batch_emails: List[Dict]) -> str:
        """Build the prompt for batch email analysis."""
        emails_text = ""
        for i, email_data in enumerate(batch_emails):
            emails_text += f"\n--- EMAIL {i+1} ---\n"
            emails_text += f"SUBJECT: {email_data.get('subject', 'No subject')}\n"
            emails_text += f"FROM: {email_data.get('sender', 'Unknown sender')}\n"
            emails_text += f"DATE: {email_data.get('date', 'Unknown date')}\n"
            emails_text += f"BODY: {email_data.get('body', 'No content')}\n"
        
        return f"""
Analyze these {len(batch_emails)} emails and provide structured classification for each:

{emails_text}

Please analyze and respond with EXACTLY this JSON format (array of analyses):
[
  {{
    "email_number": 1,
    "urgency": "urgent|to_respond|fyi|meeting|spam",
    "category": "work|personal|marketing|security|meeting_request|task_assignment|information|urgent_decision",
    "confidence": 0.95,
    "reasoning": "Clear explanation of why this classification was chosen",
    "action_required": "Specific action the user should take",
    "deadline": "extracted deadline if any, null otherwise",
    "key_points": ["point 1", "point 2", "point 3"]
  }},
  {{
    "email_number": 2,
    "urgency": "urgent|to_respond|fyi|meeting|spam",
    "category": "work|personal|marketing|security|meeting_request|task_assignment|information|urgent_decision",
    "confidence": 0.85,
    "reasoning": "Clear explanation of why this classification was chosen",
    "action_required": "Specific action the user should take",
    "deadline": "extracted deadline if any, null otherwise",
    "key_points": ["point 1", "point 2"]
  }}
]

Classification Guidelines:
- URGENT: Requires immediate action within hours, has deadlines, from VIPs, contains urgent keywords
- TO_RESPOND: Needs a response but not urgent, questions, requests
- FYI: Informational, no action required
- MEETING: Meeting invitations, calendar requests
- SPAM: Promotional, marketing, suspicious content

Provide analysis for ALL {len(batch_emails)} emails in the same order they appear above.
"""
    
    def _parse_batch_analysis_response(self, response_text: str, expected_count: int) -> List[EmailAnalysis]:
        """Parse the batch analysis response."""
        try:
            # Clean the response text
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith('```'):
                response_text = response_text[3:-3].strip()
            
            data = json.loads(response_text)
            
            analyses = []
            for item in data:
                try:
                    # Parse with validation and correction
                    urgency_value = item.get('urgency', 'fyi').lower()
                    category_value = item.get('category', 'information').lower()
                    
                    # Map common mistakes
                    urgency_mapping = {
                        'marketing': 'spam',  # Fix common AI mistake
                        'promotional': 'spam',
                        'newsletter': 'spam'
                    }
                    
                    category_mapping = {
                        'urgent': 'urgent_decision',  # Fix common AI mistake
                        'spam': 'marketing'
                    }
                    
                    # Apply mappings
                    urgency_value = urgency_mapping.get(urgency_value, urgency_value)
                    category_value = category_mapping.get(category_value, category_value)
                    
                    # Validate against enum values
                    valid_urgencies = [e.value for e in EmailUrgency]
                    valid_categories = [e.value for e in EmailCategory]
                    
                    if urgency_value not in valid_urgencies:
                        logger.warning(f"Invalid urgency '{urgency_value}', defaulting to 'fyi'")
                        urgency_value = 'fyi'
                    
                    if category_value not in valid_categories:
                        logger.warning(f"Invalid category '{category_value}', defaulting to 'information'")
                        category_value = 'information'
                    
                    analysis = EmailAnalysis(
                        urgency=EmailUrgency(urgency_value),
                        category=EmailCategory(category_value),
                        confidence=float(item.get('confidence', 0.5)),
                        reasoning=item.get('reasoning', 'AI analysis completed'),
                        action_required=item.get('action_required', 'Review email'),
                        deadline=item.get('deadline'),
                        key_points=item.get('key_points', [])
                    )
                    analyses.append(analysis)
                except (KeyError, ValueError, TypeError) as e:
                    logger.error(f"Error parsing individual analysis: {e}")
                    logger.debug(f"Problematic item: {item}")
                    # Add default analysis for this email
                    analyses.append(EmailAnalysis(
                        urgency=EmailUrgency.FYI,
                        category=EmailCategory.INFORMATION,
                        confidence=0.1,
                        reasoning=f"Failed to parse individual analysis: {str(e)}",
                        action_required="Manual review required",
                        key_points=[]
                    ))
            
            # Ensure we have the expected number of analyses
            while len(analyses) < expected_count:
                analyses.append(EmailAnalysis(
                    urgency=EmailUrgency.FYI,
                    category=EmailCategory.INFORMATION,
                    confidence=0.1,
                    reasoning="Missing analysis from batch response",
                    action_required="Manual review required",
                    key_points=[]
                ))
            
            return analyses[:expected_count]  # Trim to expected count if too many
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"Failed to parse batch analysis response: {e}")
            logger.debug(f"Response text: {response_text}")
            # Return default analyses for all emails
            return [EmailAnalysis(
                urgency=EmailUrgency.FYI,
                category=EmailCategory.INFORMATION,
                confidence=0.1,
                reasoning="Failed to parse batch response",
                action_required="Manual review required",
                key_points=[]
            ) for _ in range(expected_count)]
    
    def _parse_analysis_response(self, response_text: str) -> EmailAnalysis:
        """Parse the structured analysis response."""
        try:
            # Clean the response text
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith('```'):
                response_text = response_text[3:-3].strip()
            
            data = json.loads(response_text)
            
            return EmailAnalysis(
                urgency=EmailUrgency(data['urgency']),
                category=EmailCategory(data['category']),
                confidence=float(data['confidence']),
                reasoning=data['reasoning'],
                action_required=data['action_required'],
                deadline=data.get('deadline'),
                key_points=data.get('key_points', [])
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse analysis response: {e}")
            logger.debug(f"Response text: {response_text}")
            # Return default analysis
            return EmailAnalysis(
                urgency=EmailUrgency.FYI,
                category=EmailCategory.INFORMATION,
                confidence=0.1,
                reasoning="Failed to parse AI response",
                action_required="Manual review required",
                key_points=[]
            )
    
    def _parse_thread_summary_response(self, response_text: str) -> ThreadSummary:
        """Parse the thread summary response."""
        try:
            # Clean the response text
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith('```'):
                response_text = response_text[3:-3].strip()
            
            data = json.loads(response_text)
            
            return ThreadSummary(
                summary=data['summary'],
                key_decisions=data.get('key_decisions', []),
                action_items=data.get('action_items', []),
                open_questions=data.get('open_questions', []),
                participants=data.get('participants', [])
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse thread summary response: {e}")
            return ThreadSummary(
                summary="Failed to generate summary",
                key_decisions=[],
                action_items=[],
                open_questions=[],
                participants=[]
            )
    
    def _parse_meeting_details_response(self, response_text: str) -> Dict:
        """Parse the meeting details response."""
        try:
            # Clean the response text
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith('```'):
                response_text = response_text[3:-3].strip()
            
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse meeting details response: {e}")
            return {"error": "Failed to parse meeting details"}
