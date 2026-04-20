from flask import Response, jsonify, request

from services.follow_read_timeline_service import (
    build_follow_read_payload,
    generate_follow_read_chunked_audio_bytes,
)


@tts_bp.route('/follow-read-word', methods=['GET'])
def get_follow_read_word():
    raw = (request.args.get('w') or '').strip()
    if not raw or len(raw) > 160:
        return jsonify({'error': 'invalid w'}), 400

    return jsonify(build_follow_read_payload(
        word=raw,
        phonetic=(request.args.get('phonetic') or '').strip() or None,
        definition=(request.args.get('definition') or '').strip() or None,
        pos=(request.args.get('pos') or '').strip() or None,
    )), 200


@tts_bp.route('/follow-read-chunked-audio', methods=['GET'])
def get_follow_read_chunked_audio():
    raw = (request.args.get('w') or '').strip()
    if not raw or len(raw) > 160:
        return jsonify({'error': 'invalid w'}), 400

    try:
        audio_bytes = generate_follow_read_chunked_audio_bytes(
            word=raw,
            phonetic=(request.args.get('phonetic') or '').strip() or None,
        )
    except Exception:
        return jsonify({'error': 'follow read audio generation failed'}), 502

    response = Response(audio_bytes, mimetype='audio/mpeg')
    response.headers['X-Audio-Bytes'] = str(len(audio_bytes))
    return response
