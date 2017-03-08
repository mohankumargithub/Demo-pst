#!/usr/bin/python3
# -*- coding: utf-8 -*-
import csv
import mailbox
import os
import sqlite3 as lite
import re
import nltk
import uuid
import string
import enchant
import sys
import fnmatch
import logging.config
import json
from nltk import pos_tag
from nltk.tree import Tree
from nltk.chunk import conlltags2tree
from email.utils import parsedate
from nltk.tag import StanfordNERTagger
from nltk.tokenize import word_tokenize
from collections import OrderedDict

file_path = 'SOURCE_DIR'
filename, file_extension = os.path.splitext(file_path)
dir_path = os.path.dirname(os.path.realpath(__file__))
mbox_path = os.path.dirname(os.path.realpath(file_path))

connection = None
cur = None
dest_mbox = None
stop_words = None# set(file.read().splitlines())

uniquePhoneNumbers = set({})
count = 1
d = enchant.Dict("en_US")
st = StanfordNERTagger(
    'english.muc.7class.distsim.crf.ser.gz', encoding='utf-8')
emailRegex = re.compile(("([a-z0-9!#$%&'*+\/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+\/=?^_`"
                         "{|}~-]+)*(@|\sat\s)(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(\.|"
                         "\sdot\s))+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)"))

phoneNumberRegex = re.compile(
    '(\d\.?|\+\d\.?)?\(?\d{3}(\.| |-|\))\d{3}(\.| |-)\d{4}')
tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')

rep = None
logger = None


def setup_logging(default_path='logging.json', default_level=logging.INFO, env_key='LOG_CFG'):
    '''
        Set-up for logger files.Configuration loaded from default_path and default_level.
    '''
    global logger
    path = default_path
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = json.load(f)
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)
    logger = logging.getLogger('MyLogger')


def bio_tagger(ne_tagged):
    bio_tagged = []
    prev_tag = "O"
    for token, tag in ne_tagged:
        if tag == "O":  # O
            bio_tagged.append((token, tag))
            prev_tag = tag
            continue
        if tag != "O" and prev_tag == "O":  # Begin NE
            bio_tagged.append((token, "B-" + tag))
            prev_tag = tag
        elif prev_tag != "O" and prev_tag == tag:  # Inside NE
            bio_tagged.append((token, "I-" + tag))
            prev_tag = tag
        elif prev_tag != "O" and prev_tag != tag:  # Adjacent NE
            bio_tagged.append((token, "B-" + tag))
            prev_tag = tag
    return bio_tagged


def stanford_tree(bio_tagged):
    tokens, ne_tags = zip(*bio_tagged)
    pos_tags = [pos for token, pos in pos_tag(tokens)]
    conlltags = [(token, pos, ne)
                 for token, pos, ne in zip(tokens, pos_tags, ne_tags)]
    ne_tree = conlltags2tree(conlltags)
    return ne_tree


def structure_ne(ne_tree):
    ne = []
    for subtree in ne_tree:
        # If subtree is a noun chunk, i.e. NE != "O"
        if isinstance(subtree, Tree):
            ne_label = subtree.label()
            ne_string = " ".join([token for token, pos in subtree.leaves()])
            ne.append((ne_string, ne_label))
    return ne


def get_files_from_dir():
    '''
        Get all mbox file from directory
    '''
    mbox_files = []
    pattern = '*.mbox'
    for root, dirs, files in os.walk(mbox_path):
        for filename in fnmatch.filter(files, pattern):
            mbox_files.append((filename, os.path.join(root, filename)))
    return mbox_files


def create_output_mbox():
    '''
        Create MBOX Destination file.
    '''
    global dest_mbox, filename, file_extension
    output_file_name = filename + "_out"
    logger.info("remove file :: " + output_file_name +
                " :: " + str(remove_file(output_file_name)))
    logger.info("remove file :: " + output_file_name +
                " :: " + str(remove_file(output_file_name + '.lock')))
    dest_mbox = mailbox.mbox(output_file_name)


def load_stop_words():
    '''
        Load stop word's from text file
    '''
    global stop_words
    try:
        file = open(dir_path + "/stop-word-list.txt", "r")
        stop_words = set(file.read().splitlines())
    except OSError as err:
        logging.debug("Error on load stop word list :: ".format(err))
        sys.exit(1)


