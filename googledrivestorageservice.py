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
import dateutil.parser
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

from storageservice import StorageService

class ItemDoesNotExistError(RuntimeError):
	pass

class UTC(datetime.tzinfo):
	"""UTC"""

	def utcoffset(self, dt):
		return datetime.timedelta(0)

	def tzname(self, dt):
		return "UTC"

	def dst(self, dt):
		return datetime.timedelta(0)

class GoogleDriveStorageService(StorageService):



	def authorize(self):
		print "Authorize Google Drive Storage Service"
		self.get_google_auth()

	def upload(self, file_path, destination=None, modified_time= None, create_folder = False, overwrite = False):
		print "Upload {} Google Drive Storage Service".format(file_path)
		self.upload_file(file_path, folder=destination, modified_time=modified_time, create_folder = create_folder, overwrite = overwrite)
		


	def download(self, file_path, destination=None, overwrite=False):
		print "Download {} Google Drive Storage Service".format(file_path)
		return self.download_file(file_path, destination=destination, overwrite=overwrite)

	def is_folder(self, folder_path):
		if folder_path is None or folder_path == "":
			# Interpret as root
			return True
		try:
			folder_result = self.get_folder(folder_path)
		except ItemDoesNotExistError:
			return False

		return True
		
	def list_folder(self, folder_path):
		base_folder = None
		if folder_path is None or folder_path == "":
			base_folder = 'root'
		else:
			base_folder = self.get_folder(folder_path)
		
		folder_list = self.get_folder_listing(base_folder, [])
		return folder_list

	def get_folder_listing(self, cur_folder, path_list):


		drive = GoogleDrive(self.__google_auth__)
		result_list = []
		file_list = drive.ListFile({'q': "'{}' in parents and trashed=false ".format(cur_folder)}).GetList()
		file_list.sort(key=lambda cur_file: cur_file['title'])
		for cur_file in file_list:
			result_list.append((cur_file, path_list))
			if cur_file['mimeType'] == 'application/vnd.google-apps.folder':
				new_list = list(path_list)
				new_list.append(cur_file['title'])
				result_list.extend(self.get_folder_listing(cur_file['id'], new_list))

		return result_list
		



	def get_google_auth(self):
		self.__google_auth__ = None
		gauth = GoogleAuth()
		gauth.LoadCredentials()
		if gauth.credentials is None:
			gauth.CommandLineAuth()
		elif gauth.access_token_expired:
			gauth.Refresh()
		else:
			gauth.Authorize()
		self.__google_auth__ = gauth


	#TODO Set debug logging
	def get_refresh_token(self):
		self.get_google_auth()
		tries = 0
		while self.__google_auth__ is None or self.__google_auth__ is None:
			if tries == 10:
				print "bad refresh"
				raise RuntimeError("Unable to refresh token")
			# bad refresh?
			sleep_length = float(1 << tries) / 10
			tries= tries+1
			time.sleep(sleep_length)
			print "Error refreshing Google Drive token.  Trying again. Attempt "+str(tries)+ " of 10"
			get_google_auth()
		if tries > 0:
			print "Successfully refreshed token"


	def download_file(self, file_path, destination=None, overwrite=False):
		self.get_refresh_token()
		cur_file_info = self.get_file(file_path)

		if cur_file_info['mimeType'] == "application/vnd.google-apps.folder":
			raise RuntimeError("Path is a folder")

		drive = GoogleDrive(self.__google_auth__)
		cur_file = drive.CreateFile({'id': cur_file_info['id']})
		local_path = cur_file_info['title']
		if destination is not None:
			local_path = os.path.join(destination, local_path)
		if os.path.isdir(local_path):
			raise RuntimeError("Local destination is a folder")
		if overwrite is False and os.path.isfile(local_path):
			raise RuntimeError("Local file {} exists.  Enable overwrite option to continue.".format(local_path))
		cur_file.GetContentFile(local_path)
		# Set modified time too!
		modified_date = dateutil.parser.parse(cur_file['modifiedDate'])
		os.utime(local_path, (time.mktime(modified_date.timetuple()),time.mktime(modified_date.timetuple())))
		return (local_path, cur_file['modifiedDate'])


	def download_item(self, cur_file, destination=None, overwrite=False):
		
		local_path = cur_file['title']
		if destination is not None:
			local_path = os.path.join(destination, local_path)

		
		if cur_file['mimeType'] == "application/vnd.google-apps.folder":
			if not os.path.exists(local_path):
				os.mkdir(local_path)
			return (local_path, cur_file['modifiedDate'])

		self.get_refresh_token()
		drive = GoogleDrive(self.__google_auth__)
		# cur_file = drive.CreateFile({'id': cur_file['id']})
		
		if os.path.isdir(local_path):
			raise RuntimeError("Local destination is a folder")
		if overwrite is False and os.path.isfile(local_path):
			raise RuntimeError("Local file {} exists.  Enable overwrite option to continue.".format(local_path))
		cur_file.GetContentFile(local_path)
		modified_date = dateutil.parser.parse(cur_file['modifiedDate'])
		os.utime(local_path, (time.mktime(modified_date.timetuple()),time.mktime(modified_date.timetuple())))
		return (local_path, cur_file['modifiedDate'])

	def upload_file(self, file_path, folder=None, modified_time=None, create_folder = False, overwrite=False):
		self.get_refresh_token()
		drive = GoogleDrive(self.__google_auth__)
		try:
			with open(file_path) as f: pass
		except IOError as e:
			raise IOError("Unable to open file. Error: "+str(e))
		logging.debug("Uploading " + file_path)

		file_name = file_path.split('/')[-1]
		mime_type = guess_type(file_path)[0]
		mime_type = mime_type if mime_type else 'application/octet-stream'
		media_body = MediaFileUpload(file_path, mimetype=mime_type, chunksize=1024*1024, resumable=True)
		parents = []
		cur_folder = 'root'
		if folder is not None:
			cur_folder = self.get_folder(folder, create=create_folder)
			parents.append({"id": cur_folder})

		if modified_time is None:
			modified_time =  datetime.datetime.fromtimestamp(os.path.getmtime(file_path), UTC()).isoformat()[:-6]
			if '.' not in modified_time:
				modified_time +=".000000Z"
			else:
				modified_time += "Z"
		logging.debug("Modified time: "+modified_time)
		
		existing_file = self.get_file_if_exists(file_name, cur_folder)

		try: 
			cur_file = None

			if existing_file is not None:
				if overwrite is False:
					raise RuntimeError("File already exists")
				old_file = self.__google_auth__.service.files().get(fileId=existing_file['id']).execute()
				old_file['modifiedDate'] = modified_time
				old_file['title'] = file_name
				old_file['mimeType'] = mime_type
				old_file['parents'] = parents
				new_file = self.__google_auth__.service.files().update(fileId=existing_file['id'], body=old_file, media_body=media_body).execute()
				# cur_file = drive.CreateFile({'id': existing_file['id']})
			else:
				body = {
					'title': file_name,
					'mimeType': mime_type,
					'parents' : parents,
					'modifiedDate' : modified_time,
				}
				self.__google_auth__.service.files().insert(body=body, media_body=media_body).execute()
			# 	cur_file = drive.CreateFile({'title': file_name})
			# cur_file['parents'] = parents
			# cur_file['modifiedDate'] = modified_time
			# cur_file['mimeType'] = mime_type
			# cur_file.SetContentFile(file_path)
			# cur_file.Upload()
			
		except apiclient.errors.HttpError, error:
			print 'An error occured uploading file: %s' % error
			return None


	def get_file_if_exists(self, file_name, folder_id):
		drive = GoogleDrive(self.__google_auth__)
		file_list = drive.ListFile({'q': "'{}' in parents and trashed=false and title='{}'".format(folder_id, file_name)}).GetList()
		if len(file_list) > 1:
			raise RuntimeError('Multiple files with name "{}" exist'.format(file_name))
		elif len(file_list) is 0:
			logging.debug("File {} does not exist".format(file_name))
			return None
		else:
			logging.debug("File {} exists".format(file_name))
			return file_list[0]

	def get_folder(self, folder_path, create=False):
		return self.get_file(folder_path, is_folder = True, create = create)

	def get_file(self, file_path, is_folder=False, create=False):

		if is_folder is True and file_path.endswith('/'):
			file_path=file_path[:-1]
		
		folders = file_path.split('/')
		drive = GoogleDrive(self.__google_auth__)
		
		file_name = None
		if is_folder is False:
			file_name = folders.pop()

		parent = 'root'
		
		for cur_folder in folders:
			file_list = drive.ListFile({'q': "'{}' in parents and trashed=false and mimeType='application/vnd.google-apps.folder' and title='{}'".format(parent, cur_folder)}).GetList()
			if len(file_list) > 1:
				raise RuntimeError('Multiple folders with name "{}" exist'.format(cur_folder))
			elif len(file_list) is 0:
				if create is False:
					raise ItemDoesNotExistError('Folder "{}" does not exist'.format(cur_folder))
				parent = self.create_folder_helper(cur_folder, parent)['id']
				if parent is None:
					raise RuntimeError('Unable to create folder "{}"'.format(cur_folder))
			else:
				parent = file_list[0]['id']
			
		if is_folder is True:
			return parent

		file_list = drive.ListFile({'q': "'{}' in parents and trashed=false and title='{}'".format(parent, file_name)}).GetList()
		if len(file_list) > 1:
			raise RuntimeError('Multiple files with name "{}" exist'.format(file_name))
		elif len(file_list) is 0:
			raise ItemDoesNotExistError('File "{}" does not exist'.format(file_name))
		
		return file_list[0]



	def create_folder(self, folder_path):
		self.get_folder(folder_path, create=True)




	def create_folder_helper(self, folder_name, parent, modified_time=None):
		
		mime_type = 'application/vnd.google-apps.folder'
		parents = []
		if parent is not None:
			parents.append({"id": parent})
		body = {
		  'title': folder_name,
		  'mimeType': mime_type,
		  'parents' : parents,
		}
		if modified_time is not None:
			body['modifiedDate'] = modified_time
				
		try: 
			file = self.__google_auth__.service.files().insert(body=body).execute()
			print "Folder creation complete"
			return file
		except apiclient.errors.HttpError, error:
			print 'An error occured creating folder: %s' % error
			return None

	def get_file_name(self, file):
		return file['title']

	def is_folder_from_file_type(self, file):
		return file['mimeType'] == 'application/vnd.google-apps.folder'
