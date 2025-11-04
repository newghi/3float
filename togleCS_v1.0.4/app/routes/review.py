from flask import Blueprint, render_template, request, redirect

review_bp = Blueprint('review', __name__)

# talktalk '문의내역 업데이트'
@review_bp.route('/updateView', methods=['GET'])
def updateView():
    return render_template('index.html')