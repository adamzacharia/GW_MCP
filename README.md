# GW MCP Server

An MCP (Model Context Protocol) server providing tools to query Gravitational Wave (GW) data from GraceDB and GWOSC.

## What is MCP?

MCP (Model Context Protocol) allows AI assistants like Claude to use external tools. This server gives Claude the ability to query gravitational wave databases in real-time, so you can ask questions about GW events in natural language.

## Sample Questions

Once connected, you can ask Claude questions like:

- "What was the GPS time of GW150914?"
- "Show me all events in the GWTC-3 catalog"
- "Get strain data from the Hanford detector around GW150914"
- "Search for gravitational wave events with FAR less than 1e-10"
- "What files are available for a specific GraceDB event?"

### Example

<img width="1012" height="703" alt="Screenshot 2026-01-05 203324" src="https://github.com/user-attachments/assets/7fd8c9ed-8a7f-49ac-a5de-afc642feec89" />

## Access Levels

| Source | Public Access | Authenticated Access |
|--------|--------------|---------------------|
| **GWOSC** | Full (strain data, catalogs) | N/A |
| **GraceDB** | Released events only | Full access to current observing run |
| **GCN Kafka** | No | Requires NASA Earthdata credentials |

**This server works out-of-the-box with public data only.**

---

## Installation

### Step 1: Create Conda Environment

```bash
# Create new conda environment with Python 3.11
conda create -n opticsGPT python=3.11 -y

# Activate the environment
conda activate opticsGPT
```

### Step 2: Install Dependencies

```bash
cd C:\Users\Asus\Desktop\OpticsGPT\GW_MCP

# Install from requirements.txt
pip install -r requirements.txt
```

### Step 3: Verify Installation

```bash
# Test GWOSC (should print GPS time)
python -c "from gwosc.datasets import event_gps; print('GW150914 GPS:', event_gps('GW150914'))"
```

---

## Usage with Claude Desktop

Add to `claude_desktop_config.json`:

Or create the file

```json
{
  "mcpServers": {
    "GW-Data": {
      "command": "C:/Users/Asus/anaconda3/envs/mcp/python.exe",
      "args": ["C:/Users/Asus/Desktop/GW_MCP/server.py"]
    }
  }
}
```

> **WARNING**: You must update the paths below to match your system. Change:
> - The Python executable path to your conda environment location
> - The server.py path to where you cloned this repository
>
> Find your Python path with: `conda activate mcp && where python`

---

## Available Tools

| Tool | Source | Description |
|------|--------|-------------|
| `search_gw_events` | GraceDB | Search events by FAR, GPS time, pipeline |
| `get_event_details` | GraceDB | Get full metadata for an event |
| `get_superevent` | GraceDB | Get superevent information |
| `get_event_files` | GraceDB | List files (skymaps, PSD, etc.) |
| `get_event_labels` | GraceDB | Get event labels (DQV, PE_READY, etc.) |
| `get_event_gps` | GWOSC | Get GPS time for named event (GW150914, etc.) |
| `get_catalog_events` | GWOSC | Query GWTC-1/2/3 catalogs |
| `fetch_strain_data` | GWOSC | Get strain time-series by GPS range |
| `fetch_event_strain` | GWOSC | Get strain centered on a named event |

---

## For LIGO/Virgo Collaboration Members

If you have LIGO credentials, you can access real-time alerts from the current observing run.

### How GraceDB Authentication Works

By default, the `ligo-gracedb` client searches for credentials in this order:

1. **SciToken** at `/tmp/bt_u${UID}` or `SCITOKEN_FILE` environment variable
2. **X.509 credentials** from the `cred` parameter (cert/key pair or proxy file)
3. **Environment variables**: `X509_USER_CERT` + `X509_USER_KEY`
4. **Environment variable**: `X509_USER_PROXY`
5. **Proxy from ligo-proxy-init**: `/tmp/x509up_u${UID}`
6. **Default location**: `~/.globus/usercert.pem` and `~/.globus/userkey.pem`
7. **No credentials** (public access only)

### Option 1: Using Environment Variables (Recommended)

Set these before running the MCP server:

```bash
# For SciToken
export SCITOKEN_FILE=/path/to/your/scitoken

# OR for X.509 certificate
export X509_USER_CERT=/path/to/usercert.pem
export X509_USER_KEY=/path/to/userkey.pem

# OR for proxy file
export X509_USER_PROXY=/tmp/x509up_u${UID}
```

### Option 2: Modify the Service Code

Edit `src/gw_mcp_server/services/gracedb_service.py`:

```python
# For X.509 cert/key pair:
self._client = GraceDb(
    cred=('/path/to/cert.pem', '/path/to/key.pem')
)

# For combined proxy file:
self._client = GraceDb(
    cred='/path/to/proxy.pem'
)

# To explicitly use only SciToken:
self._client = GraceDb(use_auth='scitoken')

# To explicitly use only X.509:
self._client = GraceDb(use_auth='x509')
```

### Option 3: Force Public Access Only

If you want to explicitly disable authentication attempts:

```python
self._client = GraceDb(force_noauth=True)
```

### Getting Credentials

1. **ligo-proxy-init**: Run `ligo-proxy-init` to create a short-lived proxy from your certificate
2. **htgettoken**: Use `htgettoken` to obtain a SciToken
3. **CILogon**: Get certificates from https://cilogon.org

### Test Your Authentication

```python
from ligo.gracedb.rest import GraceDb

client = GraceDb()
client.show_credentials()  # Prints auth type and info

# Test access to current run superevents
try:
    for se in client.superevents('category: Production', max_results=5):
        print(se['superevent_id'])
except Exception as e:
    print(f"Auth required: {e}")
```

### Useful GraceDb Client Options

```python
GraceDb(
    service_url='https://gracedb.ligo.org/api/',  # Production server
    # service_url='https://gracedb-playground.ligo.org/api/',  # Test server
    cred=None,                    # Path to credentials
    force_noauth=False,           # Skip credential lookup
    fail_if_noauth=False,         # Fail if no credentials found
    reload_cred=False,            # Auto-reload expiring credentials
    reload_buffer=300,            # Seconds before expiry to reload
    use_auth='all',               # 'all', 'scitoken', or 'x509'
    retries=5,                    # Max retries on server error
)
```

For full documentation: https://ligo-gracedb.readthedocs.io/en/latest/

---

## Data Sources

| Source | URL | Auth Required |
|--------|-----|---------------|
| **GWOSC** | https://gwosc.org | No |
| **GraceDB** | https://gracedb.ligo.org | For current run |
| **GCN** | https://gcn.nasa.gov | Yes (Earthdata) |

## License

MIT
