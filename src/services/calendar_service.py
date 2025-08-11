"""
Google Calendar integration service for AI Email Manager.
Handles calendar operations, meeting scheduling, and event management.
"""

import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from googleapiclient.errors import HttpError
from loguru import logger

from ..auth.google_auth import get_auth_service
from ..ai.gemini_service import GeminiEmailAI


@dataclass
class CalendarEvent:
    """Represents a calendar event."""
    id: str
    title: str
    start_time: datetime
    end_time: datetime
    description: str = ""
    location: str = ""
    attendees: List[str] = None
    organizer: str = ""
    status: str = "confirmed"
    meeting_link: str = ""
    calendar_id: str = "primary"


@dataclass
class MeetingRequest:
    """Represents a meeting request extracted from email."""
    title: str
    proposed_times: List[datetime]
    duration_minutes: int = 60
    attendees: List[str] = None
    description: str = ""
    location: str = ""
    organizer_email: str = ""
    requires_response: bool = True


class CalendarService:
    """Handles Google Calendar operations and meeting management."""
    
    def __init__(self):
        """Initialize the Calendar service."""
        self.auth_service = get_auth_service()
        self._calendar_service = None
        
    def get_calendar_service(self):
        """Get authenticated Calendar API service."""
        if not self.auth_service.is_authenticated():
            raise ValueError("Not authenticated. Please authenticate first.")
        
        if self._calendar_service is None:
            self._calendar_service = self.auth_service.get_calendar_service()
        
        return self._calendar_service
    
    def get_upcoming_events(self, days_ahead: int = 7, max_results: int = 50) -> List[CalendarEvent]:
        """
        Get upcoming calendar events.
        
        Args:
            days_ahead: Number of days to look ahead
            max_results: Maximum number of events to return
            
        Returns:
            List of CalendarEvent objects
        """
        try:
            service = self.get_calendar_service()
            
            # Calculate time range
            now = datetime.now(timezone.utc)
            time_max = now + timedelta(days=days_ahead)
            
            # Fetch events
            events_result = service.events().list(
                calendarId='primary',
                timeMin=now.isoformat(),
                timeMax=time_max.isoformat(),
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Convert to CalendarEvent objects
            calendar_events = []
            for event in events:
                try:
                    calendar_event = self._parse_calendar_event(event)
                    calendar_events.append(calendar_event)
                except Exception as e:
                    logger.warning(f"Failed to parse calendar event: {e}")
                    continue
            
            logger.info(f"Retrieved {len(calendar_events)} upcoming events")
            return calendar_events
            
        except HttpError as e:
            logger.error(f"Calendar API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching calendar events: {e}")
            return []
    
    def check_availability(self, start_time: datetime, end_time: datetime, 
                          attendees: List[str] = None) -> Dict[str, bool]:
        """
        Check availability for a time slot.
        
        Args:
            start_time: Meeting start time
            end_time: Meeting end time
            attendees: List of attendee emails to check
            
        Returns:
            Dictionary mapping email addresses to availability (True = available)
        """
        try:
            service = self.get_calendar_service()
            
            # Prepare request body
            attendees = attendees or []
            request_body = {
                'timeMin': start_time.isoformat(),
                'timeMax': end_time.isoformat(),
                'items': [{'id': email} for email in attendees + ['primary']]
            }
            
            # Query free/busy information
            freebusy = service.freebusy().query(body=request_body).execute()
            
            availability = {}
            for email in attendees:
                busy_times = freebusy['calendars'].get(email, {}).get('busy', [])
                is_available = len(busy_times) == 0
                availability[email] = is_available
            
            # Check user's own availability
            primary_busy = freebusy['calendars'].get('primary', {}).get('busy', [])
            availability['primary'] = len(primary_busy) == 0
            
            logger.info(f"Availability check completed for {len(attendees)} attendees")
            return availability
            
        except HttpError as e:
            logger.error(f"Calendar API error during availability check: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            return {}
    
    def suggest_meeting_times(self, duration_minutes: int = 60, 
                            days_ahead: int = 14,
                            attendees: List[str] = None) -> List[datetime]:
        """
        Suggest available meeting times.
        
        Args:
            duration_minutes: Meeting duration in minutes
            days_ahead: How many days ahead to search
            attendees: List of attendee emails
            
        Returns:
            List of suggested start times
        """
        try:
            suggestions = []
            attendees = attendees or []
            
            # Working hours (9 AM to 5 PM)
            start_hour, end_hour = 9, 17
            
            # Check each day
            base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            for day_offset in range(1, days_ahead + 1):
                current_date = base_date + timedelta(days=day_offset)
                
                # Skip weekends
                if current_date.weekday() >= 5:
                    continue
                
                # Check each hour slot
                for hour in range(start_hour, end_hour):
                    start_time = current_date.replace(hour=hour)
                    end_time = start_time + timedelta(minutes=duration_minutes)
                    
                    # Don't suggest times that go past working hours
                    if end_time.hour >= end_hour:
                        continue
                    
                    # Check availability
                    availability = self.check_availability(start_time, end_time, attendees)
                    
                    # If everyone is available, add to suggestions
                    if all(availability.values()):
                        suggestions.append(start_time)
                        
                        # Limit suggestions
                        if len(suggestions) >= 5:
                            break
                
                if len(suggestions) >= 5:
                    break
            
            logger.info(f"Generated {len(suggestions)} meeting time suggestions")
            return suggestions
            
        except Exception as e:
            logger.error(f"Error suggesting meeting times: {e}")
            return []
    
    def create_event(self, title: str, start_time: datetime, end_time: datetime,
                    description: str = "", location: str = "", 
                    attendees: List[str] = None, 
                    send_updates: str = "all") -> Optional[str]:
        """
        Create a calendar event.
        
        Args:
            title: Event title
            start_time: Event start time
            end_time: Event end time
            description: Event description
            location: Event location
            attendees: List of attendee emails
            send_updates: Whether to send calendar invites ('all', 'externalOnly', 'none')
            
        Returns:
            Event ID if successful, None otherwise
        """
        try:
            service = self.get_calendar_service()
            
            # Prepare event data
            event_body = {
                'summary': title,
                'description': description,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'America/New_York',  # Default timezone
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'America/New_York',
                },
                'location': location,
                'attendees': [{'email': email} for email in (attendees or [])],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                        {'method': 'popup', 'minutes': 10},       # 10 minutes before
                    ],
                },
            }
            
            # Create the event
            event = service.events().insert(
                calendarId='primary',
                body=event_body,
                sendUpdates=send_updates
            ).execute()
            
            event_id = event.get('id')
            logger.info(f"Created calendar event: {event_id}")
            return event_id
            
        except HttpError as e:
            logger.error(f"Calendar API error creating event: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating calendar event: {e}")
            return None
    
    def respond_to_meeting_request(self, event_id: str, response: str) -> bool:
        """
        Respond to a meeting invitation.
        
        Args:
            event_id: Calendar event ID
            response: 'accepted', 'declined', or 'tentative'
            
        Returns:
            True if successful, False otherwise
        """
        try:
            service = self.get_calendar_service()
            
            # Get the event first
            event = service.events().get(calendarId='primary', eventId=event_id).execute()
            
            # Update attendee response
            attendees = event.get('attendees', [])
            user_email = self.auth_service.get_user_info().get('email')
            
            for attendee in attendees:
                if attendee.get('email') == user_email:
                    attendee['responseStatus'] = response
                    break
            
            # Update the event
            updated_event = service.events().update(
                calendarId='primary',
                eventId=event_id,
                body=event,
                sendUpdates='all'
            ).execute()
            
            logger.info(f"Responded to meeting {event_id} with: {response}")
            return True
            
        except HttpError as e:
            logger.error(f"Calendar API error responding to meeting: {e}")
            return False
        except Exception as e:
            logger.error(f"Error responding to meeting request: {e}")
            return False
    
    def extract_meeting_from_email(self, email_data: Dict) -> Optional[MeetingRequest]:
        """
        Extract meeting request details from an email using AI.
        
        Args:
            email_data: Email data dictionary
            
        Returns:
            MeetingRequest object if meeting details found, None otherwise
        """
        try:
            # Use AI to extract meeting details
            ai_service = GeminiEmailAI()
            meeting_details = ai_service.extract_meeting_details(email_data)
            
            if meeting_details.get('error') or not meeting_details.get('is_meeting_request'):
                return None
            
            # Parse the extracted details
            meeting_request = MeetingRequest(
                title=meeting_details.get('title', 'Meeting'),
                proposed_times=[],  # Would need more sophisticated parsing for multiple times
                duration_minutes=meeting_details.get('duration', 60),
                attendees=meeting_details.get('participants', []),
                description=email_data.get('body', ''),
                location=meeting_details.get('location', ''),
                organizer_email=email_data.get('sender', ''),
                requires_response=meeting_details.get('requires_response', True)
            )
            
            # Try to parse date/time
            if meeting_details.get('date') and meeting_details.get('time'):
                try:
                    date_str = meeting_details['date']
                    time_str = meeting_details['time']
                    # Simple parsing - could be enhanced
                    meeting_time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                    meeting_request.proposed_times = [meeting_time]
                except ValueError:
                    logger.warning("Failed to parse meeting date/time")
            
            logger.info("Extracted meeting request from email")
            return meeting_request
            
        except Exception as e:
            logger.error(f"Error extracting meeting from email: {e}")
            return None
    
    def get_calendar_conflicts(self, start_time: datetime, end_time: datetime) -> List[CalendarEvent]:
        """
        Get calendar events that conflict with the specified time range.
        
        Args:
            start_time: Start of time range to check
            end_time: End of time range to check
            
        Returns:
            List of conflicting CalendarEvent objects
        """
        try:
            service = self.get_calendar_service()
            
            # Fetch events in the time range
            events_result = service.events().list(
                calendarId='primary',
                timeMin=start_time.isoformat(),
                timeMax=end_time.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            conflicts = []
            
            for event in events:
                try:
                    calendar_event = self._parse_calendar_event(event)
                    conflicts.append(calendar_event)
                except Exception as e:
                    logger.warning(f"Failed to parse conflicting event: {e}")
                    continue
            
            logger.info(f"Found {len(conflicts)} calendar conflicts")
            return conflicts
            
        except Exception as e:
            logger.error(f"Error checking calendar conflicts: {e}")
            return []
    
    def _parse_calendar_event(self, event_data: Dict) -> CalendarEvent:
        """Parse Google Calendar event data into CalendarEvent object."""
        # Parse start/end times
        start = event_data.get('start', {})
        end = event_data.get('end', {})
        
        if 'dateTime' in start:
            start_time = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
        else:
            # All-day event
            start_time = datetime.fromisoformat(start['date'])
        
        if 'dateTime' in end:
            end_time = datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))
        else:
            # All-day event
            end_time = datetime.fromisoformat(end['date'])
        
        # Parse attendees
        attendees = []
        for attendee in event_data.get('attendees', []):
            attendees.append(attendee.get('email', ''))
        
        # Get meeting link
        meeting_link = ""
        if 'conferenceData' in event_data:
            entry_points = event_data['conferenceData'].get('entryPoints', [])
            for entry in entry_points:
                if entry.get('entryPointType') == 'video':
                    meeting_link = entry.get('uri', '')
                    break
        
        return CalendarEvent(
            id=event_data.get('id', ''),
            title=event_data.get('summary', 'No title'),
            start_time=start_time,
            end_time=end_time,
            description=event_data.get('description', ''),
            location=event_data.get('location', ''),
            attendees=attendees,
            organizer=event_data.get('organizer', {}).get('email', ''),
            status=event_data.get('status', 'confirmed'),
            meeting_link=meeting_link
        )


# Global calendar service instance
_calendar_service = None

def get_calendar_service() -> CalendarService:
    """Get the global calendar service instance."""
    global _calendar_service
    if _calendar_service is None:
        _calendar_service = CalendarService()
    return _calendar_service
