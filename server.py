"""MCP Server for Gravitational Wave Data.

This server provides tools for querying gravitational wave events,
strain data, and alerts from GraceDB, GWOSC, and GCN.
"""
import asyncio
import logging
import sys
import os
from typing import Any
import json

# Add services directory to path so we can import directly
_current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_current_dir, "services"))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
)

from gracedb_service import get_gracedb_service, GraceDBService
from gwosc_service import get_gwosc_service, GWOSCService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server
server = Server("gw-mcp-server")


def format_json_response(data: Any) -> str:
    """Format data as pretty JSON string."""
    return json.dumps(data, indent=2, default=str)


# =============================================================================
# Tool Definitions
# =============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available GW data tools."""
    return [
        # GraceDB Tools
        Tool(
            name="search_gw_events",
            description="""Search for gravitational wave events in GraceDB.
            
You can filter by:
- far_threshold: Maximum False Alarm Rate in Hz (e.g., 1e-6 for significant events)
- gps_start/gps_end: GPS time range
- pipeline: Detection pipeline (gstlal, pycbc, cwb, etc.)
- group: Event group (CBC for compact binary, Burst)
- query: Raw GraceDB query string

Returns list of events with GraceID, GPS time, FAR, pipeline, and labels.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "far_threshold": {
                        "type": "number",
                        "description": "Maximum False Alarm Rate threshold in Hz"
                    },
                    "gps_start": {
                        "type": "number",
                        "description": "GPS start time for search range"
                    },
                    "gps_end": {
                        "type": "number",
                        "description": "GPS end time for search range"
                    },
                    "pipeline": {
                        "type": "string",
                        "description": "Filter by pipeline (gstlal, pycbc, cwb, spiir)"
                    },
                    "group": {
                        "type": "string",
                        "enum": ["CBC", "Burst", "Test"],
                        "description": "Filter by event group"
                    },
                    "query": {
                        "type": "string",
                        "description": "Raw GraceDB query string"
                    },
                    "max_results": {
                        "type": "integer",
                        "default": 20,
                        "description": "Maximum number of results"
                    }
                }
            }
        ),
        Tool(
            name="get_event_details",
            description="""Get detailed information about a specific GraceDB event.
            
Returns full metadata including:
- GPS time, FAR (False Alarm Rate)
- Pipeline and instruments
- Labels (DQV, ADVOK, PE_READY, etc.)
- Extra attributes (SNR, masses for CBC events)
- Links to files and logs""",
            inputSchema={
                "type": "object",
                "properties": {
                    "graceid": {
                        "type": "string",
                        "description": "GraceDB event ID (e.g., G1234, T1234 for test)"
                    }
                },
                "required": ["graceid"]
            }
        ),
        Tool(
            name="get_superevent",
            description="""Get information about a GraceDB superevent.
            
Superevents group related events from different pipelines for the same
astrophysical source. Returns superevent ID, preferred event, FAR, and labels.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "superevent_id": {
                        "type": "string",
                        "description": "Superevent ID (e.g., S230518h)"
                    }
                },
                "required": ["superevent_id"]
            }
        ),
        Tool(
            name="search_superevents",
            description="""Search for superevents in GraceDB.
            
Superevents are the primary way GW events are organized and announced.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "far_threshold": {
                        "type": "number",
                        "description": "Maximum FAR threshold"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["Production", "Test", "MDC"],
                        "description": "Filter by category"
                    },
                    "query": {
                        "type": "string",
                        "description": "Raw query string"
                    },
                    "max_results": {
                        "type": "integer",
                        "default": 20
                    }
                }
            }
        ),
        Tool(
            name="get_event_files",
            description="""List files associated with a GraceDB event.
            
Files may include:
- Skymaps (bayestar.fits, bilby.fits)
- Coinc XML files
- PSD (Power Spectral Density) files
- Parameter estimation results""",
            inputSchema={
                "type": "object",
                "properties": {
                    "graceid": {
                        "type": "string",
                        "description": "GraceDB event ID"
                    }
                },
                "required": ["graceid"]
            }
        ),
        Tool(
            name="get_event_labels",
            description="""Get labels for a GraceDB event.
            
Common labels:
- ADVREQ/ADVOK: Advocate review status
- DQV: Data quality veto
- PE_READY: Parameter estimation ready
- SKYMAP_READY: Skymap available
- GCN_PRELIM_SENT: GCN notice sent""",
            inputSchema={
                "type": "object",
                "properties": {
                    "graceid": {
                        "type": "string",
                        "description": "GraceDB event ID"
                    }
                },
                "required": ["graceid"]
            }
        ),
        
        # GWOSC Tools
        Tool(
            name="get_event_gps",
            description="""Get the GPS time for a named gravitational wave event.
            
Works for all confirmed events (GW150914, GW170817, etc.)""",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_name": {
                        "type": "string",
                        "description": "Event name (e.g., GW150914, GW170817)"
                    }
                },
                "required": ["event_name"]
            }
        ),
        Tool(
            name="get_catalog_events",
            description="""Get all events from a GWTC catalog.
            
Available catalogs:
- GWTC-1: First catalog (O1+O2)
- GWTC-2: Second catalog (O3a)
- GWTC-2.1: Updated O3a analysis
- GWTC-3: Third catalog (O3b)""",
            inputSchema={
                "type": "object",
                "properties": {
                    "catalog": {
                        "type": "string",
                        "enum": ["GWTC-1", "GWTC-2", "GWTC-2.1", "GWTC-3"],
                        "default": "GWTC-3",
                        "description": "Catalog name"
                    }
                }
            }
        ),
        Tool(
            name="fetch_strain_data",
            description="""Fetch gravitational wave strain data from GWOSC.
            
Returns statistics and metadata about the strain time series.
Use for analyzing detector data around specific GPS times.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "detector": {
                        "type": "string",
                        "enum": ["H1", "L1", "V1"],
                        "description": "Detector (H1=Hanford, L1=Livingston, V1=Virgo)"
                    },
                    "gps_start": {
                        "type": "number",
                        "description": "GPS start time"
                    },
                    "gps_end": {
                        "type": "number",
                        "description": "GPS end time"
                    },
                    "sample_rate": {
                        "type": "integer",
                        "default": 4096,
                        "description": "Sample rate in Hz"
                    }
                },
                "required": ["detector", "gps_start", "gps_end"]
            }
        ),
        Tool(
            name="fetch_event_strain",
            description="""Fetch strain data centered on a named GW event.
            
Convenient way to get data around known events like GW150914.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_name": {
                        "type": "string",
                        "description": "Event name (e.g., GW150914)"
                    },
                    "detector": {
                        "type": "string",
                        "enum": ["H1", "L1", "V1"],
                        "default": "H1",
                        "description": "Detector name"
                    },
                    "duration": {
                        "type": "number",
                        "default": 32.0,
                        "description": "Total duration in seconds centered on event"
                    },
                    "sample_rate": {
                        "type": "integer",
                        "default": 4096,
                        "description": "Sample rate in Hz"
                    }
                },
                "required": ["event_name"]
            }
        ),
        Tool(
            name="get_available_events",
            description="""Get list of all available GW events from GWOSC.
            
Can optionally filter by catalog.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "catalog": {
                        "type": "string",
                        "enum": ["GWTC-1", "GWTC-2", "GWTC-2.1", "GWTC-3"],
                        "description": "Optional catalog filter"
                    }
                }
            }
        ),
    ]


