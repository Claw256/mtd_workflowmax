"""Service for managing WorkflowMax client relationships."""

from typing import Optional, List, Dict
from datetime import datetime

from ..core.exceptions import (
    ValidationError,
    ResourceNotFoundError,
    WorkflowMaxError
)
from ..core.logging import get_logger, with_logging
from ..core.utils import Timer
from ..models.relationship import Relationship
from ..repositories import repositories

logger = get_logger('workflowmax.services.relationship')

class RelationshipService:
    """Service for client relationship operations."""
    
    @with_logging
    def add_relationship(
        self,
        client_uuid: str,
        related_uuid: str,
        relationship_type: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        number_of_shared: Optional[int] = None,
        percentage: Optional[float] = None
    ) -> bool:
        """Add a relationship between clients.
        
        Args:
            client_uuid: UUID of primary client
            related_uuid: UUID of related client
            relationship_type: Type of relationship
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            number_of_shared: Optional number of shared items
            percentage: Optional percentage value
            
        Returns:
            True if relationship was added successfully
            
        Raises:
            ValidationError: If data validation fails
            ResourceNotFoundError: If client not found
            WorkflowMaxError: If API request fails
        """
        with Timer("Add client relationship"):
            # Verify clients exist
            if not repositories.contacts.exists(client_uuid):
                raise ResourceNotFoundError('Client', client_uuid)
            if not repositories.contacts.exists(related_uuid):
                raise ResourceNotFoundError('Client', related_uuid)
            
            # Create relationship model
            relationship = Relationship(
                client_uuid=client_uuid,
                related_client_uuid=related_uuid,
                type=relationship_type,
                start_date=start_date,
                end_date=end_date,
                number_of_shared=number_of_shared,
                percentage=percentage
            )
            
            # Add relationship
            return repositories.relationships.add_relationship(relationship)
    
    @with_logging
    def update_relationship(
        self,
        uuid: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        number_of_shared: Optional[int] = None,
        percentage: Optional[float] = None
    ) -> bool:
        """Update an existing relationship.
        
        Args:
            uuid: UUID of relationship to update
            start_date: Optional new start date (YYYY-MM-DD)
            end_date: Optional new end date (YYYY-MM-DD)
            number_of_shared: Optional new number of shared items
            percentage: Optional new percentage value
            
        Returns:
            True if relationship was updated successfully
            
        Raises:
            ValidationError: If data validation fails
            ResourceNotFoundError: If relationship not found
            WorkflowMaxError: If API request fails
        """
        with Timer("Update client relationship"):
            # Get existing relationship from client
            relationships = []
            for client in repositories.contacts.search():
                client_relationships = repositories.relationships.get_relationships_for_client(
                    client.uuid
                )
                relationships.extend(client_relationships)
            
            # Find relationship to update
            relationship = None
            for rel in relationships:
                if rel.uuid == uuid:
                    relationship = rel
                    break
            
            if relationship is None:
                raise ResourceNotFoundError('Relationship', uuid)
            
            # Update fields
            if start_date is not None:
                relationship.start_date = start_date
            if end_date is not None:
                relationship.end_date = end_date
            if number_of_shared is not None:
                relationship.number_of_shared = number_of_shared
            if percentage is not None:
                relationship.percentage = percentage
            
            # Update relationship
            return repositories.relationships.update_relationship(relationship)
    
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
            return repositories.relationships.delete_relationship(uuid)
    
    @with_logging
    def get_relationships(
        self,
        client_uuid: str,
        relationship_type: Optional[str] = None
    ) -> List[Relationship]:
        """Get relationships for a client.
        
        Args:
            client_uuid: UUID of client
            relationship_type: Optional type to filter by
            
        Returns:
            List of relationships
            
        Raises:
            ResourceNotFoundError: If client not found
            WorkflowMaxError: If API request fails
        """
        with Timer("Get client relationships"):
            # Verify client exists
            if not repositories.contacts.exists(client_uuid):
                raise ResourceNotFoundError('Client', client_uuid)
            
            # Get relationships
            relationships = repositories.relationships.get_relationships_for_client(
                client_uuid
            )
            
            # Filter by type if requested
            if relationship_type:
                relationships = [
                    r for r in relationships
                    if r.type == relationship_type
                ]
            
            return relationships
    
    @with_logging
    def get_relationship_network(
        self,
        client_uuid: str,
        max_depth: int = 2
    ) -> Dict[str, List[Dict]]:
        """Get network of related clients up to specified depth.
        
        Args:
            client_uuid: UUID of starting client
            max_depth: Maximum depth to traverse relationships
            
        Returns:
            Dictionary mapping client UUIDs to lists of related clients
            Format: {
                client_uuid: [
                    {
                        'uuid': related_uuid,
                        'type': relationship_type,
                        'depth': traversal_depth
                    }
                ]
            }
            
        Raises:
            ResourceNotFoundError: If client not found
            WorkflowMaxError: If API request fails
        """
        with Timer("Get relationship network"):
            network = {client_uuid: []}
            visited = {client_uuid}
            
            def traverse(current_uuid: str, depth: int):
                if depth >= max_depth:
                    return
                    
                relationships = self.get_relationships(current_uuid)
                
                for rel in relationships:
                    related_uuid = rel.related_client_uuid
                    
                    # Add to network
                    network[current_uuid].append({
                        'uuid': related_uuid,
                        'type': rel.type,
                        'depth': depth
                    })
                    
                    # Traverse further if not visited
                    if related_uuid not in visited:
                        visited.add(related_uuid)
                        network[related_uuid] = []
                        traverse(related_uuid, depth + 1)
            
            traverse(client_uuid, 0)
            return network