def define_db_connection():
    '''
        Establish SQL lite Connection 
    '''
    global connection
    global cur
    try:
        connection = lite.connect(mbox_path + '/mails.db')
        cur = connection.cursor()
        cur.execute('SELECT SQLITE_VERSION()')
        data = cur.fetchone()
        logging.info("SQLite version: %s" % data)
    except lite.Error as e:
        logging.info("Error %s:" .format(e))
        sys.exit(1)


def create_tables():
    '''
        Create table's in sqlite
    '''
    global cur
    try:
        cur.execute("DROP TABLE IF EXISTS emails")
        cur.execute(
            "CREATE TABLE emails(id INTEGER PRIMARY KEY, sender_name TEXT, sender_email TEXT, recipient_name TEXT, recipient_email TEXT, subject TEXT, message_date TEXT, message_id TEXT, text_body TEXT)")
        cur.execute('DROP TABLE IF EXISTS masking')
        cur.execute(
            'CREATE TABLE masking(id INTEGER PRIMARY KEY, original_text TEXT, replace_text TEXT, type TEXT, CONSTRAINT name_unique UNIQUE (original_text))')
        cur.execute('DROP TABLE IF EXISTS sentences')
        cur.execute(
            'CREATE TABLE sentences(id TEXT PRIMARY KEY, email_id INTEGER, sentence_text TEXT)')
        cur.execute(
            'CREATE INDEX index_email_id ON sentences (email_id)')
        cur.execute('DROP TABLE IF EXISTS nouns')
        cur.execute(
            'CREATE TABLE nouns(id TEXT PRIMARY KEY, sentence_id TEXT, email_id INTEGER, noun_text TEXT, noun_type Text)')
        cur.execute(
            'CREATE INDEX index_noun_email_id ON nouns (email_id)')
        cur.execute(
            'CREATE INDEX index_sentence_id ON nouns (sentence_id)')
        cur.execute('SELECT * FROM emails')
    except lite.Error as e:
        logging.error("Error %s:" .format(e))
        sys.exit(1)


def remove_file(filePath):
    '''
        Remove file in  directory
    '''
    if os.path.exists(filePath):
        try:
            os.remove(filePath)
            return True
        except OSError as e:
            logging.error("Error: %s - %s." % (e.filename, e.strerror))
    return False


def increment():
    '''
        Global variable increment count
    '''
    global count
    count = count + 1


def get_emails(s):
    '''
    Returns an iterator of matched emails found in string s.
    Removing lines that start with '//' because the regular expression
    mistakenly matches patterns like 'http://foo@bar.com' as '//foo@bar.com'.
    '''
    return set(email[0]
               for email in re.findall(emailRegex, s) if not email[0].startswith('//'))


def loadnoun():
    cur.execute('SELECT original_text FROM masking')
    data = cur.fetchall()
    return set(elt[0] for elt in data)


def get_phoneNumbers(s):
    '''
    (123)456-7890
    123.456.7890
    123 456 7890
    91(123)456-7890
    1(123)456.7890
    2.123.456.7890
    +(123)456-7890 is false
    +1.234.567.8790
    +1-929-432-4463
    8695067338
    91-9486540283
    044-43033536
    +91 - 9715140860
    '''
    phoneNumbers = set(phone for phone in re.findall(phoneNumberRegex, s))
    uniquePhoneNumbers.update(phoneNumbers)
    return phoneNumbers


def extract_entity_names(t):
    entity_names = []
    if hasattr(t, 'label') and t.label:
        if t.label() == 'NE':
            entity_names.append(' '.join([child[0] for child in t]))
        else:
            for child in t:
                entity_names.extend(extract_entity_names(child))

    return entity_names


def save_sentence(phrase, email_id):
    sentence_id = str(uuid.uuid4())
    sentence_row = [
        sentence_id,
        email_id,
        phrase
    ]
    cur.execute('INSERT INTO sentences VALUES(?,?,?);', sentence_row)
    return sentence_id


def save_nouns(sentence_id, noun, email_id):
    noun_id = str(uuid.uuid4())
    noun_row = [
        noun_id,
        sentence_id,
        email_id,
        noun[0],
        noun[1]
    ]
    cur.execute('INSERT INTO nouns VALUES(?,?,?,?,?);', noun_row)

