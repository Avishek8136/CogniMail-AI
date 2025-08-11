"""
RHLF (Reinforcement Learning from Human Feedback) service for personalization.
Learns from user feedback to improve AI decision-making and adapt to user preferences.
"""

import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger

from ..database.advanced_db import AdvancedDatabase, PersonalizationProfile, UserFeedback
from ..database.learning_db import get_learning_db, UserCorrection
from .gemini_service import GeminiEmailAI


class RHLFService:
    """Reinforcement Learning from Human Feedback service."""
    
    def __init__(self, advanced_db: Optional[AdvancedDatabase] = None,
                 ai_service: Optional[GeminiEmailAI] = None):
        """Initialize the RHLF service."""
        self.advanced_db = advanced_db or AdvancedDatabase()
        self.learning_db = get_learning_db()
        self.ai_service = ai_service or GeminiEmailAI()
        
    def create_or_update_user_profile(self, user_email: str, 
                                    feedback_data: Dict = None) -> PersonalizationProfile:
        """
        Create or update a user's personalization profile.
        
        Args:
            user_email: User's email address
            feedback_data: Optional feedback data to incorporate
            
        Returns:
            PersonalizationProfile object
        """
        try:
            # Get existing profile or create new one
            existing_profile = self.advanced_db.get_personalization_profile(user_email)
            
            if existing_profile:
                profile = existing_profile
                profile.interaction_count += 1
            else:
                profile = PersonalizationProfile(
                    user_email=user_email,
                    communication_style="professional",
                    preferred_tone="balanced", 
                    response_length="medium",
                    urgency_sensitivity=0.5,
                    category_preferences="{}",
                    learned_patterns="{}",
                    ai_confidence_threshold=0.7,
                    feedback_score=0.0,
                    interaction_count=1,
                    last_updated=datetime.now()
                )
            
            # Update profile with feedback data if provided
            if feedback_data:
                self._update_profile_from_feedback(profile, feedback_data)
            
            # Learn from historical corrections
            self._learn_from_corrections(profile)
            
            # Update last modified time
            profile.last_updated = datetime.now()
            
            # Save profile
            self.advanced_db.save_personalization_profile(profile)
            
            return profile
            
        except Exception as e:
            logger.error(f"Error creating/updating user profile: {e}")
            # Return default profile
            return PersonalizationProfile(user_email=user_email)
    
    def _update_profile_from_feedback(self, profile: PersonalizationProfile, 
                                    feedback_data: Dict) -> None:
        """Update profile based on feedback data."""
        try:
            # Update communication preferences based on feedback
            if 'communication_style' in feedback_data:
                profile.communication_style = feedback_data['communication_style']
            
            if 'preferred_tone' in feedback_data:
                profile.preferred_tone = feedback_data['preferred_tone']
            
            if 'response_length' in feedback_data:
                profile.response_length = feedback_data['response_length']
            
            # Adjust urgency sensitivity based on urgency-related feedback
            if 'urgency_feedback' in feedback_data:
                urgency_feedback = feedback_data['urgency_feedback']
                if urgency_feedback == 'too_sensitive':
                    profile.urgency_sensitivity = max(0.1, profile.urgency_sensitivity - 0.1)
                elif urgency_feedback == 'not_sensitive_enough':
                    profile.urgency_sensitivity = min(0.9, profile.urgency_sensitivity + 0.1)
            
            # Update learned patterns
            try:
                learned_patterns = json.loads(profile.learned_patterns) if profile.learned_patterns else {}
                
                # Add new patterns from feedback
                if 'patterns' in feedback_data:
                    for pattern_key, pattern_value in feedback_data['patterns'].items():
                        learned_patterns[pattern_key] = pattern_value
                
                profile.learned_patterns = json.dumps(learned_patterns)
            except json.JSONDecodeError:
                logger.warning("Could not parse learned patterns, resetting")
                profile.learned_patterns = "{}"
            
        except Exception as e:
            logger.error(f"Error updating profile from feedback: {e}")
    
    def _learn_from_corrections(self, profile: PersonalizationProfile) -> None:
        """Learn from user corrections to improve AI accuracy."""
        try:
            # Get recent corrections for this user (approximated by recent corrections)
            recent_corrections = self.learning_db.get_recent_corrections(days=30, limit=100)
            
            if not recent_corrections:
                return
            
            # Analyze correction patterns
            urgency_corrections = []
            category_corrections = []
            
            for correction in recent_corrections:
                if correction.original_urgency != correction.corrected_urgency:
                    urgency_corrections.append(correction)
                
                if correction.original_category != correction.corrected_category:
                    category_corrections.append(correction)
            
            # Update urgency sensitivity based on corrections
            if urgency_corrections:
                over_classified_urgent = sum(1 for c in urgency_corrections 
                                           if c.original_urgency == 'urgent' and c.corrected_urgency != 'urgent')
                under_classified_urgent = sum(1 for c in urgency_corrections 
                                            if c.original_urgency != 'urgent' and c.corrected_urgency == 'urgent')
                
                total_urgency_corrections = len(urgency_corrections)
                
                if over_classified_urgent > under_classified_urgent:
                    # AI is too aggressive with urgency classification
                    adjustment = -0.05 * (over_classified_urgent / total_urgency_corrections)
                    profile.urgency_sensitivity = max(0.1, profile.urgency_sensitivity + adjustment)
                elif under_classified_urgent > over_classified_urgent:
                    # AI is not aggressive enough
                    adjustment = 0.05 * (under_classified_urgent / total_urgency_corrections)
                    profile.urgency_sensitivity = min(0.9, profile.urgency_sensitivity + adjustment)
            
            # Update category preferences based on corrections
            if category_corrections:
                try:
                    category_prefs = json.loads(profile.category_preferences) if profile.category_preferences else {}
                    
                    for correction in category_corrections:
                        # Track which categories are frequently corrected
                        original_cat = correction.original_category
                        corrected_cat = correction.corrected_category
                        
                        # Decrease confidence in original category
                        if original_cat in category_prefs:
                            category_prefs[original_cat] = max(0.1, category_prefs[original_cat] - 0.05)
                        else:
                            category_prefs[original_cat] = 0.8  # Start with lower confidence
                        
                        # Increase confidence in corrected category
                        if corrected_cat in category_prefs:
                            category_prefs[corrected_cat] = min(1.0, category_prefs[corrected_cat] + 0.05)
                        else:
                            category_prefs[corrected_cat] = 0.9  # Start with higher confidence
                    
                    profile.category_preferences = json.dumps(category_prefs)
                    
                except json.JSONDecodeError:
                    logger.warning("Could not parse category preferences, resetting")
                    profile.category_preferences = "{}"
            
            # Adjust AI confidence threshold based on correction frequency
            total_corrections = len(recent_corrections)
            if total_corrections > 10:  # Only adjust if we have sufficient data
                correction_rate = total_corrections / profile.interaction_count if profile.interaction_count > 0 else 0
                
                if correction_rate > 0.3:  # High correction rate
                    # Increase confidence threshold to be more conservative
                    profile.ai_confidence_threshold = min(0.9, profile.ai_confidence_threshold + 0.05)
                elif correction_rate < 0.1:  # Low correction rate
                    # Decrease confidence threshold to be more aggressive
                    profile.ai_confidence_threshold = max(0.5, profile.ai_confidence_threshold - 0.05)
            
        except Exception as e:
            logger.error(f"Error learning from corrections: {e}")
    
    def get_personalized_recommendations(self, user_email: str, 
                                       email_context: Dict) -> Dict:
        """
        Get personalized recommendations based on user profile and email context.
        
        Args:
            user_email: User's email address
            email_context: Email context data
            
        Returns:
            Dictionary with personalized recommendations
        """
        try:
            profile = self.advanced_db.get_personalization_profile(user_email)
            if not profile:
                # Return default recommendations
                return self._get_default_recommendations()
            
            recommendations = {
                "urgency_threshold": profile.urgency_sensitivity,
                "confidence_threshold": profile.ai_confidence_threshold,
                "preferred_tone": profile.preferred_tone,
                "response_length": profile.response_length,
                "communication_style": profile.communication_style
            }
            
            # Add category-specific recommendations
            try:
                category_prefs = json.loads(profile.category_preferences) if profile.category_preferences else {}
                recommendations["category_preferences"] = category_prefs
            except json.JSONDecodeError:
                recommendations["category_preferences"] = {}
            
            # Add learned patterns
            try:
                learned_patterns = json.loads(profile.learned_patterns) if profile.learned_patterns else {}
                recommendations["learned_patterns"] = learned_patterns
            except json.JSONDecodeError:
                recommendations["learned_patterns"] = {}
            
            # Context-specific adjustments
            if email_context.get("sender") in learned_patterns.get("trusted_senders", []):
                recommendations["urgency_threshold"] *= 0.9  # More sensitive for trusted senders
            
            if email_context.get("subject", "").lower() in learned_patterns.get("important_keywords", []):
                recommendations["urgency_threshold"] *= 0.8  # More sensitive for important keywords
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting personalized recommendations: {e}")
            return self._get_default_recommendations()
    
    def _get_default_recommendations(self) -> Dict:
        """Get default recommendations for new users."""
        return {
            "urgency_threshold": 0.5,
            "confidence_threshold": 0.7,
            "preferred_tone": "balanced",
            "response_length": "medium",
            "communication_style": "professional",
            "category_preferences": {},
            "learned_patterns": {}
        }
    
    def process_feedback(self, user_email: str, feedback: UserFeedback) -> bool:
        """
        Process user feedback for RHLF learning.
        
        Args:
            user_email: User's email address
            feedback: User feedback object
            
        Returns:
            True if processed successfully, False otherwise
        """
        try:
            # Store feedback
            feedback_id = self.advanced_db.store_user_feedback(feedback)
            
            if feedback_id <= 0:
                return False
            
            # Update user profile based on feedback
            success = self.advanced_db.learn_from_feedback(user_email, feedback)
            
            # Update global AI parameters if needed
            self._update_global_parameters(feedback)
            
            logger.info(f"Processed feedback {feedback_id} for user {user_email}")
            return success
            
        except Exception as e:
            logger.error(f"Error processing feedback: {e}")
            return False
    
    def _update_global_parameters(self, feedback: UserFeedback) -> None:
        """Update global AI parameters based on feedback patterns."""
        try:
            # This would implement global learning from all user feedback
            # For now, we'll just log the feedback for future analysis
            logger.info(f"Global parameter update triggered by feedback on {feedback.feature_type}")
            
            # In a full implementation, this would:
            # 1. Analyze feedback patterns across all users
            # 2. Update model confidence thresholds
            # 3. Adjust default categorization rules
            # 4. Update response generation templates
            
        except Exception as e:
            logger.error(f"Error updating global parameters: {e}")
    
    def get_learning_insights(self, user_email: str) -> Dict:
        """
        Get learning insights for a user's personalization.
        
        Args:
            user_email: User's email address
            
        Returns:
            Dictionary with learning insights
        """
        try:
            profile = self.advanced_db.get_personalization_profile(user_email)
            if not profile:
                return {"error": "No profile found"}
            
            # Get feedback analytics
            feedback_analytics = self.advanced_db.get_feedback_analytics()
            
            insights = {
                "profile_summary": {
                    "communication_style": profile.communication_style,
                    "preferred_tone": profile.preferred_tone,
                    "urgency_sensitivity": profile.urgency_sensitivity,
                    "ai_confidence_threshold": profile.ai_confidence_threshold,
                    "interaction_count": profile.interaction_count,
                    "average_feedback_score": profile.feedback_score
                },
                "learning_progress": {
                    "total_interactions": profile.interaction_count,
                    "last_updated": profile.last_updated.isoformat() if profile.last_updated else None,
                    "adaptation_level": self._calculate_adaptation_level(profile),
                },
                "feedback_insights": feedback_analytics,
                "recommendations": self._get_improvement_recommendations(profile, feedback_analytics)
            }
            
            return insights
            
        except Exception as e:
            logger.error(f"Error getting learning insights: {e}")
            return {"error": str(e)}
    
    def _calculate_adaptation_level(self, profile: PersonalizationProfile) -> str:
        """Calculate how well the AI has adapted to the user."""
        if profile.interaction_count < 10:
            return "Learning"
        elif profile.interaction_count < 50:
            return "Adapting"
        elif profile.feedback_score > 4.0:
            return "Well Adapted"
        elif profile.feedback_score > 3.0:
            return "Moderately Adapted"
        else:
            return "Needs Improvement"
    
    def _get_improvement_recommendations(self, profile: PersonalizationProfile, 
                                       feedback_analytics: Dict) -> List[str]:
        """Get recommendations for improving AI performance for this user."""
        recommendations = []
        
        if profile.feedback_score < 3.0:
            recommendations.append("Consider providing more detailed feedback to help the AI learn your preferences")
        
        if profile.interaction_count < 20:
            recommendations.append("Continue using the system to allow for better personalization")
        
        avg_rating = feedback_analytics.get("average_rating", 3.0)
        if profile.feedback_score < avg_rating:
            recommendations.append("Your AI assistant is learning. More usage will improve accuracy")
        
        if profile.urgency_sensitivity > 0.8:
            recommendations.append("Your urgency sensitivity is high. Consider adjusting if you receive too many urgent notifications")
        elif profile.urgency_sensitivity < 0.2:
            recommendations.append("Your urgency sensitivity is low. Consider adjusting if you miss important emails")
        
        return recommendations
    
    def export_personalization_data(self, user_email: str) -> Dict:
        """
        Export all personalization data for a user.
        
        Args:
            user_email: User's email address
            
        Returns:
            Dictionary with all user's personalization data
        """
        try:
            profile = self.advanced_db.get_personalization_profile(user_email)
            if not profile:
                return {}
            
            # Get user's feedback history
            # Note: This would require a method to get feedback by user
            # For now, we'll just export the profile
            
            export_data = {
                "profile": {
                    "user_email": profile.user_email,
                    "communication_style": profile.communication_style,
                    "preferred_tone": profile.preferred_tone,
                    "response_length": profile.response_length,
                    "urgency_sensitivity": profile.urgency_sensitivity,
                    "ai_confidence_threshold": profile.ai_confidence_threshold,
                    "feedback_score": profile.feedback_score,
                    "interaction_count": profile.interaction_count,
                    "last_updated": profile.last_updated.isoformat() if profile.last_updated else None,
                    "category_preferences": profile.category_preferences,
                    "learned_patterns": profile.learned_patterns
                },
                "export_date": datetime.now().isoformat(),
                "data_version": "1.0"
            }
            
            return export_data
            
        except Exception as e:
            logger.error(f"Error exporting personalization data: {e}")
            return {"error": str(e)}
