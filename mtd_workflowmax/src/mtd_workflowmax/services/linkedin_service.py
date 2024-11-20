"""Service for matching profiles with LinkedIn."""

import os
import json
import re
from typing import Optional, Dict, List, Tuple, Any
from difflib import SequenceMatcher
from linkedin_api import Linkedin

from ..core.exceptions import WorkflowMaxError
from ..core.logging import get_logger, with_logging
from ..core.utils import Timer
from ..repositories import Repositories
from ..models.profile_data import ProfileData

logger = get_logger('workflowmax.services.linkedin')

def log_section(title: str) -> str:
    """Create a visually distinct section header."""
    border = "=" * 80
    return f"\n{border}\n{title}\n{border}"

def log_subsection(title: str) -> str:
    """Create a visually distinct subsection header."""
    border = "-" * 40
    return f"\n{border}\n{title}\n{border}"

def log_json(obj: Any, fields: Optional[List[str]] = None) -> str:
    """Format object as indented JSON for logging.
    
    Args:
        obj: Object to format
        fields: Optional list of fields to include. If None, includes all fields.
    """
    if fields:
        filtered = {k: obj.get(k) for k in fields if k in obj}
        return json.dumps(filtered, indent=2, default=str)
    return json.dumps(obj, indent=2, default=str)

