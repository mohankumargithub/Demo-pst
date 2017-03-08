# Cleaning the Data


Converting the PST files to text was more challenging task.I tried libpff  C++  library with python binding to read PST files. ultimately too many messages couldn’t be parsed due to what looked like unicode conversion errors.
Finally i found another library Readpst which successfully converted the messages to a more open format called mbox. The mbox files, can then be read by Python’s mailbox library.


# Analayzing the data

Now that we have the data in a usable format, we can analyze it . My approach was to combine sentiment analysis with entity extraction. For Email extraction from data using regular expression.


### Installing Python 3

#####  **Ubuntu** :
    sudo apt-get update
    sudo apt-get -y upgrade
    python3 -V
    sudo apt-get install -y python3-pip

### Installing the Sqlite3

#### Ubuntu:

    sudo apt-get update
    sudo apt-get install sqlite3

###  Install Java 8 (oracle-jdk-8)
    java -version
    sudo apt-get install python-software-properties
    sudo add-apt-repository ppa:webupd8team/java
    sudo apt-get update
    sudo apt-get install oracle-java8-installer
[Source: Digital Ocean](https://www.digitalocean.com/community/tutorials/how-to-install-java-on-ubuntu-with-apt-get)

### Installing Readpst package

#### Ubuntu:

    sudo apt-get update
    sudo apt-get install readpst (or) sudo apt-get install libpst-dev

### Command for convert PST To MBOX:

>readpst -r -t e "PST_FILE_LOCATION" -o "EXPORT_DIRECTORY"


- Go to python and download the nltk corpora using following commands:

```
import nltk
nltk.download('punkt')
nltk.download('all')
```

- Now install the Stanford NER tagger:

```
cd $HOME
# Update / Install NLTK
pip3 install -U nltk
# Download the Stanford NLP tools
wget http://nlp.stanford.edu/software/stanford-ner-2016-10-31.zip
wget http://nlp.stanford.edu/software/stanford-postagger-full-2016-10-31.zip
wget http://nlp.stanford.edu/software/stanford-parser-full-2016-10-31.zip
# Extract the zip file.
unzip stanford-ner-2016-10-31.zip
unzip stanford-parser-full-2016-10-31.zip
unzip stanford-postagger-full-2016-10-31.zip
```

- Copy and add the following paths to `.bashrc` file using this command `nano ~/.bashrc`:

```
export STANFORDTOOLSDIR=$HOME
export CLASSPATH=$STANFORDTOOLSDIR/stanford-postagger-full-2016-10-31/stanford-postagger.jar:$STANFORDTOOLSDIR/stanford-ner-2016-10-31/stanford-ner.jar:$STANFORDTOOLSDIR/stanford-parser-full-2016-10-31/stanford-parser.jar:$STANFORDTOOLSDIR/stanford-parser-full-2016-10-31/stanford-parser-3.5.2-models.jar
export STANFORD_MODELS=$STANFORDTOOLSDIR/stanford-postagger-full-2016-10-31/models:$STANFORDTOOLSDIR/stanford-ner-2016-10-31/classifiers
```
[Source: Stackoverflow](http://stackoverflow.com/questions/13883277/stanford-parser-and-nltk/34112695#34112695)

### Installing PyEnchant

    pip3 install pyenchant
