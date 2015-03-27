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

from storageservice import StorageService


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

	def upload(self, file_name, destination=None, modified_time= None, create_folder = False):
		print "Upload {} Google Drive Storage Service".format(file_name)
		self.upload_file(file_name, folder=destination, modified_time=modified_time, create_folder = create_folder)
		


	def download(self, file_path, destination=None):
		print "Download {} Google Drive Storage Service".format(file_path)
		self.download_file(file_path, destination)

	def is_folder(self, folder_path):
		pass
		
	
	def list_folder(self, folder_path):
		pass

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


	def download_file(self, file_path, destination=None):
		self.get_refresh_token()
		cur_file_info = self.get_file(file_path)
		drive = GoogleDrive(self.__google_auth__)
		cur_file = drive.CreateFile({'id': cur_file_info['id']})
		cur_file.GetContentFile(cur_file_info['title'])


	def upload_file(self, file_path, folder=None, modified_time=None, create_folder = False):
		self.get_refresh_token()
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
		if folder is not None:
			cur_folder = self.get_folder(folder, create=create_folder)['id']
			parents.append({"id": cur_folder})

		if modified_time is None:
			modified_time =  datetime.datetime.fromtimestamp(os.path.getmtime(file_path), UTC()).isoformat()[:-6]
			if '.' not in modified_time:
				modified_time +=".000000Z"
			else:
				modified_time += "Z"
		logging.debug("Modified time: "+modified_time)
		body = {
			'title': file_name,
			'mimeType': mime_type,
			'parents' : parents,
			'modifiedDate' : modified_time,
		}

		try: 
			file = self.__google_auth__.service.files().insert(body=body, media_body=media_body).execute()
			return file
		except apiclient.errors.HttpError, error:
			print 'An error occured: %s' % error
			return None


	def get_folder(self, file_path, create=False):
		return self.get_file(folder_path, is_folder = True, create = create)

	def get_file(self, file_path, is_folder=False, create=False):

		if is_folder is True and file_path.endswith('/'):
			file_path=file_path[:-1]
		
		folders = file_path.split('/')
		drive = GoogleDrive(self.__google_auth__)
		
		file_name = None
		if is_folder is False:
			file_name = folders.pop()

		parent = {'id':'root'}
		
		for cur_folder in folders:
			file_list = drive.ListFile({'q': "'{}' in parents and trashed=false and mimeType='application/vnd.google-apps.folder' and title='{}'".format(parent['id'], cur_folder)}).GetList()
			if len(file_list) > 1:
				raise RuntimeError('Multiple folders with name "{}" exist'.format(cur_folder))
			elif len(file_list) is 0:
				if  create is False:
					raise RuntimeError('Folder "{}" does not exist'.format(cur_folder))
				parent = self.create_folder(cur_folder, parent)['id']
				if parent is None:
					raise RuntimeError('Unable to create folder "{}"'.format(cur_folder))
			else:
				parent = file_list[0]
			
		if is_folder is True:
			return parent

		file_list = drive.ListFile({'q': "'{}' in parents and trashed=false and title='{}'".format(parent['id'], file_name)}).GetList()
		if len(file_list) > 1:
			raise RuntimeError('Multiple files with name "{}" exist'.format(file_name))
		elif len(file_list) is 0:
			raise RuntimeError('File "{}" does not exist'.format(file_name))
		
		return file_list[0]





	def create_folder(self, folder_name, parent, modified_time=None):
		
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
			print 'An error occured: %s' % error
			return None

