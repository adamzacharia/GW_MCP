"""GWOSC service for accessing public gravitational wave data.

GWOSC (Gravitational-Wave Open Science Center) provides public access to
LIGO/Virgo/KAGRA strain data and event catalogs.

Website: https://gwosc.org
Libraries: gwosc, gwpy
"""
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class GWOSCService:
    """Service for accessing GWOSC public gravitational wave data.
    
    This service provides access to:
    - Strain time-series data around events
    - Event catalogs (GWTC-1, GWTC-2, GWTC-3)
    - Data quality information
    - Event GPS times
    
    All data is public and requires no authentication.
    """
    
    # Known detectors
    DETECTORS = ["H1", "L1", "V1", "K1", "G1"]
    
    # GWTC catalog mappings
    CATALOGS = {
        "GWTC-1": "GWTC-1-confident",
        "GWTC-2": "GWTC-2", 
        "GWTC-2.1": "GWTC-2.1-confident",
        "GWTC-3": "GWTC-3-confident",
    }
    
    def __init__(self):
        """Initialize GWOSC service."""
        self._gwosc = None
        self._gwpy = None
        
    @property
    def gwosc(self):
        """Lazy import of gwosc module."""
        if self._gwosc is None:
            try:
                import gwosc
                self._gwosc = gwosc
                logger.info("GWOSC module loaded successfully")
            except ImportError:
                raise ImportError(
                    "gwosc is required. Install with: pip install gwosc"
                )
        return self._gwosc
    
    @property
    def gwpy_timeseries(self):
        """Lazy import of gwpy TimeSeries."""
        if self._gwpy is None:
            try:
                from gwpy.timeseries import TimeSeries
                self._gwpy = TimeSeries
                logger.info("GWpy module loaded successfully")
            except ImportError:
                raise ImportError(
                    "gwpy is required. Install with: pip install gwpy"
                )
        return self._gwpy
    
    def get_event_gps(self, event_name: str) -> float:
        """Get GPS time for a named gravitational wave event.
        
        Args:
            event_name: Event name (e.g., 'GW150914', 'GW170817')
            
        Returns:
            GPS time of the event
            
        Example:
            >>> service = GWOSCService()
            >>> gps = service.get_event_gps('GW150914')
            >>> print(gps)  # 1126259462.4
        """
        try:
            from gwosc.datasets import event_gps
            gps = event_gps(event_name)
            logger.info(f"GPS time for {event_name}: {gps}")
            return gps
        except Exception as e:
            logger.error(f"Failed to get GPS for {event_name}: {e}")
            raise
    
    def get_available_events(self, catalog: Optional[str] = None) -> List[str]:
        """Get list of available events.
        
        Args:
            catalog: Optional catalog name (GWTC-1, GWTC-2, GWTC-3)
            
        Returns:
            List of event names
        """
        try:
            from gwosc.datasets import find_datasets
            
            if catalog and catalog in self.CATALOGS:
                catalog_name = self.CATALOGS[catalog]
                datasets = find_datasets(type="event", catalog=catalog_name)
            else:
                datasets = find_datasets(type="event")
                
            return sorted(datasets)
        except Exception as e:
            logger.error(f"Failed to get available events: {e}")
            raise
    
    def get_event_info(self, event_name: str) -> Dict[str, Any]:
        """Get metadata for a specific event.
        
        Args:
            event_name: Event name (e.g., 'GW150914')
            
        Returns:
            Dictionary with event metadata
        """
        try:
            from gwosc.datasets import event_gps
            from gwosc.locate import get_event_urls
            
            gps = event_gps(event_name)
            
            # Get available data URLs for each detector
            detector_data = {}
            for detector in ["H1", "L1", "V1"]:
                try:
                    urls = get_event_urls(event_name, detector=detector)
                    detector_data[detector] = len(urls) > 0
                except:
                    detector_data[detector] = False
            
            return {
                "name": event_name,
                "gps": gps,
                "detectors": detector_data,
                "data_available": any(detector_data.values())
            }
        except Exception as e:
            logger.error(f"Failed to get info for {event_name}: {e}")
            raise
    
    def fetch_strain_data(
        self,
        detector: str,
        gps_start: float,
        gps_end: float,
        sample_rate: int = 4096
    ) -> Dict[str, Any]:
        """Fetch strain time-series data from GWOSC.
        
        Args:
            detector: Detector name (H1, L1, V1)
            gps_start: GPS start time
            gps_end: GPS end time
            sample_rate: Desired sample rate in Hz
            
        Returns:
            Dictionary with strain data information
            
        Note:
            This returns metadata about the data. For actual time series,
            use gwpy directly or the returned arrays.
        """
        if detector not in self.DETECTORS:
            raise ValueError(f"Unknown detector: {detector}. Valid: {self.DETECTORS}")
        
        try:
            TimeSeries = self.gwpy_timeseries
            
            # Fetch open data
            strain = TimeSeries.fetch_open_data(
                detector, 
                gps_start, 
                gps_end,
                sample_rate=sample_rate
            )
            
            return {
                "detector": detector,
                "gps_start": float(strain.t0.value),
                "gps_end": float(strain.t0.value + strain.duration.value),
                "duration": float(strain.duration.value),
                "sample_rate": float(strain.sample_rate.value),
                "samples": len(strain),
                "unit": str(strain.unit),
                "data_available": True,
                # Include basic statistics
                "statistics": {
                    "mean": float(strain.mean().value),
                    "std": float(strain.std().value),
                    "min": float(strain.min().value),
                    "max": float(strain.max().value),
                }
            }
        except Exception as e:
            logger.error(f"Failed to fetch strain data: {e}")
            return {
                "detector": detector,
                "gps_start": gps_start,
                "gps_end": gps_end,
                "data_available": False,
                "error": str(e)
            }
    
    def fetch_event_strain(
        self,
        event_name: str,
        detector: str = "H1",
        duration: float = 32.0,
        sample_rate: int = 4096
    ) -> Dict[str, Any]:
        """Fetch strain data centered around a named event.
        
        Args:
            event_name: Event name (e.g., 'GW150914')
            detector: Detector name
            duration: Total duration in seconds (centered on event)
            sample_rate: Sample rate in Hz
            
        Returns:
            Dictionary with strain data information
        """
        try:
            gps = self.get_event_gps(event_name)
            half_duration = duration / 2
            
            result = self.fetch_strain_data(
                detector=detector,
                gps_start=gps - half_duration,
                gps_end=gps + half_duration,
                sample_rate=sample_rate
            )
            
            result["event_name"] = event_name
            result["event_gps"] = gps
            
            return result
        except Exception as e:
            logger.error(f"Failed to fetch strain for event {event_name}: {e}")
            raise
    
    def get_run_segments(self, run: str = "O3") -> Dict[str, Any]:
        """Get information about an observing run.
        
        Args:
            run: Observing run name (O1, O2, O3, O4)
            
        Returns:
            Dictionary with run information
        """
        try:
            from gwosc.datasets import find_datasets
            
            datasets = find_datasets(type="run")
            run_datasets = [d for d in datasets if run in d]
            
            return {
                "run": run,
                "available_datasets": run_datasets,
                "count": len(run_datasets)
            }
        except Exception as e:
            logger.error(f"Failed to get run info for {run}: {e}")
            raise
    
    def get_catalog_events(self, catalog: str = "GWTC-3") -> List[Dict[str, Any]]:
        """Get all events from a specific catalog.
        
        Args:
            catalog: Catalog name (GWTC-1, GWTC-2, GWTC-2.1, GWTC-3)
            
        Returns:
            List of event information dictionaries
        """
        try:
            events = self.get_available_events(catalog)
            
            result = []
            for event_name in events:
                try:
                    gps = self.get_event_gps(event_name)
                    result.append({
                        "name": event_name,
                        "gps": gps,
                        "catalog": catalog
                    })
                except Exception as e:
                    logger.warning(f"Could not get GPS for {event_name}: {e}")
                    
            return result
        except Exception as e:
            logger.error(f"Failed to get catalog events: {e}")
            raise


# Singleton instance
_gwosc_service: Optional[GWOSCService] = None


def get_gwosc_service() -> GWOSCService:
    """Get or create singleton GWOSC service instance."""
    global _gwosc_service
    if _gwosc_service is None:
        _gwosc_service = GWOSCService()
    return _gwosc_service