class LinkedInService:
    """Service for LinkedIn profile matching operations."""
    
    SIMILARITY_THRESHOLD = 0.7  # Minimum overall similarity score required for a match
    NAME_THRESHOLD = 0.8  # Minimum name similarity required
    EXPERIENCE_THRESHOLD = 0.3  # Minimum experience similarity required
    DEFAULT_CACHE_DIR = '.linkedin'
    MAX_SEARCH_RESULTS = 10  # Limit search results to prevent timeouts
    REQUEST_TIMEOUT = 30  # Request timeout in seconds
    LINKEDIN_BASE_URL = "https://www.linkedin.com/in/"
    
    # Fields to include in profile logging
    PROFILE_LOG_FIELDS = ['lastName', 'firstName', 'location', 'experience', 'companyName', 'title', 'locationName']
    
    def __init__(
        self,
        linkedin_username: str,
        linkedin_password: str,
        repositories: Optional[Repositories] = None,
        authenticate: bool = True,
        refresh_cookies: bool = False,
        debug: bool = False,
        proxies: Dict[str, str] = {},
        cookies: Optional[Dict[str, str]] = None,
        cookies_dir: str = ''
    ):
        """Initialize LinkedIn API client."""
        try:
            cookies_dir = cookies_dir or self.DEFAULT_CACHE_DIR
            os.makedirs(cookies_dir, exist_ok=True)
            
            self.api = Linkedin(
                linkedin_username,
                linkedin_password,
                authenticate=authenticate,
                refresh_cookies=refresh_cookies,
                debug=debug,
                proxies=proxies,
                cookies=cookies,
                cookies_dir=cookies_dir
            )
            self.repositories = repositories
            logger.info("LinkedIn API client initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize LinkedIn API client", error=str(e))
            raise WorkflowMaxError("LinkedIn authentication failed") from e
    
    def _clean_text(self, text: str) -> str:
        """Clean text by replacing special characters with spaces."""
        if not text:
            return ""
            
        # Convert to lowercase
        cleaned = text.lower()
        
        # Replace special characters with spaces
        cleaned = re.sub(r'[^a-z0-9\s]', ' ', cleaned)
        
        # Normalize spaces (remove duplicates)
        cleaned = ' '.join(part for part in cleaned.split() if part)
        
        return cleaned

    def _analyze_experience(self, linkedin_profile: Dict, target_company: str, target_title: str) -> Dict[str, Any]:
        """Analyze experience entries to find potential matches.
        
        Args:
            linkedin_profile: LinkedIn profile data
            target_company: Company name to look for
            target_title: Job title to look for
            
        Returns:
            Dict containing analysis results
        """
        experience = linkedin_profile.get('experience', [])
        if not experience:
            return {
                'has_company_match': False,
                'has_title_match': False,
                'best_company': None,
                'best_title': None,
                'company_similarity': 0.0,
                'title_similarity': 0.0
            }

        # Clean target values
        target_company = self._clean_text(target_company)
        target_title = self._clean_text(target_title)

        # Track best matches
        best_company = None
        best_title = None
        best_company_score = 0.0
        best_title_score = 0.0
        has_company_match = False
        has_title_match = False

        # Log experience entries
        logger.debug("\nExperience Entries:")
        for i, role in enumerate(experience):
            logger.debug(f"\nRole {i + 1}:")
            company = role.get('companyName', '')
            title = role.get('title', '')
            logger.debug(f"Company: {company}")
            logger.debug(f"Title: {title}")
            
            if 'timePeriod' in role:
                period = role['timePeriod']
                start = period.get('startDate', {})
                end = period.get('endDate', {})
                logger.debug(f"Period: {start.get('month', '')}/{start.get('year', '')} - {end.get('month', '')}/{end.get('year', '')}")
            if 'description' in role:
                logger.debug(f"Description: {role['description']}")

            # Compare company names
            if company:
                company_clean = self._clean_text(company)
                score = SequenceMatcher(None, target_company, company_clean).ratio()
                if score > best_company_score:
                    best_company_score = score
                    best_company = company
                if score >= 0.8:  # High confidence match
                    has_company_match = True

            # Compare job titles
            if title:
                title_clean = self._clean_text(title)
                score = SequenceMatcher(None, target_title, title_clean).ratio()
                if score > best_title_score:
                    best_title_score = score
                    best_title = title
                if score >= 0.8:  # High confidence match
                    has_title_match = True

        return {
            'has_company_match': has_company_match,
            'has_title_match': has_title_match,
            'best_company': best_company,
            'best_title': best_title,
            'company_similarity': best_company_score,
            'title_similarity': best_title_score
        }
    
    @with_logging
    def calculate_similarity(self, profile: ProfileData, linkedin_profile: Dict) -> float:
        """Calculate similarity score between a profile and LinkedIn profile."""
        with Timer("Calculate profile similarity"):
            logger.debug(log_section("PROFILE COMPARISON"))
            
            # Log filtered LinkedIn profile data
            logger.debug("\nRaw LinkedIn Profile:")
            logger.debug(log_json(linkedin_profile, self.PROFILE_LOG_FIELDS))
            
            # Analyze experience data
            experience_analysis = self._analyze_experience(
                linkedin_profile,
                profile.company_name,
                profile.position_title
            )
            
            # Log profile details
            logger.debug("\nWorkflowMax Contact:")
            logger.debug(f"    Name: {profile.name}")
            logger.debug(f"    Company: {profile.company_name or 'N/A'}")
            logger.debug(f"    Position: {profile.position_title or 'N/A'}")
            
            logger.debug("\nLinkedIn Profile:")
            logger.debug(f"    Name: {linkedin_profile.get('firstName', '')} {linkedin_profile.get('lastName', '')}")
            logger.debug(f"    Company: {experience_analysis['best_company'] or 'N/A'}")
            logger.debug(f"    Title: {experience_analysis['best_title'] or 'N/A'}")
            
            # Calculate name similarity
            profile_name = self._clean_text(profile.name)
            linkedin_name = self._clean_text(f"{linkedin_profile.get('firstName', '')} {linkedin_profile.get('lastName', '')}")
            name_similarity = SequenceMatcher(None, profile_name, linkedin_name).ratio()
            
            logger.debug(log_subsection("Name Comparison"))
            logger.debug(f"    WorkflowMax: {profile_name}")
            logger.debug(f"    LinkedIn: {linkedin_name}")
            logger.debug(f"    Similarity: {name_similarity:.1%}")
            
            # Log experience matches
            logger.debug(log_subsection("Experience Analysis"))
            logger.debug(f"    Has Company Match: {experience_analysis['has_company_match']}")
            logger.debug(f"    Has Title Match: {experience_analysis['has_title_match']}")
            if experience_analysis['best_company']:
                logger.debug(f"    Best Company: {experience_analysis['best_company']}")
                logger.debug(f"    Company Similarity: {experience_analysis['company_similarity']:.1%}")
            if experience_analysis['best_title']:
                logger.debug(f"    Best Title: {experience_analysis['best_title']}")
                logger.debug(f"    Title Similarity: {experience_analysis['title_similarity']:.1%}")
            
            # Calculate experience similarity score
            # Take the maximum of company and title similarity
            experience_similarity = max(
                experience_analysis['company_similarity'],
                experience_analysis['title_similarity']
            )
            
            # Check if both name and experience meet minimum thresholds
            if name_similarity < self.NAME_THRESHOLD or experience_similarity < self.EXPERIENCE_THRESHOLD:
                weighted_score = 0.0
            else:
                # Calculate weighted score only if both thresholds are met
                weighted_score = (
                    name_similarity * 0.6 +        # 60% weight for name
                    experience_similarity * 0.4     # 40% weight for experience
                )
            
            logger.debug(log_subsection("Final Score"))
            logger.debug("    Component Scores:")
            logger.debug(f"        Name:       {name_similarity:.1%} (threshold {self.NAME_THRESHOLD:.1%})")
            logger.debug(f"        Experience: {experience_similarity:.1%} (threshold {self.EXPERIENCE_THRESHOLD:.1%})")
            logger.debug(f"    Total Score: {weighted_score:.1%}")
            logger.debug(f"    Required Score: {self.SIMILARITY_THRESHOLD:.1%}")
            logger.debug(f"    Match Status: {'✓ PASS' if weighted_score >= self.SIMILARITY_THRESHOLD else '✗ FAIL'}")
            
            return weighted_score
    
    @with_logging
    def find_linkedin_profile(self, profile: ProfileData) -> Optional[Dict[str, Any]]:
        """Search for matching LinkedIn profile."""
        with Timer("Find LinkedIn profile"):
            try:
                logger.debug(log_section("LINKEDIN SEARCH"))
                
                # Split name into first and last name
                name_parts = profile.name.split(maxsplit=1)
                if len(name_parts) != 2:
                    logger.warning(f"Could not split name '{profile.name}' into first and last name")
                    return None
                
                first_name, last_name = name_parts
                first_name = self._clean_text(first_name)
                last_name = self._clean_text(last_name)
                
                logger.debug("\nSearch Parameters:")
                logger.debug(f"    First Name: {first_name}")
                logger.debug(f"    Last Name: {last_name}")
                
                # Search by name only, including private profiles
                search_results = self.api.search_people(
                    keyword_first_name=first_name,
                    keyword_last_name=last_name,
                    include_private_profiles=True,
                    limit=self.MAX_SEARCH_RESULTS
                )
                
                # Log raw search results
                logger.debug("\nRaw Search Results:")
                logger.debug(log_json(search_results))
                
                if not search_results:
                    logger.debug(f"\nNo LinkedIn profiles found for {profile.name}")
                    return None
                
                logger.debug(f"\nFound {len(search_results)} potential matches")
                
                # Process results
                best_match = None
                best_score = 0.0
                
                logger.debug(log_section("ANALYZING MATCHES"))
                
                for i, result in enumerate(search_results[:5]):
                    profile_urn = result.get('urn_id')
                    if not profile_urn:
                        continue
                    
                    logger.debug(f"\nAnalyzing Match #{i + 1}")
                    logger.debug(f"URN: {profile_urn}")
                    logger.debug("\nRaw Search Result:")
                    logger.debug(log_json(result))
                    
                    linkedin_profile = self.api.get_profile(urn_id=profile_urn)
                    logger.debug("\nRaw Profile Data:")
                    logger.debug(log_json(linkedin_profile, self.PROFILE_LOG_FIELDS))
                    
                    score = self.calculate_similarity(profile, linkedin_profile)
                    
                    # Get contact info for this profile
                    contact_info = self.api.get_profile_contact_info(urn_id=profile_urn)
                    logger.debug("\nRaw Contact Info:")
                    logger.debug(log_json(contact_info))
                    
                    # Store match if score meets threshold
                    if score > best_score:
                        best_score = score
                        experience_analysis = self._analyze_experience(
                            linkedin_profile,
                            profile.company_name,
                            profile.position_title
                        )
                        
                        # Get profile URL from contact info or construct from public_id
                        profile_url = contact_info.get('public_profile_url')
                        if not profile_url and linkedin_profile.get('public_id'):
                            profile_url = f"{self.LINKEDIN_BASE_URL}{linkedin_profile['public_id']}"
                        
                        best_match = {
                            'url': profile_url,
                            'score': score,
                            'name': f"{linkedin_profile.get('firstName', '')} {linkedin_profile.get('lastName', '')}",
                            'company': experience_analysis['best_company'],
                            'title': experience_analysis['best_title'],
                            'public_id': linkedin_profile.get('public_id')
                        }
                        logger.debug("\nNew best match found!")
                        logger.debug(f"Score: {score:.1%}")
                        logger.debug("Match Details:")
                        logger.debug(log_json(best_match))
                
                # Return the best match if it meets the threshold
                if best_match and best_match['score'] >= self.SIMILARITY_THRESHOLD:
                    logger.debug(log_section("MATCH FOUND"))
                    logger.debug(f"Found LinkedIn profile for {profile.name}")
                    logger.debug(f"Score: {best_score:.1%}")
                    logger.debug(f"Threshold: {self.SIMILARITY_THRESHOLD:.1%}")
                    logger.debug(f"Status: ✓ PASS")
                    logger.debug("Final Match Details:")
                    logger.debug(log_json(best_match))
                    return best_match
                else:
                    logger.debug(log_section("NO MATCH"))
                    if best_match:
                        logger.debug(f"Best match found but score ({best_score:.1%}) below threshold ({self.SIMILARITY_THRESHOLD:.1%})")
                        logger.debug("Best Match Details:")
                        logger.debug(log_json(best_match))
                    else:
                        logger.debug(f"No LinkedIn profiles found for {profile.name}")
                    return None
                    
            except Exception as e:
                logger.error(f"Error finding LinkedIn profile for {profile.name}", error=str(e))
                raise WorkflowMaxError("LinkedIn profile search failed") from e
