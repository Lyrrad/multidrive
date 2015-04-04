#MultiDrive


## Description

Basic utilities to upload and download from various cloud storage services.

Support for Amazon Cloud Drive, Google Drive and Microsoft OneDrive upload and download operations are implemented.

This is in alpha and there may be serious bugs.  This has only been tested on Ubuntu, though it should work on Mac OS X.  This has not yet been tested in Windows, and may not work in that OS yet without further testing.

No API keys are provided.  You will need to sign up as a developer with each service providers to get keys.

## Usage

    ./multidrive -h

Displays help

    ./multidrive -s googledrive -a upload -l example.txt

Uploads "example.txt" to the root directory on Google Drive.

    ./multidrive -s googledrive -a upload -l example.txt -r examplefolder

Uploads "example.txt" to the "examplefolder" directory on Google Drive.

    ./multidrive -s googledrive -a upload -l example.txt -r examplefolder -c

Uploads "example.txt" to the "examplefolder" directory on Google Drive.  It will create the remote folder if necessary

    ./multidrive -s googledrive -a download -r "example.txt" 

Downloads "example.txt" in the root directory of Google Drive to the local computer. 

    ./multidrive -s googledrive -d onedrive -a copy -r "Source Folder" -e "Transfers" -c

Copies the contents of "Source Folder" on Google Drive to the "Transfers" folder on Microsoft OneDrive, creating the remote folder if necessary.  The program will get a list of files, then, transfer one file at a time to the other service by downloading it to the local machine, then uploading it again.


## Current Functionality


|					|Google Drive	|OneDrive		|Cloud Drive 	|Dropbox		|
|-------------------|---------------|---------------|---------------|---------------|
|**Authentication**| | | | |
|Authenticate user	|Yes|Yes|Yes|Pending|
| | | | | |
|**Basic File Operations**| | | | |
|Upload File	|Yes|Yes|Yes|Pending|
|Upload Folder	|Pending|Pending|Pending|Pending|
|Download File	|Yes|Yes|Yes|Pending|
|Download Folder	|Yes|Yes|Yes|Pending|
|| | | | |			
|**Advanced**				
|Get Modified Time	|Yes|Partial|Partial|Unknown
|Set Modified Time	|Yes|No|No|Unknown|
|Local Overwrite	|Yes|Yes|Yes|Pending|
|Remote Overwrite	|Yes|Yes|Yes|Pending|
|Local Destination Folder	|Yes|Yes|Yes|Pending|
|Remote Destination Folder	|Yes|Yes|Yes|Pending|
|List Remote Files	|Yes|Yes|Yes|Pending|
|Create Remote Folder	|Yes|Yes|Yes|Pending|
|List Quota	|Pending|Pending|Pending|Pending|
|Delete Remote File	|Pending|Pending|Pending|Pending|
|Copy Folders	|Yes|Yes|Yes|Pending|
|Verify Files by Hash|Yes|Yes|Yes|Pending|

## Updates

2015-04-02 0.1.8: Fixed issue with downloading/listing Google Drive folders with more than 100 items.
				  Minor changes to debug code.

2015-04-02 0.1.7: Bug Fix: Cloud Drive HTTP retry code fixed
				  Additional OneDrive retry code added.

2015-04-02 0.1.6: Additional retry code added, particularly on hash and connection failures
				  Bug Fixes

2015-04-02 0.1.5: Attempt Retry on UnicodeDecodeError on Cloud Drive
				  Fixed Retry code for OneDrive/CloudDrive
				  Bug Fixes

2015-04-01 0.1.4: Added Hash check upon upload and download to confirm files properly transferred.
				  Bug Fixes
				  

2015-04-01 0.1.3: Refactored Cloud Drive Service class to reduce access token requests and improve http request handling.
				  Refactored OneDrive HTTP requests for robustness.
				  Bug Fixes

2015-03-31 0.1.2: Refactored OneDrive Service class.  It should be faster now, with less requests going to the server.
				  Bug Fixes

2015-03-31 0.1.1: Added debug option (-b)
				  Bug Fixes

2015-03-30 0.1.0: Changed to Python 3 to try to allow 32-bit systems to upload files greater than 4GB in size to Cloud Drive.
				  Removed PyDrive as it is not supported in Python 3.
				  Added new authenticaion method for Google Drive due to removal of PyDrive.  You'll need to rename the client_secrets.json file to google_drive_client_secrets.json and reauthenticate.
				  Added prompt to acknowledge risks if malware detected by Google Drive
				  Bug Fixes

