import math
from PySide6.QtGui import QColor

class AccessibilityUtils:
    """
    Utilities for improving accessibility in the application.
    Includes contrast ratio checking, text scaling, and other accessibility helpers.
    """
    
    @staticmethod
    def calculate_luminance(color):
        """
        Calculate the relative luminance of a color according to WCAG 2.0.
        
        Args:
            color: QColor object
            
        Returns:
            float: The relative luminance value between 0 and 1
        """
        r = color.redF()
        g = color.greenF()
        b = color.blueF()
        
        # Convert RGB to sRGB
        r = AccessibilityUtils._srgb_to_linear(r)
        g = AccessibilityUtils._srgb_to_linear(g)
        b = AccessibilityUtils._srgb_to_linear(b)
        
        # Calculate luminance
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    
    @staticmethod
    def _srgb_to_linear(value):
        """
        Convert sRGB value to linear RGB.
        
        Args:
            value: float between 0 and 1
            
        Returns:
            float: Linear RGB value
        """
        if value <= 0.03928:
            return value / 12.92
        else:
            return math.pow((value + 0.055) / 1.055, 2.4)
    
    @staticmethod
    def calculate_contrast_ratio(color1, color2):
        """
        Calculate the contrast ratio between two colors according to WCAG 2.0.
        
        Args:
            color1: QColor object (typically foreground)
            color2: QColor object (typically background)
            
        Returns:
            float: The contrast ratio (1:1 to 21:1)
        """
        luminance1 = AccessibilityUtils.calculate_luminance(color1)
        luminance2 = AccessibilityUtils.calculate_luminance(color2)
        
        # Ensure the lighter color is used as the first value
        if luminance1 <= luminance2:
            temp = luminance1
            luminance1 = luminance2
            luminance2 = temp
        
        # Calculate contrast ratio
        return (luminance1 + 0.05) / (luminance2 + 0.05)
    
    @staticmethod
    def is_contrast_sufficient(color1, color2, is_large_text=False):
        """
        Check if the contrast between two colors meets WCAG 2.0 AA standards.
        
        Args:
            color1: QColor object (typically foreground)
            color2: QColor object (typically background)
            is_large_text: Boolean indicating if text is large (14pt bold or 18pt normal)
            
        Returns:
            bool: True if contrast is sufficient, False otherwise
        """
        contrast_ratio = AccessibilityUtils.calculate_contrast_ratio(color1, color2)
        
        # WCAG 2.0 Level AA requires:
        # - 4.5:1 for normal text
        # - 3:1 for large text
        min_ratio = 3.0 if is_large_text else 4.5
        return contrast_ratio >= min_ratio
    
    @staticmethod
    def adjust_color_for_contrast(foreground, background, min_ratio=4.5):
        """
        Adjust foreground color to meet minimum contrast ratio with background.
        
        Args:
            foreground: QColor object to adjust
            background: QColor object to contrast against
            min_ratio: Minimum contrast ratio to achieve (default: 4.5 for WCAG AA)
            
        Returns:
            QColor: Adjusted foreground color that meets contrast requirements
        """
        current_ratio = AccessibilityUtils.calculate_contrast_ratio(foreground, background)
        
        # If already meets requirements, return as is
        if current_ratio >= min_ratio:
            return QColor(foreground)
        
        # Convert to HSL for more intuitive adjustments
        adjusted = QColor(foreground)
        h, s, l, a = adjusted.getHslF()
        
        # Background luminance
        bg_luminance = AccessibilityUtils.calculate_luminance(background)
        
        # Determine if we should lighten or darken based on background
        lighten = bg_luminance < 0.5
        
        # Adjust lightness until contrast is sufficient
        step = 0.05  # Incremental step
        max_iterations = 10  # Prevent infinite loops
        iterations = 0
        
        while (current_ratio < min_ratio and iterations < max_iterations):
            if lighten:
                l = min(1.0, l + step)
            else:
                l = max(0.0, l - step)
                
            adjusted.setHslF(h, s, l, a)
            current_ratio = AccessibilityUtils.calculate_contrast_ratio(adjusted, background)
            iterations += 1
            
        return adjusted
    
    @staticmethod
    def get_accessible_color_pair(base_fg, base_bg, min_ratio=4.5):
        """
        Get a pair of colors that meet the minimum contrast ratio.
        Will adjust the foreground color if needed.
        
        Args:
            base_fg: Base foreground QColor
            base_bg: Base background QColor
            min_ratio: Minimum contrast ratio to achieve
            
        Returns:
            tuple: (foreground QColor, background QColor)
        """
        current_ratio = AccessibilityUtils.calculate_contrast_ratio(base_fg, base_bg)
        
        if current_ratio >= min_ratio:
            return (QColor(base_fg), QColor(base_bg))
        
        # Adjust foreground to meet contrast
        adjusted_fg = AccessibilityUtils.adjust_color_for_contrast(base_fg, base_bg, min_ratio)
        return (adjusted_fg, QColor(base_bg))
    
    @staticmethod
    def enhance_stylesheet_contrast(stylesheet):
        """
        Process a stylesheet to improve color contrast.
        This is a simplified implementation - in a real app, you'd need a proper CSS parser.
        
        Args:
            stylesheet: The CSS stylesheet string
            
        Returns:
            str: Updated stylesheet with improved contrast colors
        """
        # This is a simplified approach. In a real application, you would use
        # a proper CSS parser to modify colors more accurately.
        
        # Colors used in both light and dark themes that need to be checked
        light_text = QColor("#202020")
        light_bg = QColor("#f5f5f5")
        dark_text = QColor("#e0e0e0")
        dark_bg = QColor("#2d2d2d")
        
        # Enhance some commonly used colors
        color_replacements = {
            # Light theme contrast improvements
            "#909090": AccessibilityUtils.adjust_color_for_contrast(
                QColor("#909090"), light_bg).name(),
                
            # Dark theme contrast improvements
            "#707070": AccessibilityUtils.adjust_color_for_contrast(
                QColor("#707070"), dark_bg).name(),
        }
        
        # Apply replacements
        for old_color, new_color in color_replacements.items():
            stylesheet = stylesheet.replace(old_color, new_color)
            
        return stylesheet 