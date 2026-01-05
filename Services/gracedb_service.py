"""GraceDB service for querying gravitational wave events.

This service wraps the ligo-gracedb Python client to provide
access to the GraceDB API for querying events and superevents.

Documentation: https://ligo-gracedb.readthedocs.io
"""
import logging
from typing import Optional, List, Dict, Any
from functools import lru_cache

logger = logging.getLogger(__name__)


class GraceDBService:
    """Service for interacting with GraceDB API.
    
    GraceDB (Gravitational-wave Candidate Event Database) is the central
    database for LIGO/Virgo/KAGRA gravitational wave candidate events.
    
    Note: Full access to current observing run data requires LIGO credentials.
    Public access is available for released events.
    """
    
    def __init__(self, service_url: Optional[str] = None):
        """Initialize GraceDB client.
        
        Args:
            service_url: Optional custom GraceDB URL. Defaults to production.
        """
        self._client = None
        self._service_url = service_url
        
    @property
    def client(self):
        """Lazy initialization of GraceDB client."""
        if self._client is None:
            try:
                from ligo.gracedb.rest import GraceDb
                self._client = GraceDb(service_url=self._service_url) if self._service_url else GraceDb()
                logger.info("GraceDB client initialized successfully")
            except ImportError:
                raise ImportError(
                    "ligo-gracedb is required. Install with: pip install ligo-gracedb"
                )
            except Exception as e:
                logger.error(f"Failed to initialize GraceDB client: {e}")
                raise
        return self._client
    
    def get_event(self, graceid: str) -> Dict[str, Any]:
        """Retrieve a specific event by GraceID.
        
        Args:
            graceid: The GraceDB event ID (e.g., 'G1234', 'T1234' for test events)
            
        Returns:
            Dictionary containing event metadata
            
        Example:
            >>> service = GraceDBService()
            >>> event = service.get_event('G1234')
            >>> print(event['graceid'], event['far'])
        """
        try:
            response = self.client.event(graceid)
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get event {graceid}: {e}")
            raise
    
    def get_superevent(self, superevent_id: str) -> Dict[str, Any]:
        """Retrieve a superevent by ID.
        
        Superevents group related events from different pipelines
        for the same astrophysical source.
        
        Args:
            superevent_id: The superevent ID (e.g., 'S230518h')
            
        Returns:
            Dictionary containing superevent metadata
        """
        try:
            response = self.client.superevent(superevent_id)
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get superevent {superevent_id}: {e}")
            raise
    
    def search_events(
        self,
        query: Optional[str] = None,
        far_threshold: Optional[float] = None,
        gps_start: Optional[float] = None,
        gps_end: Optional[float] = None,
        pipeline: Optional[str] = None,
        group: Optional[str] = None,
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """Search for events matching criteria.
        
        Args:
            query: GraceDB query string (e.g., 'far < 1e-6')
            far_threshold: Maximum false alarm rate in Hz
            gps_start: Minimum GPS time
            gps_end: Maximum GPS time  
            pipeline: Filter by pipeline (gstlal, pycbc, cwb, etc.)
            group: Filter by group (CBC, Burst, Test)
            max_results: Maximum number of results to return
            
        Returns:
            List of event dictionaries
            
        Example:
            >>> events = service.search_events(far_threshold=1e-6, max_results=10)
        """
        # Build query string
        query_parts = []
        
        if query:
            query_parts.append(query)
        if far_threshold is not None:
            query_parts.append(f"far < {far_threshold}")
        if gps_start is not None:
            query_parts.append(f"gpstime >= {gps_start}")
        if gps_end is not None:
            query_parts.append(f"gpstime <= {gps_end}")
        if pipeline:
            query_parts.append(f"pipeline = {pipeline}")
        if group:
            query_parts.append(f"group = {group}")
            
        full_query = " ".join(query_parts) if query_parts else None
        
        try:
            if full_query:
                response = self.client.events(query=full_query)
            else:
                response = self.client.events()
                
            events = []
            for event in response:
                events.append(event)
                if len(events) >= max_results:
                    break
            return events
        except Exception as e:
            logger.error(f"Failed to search events with query '{full_query}': {e}")
            raise
    
    def search_superevents(
        self,
        query: Optional[str] = None,
        far_threshold: Optional[float] = None,
        category: Optional[str] = None,
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """Search for superevents matching criteria.
        
        Args:
            query: GraceDB query string
            far_threshold: Maximum FAR threshold
            category: Filter by category (Production, Test, MDC)
            max_results: Maximum results
            
        Returns:
            List of superevent dictionaries
        """
        query_parts = []
        
        if query:
            query_parts.append(query)
        if far_threshold is not None:
            query_parts.append(f"far < {far_threshold}")
        if category:
            query_parts.append(f"category = {category}")
            
        full_query = " ".join(query_parts) if query_parts else None
        
        try:
            if full_query:
                response = self.client.superevents(query=full_query)
            else:
                response = self.client.superevents()
                
            superevents = []
            for se in response:
                superevents.append(se)
                if len(superevents) >= max_results:
                    break
            return superevents
        except Exception as e:
            logger.error(f"Failed to search superevents: {e}")
            raise
    
    def get_event_files(self, graceid: str) -> List[Dict[str, Any]]:
        """Get list of files associated with an event.
        
        Files may include:
        - Skymaps (bayestar.fits, bilby.fits, etc.)
        - Coinc XML files
        - PSD files
        - Log files
        
        Args:
            graceid: Event GraceID
            
        Returns:
            List of file metadata dictionaries
        """
        try:
            response = self.client.files(graceid)
            files_data = response.json()
            
            # Convert to list format
            files = []
            for filename, url in files_data.items():
                files.append({
                    "filename": filename,
                    "download_url": url
                })
            return files
        except Exception as e:
            logger.error(f"Failed to get files for {graceid}: {e}")
            raise
    
    def get_event_logs(self, graceid: str, max_entries: int = 50) -> List[Dict[str, Any]]:
        """Get log entries for an event.
        
        Log entries contain human activity, comments, and automated updates.
        
        Args:
            graceid: Event GraceID
            max_entries: Maximum log entries to return
            
        Returns:
            List of log entry dictionaries
        """
        try:
            response = self.client.logs(graceid)
            logs_data = response.json()
            
            logs = logs_data.get('log', [])
            return logs[:max_entries]
        except Exception as e:
            logger.error(f"Failed to get logs for {graceid}: {e}")
            raise
    
    def get_event_labels(self, graceid: str) -> List[str]:
        """Get labels applied to an event.
        
        Common labels include:
        - ADVREQ: Advocate review requested
        - ADVOK: Advocate approved
        - DQV: Data quality veto
        - PE_READY: Parameter estimation ready
        - SKYMAP_READY: Skymap available
        
        Args:
            graceid: Event GraceID
            
        Returns:
            List of label strings
        """
        try:
            event = self.get_event(graceid)
            return event.get('labels', [])
        except Exception as e:
            logger.error(f"Failed to get labels for {graceid}: {e}")
            raise
    
    def download_file(self, graceid: str, filename: str) -> bytes:
        """Download a file associated with an event.
        
        Args:
            graceid: Event GraceID
            filename: Name of file to download (e.g., 'bayestar.multiorder.fits')
            
        Returns:
            File contents as bytes
        """
        try:
            response = self.client.files(graceid, filename)
            return response.read()
        except Exception as e:
            logger.error(f"Failed to download {filename} for {graceid}: {e}")
            raise


# Singleton instance for reuse
_gracedb_service: Optional[GraceDBService] = None


def get_gracedb_service() -> GraceDBService:
    """Get or create singleton GraceDB service instance."""
    global _gracedb_service
    if _gracedb_service is None:
        _gracedb_service = GraceDBService()
    return _gracedb_service
