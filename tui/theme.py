"""
IronSilo TUI Theme Configuration.
"""

from textual.theme import Theme


IRONSILO_THEME = Theme(
    name="ironsilo",
    primary="#00ff88",  # Bright green
    secondary="#00ccff",  # Cyan
    accent="#ff6600",  # Orange
    foreground="#ffffff",  # White
    background="#1a1a2e",  # Dark blue
    success="#00ff88",  # Green
    warning="#ffff00",  # Yellow
    error="#ff0000",  # Red
    surface="#16213e",  # Darker blue
    panel="#0f3460",  # Deep blue
    boost="#ffffff",
    dark_surface="#1a1a2e",
    dark_foreground="#ffffff",
    dark_background="#0d0d1a",
)


DEFAULT_THEME = Theme(
    name="default",
    primary="#007acc",
    secondary="#7c3aed",
    accent="#f472b6",
    foreground="#1e1e1e",
    background="#ffffff",
    success="#10b981",
    warning="#f59e0b",
    error="#ef4444",
    surface="#f3f4f6",
    panel="#e5e7eb",
    boost="#ffffff",
    dark_surface="#374151",
    dark_foreground="#f9fafb",
    dark_background="#111827",
)
