# AI Email Manager

An intelligent email management system that uses Google's Gemma-3 AI model to automatically triage, categorize, and process your Gmail inbox. This project implements a phased approach to building a sophisticated, user-trusted email automation system.

## 🌟 Features

### Core AI Intelligence
- **Smart Email Triage**: Automatically classify emails by urgency (Urgent, To Respond, FYI, Meeting, Spam)
- **Intelligent Categorization**: Sort emails into meaningful categories (Work, Personal, Marketing, Security, etc.)
- **Confidence Scoring**: Each AI decision includes a confidence score and clear reasoning
- **Learning System**: Improves accuracy over time based on user corrections
- **RHLF Personalization**: Reinforcement Learning from Human Feedback adapts to your unique preferences and communication patterns

### Advanced Task Management
- **Follow-up Tracking**: Automatically identifies emails requiring follow-up action and tracks pending responses
- **Overdue Detection**: Highlights overdue tasks and missed deadlines with smart notifications
- **Smart Reminders**: AI-powered reminder system for important emails and upcoming deadlines
- **Context-Aware Scheduling**: Integrates with calendar to suggest optimal timing for follow-ups

### User Interface
- **Modern GUI**: Built with CustomTkinter for a clean, professional interface
- **Priority Inbox**: Emails automatically sorted by importance and urgency
- **AI Analysis Dashboard**: View detailed AI reasoning and confidence scores
- **One-Click Corrections**: Easy feedback system to train the AI
- **Thread Summaries**: AI-generated summaries of email conversations
- **Task Management Panel**: Dedicated views for follow-ups, overdue items, and reminders
- **Feedback Collection System**: Built-in report button for collecting user feedback and improving AI performance
- **Personalization Dashboard**: View and adjust RHLF learning preferences and AI behavior patterns

### Security & Privacy
- **OAuth2 Authentication**: Secure Google Workspace integration
- **Local Data Storage**: All learning data stored locally in SQLite database
- **Minimal Permissions**: Only requests necessary Gmail and Calendar permissions
- **Transparent AI**: All AI decisions explained with clear reasoning

## 🚀 Quick Start

### Prerequisites
- Python 3.10 or higher
- Google Cloud Project with Gmail and Calendar APIs enabled
- Gemini API key from Google AI Studio (for Gemma-3 model access)

### Installation

1. **Clone and Setup Environment**
   ```bash
   git clone <your-repo-url>
   cd "Email & Calendar Management RPD"
   python -m venv ai_email_manager_env
   ai_email_manager_env\Scripts\Activate.ps1  # Windows PowerShell
   # or
   source ai_email_manager_env/bin/activate  # Linux/Mac
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure API Keys**
   ```bash
   copy .env.template .env
   # Edit .env with your API keys (see Configuration section below)
   ```

4. **Run the Application**
   ```bash
   python main.py
   ```

## ⚙️ Configuration

### 1. Get Google API Credentials
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Gmail API and Google Calendar API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download the JSON file (not needed directly, but used for reference)

### 2. Get Gemini API Key
1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create a new API key (ensure Gemma-3 model access)
3. Copy the key for use in configuration

### 3. Update .env File
```bash
# AI Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Google Workspace Configuration
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
GOOGLE_REDIRECT_URI=http://localhost:8080/callback

# Application Settings
APP_NAME=AI Email Manager
DEBUG=false
LOG_LEVEL=INFO

# AI Model Settings (Gemma-3)
AI_MODEL=gemma-3-27b-it
AI_CONFIDENCE_THRESHOLD=0.7
MAX_TOKENS=1000
TEMPERATURE=0.3
EMAIL_FETCH_COUNT=100
EMAIL_FETCH_DAYS=30

