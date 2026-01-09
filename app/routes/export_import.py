from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import Response
from typing import Optional, List
import json
from datetime import datetime

from .. import crud

router = APIRouter(prefix="/api", tags=["export-import"])


# ============ ENTRIES EXPORT ============

@router.get("/responses/export")
async def export_responses():
    """Export all responses/entries as JSON - browser download."""
    responses = crud.get_responses()

    # Get config for name lookups
    functions = {f['id']: f['name'] for f in crud.get_functions()}
    teams = {t['id']: t['name'] for t in crud.get_teams()}
    capabilities = {c['id']: c['name'] for c in crud.get_capabilities()}
    tools = {t['id']: t['name'] for t in crud.get_tools()}

    entries = []
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

        # Build impacts array
        impacts = []
        for i in range(1, 5):
            prefix = f'impact{i}_'
            impact_type = r.get(f'{prefix}type')
            if impact_type:
                impact = {'type': impact_type}
                if r.get(f'{prefix}value') is not None:
                    impact['value'] = r.get(f'{prefix}value')
                if r.get(f'{prefix}frequency'):
                    impact['frequency'] = r.get(f'{prefix}frequency')
                if r.get(f'{prefix}time_unit'):
                    impact['time_unit'] = r.get(f'{prefix}time_unit')
                if r.get(f'{prefix}annual_value') is not None:
                    impact['annual_value'] = r.get(f'{prefix}annual_value')
                if r.get(f'{prefix}description'):
                    impact['description'] = r.get(f'{prefix}description')
                impacts.append(impact)

        entry = {
            'id': r.get('id'),
            'function': functions.get(r.get('function_id'), ''),
            'team': teams.get(r.get('team_id')) if r.get('team_id') else None,
            'method_type': r.get('method_type', ''),
            'capability': capabilities.get(r.get('capability_id'), ''),
            'capability_other': r.get('capability_other') if r.get('capability_other') else None,
            'description': r.get('description', ''),
            'tools': tool_names,
            'other_tools': other_tools_list if other_tools_list else None,
            'impacts': impacts if impacts else None,
            'submitted_by': r.get('submitted_by') if r.get('submitted_by') else None,
            'submitted_at': r.get('submitted_at', '')
        }

        # Remove None values for cleaner output
        entry = {k: v for k, v in entry.items() if v is not None}
        entries.append(entry)

    output = json.dumps(entries, indent=2)
    filename = f"ai_usage_entries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    return Response(
        content=output,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ============ ENTRIES IMPORT ============

@router.post("/responses/import")
async def import_responses(
    file: UploadFile = File(...),
    mode: str = Query("append", pattern="^(append|replace)$")
):
    """Import responses/entries from uploaded JSON file.

    mode: 'append' to add to existing, 'replace' to clear and reimport
    """
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="File must be a JSON file")

    # Read file content
    content = await file.read()
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        text = content.decode('latin-1')

    try:
        entries = json.loads(text)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

    if not isinstance(entries, list):
        raise HTTPException(status_code=400, detail="JSON must be an array of entries")

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

    results = {
        'success': 0,
        'errors': [],
        'mode': mode
    }

    rows_to_import = []

    for row_num, entry in enumerate(entries, start=1):
        errors = []

        # Resolve function
        func_name = entry.get('function', '').strip() if entry.get('function') else ''
        if not func_name:
            errors.append("Missing function")
            function_id = None
        else:
            function_id = functions.get(func_name.lower())
            if not function_id:
                errors.append(f"Unknown function: {func_name}")

        # Resolve team (optional)
        team_name = entry.get('team', '').strip() if entry.get('team') else ''
        team_id = None
        if team_name and function_id:
            func_teams = teams_by_func.get(function_id, {})
            team_id = func_teams.get(team_name.lower())
            if not team_id:
                errors.append(f"Unknown team: {team_name} (for function {func_name})")

        # Resolve capability
        cap_name = entry.get('capability', '').strip() if entry.get('capability') else ''
        if not cap_name:
            errors.append("Missing capability")
            capability_id = None
        else:
            capability_id = capabilities.get(cap_name.lower())
            if not capability_id:
                errors.append(f"Unknown capability: {cap_name}")

        # Validate method_type
        method_type = entry.get('method_type', '').strip().lower() if entry.get('method_type') else ''
        if method_type not in ['workflow', 'task', 'experiment']:
            errors.append(f"Invalid method_type: {method_type}")

        # Resolve tools
        tool_list = entry.get('tools', [])
        if isinstance(tool_list, str):
            tool_list = [t.strip() for t in tool_list.split(',') if t.strip()]

        tool_ids = []
        if tool_list:
            for tool_name in tool_list:
                if tool_name:
                    tid = tools.get(tool_name.lower())
                    if tid:
                        tool_ids.append(tid)
                    else:
                        errors.append(f"Unknown tool: {tool_name}")

        # Parse other_tools
        other_tools_list = entry.get('other_tools', [])
        if isinstance(other_tools_list, str):
            other_tools_list = [t.strip() for t in other_tools_list.split(',') if t.strip()]

        # Validate description
        description = entry.get('description', '').strip() if entry.get('description') else ''
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
            'capability_other': entry.get('capability_other', '').strip() if entry.get('capability_other') else None,
            'description': description,
            'tools_used': json.dumps(tool_ids),
            'other_tools': json.dumps(other_tools_list) if other_tools_list else None,
            'submitted_by': entry.get('submitted_by', '').strip() if entry.get('submitted_by') else None
        }

        # Parse impacts array
        impacts = entry.get('impacts', [])
        for i, impact in enumerate(impacts[:4], start=1):  # Max 4 impacts
            prefix = f'impact{i}_'
            impact_type = impact.get('type', '').strip() if impact.get('type') else None
            if impact_type and impact_type not in ['cost_savings', 'time_savings', 'quality', 'new_capability']:
                impact_type = None

            response_data[f'{prefix}type'] = impact_type
            response_data[f'{prefix}value'] = impact.get('value')
            response_data[f'{prefix}frequency'] = impact.get('frequency')
            response_data[f'{prefix}time_unit'] = impact.get('time_unit')
            response_data[f'{prefix}annual_value'] = impact.get('annual_value')
            response_data[f'{prefix}description'] = impact.get('description')

        # Fill remaining impact slots with None
        for i in range(len(impacts) + 1, 5):
            prefix = f'impact{i}_'
            response_data[f'{prefix}type'] = None
            response_data[f'{prefix}value'] = None
            response_data[f'{prefix}frequency'] = None
            response_data[f'{prefix}time_unit'] = None
            response_data[f'{prefix}annual_value'] = None
            response_data[f'{prefix}description'] = None

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
    """Export functions as JSON - browser download."""
    functions = crud.get_functions()
    data = [{'name': f['name']} for f in functions]

    output = json.dumps(data, indent=2)
    filename = f"functions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    return Response(
        content=output,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/config/export/teams")
