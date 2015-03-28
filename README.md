#Multidrive


## Description

Basic utilities to upload and download from various cloud storage services.

Currently support for Google Drive and Microsoft OneDrive upload and download operations is implemented.

This is in alpha.

## Usage

    ./multidrive -s googledrive -a upload -l example.txt

Uploads "test.txt" to the root directory on Google Drive.

    ./multidrive -s googledrive -a upload -l example.txt -r examplefolder

Uploads "test.txt" to the "examplefolder" directory on Google Drive.

    ./multidrive -s googledrive -a upload -l example.txt -r examplefolder -c

Uploads "test.txt" to the "examplefolder" directory on Google Drive.  It will create the remote folder if necessary

    ./multidrive -s googledrive -a download -r "example.txt" 

Downloads "test.txt" in the root directory of Google Drive to the local computer.  WARNING: Local files may be overwritten with no warning if they match the remote file name.

## Current Functionality

Google Drive:
Upload file to any remote folder
Download files and folders to any local folder.
List remote files/folders.
(Cannot upload folders yet)

OneDrive
Upload file to any remote folder
Download file to local folder.
(Cannot list files/folders yet)
(Cannot download folders yet)
(Cannot upload folders yet)

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
Support for moving files and folders from one service to another.
Support for setting modification dates is planned for services that support it.  It currently sets the modification date for Google Drive.
Support for handling quota errors.
When downloading/uploading folders, if overwrite is disabled, check to see if there are any file conflicts before starting operations
Support keeping track of last modified time on platforms that support it (Supported for Google Drive, limited support on Amazon Cloud Drive and Microsoft OneDrive).

## Licence 

GPL v3

See licence file for details


THERE IS NO WARRANTY FOR THE PROGRAM, TO THE EXTENT PERMITTED BY APPLICABLE LAW. EXCEPT WHEN OTHERWISE STATED IN WRITING THE COPYRIGHT HOLDERS AND/OR OTHER PARTIES PROVIDE THE PROGRAM “AS IS” WITHOUT WARRANTY OF ANY KIND, EITHER EXPRESSED OR IMPLIED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE ENTIRE RISK AS TO THE QUALITY AND PERFORMANCE OF THE PROGRAM IS WITH YOU. SHOULD THE PROGRAM PROVE DEFECTIVE, YOU ASSUME THE COST OF ALL NECESSARY SERVICING, REPAIR OR CORRECTION.

IN NO EVENT UNLESS REQUIRED BY APPLICABLE LAW OR AGREED TO IN WRITING WILL ANY COPYRIGHT HOLDER, OR ANY OTHER PARTY WHO MODIFIES AND/OR CONVEYS THE PROGRAM AS PERMITTED ABOVE, BE LIABLE TO YOU FOR DAMAGES, INCLUDING ANY GENERAL, SPECIAL, INCIDENTAL OR CONSEQUENTIAL DAMAGES ARISING OUT OF THE USE OR INABILITY TO USE THE PROGRAM (INCLUDING BUT NOT LIMITED TO LOSS OF DATA OR DATA BEING RENDERED INACCURATE OR LOSSES SUSTAINED BY YOU OR THIRD PARTIES OR A FAILURE OF THE PROGRAM TO OPERATE WITH ANY OTHER PROGRAMS), EVEN IF SUCH HOLDER OR OTHER PARTY HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES