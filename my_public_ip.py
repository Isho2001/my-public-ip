#author: Isha Yokh

import subprocess
import sys
import argparse
import time
import smtplib
from email.message import EmailMessage
import sqlite3
import socket


#database class that will used to interact with the local database
class Database:
    #constructor initialises database name and creates database connection and cursor
    def __init__(self, db_name):
        self.db_name = db_name
        self.sql_connection = sqlite3.connect(db_name)
        self.cursor = self.sql_connection.cursor()

    #sends commands to the local database - no return
    def send_command(self, command="", **close_db):
        self.cursor.execute(command)
        self.sql_connection.commit()

        if close_db == True:
            self.sql_connection.close()

    #sends query to the local database and returns query output
    def send_query(self, query="", **close_db):
        query_return = self.cursor.execute(query)
        query_return = query_return.fetchall()
        self.sql_connection.commit()

        if close_db == True:
            self.sql_connection.close()

        return query_return


#takes command line arguments
def take_args():
    argparser = argparse.ArgumentParser(description=""" [Example 1]: python my_public_ip.py --re ExampleReceiverEmail@ExampleDomain.com --o windows --se ExampleSenderEmail2@gmail.com --pw ExampleSenderPassword --t 24\n
                                                     [Example 2]: python3 my_public_ip.py --re ExampleReceiverEmail@ExampleDomain.com --o linux --se ExampleSenderEmail2@gmail.com --pw ExampleSenderPassword --t 24 """)
    argparser.add_argument("--re", "--receiver_email", help="Email that the IP address will be sent to", required=True)
    argparser.add_argument("--o", "--os", help="OS to be specified so the accurate command can get executed (Available options: Windows/Linux)", required=True)
    argparser.add_argument("--se", "--sender_email", help="Email address that will be used to send the results (Less secure apps must be enabled on your account)", required=True)
    argparser.add_argument("--pw", "--sender_password", help="Email password that will be used to login to the sender's email (Will appear in plain text on this terminal)", required=True)
    argparser.add_argument("--t", "--time", help="Wait time until IP address is obtained and sent again (time should be in hours)", required=False)
    args =  argparser.parse_args()

    return args

#contains main control flow and calls other functions
def main():
    args = take_args()

    print("[!] Connecting to local Database")
    database = Database("IP_addresses.db")

    os_commands = {"windows":"nslookup myip.opendns.com. resolver1.opendns.com", \
    "linux":"dig +short myip.opendns.com @resolver1.opendns.com"}
    email_message = """ Public IP address for today: """

    command = validate_os(args.o, os_commands)

    if command == False:
        print("[!] Operating System couldn't be verified - run my_public_ip.py --help for more info")
        sys.exit(0)

    try:
        print("[!] Obtaining IP address")
        output = execute_command(command)
    except:
        print("[!] Command couldn't be run - check your internet connection and run my_public_ip.py --help")
        sys.exit(0)
    
    ip_address, error = validate_and_parse_ip_from_output(output, args.o)

    try:
        int(ip_address.replace(".", ""))
    except ValueError:
        print("[X] IP address format is incorrect - check your internet connection, validate the arguments and make sure you have selected the right OS - run my_public_ip.py --help")
        sys.exit(0)

    if error:
        print(error)
        sys.exit(0)

    else:
        print("[!] Public IP address: {0}".format(ip_address))

    try:
        database.send_command(""" CREATE TABLE ip_addresses 
                                          (ip_address string) """, close_db=False)
    except sqlite3.OperationalError:
        pass
    
    print("[!] Validating IP address in the database")
    query_return = database.send_query(""" SELECT ip_address FROM ip_addresses WHERE ip_address = "{ip_address}" """.format(ip_address=ip_address), close_db=True)
    check_output_and_database(query_return, ip_address, args, email_message)


#checks query return to decide whether to avoid the sending the result as the IP address is already stored in the database and vice versa
def check_output_and_database(query_return, ip_address, args, email_message):
    email_message += ip_address
    database = Database("IP_addresses.db")
    
    if len(query_return) == 0 and not args.t:

        print("[!] Adding result to database and sending email to {0}".format(args.re))
        error = send_email(args.se, args.pw, args.re, email_message)

        if error:
            print(error)
            sys.exit(0)

        database.send_command(""" INSERT INTO ip_addresses (ip_address) VALUES ("{ip_address}") """.format(ip_address=ip_address), close_db=True)
        
    
    elif args.t and len(query_return) > 0:
        print("[!] IP address is already in the database - waiting until next run in {0} hours\n".format(str(args.t)))
        while True:
            time.sleep(float(args.t)*3600)
            main()
        

    elif len(query_return) == 0 and args.t:
        print("[!] Adding result to database and sending email to {0}".format(args.re))
        error = send_email(args.se, args.pw, args.re, email_message)

        if error:
            print(error)
            sys.exit(0)

        database.send_command(""" INSERT INTO ip_addresses (ip_address) VALUES ("{ip_address}") """.format(ip_address=ip_address), close_db=True)
        print("[!] Waiting until next run in {0} hours\n".format(str(args.t)))
        while True:
            time.sleep(float(args.t)*3600)
            main()

    else:
        print("[!] IP address is already in the database - Exiting.")
        sys.exit(0)


#validates the os based on the user input and returns the accurate command to be executed
def validate_os(os, os_commands):
    command = ""

    for key in os_commands:
        if key == os.lower():
            command = os_commands.get(key)
            break
    
    return command


#executes ns lookup command locally to get the public ip address
def execute_command(command):
    output = subprocess.run(command, shell=True, capture_output=True)
    output = output.stdout.decode()

    return output


#parses the necessary info from output of the command that's executed locally
def validate_and_parse_ip_from_output(output, os):
    altered_output = ""
    error = "[X] Error with command output - check your DNS or internet connection"

    if os.lower() == "windows":
        if output.split()[0] == "Server:" and output.split()[1] == "UnKnown":
            pass
        else:
            altered_output = output.split()[7]
            error = ""

    elif os.lower() == "linux":
        if len(output) == 0:
            pass
        else:
            altered_output = output
            error = ""

    else:
        altered_output = False

    return altered_output, error


#creates message and sends email using free gmail SMTP service
def send_email(from_email, from_password, to_email, message):
    msg = EmailMessage()
    error = ""
    
    msg["Subject"] = "My public IP address for today"
    msg["From"] = from_email
    msg["To"] = to_email
    msg.set_content(message)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            try:
                smtp.login(from_email, from_password)
                smtp.send_message(msg)
            except smtplib.SMTPAuthenticationError:
                error = "[X] Error sending email - check receiver email or sender email and password\n\t \
                         [!] Make sure less secure apps is enabled on the sender email\n\t \
                         [!] Make sure you haven't been blocked"
            
    except socket.gaierror:
        error = "[X] Error sending email - check your internet connection"
    

    return error


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("[!] Program interrupted by user - Exiting")
        sys.exit(0)
        
#author: Isha Yokh