# GUI Settings
THEME=dark
WINDOW_WIDTH=1200
WINDOW_HEIGHT=800
```

## 🖥️ Usage Guide

### First Time Setup
1. Launch the application: `python main.py`
2. Click "Authenticate" and follow the Google OAuth flow
3. Grant permissions for Gmail and Calendar access
3. Click "Refresh Emails" to load and analyze your inbox (fetches up to 100 emails from the past 30 days)

### Daily Workflow
1. **Review Priority Inbox**: Emails are automatically sorted by urgency
2. **Check Follow-ups**: Review pending follow-ups and overdue items in the task management panel
3. **Manage Reminders**: View and respond to AI-generated smart reminders
4. **Check AI Analysis**: Click any email to see AI reasoning and recommendations
5. **Correct Mistakes**: Use the correction interface to improve AI accuracy
6. **Take Actions**: Mark as read, quick reply, or view thread summaries
7. **Provide Feedback**: Use the report button to submit feedback and help improve the AI
8. **Review Personalization**: Check RHLF learning progress and adjust preferences as needed

### Understanding AI Classifications

#### Urgency Levels
- **Urgent**: Requires immediate action (deadlines, VIPs, urgent keywords)
- **To Respond**: Needs a response but not urgent (questions, requests)
- **FYI**: Informational only, no action required
- **Meeting**: Meeting invitations and calendar requests
- **Spam**: Promotional content or suspicious emails

#### Categories
- **Work**: Business-related communications
- **Personal**: Personal correspondence
- **Marketing**: Newsletters and promotional content
- **Security**: Security alerts and notifications
- **Meeting Request**: Calendar invitations
- **Task Assignment**: Work assignments and tasks
- **Information**: General informational content
- **Urgent Decision**: Requires immediate decision-making
- **Follow-up Required**: Emails that need follow-up action
- **Overdue**: Past-due items requiring immediate attention

### Task Management Features

#### Follow-up System
- **Automatic Detection**: AI identifies emails that require follow-up based on content and context
- **Smart Scheduling**: Suggests optimal follow-up timing based on email urgency and your calendar
- **Progress Tracking**: Monitors follow-up status and completion rates
- **Customizable Rules**: Set personal preferences for follow-up criteria and timing

#### Overdue Management
- **Deadline Detection**: Automatically identifies deadlines from email content
- **Priority Escalation**: Escalates overdue items based on importance and sender
- **Visual Indicators**: Clear color-coding and alerts for overdue tasks
- **Recovery Suggestions**: AI-powered recommendations for handling overdue items

#### Smart Reminders
- **Context-Aware Timing**: Reminders scheduled based on your work patterns and availability
- **Adaptive Frequency**: Reminder frequency adjusts based on task importance and your response patterns
- **Cross-Platform Sync**: Reminders integrate with your calendar and notification system
- **Snooze Intelligence**: Smart snooze suggestions based on email content and your schedule

### RHLF Personalization System

#### Learning Capabilities
- **Behavioral Adaptation**: AI learns your communication patterns and preferences over time
- **Context Understanding**: Improves understanding of your specific work context and priorities
- **Feedback Integration**: Continuously improves based on your corrections and feedback
- **Personal Workflow Optimization**: Adapts to your unique email management style

#### Feedback Collection
- **Report Button**: Easy-to-access feedback collection for any AI decision or recommendation
- **Structured Feedback**: Multiple feedback types (accuracy, helpfulness, timing, etc.)
- **Anonymous Analytics**: Optional anonymous usage data to improve the system for all users
- **Preference Learning**: System learns from implicit feedback (actions taken, ignored suggestions, etc.)

## 🏗️ Project Architecture

```
src/
├── core/           # Core application logic
│   ├── config.py   # Configuration management
│   └── email_service.py  # Gmail API integration
├── ai/             # AI services
│   ├── gemini_service.py  # Gemini AI integration
│   └── rhlf_service.py    # RHLF personalization engine
├── auth/           # Authentication
│   └── google_auth.py     # OAuth2 flow
├── database/       # Data persistence
│   ├── learning_db.py     # Learning database
│   └── feedback_db.py     # Feedback and RHLF data
├── tasks/          # Task management
│   ├── followup_manager.py    # Follow-up tracking
│   ├── overdue_detector.py    # Overdue task detection
│   └── reminder_system.py     # Smart reminder system
├── gui/            # User interface
│   ├── main_app.py        # Main GUI application
│   ├── task_panel.py      # Task management interface
│   └── feedback_widget.py # Feedback collection UI
└── utils/          # Utility functions
```

### Key Components

- **GeminiEmailAI**: Handles all AI operations using Google's Gemma-3 model via Gemini API
- **RHLFService**: Manages reinforcement learning from human feedback and personalization
- **EmailService**: Manages Gmail API operations and email processing
- **GoogleAuthService**: Handles secure OAuth2 authentication
- **LearningDatabase**: Stores user feedback and learning data
- **FeedbackDatabase**: Manages RHLF data and user feedback collection
- **FollowupManager**: Tracks and manages email follow-ups
- **OverdueDetector**: Identifies and manages overdue tasks and deadlines
- **ReminderSystem**: AI-powered smart reminder system
- **EmailManagerApp**: Main GUI application with CustomTkinter
- **TaskPanel**: User interface for task management features
- **FeedbackWidget**: UI component for collecting user feedback

## 🎯 Roadmap

### Phase 1: ✅ Core Intelligence (Current)
- Email triage and classification
- User feedback and learning system
- Basic GUI with intelligent inbox

### Phase 2: ✅ Advanced Task Management (Current)
- Follow-up tracking and management system
- Overdue task detection and escalation
- Smart reminder system with context awareness
- RHLF-based personalization engine
- Comprehensive feedback collection system

### Phase 3: 🔄 Automation Sophistication (Next)
- AI-powered response generation
- Email-to-calendar conversion
- Advanced thread summarization
- Workflow automation based on learned patterns

### Phase 4: 🔮 Safety and Learning (Future)
- Preview-before-execution framework
- Advanced learning algorithms
- Granular user controls
- Rollback capabilities

### Phase 5: 🚀 Optimization and Scale (Future)
- Performance optimization
- Cross-platform integrations
- Productivity metrics
- Advanced workflow orchestration
- Enterprise-grade scalability

## 🧪 Testing

Run the built-in tests:
```bash
python -m pytest tests/
```

Test individual components:
```bash
# Test AI service with Gemma-3 model (requires API key)
python -c "from src.ai.gemini_service import GeminiEmailAI; ai = GeminiEmailAI(); print('Gemma-3 AI service working!')"

