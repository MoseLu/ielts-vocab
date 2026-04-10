from flask import Blueprint, jsonify, request
from models import User
from routes.middleware import token_required

ai_bp = Blueprint('ai', __name__)
