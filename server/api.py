import time

from flask import request, jsonify

from server import app, auth, database, reloader
from server.models import FlagStatus
from server.spam import is_spam_flag


@app.route('/api/get_config')
@auth.api_auth_required
def get_config():
    config = reloader.get_config()
    return jsonify({key: value for key, value in config.items()
                    if 'PASSWORD' not in key and 'TOKEN' not in key})


@app.route('/api/post_flags', methods=['POST'])
@auth.api_auth_required
def post_flags():
    flags = request.get_json()
    flags = [item for item in flags if not is_spam_flag(item['flag'])]

    cur_time = round(time.time())
    rows = [(item['flag'], item['sploit'], item['team'], cur_time, FlagStatus.QUEUED.name)
            for item in flags]

    db = database.get()
    db.executemany("INSERT OR IGNORE INTO flags (flag, sploit, team, time, status) "
                   "VALUES (?, ?, ?, ?, ?)", rows)
    db.commit()

    return ''

@app.route('/api/scripts/add', methods=['POST'])
@auth.api_auth_required
def api_add_script():
    """API endpoint to create or update an exploit script."""
    chall_name = request.form.get('chall_name', '').strip()
    exp_name = request.form.get('exp_name', '').strip()
    content = request.form.get('content', '')

    # Simple validation to ensure clean path names
    if not chall_name or not exp_name or not content:
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        database.add_or_update_script(chall_name, exp_name, content)
        return jsonify({'status': 'success', 'message': 'Script saved successfully.'})
    except Exception as e:
        app.logger.error(f"Error adding script: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/scripts/view', methods=['GET'])
@auth.api_auth_required
def api_view_script():
    """API endpoint to get the raw content of a script via its combined path."""
    script_path = request.args.get('path', '')
    
    # Parse the 'chall_name/exp_name' format from the frontend
    if '/' not in script_path:
        return jsonify({'error': 'Invalid script path format'}), 400
        
    chall_name, exp_name = script_path.split('/', 1)
    
    script = database.get_script(chall_name, exp_name)
    if not script:
        return jsonify({'error': 'Script not found'}), 404
        
    return jsonify({'content': script['content']})


@app.route('/api/scripts/delete', methods=['POST'])
@auth.api_auth_required
def api_delete_script():
    """API endpoint to remove an exploit script from the database."""
    script_path = request.form.get('path', '')
    
    if '/' not in script_path:
        return jsonify({'error': 'Invalid script path format'}), 400
        
    chall_name, exp_name = script_path.split('/', 1)
    
    try:
        database.delete_script(chall_name, exp_name)
        return jsonify({'status': 'success', 'message': 'Script deleted.'})
    except Exception as e:
        app.logger.error(f"Error deleting script: {e}")
        return jsonify({'error': 'Internal server error'}), 500
@app.route('/api/scripts/list', methods=['GET'])
@auth.api_auth_required
def api_list_all_scripts():
    """API endpoint returning a full JSON dump of all saved exploit scripts."""
    try:
        all_scripts = database.get_all_scripts()
        return jsonify(all_scripts)
    except Exception as e:
        app.logger.error(f"Error serving script list data dump: {e}")
        return jsonify({'error': 'Internal server error'}), 500