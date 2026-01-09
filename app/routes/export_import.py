from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
import csv
import os
import json
from datetime import datetime
from pathlib import Path

from .. import crud

router = APIRouter(prefix="/api", tags=["export-import"])

# Directory for exports/imports - relative to project root
EXPORT_DIR = Path(__file__).parent.parent.parent / "exports"
EXPORT_DIR.mkdir(exist_ok=True)


class FilePathRequest(BaseModel):
    file_path: str


class ExportResponse(BaseModel):
    success: bool
    file_path: str
    records_exported: int
    message: str


class ImportResponse(BaseModel):
    success: int
    skipped: int = 0
    errors: List[dict] = []
    mode: str
    total_rows: int = 0


# ============ ENTRIES EXPORT ============

@router.post("/responses/export", response_model=ExportResponse)
async def export_responses(filename: Optional[str] = None):
    """Export all responses/entries to a CSV file on the server."""
    # Get all responses with details
    responses = crud.get_responses()

    # Get config for name lookups
    functions = {f['id']: f['name'] for f in crud.get_functions()}
    teams = {t['id']: t['name'] for t in crud.get_teams()}
    capabilities = {c['id']: c['name'] for c in crud.get_capabilities()}
    tools = {t['id']: t['name'] for t in crud.get_tools()}

    # Generate filename if not provided
    if not filename:
        filename = f"entries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    file_path = EXPORT_DIR / filename

    fieldnames = [
        'id', 'function', 'team', 'method_type', 'capability', 'capability_other',
        'description', 'tools', 'other_tools',
        'impact1_type', 'impact1_value', 'impact1_frequency', 'impact1_time_unit', 'impact1_annual_value', 'impact1_description',
        'impact2_type', 'impact2_value', 'impact2_frequency', 'impact2_time_unit', 'impact2_annual_value', 'impact2_description',
        'impact3_type', 'impact3_value', 'impact3_frequency', 'impact3_time_unit', 'impact3_annual_value', 'impact3_description',
        'impact4_type', 'impact4_value', 'impact4_frequency', 'impact4_time_unit', 'impact4_annual_value', 'impact4_description',
        'submitted_by', 'submitted_at'
    ]

    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for r in responses:
            # Parse tools_used JSON to get tool names
            tool_names = []
            if r.get('tools_used'):
                try:
                    tool_ids = json.loads(r['tools_used'])
                    tool_names = [tools.get(tid, f"Unknown({tid})") for tid in tool_ids if isinstance(tid, int)]
                except (json.JSONDecodeError, TypeError):
                    tool_names = []

            # Parse other_tools JSON
            other_tools_list = []
            if r.get('other_tools'):
                try:
                    other_tools_list = json.loads(r['other_tools'])
                except (json.JSONDecodeError, TypeError):
                    other_tools_list = []

            row = {
                'id': r.get('id'),
                'function': functions.get(r.get('function_id'), ''),
                'team': teams.get(r.get('team_id'), ''),
                'method_type': r.get('method_type', ''),
                'capability': capabilities.get(r.get('capability_id'), ''),
                'capability_other': r.get('capability_other', ''),
                'description': r.get('description', ''),
                'tools': ', '.join(tool_names),
                'other_tools': ', '.join(other_tools_list) if other_tools_list else '',
                'impact1_type': r.get('impact1_type', ''),
                'impact1_value': r.get('impact1_value', ''),
                'impact1_frequency': r.get('impact1_frequency', ''),
                'impact1_time_unit': r.get('impact1_time_unit', ''),
                'impact1_annual_value': r.get('impact1_annual_value', ''),
                'impact1_description': r.get('impact1_description', ''),
                'impact2_type': r.get('impact2_type', ''),
                'impact2_value': r.get('impact2_value', ''),
                'impact2_frequency': r.get('impact2_frequency', ''),
                'impact2_time_unit': r.get('impact2_time_unit', ''),
                'impact2_annual_value': r.get('impact2_annual_value', ''),
                'impact2_description': r.get('impact2_description', ''),
                'impact3_type': r.get('impact3_type', ''),
                'impact3_value': r.get('impact3_value', ''),
                'impact3_frequency': r.get('impact3_frequency', ''),
                'impact3_time_unit': r.get('impact3_time_unit', ''),
                'impact3_annual_value': r.get('impact3_annual_value', ''),
                'impact3_description': r.get('impact3_description', ''),
                'impact4_type': r.get('impact4_type', ''),
                'impact4_value': r.get('impact4_value', ''),
                'impact4_frequency': r.get('impact4_frequency', ''),
                'impact4_time_unit': r.get('impact4_time_unit', ''),
                'impact4_annual_value': r.get('impact4_annual_value', ''),
                'impact4_description': r.get('impact4_description', ''),
                'submitted_by': r.get('submitted_by', ''),
                'submitted_at': r.get('submitted_at', '')
            }
            writer.writerow(row)

    return ExportResponse(
        success=True,
        file_path=str(file_path),
        records_exported=len(responses),
        message=f"Exported {len(responses)} entries to {file_path}"
    )


