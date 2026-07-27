from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from services.command_center import CommandCenterService
from services.ai_engine import AIEngine
from services.grading_service import GradingService
from services.risk_analytics import RiskAnalyticsService

ai_api_bp = Blueprint('ai_api', __name__)

@ai_api_bp.route('/api/ai/command', methods=['POST'])
@login_required
def command_center_api():
    data = request.get_json() or {}
    query = data.get('query', '')
    if not query:
        return jsonify({'status': 'error', 'message': 'Empty query'}), 400
        
    result = CommandCenterService.process_command(current_user, query)
    return jsonify(result)

@ai_api_bp.route('/api/ai/tutor', methods=['POST'])
@login_required
def tutor_api():
    data = request.get_json() or {}
    prompt = data.get('prompt', '')
    answer = AIEngine.generate_completion(prompt, system_message="You are an AI Tutor providing institutional assistance.")
    return jsonify({'status': 'success', 'answer': answer})
