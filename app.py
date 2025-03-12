from flask import Flask, redirect, render_template, request, session,make_response,session, jsonify, url_for,flash
from datetime import timedelta
import datetime
import mysql.connector
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps


app = Flask(__name__)
app.config['SECRET_KEY'] = 'srlkjghnslkrjhgjHL@ljkshlgksjrhlkjlsrkglksjrgllskrjglslslssl'
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)
app.config['SESSION_REFRESH_EACH_REQUEST'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

username = 'root'
password = ''
host = 'localhost'
database = 'leaveal1'

# Create a connection to the MySQL database
conn = mysql.connector.connect(
    user=username,
    password=password,
    host=host,
    database=database
)

# Create a cursor object to execute SQL queries
cursor = conn.cursor()
            

# Authentication Decorator
def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print("Session content:", session)  
        if 'user' not in session:
            flash("You need to log in first!", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        first_name = request.form['first_name']
        last_name = request.form['last_name']

        cursor.execute("SELECT email FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            flash("Email already registered.", "danger")
            return redirect(url_for('signup'))

        hashed_password = generate_password_hash(password)
        query = "INSERT INTO users (username, email, password, first_name, last_name) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(query, (username, email, hashed_password, first_name, last_name))
        conn.commit()
        flash("Account created successfully.", "success")
        return redirect(url_for('login'))
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor.execute("SELECT id, username, password FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user[2], password):
            session['user'] = {'id': user[0], 'username': user[1]}
            return redirect(url_for('dashboard'))

        flash("Invalid credentials.", "danger")

    return render_template('login.html')



@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

@app.route('/')
def home():
    return render_template('home.html')

##############################################
""" Private Routes (Require authorization) """


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user' not in session:  # Fix: Changed 'user_id' to 'user'
        return redirect(url_for('login'))

    if request.method == 'POST':
        if 'teacher' in request.form:
            return redirect(url_for('teacher_organization'))
        elif 'student' in request.form:
            return redirect(url_for('students_organization'))

    return render_template('dashboard.html')


@app.route('/teacher_organization', methods=['GET', 'POST'])
def teacher_organization():
    if 'user' not in session:
        return redirect(url_for('login'))

    user_id = session['user']['id']

    # Fetch only the organizations that the user created
    cursor.execute("SELECT * FROM organizations WHERE creator_id = %s", (user_id,))
    user_created_organizations = cursor.fetchall()  # Renamed for clarity

    # Fetch user's joined organizations
    cursor.execute("SELECT organization_id FROM user_organization WHERE user_id = %s", (user_id,))
    user_organizations = [row[0] for row in cursor.fetchall()]

    # Get details of joined organizations (but exclude ones they didn’t create)
    user_organization_details = []
    for organization_id in user_organizations:
        cursor.execute("SELECT * FROM organizations WHERE id = %s AND creator_id = %s", (organization_id, user_id))
        organization = cursor.fetchone()
        if organization:
            user_organization_details.append(organization)

    if request.method == 'POST':
        organization_name = request.form['organization_name']
        organization_pin = request.form['organization_pin']

        cursor.execute("SELECT id FROM organizations WHERE name = %s AND pin = %s", (organization_name, organization_pin))
        organization_id = cursor.fetchone()

        if organization_id:
            organization_id = organization_id[0]
            cursor.execute("SELECT * FROM user_organization WHERE user_id = %s AND organization_id = %s", (user_id, organization_id))
            if cursor.fetchone():
                flash("You are already a member of this organization", "error")
            else:
                cursor.execute("INSERT INTO user_organization (user_id, organization_id) VALUES (%s, %s)", (user_id, organization_id))
                conn.commit()
                flash("Organization joined successfully", "success")
        else:
            flash("Invalid organization name or pin", "error")

        return redirect(url_for('teacher_organization'))

    return render_template(
        'teacher_organization.html',
        all_organizations=user_created_organizations,  # Only show the ones created by the user
        user_organizations=user_organizations,
        user_organization_details=user_organization_details
    )




@app.route('/create_organization', methods=['POST'])
def create_organization():
    if 'user' not in session:  # Ensure user is logged in
        return redirect(url_for('login'))

    organization_name = request.form['organization_name']
    organization_pin = request.form['organization_pin']
    user_id = session['user']['id']  
    creator_name = session['user']['username']  

    cursor.execute("SELECT * FROM organizations WHERE name = %s", (organization_name,))
    if cursor.fetchone():
        flash('Organization with this name already exists', 'error')
    else:
        # FIX: Include `creator_id` in the insert statement
        cursor.execute(
            "INSERT INTO organizations (name, pin, creator_name, creator_id) VALUES (%s, %s, %s, %s)",
            (organization_name, organization_pin, creator_name, user_id)
        )
        conn.commit()
        organization_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO user_organization (user_id, organization_id) VALUES (%s, %s)",
            (user_id, organization_id)
        )
        conn.commit()
        flash('Organization created successfully', 'success')
    
    return redirect(url_for('teacher_organization'))




@app.route('/join_organization', methods=['POST'])
def join_organization():
    if 'user' not in session:  # Fix: Changed 'user_id' to 'user'
        return redirect(url_for('login'))

    organization_id = request.form['organization_id']
    organization_pin = request.form['organization_pin']
    user_id = session['user']['id']

    cursor.execute("SELECT * FROM organizations WHERE id = %s AND pin = %s", (organization_id, organization_pin))
    if cursor.fetchone():
        cursor.execute("SELECT * FROM user_organization WHERE user_id = %s AND organization_id = %s", (user_id, organization_id))
        if cursor.fetchone():
            flash("You are already a member of this organization", "error")
        else:
            cursor.execute("INSERT INTO user_organization (user_id, organization_id) VALUES (%s, %s)", (user_id, organization_id))
            conn.commit()
            flash("Organization joined successfully", "success")
    else:
        flash("Invalid organization name or pin", "error")

    return redirect(url_for('teacher_organization'))

    
    
    
@app.route('/organization/<int:organization_id>/rename', methods=['POST'])
@auth_required
def rename_organization(organization_id):
    user_name = session['user'].get('username')

    if not user_name:
        flash("User not found in session. Please log in again.", "error")
        return redirect(url_for('login'))
    
    new_name = request.form['new_name']

    # Validate the user's name
    query = "SELECT creator_name FROM organizations WHERE id = %s"
    cursor.execute(query, (organization_id,))
    result = cursor.fetchone()
    
    if not result:  
        flash("Organization not found", "error")
        return redirect(url_for('teacher_inside_org', organization_id=organization_id))
    
    creator_name = result[0]

    if creator_name != user_name:
        flash("You don't have permission to rename this organization", "error")
        return redirect(url_for('teacher_inside_org', organization_id=organization_id))

    # Rename the organization
    query = "UPDATE organizations SET name = %s WHERE id = %s"
    cursor.execute(query, (new_name, organization_id))
    conn.commit()

    flash('Organization renamed successfully!', 'success')
    return redirect(url_for('teacher_inside_org', organization_id=organization_id))


@app.route('/organization/<int:organization_id>/change_pin', methods=['POST'])
@auth_required
def change_pin(organization_id):
    user_name = session['user'].get('username')  # Fix here

    if not user_name:
        flash("User not found in session. Please log in again.", "error")
        return redirect(url_for('login'))

    new_pin = request.form['new_pin']

    query = "SELECT creator_name FROM organizations WHERE id = %s"
    cursor.execute(query, (organization_id,))
    result = cursor.fetchone()

    if not result:
        flash("Organization not found.", "error")
        return redirect(url_for('teacher_inside_org', organization_id=organization_id))

    creator_name = result[0]

    if creator_name != user_name:
        flash("You don't have permission to change the pin of this organization", "error")
        return redirect(url_for('teacher_inside_org', organization_id=organization_id))

    query = "UPDATE organizations SET pin = %s WHERE id = %s"
    cursor.execute(query, (new_pin, organization_id))
    conn.commit()

    flash('Pin changed successfully!', 'success')
    return redirect(url_for('teacher_inside_org', organization_id=organization_id))




@app.route('/organization/<int:organization_id>/delete', methods=['POST'])
@auth_required
def delete_organization(organization_id):
    user_name = session['user'].get('username')  # Fix here

    if not user_name:
        flash("User not found in session. Please log in again.", "error")
        return redirect(url_for('login'))

    # Validate the user's name
    query = "SELECT creator_name FROM organizations WHERE id = %s"
    cursor.execute(query, (organization_id,))
    result = cursor.fetchone()
    
    if not result:  
        flash("Organization not found", "error")
        return redirect(url_for('teacher_inside_org', organization_id=organization_id))

    creator_name = result[0]

    if creator_name != user_name:
        flash("You don't have permission to delete this organization", "error")
        return redirect(url_for('teacher_inside_org', organization_id=organization_id))

    # Delete related records from user_organization table
    query = "DELETE FROM user_organization WHERE organization_id = %s"
    cursor.execute(query, (organization_id,))

    # Delete the organization
    query = "DELETE FROM organizations WHERE id = %s"
    cursor.execute(query, (organization_id,))
    conn.commit()

    flash('Organization deleted successfully!', 'success')
    return redirect(url_for('teacher_organization'))




@app.route('/organization/<int:organization_id>', methods=['GET', 'POST'])
@auth_required
def teacher_inside_org(organization_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    user_id = session['user'].get('id')  # Ensure 'id' exists

    # Debugging: Log session data and user_id
    print("Session Data:", session['user'])
    print("User ID:", user_id)

    # Validate user_id
    if not user_id or not isinstance(user_id, int):
        flash("Invalid user ID", "error")
        return redirect(url_for('dashboard'))

    # Ensure connection is active
    if not conn.is_connected():
        conn.reconnect()

    # Try to get first_name from session
    first_name = session['user'].get('first_name')

    # If first_name is missing, fetch it from the database
    if not first_name:
        query = "SELECT first_name FROM users WHERE id = %s"
        cursor.execute(query, (user_id,))
        result = cursor.fetchone()
        if result:
            first_name = result[0]  # Fetch from DB
        else:
            first_name = "Unknown Teacher"  # Final fallback

    print(f"Resolved Teacher Name: {first_name}")

    # Get organization details
    query = "SELECT * FROM organizations WHERE id = %s"
    cursor.execute(query, (organization_id,))
    organization = cursor.fetchone()

    if not organization:
        flash("Organization not found", "error")
        return redirect(url_for('dashboard'))

    organization_name = organization[1]

    # Determine if the user is the creator of the organization
    creator_id = organization[5]  # Fetch creator_id directly from the organization record
    is_creator = user_id == creator_id

    # Log teacher entry immediately
    log_query = "INSERT INTO user_logs (user_id, org_id, activity) VALUES (%s, %s, %s)"
    log_message = f"Teacher {first_name} joined the class"
    cursor.execute(log_query, (user_id, organization_id if not is_creator else organization_id, log_message))
    conn.commit()  # ✅ Save to DB immediately

    # Fetch members
    members = get_updated_members(organization_id)

    return render_template(
        'teacher_dashboard.html',
        organization_name=organization_name,
        organization_data=organization,
        organization_id=organization_id,
        members=members
    )







from flask import jsonify

@app.route('/organization/<int:organization_id>/logs')
@auth_required
def get_organization_logs(organization_id):
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 403

    user_id = session['user'].get('id')

    # Ensure the database connection is active
    if conn.is_connected() == False:
        conn.reconnect(attempts=3, delay=2)

    cursor = conn.cursor()

    # Fetch the latest logs for the organization
    query = """
        SELECT activity, timestamp 
        FROM user_logs 
        WHERE org_id = %s 
        ORDER BY timestamp DESC 
        LIMIT 10
    """
    cursor.execute(query, (organization_id,))
    logs = cursor.fetchall()

    logs_list = [{"activity": log[0], "timestamp": log[1].strftime("%Y-%m-%d %H:%M:%S")} for log in logs]

    return jsonify({"logs": logs_list})











@app.route('/organization/<int:organization_id>/members', methods=['GET'])
@auth_required
def get_organization_members(organization_id):
    cursor = conn.cursor()  # Ensure cursor is correctly acquired

    cursor.execute("""
        SELECT m.id, u.first_name, u.last_name, m.join_date, m.is_active 
        FROM members m 
        JOIN users u ON m.user_id = u.id 
        WHERE m.organization_id = %s
    """, (organization_id,))

    members = cursor.fetchall()

    members_data = [{
        'id': member[0],
        'first_name': member[1],
        'last_name': member[2],
        'join_date': member[3].isoformat() if member[3] else None,
        'is_active': member[4]
    } for member in members]

    print("🔍 DEBUG: API is sending this data:", members_data)  # Debugging output ✅

    return jsonify({'organization_id': organization_id, 'members': members_data})



def get_updated_members(organization_id):
    query = """SELECT m.id, u.first_name, u.last_name, m.join_date, m.is_active 
               FROM members m 
               JOIN users u ON m.user_id = u.id 
               WHERE m.organization_id = %s"""
    cursor.execute(query, (organization_id,))
    members = cursor.fetchall()

    return [{
        'id': member[0],
        'first_name': member[1],
        'last_name': member[2],
        'join_date': member[3].isoformat() if isinstance(member[3], datetime.datetime) else str(member[3]),
        'is_active': member[4]
    } for member in members]


@app.route('/organization/<int:organization_id>/deactivate_member/<int:member_id>', methods=['POST'])
@auth_required
def deactivate_member(organization_id, member_id):
    cursor.execute("UPDATE members SET is_active = 0 WHERE id = %s AND organization_id = %s", (member_id, organization_id))
    conn.commit()
     
    return jsonify({"message": "Member deactivated successfully"}), 200


@app.route('/organization/<int:organization_id>/activate_member/<int:member_id>', methods=['POST'])
@auth_required
def activate_member(organization_id, member_id):
    cursor.execute("UPDATE members SET is_active = 1 WHERE id = %s AND organization_id = %s", (member_id, organization_id))
    conn.commit()

    return jsonify({"message": "Member activated successfully"}), 200

@app.route('/organization/<int:organization_id>/remove_member/<int:member_id>', methods=['POST'])
@auth_required
def remove_member(organization_id, member_id):
    cursor.execute("DELETE FROM members WHERE id = %s AND organization_id = %s", (member_id, organization_id))
    conn.commit()
    
    return jsonify({"message": "Member removed successfully"}), 200





    
########################## STUDENTS SIDE #################################

########################## STUDENTS SIDE #################################

########################## STUDENTS SIDE #################################

########################## STUDENTS SIDE #################################

########################## STUDENTS SIDE #################################

########################## STUDENTS SIDE #################################

########################## STUDENTS SIDE #################################

@app.route('/students/student_organization', methods=['GET', 'POST'])
@auth_required
def students_organization():
    if 'user' not in session:  
        return redirect(url_for('login'))

    user_id = session['user']['id']  

    cursor.execute("SELECT organization_id FROM user_organization WHERE user_id = %s", (user_id,))
    user_organizations = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT * FROM organizations")
    all_organizations = cursor.fetchall()

    user_organization_details = []
    for organization_id in user_organizations:
        cursor.execute("SELECT * FROM organizations WHERE id = %s", (organization_id,))
        organization = cursor.fetchone()
        user_organization_details.append(organization)

    if request.method == 'POST':
        organization_name = request.form['organization_name']
        organization_pin = request.form['organization_pin']

        cursor.execute("SELECT id FROM organizations WHERE name = %s AND pin = %s", (organization_name, organization_pin))
        organization_id = cursor.fetchone()

        if organization_id:
            organization_id = organization_id[0]
            cursor.execute("SELECT * FROM user_organization WHERE user_id = %s AND organization_id = %s", (user_id, organization_id))
            if cursor.fetchone():
                flash("You are already a member of this organization", "error")
            else:
                cursor.execute("INSERT INTO user_organization (user_id, organization_id) VALUES (%s, %s)", (user_id, organization_id))
                conn.commit()
                flash("Organization joined successfully", "success")
        else:
            flash("Invalid organization name or pin", "error")
        return redirect(url_for('students_organization'))

    return render_template('student_organization.html', all_organizations=all_organizations, user_organizations=user_organizations, user_organization_details=user_organization_details)


@app.route('/students/leave_organization/<int:organization_id>', methods=['POST'])
@auth_required
def leave_organization(organization_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    user_id = session['user']['id']
    
    if not organization_id:
        flash("Invalid organization ID.", "error")
        return redirect(url_for('students_organization'))

    # Ensure first_name is retrieved correctly
    first_name = session['user'].get('first_name')
    
    if not first_name:  
        cursor.execute("SELECT first_name FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()
        first_name = result[0] if result and result[0] else 'Unknown Student'

    # Log exit in user_logs
    log_message = f"Student {first_name} is inactive."
    cursor.execute("INSERT INTO user_logs (user_id, org_id, activity) VALUES (%s, %s, %s)", 
                   (user_id, organization_id, log_message))
    
    # Update members table to mark user as inactive
    cursor.execute("UPDATE members SET is_active = 0 WHERE user_id = %s AND organization_id = %s", 
                   (user_id, organization_id))
    
    conn.commit()  # Save changes
    flash("You have left the room.", "info")

    return redirect(url_for('students_organization'))





@app.route('/students/students_join_organization', methods=['POST'])
@auth_required
def students_join_organization():
    if 'user' not in session:  # Fix: Changed 'user_id' to 'user'
        return redirect(url_for('login'))

    organization_id = request.form['organization_id']
    organization_pin = request.form['organization_pin']
    user_id = session['user']['id']

    cursor.execute("SELECT * FROM organizations WHERE id = %s AND pin = %s", (organization_id, organization_pin))
    if cursor.fetchone():
        cursor.execute("SELECT * FROM user_organization WHERE user_id = %s AND organization_id = %s", (user_id, organization_id))
        if cursor.fetchone():
            flash("You are already a member of this organization", "error")
        else:
            cursor.execute("INSERT INTO user_organization (user_id, organization_id) VALUES (%s, %s)", (user_id, organization_id))
            conn.commit()
            flash("Organization joined successfully", "success")
    else:
        flash("Invalid organization name or pin", "error")

    return redirect(url_for('students_organization'))




@app.route('/students/students_inside_org/<int:organization_id>', methods=['GET'])
@auth_required
def students_inside_org(organization_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    print(f"Page loading with organization id: {organization_id}")

    # Query the database to retrieve the organization data
    query = "SELECT * FROM organizations WHERE id = %s"
    cursor.execute(query, (organization_id,))
    organization = cursor.fetchone()

    if not organization:
        flash("Organization not found", "error")
        return redirect(url_for('dashboard'))  # Redirect to a relevant page

    organization_name = organization[1]  # Extract the organization name
    organization_pin = organization[4] 

    # Get student info
    user_id = session['user'].get('id')
    first_name = session['user'].get('first_name')

    # Fetch first_name from database if missing
    if not first_name:
        cursor.execute("SELECT first_name FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()
        first_name = result[0] if result else "Unknown Student"
    
    # Check if user is already in members table
    cursor.execute("SELECT id FROM members WHERE user_id = %s AND organization_id = %s", (user_id, organization_id))
    existing_member = cursor.fetchone()

    if not existing_member:
        # Insert into members table with is_active = 0
        cursor.execute("INSERT INTO members (user_id, organization_id, is_active) VALUES (%s, %s, 0)", 
                       (user_id, organization_id))
        conn.commit()

    # Log student entry
    log_query = "INSERT INTO user_logs (user_id, org_id, activity) VALUES (%s, %s, %s)"
    log_message = f"Student {first_name} entered the room"
    cursor.execute(log_query, (user_id, organization_id, log_message))
    conn.commit()

    return render_template(
        'students_dashboard.html',
        organization_name=organization_name,
        organization_data=organization,
        organization_id=organization_id,
        organization_pin=organization_pin
    )


@app.route('/log_split_screen', methods=['POST'])
@auth_required
def log_split_screen():
    if 'user' not in session:
        print("Unauthorized request")
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    print("Received data:", data)  # Debugging

    organization_id = data.get('organization_id')
    user_id = session['user'].get('id')
    first_name = session['user'].get('first_name')

    # Fetch first_name from database if missing
    if not first_name:
        cursor.execute("SELECT first_name FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()
        first_name = result[0] if result else "Unknown Student"

    print(f"Logging: Student {first_name} is using splitscreen.")

    try:
        # Insert log into user_logs table
        log_query = "INSERT INTO user_logs (user_id, org_id, activity) VALUES (%s, %s, %s)"
        log_message = f"Student {first_name} is using splitscreen."
        
        cursor.execute(log_query, (user_id, organization_id, log_message))
        conn.commit()
        print("Log successfully added")

        return jsonify({"message": "Split-screen logged"}), 200
    except Exception as e:
        print("Error inserting log:", e)
        conn.rollback()
        return jsonify({"error": "Database error"}), 500


@app.route('/log_app_minimized', methods=['POST'])
@auth_required
def log_app_minimized():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    organization_id = data.get('organization_id')
    user_id = session['user'].get('id')
    first_name = session['user'].get('first_name')

    # Fetch first_name if missing
    if not first_name:
        cursor.execute("SELECT first_name FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()
        first_name = result[0] if result else "Unknown Student"

    # Fetch organization_id from database if missing
    if not organization_id:
        cursor.execute("SELECT organization_id FROM user_organization WHERE user_id = %s LIMIT 1", (user_id,))
        result = cursor.fetchone()
        organization_id = result[0] if result else None

    if not organization_id:
        return jsonify({"error": "Organization ID not found"}), 400  # Bad request

    # Insert log into user_logs table
    log_query = "INSERT INTO user_logs (user_id, org_id, activity) VALUES (%s, %s, %s)"
    log_message = f"User {first_name} minimized the app."

    cursor.execute(log_query, (user_id, organization_id, log_message))
    conn.commit()

    return jsonify({"message": "App minimized logged"}), 200








@app.route('/students/set_active/<int:organization_id>', methods=['POST'])
@auth_required
def set_student_active(organization_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    user_id = session['user']['id']
    first_name = session['user'].get('first_name')

    # Fetch first_name from database if missing
    if not first_name:
        cursor.execute("SELECT first_name FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()
        first_name = result[0] if result else "Unknown Student"

    # Check if user is a member of the organization
    cursor.execute("SELECT id FROM members WHERE organization_id = %s AND user_id = %s", (organization_id, user_id))
    member = cursor.fetchone()

    if member:
        cursor.execute("UPDATE members SET is_active = 1 WHERE organization_id = %s AND user_id = %s", (organization_id, user_id))
    else:
        cursor.execute("INSERT INTO members (organization_id, user_id, is_active) VALUES (%s, %s, 1)", (organization_id, user_id))

    conn.commit()

    # Log activity in user_logs table
    log_query = "INSERT INTO user_logs (user_id, org_id, activity) VALUES (%s, %s, %s)"
    log_message = f"Student {first_name} is active."

    cursor.execute(log_query, (user_id, organization_id, log_message))
    conn.commit()

    return jsonify({"message": "Status updated successfully"}), 200




if __name__ == '__main__':
    app.run(debug=True)