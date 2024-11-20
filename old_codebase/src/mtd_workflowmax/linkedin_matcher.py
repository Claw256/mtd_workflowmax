"""Module for matching WorkflowMax contacts with LinkedIn profiles."""

import os
from typing import Optional, Dict, List, Tuple
from difflib import SequenceMatcher
from linkedin_api import Linkedin
from .models import Contact
from .contact_fetcher import get_workflowmax_contact, update_contact_custom_fields
from .logging_config import get_logger

logger = get_logger('workflowmax.linkedin_matcher')

class LinkedInMatcher:
    """Class for matching WorkflowMax contacts with LinkedIn profiles."""
    
    def __init__(self, linkedin_username: str, linkedin_password: str):
        """Initialize LinkedIn API client.
        
        Args:
            linkedin_username: LinkedIn account username
            linkedin_password: LinkedIn account password
        """
        self.api = Linkedin(linkedin_username, linkedin_password)
        logger.info("LinkedIn API client initialized")
        
    def calculate_similarity(self, contact: Contact, linkedin_profile: Dict) -> float:
        """Calculate similarity score between a WorkflowMax contact and LinkedIn profile.
        
        Args:
            contact: WorkflowMax contact
            linkedin_profile: LinkedIn profile data
            
        Returns:
            float: Similarity score between 0 and 1
        """
        # Get name similarity
        contact_name = contact.Name.lower()
        linkedin_name = f"{linkedin_profile.get('firstName', '')} {linkedin_profile.get('lastName', '')}".lower()
        name_similarity = SequenceMatcher(None, contact_name, linkedin_name).ratio()
        
        # Get company similarity if available
        company_similarity = 0.0
        if contact.ClientName and linkedin_profile.get('companyName'):
            company_similarity = SequenceMatcher(
                None, 
                contact.ClientName.lower(), 
                linkedin_profile['companyName'].lower()
            ).ratio()
            
        # Get position similarity if available
        position_similarity = 0.0
        if contact.Position and linkedin_profile.get('title'):
            position_similarity = SequenceMatcher(
                None,
                contact.Position.lower(),
                linkedin_profile['title'].lower()
            ).ratio()
            
        # Weight the similarities (name is most important)
        weighted_score = (
            name_similarity * 0.5 +  # 50% weight for name
            company_similarity * 0.3 +  # 30% weight for company
            position_similarity * 0.2  # 20% weight for position
        )
        
        logger.debug(
            f"Similarity scores for {contact.Name} vs {linkedin_name}:\n"
            f"Name: {name_similarity:.2f}\n"
            f"Company: {company_similarity:.2f}\n"
            f"Position: {position_similarity:.2f}\n"
            f"Weighted: {weighted_score:.2f}"
        )
        
        return weighted_score
        
    def find_linkedin_profile(self, contact: Contact) -> Optional[str]:
        """Search for matching LinkedIn profile for a WorkflowMax contact.
        
        Args:
            contact: WorkflowMax contact to find LinkedIn profile for
            
        Returns:
            Optional[str]: LinkedIn profile URL if found, None otherwise
        """
        try:
            # Split contact name into first and last name
            name_parts = contact.Name.split(maxsplit=1)
            if len(name_parts) != 2:
                logger.warning(f"Could not split name '{contact.Name}' into first and last name")
                return None
                
            first_name, last_name = name_parts
            
            # Search for the person on LinkedIn
            search_results = self.api.search_people(
                keyword_first_name=first_name,
                keyword_last_name=last_name,
                keyword_company=contact.ClientName if contact.ClientName else None,
                keyword_title=contact.Position if contact.Position else None
            )
            
            if not search_results:
                logger.info(f"No LinkedIn profiles found for {contact.Name}")
                return None
                
            # Get full profile data for each result and calculate similarity
            best_match = None
            best_score = 0.0
            
            for result in search_results[:5]:  # Check top 5 results
                profile_urn = result.get('urn_id')
                if not profile_urn:
                    continue
                    
                profile = self.api.get_profile(urn_id=profile_urn)
                score = self.calculate_similarity(contact, profile)
                
                if score > best_score:
                    best_score = score
                    # Get public profile URL
                    contact_info = self.api.get_profile_contact_info(urn_id=profile_urn)
                    profile_url = contact_info.get('public_profile_url')
                    if profile_url:
                        best_match = profile_url
            
            # Only return match if similarity is high enough
            if best_score >= 0.8:  # 80% similarity threshold
                logger.info(f"Found LinkedIn profile for {contact.Name} with {best_score:.2%} confidence")
                return best_match
            else:
                logger.info(f"No confident matches found for {contact.Name} (best score: {best_score:.2%})")
                return None
                
        except Exception as e:
            logger.error(f"Error finding LinkedIn profile for {contact.Name}: {str(e)}", exc_info=True)
            return None
            
    def update_missing_linkedin_profiles(self) -> Tuple[int, int]:
        """Update LinkedIn profile URLs for all contacts missing them.
        
        Returns:
            Tuple[int, int]: Count of (processed contacts, successful updates)
        """
        try:
            processed = 0
            updated = 0
            
            # Get all contacts
            # TODO: Implement method to get all contacts
            # For now, use test contact
            contact_uuid = os.getenv('WORKFLOWMAX_TEST_CONTACT_UUID')
            if not contact_uuid:
                logger.error("No test contact UUID provided")
                return processed, updated
                
            contact = get_workflowmax_contact(contact_uuid)
            if not contact:
                logger.error(f"Could not fetch contact {contact_uuid}")
                return processed, updated
                
            processed += 1
            
            # Check if LinkedIn profile is missing
            current_linkedin = contact.get_custom_field_value('LINKEDIN PROFILE')
            if current_linkedin:
                logger.info(f"Contact {contact.Name} already has LinkedIn profile")
                return processed, updated
                
            # Search for LinkedIn profile
            linkedin_url = self.find_linkedin_profile(contact)
            if not linkedin_url:
                logger.info(f"No LinkedIn profile found for {contact.Name}")
                return processed, updated
                
            # Update contact's LinkedIn profile
            if update_contact_custom_fields(contact.UUID, {
                'LINKEDIN PROFILE': linkedin_url
            }):
                logger.info(f"Updated LinkedIn profile for {contact.Name}")
                updated += 1
            else:
                logger.error(f"Failed to update LinkedIn profile for {contact.Name}")
            
            return processed, updated
            
        except Exception as e:
            logger.error(f"Error updating LinkedIn profiles: {str(e)}", exc_info=True)
            return processed, updated

def main():
    """Main entry point for LinkedIn profile matching."""
    # Get LinkedIn credentials from environment
    linkedin_username = os.getenv('LINKEDIN_USERNAME')
    linkedin_password = os.getenv('LINKEDIN_PASSWORD')
    
    if not linkedin_username or not linkedin_password:
        logger.error("LinkedIn credentials not found in environment")
        return
        
    try:
        matcher = LinkedInMatcher(linkedin_username, linkedin_password)
        processed, updated = matcher.update_missing_linkedin_profiles()
        
        logger.info(f"LinkedIn profile matching complete:")
        logger.info(f"Processed {processed} contacts")
        logger.info(f"Updated {updated} LinkedIn profiles")
        
    except Exception as e:
        logger.error(f"LinkedIn profile matching failed: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()
