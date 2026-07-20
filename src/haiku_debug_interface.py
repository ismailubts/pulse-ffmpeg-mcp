#!/usr/bin/env python3
"""
Haiku Debug Interface - Non-intrusive debugging for Haiku LLM integration
Captures FFmpeg commands, prompts, and responses for analysis and improvement
"""

import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

# Configure debug logging
debug_logger = logging.getLogger('haiku_debug')
debug_logger.setLevel(logging.DEBUG)

@dataclass
class HaikuDebugSession:
    session_id: str
    timestamp: str
    user_request: str
    haiku_prompt_sent: str
    haiku_response: str
    ffmpeg_commands_generated: List[str]
    actual_files_used: List[str]
    expected_files: List[str]
    processing_result: Dict[str, Any]
    confidence_score: float
    cost_usd: float
    success: bool
    errors: List[str]

class HaikuDebugger:
    """
    Debug interface for Haiku LLM integration
    Can be easily disabled with environment variable HAIKU_DEBUG=false
    """
    
    def __init__(self):
        import os
        self.enabled = os.getenv("HAIKU_DEBUG", "true").lower() == "true"
        self.debug_dir = Path("/tmp/music/debug/haiku")
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        
        if self.enabled:
            debug_logger.info("🐛 Haiku Debug Interface ENABLED")
        else:
            debug_logger.info("🔇 Haiku Debug Interface DISABLED")
    
    def start_session(self, user_request: str) -> str:
        """Start a new debug session and return session ID"""
        if not self.enabled:
            return ""
            
        session_id = f"haiku_debug_{int(time.time() * 1000)}"
        self.current_session = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "user_request": user_request,
            "haiku_prompt_sent": "",
            "haiku_response": "",
            "ffmpeg_commands_generated": [],
            "actual_files_used": [],
            "expected_files": [],
            "processing_result": {},
            "confidence_score": 0.0,
            "cost_usd": 0.0,
            "success": False,
            "errors": []
        }
        
        debug_logger.info(f"🎬 Started debug session: {session_id}")
        return session_id
    
    def log_haiku_prompt(self, prompt: str):
        """Log the prompt sent to Haiku"""
        if not self.enabled:
            return
            
        self.current_session["haiku_prompt_sent"] = prompt
        debug_logger.debug(f"📝 Haiku prompt logged: {len(prompt)} characters")
    
    def log_haiku_response(self, response: str, confidence: float = 0.0, cost: float = 0.0):
        """Log Haiku's response"""
        if not self.enabled:
            return
            
        self.current_session["haiku_response"] = response
        self.current_session["confidence_score"] = confidence
        self.current_session["cost_usd"] = cost
        debug_logger.debug(f"💭 Haiku response logged: confidence={confidence:.2f}, cost=${cost:.4f}")
    
    def log_ffmpeg_command(self, command: str):
        """Log an FFmpeg command that was generated"""
        if not self.enabled:
            return
            
        self.current_session["ffmpeg_commands_generated"].append(command)
        debug_logger.debug(f"⚡ FFmpeg command: {command[:100]}...")
    
    def log_file_usage(self, actual_files: List[str], expected_files: List[str] = None):
        """Log which files were actually used vs expected"""
        if not self.enabled:
            return
            
        self.current_session["actual_files_used"] = actual_files
        self.current_session["expected_files"] = expected_files or []
        debug_logger.debug(f"📁 Files used: {len(actual_files)} actual, {len(expected_files or [])} expected")
    
    def log_processing_result(self, result: Dict[str, Any]):
        """Log the final processing result"""
        if not self.enabled:
            return
            
        self.current_session["processing_result"] = result
        self.current_session["success"] = result.get("success", False)
        debug_logger.debug(f"✅ Processing result: success={result.get('success', False)}")
    
    def log_error(self, error: str):
        """Log an error during processing"""
        if not self.enabled:
            return
            
        self.current_session["errors"].append(error)
        debug_logger.error(f"❌ Error logged: {error}")
    
    def end_session(self) -> Optional[str]:
        """End debug session and save to file"""
        if not self.enabled or not hasattr(self, 'current_session'):
            return None
            
        session_id = self.current_session["session_id"]
        
        # Save debug session to file
        debug_file = self.debug_dir / f"{session_id}.json"
        with open(debug_file, 'w') as f:
            json.dump(self.current_session, f, indent=2)
        
        debug_logger.info(f"💾 Debug session saved: {debug_file}")
        
        # Generate summary report
        self._generate_summary_report()
        
        return str(debug_file)
    
    def _generate_summary_report(self):
        """Generate a summary report for analysis"""
        session = self.current_session
        
        report = f"""
🐛 HAIKU DEBUG SESSION REPORT
================================

🎯 User Request: {session['user_request']}

📝 Haiku Prompt Length: {len(session['haiku_prompt_sent'])} characters
💭 Haiku Response Length: {len(session['haiku_response'])} characters
📊 Confidence Score: {session['confidence_score']:.2f}
💰 Cost: ${session['cost_usd']:.4f}

⚡ FFmpeg Commands Generated: {len(session['ffmpeg_commands_generated'])}
{chr(10).join(f"   {i+1}. {cmd[:80]}..." for i, cmd in enumerate(session['ffmpeg_commands_generated']))}

📁 File Usage Analysis:
   Expected files: {len(session['expected_files'])}
   Actual files used: {len(session['actual_files_used'])}
   
   Expected: {session['expected_files']}
   Actual: {session['actual_files_used']}

✅ Processing Success: {session['success']}
❌ Errors: {len(session['errors'])}
{chr(10).join(f"   - {error}" for error in session['errors'])}

🎬 Final Result: {session['processing_result'].get('message', 'N/A')}
"""
        
        # Save report to readable file
        report_file = self.debug_dir / f"{session['session_id']}_report.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(report)
        debug_logger.info(f"📊 Summary report: {report_file}")

