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
# import apiclient
# from apiclient.discovery import build
# from apiclient.http import MediaFileUpload
# from apiclient.http import MediaIoBaseUpload
# from apiclient.errors import ResumableUploadError
# from oauth2client.client import OAuth2WebServerFlow
# from oauth2client.file import Storage

import argparse
import logging

import time

from storageservice import StorageService


# class UTC(datetime.tzinfo):
# 	"""UTC"""

# 	def utcoffset(self, dt):
# 		return datetime.timedelta(0)

# 	def tzname(self, dt):
# 		return "UTC"

# 	def dst(self, dt):
# 		return datetime.timedelta(0)

class OneDriveStorageService(StorageService):

	onedrive_url_root = "https://api.onedrive.com/v1.0"

	def authorize(self):
		print "Authorize OneDrive Storage Service"
		try:
			with open('onedrive_client_secrets.json', 'r') as f:
				config = json.load(f)
				self.__client_id__ = config['client_id']
				self.__client_secret__ = config['client_secret']
		except IOError:
			pass
		# TODO: Store refresh token in class.
		refresh_token = self.load_refresh_token()
		access_token = self.get_access_token(refresh_token)

	def get_refresh_token_from_code(self, code):
		data = {'client_id': self.__client_id__, 'redirect_uri': 'https://login.live.com/oauth20_desktop.srf', 'client_secret': self.__client_secret__, 'code':code, 'grant_type':'authorization_code'}
		headers = {'Content-Type': 'application/x-www-form-urlencoded'}
		r = requests.post('https://login.live.com/oauth20_token.srf', data=data, headers=headers)
		data = json.loads(r.text)
		return data['refresh_token']
		# TODO: Could also get access token and store it along with expiry time, since it's good for 1 hour

	def get_access_token(self, refresh_token):
		data = {'client_id': self.__client_id__, 'redirect_uri': 'https://login.live.com/oauth20_desktop.srf', 'client_secret': self.__client_secret__, 'refresh_token':refresh_token, 'grant_type':'refresh_token'}
		headers = {'Content-Type': 'application/x-www-form-urlencoded'}
		r = requests.post('https://login.live.com/oauth20_token.srf', data=data, headers=headers)
		data = json.loads(r.text)
		return data['access_token']
		#Add abiliy to store new refresh token.

	def parse_response(self, response):
		parsed = parse_qs(urlparse(response).query)['code'][0]
		return parsed

	def load_refresh_token(self):
		refresh_token = None
		try:
			with open('onedrive_settings.json', 'r') as f:
				config = json.load(f)
				refresh_token = config['refresh_token']
		except IOError:
			pass
		
		if refresh_token is not None:
			return refresh_token

		parameters = {'client_id': self.__client_id__, 'scope': 'wl.offline_access onedrive.readwrite', 'response_type': 'code', 'redirect_uri': 'https://login.live.com/oauth20_desktop.srf'}
		print("Go to this URL to authorize.  Input the redirected URL: https://login.live.com/oauth20_authorize.srf?" + urllib.urlencode(parameters))

		response = raw_input("Enter the URL you were redirected to: ")
		code = self.parse_response(response)
		refresh_token = self.get_refresh_token_from_code(code)

		if (refresh_token is None):
			logging.warning("Unable to get refresh token")
			return None

		config = {'refresh_token': refresh_token}
		with open('onedrive_settings.json', 'w') as f:
			json.dump(config, f)

		return refresh_token

	def upload(self, file_name, destination=None, modified_time= None, create_folder = False):
		print "Upload {} OneDrive Storage Service".format(file_name)
		print "Function incomplete"
		

	def open_if_not_exists(self, filename):
		try:
			fd = os.open(filename, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
		except:
			return None
		fobj = os.fdopen(fd, "wb")
		return fobj

	def download(self, file_path, destination=None):
		print "Download {} OneDrive Storage Service".format(file_path)
		
		refresh_token = self.load_refresh_token()
		access_token = self.get_access_token(refresh_token)

		url = self.onedrive_url_root+"/drive/root:/"+urllib.quote(file_path)+":/content"
		logging.info("URL to save file is: "+url)
		headers = {'Authorization':"bearer " +access_token}
		response = requests.get(url, headers=headers, stream = True)
		tries = 0
		while response.status_code != requests.codes.ok and tries < 6:
			tries+=1
			logging.info("Save File: OneDrive connection failed Error: "+ response.text)
			logging.info("Retry "+ str(tries))
			sleep_length = float(1 << tries) / 2
			time.sleep(sleep_length)
			response = requests.get(url, headers=headers, stream = True)
			
		if response.status_code != requests.codes.ok:
			raise RuntimeError("Unable to access onedrive file")

		filename = file_path.split('/')[-1]
		f = self.open_if_not_exists(filename)
		if f is None: 
			print "Unable to save file.  It may already exist."
			return
		size = 0;
		for chunk in response.iter_content(chunk_size=1024*1024):
			if chunk: # filter out keep-alive new chunks
				f.write(chunk)
				f.flush()
				size = size +  1
				if size % 200 == 0:
					logging.info(str(size) + "MB written")
		os.fsync(f.fileno())
		f.close()

		lastModifiedDateTimeString = self.get_modified_time(file_path) 
		modifiedDate = parse(lastModifiedDateTimeString)
		
		os.utime(filename, (time.mktime(modifiedDate.timetuple()),time.mktime(modifiedDate.timetuple())))
		
		print filename + " has been saved to disk"
		# TODO: deal with return values.
		return (filename, lastModifiedDateTimeString)
		

	# Due to a issue with OneDrive API, Modified time doesn't match time in Web or Desktop OneDrive Clients
	def get_modified_time(self, file_path):
		refresh_token = self.load_refresh_token()
		access_token = self.get_access_token(refresh_token)

		headers = {'Authorization':"bearer " +access_token}
		if file_path.endswith('/'):
			file_path = file_path[:-1]

		url = self.onedrive_url_root+"/drive/root:/"+urllib.quote(file_path)

		response = requests.get(url, headers=headers)
		tries = 0
		while response.status_code != requests.codes.ok and tries < 6:
			tries+=1
			logging.info("OneDrive connection failed Error: "+ response.text)
			logging.info("Attempt: "+ str(tries))
			sleep_length = float(1 << tries) / 2
			time.sleep(sleep_length)
			response = requests.get(url, headers=headers)

		if response.status_code != requests.codes.ok:
			raise RuntimeError("Unable to access OneDrive file metadata.")
		data = json.loads(response.text)
		
		if "lastModifiedDateTime" not in data:
			raise RuntimeError("Last Modified date/time does not exist")
		return data["lastModifiedDateTime"]


	def is_folder(self, folder_path):
		pass
		
	
	def list_folder(self, folder_path):
		pass

	
