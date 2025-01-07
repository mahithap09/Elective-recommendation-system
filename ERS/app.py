from flask import Flask, render_template, request, redirect, session
from flask_mysqldb import MySQL
import pandas as pd
import openai
from sklearn.metrics.pairwise import cosine_similarity
import re


app = Flask(__name__)
app.secret_key = 'secret key'


app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'password'
app.config['MYSQL_DB'] = 'capstone6'

mysql = MySQL(app)


openai.api_key = 'openapikey'


df = pd.read_csv('electives.csv')

# Input validation functions
def validate_student_id(student_id):
    return bool(re.match(r'^2\d{4}$', student_id)) and student_id != "00000"

def validate_name(name):
    return len(name) > 3 and not re.match(r'^(xxx|xyz|ssl|wwe|www|abcd)$', name, re.IGNORECASE)

def validate_prompt(prompt):
    invalid_prompts = [
        'xxxx', 'abc', 'xyz', 'ssl', 'wwe', 'www', 'abcd', 'dsfls', '233fd', 'sdljz', 'dfe23'
    ]
    if any(invalid_string in prompt.lower() for invalid_string in invalid_prompts):
        return False
    return bool(re.match(r'^[a-zA-Z\s]+$', prompt))

# Function to recommend electives using embeddings
import logging

logging.basicConfig(level=logging.DEBUG)

def recommend_electives_with_embeddings(prompt, electives_df):
    try:
        logging.debug("Generating embeddings for the prompt...")
        prompt_embedding = openai.Embedding.create(
            input=prompt,
            model="text-embedding-ada-002"
        )['data'][0]['embedding']
        logging.debug("Prompt embeddings generated.")

        elective_embeddings = []
        for i, elective in enumerate(electives_df['Elective']):
            logging.debug(f"Generating embeddings for elective {i + 1}: {elective}")
            elective_embedding = openai.Embedding.create(
                input=elective,
                model="text-embedding-ada-002"
            )['data'][0]['embedding']
            elective_embeddings.append(elective_embedding)

        logging.debug("Calculating similarity scores...")
        similarity_scores = cosine_similarity(
            [prompt_embedding], elective_embeddings
        ).flatten()

        electives_df['Similarity'] = similarity_scores

        top_recommendations = electives_df.sort_values(by='Similarity', ascending=False).head(5)

        logging.debug("Recommendations generated successfully.")
        return top_recommendations[['Elective', 'Department', 'Course Code', 'Year', 'Similarity']].to_dict(orient='records')

    except Exception as e:
        logging.error(f"Error in recommend_electives_with_embeddings: {e}")
        return []



@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        student_id = request.form['student_id']
        name = request.form['name']
        department = request.form['department']
        year = request.form['year']
        prompt = request.form['prompt']

        if not validate_student_id(student_id):
            return render_template('error.html', message="Invalid Student ID.")
        if not validate_name(name):
            return render_template('error.html', message="Invalid Name.")
        if not validate_prompt(prompt):
            return render_template('error.html', message="Invalid Prompt.")

        
        try:
            recommendations = recommend_electives_with_embeddings(prompt, df)
            if not recommendations:
                return render_template('error.html', message="No relevant electives found based on the provided prompt.")

            return render_template('recommendations.html', 
                                   recommendations=recommendations, 
                                   name=name, 
                                   department=department, 
                                   student_id=student_id,
                                   year=year)
        except Exception as e:
            return render_template('error.html', message=f"Error: {e}")

    return render_template('index.html')


@app.route('/select_elective', methods=['POST'])
def select_elective():
    student_id = request.form.get('student_id')
    student_name = request.form.get('student_name')
    elective_name = request.form.get('elective_name')
    department = request.form.get('department')
    course_code = request.form.get('course_code')
    year = request.form.get('year')

    if not all([student_id, student_name, elective_name, department, course_code, year]):
        return "Missing required form fields", 400

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM elective_selections WHERE student_id = %s AND elective_name = %s", (student_id, elective_name))
    existing_record = cur.fetchone()

    if existing_record:
        return f"You are already registered for the elective: {elective_name}.", 400

    cur.execute("INSERT INTO elective_selections (student_id, student_name, elective_name, department, course_code, year) VALUES (%s, %s, %s, %s, %s, %s)",
                (student_id, student_name, elective_name, department, course_code, year))
    mysql.connection.commit()

    return redirect('/confirmation')


@app.route('/confirmation')
def confirmation():
    return render_template('confirmation.html')


@app.route('/hod_login', methods=['GET', 'POST'])
def hod_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM hod WHERE email = %s AND password = %s", (email, password))
        hod = cur.fetchone()

        if hod:
            session['hod_logged_in'] = True
            return redirect('/hod_dashboard')
        else:
            error = "Invalid credentials. Please contact admin support."
            return render_template('hod_login.html', error=error)

    return render_template('hod_login.html')


@app.route('/hod_dashboard')
def hod_dashboard():
    cur = mysql.connection.cursor()
    try:
        # Explicitly exclude the 'id' column and fetch relevant columns
        cur.execute("SELECT student_id, student_name, elective_name, department, year FROM elective_selections")
        all_electives = cur.fetchall()

        cur.execute("SELECT elective_name, COUNT(*) AS student_count FROM elective_selections GROUP BY elective_name")
        elective_counts = cur.fetchall()

        cur.execute("SELECT department, COUNT(*) AS department_count FROM elective_selections GROUP BY department")
        department_counts = cur.fetchall()

        cur.execute("SELECT year, COUNT(*) AS year_count FROM elective_selections GROUP BY year")
        year_counts = cur.fetchall()

        return render_template(
            'hod_dashboard.html',
            all_electives=all_electives,
            elective_counts=elective_counts,
            department_counts=department_counts,
            year_counts=year_counts
        )

    except Exception as e:
        return f"Error: {str(e)}"


if __name__ == '__main__':
    app.run(debug=True)