# =============================================================================
# Tool Implementations
# =============================================================================

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute a GW data tool."""
    
    try:
        # GraceDB Tools
        if name == "search_gw_events":
            service = get_gracedb_service()
            events = service.search_events(
                query=arguments.get("query"),
                far_threshold=arguments.get("far_threshold"),
                gps_start=arguments.get("gps_start"),
                gps_end=arguments.get("gps_end"),
                pipeline=arguments.get("pipeline"),
                group=arguments.get("group"),
                max_results=arguments.get("max_results", 20)
            )
            return [TextContent(
                type="text",
                text=f"Found {len(events)} events:\n\n{format_json_response(events)}"
            )]
            
        elif name == "get_event_details":
            service = get_gracedb_service()
            event = service.get_event(arguments["graceid"])
            return [TextContent(
                type="text",
                text=f"Event details for {arguments['graceid']}:\n\n{format_json_response(event)}"
            )]
            
        elif name == "get_superevent":
            service = get_gracedb_service()
            superevent = service.get_superevent(arguments["superevent_id"])
            return [TextContent(
                type="text",
                text=f"Superevent {arguments['superevent_id']}:\n\n{format_json_response(superevent)}"
            )]
            
        elif name == "search_superevents":
            service = get_gracedb_service()
            superevents = service.search_superevents(
                query=arguments.get("query"),
                far_threshold=arguments.get("far_threshold"),
                category=arguments.get("category"),
                max_results=arguments.get("max_results", 20)
            )
            return [TextContent(
                type="text",
                text=f"Found {len(superevents)} superevents:\n\n{format_json_response(superevents)}"
            )]
            
        elif name == "get_event_files":
            service = get_gracedb_service()
            files = service.get_event_files(arguments["graceid"])
            return [TextContent(
                type="text",
                text=f"Files for {arguments['graceid']}:\n\n{format_json_response(files)}"
            )]
            
        elif name == "get_event_labels":
            service = get_gracedb_service()
            labels = service.get_event_labels(arguments["graceid"])
            return [TextContent(
                type="text",
                text=f"Labels for {arguments['graceid']}: {labels}"
            )]
            
        # GWOSC Tools
        elif name == "get_event_gps":
            service = get_gwosc_service()
            gps = service.get_event_gps(arguments["event_name"])
            return [TextContent(
                type="text",
                text=f"GPS time for {arguments['event_name']}: {gps}"
            )]
            
        elif name == "get_catalog_events":
            service = get_gwosc_service()
            catalog = arguments.get("catalog", "GWTC-3")
            events = service.get_catalog_events(catalog)
            return [TextContent(
                type="text",
                text=f"{catalog} events ({len(events)} total):\n\n{format_json_response(events)}"
            )]
            
        elif name == "fetch_strain_data":
            service = get_gwosc_service()
            result = service.fetch_strain_data(
                detector=arguments["detector"],
                gps_start=arguments["gps_start"],
                gps_end=arguments["gps_end"],
                sample_rate=arguments.get("sample_rate", 4096)
            )
            return [TextContent(
                type="text",
                text=f"Strain data:\n\n{format_json_response(result)}"
            )]
            
        elif name == "fetch_event_strain":
            service = get_gwosc_service()
            result = service.fetch_event_strain(
                event_name=arguments["event_name"],
                detector=arguments.get("detector", "H1"),
                duration=arguments.get("duration", 32.0),
                sample_rate=arguments.get("sample_rate", 4096)
            )
            return [TextContent(
                type="text",
                text=f"Strain data for {arguments['event_name']}:\n\n{format_json_response(result)}"
            )]
            
        elif name == "get_available_events":
            service = get_gwosc_service()
            events = service.get_available_events(arguments.get("catalog"))
            return [TextContent(
                type="text",
                text=f"Available events ({len(events)} total):\n\n{events}"
            )]
            
        else:
            return [TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]
            
    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        return [TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]


async def run_server():
    """Run the MCP server."""
    logger.info("Starting GW MCP Server...")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


def main():
    """Entry point."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
