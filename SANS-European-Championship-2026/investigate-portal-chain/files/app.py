from flask import Flask, send_from_directory, render_template_string, request, redirect, url_for, flash, session, render_template, request, jsonify, make_response
import logging
import os
from functools import wraps
from logging_config import setup_logging  # Import the logging configuration

app = Flask(__name__)
app.secret_key = 'GVhVLraKTxXEHHWArrLp'  # For flashing messages and sessions 
# Create API keys
USER_API_KEY = 'KQ7VJKY2YI5Z5RSN0U9NIURF22J8P63B'
ADMIN_API_KEY = 'B9O8MXV4TKTGWJ37H8ZGYFF5R2IAM6CH'

# Create valid users

VALID_USERNAME = 'dev'
VALID_PASSWORD = 'samtheman'
VALID_USERNAME_ADMIN = 'admin'
VALID_PASSWORD_ADMIN = 'LoremIpsumColorDamet9911??' 

###Set up logging####

logger = setup_logging()

def custom_log(message):
    logger.info(message)  # This will go to 'custom_logs.log

# Function to log custom messages
def log_session_request():
    # Check if session is present
    if 'logged_in' in session:
        #session_token = request.cookies.get(app.session_cookie_name)  # Get the actual session token from cookies
        session_token = app.config['SESSION_COOKIE_NAME']
        log_message = f"User '{session.get('username')}' - {request.method} {request.path} - Session Cookie: {session_token[0:20]} (truncated), signed with key: '{app.secret_key}'"
        custom_log(log_message)
    else:
        log_message = f"A request was made without an active session: {request.method} {request.path} from IP {request.remote_addr}"
        custom_log(log_message)

#Configure logging
#logging.basicConfig(filename='requestlog.log', level=logging.DEBUG,
#                    format='%(asctime)s - %(levelname)s - %(message)s')


###DECORATORS FOR ACCESS CONTROL####

