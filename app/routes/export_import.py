from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional, List
import csv
import io
import json
from datetime import datetime

from .. import crud

router = APIRouter(prefix="/api", tags=["export-import"])


# ============ ENTRIES EXPORT ============

@router.get("/responses/export")
async def export_responses():
    """Export all responses/entries as CSV."""
    # Get all responses with details
    responses = crud.get_responses()

    # Get config for name lookups
    functions = {f['id']: f['name'] for f in crud.get_functions()}
    teams = {t['id']: t['name'] for t in crud.get_teams()}
    capabilities = {c['id']: c['name'] for c in crud.get_capabilities()}
    tools = {t['id']: t['name'] for t in crud.get_tools()}

    # Create CSV in memory
    output = io.StringIO()

    fieldnames = [
        'id', 'function', 'team', 'method_type', 'capability', 'capability_other',
        'description', 'tools', 'other_tools',
        'impact1_type', 'impact1_value', 'impact1_frequency', 'impact1_time_unit', 'impact1_annual_value', 'impact1_description',
        'impact2_type', 'impact2_value', 'impact2_frequency', 'impact2_time_unit', 'impact2_annual_value', 'impact2_description',
        'impact3_type', 'impact3_value', 'impact3_frequency', 'impact3_time_unit', 'impact3_annual_value', 'impact3_description',
        'impact4_type', 'impact4_value', 'impact4_frequency', 'impact4_time_unit', 'impact4_annual_value', 'impact4_description',
        'submitted_by', 'submitted_at'
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames)
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

    output.seek(0)

    filename = f"ai_usage_entries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ============ ENTRIES IMPORT ============

@router.post("/responses/import")
async def import_responses(
    file: UploadFile = File(...),
    mode: str = Query("append", regex="^(append|replace)$")
):
    """Import responses/entries from CSV.

    mode: 'append' to add to existing, 'replace' to clear and reimport
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    # Read file content
    content = await file.read()
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        text = content.decode('latin-1')

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

    return results


# ============ CONFIG EXPORT ============

@router.get("/config/export/functions")
async def export_functions():
    """Export functions as CSV."""
    functions = crud.get_functions()

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=['name'])
    writer.writeheader()

    for f in functions:
        writer.writerow({'name': f['name']})

    output.seek(0)
    filename = f"functions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/config/export/teams")
async def export_teams():
    """Export teams as CSV."""
    teams = crud.get_teams()
    functions = {f['id']: f['name'] for f in crud.get_functions()}

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=['function', 'team'])
    writer.writeheader()

    for t in teams:
        writer.writerow({
            'function': functions.get(t['function_id'], ''),
            'team': t['name']
        })

    output.seek(0)
    filename = f"teams_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/config/export/tools")
async def export_tools():
    """Export tools as CSV."""
    tools = crud.get_tools()

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=['name'])
    writer.writeheader()

    for t in tools:
        writer.writerow({'name': t['name']})

    output.seek(0)
    filename = f"tools_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/config/export/capabilities")
async def export_capabilities():
    """Export capabilities as CSV."""
    capabilities = crud.get_capabilities()

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=['name'])
    writer.writeheader()

    for c in capabilities:
        writer.writerow({'name': c['name']})

    output.seek(0)
    filename = f"capabilities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ============ CONFIG IMPORT ============

@router.post("/config/import/functions")
async def import_functions(
    file: UploadFile = File(...),
    mode: str = Query("merge", regex="^(merge|replace)$")
):
    """Import functions from CSV."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    content = await file.read()
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        text = content.decode('latin-1')

    reader = csv.DictReader(io.StringIO(text))

    existing = {f['name'].lower() for f in crud.get_functions()}

    results = {'added': 0, 'skipped': 0, 'errors': [], 'mode': mode}

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
        # Clear and reimport (this is destructive!)
        crud.clear_functions()
        existing = set()
        for name in new_functions:
            crud.create_function_by_name(name)
            results['added'] += 1
    else:
        for name in new_functions:
            crud.create_function_by_name(name)
            results['added'] += 1

    return results


@router.post("/config/import/teams")
async def import_teams(
    file: UploadFile = File(...),
    mode: str = Query("merge", regex="^(merge|replace)$")
):
    """Import teams from CSV."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    content = await file.read()
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        text = content.decode('latin-1')

    reader = csv.DictReader(io.StringIO(text))

    functions = {f['name'].lower(): f['id'] for f in crud.get_functions()}
    existing_teams = set()
    for t in crud.get_teams():
        existing_teams.add((t['function_id'], t['name'].lower()))

    results = {'added': 0, 'skipped': 0, 'errors': [], 'mode': mode}

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
        results['added'] += 1

    return results


@router.post("/config/import/tools")
async def import_tools(
    file: UploadFile = File(...),
    mode: str = Query("merge", regex="^(merge|replace)$")
):
    """Import tools from CSV."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    content = await file.read()
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        text = content.decode('latin-1')

    reader = csv.DictReader(io.StringIO(text))

    existing = {t['name'].lower() for t in crud.get_tools()}

    results = {'added': 0, 'skipped': 0, 'errors': [], 'mode': mode}

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
        results['added'] += 1

    return results


@router.post("/config/import/capabilities")
async def import_capabilities(
    file: UploadFile = File(...),
    mode: str = Query("merge", regex="^(merge|replace)$")
):
    """Import capabilities from CSV."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    content = await file.read()
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        text = content.decode('latin-1')

    reader = csv.DictReader(io.StringIO(text))

    existing = {c['name'].lower() for c in crud.get_capabilities()}

    results = {'added': 0, 'skipped': 0, 'errors': [], 'mode': mode}

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
        results['added'] += 1

    return results
