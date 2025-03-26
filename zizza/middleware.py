from functools import wraps

def is_agent_set(func):
    """
    Decorator to check if the agent is set before executing a method.
    Raises a RuntimeError if the agent is not set.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        self = args[0]
        if self.agent is None:
            raise RuntimeError("Agent is not set")
        return func(*args, **kwargs)
    return wrapper

def normalize_chain_params(func):
    """
    Decorator that normalizes parameters containing 'chain' by converting them to lowercase.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        new_kwargs = {
            key: value.lower() if "chain" in key and isinstance(value, str) else value
            for key, value in kwargs.items()
        }
        return func(*args, **new_kwargs)
    
    return wrapper

def normalize_boolean_params(func):
    """
    Decorator that normalizes parameters by converting "true" to True and "false" to False.
    Only strings with value "true" or "false" (case-insensitive) are normalized.
    Other values are left unchanged.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        new_kwargs = {
            key: (True if value.lower() == "true" else False if value.lower() == "false" else value)
            if isinstance(value, str) and "on_" in key else value
            for key, value in kwargs.items()
        }
        return func(*args, **new_kwargs)
    
    return wrapper
def normalize_amount_params(func):
    """
    Decorator that ensures parameters containing 'amount' are converted to float.
    Prevents overflow by handling improper string inputs.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        new_kwargs = {}
        for key, value in kwargs.items():
            if "amount" in key and isinstance(value, str):
                try:
                    new_kwargs[key] = float(value)
                except ValueError:
                    raise ValueError(f"Invalid amount format for parameter '{key}': {value}")
            else:
                new_kwargs[key] = value
        return func(*args, **new_kwargs)
    
    return wrapper