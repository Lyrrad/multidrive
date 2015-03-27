#Multidrive


## Description

Basic utilities to upload and download from various cloud storage services.

Currently this only supports Google Drive upload and download operations.

This is in alpha.

## Usage

    ./multidrive -s googledrive -a upload -l example.txt

Uploads "test.txt" to the root  directory on Google Drive.

    ./multidrive -s googledrive -a upload -l example.txt -r examplefolder

Uploads "test.txt" to the "examplefolder" directory on Google Drive.

    ./multidrive -s googledrive -a upload -l example.txt -r examplefolder -c

Uploads "test.txt" to the "examplefolder" directory on Google Drive.  It will create the remote folder if necessary

    ./multidrive -s googledrive -a download -r "example.txt" 

Downloads "test.txt" in the root directory of Google Drive to the local computer.  WARNING: Local files may be overwritten with no warning if they match the remote file name.

## Current Functionality

Upload/Download to Google Drive
Upload/Download from OneDrive. (Can only upload to root onedrive folder)

## Requirements

Requires pydrive and requests libraries.

This can be installed by running:
pip install PyDrive
pip install requests


## Google Drive setup

See http://pythonhosted.org/PyDrive/quickstart.html for details on authentication.

In short, go to the APIs console and create a new Drive API project and put the client_secrets.json file in the working directory of this program.

Credentials are stored in credentials.json after authenticated.

## OneDrive Setup

Sign up for API key (TODO: Add instructions)

Create a file onedrive_client_secrets.json with the following information (insert your client id and secret):
    {"client_id": "000000001234ABCD", "client_secret":"cL1eNtS3cr3T60eSHere01234567890A"}


## Planned features
Support for Amazon Cloud Drive and Dropbox is planned.
Support for moving files from one service to another is planned.
Support for downloading, uploading, and moving folders is planned.
Support for setting modification dates is planned for services that support it.  It currently sets the modification date for Google Drive.
Support for overwriting if file already.

## Licence 

GPL v3

See licence file for details


THERE IS NO WARRANTY FOR THE PROGRAM, TO THE EXTENT PERMITTED BY APPLICABLE LAW. EXCEPT WHEN OTHERWISE STATED IN WRITING THE COPYRIGHT HOLDERS AND/OR OTHER PARTIES PROVIDE THE PROGRAM “AS IS” WITHOUT WARRANTY OF ANY KIND, EITHER EXPRESSED OR IMPLIED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE ENTIRE RISK AS TO THE QUALITY AND PERFORMANCE OF THE PROGRAM IS WITH YOU. SHOULD THE PROGRAM PROVE DEFECTIVE, YOU ASSUME THE COST OF ALL NECESSARY SERVICING, REPAIR OR CORRECTION.

IN NO EVENT UNLESS REQUIRED BY APPLICABLE LAW OR AGREED TO IN WRITING WILL ANY COPYRIGHT HOLDER, OR ANY OTHER PARTY WHO MODIFIES AND/OR CONVEYS THE PROGRAM AS PERMITTED ABOVE, BE LIABLE TO YOU FOR DAMAGES, INCLUDING ANY GENERAL, SPECIAL, INCIDENTAL OR CONSEQUENTIAL DAMAGES ARISING OUT OF THE USE OR INABILITY TO USE THE PROGRAM (INCLUDING BUT NOT LIMITED TO LOSS OF DATA OR DATA BEING RENDERED INACCURATE OR LOSSES SUSTAINED BY YOU OR THIRD PARTIES OR A FAILURE OF THE PROGRAM TO OPERATE WITH ANY OTHER PROGRAMS), EVEN IF SUCH HOLDER OR OTHER PARTY HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES