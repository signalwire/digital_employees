#!/bin/bash

GITDIR=/usr/local/digital_employees
WORKINGDIR=/usr/local/digital_employees/server/Perl_Examples/Babelfish
echo -e "===================================="
echo -e "                                    "
echo -e "Don't forget to cp -r env.example .env and edit the .env variables in ${WORKINGDIR}"
echo -e "                                    "
echo -e "===================================="

source .env

#read -p "Please enter a FROM number associated with your SignalWire space.  Formatted as +15551234567: " FROM_NUMBER

# Clone
if [ ! -d ${GITDIR} ]; then
  echo -ne "Downloading Source Code... "
  git clone --quiet https://github.com/signalwire/digital_employees.git ${GITDIR} > /dev/null
  echo -e  "Complete!"
else
  echo "Source code already exists, skipping download"
fi

cd ${WORKINGDIR}

## CPAN
# NOTE:
# Occasionally the C module will fail to install.  Re-running seems to resolve the issue.
# If the module fails, a re-run of this wrapper command should resolve and start the app.
#
echo -ne "Installing Perl Dependencies.  This may take a few minutes... "
cpanm --installdeps ${WORKINGDIR} > /dev/null 2>&1
# Retry incase something failed (yes, this is hacky, but C seems to fail randomly)
cpanm --installdeps ${WORKINGDIR} > /dev/null 2>&1
cpanm Carton > /dev/null 2>&1
carton install
echo -e  "Complete!"


## APPLICATION
# create symlink from WORKINGDIR to /app

rm /app
if [ ! -h /app ]; then
    ln -s ${WORKINGDIR} /app > /dev/null 2>&1
fi

# Set the Application ENV
export DEBUG=0
#export FROM_NUMBER=${FROM_NUMBER}
export SAVE_BLANK_CONVERSATIONS=1
#export API_VERSION=api/relay/rest
export TOP_P=0.6
export TEMPERATURE=0.6
echo -e "===================================="

echo -e "===================================="
#

NGROK_HOST=${NGROK_URL:8}   # Strip out https:// for now.
RELAY_URL="https://${NGROK_HOST}/swml"

carton exec perl ${WORKINGDIR}/app.pl
