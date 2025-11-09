from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

@app.route('/')
def session_home():
    """
    Serve the home.html file with dynamic vibe support.
    
    Query parameters:
      - vibe: string (optional) - one of: "Energetic and Upbeat", "Calm and Mellow", 
              "Rising Energy", "Slowing Down"
    
    Example: /session?vibe=Calm and Mellow
    """

    vibe = request.args.get('vibe', 'Rising Energy')
    
    # Read the home.html file
    try:
        with open('home.html', 'r') as f:
            html_content = f.read()
        
        # Inject the vibe setting into the page
        vibe_script = f'''
        <script>
            // Set initial vibe from server
            document.addEventListener('DOMContentLoaded', function() {{
                if (window.setVibe) {{
                    window.setVibe("{vibe}");
                }}
            }});
        </script>
        '''
        
        # Insert the script before the closing body tag
        html_content = html_content.replace('</body>', f'{vibe_script}</body>')
        
        return html_content
    except FileNotFoundError:
        return jsonify({'error': 'home.html not found'}), 404


@app.route('/audio', methods=['POST'])
def process_audio():
    """
    Skeleton route that accepts audio bytes and returns a list of strings.

    Accepts:
      - raw bytes in request.data
      - a file upload under form field 'file' (multipart/form-data)

    Returns:
      JSON list of strings (placeholder).
    """
    audio_bytes = None

    # Prefer raw body bytes
    if request.data:
        audio_bytes = request.data
    # Fallback: multipart file upload
    elif 'file' in request.files:
        f = request.files['file']
        audio_bytes = f.read()
    else:
        return jsonify({'error': 'No audio provided'}), 400

    # TODO: replace this placeholder with real audio processing/transcription
    result = ["placeholder_transcript"]
    return jsonify(result), 200


if __name__ == '__main__':
    app.run(debug=True)