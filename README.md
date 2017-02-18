Install Python 3:

sudo apt-get update
sudo apt-get -y upgrade
python3 -V
sudo apt-get install -y python3-pip

Install the Sqlite command line

sudo apt-get update.
sudo apt-get install sqlite3

Readpst package in Ubuntu

sudo apt-get update
sudo apt-get install readpst (or) sudo apt-get install libpst-dev


Command for convert PST To MBOX:

readpst -r -t e "PST_FILE_LOCATION" -o "EXPORT_DIRECTORY"