# ============ ENTRIES IMPORT ============

@router.post("/responses/import", response_model=ImportResponse)
async def import_responses(
    request: FilePathRequest,
    mode: str = Query("append", regex="^(append|replace)$")
):
    """Import responses/entries from a CSV file on the server.

    mode: 'append' to add to existing, 'replace' to clear and reimport
    """
    file_path = Path(request.file_path)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    if not str(file_path).endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    # Read file content
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='latin-1') as f:
            text = f.read()

    # Build lookup dictionaries (name -> id)
    functions = {f['name'].lower(): f['id'] for f in crud.get_functions()}
    teams_by_func = {}  # {function_id: {team_name.lower(): team_id}}
    for t in crud.get_teams():
        fid = t['function_id']
        if fid not in teams_by_func:
            teams_by_func[fid] = {}
        teams_by_func[fid][t['name'].lower()] = t['id']

    capabilities = {c['name'].lower(): c['id'] for c in crud.get_capabilities()}
    tools = {t['name'].lower(): t['id'] for t in crud.get_tools()}

    # Parse CSV
    import io
    reader = csv.DictReader(io.StringIO(text))

    results = {
        'success': 0,
        'errors': [],
        'mode': mode
    }

    rows_to_import = []

    for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
        errors = []

        # Resolve function
        func_name = row.get('function', '').strip()
        if not func_name:
            errors.append("Missing function")
            function_id = None
        else:
            function_id = functions.get(func_name.lower())
            if not function_id:
                errors.append(f"Unknown function: {func_name}")

        # Resolve team (optional)
        team_name = row.get('team', '').strip()
        team_id = None
        if team_name and function_id:
            func_teams = teams_by_func.get(function_id, {})
            team_id = func_teams.get(team_name.lower())
            if not team_id:
                errors.append(f"Unknown team: {team_name} (for function {func_name})")

        # Resolve capability
        cap_name = row.get('capability', '').strip()
        if not cap_name:
            errors.append("Missing capability")
            capability_id = None
        else:
            capability_id = capabilities.get(cap_name.lower())
            if not capability_id:
                errors.append(f"Unknown capability: {cap_name}")

        # Validate method_type
        method_type = row.get('method_type', '').strip().lower()
        if method_type not in ['workflow', 'task', 'experiment']:
            errors.append(f"Invalid method_type: {method_type}")

        # Resolve tools
        tools_str = row.get('tools', '').strip()
        tool_ids = []
        if tools_str:
            for tool_name in [t.strip() for t in tools_str.split(',')]:
                if tool_name:
                    tid = tools.get(tool_name.lower())
                    if tid:
                        tool_ids.append(tid)
                    else:
                        errors.append(f"Unknown tool: {tool_name}")

        # Parse other_tools
        other_tools_str = row.get('other_tools', '').strip()
        other_tools_list = [t.strip() for t in other_tools_str.split(',') if t.strip()] if other_tools_str else []

        # Validate description
        description = row.get('description', '').strip()
        if not description:
            errors.append("Missing description")

        if errors:
            results['errors'].append({'row': row_num, 'errors': errors})
            continue

        # Build response data
        response_data = {
            'function_id': function_id,
            'team_id': team_id,
            'method_type': method_type,
            'capability_id': capability_id,
            'capability_other': row.get('capability_other', '').strip() or None,
            'description': description,
            'tools_used': json.dumps(tool_ids),
            'other_tools': json.dumps(other_tools_list) if other_tools_list else None,
            'submitted_by': row.get('submitted_by', '').strip() or None
        }

        # Parse impact fields
        for i in range(1, 5):
            prefix = f'impact{i}_'
            impact_type = row.get(f'{prefix}type', '').strip() or None
            if impact_type and impact_type not in ['cost_savings', 'time_savings', 'quality', 'new_capability']:
                impact_type = None

            response_data[f'{prefix}type'] = impact_type

            # Parse numeric values
            for field in ['value', 'annual_value']:
                val = row.get(f'{prefix}{field}', '').strip()
                if val:
                    try:
                        response_data[f'{prefix}{field}'] = float(val)
                    except ValueError:
                        response_data[f'{prefix}{field}'] = None
                else:
                    response_data[f'{prefix}{field}'] = None

            # Parse frequency
            freq = row.get(f'{prefix}frequency', '').strip() or None
            if freq and freq not in ['one_time', 'daily', 'weekly', 'monthly']:
                freq = None
            response_data[f'{prefix}frequency'] = freq

            response_data[f'{prefix}time_unit'] = row.get(f'{prefix}time_unit', '').strip() or None
            response_data[f'{prefix}description'] = row.get(f'{prefix}description', '').strip() or None

        rows_to_import.append(response_data)

    # If replace mode, clear existing responses
    if mode == 'replace' and rows_to_import:
        crud.clear_all_responses()

    # Import valid rows
    for row_data in rows_to_import:
        try:
            crud.create_response_from_dict(row_data)
            results['success'] += 1
        except Exception as e:
            results['errors'].append({'row': 'unknown', 'errors': [str(e)]})

    results['total_rows'] = len(rows_to_import) + len(results['errors'])

    return ImportResponse(**results)


