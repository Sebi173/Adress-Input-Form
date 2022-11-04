from flask import Blueprint, render_template, request, redirect, url_for
import xml.etree.ElementTree as ET
import psycopg2

'''
We will handle 3 different tasks in this script:
    1. Defining two views in /home and /upload.
    2. Requesting and Checking the Input data from the user, giving Feedback if needed.
    3. Writing the Input data into our database
'''


views = Blueprint(__name__, 'views')

fields = [{'id': 'fname', 'text': "First Name"}, {'id': 'lname', 'text': 'Last Name'}, {
    'id': 'address', 'text': 'Address'}, {'id': 'email', 'text': 'Email'}, {'id': 'phoneNumber', 'text': 'Phone Number'}]


def check_email(user_email):
    '''This function checks whether the email is legit'''
    if '@' not in user_email:
        return 'There must be a @ in your email address'
    elif '.' not in user_email.split('@')[1]:
        return 'There must be a . after the @'
    elif user_email[-1] == '.':
        return 'The email must not end on a .'

    return ''


def check_if_populated(user_input_data, user_feedback):
    '''This function checks whether the user gave his input in all fields'''
    for field in fields:
        if user_input_data.get(field['id']) == '':
            user_feedback[field['id']] = 'This field must be populated'

    return user_feedback


@views.route('/')
def base():
    return redirect(url_for('views.home'))


@views.route('/home', methods=['GET', 'POST'])
def home():
    '''This is the route, where the user may input his data manually'''
    user_input_data = ''
    user_feedback = {}
    message_to_user = 'Please fill in all the Boxes'

    if request.method == "POST":
        user_input_data = request.form
        user_email = user_input_data.get('email')

        # Gathering Feedback for the user
        feedback_email = check_email(user_email)
        if feedback_email != '':
            user_feedback['email'] = feedback_email
        user_feedback = check_if_populated(user_input_data, user_feedback)

        if user_feedback == {}:  # If there is no user feedback, we may try to upload the Input data into the database

            try:
                connection = psycopg2.connect(user="postgres",
                                              password="Test123",
                                              host="127.0.0.1",
                                              port="5432",
                                              database="exercise")
                cursor = connection.cursor()

                postgres_insert_query = """ INSERT INTO contact (first_name, last_name, address, email, phone_number) VALUES (%s,%s,%s,%s,%s)"""
                record_to_insert = (user_input_data.get('fname'), user_input_data.get('lname'), user_input_data.get(
                    'address'), user_input_data.get('email'), user_input_data.get('phoneNumber'))
                cursor.execute(postgres_insert_query, record_to_insert)
                connection.commit()
                count = cursor.rowcount
                message_to_user = 'Thank you for your Information! We have received your Data!'
                print(count, "Record inserted successfully into contact table")

            except (Exception, psycopg2.Error) as error:
                message_to_user = 'Unfortunately your file was not received by the database. Please contact an administrator'
                print("Failed to insert record into contact table", error)

            finally:  # closing database connection.

                if connection:
                    cursor.close()
                    connection.close()
                    print("PostgreSQL connection is closed")

    return render_template("index.html", data=user_input_data, user_feedback=user_feedback, fields=fields, message_to_user=message_to_user)


@views.route("/upload", methods=["GET", "POST"])
def upload():
    '''This is the route for the mass upload'''
    user_feedback = []
    user_input_data = []
    message_to_user = ''

    if request.method == 'POST':

        # Parsing the XML file
        file = request.files['file']
        tree = ET.parse(file)
        root = tree.getroot()

        # Looping over all texts and tags from the XML file
        for element in root:

            # Will be used to gather the information of each contact as a tuple
            user_input_data_row = ()

            for row, subelement in enumerate(element):

                user_feedback_error = {}  # Will be used to gather every feedback per tag and row

                if subelement.tag == 'email':
                    feedback_email = check_email(subelement.text)

                    if feedback_email != '':
                        user_feedback_error['tag'] = 'email'
                        user_feedback_error['row'] = str(row)
                        user_feedback_error['message'] = feedback_email

                if subelement.text == None:
                    user_feedback_error['tag'] = subelement.tag
                    user_feedback_error['row'] = str(row)
                    user_feedback_error['message'] = 'This field must be populated'

                user_input_data_row += (subelement.text,)

                if user_feedback_error != {}:
                    user_feedback.append(user_feedback_error)

            # Make a list of tuples with the information of every contact as the tuples
            user_input_data.append(user_input_data_row)

        if user_feedback == []:

            try:
                connection = psycopg2.connect(user="postgres",
                                              password="Test123",
                                              host="127.0.0.1",
                                              port="5432",
                                              database="exercise")
                cursor = connection.cursor()

                args = ','.join(cursor.mogrify("(%s,%s,%s,%s,%s)", user_input_data_row).decode('utf-8')
                                for user_input_data_row in user_input_data)

                cursor.execute(
                    "INSERT INTO contact (first_name, last_name, address, email, phone_number) VALUES " + (args))
                connection.commit()
                count = cursor.rowcount
                message_to_user = 'Thank you for uploading your file. We have received the data.'
                print(count, "Record inserted successfully into contact table")

            except (Exception, psycopg2.Error) as error:
                message_to_user = 'Unfortunately your file was not received by the database. Please contact an administrator'
                print("Failed to insert record into contact table", error)

            finally:
                # closing database connection.
                if connection:
                    cursor.close()
                    connection.close()
                    print("PostgreSQL connection is closed")

        return render_template("upload.html", message_to_user=message_to_user, user_feedback=user_feedback)

    return render_template("upload.html", message_to_user=message_to_user, user_feedback=user_feedback)
