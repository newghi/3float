from flask import Blueprint, render_template, request, redirect

talktalk_bp = Blueprint('talktalk', __name__)

# talktalk '문의내역 업데이트'
@talktalk_bp.route('/index', methods=['GET'])
def index():
    return render_template('index.html')