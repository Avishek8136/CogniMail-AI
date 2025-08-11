from src.auth.google_auth import get_auth_service

def main():
    auth = get_auth_service()
    
    # First check current state
    print(f"Initial auth state: {auth.is_authenticated()}")
    
    # Force reauth
    print("Performing authentication...")
    auth.authenticate(force_reauth=True)
    
    # Check state again
    print(f"Auth state after authentication: {auth.is_authenticated()}")
    
    # Test calendar specifically
    print("Testing calendar connection...")
    calendar_result = auth.test_calendar_connection()
    print(f"Calendar test result: {calendar_result}")

if __name__ == "__main__":
    main()
