"""
Input validation and sanitization utilities for coordinate parsing.
Provides security and robustness improvements for user input handling.
"""
import re
from typing import Optional, Union


class CoordinateValidationError(Exception):
    """Raised when coordinate input validation fails."""
    pass


class InputValidator:
    """Centralized input validation and sanitization for coordinate inputs."""
    
    # Security limits
    MAX_INPUT_LENGTH = 1000  # Prevent memory exhaustion attacks
    MAX_COORDINATE_VALUE = 9999999.0  # Reasonable limit for coordinate values
    MIN_COORDINATE_VALUE = -9999999.0
    
    # Geographic bounds for validation
    MIN_LONGITUDE = -180.0
    MAX_LONGITUDE = 180.0
    MIN_LATITUDE = -90.0
    MAX_LATITUDE = 90.0
    
    # Allowed characters in coordinate input (whitelist approach)
    COORDINATE_PATTERN = re.compile(
        r'^[0-9\s\.\-\+\,°′″\'"NSEWnsew°\(\)\[\]HhMmSsZzTt\:]+$'
    )
    
    @staticmethod
    def sanitize_coordinate_input(text: str) -> str:
        """
        Sanitize user coordinate input for safe processing.
        
        Args:
            text: Raw user input string
            
        Returns:
            Sanitized string safe for coordinate parsing
            
        Raises:
            CoordinateValidationError: If input is invalid or potentially malicious
        """
        if not isinstance(text, str):
            raise CoordinateValidationError("Input must be a string")
            
        # Check for null or empty input
        if not text or text.isspace():
            raise CoordinateValidationError("Input cannot be empty")
            
        # Length validation (prevent memory exhaustion)
        if len(text) > InputValidator.MAX_INPUT_LENGTH:
            raise CoordinateValidationError(
                f"Input too long (max {InputValidator.MAX_INPUT_LENGTH} characters)"
            )
            
        # Remove null bytes and other control characters (security)
        sanitized = text.replace('\x00', '').replace('\r', '').replace('\n', ' ')
        
        # Normalize whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        # Character whitelist validation (security)
        if not InputValidator.COORDINATE_PATTERN.match(sanitized):
            raise CoordinateValidationError(
                "Input contains invalid characters for coordinate data"
            )
            
        return sanitized
    
    @staticmethod
    def validate_coordinate_bounds(lat: float, lon: float, strict: bool = True) -> bool:
        """
        Validate that coordinate values are within Earth bounds.
        
        Args:
            lat: Latitude value
            lon: Longitude value
            strict: If True, enforce strict geographic bounds (±180/±90)
                   If False, allow slightly larger ranges for projected coordinates
            
        Returns:
            True if coordinates are valid
            
        Raises:
            CoordinateValidationError: If coordinates are out of bounds
        """
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            raise CoordinateValidationError("Coordinates must be numeric values")
            
        if strict:
            min_lon, max_lon = InputValidator.MIN_LONGITUDE, InputValidator.MAX_LONGITUDE
            min_lat, max_lat = InputValidator.MIN_LATITUDE, InputValidator.MAX_LATITUDE
        else:
            # Allow larger ranges for projected coordinate systems
            min_lon, max_lon = InputValidator.MIN_COORDINATE_VALUE, InputValidator.MAX_COORDINATE_VALUE
            min_lat, max_lat = InputValidator.MIN_COORDINATE_VALUE, InputValidator.MAX_COORDINATE_VALUE
            
        if not (min_lat <= lat <= max_lat):
            raise CoordinateValidationError(
                f"Latitude {lat} outside valid range [{min_lat}, {max_lat}]"
            )
            
        if not (min_lon <= lon <= max_lon):
            raise CoordinateValidationError(
                f"Longitude {lon} outside valid range [{min_lon}, {max_lon}]"
            )
            
        return True
    
    @staticmethod
    def validate_numeric_range(value: float, min_val: float, max_val: float, name: str = "value") -> bool:
        """
        Validate that a numeric value is within specified range.
        
        Args:
            value: Value to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            name: Name of the value for error messages
            
        Returns:
            True if value is in range
            
        Raises:
            CoordinateValidationError: If value is out of range
        """
        if not isinstance(value, (int, float)):
            raise CoordinateValidationError(f"{name} must be a numeric value")
            
        if not (min_val <= value <= max_val):
            raise CoordinateValidationError(
                f"{name} {value} outside valid range [{min_val}, {max_val}]"
            )
            
        return True
    
    @staticmethod
    def extract_numeric_values(text: str) -> list:
        """
        Safely extract numeric values from coordinate text.
        
        Args:
            text: Sanitized coordinate text
            
        Returns:
            List of numeric values found in text
            
        Raises:
            CoordinateValidationError: If no numeric values found or values are invalid
        """
        # Pattern to match decimal numbers (including negative and scientific notation)
        number_pattern = re.compile(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?')
        
        matches = number_pattern.findall(text)
        if not matches:
            raise CoordinateValidationError("No numeric values found in input")
            
        numeric_values = []
        for match in matches:
            try:
                value = float(match)
                # Check for reasonable coordinate value ranges
                if abs(value) > InputValidator.MAX_COORDINATE_VALUE:
                    raise CoordinateValidationError(
                        f"Numeric value {value} exceeds maximum allowed range"
                    )
                numeric_values.append(value)
            except (ValueError, OverflowError) as e:
                raise CoordinateValidationError(f"Invalid numeric value '{match}': {e}")
                
        return numeric_values
    
    @staticmethod
    def detect_coordinate_format(text: str) -> Optional[str]:
        """
        Attempt to detect the coordinate format from sanitized input.
        
        Args:
            text: Sanitized coordinate text
            
        Returns:
            String indicating detected format, or None if format unclear
        """
        text_upper = text.upper()
        
        # Pattern matching for format detection
        if re.search(r'\d+[NS]\s+\d+', text_upper):
            return "UTM"
        elif re.search(r'\d+°.*[NS].*\d+°.*[EW]', text):
            return "DMS"
        elif re.search(r'POINT\s*\(', text_upper):
            return "WKT"
        elif re.search(r'\d+[A-Z]{2,3}\d+', text_upper):
            return "MGRS"
        elif re.search(r'[A-Z0-9]{8,}', text_upper):
            return "PLUS_CODES"
        elif len(text.replace(' ', '').replace(',', '')) > 20 and all(c in '0123456789ABCDEF' for c in text.replace(' ', '').replace(',', '')):
            return "WKB"
        elif re.search(r'[A-Z]{2}\d{2}[A-Z]{2}', text_upper):
            return "MAIDENHEAD"
        
        return None


# Convenience functions for backward compatibility and ease of use
def sanitize_coordinate_input(text: str) -> str:
    """Convenience function for input sanitization."""
    return InputValidator.sanitize_coordinate_input(text)


def validate_coordinate_bounds(lat: float, lon: float, strict: bool = True) -> bool:
    """Convenience function for coordinate bounds validation."""
    return InputValidator.validate_coordinate_bounds(lat, lon, strict)


def safe_coordinate_parse(text: str, parser_func, *args, **kwargs):
    """
    Safely parse coordinate text with input validation.
    
    Args:
        text: Raw coordinate text from user
        parser_func: Function to use for parsing (e.g., utm_parse)
        *args, **kwargs: Additional arguments for parser function
        
    Returns:
        Result from parser function
        
    Raises:
        CoordinateValidationError: If input validation fails
        Other exceptions: As raised by parser_func
    """
    # Sanitize input first
    sanitized_text = InputValidator.sanitize_coordinate_input(text)
    
    # Call the parser with sanitized input
    result = parser_func(sanitized_text, *args, **kwargs)
    
    # If parser returns coordinates, validate them
    if isinstance(result, (tuple, list)) and len(result) >= 2:
        if isinstance(result[0], (int, float)) and isinstance(result[1], (int, float)):
            # Assume first two values are lat, lon (or lon, lat)
            # Use non-strict validation since this could be projected coordinates
            try:
                InputValidator.validate_coordinate_bounds(result[0], result[1], strict=False)
            except CoordinateValidationError:
                # Try swapped coordinates (some formats are lon, lat)
                InputValidator.validate_coordinate_bounds(result[1], result[0], strict=False)
    
    return result