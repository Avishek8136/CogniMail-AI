"""
Smart Scheduling System: AI-powered calendar conflict resolution and optimization.
Handles intelligent scheduling, conflict detection, and optimal time slot suggestions.
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import itertools
from loguru import logger

from .calendar_service import CalendarService, CalendarEvent, MeetingRequest
from ..ai.gemini_service import GeminiEmailAI


@dataclass
class TimeSlot:
    """Represents an available time slot with additional metadata."""
    start_time: datetime
    end_time: datetime
    score: float = 0.0  # Higher score = better slot
    attendee_conflicts: Dict[str, List[CalendarEvent]] = None
    notes: List[str] = None  # Reasons for the score


class SmartScheduler:
    """Handles intelligent meeting scheduling and calendar optimization."""
    
    def __init__(self):
        """Initialize the Smart Scheduler."""
        self.calendar_service = CalendarService()
        self.ai_service = GeminiEmailAI()
        
        # Scheduling preferences (could be customized per user)
        self.preferences = {
            'min_buffer_minutes': 15,  # Minimum buffer between meetings
            'max_meetings_per_day': 8,  # Maximum meetings per day
            'preferred_meeting_times': [  # Preferred time slots
                (9, 12),  # Morning
                (14, 16),  # Afternoon
            ],
            'lunch_time': (12, 13),  # Typical lunch hour
            'working_hours': (9, 17),  # Standard working hours
        }
    
    def resolve_conflicts(self, meeting: MeetingRequest) -> List[TimeSlot]:
        """
        Find optimal meeting times that minimize conflicts for all attendees.
        
        Args:
            meeting: The meeting request to schedule
            
        Returns:
            List of TimeSlot objects, sorted by score (best first)
        """
        try:
            # Validate meeting request
            if not meeting:
                logger.error("No meeting request provided")
                return []
                
            # Use default duration if none specified
            duration = meeting.duration_minutes or 60  # Default to 1 hour
            if duration <= 0:
                logger.error(f"Invalid meeting duration: {duration} minutes")
                return []
                
            # Validate attendees
            attendees = meeting.attendees or []
            if not attendees:
                logger.warning("No attendees specified in meeting request")
            
            # Start with all possible time slots in the next 2 weeks
            potential_slots = self._generate_time_slots(
                days_ahead=14,
                duration_minutes=duration
            )
            
            if not potential_slots:
                logger.warning("No potential time slots found")
                return []
            
            # Score and filter the slots
            scored_slots = []
            for slot in potential_slots:
                try:
                    score, conflicts, notes = self._evaluate_time_slot(
                        slot.start_time, 
                        slot.end_time,
                        attendees
                    )
                    
                    if score > 0:  # Slot is viable
                        slot.score = score
                        slot.attendee_conflicts = conflicts
                        slot.notes = notes
                        scored_slots.append(slot)
                except Exception as e:
                    logger.warning(f"Error evaluating time slot: {e}")
                    continue
            
            # Sort by score (highest first)
            scored_slots.sort(key=lambda x: x.score, reverse=True)
            
            # Log results
            if scored_slots:
                logger.info(f"Found {len(scored_slots)} viable time slots")
            else:
                logger.warning("No viable time slots found after conflict resolution")
            
            # Return top 5 slots
            return scored_slots[:5]
            
        except Exception as e:
            logger.error(f"Error resolving conflicts: {e}")
            return []
    
    def optimize_calendar(self, start_date: datetime, days: int = 7) -> List[Dict]:
        """
        Analyze and optimize the calendar for the specified time range.
        
        Args:
            start_date: Start date for optimization
            days: Number of days to analyze
            
        Returns:
            List of optimization suggestions
        """
        try:
            suggestions = []
            end_date = start_date + timedelta(days=days)
            
            # Get all events in the range
            events = self.calendar_service.get_upcoming_events(
                days_ahead=days,
                max_results=100
            )
            
            if not events:
                return suggestions
            
            # Group events by day
            events_by_day = {}
            for event in events:
                day = event.start_time.date()
                if day not in events_by_day:
                    events_by_day[day] = []
                events_by_day[day].append(event)
            
            # Analyze each day
            for day, day_events in events_by_day.items():
                # Check for overbooked days
                if len(day_events) > self.preferences['max_meetings_per_day']:
                    suggestions.append({
                        'type': 'overbooked_day',
                        'date': day,
                        'severity': 'high',
                        'message': f"Day is overbooked with {len(day_events)} meetings"
                    })
                
                # Check for insufficient breaks
                for i in range(len(day_events) - 1):
                    current = day_events[i]
                    next_event = day_events[i + 1]
                    break_duration = (next_event.start_time - current.end_time).total_seconds() / 60
                    
                    if break_duration < self.preferences['min_buffer_minutes']:
                        suggestions.append({
                            'type': 'insufficient_break',
                            'date': day,
                            'events': [current.id, next_event.id],
                            'severity': 'medium',
                            'message': f"Only {break_duration:.0f} minutes between meetings"
                        })
                
                # Check for lunch time conflicts
                lunch_start, lunch_end = self.preferences['lunch_time']
                lunch_conflicts = [
                    event for event in day_events
                    if (event.start_time.hour < lunch_end and 
                        event.end_time.hour > lunch_start)
                ]
                
                if lunch_conflicts:
                    suggestions.append({
                        'type': 'lunch_conflict',
                        'date': day,
                        'events': [e.id for e in lunch_conflicts],
                        'severity': 'low',
                        'message': "Meetings scheduled during typical lunch hour"
                    })
            
            # Sort suggestions by severity
            severity_order = {'high': 0, 'medium': 1, 'low': 2}
            suggestions.sort(key=lambda x: severity_order[x['severity']])
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error optimizing calendar: {e}")
            return []
    
    def _generate_time_slots(self, days_ahead: int, 
                           duration_minutes: int) -> List[TimeSlot]:
        """Generate potential time slots for scheduling."""
        slots = []
        base_date = datetime.now().replace(
            hour=self.preferences['working_hours'][0],
            minute=0, second=0, microsecond=0
        )
        
        for day in range(1, days_ahead + 1):
            current_date = base_date + timedelta(days=day)
            
            # Skip weekends
            if current_date.weekday() >= 5:
                continue
            
            # Generate slots during working hours
            start_hour, end_hour = self.preferences['working_hours']
            for hour in range(start_hour, end_hour):
                for minute in [0, 30]:  # 30-minute increments
                    start_time = current_date.replace(hour=hour, minute=minute)
                    end_time = start_time + timedelta(minutes=duration_minutes)
                    
                    # Don't go past working hours
                    if end_time.hour >= end_hour:
                        continue
                    
                    slots.append(TimeSlot(
                        start_time=start_time,
                        end_time=end_time,
                        attendee_conflicts={},
                        notes=[]
                    ))
        
        return slots
    
    def _evaluate_time_slot(self, start_time: datetime, end_time: datetime,
                          attendees: List[str]) -> Tuple[float, Dict, List[str]]:
        """
        Evaluate a time slot for scheduling quality.
        
        Returns:
            Tuple of (score, conflicts dict, notes list)
        """
        score = 1.0
        notes = []
        conflicts = {}
        
        # Validate inputs
        if not start_time or not end_time:
            logger.error("Missing start or end time for evaluation")
            return 0.0, conflicts, ["Invalid time slot"]
            
        if start_time >= end_time:
            logger.error("Start time must be before end time")
            return 0.0, conflicts, ["Invalid time range"]
        
        # Convert times to timezone-aware if needed
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=datetime.now().astimezone().tzinfo)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=datetime.now().astimezone().tzinfo)
        
        # Check availability for all attendees
        if attendees:
            availability = self.calendar_service.check_availability(
                start_time, end_time, attendees
            )
            
            # Check if any attendee is not available
            for attendee, is_available in availability.items():
                if not is_available:
                    attendee_conflicts = self.calendar_service.get_calendar_conflicts(
                        start_time, end_time
                    )
                    if attendee_conflicts:
                        conflicts[attendee] = attendee_conflicts
                        score = 0  # Immediate disqualification
                        notes.append(f"Conflicts for {attendee}")
        
        if score == 0:
            return score, conflicts, notes
        
        # Preferred time bonus
        for start, end in self.preferences['preferred_meeting_times']:
            if start <= start_time.hour < end:
                score += 0.2
                notes.append("Within preferred hours")
                break
        
        # Buffer time bonus
        day_events = self.calendar_service.get_calendar_conflicts(
            start_time - timedelta(hours=2),
            end_time + timedelta(hours=2)
        )
        
        min_buffer = float('inf')
        for event in day_events:
            if event.end_time <= start_time:
                buffer = (start_time - event.end_time).total_seconds() / 60
                min_buffer = min(min_buffer, buffer)
            elif event.start_time >= end_time:
                buffer = (event.start_time - end_time).total_seconds() / 60
                min_buffer = min(min_buffer, buffer)
        
        if min_buffer < float('inf'):
            if min_buffer >= self.preferences['min_buffer_minutes']:
                score += 0.1
                notes.append(f"Good buffer time: {min_buffer:.0f} minutes")
            else:
                score -= 0.1
                notes.append(f"Limited buffer time: {min_buffer:.0f} minutes")
        
        # Lunch time penalty
        lunch_start, lunch_end = self.preferences['lunch_time']
        if (start_time.hour < lunch_end and end_time.hour > lunch_start):
            score -= 0.2
            notes.append("Conflicts with typical lunch hour")
        
        return score, conflicts, notes


# Global smart scheduler instance
_smart_scheduler = None

def get_smart_scheduler() -> SmartScheduler:
    """Get the global smart scheduler instance."""
    global _smart_scheduler
    if _smart_scheduler is None:
        _smart_scheduler = SmartScheduler()
    return _smart_scheduler
