import sys
from src.utils.logger import logging

def error_details(error, error_detail:sys):
    """
    Extracts the error details from the exception.
    
    Args:
        error (Exception): The exception object.
        error_detail (sys): The sys module for accessing traceback information.
        
    Returns:
        str: A string containing the error details.
    """
    _, _, exc_tb = error_detail.exc_info()

    if exc_tb is not None:
        file_name = exc_tb.tb_frame.f_code.co_filename
        line_number = exc_tb.tb_lineno
        error_message = f"Error detected in script: [{file_name}] at line number: [{line_number}] with message: [{str(error)}]"
    else:
        error_message = f"Error detected with message: [{str(error)}]"
        
    return error_message

class CustomException(Exception):
    """
    Custom exception class that captures error details.
    
    Args:
        error (Exception): The exception object.
        error_detail (sys): The sys module for accessing traceback information.
    """
    
    def __init__(self, error, error_detail:sys):
        super().__init__(error)
        self.error_message = error_details(error, error_detail=error_detail)

    def __str__(self):
        return self.error_message
        