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

class CloudDriveStorageService(StorageService):
    def authorize(self):
        logging.debug("Authorize OneDrive Storage Service")
    
        with open('cloud_drive_client_secrets.json', 'r') as f:
            config = json.load(f)
            self.__client_id__ = config['client_id']
            self.__client_secret__ = config['client_secret']
            self.__return_uri__ = config['return_uri']
        # If there's an error loading file, tell the user, as ask for client_id and secret
            
        # TODO: Store refresh token in class and check expiry
        refresh_token = self.load_refresh_token()
        access_token = self.get_access_token(refresh_token)
        print "refresh token: "+ refresh_token
        print "access token: "+ access_token

    def get_refresh_token_from_code(self, code):
        data = {'client_id': self.__client_id__, 'redirect_uri': self.__return_uri__, 'client_secret': self.__client_secret__, 'code':code, 'grant_type':'authorization_code'}
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        r = requests.post('https://api.amazon.com/auth/o2/token', data=data, headers=headers)
        data = json.loads(r.text)
        return data['refresh_token']
        # TODO: Could also get access token and store it along with expiry time, since it's good for 1 hour

    def parse_response(self, response):
        parsed = parse_qs(urlparse(response).query)['code'][0]
        return parsed

    def load_refresh_token(self):
        refresh_token = None
        try:
            with open('cloud_drive_settings.json', 'r') as f:
                config = json.load(f)
                refresh_token = config['refresh_token']
        except IOError:
            pass
        
        if refresh_token is not None:
            return refresh_token

        parameters = {'client_id': self.__client_id__, 'scope': 'clouddrive:read clouddrive:write', 'response_type': 'code', 'redirect_uri': self.__return_uri__}
        print("Go to this URL to authorize.  Input the redirected URL: https://www.amazon.com/ap/oa?" + urllib.urlencode(parameters))

        response = raw_input("Enter the URL you were redirected to: ")
        code = self.parse_response(response)
        refresh_token = self.get_refresh_token_from_code(code)

        if (refresh_token is None):
            logging.warning("Unable to get refresh token")
            return None

        config = {'refresh_token': refresh_token}
        with open('cloud_drive_settings.json', 'w') as f:
            json.dump(config, f)

        return refresh_token
    
    def get_access_token(self, refresh_token):
        data = {'client_id': self.__client_id__, 'redirect_uri': self.__return_uri__, 'client_secret': self.__client_secret__, 'refresh_token':refresh_token, 'grant_type':'refresh_token'}
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        r = requests.post('https://api.amazon.com/auth/o2/token', data=data, headers=headers)
        data = json.loads(r.text)
        return data['access_token']
        #Add abiliy to store new refresh token.

    def upload(self, file_path, destination=None, modified_time= None, create_folder=False, overwrite=False):
        raise ValueError("This is not implemented yet")
        pass

    def download(self, file_path, destination=None, overwrite = False):
        raise ValueError("This is not implemented yet")
        

    def download_item(self, cur_file, destination=None, overwrite=False):
        raise ValueError("This is not implemented yet")
        

    def create_folder(self, folder_path):
        raise ValueError("This is not implemented yet")
        

    def is_folder(self, folder_path):
        raise ValueError("This is not implemented yet")
        

    def list_folder(self, folder_path):
        raise ValueError("This is not implemented yet")
        

    def get_file_name(self, file):
        raise ValueError("This is not implemented yet")
        

    def is_folder_from_file_type(self, file):
        raise ValueError("This is not implemented yet")
        