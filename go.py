import smtplib
import dns.resolver
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import time

# Setup logging to both file and console
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("logs.txt"),
                        logging.StreamHandler()
                    ])

# Function to get MX records for a domain
def get_mx_records(domain):
    try:
        records = dns.resolver.resolve(domain, 'MX')
        mx_records = sorted(records, key=lambda record: record.preference)
        return [str(record.exchange) for record in mx_records]
    except Exception as e:
        logging.error(f"Failed to retrieve MX records for {domain}: {e}")
        return []

# Function to send email via MX record with BCC
def send_email_via_mx(to_emails, from_email, from_name, subject, html_body):
    if not to_emails:
        return

    # Extract domain from the first email (assuming all emails are from the same domain)
    domain = to_emails[0].split('@')[1]
    mx_records = get_mx_records(domain)

    if not mx_records:
        logging.error(f"No MX records found for {domain}. Skipping batch.")
        return

    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = f"{from_name} <{from_email}>"
    msg['To'] = from_email  # To field can be any valid email address
    msg['Bcc'] = ', '.join(to_emails)
    msg.attach(MIMEText(html_body, 'html'))

    for mx in mx_records:
        try:
            with smtplib.SMTP(mx) as server:
                # Set an explicit HELO hostname (replace 'yourhostname.com' with your actual hostname)
                server.helo("yourhostname.com")  
                server.sendmail(from_email, to_emails, msg.as_string())
                logging.info(f"Batch of {len(to_emails)} emails sent successfully via {mx}")
                return  # Stop after first successful send
        except smtplib.SMTPHeloError:
            logging.error(f"HELO command rejected by {mx}. Trying next MX server.")
        except Exception as e:
            logging.error(f"Failed to send batch of {len(to_emails)} emails via {mx}: {e}")

# Function to read email list from a file
def read_email_list(file_path):
    try:
        with open(file_path, 'r') as file:
            emails = [line.strip() for line in file if line.strip()]
        return emails
    except Exception as e:
        logging.error(f"Error reading email list from {file_path}: {e}")
        return []

# Function to batch the email list
def batch_email_list(email_list, batch_size):
    for i in range(0, len(email_list), batch_size):
        yield email_list[i:i + batch_size]

# Function to read HTML content from a file
def read_html_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        logging.error(f"Error reading HTML content from {file_path}: {e}")
        return ""

# Email details
from_email = "asawards@gmail.com"
from_name = "dsfsdf"
subject = "sdfsdfsdfsdf"

# Read HTML content from file
html_body = read_html_file('letter.html')

# Read email list from file
email_list = read_email_list('mails.txt')

# Send email in batches of 100
batch_size = 100
batches = list(batch_email_list(email_list, batch_size))

# Use ThreadPoolExecutor to send emails concurrently
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = []
    for batch in batches:
        futures.append(executor.submit(send_email_via_mx, batch, from_email, from_name, subject, html_body))
        time.sleep(3)  # Sleep for 3 seconds between sending each batch

    for future in as_completed(futures):
        try:
            future.result()
        except Exception as exc:
            logging.error(f"Batch generated an exception: {exc}")