#Decorator for allowing api-acces with a user/admin token
# TODO: add admintoken to this decoreator
def user_api_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if the API-Token header is present and matches the user API key
        api_token = request.headers.get('API-Key')
        if api_token != USER_API_KEY and api_token != ADMIN_API_KEY:
            return jsonify({'error': 'Unauthorized access. Invalid or missing "API-Key" for user.'}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_api_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if the API-Token header is present and matches the admin API key
        api_token = request.headers.get('API-Key')
        if api_token != ADMIN_API_KEY:
            return jsonify({'error': 'Unauthorized access. Invalid or missing "API-Key" for admin.'}), 401
        return f(*args, **kwargs)
    return decorated_function

# Decorator to protect routes
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('You need to log in to access this page.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

###WEB ENDPOINTS###

@app.route('/')
def home():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username != "dev" and username != "admin":
            flash('User does not exist.')
            return redirect(url_for('login'))


        # Check if the user has correct password for one of the two defined users
        if username == VALID_USERNAME and password == VALID_PASSWORD:
            session['logged_in'] = True
            session['username'] = "dev"
            session['usertype'] = "user"
            return redirect(url_for('profile'))
        elif username == VALID_USERNAME_ADMIN and password == VALID_PASSWORD_ADMIN:
            session['logged_in'] = True
            session['username'] = "admin"
            session['usertype'] = "administrator"
            return redirect(url_for('profile'))
        else:
            flash('Invalid credentials, please try again.')
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('login'))


@app.route('/profile')
@login_required
def profile():
    log_session_request()
    return render_template('profile.html')



@app.route('/robots.txt')
def serve_robots():
    return send_from_directory('.', 'robots.txt')

# Make the /tmp/ folder indexable and map it to /tmpfiles/all
@app.route('/tmpfiles/all')
def index_tmp():
    directory = './tmp'
    items = os.listdir(directory)

    # Generate an HTML list of files and directories
    html = "<h1>Index of /tmp/</h1><ul>"
    for item in items:
        if os.path.isdir(os.path.join(directory, item)):
            html += f"<li><a href='/tmp/{item}/'>{item}/</a></li>"
        else:
            html += f"<li><a href='/tmp/{item}'>{item}</a></li>"
    html += "</ul>"
    return render_template_string(html)


# Route to list files inside ./tmp/backup or other subdirectories
@app.route('/tmp/<path:subpath>/')
def list_subdir(subpath):
    directory = os.path.join('./tmp', subpath)
    if not os.path.exists(directory) or not os.path.isdir(directory):
        return "Directory not found.", 404

    items = os.listdir(directory)
    if not items:
        return f"<h1>Index of /tmp/{subpath}/</h1><p>Directory is empty.</p>"

    # Generate an HTML list of files
    html = f"<h1>Index of /tmp/{subpath}/</h1><ul>"
    for item in items:
        full_path = os.path.join(directory, item)
        if os.path.isdir(full_path):
            html += f"<li><a href='/tmp/{subpath}/{item}/'>{item}/</a></li>"
        else:
            html += f"<li><a href='/tmp/{subpath}/{item}'>{item}</a></li>"
    html += "</ul>"
    return render_template_string(html)


# Route to serve individual files
@app.route('/tmp/<path:subpath>/<path:filename>')
def serve_file(subpath, filename):
    directory = os.path.join('./tmp', subpath)
    return send_from_directory(directory, filename)

###API ENDPOINTS###

##LOW PRIV API###

# Fetch API key based on user 
@app.route('/api/getApiKey')
@login_required
def get_api_key():
    # Get the username from the session
    username = session.get('username')

    # Check if the user is 'dev' or 'admin' and return the respective API key
    if username == 'dev':
        return jsonify({'api_key': USER_API_KEY})
    elif username == 'admin':
        return jsonify({'api_key': ADMIN_API_KEY})
    else:
        return jsonify({'error': 'Unauthorized access or user not exist.'}), 401

# Fetch current user session and return the username
@app.route('/api/getCurrentUser', methods=['GET'])
@login_required
def get_current_user():
    if 'logged_in' in session:
        return jsonify({'logged_in_as': session.get('username')})
    else:
        return


## ADMIN API - check access decorator##

# Endpoint to get the log file content
@app.route('/api/admin/getLogs', methods=['GET'])
@user_api_required #intended, this is vulnerable.
def get_logs():
    try:
        # Read the contents of the custom log file
        with open('custom_logs.log', 'r') as log_file:
            logs = log_file.read()
        
        logs_with_newlines = logs.replace('\n', '\n\n')
        # Return logs as plain text
        response = make_response((logs, 200))  # Create a response object
        response.headers['FLAG4'] = 'mne{k33p_y0ur_l0gs_cl0s3_but_n0t_th4t_cl0s3}'  #
        return response

    except Exception as e:
        return jsonify({"error": f"Failed to read log file: {str(e)}"}), 500

@app.route('/api/admin/getFlag', methods=['GET'])
@admin_api_required
def get_flag():
    return "Well done, here is your FLAG5: mne{d0nt_dr0p_y0ur_k3ys}"

### ENDPOINTS FOR CASES AND EVIDENCE ###

ongoing_cases = [
    {'case_id': 1, 'case_title': 'Robbery at 5th Avenue', 'status': 'Investigating', 'assigned_to': 'Detective John', 'date_reported': '2025-01-20'},
    {'case_id': 2, 'case_title': 'Missing Person - Jane Doe', 'status': 'Open', 'assigned_to': 'Detective Maria', 'date_reported': '2025-01-18'},
    {'case_id': 3, 'case_title': 'Arson at Park Mall', 'status': 'Under Review', 'assigned_to': 'Detective Liam', 'date_reported': '2025-01-15'},
    {'case_id': 4, 'case_title': 'Homicide at Maple Street', 'status': 'Investigating', 'assigned_to': 'Detective Alice', 'date_reported': '2025-01-12'},
    {'case_id': 5, 'case_title': 'Bank Heist at Central Bank', 'status': 'Open', 'assigned_to': 'Detective Michael', 'date_reported': '2025-01-10'},
    {'case_id': 6, 'case_title': 'Cyber Fraud at TechCorp', 'status': 'Under Review', 'assigned_to': 'Detective Robert', 'date_reported': '2025-01-08'},
    {'case_id': 7, 'case_title': 'Drug Bust at Riverside', 'status': 'Investigating', 'assigned_to': 'Detective Sarah', 'date_reported': '2025-01-05'},
    {'case_id': 8, 'case_title': 'Kidnapping of Alex Green', 'status': 'Open', 'assigned_to': 'Detective Emma', 'date_reported': '2025-01-03'},
    {'case_id': 9, 'case_title': 'Murder of John Smith', 'status': 'Under Review', 'assigned_to': 'Detective Noah', 'date_reported': '2025-01-01'},
    {'case_id': 10, 'case_title': 'Smuggling Ring at Harbor', 'status': 'Investigating', 'assigned_to': 'Detective Isabella', 'date_reported': '2024-12-29'},
    {'case_id': 11, 'case_title': 'Hit-and-Run at Elm Street', 'status': 'Open', 'assigned_to': 'Detective Jacob', 'date_reported': '2024-12-28'},
    {'case_id': 12, 'case_title': 'Armed Robbery at Diamond Store', 'status': 'Under Review', 'assigned_to': 'Detective Sophia', 'date_reported': '2024-12-25'},
    {'case_id': 13, 'case_title': 'Vandalism at City Park', 'status': 'Investigating', 'assigned_to': 'Detective Liam', 'date_reported': '2024-12-22'},
]

# Sample data: sensitive-looking evidence related to each case
evidence = {
    1: [{'evidence_id': 1, 'description': 'Security Camera Footage', 'type': 'Video', 'confidential_info': 'Involves police informant, potential risk to undercover operation'},
        {'evidence_id': 2, 'description': 'Fingerprints', 'type': 'Physical', 'confidential_info': 'Match to criminal syndicate, needs clearance before public disclosure'},
        {'evidence_id': 3, 'description': 'Witness Testimony', 'type': 'Testimony', 'confidential_info': 'Witness in protective custody, full name withheld for security reasons'},
        {'evidence_id': 4, 'description': 'Confidential Report', 'type': 'Document', 'confidential_info': 'Detailed financial transactions pointing to organized crime'}],
    2: [{'evidence_id': 1, 'description': 'Missing Person’s Last Known Location', 'type': 'Location', 'confidential_info': 'Location linked to suspected criminal activities, potentially dangerous'},
        {'evidence_id': 2, 'description': 'Witness Testimony', 'type': 'Testimony', 'confidential_info': 'Inconsistent testimony, could be fabricated under pressure from unknown parties'},
        {'evidence_id': 3, 'description': 'Security Footage from Nearby Cafe', 'type': 'Video', 'confidential_info': 'Footage reveals sensitive locations that could jeopardize ongoing investigations'}],
    3: [{'evidence_id': 1, 'description': 'Fire Department Report', 'type': 'Report', 'confidential_info': 'Contains names of suspected arsonists linked to a major criminal organization'},
        {'evidence_id': 2, 'description': 'Surveillance Footage', 'type': 'Video', 'confidential_info': 'Footage includes vehicle registration number linked to a top-secret witness protection case'},
        {'evidence_id': 3, 'description': 'Witness Testimony', 'type': 'Testimony', 'confidential_info': 'Witness details can lead to uncovering a series of illegal operations, requires further verification'}],
    4: [{'evidence_id': 1, 'description': 'Autopsy Report', 'type': 'Document', 'confidential_info': 'Contains graphic details, confidential witness information in custody'},
        {'evidence_id': 2, 'description': 'DNA Analysis', 'type': 'Physical', 'confidential_info': 'DNA linked to a top-tier criminal organization'},
        {'evidence_id': 3, 'description': 'Witness Report', 'type': 'Testimony', 'confidential_info': 'Potential conflicts with witness safety, partial names redacted'}],
    5: [{'evidence_id': 1, 'description': 'Security Camera Footage', 'type': 'Video', 'confidential_info': 'Video feeds implicating high-level suspects'},
        {'evidence_id': 2, 'description': 'Robbery Blueprint', 'type': 'Document', 'confidential_info': 'Detailed planning of the heist, potentially incriminating'}],
    6: [{'evidence_id': 1, 'description': 'Transaction Logs', 'type': 'Document', 'confidential_info': 'Identifying a chain of money transfers linked to dark web activity'},
        {'evidence_id': 2, 'description': 'Encrypted Files', 'type': 'Digital', 'confidential_info': 'Contains suspicious encrypted documents related to the fraud case'}],
    7: [{'evidence_id': 1, 'description': 'Drug Seized', 'type': 'Physical', 'confidential_info': 'Amounts of narcotics that tie into an international trafficking ring'},
        {'evidence_id': 2, 'description': 'Undercover Report', 'type': 'Document', 'confidential_info': 'Details about an ongoing undercover operation that could be compromised'}],
    8: [{'evidence_id': 1, 'description': 'Kidnapper’s Message', 'type': 'Text', 'confidential_info': 'Threats implicating high-profile people in the kidnapping case'},
        {'evidence_id': 2, 'description': 'Ransom Note', 'type': 'Document', 'confidential_info': 'Encrypted message sent to family, could have hidden meanings'}],
    9: [{'evidence_id': 1, 'description': 'Crime Scene Photos', 'type': 'Image', 'confidential_info': 'Graphic photos, sensitive info not yet released to the public'},
        {'evidence_id': 2, 'description': 'Suspect’s Fingerprints', 'type': 'Physical', 'confidential_info': 'DNA match linking the suspect to a number of other open cases'}],
    10: [{'evidence_id': 1, 'description': 'Seized Documents', 'type': 'Document', 'confidential_info': 'Evidence pointing to a larger network of smugglers'},
          {'evidence_id': 2, 'description': 'Covert Surveillance Footage', 'type': 'Video', 'confidential_info': 'Shows high-level traffickers, not to be made public'}],
    11: [{'evidence_id': 1, 'description': 'Accident Scene Photos', 'type': 'Image', 'confidential_info': 'Sensitive images of the injured, not to be shared'},
          {'evidence_id': 2, 'description': 'Witness Statements', 'type': 'Testimony', 'confidential_info': 'Details of the witnesses are currently redacted for safety reasons'}],
    12: [{'evidence_id': 1, 'description': 'Security Footage from Diamond Store', 'type': 'Video', 'confidential_info': 'Video footage implicates high-profile individuals'},
          {'evidence_id': 2, 'description': 'Forensic Report', 'type': 'Document', 'confidential_info': 'Contains chemical traces linking the suspects to explosives'}],
    13: [{'evidence_id': 1, 'description': 'Graffiti Evidence', 'type': 'Physical', 'confidential_info': 'Evidence collected from known vandalism hotspots'},
          {'evidence_id': 2, 'description': 'Witness Testimony', 'type': 'Testimony', 'confidential_info': 'Witness details suppressed to avoid retribution'}],
}

@app.route('/api/getOngoingCases', methods=['GET'])
@user_api_required # For dev user and Admin user
def get_ongoing_cases():
    return jsonify(ongoing_cases)

@app.route('/api/admin/getOngoingCaseEvidence', methods=['GET'])
@admin_api_required # Only for admin user
def get_ongoing_case_evidence():
    cases_with_evidence = []

    for case in ongoing_cases:
        case_id = case['case_id']
        case_copy = case.copy()  # Make a copy to avoid modifying the original
        case_copy['evidence'] = evidence.get(case_id, [])
        cases_with_evidence.append(case_copy)

    return jsonify(cases_with_evidence)

if __name__ == '__main__':
    #Only for debug: app.run(host='0.0.0.0', port=8000, debug=True)
    app.run(host='0.0.0.0', port=8000)
