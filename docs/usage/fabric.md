# Fabric Usage

The `fabric` subpackage contains Microsoft Fabric-specific helpers.

These helpers are intentionally separated from the generic HTTP, auth, patching, and throttling logic because they depend on the Fabric notebook runtime.

## Imports

```python
from async_rest_factory.fabric import (
    get_key_vault_secret,
    load_latest_watermarks,
    write_rows_to_lakehouse_json,
)
```

---

## Runtime requirements

The `fabric` subpackage assumes the code is running inside a Microsoft Fabric notebook.

It uses:

```python
import notebookutils
```

inside functions instead of at module import time.

This keeps the base package importable outside Fabric, while still allowing Fabric-specific helpers to work when called inside notebooks.

---

## Package structure

```text
async_rest_factory/
    fabric/
        __init__.py
        key_vault.py
        lakehouse_files.py
        watermarks.py
```

---

## `fabric/__init__.py`

```python
# async_rest_factory/fabric/__init__.py

from async_rest_factory.fabric.key_vault import get_key_vault_secret
from async_rest_factory.fabric.lakehouse_files import write_rows_to_lakehouse_json
from async_rest_factory.fabric.watermarks import load_latest_watermarks

__all__ = [
    "get_key_vault_secret",
    "load_latest_watermarks",
    "write_rows_to_lakehouse_json",
]
```

---

# Key Vault secrets

Use `get_key_vault_secret()` to fetch secrets from Azure Key Vault using Fabric notebook credentials.

```python
from async_rest_factory.fabric import get_key_vault_secret


token = get_key_vault_secret("hubspot-api-token")
```

## Custom vault URL

```python
token = get_key_vault_secret(
    "hubspot-api-token",
    vault_url="https://andersfabric-kv.vault.azure.net/",
)
```

## Example with auth

```python
from async_rest_factory.auth import AuthContext, token_auth_context
from async_rest_factory.fabric import get_key_vault_secret


async def get_hubspot_auth_context() -> AuthContext:
    token = get_key_vault_secret("hubspot-api-token")

    return token_auth_context(
        header_name="Authorization",
        token=token,
        prefix="Bearer",
    )
```

---

# Load watermarks

Use `load_latest_watermarks()` to load the most recent watermark file from a Lakehouse folder.

```python
from async_rest_factory.fabric import load_latest_watermarks


watermarks = load_latest_watermarks("Files/hubspot/watermarks")
```

Expected behavior:

- lists `.json` files in the folder, ignoring subfolders
- picks the latest file by name, so use sortable names such as timestamps
- returns the parsed JSON content of that file
- returns `{}` when the folder cannot be listed or has no `.json` files

---

# Write API rows to Lakehouse Files

Use `write_rows_to_lakehouse_json()` to persist parsed API rows to the default Lakehouse `Files` area.

```python
from async_rest_factory.fabric import write_rows_to_lakehouse_json


path = write_rows_to_lakehouse_json(
    rows=rows,
    source_system="hubspot",
    table_name="deals",
)

print(path)
```

Default output path shape:

```text
/lakehouse/default/Files/{source_system}/{table_name}/data/{uuid}.json
```

Example:

```text
/lakehouse/default/Files/hubspot/deals/data/2eaa0f5e6c844fd8901d6d20c8f157fb.json
```

---

## Why the file extension is `.json`

The file content is newline-delimited JSON, but the extension is intentionally `.json`.

This is done so the Fabric UI recognizes the file as JSON during right-click **Load data** workflows.

The practical format is:

```text
.json extension
newline-delimited JSON content
```

Example file content:

```json
{"id": 1, "name": "A"}
{"id": 2, "name": "B"}
{"id": 3, "name": "C"}
```

This is not a single JSON array. It is one JSON object per line.

---

## Why the default path uses `/lakehouse/default/Files`

In pure Python Fabric notebooks, this path writes to persistent Lakehouse storage:

```python
"/lakehouse/default/Files"
```

That avoids temporary notebook directories that may not persist reliably.

Default root:

```python
/lakehouse/default/Files
```

Default full folder:

```python
/lakehouse/default/Files/{source_system}/{table_name}/data
```

---

## Override the Lakehouse root

Use `lakehouse_files_root` when writing somewhere other than the default attached Lakehouse.

```python
path = write_rows_to_lakehouse_json(
    rows=rows,
    source_system="hubspot",
    table_name="deals",
    lakehouse_files_root="/lakehouse/default/Files",
)
```

---

# End-to-end Fabric example

```python
import aiohttp

from async_rest_factory.auth import AuthContext, token_auth_context
from async_rest_factory.fabric import (
    get_key_vault_secret,
    write_rows_to_lakehouse_json,
)
from async_rest_factory.http import send_request


async def get_auth_context() -> AuthContext:
    token = get_key_vault_secret("hubspot-api-token")

    return token_auth_context(
        header_name="Authorization",
        token=token,
        prefix="Bearer",
    )


async def run_one_config(cfg: dict):
    auth_context = await get_auth_context()

    async with aiohttp.ClientSession(**auth_context.session_kwargs) as session:
        query_template = cfg.get("query_template") or {}

        body = await send_request(
            session=session,
            method=cfg["http_method"],
            url=cfg["endpoint"],
            params=query_template.get("request_parameters"),
            json_body=query_template.get("request_body"),
        )

    rows = body if isinstance(body, list) else body.get("results", [])

    return write_rows_to_lakehouse_json(
        rows=rows,
        source_system=cfg["source_system"],
        table_name=cfg["table_name"],
    )


configs = [
    {
        "source_system": "hubspot",
        "table_name": "deals",
        "http_method": "POST",
        "endpoint": "https://api.hubapi.com/crm/v3/objects/deals/search",
        "query_template": {
            "request_body": {"limit": 100},
        },
    },
]

for cfg in configs:
    path = await run_one_config(cfg)
    print(path)
```

---

# Design rule

The `fabric` subpackage should contain Fabric runtime concerns only.

Good examples:

```text
fetch secrets with notebookutils credentials
write files to Lakehouse Files
```

Avoid putting generic HTTP execution logic here.

Generic logic belongs in:

```text
http/
auth/
patching/
throttling/
runner.py
```

Fabric-specific input/output belongs in:

```text
fabric/
```