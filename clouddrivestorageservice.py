# Copyright (C) 2015 Darryl Tam <contact@darryltam.com>

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

from requests_toolbelt import MultipartEncoder
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

    cloud_drive_url_root = "https://drive.amazonaws.com"
    cloud_drive_end_point = None
    content_url = None
    metadata_url = None
    root_folder = None

    def authorize(self):
        logging.debug("Authorize OneDrive Storage Service")

        with open('cloud_drive_client_secrets.json', 'r') as f:
            config = json.load(f)
            self.__client_id__ = config['client_id']
            self.__client_secret__ = config['client_secret']
            self.__return_uri__ = config['return_uri']
        # If there's an error loading file, tell the user, as ask for client_id
        # and secret

        # TODO: Store refresh token in class and check expiry
        refresh_token = self.load_refresh_token()
        access_token = self.get_access_token(refresh_token)
        self.load_end_points(access_token)
        self.load_root_folder(access_token)
        print "refresh token: " + refresh_token
        print "access token: " + access_token

    def get_refresh_token_from_code(self, code):
        data = {'client_id': self.__client_id__,
                'redirect_uri': self.__return_uri__,
                'client_secret': self.__client_secret__,
                'code': code,
                'grant_type': 'authorization_code'}
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        r = requests.post('https://api.amazon.com/auth/o2/token',
                          data=data,
                          headers=headers)
        data = json.loads(r.text)
        return data['refresh_token']
        # TODO: Could also get access token and store it along with expiry time
        # , since it's good for 1 hour

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

        parameters = {'client_id': self.__client_id__,
                      'scope': 'clouddrive:read clouddrive:write',
                      'response_type': 'code',
                      'redirect_uri': self.__return_uri__}
        print(("Go to this URL to authorize.  Input the redirected URL: "
               "https://www.amazon.com/ap/oa?")
              + urllib.urlencode(parameters))

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
        data = {'client_id': self.__client_id__,
                'redirect_uri': self.__return_uri__,
                'client_secret': self.__client_secret__,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token'}
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        r = requests.post('https://api.amazon.com/auth/o2/token',
                          data=data,
                          headers=headers)
        data = json.loads(r.text)
        return data['access_token']
        # Add abiliy to store new refresh token.

    def load_end_points(self, access_token):
        headers = {}
        headers['Authorization'] = "Bearer " + access_token
        r = requests.get(self.cloud_drive_url_root +
                         '/drive/v1/account/endpoint',
                         headers=headers)
        if r.status_code is not requests.codes.ok:
            print r.status_code
            print r.text
            raise RuntimeError("Error getting endpoints")
        data = json.loads(r.text)
        if data['customerExists'] is not True:
            raise RuntimeError("Error with account")
        self.content_url = data['contentUrl']
        self.metadata_url = data['metadataUrl']

    def load_root_folder(self, access_token):
        headers = {}
        headers['Authorization'] = "Bearer " + access_token
        r = requests.get(self.metadata_url +
                         '/nodes?filters=isRoot:true',
                         headers=headers)
        if r.status_code is not requests.codes.ok:
            print r.status_code
            print r.text
            raise RuntimeError("Error getting endpoints")
        data = json.loads(r.text)
        if 'data' not in data:
            raise RuntimeError("Error getting root folder")
        self.root_folder = data['data'][0]['id']

    def upload(self, file_path, destination=None,
               modified_time=None, create_folder=False, overwrite=False):
        # TODO: Stream request for large files
        refresh_token = self.load_refresh_token()
        access_token = self.get_access_token(refresh_token)

        print "Upload {} Cloud Drive Storage Service".format(file_path)

        destination_id = self.root_folder
        if destination is not None:
            destination_id = self.get_folder(self.root_folder,
                                             destination,
                                             create_folder)

        file_name = os.path.basename(file_path)
        file_id = self.get_file(destination_id, file_name)

        if file_id is None:
            url = self.content_url + "/nodes?suppress=deduplication"
            headers = {}
            headers['Authorization'] = "Bearer " + access_token

            metadata = {}
            metadata['name'] = file_name
            metadata['kind'] = "FILE"
            metadata['parents'] = [destination_id]

            mime_type = guess_type(file_path)[0]
            mime_type = mime_type if mime_type else 'application/octet-stream'

            content = MultipartEncoder(
                fields=[('metadata', ("", json.dumps(metadata))),
                        ('content', (file_name,
                                     open(file_path, 'rb'),
                                     mime_type))])

            headers["Content-Type"] = content.content_type

            r = requests.post(url,
                             headers=headers, data=content)

            if r.status_code is not requests.codes.created:
                print "Status: "+ str(r.status_code)

                raise RuntimeError("Error uploading file")
        else:
            if overwrite is False:
                raise RuntimeError("File: {} exists, but overwrite is not set".format(file_name))
            url = self.content_url + "/nodes/"+file_id+"/content"
            headers = {}
            headers['Authorization'] = "Bearer " + access_token

            mime_type = guess_type(file_path)[0]
            mime_type = mime_type if mime_type else 'application/octet-stream'

            content = MultipartEncoder(
                fields=[('content',
                        (file_name, open(file_path, 'rb'), mime_type))])

            headers["Content-Type"] = content.content_type

            r = requests.put(url,
                             headers=headers, data=content)

            if r.status_code is not requests.codes.ok:
                print "Status: " + str(r.status_code)
                raise RuntimeError("Error uploading file")
        print u"{} successfully uploaded".format(file_name)

    def get_folder(self, cur_folder, folder_path, create=False):
        refresh_token = self.load_refresh_token()
        access_token = self.get_access_token(refresh_token)

        if folder_path.endswith('/'):
            folder_path = folder_path[:-1]

        split_path = folder_path.split('/')
        # cur_path = cur_folder
        create_rest = False
        while len(split_path) > 0:
            cur_item = split_path.pop(0)
            data = None
            if create_rest is False:
                headers = {}
                headers['Authorization'] = "Bearer " + access_token
                r = requests.get(self.metadata_url + '/nodes/'
                                 + cur_folder + '/children',
                                 params={'filters': 'name:'+cur_item},
                                 headers=headers)
                print "get Folder: " + folder_path
                print "cur_item:"+cur_item
                print r.status_code
                print r.text

                if r.status_code is not requests.codes.ok:
                    raise RuntimeError("Error getting folder")
                data = json.loads(r.text)
                if 'data' not in data:
                    raise RuntimeError("Error getting folder " + cur_item)

            if create_rest is True or len(data['data']) == 0:
                if create is False:
                    raise ItemDoesNotExistError("Error: Folder {} does not exist and createfolder is not set.".format(cur_item))
                url = self.metadata_url + "/nodes"

                headers = {}
                headers['Authorization'] = "Bearer " + access_token

                metadata = {}
                metadata['name'] = cur_item
                metadata['kind'] = "FOLDER"
                metadata['parents'] = [cur_folder]

                # data = [('metadata', ("", json.dumps(metadata)))]
                data = json.dumps(metadata)

                r = requests.post(url, headers=headers, data=data)

                print "Text: "+ r.text
                if r.status_code is not requests.codes.created:
                    print "Status: "+ str(r.status_code)
                    # print "The request that was sent was:"
                    # req = requests.Request('POST',url,headers=headers,files=files).prepare()
                    # print req.body

                    raise RuntimeError("Error creating folder")
                data = json.loads(r.text)
                cur_folder = data['id']
            elif len(data['data']) > 1:
                raise RuntimeError("Error: Multiple items with name: " +
                                   cur_item)
            else:
                if data['data'][0]['kind'] != "FOLDER":
                    raise RuntimeError("Error: {} is not a folder."
                                       .format(cur_item))
                cur_folder = data['data'][0]['id']

        return cur_folder

    def get_file(self, folder_id, file_name):
        refresh_token = self.load_refresh_token()
        access_token = self.get_access_token(refresh_token)

        headers = {}
        headers['Authorization'] = "Bearer " + access_token
        r = requests.get(self.metadata_url + '/nodes/'
                         + folder_id + '/children',
                         params={'filters': 'name:'+file_name},
                         headers=headers)
        # print "get Folder: " + folder_path
        # print "cur_item:"+cur_item
        # print r.status_code
        # print r.text

        if r.status_code is not requests.codes.ok:
            raise RuntimeError("Error getting file")
        data = json.loads(r.text)
        if 'data' not in data:
            raise RuntimeError("Error getting file " + file_name)
        if (len(data['data']) == 0):
            return None
        elif len(data['data']) > 1:
            raise RuntimeError("Error: Multiple items with name: " +
                               file_name)

        if data['data'][0]['kind'] != "FILE":
            raise RuntimeError("Error: {} exists, but is not a file."
                               .format(file_name))

        return data['data'][0]['id']

    def download(self, file_path, destination=None, overwrite=False):
        raise ValueError("This is not implemented yet")

    def download_item(self, cur_file, destination=None, overwrite=False):
        raise ValueError("This is not implemented yet")

    def create_folder(self, folder_path):
        self.get_folder(self.root_folder, folder_path, create=True)

    def is_folder(self, folder_path):
        try:
            result = self.get_folder(self.root_folder, folder_path, create=False)
            if result is None:
                return False
            return True
        except ItemDoesNotExistError:
            return False

    def list_folder(self, folder_path):
        raise ValueError("This is not implemented yet")

    def get_file_name(self, file):
        raise ValueError("This is not implemented yet")

    def is_folder_from_file_type(self, file):
        raise ValueError("This is not implemented yet")
