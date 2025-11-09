from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)


@app.route('/')
@app.route('/login')
def hello_world():
        """Return a simple HTML login screen."""
        login_html = '''
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Login</title>
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background:#f5f7fb; }
                .container { max-width:400px; margin:80px auto; background:white; padding:24px; border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,0.08); }
                label { display:block; margin-bottom:6px; font-weight:600 }
                input[type="email"], input[type="password"] { width:100%; padding:8px 10px; margin-bottom:12px; border:1px solid #dfe6ef; border-radius:4px }
                button { width:100%; padding:10px; background:#2563eb; color:white; border:none; border-radius:4px; font-weight:600 }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Sign in</h2>
                <form method="POST" action="/login">
                    <div>
                        <label for="email">Email</label>
                        <input id="email" name="email" type="email" required />
                    </div>
                    <div>
                        <label for="password">Password</label>
                        <input id="password" name="password" type="password" required />
                    </div>
                    <button type="submit">Sign in</button>
                </form>
            </div>
        </body>
        </html>
        '''

        return render_template_string(login_html)

@app.route('/session')
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
    app.run(debug=True, port = 5001)