# Process text


def process_text(txt_file):
    token_text = word_tokenize(txt_file)
    token_text = filter(lambda x: x not in string.punctuation, token_text)
    token_text = [w for w in token_text if not w.lower() in stop_words]
    token_text = [w for w in token_text if not d.check(w)]
    return token_text

def stanford_tagger(token_text):
    st = StanfordNERTagger(
        'english.muc.7class.distsim.crf.ser.gz', encoding='utf-8')
    ne_tagged = st.tag(token_text)
    return(ne_tagged)


def stanford_main(txt_file):
    return stanford_tagger(process_text(txt_file))


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


def handleerror(errmsg, emailmsg, cs):
    logging.error(
        "This error occurred while decoding with " + str(cs) + " charset.")
    logging.error(
        "These charsets were found in the one email." + str(getcharsets(emailmsg)))
    logging.error("Message-ID:" + str(emailmsg['Message-ID']))


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
            handleerror("UnicodeDecodeError: encountered.", msg, charset)
        except AttributeError:
            handleerror("AttributeError: encountered", msg, charset)
    return body


def setbodytoemail(message):
    load_masking()
    if 'From' in message:
        fromStr = message['From'].encode('utf-8')
        fromStr = multireplace(fromStr, rep)
        del message['From']
        message['From'] = fromStr.decode('utf-8')
    if 'To' in message:
        toStr = message['To'].encode('utf-8')
        toStr = multireplace(toStr, rep)
        del message['To']
        message['To'] = toStr.decode('utf-8')
    if 'Subject' in message:
        sub_str = message['Subject'].encode('utf-8')
        sub_str = multireplace(sub_str, rep)
        del message['Subject']
        message['Subject'] = sub_str.decode('utf-8')
    if 'Cc' in message:
        cc_str = message['Cc'].encode('utf-8')
        cc_str = multireplace(cc_str, rep)
        del message['Cc']
        message['Cc'] = cc_str.decode('utf-8')
    for part in message.walk():
        if not part.get_content_maintype() == 'multipart' and not part.is_multipart():
            if part.get_content_type() == 'text/plain':
                body = part.get_payload(decode=True)
                encoding_body = multireplace(body, rep)
                part.set_payload(encoding_body)
                body = part.get_payload(decode=True)
    return message

# 'Rajini'; 'Kalpana'
# To: rakesh <rakesh@mohan.com>;mohankumar <mohankumar@mohan.com>


def names_emails(emailId_Str, unique_names, unique_email_ids):
    name = None
    email = None
    if not emailId_Str:
        return name, email
    email_name_split_list = emailId_Str.split(';')
    for email_name in email_name_split_list:
        ret = name_email(email_name, unique_names, unique_email_ids)
    name = ret[0]
    email = ret[1]
    if name:
        name = name.strip().replace("\'", '')
        unique_names.add(name)
    if email:
        email = email.strip().replace("\'", '')
        email = email.replace('mailto:', '')
        unique_email_ids.add(email)
    return name, email

# From: rakesh <rakesh@mohan.com>


def name_email(emailId_Str, unique_names, unique_email_ids):
    name = None
    email = None
    if not emailId_Str:
        return name, email
    if ';' in emailId_Str:
        ret = names_emails(emailId_Str, unique_names, unique_email_ids)
        return ret[0], ret[1]
    else:
        if '<' in emailId_Str:
            pieces = emailId_Str.split('<')
            if len(pieces) > 1:
                name = pieces[0].replace('"', '').strip()
                email = pieces[1].replace('>', '')
            else:
                name = None
                email = pieces[0].replace('>', '')
        else:
            if '@' in emailId_Str:
                email = emailId_Str
            else:
                name = emailId_Str
    if name:
        name = name.strip().replace("\'", '')
        unique_names.add(name)
    if email:
        email = email.strip().replace("\'", '')
        email = email.replace('mailto:', '')
        unique_email_ids.add(email)
    return name, email


def load_masking():
    global cur, rep
    try:
        rep = None
        cur.execute(
            'SELECT original_text,replace_text FROM masking group by masking.original_text ORDER BY length(masking.original_text) desc')
        data = cur.fetchall()
        rep = dict((x) for index, x in enumerate(data))
        rep = OrderedDict(
            sorted(rep.items(), key=lambda t: len(t[0]), reverse=True))
        rep = OrderedDict((re.escape(k), v) for k, v in rep.items())
    except TypeError as err:
        logging.error(
            "Type cast error while load masking value :: ".format(err))
    return False


