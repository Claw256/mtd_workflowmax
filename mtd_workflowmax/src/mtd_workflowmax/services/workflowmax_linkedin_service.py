"""WorkflowMax-specific LinkedIn service."""

import os
import json
from typing import Optional, Dict, Any, Tuple
from ..core.logging import get_logger, with_logging
from ..core.utils import Timer
from ..core.exceptions import WorkflowMaxError
from ..repositories import Repositories
from .linkedin_service import LinkedInService, log_section, log_subsection

logger = get_logger('workflowmax.services.linkedin')

class WorkflowMaxLinkedInService:
    """Service for matching WorkflowMax contacts with LinkedIn profiles."""
    
    def __init__(
        self,
        linkedin_username: str,
        linkedin_password: str,
        repositories: Repositories,
        authenticate: bool = True,
        refresh_cookies: bool = False,
        debug: bool = False,
        proxies: Dict[str, str] = {},
        cookies: Optional[Dict[str, str]] = None,
        cookies_dir: str = ''
    ):
        """Initialize WorkflowMax LinkedIn service."""
        try:
            self.repositories = repositories
            self.linkedin_username = linkedin_username
            self.linkedin_password = linkedin_password
            self.linkedin_options = {
                'authenticate': authenticate,
                'refresh_cookies': refresh_cookies,
                'debug': debug,
                'proxies': proxies,
                'cookies': cookies,
                'cookies_dir': cookies_dir
            }
            self._linkedin: Optional[LinkedInService] = None
            logger.info("WorkflowMax LinkedIn service initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize WorkflowMax LinkedIn service", error=str(e))
            raise WorkflowMaxError("Failed to initialize WorkflowMax LinkedIn service") from e
    
    @property
    def linkedin(self) -> LinkedInService:
        """Get LinkedIn service, initializing if needed."""
        if self._linkedin is None:
            self._linkedin = LinkedInService(
                self.linkedin_username,
                self.linkedin_password,
                repositories=self.repositories,
                **self.linkedin_options
            )
        return self._linkedin
    
    @with_logging
    def update_single_contact(
        self,
        contact_uuid: str,
        dry_run: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Update LinkedIn profile for a single contact."""
        try:
            logger.debug(log_section("UPDATING CONTACT"))
            
            # Get contact
            logger.debug("\nFetching contact details...")
            contact = self.repositories.contacts.get_by_uuid(contact_uuid)
            logger.debug(f"Retrieved contact: {contact.name}")
            
            # Check existing LinkedIn profile
            current_linkedin = contact.get_custom_field_value('LINKEDIN PROFILE')
            if current_linkedin:
                logger.info(log_subsection("Already Has LinkedIn Profile"))
                logger.info(f"Contact: {contact.name}")
                logger.info(f"LinkedIn: {current_linkedin}")
                return None
            
            # Search for LinkedIn profile
            match = self.linkedin.find_linkedin_profile(contact)
            if not match:
                logger.info(log_subsection("No Match Found"))
                logger.info(f"No LinkedIn profile found for {contact.name}")
                return None
            
            # Get profile URL or construct from public_id
            profile_url = match.get('url')
            if not profile_url and match.get('public_id'):
                profile_url = f"{self.linkedin.LINKEDIN_BASE_URL}{match['public_id']}"
            
            # Skip update if no URL available
            if not profile_url:
                logger.info(log_subsection("No URL Available"))
                logger.info(f"No LinkedIn URL available for {contact.name}")
                return None
            
            # Log match details
            logger.info(log_subsection("Match Found"))
            logger.info(f"Contact: {contact.name}")
            logger.info(f"LinkedIn URL: {profile_url}")
            logger.info(f"Score: {match['score']:.1%}")
            logger.info(f"Threshold: {self.linkedin.SIMILARITY_THRESHOLD:.1%}")
            logger.info(f"Status: {'✓ PASS' if match['score'] >= self.linkedin.SIMILARITY_THRESHOLD else '✗ FAIL'}")
            
            # Update contact if not dry run and score meets threshold
            if not dry_run and match['score'] >= self.linkedin.SIMILARITY_THRESHOLD:
                logger.debug(log_subsection("Updating Contact"))
                logger.debug(f"Contact: {contact.name}")
                logger.debug(f"LinkedIn URL: {profile_url}")
                
                # Update LinkedIn profile field
                success = self.repositories.contacts.update_custom_field(
                    contact.uuid,
                    'LINKEDIN PROFILE',
                    profile_url
                )
                
                if success:
                    logger.info(log_subsection("Update Successful"))
                    logger.info(f"✓ Updated LinkedIn profile for {contact.name}")
                else:
                    logger.error(log_subsection("Update Failed"))
                    logger.error(f"✗ Failed to update LinkedIn profile for {contact.name}")
                    return None
            else:
                logger.info(log_subsection("Dry Run"))
                logger.info(f"Would update LinkedIn profile for {contact.name}")
                logger.info(f"URL: {profile_url}")
                logger.info(f"Score: {match['score']:.1%}")
            
            return match
            
        except Exception as e:
            logger.error(f"Error updating contact {contact_uuid}", error=str(e))
            raise WorkflowMaxError(f"Failed to update contact {contact_uuid}") from e
    
    @with_logging
    def update_missing_linkedin_profiles(
        self,
        batch_size: int = 10,
        dry_run: bool = False
    ) -> Tuple[int, int]:
        """Update LinkedIn profile URLs for all contacts missing them."""
        with Timer("Update missing LinkedIn profiles"):
            processed = 0
            updated = 0
            page = 1
            
            logger.debug(log_section("BATCH PROCESSING CONTACTS"))
            
            while True:
                # Get batch of contacts
                try:
                    logger.debug(log_subsection(f"Processing Batch {page}"))
                    logger.debug(f"Batch size: {batch_size}")
                    
                    contacts = self.repositories.contacts.search(
                        page=page,
                        page_size=batch_size
                    )
                    
                    if not contacts:
                        logger.debug("\nNo more contacts to process")
                        break
                    
                    logger.debug(f"\nProcessing {len(contacts)} contacts...")
                    
                    for contact in contacts:
                        processed += 1
                        logger.debug(f"\nContact {processed}: {contact.name}")
                        
                        # Check if LinkedIn profile is missing
                        current_linkedin = contact.get_custom_field_value('LINKEDIN PROFILE')
                        if current_linkedin:
                            logger.debug("Already has LinkedIn profile")
                            continue
                        
                        # Try to update the contact
                        match = self.update_single_contact(contact.uuid, dry_run=dry_run)
                        if match and match['score'] >= self.linkedin.SIMILARITY_THRESHOLD:
                            updated += 1
                            logger.debug("Successfully processed")
                    
                    page += 1
                    logger.debug(f"\nCompleted batch {page - 1}")
                    
                except WorkflowMaxError as e:
                    logger.error("Error processing contacts batch", error=str(e))
                    break
            
            logger.info(log_section("PROCESSING COMPLETE"))
            mode = "[DRY RUN] " if dry_run else ""
            success_rate = (updated/processed*100) if processed > 0 else 0.0
            
            logger.info(f"{mode}Results:")
            logger.info(f"    Processed: {processed} contacts")
            logger.info(f"    Updated: {updated} LinkedIn profiles")
            logger.info(f"    Success Rate: {success_rate:.1f}%")
            
            return processed, updated
