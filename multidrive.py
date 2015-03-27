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
	# parser.add_argument('-o', '--overwrite', help='enable overwriting of files', action='store_true')
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
		storage_service.upload(args.local[0], destination=args.remote[0], create_folder=args.createfolder)
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



# if args.moveFile is not None:
# 	cur_file_name= odfunctions.save_file(args.moveFile)

# 	if cur_file_name is not None:
# 		try:
# 			gauth_object = getGoogleAuth();
# 			upload_file(cur_file_name, gauth_object.service, ("***REMOVED***",))
# 		finally:
# 			os.remove(cur_file_name)
# 			print cur_file_name+" has been moved"

# if args.moveFiles is not None:
# 	for file_path in args.moveFiles:
# 		cur_file_name= odfunctions.save_file(file_path)
		
# 		if cur_file_name is not None:
# 			# print "The current file name is'"+cur_file_name+"'"
# 			try:
# 				gauth_object = getGoogleAuth();
# 				tries = 0
# 				while gauth_object is None or gauth_object.service is None:
# 					if tries == 10:
# 						print "bad refresh"
# 						raise RuntimeError("Unable to refresh token")
# 					# bad refresh?
# 					sleep_length = float(1 << tries) / 10
# 					tries= tries+1
# 					time.sleep(sleep_length)
# 					print "Error refreshing Google Drive token.  Trying again. Attempt "+str(tries)+ " of 10"
# 					gauth_object = getGoogleAuth();
# 				if tries > 0:
# 					print "Successfully refreshed token"
# 				upload_file(cur_file_name, gauth_object.service, ("***REMOVED***",))
# 			finally:
# 				os.remove(cur_file_name)
# 				print cur_file_name+" has been moved"




# def get_parent_path(path):
# 	if path.endswith('/'):
# 		path = path[:-1]
# 	path = path.rsplit('/', 1)[0]
# 	logging.debug("parent path is "+path+"/")
# 	return path+"/"

# def get_child_path(path):
# 	if path.endswith('/'):
# 		path = path[:-1]
# 	path = path.rsplit('/', 1)[1]
# 	logging.debug("child path is "+path)
# 	return path

# gauth_object = getGoogleAuth();
# if gauth_object is None:
# 	print 'Error authenticating with Google Drive'
# 	sys.exit(1)



# if args.debug:
#     logging.basicConfig(level=logging.DEBUG)

# if args.testFile is not None:
# 	odfunctions.upload_test2(args.testFile)

# if args.listFile is not None:
# 	print "Getting File Listing: "
# 	listing = [args.listFile]
# 	listing.extend(odfunctions.get_file_listing(args.listFile))
# 	print "Listing: "
# 	print listing


# if args.copyFile is not None:
# 	for current_file_or_path in args.copyFile:
# 		print "Retreiving list of files and folders"
# 		google_drive_paths = {}
# 		if odfunctions.is_valid_folder(current_file_or_path) is True:
# 			if current_file_or_path.endswith('/') is not True:
# 				current_file_or_path= current_file_or_path+'/'
# 			google_drive_paths[current_file_or_path] = args.parent
		
# 		listing = [current_file_or_path]
# 		listing.extend(odfunctions.get_file_listing(current_file_or_path))
		
# 		logging.debug("File Listing Complete")
# 		for current_subpath in listing:

# 			if current_subpath.endswith('/'):
# 				if current_subpath == current_file_or_path:

# 					continue
# 				# 
# 				# it's a folder, so we just create the google folder remotely and store in the dictionary
# 				# maybe check if it already exists?  What if multiple of same name exist?
# 				print "Copying Folder: " + current_subpath
				
# 				# throw exception or retry if something goes wrong here?
# 				gauth_object = get_refresh_token()
# 				cur_parent = get_parent_path(current_subpath)
# 				new_folder = create_folder(get_child_path(current_subpath), gauth_object.service, (google_drive_paths[cur_parent],), modified_time=odfunctions.get_modified_time(current_subpath))
# 				if new_folder is None:
# 					raise RuntimeError("Error creating folder on Google Drive")
# 				logging.debug("The new folder id is: "+new_folder['id'])
# 				google_drive_paths[current_subpath] = new_folder['id']
# 				print "Copy of Folder: " + current_subpath + " complete."
# 			else: # it's a file
# 				print "Copying File: " + current_subpath
# 				(cur_file_name, modified_time) = odfunctions.save_file(current_subpath)
# 				parent_id = None
# 				if current_file_or_path == current_subpath:
# 					parent_id = args.parent
# 				else:
# 					parent_id = google_drive_paths[get_parent_path(current_subpath)]
# 				# print "parent of file is:" + parent_id
# 				# throw exception if no parent?
# 				if cur_file_name is not None:
# 					# print "The current file name is'"+cur_file_name+"'"
# 					try:
# 						gauth_object = get_refresh_token()
# 						upload_file(cur_file_name, gauth_object.service, (parent_id,), modified_time=modified_time)
# 					finally:
# 						os.remove(cur_file_name)
# 						print "Copy of File: " + current_subpath + " complete."