# Test authentication (requires credentials)
python -c "from src.auth.google_auth import get_auth_service; auth = get_auth_service(); print('Auth service ready!')"
```

## 🔄 Recent Improvements

The application has been enhanced with several critical fixes and improvements:

### Datetime Handling Improvements
- **Robust Datetime Processing**: Fixed timezone-aware vs timezone-naive datetime comparison errors
- **Enhanced Date Parsing**: Added fallback mechanisms for various date formats and string dates
- **UI Stability**: Eliminated crashes during email display caused by datetime comparison issues
- **Consistent Date Handling**: All dates are now normalized to timezone-naive format for consistent processing

### AI Analysis Enhancements
- **Error Recovery**: Improved parsing of AI batch analysis with robust error handling
- **Enum Validation**: Added validation and correction for EmailUrgency and EmailCategory values
- **Common Mistake Mapping**: Automatically corrects common AI classification mistakes (e.g., 'marketing' -> 'spam')
- **Fallback Analysis**: Provides default analysis when parsing fails, preventing application crashes
- **Batch Processing Optimization**: Enhanced batch size handling for improved processing efficiency

### Error Handling and Stability
- **Comprehensive Exception Handling**: Added try-catch blocks throughout the application
- **Graceful Degradation**: Application continues to function even when individual components fail
- **Detailed Logging**: Enhanced error logging with context information for better debugging
- **User-Friendly Error Messages**: Improved error reporting for better user experience

### Performance Improvements
- **Optimized Batch Processing**: Better handling of AI analysis batches to reduce processing time
- **Memory Management**: Improved memory usage during email fetching and processing
- **Database Operations**: Enhanced database query performance and error handling

These improvements significantly enhance the application's reliability, user experience, and overall stability.

## 🔧 Troubleshooting

### Common Issues

**"Authentication Failed"**
- Verify your Google Client ID and Secret are correct
- Check that Gmail and Calendar APIs are enabled
- Ensure redirect URI matches exactly

**"AI Analysis Failed"**
- Verify your Gemini API key is valid and has Gemma-3 model access
- Check your internet connection
- Ensure Gemma-3 model is available in your region
- Review the logs in `data/app.log`

**"No Emails Loaded"**
- Ensure you've completed OAuth authentication
- Check Gmail API permissions
- Verify your Gmail account has recent emails

### Debug Mode
Enable debug logging by setting `DEBUG=true` in your `.env` file. This will provide detailed logs in `data/app.log`.

## 📊 Learning and Analytics

The application tracks learning progress and provides insights:

- **User Corrections**: Number of AI classifications corrected
- **Model Accuracy**: Confidence scores and improvement over time
- **Sender Patterns**: Learned behaviors for frequent contacts
- **Usage Statistics**: Email processing and user interaction metrics
- **Task Completion Rates**: Follow-up completion and overdue task resolution metrics
- **Reminder Effectiveness**: Analysis of reminder timing and response rates
- **RHLF Progress**: Personalization learning progress and adaptation metrics
- **Feedback Analytics**: User satisfaction and system improvement insights

View statistics through the database:
```python
from src.database.learning_db import get_learning_db
from src.database.feedback_db import get_feedback_db

# Learning statistics
learning_db = get_learning_db()
learning_stats = learning_db.get_learning_statistics()
print("Learning Stats:", learning_stats)

# RHLF and feedback statistics
feedback_db = get_feedback_db()
rhlf_stats = feedback_db.get_rhlf_statistics()
feedback_summary = feedback_db.get_feedback_summary()
print("RHLF Stats:", rhlf_stats)
print("Feedback Summary:", feedback_summary)

# Task management statistics
from src.tasks.followup_manager import FollowupManager
from src.tasks.reminder_system import ReminderSystem

followup_mgr = FollowupManager()
reminder_sys = ReminderSystem()
task_stats = {
    'followups': followup_mgr.get_statistics(),
    'reminders': reminder_sys.get_statistics()
}
print("Task Management Stats:", task_stats)
```

## 🤝 Contributing

We welcome contributions! Please see our [contribution guidelines](CONTRIBUTING.md) for details.

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Set up development environment
4. Make your changes
5. Add tests
6. Submit a pull request

### Code Style
- Use Black for formatting: `black src/`
- Follow PEP 8 guidelines
- Add type hints where possible
- Include docstrings for functions and classes

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Google AI Team for the Gemini API and Gemma-3 model
- Google Cloud Team for Gmail and Calendar APIs
- CustomTkinter community for the modern GUI framework
- Open source contributors and testers

## 📞 Support

- **Documentation**: This README and inline code documentation
- **Issues**: Use GitHub Issues for bug reports and feature requests
- **Discussions**: Use GitHub Discussions for questions and ideas

---

**Built with ❤️ using Python, Google AI, and modern development practices.**
