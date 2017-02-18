#!/usr/bin/python3
# -*- coding: utf-8 -*-
import mailbox
import os
import email
import sqlite3 as lite
from email.utils import parsedate

cwd = os.path.dirname(os.path.realpath('MBOX Dir'))
conn = None
cur = None
mbox_path = cwd 
mbox_files = []

conn = lite.connect(cwd + '/mails.db')
cur = conn.cursor()    
cur.execute("DROP TABLE IF EXISTS emails")    
cur.execute("CREATE TABLE emails(id INTEGER PRIMARY KEY, sender_name TEXT, sender_email TEXT, recipient_name TEXT, recipient_email TEXT, subject TEXT, message_date TEXT, message_id TEXT, text_body TEXT)")

def extract_date(email):
    date = email.get('Date')
    a = parsedate(date)
    return a

def getcharsets(msg):
    charsets = set({})
    for c in msg.get_charsets():
        if c is not None:
            charsets.update([c])
    return charsets

def handleerror(errmsg, emailmsg,cs):
    print()
    print(errmsg)
    print("This error occurred while decoding with ",cs," charset.")
    print("These charsets were found in the one email.",getcharsets(emailmsg))
    print("This is the subject:",emailmsg['subject'])
    print("This is the sender:",emailmsg['From'])
    print("Message-ID:",emailmsg['Message-ID'])


def getbodyfromemail(msg):
    body = None
    if msg.is_multipart():    
        for part in msg.walk():
            if part.is_multipart(): 
                for subpart in part.walk():
                    if subpart.get_content_type() == 'text/plain':
                        body = subpart.get_payload(decode=True) 
            elif part.get_content_type() == 'text/plain':
                body = part.get_payload(decode=True)
    elif msg.get_content_type() == 'text/plain':
        body = msg.get_payload(decode=True) 
    for charset in getcharsets(msg):
        try:
            body = body.decode(charset)
        except UnicodeDecodeError:
            handleerror("UnicodeDecodeError: encountered.",msg,charset)
        except AttributeError:
            handleerror("AttributeError: encountered" ,msg,charset)
    return body    


def name_email(s):
    if not s:
        return None, None
    pieces = s.split('<')
    if len(pieces) > 1:
        name = pieces[0].replace('"','').strip()
        email = pieces[1].replace('>','')
    else:
        name = None
        email = pieces[0].replace('>','')
    return name,email

def extract_entity_names(t):
    entity_names = []
    if hasattr(t, 'label') and t.label:
        if t.label() == 'NE':
            entity_names.append(' '.join([child[0] for child in t]))
        else:
            for child in t:
                entity_names.extend(extract_entity_names(child))

    return entity_names
 
def main():
    for root, dirs, files in os.walk(mbox_path):
        print(dirs)
        for filename in files:
            mbox_files.append((filename, os.path.join(root, filename)))
    for mbox_file in mbox_files:
        src_mbox = mailbox.mbox(mbox_file[1])
        sorted_mails = sorted(src_mbox, key=extract_date, reverse=True)
        src_mbox.update(enumerate(sorted_mails))
        src_mbox.flush()
        for message in src_mbox:
            sender = name_email(message['From'])
            recipient = name_email(message['To'])
            subject = message['subject']
            date = message['Date']
            messageId = message['Message-ID']
            text_body = getbodyfromemail(message)
            row = [None,sender[0],sender[1],recipient[0],recipient[1],subject,date,messageId,text_body]
            cur.execute("INSERT INTO emails VALUES(?,?,?,?,?,?,?,?,?);", row)
    conn.commit()
    conn.close()

main()
