# -*- coding: utf-8 -*-
from __future__ import print_function
import os
import smtplib
import zipfile
import shutil
import pickle
from dotenv import load_dotenv
from util.Cloud import s3_send
from email.mime.text import MIMEText
from application import celery
from marker.MarkExercise import check_functions, check_console
from util.sesEmail import Email
from models.models import Result
load_dotenv(".env")
ARUP_SMTP_SERVER = os.environ.get('ARUP_SMTP_SERVER')


def copy(src, dest):
    try:
        shutil.copytree(src, dest)
    except OSError as e:
        shutil.copy(src, dest)


def del_files_in_dir(folder):
    for the_file in os.listdir(folder):
        file_path = os.path.join(folder, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(e)


def email_content(recipient, question, url):
    return """<html>
                <head></head>
                <body>
                  <p>Hey {0},</p>
                  <p>Learning to program takes time but what you put in now will save you time in the long run.
                  why not try your hand at {1}
                  <a href="{3}">here!</a></p>
                  <p>Happy Coding,</p>
                  <p>Lunchtime Python Team</p>
                </body>
              </html>""".format(recipient, question, url)


def send_aws_email(recipient, email, question, url):
    """send email using SES, need to update so it can send to anyone"""
    content = email_content(recipient, question, url)
    email = Email(to=email, subject='Its been a while...')
    email.text(content)
    email.html(content)
    email.send()


def send_reminder_email(recipient, email, question, url):
    """send email from within arup"""
    server = smtplib.SMTP(ARUP_SMTP_SERVER)
    content = email_content(recipient, question, url)

    # Create a text/plain message
    msg = MIMEText(content.encode('ascii', 'replace'), 'html', 'ascii')
    msg['Subject'] = 'Its been a while...'
    msg['From'] = email
    msg['To'] = email
    # Send the message via our own SMTP server
    server.sendmail(email, email, msg.as_string())
    server.quit()


@celery.task(bind=True, name='celery_tasks.check_function_task')
def check_function_task(self, file_path, user_id, q_id, function_name, args, answers, timeout):
    """task that will check a submission"""
    import application as mb
    db, _ = mb.run_setup()
    results = []
    total = len(args)
    status = 'Unsucessful'
    sub_result = Result(int(user_id), q_id, False)
    for i, arg in enumerate(args):
        results.append(check_functions(file_path,
                                       function_name,
                                       arg,
                                       answers[i],
                                       timeout))

        self.update_state(state='PROGRESS',
                          meta={'current': i,
                                'total': total,
                                'status': 'hold on m8!'})

    if all([x['result'] for x in results]):
        status = 'Successful!'
        sub_result = Result(int(user_id), q_id, True)

    db.session.add(sub_result)
    db.session.commit()

    return {'question_name': function_name,
            'current': i,
            'q_id': q_id,
            'total': total,
            'status': status,
            'result': results
            }

# @celery.task(name='celery_tasks.check_console_task')
# def check_console_task(test_file, q_id):
#     """task that will run python in a separate process and parse stdout"""
#     # query DB for question and get info required
#     q_name = ''
#     answers = 42
#     return check_console(test_file, q_name, answers)


# @celery.task(name='celery_tasks.spam_users')
# def spam_users(file_path, function_name, q_id, answers):
#     # hassle users that have stopped logging in and completing questions...?
#     # could check for last attempt in results table if its been over 
#     # 2 weeks send them an email saying we miss you try this question
#     # send_reminder_emailp(recipient, email, question, url)
#     pass

# @celery.task(name='celery_tasks.clean_up')
# def clean_up(file_path, function_name, q_id, answers):
#     """task that will clean up uploads directory, run once a day?"""
#     pass


# @celery.task(name='celery_tasks.check_question_set')
# def check_question_set(file_path, function_name, q_id, answers):
#     """task that will check for new questions"""
#     pass