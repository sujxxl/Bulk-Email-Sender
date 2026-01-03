import smtplib
import ssl
import csv
import io
import time
from flask import Flask, render_template, request, jsonify, send_from_directory
from datetime import datetime

app = Flask(__name__, template_folder='.')


@app.route('/public/<path:filename>')
def public_file(filename):
    return send_from_directory('public', filename)

@app.route('/')
def index():
    return render_template('index.html', year=datetime.now().year)

@app.route('/test', methods=['POST'])
def test_connection():
    data = request.json
    server = data['server']
    port = int(data['port'])
    email = data['email']
    password = data['password']
    sender_name = data.get('senderName', '')
    context = ssl.create_default_context()
    timeout_seconds = 30
    try:
        if port == 465:
            with smtplib.SMTP_SSL(server, port, context=context, timeout=timeout_seconds) as s:
                s.login(email, password)
        elif port == 587:
            with smtplib.SMTP(server, port, timeout=timeout_seconds) as s:
                s.starttls(context=context)
                s.login(email, password)
        else:
            return jsonify({'success': False, 'message': f'Unsupported port: {port}. Use 465 or 587.'})
        sender_email = email
        receiver_email = email
        from_display = f"{sender_name} <{email}>" if sender_name else email
        message = f"From: {from_display}\r\n"
        message += f"To: {receiver_email}\r\n"
        message += f"Subject: SMTP Test Successful\r\n\r\n"
        message += f"This is a test message from the Cold Mailer 3000. Your connection to {server} is working perfectly."
        if port == 465:
            with smtplib.SMTP_SSL(server, port, context=context, timeout=timeout_seconds) as s:
                s.login(email, password)
                s.sendmail(sender_email, receiver_email, message.encode('utf-8'))
        else:
            with smtplib.SMTP(server, port, timeout=timeout_seconds) as s:
                s.starttls(context=context)
                s.login(email, password)
                s.sendmail(sender_email, receiver_email, message.encode('utf-8'))
        return jsonify({'success': True, 'message': f'Connection to {server} successful! A test email was sent to {email}.'})
    except smtplib.SMTPAuthenticationError:
        return jsonify({'success': False, 'message': 'Authentication failed. Please check your email and password. Make sure you are using the correct password (for GoDaddy, it is your regular password).'})
    except smtplib.SMTPException as e:
        return jsonify({'success': False, 'message': f'SMTP Error: {str(e)}'})
    except Exception as e:
        if 'Operation timed out' in str(e) or 'timeout' in str(e).lower():
            return jsonify({'success': False, 'message': 'Connection Timed Out. This is common. \n\n1. Check your internet connection. \n2. Try switching to Port 587 (if you are on 465) or 465 (if you are on 587). \n3. A firewall might be blocking the connection.'})
        return jsonify({'success': False, 'message': f'An unexpected error occurred: {str(e)}'})

@app.route('/send', methods=['POST'])
def send_emails():
    data = request.form
    file = request.files['file']
    server = data['server']
    port = int(data['port'])
    email = data['email']
    password = data['password']
    sender_name_template = data.get('senderName', '')
    subject_template = data['subject']
    body_template = data['body']
    if not file:
        return jsonify({'success': False, 'message': 'No file uploaded.'})
    try:
        stream = io.StringIO(file.stream.read().decode("UTF-8"), newline=None)
        csv_reader = csv.DictReader(stream)
        contacts = list(csv_reader)
        if 'email' not in csv_reader.fieldnames:
             return jsonify({'success': False, 'message': 'CSV file must have an "email" column.'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error reading CSV: {str(e)}'})
    results = []
    context = ssl.create_default_context()
    timeout_seconds = 30 
    try:
        with (smtplib.SMTP_SSL(server, port, context=context, timeout=timeout_seconds) if port == 465 else smtplib.SMTP(server, port, timeout=timeout_seconds)) as s:
            if port == 587:
                s.starttls(context=context)
            s.login(email, password)
            print(f'Successfully logged into {server}. Starting to send {len(contacts)} emails...')
            for contact in contacts:
                receiver_email = contact['email']
                try:
                    personalized_subject = subject_template.format(**contact)
                    personalized_body = body_template.format(**contact)
                    normalized_body = personalized_body.replace('\r\n', '\n').replace('\n', '\r\n')
                    personalized_sender_name = sender_name_template.format(**contact)
                    message = f"From: {personalized_sender_name} <{email}>\r\n"
                    message += f"To: {receiver_email}\r\n"
                    message += f"Subject: {personalized_subject}\r\n\r\n"
                    message += normalized_body
                    s.sendmail(email, receiver_email, message.encode('utf-8'))
                    results.append({'status': 'success', 'email': receiver_email})
                except KeyError as e:
                    results.append({'status': 'fail', 'email': receiver_email, 'error': f'Missing CSV column: {str(e)}'})
                except Exception as e:
                    results.append({'status': 'fail', 'email': receiver_email, 'error': str(e)})
                time.sleep(2)
        return jsonify({'success': True, 'message': f'Sending complete. Processed {len(contacts)} emails.', 'results': results})
    except smtplib.SMTPAuthenticationError:
        return jsonify({'success': False, 'message': 'Authentication failed. Please check your SMTP settings.'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'An error occurred during sending: {str(e)}'})

if __name__ == '__main__':
    print("--- Starting the Mailer Web App ---")
    print("To use, open this link in your browser: http://127.0.0.1:5001")
    print("To stop, press CTRL+C in this terminal.")
    app.run(host='0.0.0.0', port=5001, debug=True)