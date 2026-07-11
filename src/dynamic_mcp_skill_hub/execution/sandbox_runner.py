from __future__ import annotations

import sys
import importlib.util
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4
from typing import Any

from dynamic_mcp_skill_hub.models import ToolRun
from dynamic_mcp_skill_hub.utils import logger


class SandboxRunner:
    def run(self, tool_id: str, version_number: str, input_data: dict[str, Any]) -> ToolRun:
        started_at = datetime.now(UTC).isoformat()
        run_id = str(uuid4())
        
        logger.info(
            "running_sandbox_tool",
            tool_id=tool_id,
            version=version_number,
            run_id=run_id,
            input=input_data,
        )
        
        # Build the exact path to tool.py
        from dynamic_mcp_skill_hub.config import get_settings
        settings = get_settings()
        tool_file = Path(settings.tool_registry_dir) / tool_id / "versions" / version_number / "tool.py"
        
        if not tool_file.exists():
            error_msg = f"Tool file not found: {tool_file}"
            logger.error(
                "sandbox_tool_missing_file",
                tool_id=tool_id,
                version=version_number,
                file_path=str(tool_file),
            )
            return ToolRun(
                run_id=run_id,
                tool_id=tool_id,
                version_number=version_number,
                input=input_data,
                started_at=started_at,
                error=error_msg,
                finished_at=datetime.now(UTC).isoformat(),
            )
            
        try:
            # Load the module dynamically
            module_name = f"dynamic_tool_{tool_id}_{version_number}_{run_id.replace('-', '_')}"
            spec = importlib.util.spec_from_file_location(module_name, tool_file)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load spec from {tool_file}")
                
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            if not hasattr(module, "run"):
                raise AttributeError("Generated tool code does not export a 'run' function.")
                
            # Execute the tool
            output = module.run(input_data)
            
            # Clean up sys.modules to prevent memory leaks
            sys.modules.pop(module_name, None)
            
            logger.info(
                "sandbox_tool_run_success",
                tool_id=tool_id,
                version=version_number,
                run_id=run_id,
            )
            
            return ToolRun(
                run_id=run_id,
                tool_id=tool_id,
                version_number=version_number,
                input=input_data,
                output=output,
                started_at=started_at,
                finished_at=datetime.now(UTC).isoformat(),
            )
        except Exception as exc:
            import traceback
            tb = traceback.format_exc()
            logger.error(
                "sandbox_tool_run_failed",
                tool_id=tool_id,
                version=version_number,
                run_id=run_id,
                error=str(exc),
            )
            return ToolRun(
                run_id=run_id,
                tool_id=tool_id,
                version_number=version_number,
                input=input_data,
                error=f"Runtime Exception: {exc}\n{tb}",
                started_at=started_at,
                finished_at=datetime.now(UTC).isoformat(),
            )