def save_masking(obj_list, obj_type):
    for single in obj_list:
        masking = [count, single, obj_type + '-' + str(count), obj_type]
        increment()
        cur.execute('INSERT INTO masking VALUES(?,?,?,?);', masking)


def multireplace(string, rep):
    pattern = re.compile("|".join(rep.keys()))
    string = pattern.sub(lambda m: rep[re.escape(m.group(0))],
                         string.decode('utf-8'))
    return string.encode()


def main():
    with connection:
        global dest_mbox
        masking_set = loadnoun()
        print(masking_set)
        mbox_files = get_files_from_dir()
        emailid = 1
        for mbox_file in mbox_files:
            src_mbox = mailbox.mbox(mbox_file[1])
            src_mbox.lock()  # Optional -- but a good idea
            messageId = None
            try:
                for message in src_mbox:
                    logging.info(
                        "Start to read message id :: " + message['Message-ID'])
                    unique_email_ids = set({})
                    unique_names = set({})
                    sender = name_email(
                        message['From'], unique_names, unique_email_ids)
                    recipient = name_email(
                        message['To'], unique_names, unique_email_ids)
                    if 'Cc' in message:
                        name_email(
                            message['Cc'], unique_names, unique_email_ids)
                    subject = message['subject']
                    date = message['Date']
                    messageId = message['Message-ID']
                    text_body = getbodyfromemail(message)
                    row = [emailid, sender[0], sender[1], recipient[0],
                           recipient[1], subject, date, messageId, text_body]
                    emailid = emailid + 1
                    cur.execute(
                        "INSERT INTO emails VALUES(?,?,?,?,?,?,?,?,?);", row)
                    unique_email_ids.update(get_emails(row[8]))
                    unique_email_ids = unique_email_ids - masking_set
                    save_masking(unique_email_ids, "EmailId")
                    masking_set.update(unique_email_ids)
                    temp_nouns = stanford_main(row[8])
                    nouns = ({})
                    if temp_nouns:
                        nouns = set(
                            set(structure_ne(stanford_tree(bio_tagger(temp_nouns)))) | set(temp_nouns))
                    else:
                        nouns = set(temp_nouns)
                    noun_list = set(elt[0] for elt in nouns)
                    noun_list = noun_list - masking_set
                    unique_names = unique_names - masking_set
                    save_masking(unique_names, "Person")
                    masking_set.update(unique_names)
                    for noun in nouns:
                        if noun[0] in noun_list:
                            if not noun[0] in masking_set:
                                save_nouns(None, noun, emailid)
                                save_masking([noun[0]], noun[1])
                                masking_set.update([noun[0]])
                    message = setbodytoemail(message)
                    dest_mbox.add(message)
                    dest_mbox.flush()
                    logging.info(
                        "Completed to write message id :: " + message['Message-ID'])
            except Exception as e:
                logging.error("Error while reading message :: " + e)
                logging.debug(e)
            finally:
                dest_mbox.unlock()
                src_mbox.unlock()
            connection.commit()
    export_csv()
    connection.close()


def executionTimeCalculation(executionStartTime):
    executionEndTime = os.times()[4]
    print('Total Execution Time in Seconds :: ',
          executionEndTime - executionStartTime)


def export_csv():
    logger.info("*************Start to create CSV*****************")
    f = open(mbox_path + '/masking.csv', 'w')
    w = csv.writer(f)
    w.writerow(['Id', 'Original Text', 'Replacement Text'])
    rows = cur.execute('SELECT id,original_text,replace_text FROM masking')
    for row in rows:
        w.writerow(row)
    logger.info("**********CREATED CSV*******************")

if __name__ == '__main__':
    executionStartTime = os.times()[4]
    setup_logging()
    if logger is None:
        print("Logger Files not created")
        executionTimeCalculation(executionStartTime)
        sys.exit(0)
    create_output_mbox()
    load_stop_words()
    define_db_connection()
    create_tables()
    main()
    executionTimeCalculation(executionStartTime)
