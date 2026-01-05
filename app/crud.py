import sqlite3
from typing import List, Optional, Dict, Any
from datetime import datetime

from .database import get_db_connection
from .models import (
    FunctionCreate, TeamCreate, ToolCreate, CapabilityCreate,
    ResponseCreate, ResponseUpdate, DashboardSummary, FunctionBreakdown, TeamBreakdown
)


def dict_from_row(row: sqlite3.Row) -> dict:
    """Convert sqlite3.Row to dictionary."""
    return dict(zip(row.keys(), row))


# ============ Functions CRUD ============

def get_functions(active_only: bool = True) -> List[dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    if active_only:
        cursor.execute("SELECT * FROM functions WHERE active = 1 ORDER BY name")
    else:
        cursor.execute("SELECT * FROM functions ORDER BY name")
    rows = cursor.fetchall()
    conn.close()
    return [dict_from_row(row) for row in rows]


def get_function(function_id: int) -> Optional[dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM functions WHERE id = ?", (function_id,))
    row = cursor.fetchone()
    conn.close()
    return dict_from_row(row) if row else None


def create_function(func: FunctionCreate) -> dict:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO functions (name) VALUES (?)", (func.name,))
    conn.commit()
    function_id = cursor.lastrowid
    conn.close()
    return get_function(function_id)


# ============ Teams CRUD ============

def get_teams(function_id: Optional[int] = None, active_only: bool = True) -> List[dict]:
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT t.*, f.name as function_name
        FROM teams t
        JOIN functions f ON t.function_id = f.id
    """
    conditions = []
    params = []

    if active_only:
        conditions.append("t.active = 1")
    if function_id:
        conditions.append("t.function_id = ?")
        params.append(function_id)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY f.name, t.name"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict_from_row(row) for row in rows]


def get_team(team_id: int) -> Optional[dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.*, f.name as function_name
        FROM teams t
        JOIN functions f ON t.function_id = f.id
        WHERE t.id = ?
    """, (team_id,))
    row = cursor.fetchone()
    conn.close()
    return dict_from_row(row) if row else None


def create_team(team: TeamCreate) -> dict:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO teams (function_id, name) VALUES (?, ?)",
        (team.function_id, team.name)
    )
    conn.commit()
    team_id = cursor.lastrowid
    conn.close()
    return get_team(team_id)


# ============ Tools CRUD ============

