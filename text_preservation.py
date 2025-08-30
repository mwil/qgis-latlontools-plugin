"""
Text Preservation Module
Handles preserving input text when coordinate order is changed (X,Y button)
"""

class TextPreservationMixin:
    """
    Mixin class to add text preservation functionality to coordinate input dialogs
    """
    
    def preserve_text_during_order_change(self, coord_text_widget, settings_obj, configure_method):
        """
        Preserve current input text when changing coordinate order
        
        Args:
            coord_text_widget: The QLineEdit containing coordinate text
            settings_obj: Settings object with coordinate order methods
            configure_method: Method to call to update UI after order change
        """
        # Preserve current input
        current_text = coord_text_widget.text()
        
        # Change coordinate order
        if settings_obj.zoomToCoordOrder == 0:
            settings_obj.setZoomToCoordOrder(1)
        else:
            settings_obj.setZoomToCoordOrder(0)
        
        # Update UI but preserve input
        configure_method()
        
        # Restore the input text
        coord_text_widget.setText(current_text)