# Global debugger instance
haiku_debugger = HaikuDebugger()

def debug_haiku_session(user_request: str):
    """Decorator/context manager for debugging Haiku sessions"""
    session_id = haiku_debugger.start_session(user_request)
    
    class DebugContext:
        def __enter__(self):
            return haiku_debugger
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type:
                haiku_debugger.log_error(f"Exception: {exc_type.__name__}: {exc_val}")
            haiku_debugger.end_session()
    
    return DebugContext()

# Helper functions for easy integration
def log_haiku_prompt(prompt: str):
    """Log Haiku prompt - can be called from anywhere"""
    haiku_debugger.log_haiku_prompt(prompt)

def log_haiku_response(response: str, confidence: float = 0.0, cost: float = 0.0):
    """Log Haiku response - can be called from anywhere"""
    haiku_debugger.log_haiku_response(response, confidence, cost)

def log_ffmpeg_command(command: str):
    """Log FFmpeg command - can be called from anywhere"""
    haiku_debugger.log_ffmpeg_command(command)

def log_file_usage(actual_files: List[str], expected_files: List[str] = None):
    """Log file usage - can be called from anywhere"""
    haiku_debugger.log_file_usage(actual_files, expected_files)

def log_processing_result(result: Dict[str, Any]):
    """Log processing result - can be called from anywhere"""
    haiku_debugger.log_processing_result(result)

def log_error(error: str):
    """Log error - can be called from anywhere"""
    haiku_debugger.log_error(error)

# MCP Tool for interacting with debug data
def get_debug_sessions() -> List[str]:
    """Get list of debug session files"""
    if not haiku_debugger.enabled:
        return []
    
    return [f.name for f in haiku_debugger.debug_dir.glob("haiku_debug_*.json")]

def get_debug_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get specific debug session data"""
    if not haiku_debugger.enabled:
        return None
    
    debug_file = haiku_debugger.debug_dir / f"{session_id}.json"
    if debug_file.exists():
        with open(debug_file) as f:
            return json.load(f)
    return None

def analyze_debug_sessions() -> Dict[str, Any]:
    """Analyze all debug sessions and provide insights"""
    if not haiku_debugger.enabled:
        return {"enabled": False}
    
    sessions = []
    for session_file in haiku_debugger.debug_dir.glob("haiku_debug_*.json"):
        with open(session_file) as f:
            sessions.append(json.load(f))
    
    if not sessions:
        return {"enabled": True, "sessions": 0}
    
    # Analyze patterns
    total_cost = sum(s.get("cost_usd", 0) for s in sessions)
    avg_confidence = sum(s.get("confidence_score", 0) for s in sessions) / len(sessions)
    success_rate = sum(1 for s in sessions if s.get("success", False)) / len(sessions)
    
    # File usage analysis
    file_mismatches = []
    for session in sessions:
        expected = set(session.get("expected_files", []))
        actual = set(session.get("actual_files_used", []))
        if expected != actual:
            file_mismatches.append({
                "session_id": session["session_id"],
                "expected": list(expected),
                "actual": list(actual),
                "missing": list(expected - actual),
                "unexpected": list(actual - expected)
            })
    
    return {
        "enabled": True,
        "sessions": len(sessions),
        "total_cost_usd": total_cost,
        "average_confidence": avg_confidence,
        "success_rate": success_rate,
        "file_mismatches": len(file_mismatches),
        "mismatch_details": file_mismatches[:5],  # Show first 5
        "recommendations": _generate_recommendations(sessions)
    }

def _generate_recommendations(sessions: List[Dict[str, Any]]) -> List[str]:
    """Generate recommendations based on debug session analysis"""
    recommendations = []
    
    # Check confidence scores
    low_confidence_sessions = [s for s in sessions if s.get("confidence_score", 0) < 0.7]
    if len(low_confidence_sessions) > len(sessions) * 0.3:
        recommendations.append("Consider improving Haiku prompts - 30%+ sessions have low confidence")
    
    # Check file usage
    file_mismatch_sessions = []
    for session in sessions:
        expected = set(session.get("expected_files", []))
        actual = set(session.get("actual_files_used", []))
        if expected != actual:
            file_mismatch_sessions.append(session)
    
    if len(file_mismatch_sessions) > len(sessions) * 0.5:
        recommendations.append("File selection logic needs improvement - 50%+ sessions use wrong files")
    
    # Check success rate
    success_rate = sum(1 for s in sessions if s.get("success", False)) / len(sessions)
    if success_rate < 0.8:
        recommendations.append(f"Low success rate ({success_rate:.1%}) - review error patterns")
    
    return recommendations