async def export_teams():
    """Export teams as JSON - browser download."""
    teams = crud.get_teams()
    functions = {f['id']: f['name'] for f in crud.get_functions()}

    data = [
        {'function': functions.get(t['function_id'], ''), 'team': t['name']}
        for t in teams
    ]

    output = json.dumps(data, indent=2)
    filename = f"teams_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    return Response(
        content=output,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/config/export/tools")
async def export_tools():
    """Export tools as JSON - browser download."""
    tools = crud.get_tools()
    data = [{'name': t['name']} for t in tools]

    output = json.dumps(data, indent=2)
    filename = f"tools_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    return Response(
        content=output,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/config/export/capabilities")
async def export_capabilities():
    """Export capabilities as JSON - browser download."""
    capabilities = crud.get_capabilities()
    data = [{'name': c['name']} for c in capabilities]

    output = json.dumps(data, indent=2)
    filename = f"capabilities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    return Response(
        content=output,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ============ CONFIG IMPORT ============

@router.post("/config/import/functions")
async def import_functions(
    file: UploadFile = File(...),
    mode: str = Query("merge", pattern="^(merge|replace)$")
):
    """Import functions from uploaded JSON file."""
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="File must be a JSON file")

    content = await file.read()
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        text = content.decode('latin-1')

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

    if not isinstance(data, list):
        raise HTTPException(status_code=400, detail="JSON must be an array")

    existing = {f['name'].lower() for f in crud.get_functions()}

    results = {'added': 0, 'skipped': 0, 'errors': [], 'mode': mode}

    new_functions = []
    for row_num, item in enumerate(data, start=1):
        name = item.get('name', '').strip() if isinstance(item, dict) else str(item).strip()
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
            results['added'] += 1
    else:
        for name in new_functions:
            crud.create_function_by_name(name)
            results['added'] += 1

    return results


@router.post("/config/import/teams")
async def import_teams(
    file: UploadFile = File(...),
    mode: str = Query("merge", pattern="^(merge|replace)$")
):
    """Import teams from uploaded JSON file."""
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="File must be a JSON file")

    content = await file.read()
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        text = content.decode('latin-1')

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

    if not isinstance(data, list):
        raise HTTPException(status_code=400, detail="JSON must be an array")

    functions = {f['name'].lower(): f['id'] for f in crud.get_functions()}
    existing_teams = set()
    for t in crud.get_teams():
        existing_teams.add((t['function_id'], t['name'].lower()))

    results = {'added': 0, 'skipped': 0, 'errors': [], 'mode': mode}

    new_teams = []
    for row_num, item in enumerate(data, start=1):
        func_name = item.get('function', '').strip() if item.get('function') else ''
        team_name = item.get('team', '').strip() if item.get('team') else ''

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
    mode: str = Query("merge", pattern="^(merge|replace)$")
):
    """Import tools from uploaded JSON file."""
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="File must be a JSON file")

    content = await file.read()
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        text = content.decode('latin-1')

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

    if not isinstance(data, list):
        raise HTTPException(status_code=400, detail="JSON must be an array")

    existing = {t['name'].lower() for t in crud.get_tools()}

    results = {'added': 0, 'skipped': 0, 'errors': [], 'mode': mode}

    new_tools = []
    for row_num, item in enumerate(data, start=1):
        name = item.get('name', '').strip() if isinstance(item, dict) else str(item).strip()
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
    mode: str = Query("merge", pattern="^(merge|replace)$")
):
    """Import capabilities from uploaded JSON file."""
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="File must be a JSON file")

    content = await file.read()
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        text = content.decode('latin-1')

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

    if not isinstance(data, list):
        raise HTTPException(status_code=400, detail="JSON must be an array")

    existing = {c['name'].lower() for c in crud.get_capabilities()}

    results = {'added': 0, 'skipped': 0, 'errors': [], 'mode': mode}

    new_capabilities = []
    for row_num, item in enumerate(data, start=1):
        name = item.get('name', '').strip() if isinstance(item, dict) else str(item).strip()
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