def get_tools(active_only: bool = True) -> List[dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    if active_only:
        cursor.execute("SELECT * FROM tools WHERE active = 1 ORDER BY name")
    else:
        cursor.execute("SELECT * FROM tools ORDER BY name")
    rows = cursor.fetchall()
    conn.close()
    return [dict_from_row(row) for row in rows]


def get_tool(tool_id: int) -> Optional[dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tools WHERE id = ?", (tool_id,))
    row = cursor.fetchone()
    conn.close()
    return dict_from_row(row) if row else None


def create_tool(tool: ToolCreate) -> dict:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tools (name) VALUES (?)", (tool.name,))
    conn.commit()
    tool_id = cursor.lastrowid
    conn.close()
    return get_tool(tool_id)


# ============ Capabilities CRUD ============

def get_capabilities(active_only: bool = True) -> List[dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    if active_only:
        cursor.execute("SELECT * FROM capabilities WHERE active = 1 ORDER BY name")
    else:
        cursor.execute("SELECT * FROM capabilities ORDER BY name")
    rows = cursor.fetchall()
    conn.close()
    return [dict_from_row(row) for row in rows]


def get_capability(capability_id: int) -> Optional[dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM capabilities WHERE id = ?", (capability_id,))
    row = cursor.fetchone()
    conn.close()
    return dict_from_row(row) if row else None


def create_capability(cap: CapabilityCreate) -> dict:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO capabilities (name) VALUES (?)", (cap.name,))
    conn.commit()
    cap_id = cursor.lastrowid
    conn.close()
    return get_capability(cap_id)


# ============ Config Update/Delete Operations ============

def update_function(function_id: int, name: str) -> Optional[dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE functions SET name = ? WHERE id = ?", (name, function_id))
    conn.commit()
    conn.close()
    return get_function(function_id)


def delete_function(function_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    # Check if function has teams or responses
    cursor.execute("SELECT COUNT(*) FROM teams WHERE function_id = ?", (function_id,))
    if cursor.fetchone()[0] > 0:
        conn.close()
        return False
    cursor.execute("SELECT COUNT(*) FROM responses WHERE function_id = ?", (function_id,))
    if cursor.fetchone()[0] > 0:
        conn.close()
        return False
    cursor.execute("DELETE FROM functions WHERE id = ?", (function_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def update_team(team_id: int, name: str, function_id: int) -> Optional[dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE teams SET name = ?, function_id = ? WHERE id = ?", (name, function_id, team_id))
    conn.commit()
    conn.close()
    return get_team(team_id)


def delete_team(team_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM responses WHERE team_id = ?", (team_id,))
    if cursor.fetchone()[0] > 0:
        conn.close()
        return False
    cursor.execute("DELETE FROM teams WHERE id = ?", (team_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def update_tool(tool_id: int, name: str) -> Optional[dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tools SET name = ? WHERE id = ?", (name, tool_id))
    conn.commit()
    conn.close()
    return get_tool(tool_id)


def delete_tool(tool_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tools WHERE id = ?", (tool_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def update_capability(capability_id: int, name: str) -> Optional[dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE capabilities SET name = ? WHERE id = ?", (name, capability_id))
    conn.commit()
    conn.close()
    return get_capability(capability_id)


def delete_capability(capability_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM responses WHERE capability_id = ?", (capability_id,))
    if cursor.fetchone()[0] > 0:
        conn.close()
        return False
    cursor.execute("DELETE FROM capabilities WHERE id = ?", (capability_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


# ============ Responses CRUD ============

def get_responses(
    function_id: Optional[int] = None,
    team_id: Optional[int] = None,
    method_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[dict]:
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT r.*,
               f.name as function_name,
               t.name as team_name,
               c.name as capability_name
        FROM responses r
        JOIN functions f ON r.function_id = f.id
        LEFT JOIN teams t ON r.team_id = t.id
        JOIN capabilities c ON r.capability_id = c.id
    """
    conditions = []
    params = []

    if function_id:
        conditions.append("r.function_id = ?")
        params.append(function_id)
    if team_id:
        conditions.append("r.team_id = ?")
        params.append(team_id)
    if method_type:
        conditions.append("r.method_type = ?")
        params.append(method_type)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY r.submitted_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict_from_row(row) for row in rows]


def get_response(response_id: int) -> Optional[dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.*,
               f.name as function_name,
               t.name as team_name,
               c.name as capability_name
        FROM responses r
        JOIN functions f ON r.function_id = f.id
        LEFT JOIN teams t ON r.team_id = t.id
        JOIN capabilities c ON r.capability_id = c.id
        WHERE r.id = ?
    """, (response_id,))
    row = cursor.fetchone()
    conn.close()
    return dict_from_row(row) if row else None


def create_response(response: ResponseCreate) -> dict:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO responses (
            function_id, team_id, method_type, capability_id, capability_other,
            description, tools_used, other_tools,
            impact1_type, impact1_value, impact1_frequency, impact1_time_unit, impact1_annual_value, impact1_description,
            impact2_type, impact2_value, impact2_frequency, impact2_time_unit, impact2_annual_value, impact2_description,
            impact3_type, impact3_value, impact3_frequency, impact3_time_unit, impact3_annual_value, impact3_description,
            impact4_type, impact4_value, impact4_frequency, impact4_time_unit, impact4_annual_value, impact4_description,
            submitted_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        response.function_id, response.team_id, response.method_type.value,
        response.capability_id, response.capability_other,
        response.description, response.tools_used, response.other_tools,
        response.impact1_type.value if response.impact1_type else None,
        response.impact1_value, response.impact1_frequency.value if response.impact1_frequency else None,
        response.impact1_time_unit, response.impact1_annual_value, response.impact1_description,
        response.impact2_type.value if response.impact2_type else None,
        response.impact2_value, response.impact2_frequency.value if response.impact2_frequency else None,
        response.impact2_time_unit, response.impact2_annual_value, response.impact2_description,
        response.impact3_type.value if response.impact3_type else None,
        response.impact3_value, response.impact3_frequency.value if response.impact3_frequency else None,
        response.impact3_time_unit, response.impact3_annual_value, response.impact3_description,
        response.impact4_type.value if response.impact4_type else None,
        response.impact4_value, response.impact4_frequency.value if response.impact4_frequency else None,
        response.impact4_time_unit, response.impact4_annual_value, response.impact4_description,
        response.submitted_by
    ))

    conn.commit()
    response_id = cursor.lastrowid
    conn.close()
    return get_response(response_id)


def update_response(response_id: int, response: ResponseUpdate) -> Optional[dict]:
    conn = get_db_connection()
    cursor = conn.cursor()

    # Build dynamic update query
    update_fields = []
    params = []

    update_data = response.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            # Handle enum values
            if hasattr(value, 'value'):
                value = value.value
            update_fields.append(f"{field} = ?")
            params.append(value)

    if not update_fields:
        conn.close()
        return get_response(response_id)

    update_fields.append("updated_at = ?")
    params.append(datetime.now().isoformat())
    params.append(response_id)

    query = f"UPDATE responses SET {', '.join(update_fields)} WHERE id = ?"
    cursor.execute(query, params)
    conn.commit()
    conn.close()

    return get_response(response_id)


def delete_response(response_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM responses WHERE id = ?", (response_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


# ============ Dashboard Aggregations ============

def get_dashboard_summary() -> dict:
    conn = get_db_connection()
    cursor = conn.cursor()

    # Total counts by method type
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN method_type = 'workflow' THEN 1 ELSE 0 END) as workflows,
            SUM(CASE WHEN method_type = 'task' THEN 1 ELSE 0 END) as tasks,
            SUM(CASE WHEN method_type = 'experiment' THEN 1 ELSE 0 END) as experiments
        FROM responses
    """)
    counts = cursor.fetchone()

    # Aggregate impacts across all 4 impact fields
    cursor.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN impact1_type = 'cost_savings' THEN impact1_annual_value ELSE 0 END), 0) +
            COALESCE(SUM(CASE WHEN impact2_type = 'cost_savings' THEN impact2_annual_value ELSE 0 END), 0) +
            COALESCE(SUM(CASE WHEN impact3_type = 'cost_savings' THEN impact3_annual_value ELSE 0 END), 0) +
            COALESCE(SUM(CASE WHEN impact4_type = 'cost_savings' THEN impact4_annual_value ELSE 0 END), 0) as cost_savings,

            COALESCE(SUM(CASE WHEN impact1_type = 'time_savings' THEN impact1_annual_value ELSE 0 END), 0) +
            COALESCE(SUM(CASE WHEN impact2_type = 'time_savings' THEN impact2_annual_value ELSE 0 END), 0) +
            COALESCE(SUM(CASE WHEN impact3_type = 'time_savings' THEN impact3_annual_value ELSE 0 END), 0) +
            COALESCE(SUM(CASE WHEN impact4_type = 'time_savings' THEN impact4_annual_value ELSE 0 END), 0) as time_savings,

            (SELECT COUNT(*) FROM responses WHERE impact1_type = 'quality' OR impact2_type = 'quality' OR impact3_type = 'quality' OR impact4_type = 'quality') as quality_count,

            (SELECT COUNT(*) FROM responses WHERE impact1_type = 'new_capability' OR impact2_type = 'new_capability' OR impact3_type = 'new_capability' OR impact4_type = 'new_capability') as new_capability_count
        FROM responses
    """)
    impacts = cursor.fetchone()

    conn.close()

    return {
        "total_methods": counts["total"] or 0,
        "total_workflows": counts["workflows"] or 0,
        "total_tasks": counts["tasks"] or 0,
        "total_experiments": counts["experiments"] or 0,
        "total_cost_savings": impacts["cost_savings"] or 0.0,
        "total_time_savings": impacts["time_savings"] or 0.0,
        "quality_count": impacts["quality_count"] or 0,
        "new_capability_count": impacts["new_capability_count"] or 0
    }


def get_dashboard_by_function() -> List[dict]:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            f.id as function_id,
            f.name as function_name,
            COUNT(r.id) as method_count,
            SUM(CASE WHEN r.method_type = 'workflow' THEN 1 ELSE 0 END) as workflow_count,
            SUM(CASE WHEN r.method_type = 'task' THEN 1 ELSE 0 END) as task_count,
            SUM(CASE WHEN r.method_type = 'experiment' THEN 1 ELSE 0 END) as experiment_count,
            COALESCE(SUM(CASE WHEN r.impact1_type = 'cost_savings' THEN r.impact1_annual_value ELSE 0 END), 0) +
            COALESCE(SUM(CASE WHEN r.impact2_type = 'cost_savings' THEN r.impact2_annual_value ELSE 0 END), 0) +
            COALESCE(SUM(CASE WHEN r.impact3_type = 'cost_savings' THEN r.impact3_annual_value ELSE 0 END), 0) +
            COALESCE(SUM(CASE WHEN r.impact4_type = 'cost_savings' THEN r.impact4_annual_value ELSE 0 END), 0) as cost_savings,
            COALESCE(SUM(CASE WHEN r.impact1_type = 'time_savings' THEN r.impact1_annual_value ELSE 0 END), 0) +
            COALESCE(SUM(CASE WHEN r.impact2_type = 'time_savings' THEN r.impact2_annual_value ELSE 0 END), 0) +
            COALESCE(SUM(CASE WHEN r.impact3_type = 'time_savings' THEN r.impact3_annual_value ELSE 0 END), 0) +
            COALESCE(SUM(CASE WHEN r.impact4_type = 'time_savings' THEN r.impact4_annual_value ELSE 0 END), 0) as time_savings,
            SUM(CASE WHEN r.impact1_type = 'quality' OR r.impact2_type = 'quality' OR r.impact3_type = 'quality' OR r.impact4_type = 'quality' THEN 1 ELSE 0 END) as quality_count,
            SUM(CASE WHEN r.impact1_type = 'new_capability' OR r.impact2_type = 'new_capability' OR r.impact3_type = 'new_capability' OR r.impact4_type = 'new_capability' THEN 1 ELSE 0 END) as new_capability_count
        FROM functions f
        LEFT JOIN responses r ON f.id = r.function_id
        WHERE f.active = 1
        GROUP BY f.id, f.name
        ORDER BY method_count DESC
    """)

    rows = cursor.fetchall()
    conn.close()
    return [dict_from_row(row) for row in rows]


def get_dashboard_by_team() -> List[dict]:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            t.id as team_id,
            t.name as team_name,
            f.id as function_id,
            f.name as function_name,
            COUNT(r.id) as method_count,
            COALESCE(SUM(CASE WHEN r.impact1_type = 'cost_savings' THEN r.impact1_annual_value ELSE 0 END), 0) +
            COALESCE(SUM(CASE WHEN r.impact2_type = 'cost_savings' THEN r.impact2_annual_value ELSE 0 END), 0) +
            COALESCE(SUM(CASE WHEN r.impact3_type = 'cost_savings' THEN r.impact3_annual_value ELSE 0 END), 0) +
            COALESCE(SUM(CASE WHEN r.impact4_type = 'cost_savings' THEN r.impact4_annual_value ELSE 0 END), 0) as cost_savings,
            COALESCE(SUM(CASE WHEN r.impact1_type = 'time_savings' THEN r.impact1_annual_value ELSE 0 END), 0) +
            COALESCE(SUM(CASE WHEN r.impact2_type = 'time_savings' THEN r.impact2_annual_value ELSE 0 END), 0) +
            COALESCE(SUM(CASE WHEN r.impact3_type = 'time_savings' THEN r.impact3_annual_value ELSE 0 END), 0) +
            COALESCE(SUM(CASE WHEN r.impact4_type = 'time_savings' THEN r.impact4_annual_value ELSE 0 END), 0) as time_savings
        FROM teams t
        JOIN functions f ON t.function_id = f.id
        LEFT JOIN responses r ON t.id = r.team_id
        WHERE t.active = 1
        GROUP BY t.id, t.name, f.id, f.name
        ORDER BY f.name, method_count DESC
    """)

    rows = cursor.fetchall()
    conn.close()
    return [dict_from_row(row) for row in rows]


# ============ Config Bulk Operations ============

def get_dashboard_impact_types() -> List[dict]:
    """Get count of methods by impact type."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Count each impact type across all 4 impact fields
    cursor.execute("""
        SELECT
            'Cost Savings' as type,
            (SELECT COUNT(DISTINCT id) FROM responses WHERE
                impact1_type = 'cost_savings' OR impact2_type = 'cost_savings' OR
                impact3_type = 'cost_savings' OR impact4_type = 'cost_savings') as count
        UNION ALL
        SELECT
            'Time Savings' as type,
            (SELECT COUNT(DISTINCT id) FROM responses WHERE
                impact1_type = 'time_savings' OR impact2_type = 'time_savings' OR
                impact3_type = 'time_savings' OR impact4_type = 'time_savings') as count
        UNION ALL
        SELECT
            'Quality Improvement' as type,
            (SELECT COUNT(DISTINCT id) FROM responses WHERE
                impact1_type = 'quality' OR impact2_type = 'quality' OR
                impact3_type = 'quality' OR impact4_type = 'quality') as count
        UNION ALL
        SELECT
            'New Capability' as type,
            (SELECT COUNT(DISTINCT id) FROM responses WHERE
                impact1_type = 'new_capability' OR impact2_type = 'new_capability' OR
                impact3_type = 'new_capability' OR impact4_type = 'new_capability') as count
    """)

    rows = cursor.fetchall()
    conn.close()
    return [dict_from_row(row) for row in rows]


def get_dashboard_tools_used() -> List[dict]:
    """Get count of methods by tool used."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get all responses with their tools_used and other_tools
    cursor.execute("SELECT tools_used, other_tools FROM responses")
    rows = cursor.fetchall()

    # Get tool names mapping
    cursor.execute("SELECT id, name FROM tools WHERE active = 1")
    tools = {str(row['id']): row['name'] for row in cursor.fetchall()}

    conn.close()

    # Count tool usage
    import json
    tool_counts = {}

    for row in rows:
        tools_used = row['tools_used']
        other_tools = row['other_tools']

        if tools_used:
            try:
                tool_ids = json.loads(tools_used)
                for tool_id in tool_ids:
                    tool_name = tools.get(str(tool_id), 'Unknown')
                    # Check if this is "Other" tool
                    if tool_name.lower() == 'other' and other_tools:
                        try:
                            other_names = json.loads(other_tools)
                            for other_name in other_names:
                                tool_counts[other_name] = tool_counts.get(other_name, 0) + 1
                        except:
                            tool_counts['Other'] = tool_counts.get('Other', 0) + 1
                    else:
                        tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
            except:
                pass

    # Convert to list sorted by count
    result = [{'tool': name, 'count': count} for name, count in tool_counts.items()]
    result.sort(key=lambda x: x['count'], reverse=True)
    return result


def get_dashboard_capabilities() -> List[dict]:
    """Get count of methods by capability."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT c.name as capability, COUNT(r.id) as count
        FROM capabilities c
        LEFT JOIN responses r ON c.id = r.capability_id
        WHERE c.active = 1
        GROUP BY c.id, c.name
        HAVING COUNT(r.id) > 0
        ORDER BY count DESC
    """)

    rows = cursor.fetchall()
    conn.close()
    return [dict_from_row(row) for row in rows]


def get_dashboard_by_category() -> dict:
    """Get detailed breakdown by method type category (workflow, task, experiment)."""
    conn = get_db_connection()
    cursor = conn.cursor()

    result = {}
    for method_type in ['workflow', 'task', 'experiment']:
        cursor.execute("""
            SELECT
                COUNT(*) as count,
                COALESCE(SUM(CASE WHEN impact1_type = 'cost_savings' THEN impact1_annual_value ELSE 0 END), 0) +
                COALESCE(SUM(CASE WHEN impact2_type = 'cost_savings' THEN impact2_annual_value ELSE 0 END), 0) +
                COALESCE(SUM(CASE WHEN impact3_type = 'cost_savings' THEN impact3_annual_value ELSE 0 END), 0) +
                COALESCE(SUM(CASE WHEN impact4_type = 'cost_savings' THEN impact4_annual_value ELSE 0 END), 0) as cost_savings,
                COALESCE(SUM(CASE WHEN impact1_type = 'time_savings' THEN impact1_annual_value ELSE 0 END), 0) +
                COALESCE(SUM(CASE WHEN impact2_type = 'time_savings' THEN impact2_annual_value ELSE 0 END), 0) +
                COALESCE(SUM(CASE WHEN impact3_type = 'time_savings' THEN impact3_annual_value ELSE 0 END), 0) +
                COALESCE(SUM(CASE WHEN impact4_type = 'time_savings' THEN impact4_annual_value ELSE 0 END), 0) as time_savings,
                (SELECT COUNT(DISTINCT id) FROM responses WHERE method_type = ? AND
                    (impact1_type = 'cost_savings' OR impact2_type = 'cost_savings' OR
                     impact3_type = 'cost_savings' OR impact4_type = 'cost_savings')) as cost_savings_count,
                (SELECT COUNT(DISTINCT id) FROM responses WHERE method_type = ? AND
                    (impact1_type = 'time_savings' OR impact2_type = 'time_savings' OR
                     impact3_type = 'time_savings' OR impact4_type = 'time_savings')) as time_savings_count,
                (SELECT COUNT(DISTINCT id) FROM responses WHERE method_type = ? AND
                    (impact1_type = 'quality' OR impact2_type = 'quality' OR
                     impact3_type = 'quality' OR impact4_type = 'quality')) as quality_count,
                (SELECT COUNT(DISTINCT id) FROM responses WHERE method_type = ? AND
                    (impact1_type = 'new_capability' OR impact2_type = 'new_capability' OR
                     impact3_type = 'new_capability' OR impact4_type = 'new_capability')) as new_capability_count
            FROM responses
            WHERE method_type = ?
        """, (method_type, method_type, method_type, method_type, method_type))

        row = cursor.fetchone()
        result[method_type] = {
            'count': row['count'] or 0,
            'cost_savings': row['cost_savings'] or 0,
            'time_savings': row['time_savings'] or 0,
            'impact_breakdown': {
                'cost_savings': row['cost_savings_count'] or 0,
                'time_savings': row['time_savings_count'] or 0,
                'quality': row['quality_count'] or 0,
                'new_capability': row['new_capability_count'] or 0
            }
        }

    conn.close()
    return result


def get_dashboard_by_function_with_teams() -> List[dict]:
    """Get function breakdown including functions without teams (aggregate data)."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get function data including responses without teams
    cursor.execute("""
        SELECT
            f.id as function_id,
            f.name as function_name,
            COUNT(r.id) as method_count,
            SUM(CASE WHEN r.method_type = 'workflow' THEN 1 ELSE 0 END) as workflow_count,
            SUM(CASE WHEN r.method_type = 'task' THEN 1 ELSE 0 END) as task_count,
            SUM(CASE WHEN r.method_type = 'experiment' THEN 1 ELSE 0 END) as experiment_count,
            COALESCE(SUM(CASE WHEN r.impact1_type = 'cost_savings' THEN r.impact1_annual_value ELSE 0 END), 0) +
            COALESCE(SUM(CASE WHEN r.impact2_type = 'cost_savings' THEN r.impact2_annual_value ELSE 0 END), 0) +
            COALESCE(SUM(CASE WHEN r.impact3_type = 'cost_savings' THEN r.impact3_annual_value ELSE 0 END), 0) +
            COALESCE(SUM(CASE WHEN r.impact4_type = 'cost_savings' THEN r.impact4_annual_value ELSE 0 END), 0) as cost_savings,
            COALESCE(SUM(CASE WHEN r.impact1_type = 'time_savings' THEN r.impact1_annual_value ELSE 0 END), 0) +
            COALESCE(SUM(CASE WHEN r.impact2_type = 'time_savings' THEN r.impact2_annual_value ELSE 0 END), 0) +
            COALESCE(SUM(CASE WHEN r.impact3_type = 'time_savings' THEN r.impact3_annual_value ELSE 0 END), 0) +
            COALESCE(SUM(CASE WHEN r.impact4_type = 'time_savings' THEN r.impact4_annual_value ELSE 0 END), 0) as time_savings,
            SUM(CASE WHEN r.impact1_type = 'quality' OR r.impact2_type = 'quality' OR r.impact3_type = 'quality' OR r.impact4_type = 'quality' THEN 1 ELSE 0 END) as quality_count,
            SUM(CASE WHEN r.impact1_type = 'new_capability' OR r.impact2_type = 'new_capability' OR r.impact3_type = 'new_capability' OR r.impact4_type = 'new_capability' THEN 1 ELSE 0 END) as new_capability_count
        FROM functions f
        LEFT JOIN responses r ON f.id = r.function_id
        WHERE f.active = 1
        GROUP BY f.id, f.name
        ORDER BY method_count DESC
    """)

    functions_data = [dict_from_row(row) for row in cursor.fetchall()]

    # For each function, get team breakdown if teams exist
    for func in functions_data:
        # Check if function has teams
        cursor.execute("SELECT COUNT(*) as cnt FROM teams WHERE function_id = ? AND active = 1", (func['function_id'],))
        has_teams = cursor.fetchone()['cnt'] > 0

        if has_teams:
            # Get team breakdown
            cursor.execute("""
                SELECT
                    t.id as team_id,
                    t.name as team_name,
                    COUNT(r.id) as method_count,
                    SUM(CASE WHEN r.method_type = 'workflow' THEN 1 ELSE 0 END) as workflow_count,
                    SUM(CASE WHEN r.method_type = 'task' THEN 1 ELSE 0 END) as task_count,
                    SUM(CASE WHEN r.method_type = 'experiment' THEN 1 ELSE 0 END) as experiment_count,
                    COALESCE(SUM(CASE WHEN r.impact1_type = 'cost_savings' THEN r.impact1_annual_value ELSE 0 END), 0) +
                    COALESCE(SUM(CASE WHEN r.impact2_type = 'cost_savings' THEN r.impact2_annual_value ELSE 0 END), 0) +
                    COALESCE(SUM(CASE WHEN r.impact3_type = 'cost_savings' THEN r.impact3_annual_value ELSE 0 END), 0) +
                    COALESCE(SUM(CASE WHEN r.impact4_type = 'cost_savings' THEN r.impact4_annual_value ELSE 0 END), 0) as cost_savings,
                    COALESCE(SUM(CASE WHEN r.impact1_type = 'time_savings' THEN r.impact1_annual_value ELSE 0 END), 0) +
                    COALESCE(SUM(CASE WHEN r.impact2_type = 'time_savings' THEN r.impact2_annual_value ELSE 0 END), 0) +
                    COALESCE(SUM(CASE WHEN r.impact3_type = 'time_savings' THEN r.impact3_annual_value ELSE 0 END), 0) +
                    COALESCE(SUM(CASE WHEN r.impact4_type = 'time_savings' THEN r.impact4_annual_value ELSE 0 END), 0) as time_savings
                FROM teams t
                LEFT JOIN responses r ON t.id = r.team_id AND r.function_id = ?
                WHERE t.function_id = ? AND t.active = 1
                GROUP BY t.id, t.name
                ORDER BY method_count DESC
            """, (func['function_id'], func['function_id']))
            func['teams'] = [dict_from_row(row) for row in cursor.fetchall()]
        else:
            # Function has no teams - include it as its own "team" if it has responses
            func['teams'] = []
            func['has_no_teams'] = True

    conn.close()
    return functions_data


def clear_and_reload_config(functions: List[str], teams: Dict[str, List[str]],
                            tools: List[str], capabilities: List[tuple]):
    """Clear existing config and reload from Excel data."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Clear existing data (but preserve responses by keeping referenced items)
    # For safety, we'll just add new items and not delete existing ones with responses

    # Add functions
    for func_name in functions:
        cursor.execute("INSERT OR IGNORE INTO functions (name) VALUES (?)", (func_name,))

    # Add teams
    for func_name, team_list in teams.items():
        cursor.execute("SELECT id FROM functions WHERE name = ?", (func_name,))
        func_row = cursor.fetchone()
        if func_row:
            func_id = func_row["id"]
            for team_name in team_list:
                cursor.execute(
                    "INSERT OR IGNORE INTO teams (function_id, name) VALUES (?, ?)",
                    (func_id, team_name)
                )

    # Add tools
    for tool_name in tools:
        cursor.execute("INSERT OR IGNORE INTO tools (name) VALUES (?)", (tool_name,))

    # Add capabilities
    for cap_data in capabilities:
        if isinstance(cap_data, tuple):
            name = cap_data[0]
        else:
            name = cap_data
        cursor.execute("INSERT OR IGNORE INTO capabilities (name) VALUES (?)", (name,))

    conn.commit()
    conn.close()