# ============ CONFIG EXPORT ============

@router.post("/config/export/functions", response_model=ExportResponse)
async def export_functions(filename: Optional[str] = None):
    """Export functions to a CSV file on the server."""
    functions = crud.get_functions()

    if not filename:
        filename = f"functions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    file_path = EXPORT_DIR / filename

    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['name'])
        writer.writeheader()
        for func in functions:
            writer.writerow({'name': func['name']})

    return ExportResponse(
        success=True,
        file_path=str(file_path),
        records_exported=len(functions),
        message=f"Exported {len(functions)} functions to {file_path}"
    )


@router.post("/config/export/teams", response_model=ExportResponse)
async def export_teams(filename: Optional[str] = None):
    """Export teams to a CSV file on the server."""
    teams = crud.get_teams()
    functions = {f['id']: f['name'] for f in crud.get_functions()}

    if not filename:
        filename = f"teams_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    file_path = EXPORT_DIR / filename

    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['function', 'team'])
        writer.writeheader()
        for t in teams:
            writer.writerow({
                'function': functions.get(t['function_id'], ''),
                'team': t['name']
            })

    return ExportResponse(
        success=True,
        file_path=str(file_path),
        records_exported=len(teams),
        message=f"Exported {len(teams)} teams to {file_path}"
    )


@router.post("/config/export/tools", response_model=ExportResponse)
async def export_tools(filename: Optional[str] = None):
    """Export tools to a CSV file on the server."""
    tools = crud.get_tools()

    if not filename:
        filename = f"tools_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    file_path = EXPORT_DIR / filename

    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['name'])
        writer.writeheader()
        for tool in tools:
            writer.writerow({'name': tool['name']})

    return ExportResponse(
        success=True,
        file_path=str(file_path),
        records_exported=len(tools),
        message=f"Exported {len(tools)} tools to {file_path}"
    )


@router.post("/config/export/capabilities", response_model=ExportResponse)
async def export_capabilities(filename: Optional[str] = None):
    """Export capabilities to a CSV file on the server."""
    capabilities = crud.get_capabilities()

    if not filename:
        filename = f"capabilities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    file_path = EXPORT_DIR / filename

    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['name'])
        writer.writeheader()
        for cap in capabilities:
            writer.writerow({'name': cap['name']})

    return ExportResponse(
        success=True,
        file_path=str(file_path),
        records_exported=len(capabilities),
        message=f"Exported {len(capabilities)} capabilities to {file_path}"
    )


# ============ CONFIG IMPORT ============

@router.post("/config/import/functions", response_model=ImportResponse)
async def import_functions(
    request: FilePathRequest,
    mode: str = Query("merge", regex="^(merge|replace)$")
):
    """Import functions from a CSV file on the server."""
    file_path = Path(request.file_path)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    if not str(file_path).endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='latin-1') as f:
            text = f.read()

    import io
    reader = csv.DictReader(io.StringIO(text))

    existing = {f['name'].lower() for f in crud.get_functions()}

    results = {'success': 0, 'skipped': 0, 'errors': [], 'mode': mode}

    new_functions = []
    for row_num, row in enumerate(reader, start=2):
        name = row.get('name', '').strip()
        if not name:
            results['errors'].append({'row': row_num, 'error': 'Missing name'})
            continue

        if name.lower() in existing:
            results['skipped'] += 1
            continue

        new_functions.append(name)
        existing.add(name.lower())

    if mode == 'replace':
        crud.clear_functions()
        existing = set()
        for name in new_functions:
            crud.create_function_by_name(name)
            results['success'] += 1
    else:
        for name in new_functions:
            crud.create_function_by_name(name)
            results['success'] += 1

    results['total_rows'] = results['success'] + results['skipped'] + len(results['errors'])

    return ImportResponse(**results)