## Known issues

On a 32-bit system, can't upload files bigger than 4GB to Amazon Cloud Drive. It is an issue with requests-toolbelt and has been reported.  It has been fixed with this pull request: https://github.com/sigmavirus24/requests-toolbelt/pull/81

## Requirements

Requires the httplib2, python-dateutil, google-api-python-client, requests, and requests-toolbelt libraries.

google-api-python-client now supports Python 3, though it requires an updated httplib2 module not available in pip.  This can be installed from source.

This can be installed by running:
wget https://github.com/jcgregorio/httplib2/archive/master.zip
unzip master.zip
cd httplib2-master
python3 ./setup.py install
pip install google-api-python-client
pip install requests
pip install requests-toolbelt
pip install python-dateutil


## Google Drive setup

Go to https://code.google.com/apis/console with your Google Account.

Create a new project.
Under API's and Auth, enable the Drive API.
In Credentials: Create a new Client ID for an "Installed Application"
Download the JSON file, put it in the working directory and name it google_drive_client_secrets.json

Credentials are stored in google_drive_settings.dat after authentication.

## OneDrive Setup

Sign up for API key (TODO: Add instructions)

Create a file onedrive_client_secrets.json with the following information (insert your client id and secret):

    {"client_id": "000000001234ABCD", "client_secret":"cL1eNtS3cr3T60eSHere01234567890A"}

## Cloud Drive Setup.

Sign up for API key. See https://developer.amazon.com/public/apis/experience/cloud-drive/content/getting-started

Create a file cloud_drive_client_secrets.json with the following information (insert your client id and secret, as well as your Return URL):

    {"client_id": "amzn1.application-oa2-client.000000001234ABCD", "client_secret":"cL1eNtS3cr3T60eSHere01234567890A", "return_uri":"https://example.com/login"}


## Planned features
Support for Dropbox is planned.
Support for setting modification dates is planned for services that support it.  It currently sets the modification date for Google Drive files, though it has not been extensively tested.
Support for handling quota errors and displaying remaining quota.
When downloading/uploading folders, if overwrite is disabled, check to see if there are any file conflicts before starting operations
Support keeping track of last modified time on platforms that support it (Supported for Google Drive, limited support on Amazon Cloud Drive and Microsoft OneDrive).
Deal with Google's versions feature when overwriting files.
Support for OneDrive's experimental upload from URL feature.  This could speed up transfers to OneDrive from other services that provide a public URL for files.

## Licence 

GPL v3

See licence file for details


THERE IS NO WARRANTY FOR THE PROGRAM, TO THE EXTENT PERMITTED BY APPLICABLE LAW. EXCEPT WHEN OTHERWISE STATED IN WRITING THE COPYRIGHT HOLDERS AND/OR OTHER PARTIES PROVIDE THE PROGRAM “AS IS” WITHOUT WARRANTY OF ANY KIND, EITHER EXPRESSED OR IMPLIED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE ENTIRE RISK AS TO THE QUALITY AND PERFORMANCE OF THE PROGRAM IS WITH YOU. SHOULD THE PROGRAM PROVE DEFECTIVE, YOU ASSUME THE COST OF ALL NECESSARY SERVICING, REPAIR OR CORRECTION.

IN NO EVENT UNLESS REQUIRED BY APPLICABLE LAW OR AGREED TO IN WRITING WILL ANY COPYRIGHT HOLDER, OR ANY OTHER PARTY WHO MODIFIES AND/OR CONVEYS THE PROGRAM AS PERMITTED ABOVE, BE LIABLE TO YOU FOR DAMAGES, INCLUDING ANY GENERAL, SPECIAL, INCIDENTAL OR CONSEQUENTIAL DAMAGES ARISING OUT OF THE USE OR INABILITY TO USE THE PROGRAM (INCLUDING BUT NOT LIMITED TO LOSS OF DATA OR DATA BEING RENDERED INACCURATE OR LOSSES SUSTAINED BY YOU OR THIRD PARTIES OR A FAILURE OF THE PROGRAM TO OPERATE WITH ANY OTHER PROGRAMS), EVEN IF SUCH HOLDER OR OTHER PARTY HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES