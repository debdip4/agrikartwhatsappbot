# In-memory store for user session data.
# Note: This will reset if the server restarts. For production, use Redis or a database.
user_states = {}

class StateManager:
    @staticmethod
    def get_user_state(phone_number):
        """Retrieves the state for a given user."""
        return user_states.get(phone_number, {})

    @staticmethod
    def set_user_state(phone_number, state_data):
        """Updates the state for a given user."""
        user_states[phone_number] = state_data

    @staticmethod
    def reset_user_state(phone_number):
        """Resets a user's state, keeping language and token."""
        current_state = user_states.get(phone_number, {})
        user_states[phone_number] = {
            'language': current_state.get('language'),
            'token': current_state.get('token')
        }
