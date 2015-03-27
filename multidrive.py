#!/usr/bin/env python
# -*- coding: utf-8 -*-
 
    # This file is part of MultiDrive.

    # MultiDrive is free software: you can redistribute it and/or modify
    # it under the terms of the GNU General Public License as published by
    # the Free Software Foundation, either version 3 of the License, or
    # (at your option) any later version.

    # MultiDrive is distributed in the hope that it will be useful,
    # but WITHOUT ANY WARRANTY; without even the implied warranty of
    # MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    # GNU General Public License for more details.

    # You should have received a copy of the GNU General Public License
    # along with MultiDrive.  If not, see <http://www.gnu.org/licenses/>.


import requests
import json
from dateutil.parser import parse
import datetime
import argparse
import sys
import urllib
from urlparse import urlparse, parse_qs
import os

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import sys
import socket
import logging
import httplib2
import os
from time import sleep
from mimetypes import guess_type

# sudo pip install --upgrade google-api-python-client
import apiclient
from apiclient.discovery import build
from apiclient.http import MediaFileUpload
from apiclient.http import MediaIoBaseUpload
from apiclient.errors import ResumableUploadError
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.file import Storage

import argparse
import logging

import time
from googledrivestorageservice import GoogleDriveStorageService
from onedrivestorageservice import OneDriveStorageService




def main():
	parser = argparse.ArgumentParser(description='Multiple Cloud Storage Operation')
	# parser.add_argument('-m', '--moveFile', help="Path to File to move")
	# parser.add_argument('-s', '--moveFiles', nargs= '*', help="Path to Files to move")
	parser.add_argument('-s', '--source', nargs=1, required=True, help='set primary service for this command. Valid values are onedrive and googledrive')
	parser.add_argument('-a', '--action', nargs=1, required=True, help='action to perform, valid actions include download, upload, and copy')
	parser.add_argument('-d', '--destination', nargs=1, help='set secondary service for this command, Valid values are onedrive and googledrive.  Only valid with copy command')
	parser.add_argument('-l', '--local', nargs=1, help='path of local file or folder')
	parser.add_argument('-r', '--remote', nargs=1, help='path of remote file or folder')
	parser.add_argument('-c', '--createfolder', help='enable creation of remote folders', action='store_true')
	parser.add_argument('-e', '--secondaryremote', nargs=1, help='path secondary remote file or folder (for copy action)')
	parser.add_argument('-o', '--overwrite', help='enable overwriting of files', action='store_true')
	# parser.add_argument('-p', '--parent', help="parent folder for Google Drive")
	# parser.add_argument('-d', '--debug', help="enable debug logging")

	args = parser.parse_args();

	storage_service = None
	if args.source[0].lower() == 'googledrive':
		storage_service = GoogleDriveStorageService()
	elif args.source[0].lower() == 'onedrive':
		storage_service = OneDriveStorageService()
	else:
		raise ValueError("Please specify a valid source service.")

	storage_service.authorize()

	if args.action[0].lower() == "upload":
		if args.local is None:
			raise ValueError("Please specify a local file to upload.")
		destination = None
		if args.remote is not None:
			destination = args.remote[0]
		storage_service.upload(args.local[0], destination=destination, create_folder=args.createfolder, overwrite=overwrite)
		pass
	elif args.action[0].lower() == "download":
		if args.remote is None:
			raise ValueError("Please specify a remote file to download.")
		local_path = None
		if args.local is not None:
			local_path = args.local[0]

		storage_service.download(args.remote[0], local_path)
	elif args.action[0].lower() == "copy":
		raise ValueError("Copy support is not yet implemented")
	else:
		raise ValueError("Please specify a valid action.")
	
	# storage_service.download("test")
if __name__ == "__main__":
	main()
