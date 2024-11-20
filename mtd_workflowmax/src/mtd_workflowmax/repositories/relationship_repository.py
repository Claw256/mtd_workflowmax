"""Repository for managing WorkflowMax client relationships."""

from typing import Optional, List
import xml.etree.ElementTree as ET

from ..core.exceptions import (
    ResourceNotFoundError,
    ValidationError,
    XMLParsingError,
    WorkflowMaxError
)
from ..core.logging import get_logger, with_logging
from ..core.utils import Timer
from ..models.relationship import Relationship

logger = get_logger('workflowmax.repositories.relationship')

class RelationshipRepository:
    """Repository for client relationship operations."""
    
    def __init__(self, api_client):
        """Initialize repository.
        
        Args:
            api_client: Initialized API client instance
        """
        self.api_client = api_client
    
    @with_logging
    def add_relationship(self, relationship: Relationship) -> bool:
        """Add a relationship between clients.
        
        Args:
            relationship: Relationship to add
            
        Returns:
            True if relationship was added successfully
            
        Raises:
            ValidationError: If relationship data is invalid
            WorkflowMaxError: If API request fails
        """
        with Timer("Add client relationship"):
            # Generate XML payload
            xml_payload = relationship.to_xml()
            
            # Make request
            response = self.api_client.post(
                'client.api/addrelationship',
                data=xml_payload
            )
            
            try:
                xml_root = ET.fromstring(response.text.encode('utf-8'))
                status_elem = xml_root.find('Status')
                
                if status_elem is not None and status_elem.text == 'OK':
                    logger.info(
                        "Successfully added client relationship",
                        client_uuid=relationship.client_uuid,
                        related_uuid=relationship.related_client_uuid
                    )
                    return True
                    
                logger.error(
                    "Failed to add client relationship",
                    client_uuid=relationship.client_uuid,
                    related_uuid=relationship.related_client_uuid,
                    response=response.text
                )
                return False
                
            except Exception as e:
                logger.error(f"Failed to parse add relationship response: {str(e)}")
                raise XMLParsingError(f"Failed to parse add relationship response: {str(e)}")
    
    @with_logging
    def update_relationship(self, relationship: Relationship) -> bool:
        """Update an existing relationship.
        
        Args:
            relationship: Relationship to update
            
        Returns:
            True if relationship was updated successfully
            
        Raises:
            ValidationError: If relationship data is invalid
            ResourceNotFoundError: If relationship not found
            WorkflowMaxError: If API request fails
        """
        with Timer("Update client relationship"):
            if not relationship.uuid:
                raise ValidationError("Relationship UUID is required for updates")
            
            # Generate XML payload
            xml_payload = relationship.to_xml()
            
            # Make request
            response = self.api_client.post(
                'client.api/updaterelationship',
                data=xml_payload
            )
            
            try:
                xml_root = ET.fromstring(response.text.encode('utf-8'))
                status_elem = xml_root.find('Status')
                
                if status_elem is not None and status_elem.text == 'OK':
                    logger.info(
                        "Successfully updated client relationship",
                        relationship_uuid=relationship.uuid
                    )
                    return True
                    
                logger.error(
                    "Failed to update client relationship",
                    relationship_uuid=relationship.uuid,
                    response=response.text
                )
                return False
                
            except Exception as e:
                logger.error(f"Failed to parse update relationship response: {str(e)}")
                raise XMLParsingError(f"Failed to parse update relationship response: {str(e)}")
    
    @with_logging
    def delete_relationship(self, uuid: str) -> bool:
        """Delete a relationship.
        
        Args:
            uuid: UUID of relationship to delete
            
        Returns:
            True if relationship was deleted successfully
            
        Raises:
            ResourceNotFoundError: If relationship not found
            WorkflowMaxError: If API request fails
        """
        with Timer("Delete client relationship"):
            # Generate XML payload
            xml_payload = f'<Relationship><UUID>{uuid}</UUID></Relationship>'
            
            # Make request
            response = self.api_client.post(
                'client.api/deleterelationship',
                data=xml_payload
            )
            
            try:
                xml_root = ET.fromstring(response.text.encode('utf-8'))
                status_elem = xml_root.find('Status')
                
                if status_elem is not None and status_elem.text == 'OK':
                    logger.info(
                        "Successfully deleted client relationship",
                        relationship_uuid=uuid
                    )
                    return True
                    
                logger.error(
                    "Failed to delete client relationship",
                    relationship_uuid=uuid,
                    response=response.text
                )
                return False
                
            except Exception as e:
                logger.error(f"Failed to parse delete relationship response: {str(e)}")
                raise XMLParsingError(f"Failed to parse delete relationship response: {str(e)}")
    
    @with_logging
    def get_relationships_for_client(self, client_uuid: str) -> List[Relationship]:
        """Get all relationships for a client.
        
        Args:
            client_uuid: UUID of client
            
        Returns:
            List of relationships
            
        Raises:
            ResourceNotFoundError: If client not found
            WorkflowMaxError: If API request fails
        """
        with Timer("Get client relationships"):
            # Make request
            response = self.api_client.get(f'client.api/get/{client_uuid}')
            
            try:
                xml_root = ET.fromstring(response.text.encode('utf-8'))
                
                relationships = []
                relationships_elem = xml_root.find('Relationships')
                if relationships_elem is not None:
                    for rel_elem in relationships_elem.findall('Relationship'):
                        relationships.append(Relationship.from_xml(rel_elem))
                        
                return relationships
                
            except Exception as e:
                logger.error(f"Failed to parse relationships response: {str(e)}")
                raise XMLParsingError(f"Failed to parse relationships response: {str(e)}")
