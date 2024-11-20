"""Protocol for profile data that can be matched with LinkedIn."""

from typing import Optional, runtime_checkable, Protocol

@runtime_checkable
class ProfileData(Protocol):
    """Protocol for profile data that can be matched with LinkedIn."""
    
    @property
    def name(self) -> str:
        """Full name of the person."""
        ...
    
    @property
    def company_name(self) -> Optional[str]:
        """Company name, if available."""
        ...
    
    @property
    def position_title(self) -> Optional[str]:
        """Position/job title, if available."""
        ...
