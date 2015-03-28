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

	def upload(self, file_path, destination=None, modified_time= None, create_folder = False, overwrite=False):
		print "Upload {} OneDrive Storage Service".format(file_path)
		
		refresh_token = self.load_refresh_token()
		access_token = self.get_access_token(refresh_token)
		
		full_remote_path =os.path.basename(file_path)
		if destination is not None:
			if self.is_folder(destination) is False:
				raise RunTimeError("Destination folder not valid")
			if destination.endswith('/') is False:
				destination = destination+"/"
			full_remote_path=destination+full_remote_path


		file_size = os.path.getsize(file_path)

		payload = {}
		payload["@name.conflictBehavior"] = "fail"
		if overwrite is True:
			payload["@name.conflictBehavior"] = "replace"
		# Special case for empty file
		if file_size == 0:
			headers = {}
			headers['Authorization']="bearer " +access_token
			response = requests.put(self.onedrive_url_root+"/drive/root:/"+urllib.quote(full_remote_path)+":/content", headers=headers, data="", params=payload)
			# TODO: Don't retry if 409 error received that it already exists
			if response.status_code not in (requests.codes.ok, requests.codes.created, requests.codes.accepted):
				tries = 1;
				while tries < 6 and response.status_code not in (requests.codes.ok, requests.codes.created):
					print response.status_code
					print "Onedrive connection failed Error: "+ response.text
					if response.status_code in (requests.codes.conflict,):
						raise RuntimeError("Unable to complete OneDrive upload")
					print "Retry "+ str(tries)
					if response.headers is not None and 'Retry-After' in response.headers:
						print "retry after requested, value: " + response.headers['Retry-After']
					sleep_length = float(1 << tries) / 2
					time.sleep(sleep_length)
					response = requests.put(self.onedrive_url_root+"/drive/root:/"+urllib.quote(full_remote_path)+":/content", headers=headers, data="", params=payload)
					tries = tries+1
				if response.status_code not in (requests.codes.ok, requests.codes.created):
					raise RuntimeError("Unable to complete upload session for onedrive")
			print response.status_code
			print response.text
			return 
			

		headers = {'Authorization':"bearer " +access_token, 'Content-Type':"application/json"}
		
		
		print "Payload: "+str(payload)
		response = requests.post(self.onedrive_url_root+"/drive/root:/"+urllib.quote(full_remote_path)+":/upload.createSession", headers=headers, data=json.dumps(payload))
		if response.status_code != requests.codes.ok:
			tries = 1;
			while tries < 6 and response.status_code != requests.codes.ok:
				print "Onedrive connection failed Error: "+ response.text
				print "Retry "+ str(tries)
				sleep_length = float(1 << tries) / 2
				time.sleep(sleep_length)
				response = requests.post(self.onedrive_url_root+"/drive/root:/"+urllib.quote(full_remote_path)+":/upload.createSession", headers=headers, data=json.dumps(payload))
				tries = tries+1
			if response.status_code != requests.codes.ok:
				raise RuntimeError("Unable to open upload session for onedrive")


		data = json.loads(response.text)

		# print "Upload Session created: "
		# print "uploadUrl: " + data["uploadUrl"]
		# print "expirationDateTime: " + data["expirationDateTime"]
		# print "nextExpectedRanges: " + str(data["nextExpectedRanges"])

		
		CHUNK_SIZE = 10*1024*1024
		chunk_start = 0
		chunk_end = CHUNK_SIZE - 1
		if chunk_end+1 >= file_size:
			chunk_end = file_size - 1
		response = None
		
		## TODO: Implement Retry-After 
		## TODO: Deal with insufficient Storage error (507)
		## TODO: Deal with other 400/500 series errors
		with open (file_path, "rb") as f:
			while chunk_start < file_size:
				chunk_data = f.read(CHUNK_SIZE)
				headers = {}
				headers['Authorization']="bearer " +access_token
				headers['Content-Length'] = str(file_size)
				headers['Content-Range'] = 'bytes {}-{}/{}'.format(chunk_start, chunk_end, file_size)
				response = requests.put(data["uploadUrl"], data = chunk_data, headers=headers)
				#TODO: Check for proper response based on location in file uploading.
				if response.status_code not in (requests.codes.ok, requests.codes.created, requests.codes.accepted):
					tries = 1;
					while tries < 6 and response.status_code not in (requests.codes.ok, requests.codes.created):
						print response.status_code
						print "Onedrive connection failed Error: "+ response.text
						if response.status_code in (requests.codes.conflict,):
							raise RuntimeError("Unable to complete upload session for onedrive")
						print "Retry "+ str(tries)
						if response.headers is not None and 'Retry-After' in response.headers:
							print "retry after requested, value: " + response.headers['Retry-After']
						sleep_length = float(1 << tries) / 2
						time.sleep(sleep_length)
						response = requests.put(data["uploadUrl"], data = chunk_data, headers=headers)
						tries = tries+1
					if response.status_code not in (requests.codes.ok, requests.codes.created):
						raise RuntimeError("Unable to complete upload session for onedrive")
				
				print "{} of {} bytes sent, {}% complete".format(str(chunk_end+1), str(file_size), str(float(chunk_end+1)/float(file_size)*100))
				chunk_start+=CHUNK_SIZE
				chunk_end+=CHUNK_SIZE
				if chunk_end+1 >= file_size:
					chunk_end = file_size - 1

		if response is not None:
			print response.status_code
			print response.text


	def download(self, file_path, destination=None, overwrite=False):
		print "Download {} OneDrive Storage Service".format(file_path)
		
		refresh_token = self.load_refresh_token()
		access_token = self.get_access_token(refresh_token)

		local_path = file_path.split('/')[-1]
		if destination is not None:
			local_path = os.path.join(destination, file_path)

		if os.path.isdir(local_path):
			raise RuntimeError("Local destination is a folder")
		if overwrite is False and os.path.isfile(local_path):
			raise RuntimeError("Local file {} exists.  Enable overwrite option to continue.".format(local_path))
		f = open(local_path, "wb")

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
		
		os.utime(local_path, (time.mktime(modifiedDate.timetuple()),time.mktime(modifiedDate.timetuple())))
		
		print local_path + " has been saved to disk"
		# TODO: deal with return values.
		return (local_path, lastModifiedDateTimeString)
		

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
		
		print data['file']['hashes']
		if "lastModifiedDateTime" not in data:
			raise RuntimeError("Last Modified date/time does not exist")
		return data["lastModifiedDateTime"]


	def is_folder(self, folder_path):
		refresh_token = self.load_refresh_token()
		access_token = self.get_access_token(refresh_token)

		if folder_path.endswith('/'):
			folder_path = folder_path[:-1]

		headers = {'Authorization':"bearer " +access_token}
		url = self.onedrive_url_root+"/drive/root:/"+urllib.quote(folder_path)
		tries = 0
		response = requests.get(url, headers=headers)
		while response.status_code != requests.codes.ok and tries < 6:
			logging.info("Error Status code: "+str(response.status_code))
			if response.status_code == 404:
				logging.info("Item not found: "+ folder_path)
				return False
			tries+=1
			logging.info("Onedrive connection failed Error: "+ response.text)
			logging.info("Attempt: "+ str(tries))
			sleep_length = float(1 << tries)
			time.sleep(sleep_length)
			response = requests.get(url, headers=headers)
		
		if response.status_code != requests.codes.ok:
			raise RuntimeError("Unable to access onedrive folder")
		
		data = json.loads(response.text)
		if "folder" in data:
			return True
		else:
			return False
		
	#TODO Implement this.
	def create_folder(self, folder_path):
		refresh_token = self.load_refresh_token()
		access_token = self.get_access_token(refresh_token)

		if folder_path.endswith('/'):
			folder_path = path[:-1]

		headers = {'Authorization':"bearer " +access_token}
		url = onedrive_url_root+"/drive/root:/"+urllib.quote(path)
		tries = 0
		response = requests.get(url, headers=headers)
		while response.status_code != requests.codes.ok and tries < 6:
			logging.info("Error Status code: "+str(response.status_code))
			if response.status_code == 404:
				logging.info("Item not found: "+ path)
				return False
			tries+=1
			logging.info("Onedrive connection failed Error: "+ response.text)
			logging.info("Attempt: "+ str(tries))
			sleep_length = float(1 << tries)
			time.sleep(sleep_length)
			response = requests.get(url, headers=headers)
		
		if response.status_code != requests.codes.ok:
			raise RuntimeError("Unable to access onedrive folder")
		
		data = json.loads(response.text)
		if "folder" in data:
			return True
		else:
			return False
	def list_folder(self, folder_path):
		pass

	
