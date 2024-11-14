from flask import Flask, render_template, request, redirect, url_for
from sqlalchemy import create_engine, text
from fuzzywuzzy import fuzz

# Database connection
DATABASEURL = 'postgresql://hw3072:hw3072@w4111.cisxo09blonu.us-east-1.rds.amazonaws.com:5432/postgres'
engine = create_engine(DATABASEURL)
connection = engine.connect()

# App creation
app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    global user_id
    if request.method == 'POST':
        user_id = request.form.get('user')
        return redirect(url_for('index'))

    users = connection.execute(text("SELECT uid, name FROM Users;")).fetchall()

    current_user = connection.execute(text("SELECT name FROM Users WHERE uid = :uid"), {"uid": user_id}).fetchone()

    return render_template('index.html', users=users, current_user=current_user)

@app.route('/courses', methods=['GET'])
def courses():
    query = request.args.get('query', '')
    all_courses_result = connection.execute(text("SELECT * FROM courses"))
    all_courses = all_courses_result.fetchall()

    if query:
        courses = [course for course in all_courses if 
                   fuzz.partial_ratio(query.lower(), course.name.lower()) > 70 or 
                   fuzz.partial_ratio(query.lower(), course.cid.lower()) > 70]
    else:
        courses = all_courses

    current_user = connection.execute(text("SELECT name FROM Users WHERE uid = :uid"), {"uid": user_id}).fetchone()

    return render_template('courses.html', courses=courses, current_user=current_user)

@app.route('/jobs')
def jobs():
    interested_jobs = connection.execute(text("""
    SELECT * 
    FROM Interested NATURAL JOIN Jobs
    WHERE uid = :uid;
    """), {"uid": user_id}).fetchall()

    recommended_jobs = connection.execute(text("""
    SELECT * 
    FROM Recommend NATURAL JOIN Jobs
    WHERE uid = :uid;
    """), {"uid": user_id}).fetchall()

    contributions = connection.execute(text("""
    SELECT title, cid 
    FROM Contribute;
    """)).fetchall()

    contribution_dict = {}
    for contribution in contributions:
        if contribution.title not in contribution_dict:
            contribution_dict[contribution.title] = []
        contribution_dict[contribution.title].append(contribution.cid)

    taken_courses = connection.execute(text("""
    SELECT cid 
    FROM Take NATURAL JOIN Have_Slots
    WHERE uid = :uid;
    """), {"uid": user_id}).fetchall()
    taken_courses_set = {course.cid for course in taken_courses}

    current_user = connection.execute(text("SELECT name FROM Users WHERE uid = :uid"), {"uid": user_id}).fetchone()

    return render_template(
        'jobs.html',
        interested_jobs=interested_jobs,
        recommended_jobs=recommended_jobs,
        contribution_dict=contribution_dict,
        taken_courses_set=taken_courses_set, 
        current_user=current_user
    )

@app.route('/profile')
def profile():
    user_result = connection.execute(text("SELECT * FROM Users WHERE uid = :uid"), {"uid": user_id})
    user = user_result.fetchone()

    matches = connection.execute(text("""
    SELECT Users.name, Users.email
    FROM Match
    JOIN Users ON Users.uid = Match.uid2
    WHERE Match.uid1 = :uid;
    """), {"uid": user_id}).fetchall()

    current_user = connection.execute(text("SELECT name FROM Users WHERE uid = :uid"), {"uid": user_id}).fetchone()

    return render_template('profile.html', user=user, matches=matches, current_user=current_user)

@app.route('/course_details', methods=['GET'])
def course_details():
    cid = request.args.get('cid', '')
    
    course = connection.execute(
        text("SELECT * FROM courses WHERE cid = :cid"),
        {'cid': cid}
    ).fetchone()

    comments = connection.execute(
        text("SELECT * FROM comment WHERE cid = :cid"),
        {'cid': cid}
    ).fetchall()

    grade_result = connection.execute(
        text("""
SELECT 
    SUM(CASE WHEN score >= 90 THEN 1 ELSE 0 END) AS A,
    SUM(CASE WHEN score >= 75 AND score < 90 THEN 1 ELSE 0 END) AS B,
    SUM(CASE WHEN score >= 60 AND score < 75 THEN 1 ELSE 0 END) AS C,
    SUM(CASE WHEN score >= 40 AND score < 60 THEN 1 ELSE 0 END) AS D,
    SUM(CASE WHEN score < 40 THEN 1 ELSE 0 END) AS F
FROM Take JOIN Have_Slots ON Take.sid = Have_Slots.sid
WHERE Have_Slots.cid = :cid;
"""),
        {'cid': cid}
    )
    grades = grade_result.fetchall()
    ss = "ABCDF"
    grade_distribution = []
    for i in range(5):
        grade_distribution.append({"lv": ss[i], "count": grades[0][i]})

    slots = connection.execute(
        text("""SELECT * FROM Have_Slots WHERE cid = :cid;"""),
        {'cid': cid}
    ).fetchall()

    return render_template('course_details.html', course=course, comments=comments, grade_distribution=grade_distribution, slots=slots)

if __name__ == '__main__':
    user_id = 'pw2629'

    app.run(debug=True)