@router.post("/config/import/teams", response_model=ImportResponse)
async def import_teams(
    request: FilePathRequest,
    mode: str = Query("merge", regex="^(merge|replace)$")
):
    """Import teams from a CSV file on the server."""
    file_path = Path(request.file_path)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    if not str(file_path).endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='latin-1') as f:
            text = f.read()

    import io
    reader = csv.DictReader(io.StringIO(text))

    functions = {f['name'].lower(): f['id'] for f in crud.get_functions()}
    existing_teams = set()
    for t in crud.get_teams():
        existing_teams.add((t['function_id'], t['name'].lower()))

    results = {'success': 0, 'skipped': 0, 'errors': [], 'mode': mode}

    new_teams = []
    for row_num, row in enumerate(reader, start=2):
        func_name = row.get('function', '').strip()
        team_name = row.get('team', '').strip()

        if not func_name:
            results['errors'].append({'row': row_num, 'error': 'Missing function'})
            continue
        if not team_name:
            results['errors'].append({'row': row_num, 'error': 'Missing team'})
            continue

        func_id = functions.get(func_name.lower())
        if not func_id:
            results['errors'].append({'row': row_num, 'error': f'Unknown function: {func_name}'})
            continue

        if (func_id, team_name.lower()) in existing_teams:
            results['skipped'] += 1
            continue

        new_teams.append((func_id, team_name))
        existing_teams.add((func_id, team_name.lower()))

    if mode == 'replace':
        crud.clear_teams()
        existing_teams = set()

    for func_id, team_name in new_teams:
        crud.create_team_by_name(func_id, team_name)
        results['success'] += 1

    results['total_rows'] = results['success'] + results['skipped'] + len(results['errors'])

    return ImportResponse(**results)


@router.post("/config/import/tools", response_model=ImportResponse)
async def import_tools(
    request: FilePathRequest,
    mode: str = Query("merge", regex="^(merge|replace)$")
):
    """Import tools from a CSV file on the server."""
    file_path = Path(request.file_path)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    if not str(file_path).endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='latin-1') as f:
            text = f.read()

    import io
    reader = csv.DictReader(io.StringIO(text))

    existing = {t['name'].lower() for t in crud.get_tools()}

    results = {'success': 0, 'skipped': 0, 'errors': [], 'mode': mode}

    new_tools = []
    for row_num, row in enumerate(reader, start=2):
        name = row.get('name', '').strip()
        if not name:
            results['errors'].append({'row': row_num, 'error': 'Missing name'})
            continue

        if name.lower() in existing:
            results['skipped'] += 1
            continue

        new_tools.append(name)
        existing.add(name.lower())

    if mode == 'replace':
        crud.clear_tools()

    for name in new_tools:
        crud.create_tool_by_name(name)
        results['success'] += 1

    results['total_rows'] = results['success'] + results['skipped'] + len(results['errors'])

    return ImportResponse(**results)


@router.post("/config/import/capabilities", response_model=ImportResponse)
async def import_capabilities(
    request: FilePathRequest,
    mode: str = Query("merge", regex="^(merge|replace)$")
):
    """Import capabilities from a CSV file on the server."""
    file_path = Path(request.file_path)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    if not str(file_path).endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='latin-1') as f:
            text = f.read()

    import io
    reader = csv.DictReader(io.StringIO(text))

    existing = {c['name'].lower() for c in crud.get_capabilities()}

    results = {'success': 0, 'skipped': 0, 'errors': [], 'mode': mode}

    new_capabilities = []
    for row_num, row in enumerate(reader, start=2):
        name = row.get('name', '').strip()
        if not name:
            results['errors'].append({'row': row_num, 'error': 'Missing name'})
            continue

        if name.lower() in existing:
            results['skipped'] += 1
            continue

        new_capabilities.append(name)
        existing.add(name.lower())

    if mode == 'replace':
        crud.clear_capabilities()

    for name in new_capabilities:
        crud.create_capability_by_name(name)
        results['success'] += 1

    results['total_rows'] = results['success'] + results['skipped'] + len(results['errors'])

    return ImportResponse(**results)


# ============ LIST EXPORT FILES ============

@router.get("/exports/list")
async def list_export_files():
    """List all files in the exports directory."""
    files = []
    if EXPORT_DIR.exists():
        for f in sorted(EXPORT_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if f.is_file():
                stat = f.stat()
                files.append({
                    'name': f.name,
                    'path': str(f),
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
    return {'directory': str(EXPORT_DIR), 'files': files}
