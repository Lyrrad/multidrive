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
import urllib
from urllib.parse import urlparse, parse_qs
import os
from enum import Enum

import logging

import time

from storageservice import StorageService


class ItemDoesNotExistError(RuntimeError):
    pass


class RemoteConnectionError(RuntimeError):
    pass


class UTC(datetime.tzinfo):
    """UTC"""

    def utcoffset(self, dt):
        return datetime.timedelta(0)

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return datetime.timedelta(0)


class RequestType(Enum):
    GET = 0
    PUT = 1
    POST = 2


class OneDriveStorageService(StorageService):

    onedrive_url_root = "https://api.onedrive.com/v1.0"

    def authorize(self):
        logger = logging.getLogger("multidrive")
        logger.debug("Authorize OneDrive Storage Service")

        with open('onedrive_client_secrets.json', 'r') as f:
            config = json.load(f)
            self.__client_id__ = config['client_id']
            self.__client_secret__ = config['client_secret']
        # TODO: If there's an error loading file, tell the user, and
        # ask for client_id and secret

        self.load_tokens()

    def get_tokens_from_code(self, code):
        data = {'client_id': self.__client_id__,
                'redirect_uri': 'https://login.live.com/oauth20_desktop.srf',
                'client_secret': self.__client_secret__,
                'code': code,
                'grant_type': 'authorization_code'}
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        url = 'https://login.live.com/oauth20_token.srf'
        response = self.http_request(url=url,
                                     request_type=RequestType.POST,
                                     status_codes=(requests.codes.ok,),
                                     headers=headers,
                                     data=data,
                                     use_access_token=False,
                                     action_string="OneDrive Get Tokens "
                                     "From Code")
        data = json.loads(response.text)
        return (data['refresh_token'],
                data['access_token'],
                int(data['expires_in']))

    def http_request(self, url, request_type, status_codes=(), headers={},
                     stream=False, data="", params=None,
                     severe_status_codes=(),
                     use_access_token=False, action_string="OneDrive HTTP",
                     max_tries=6):
        logger = logging.getLogger("multidrive")

        if use_access_token is True:
            headers['Authorization'] = "Bearer " + self.get_access_token()

        if request_type == RequestType.GET:
            response = requests.get(url, headers=headers, params=params,
                                    stream=stream)
        elif request_type == RequestType.PUT:
            response = requests.put(url, headers=headers, data=data,
                                    params=params)
        elif request_type == RequestType.POST:
            response = requests.post(url, headers=headers, data=data)

        tries = 0
        while (response.status_code not in status_codes
               and tries < max_tries):
            tries += 1
            logger.warning("{}: Connection failed Code: {}"
                           .format(action_string, str(response.status_code)))
            logger.warning("Error: {}".format(response.text))
            logger.warning("Headers: {}".format(str(response.headers)))
            logger.warning("Retry " + str(tries))

            sleep_length = float(1 << tries) / 2

            if 'Retry-After' in response.headers:
                logger.warning("Server requested wait of {} seconds".
                               format(response.headers['Retry-After']))
                sleep_length = int(response.headers['Retry-After'])
            elif response.status_code in severe_status_codes:
                logger.warning("Server Error, increasing wait time")
                sleep_length *= 20
            logger.warning("Waiting {} second(s) for next attempt"
                           .format(str(sleep_length)))

            time.sleep(sleep_length)
            # Force refresh of token once in case it's expired
            if (tries == 1):
                self.refresh_access_token()

            if use_access_token is True:
                headers['Authorization'] = "Bearer " + self.get_access_token()

            if request_type == RequestType.GET:
                response = requests.get(url, headers=headers, params=params,
                                        stream=stream)
            elif request_type == RequestType.PUT:
                requests.put(url, headers=headers, data=data, params=params)
            elif request_type == RequestType.POST:
                requests.post(url, headers=headers, data=data)

        if response.status_code not in status_codes:
            logger.warning("{}: Connection failed Code: {}"
                           .format(action_string, str(response.status_code)))
            logger.warning("Error: {}".format(response.text))
            logger.warning("Headers: {}".format(str(response.headers)))
            logger.warning("Retry " + str(tries))
            raise RemoteConnectionError("{}: Unable to complete request."
                                        .format(action_string))

        return response

    def get_access_token(self):
        now = datetime.datetime.utcnow()
        if (now > self.__token__expiry__):
            self.refresh_access_token()
        return self.__access_token__

    def refresh_access_token(self):
        data = {'client_id': self.__client_id__,
                'redirect_uri': 'https://login.live.com/oauth20_desktop.srf',
                'client_secret': self.__client_secret__,
                'refresh_token': self.__refresh_token__,
                'grant_type': 'refresh_token'}
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        url = 'https://login.live.com/oauth20_token.srf'
        response = self.http_request(url=url,
                                     request_type=RequestType.POST,
                                     status_codes=(requests.codes.ok,),
                                     headers=headers,
                                     data=data,
                                     use_access_token=False,
                                     action_string="OneDrive Refresh Access"
                                     "Token")

        data = json.loads(response.text)
        self.set_access_token(data['access_token'], int(data['expires_in']))
        return

    def set_access_token(self, access_token, expiry):
        self.__access_token__ = access_token
        self.__token__expiry__ = (datetime.datetime.utcnow() +
                                  datetime.timedelta(seconds=(expiry-60)))

    def load_tokens(self):
        # logger = logging.getLogger("multidrive")
        refresh_token = None
        try:
            with open('onedrive_settings.json', 'r') as f:
                config = json.load(f)
                refresh_token = config['refresh_token']
        except IOError:
            pass

        if refresh_token is not None:
            self.__refresh_token__ = refresh_token
            self.refresh_access_token()
            return

        parameters = {'client_id': self.__client_id__,
                      'scope': 'wl.offline_access onedrive.readwrite',
                      'response_type': 'code',
                      'redirect_uri':
                      'https://login.live.com/oauth20_desktop.srf'}
        print("Go to this URL to authorize.  Input the redirected URL: "
              "https://login.live.com/oauth20_authorize.srf?" +
              urllib.urlencode(parameters))

        response = input("Enter the URL you were redirected to: ")
        code = parse_qs(urlparse(response).query)['code'][0]
        (refresh_token, access_token, expiry) = self.get_tokens_from_code(code)

        if (refresh_token is None):
            raise RuntimeError("Unable to get refresh token")

        config = {'refresh_token': refresh_token}
        with open('onedrive_settings.json', 'w') as f:
            json.dump(config, f)
        self.__refresh_token__ = refresh_token
        self.set_access_token(access_token, expiry)
        return

    def upload(self, file_path, destination=None, modified_time=None,
               create_folder=False, overwrite=False):
        logger = logging.getLogger("multidrive")
        logger.info("Upload {} OneDrive Storage Service".format(file_path))

        file_name = os.path.basename(file_path)
        full_remote_path = file_name
        if destination is not None:
            if self.is_folder(destination) is False:
                if create_folder is False:
                    raise RuntimeError("Destination folder not valid")
                self.create_folder(destination)

            if destination.endswith('/') is False:
                destination = destination+"/"
            full_remote_path = destination+full_remote_path

        file_size = os.path.getsize(file_path)

        payload = {}
        payload["@name.conflictBehavior"] = "fail"
        if overwrite is True:
            payload["@name.conflictBehavior"] = "replace"

        # Special case for empty file
        if file_size == 0:
            url = (self.onedrive_url_root+"/drive/root:/" +
                   urllib.parse.quote(full_remote_path)+":/content")
            response = self.http_request(url=url,
                                         request_type=RequestType.PUT,
                                         status_codes=(requests.codes.ok,
                                                       requests.codes.created,
                                                       requests.codes.accepted,
                                                       requests.codes.
                                                       conflict),
                                         data="",
                                         params=payload,
                                         use_access_token=True,
                                         action_string="Upload")

            if response.status_code in (requests.codes.conflict,):
                raise RuntimeError("File already exists")
            logger.info("Upload complete")
            return

        headers = {'Content-Type': "application/json"}

        logger.warning("Payload: " + str(payload))

        url = (self.onedrive_url_root+"/drive/root:/" +
               urllib.parse.quote(full_remote_path)+":/upload.createSession")
        response = self.http_request(url=url,
                                     request_type=RequestType.POST,
                                     status_codes=(requests.codes.ok,),
                                     headers=headers,
                                     data=json.dumps(payload),
                                     use_access_token=True,
                                     action_string="Upload",)

        data = json.loads(response.text)

        CHUNK_SIZE = 4*1024*1024
        chunk_start = 0
        chunk_end = CHUNK_SIZE - 1
        if chunk_end+1 >= file_size:
            chunk_end = file_size - 1
        response = None

        url = data['uploadUrl']

        # TODO: Deal with insufficient Storage error (507)
        # TODO: Deal with other 400/500 series errors
        with open(file_path, "rb") as f:
            while chunk_start < file_size:
                chunk_data = f.read(CHUNK_SIZE)
                headers = {}
                headers['Content-Length'] = str(file_size)
                headers['Content-Range'] = 'bytes {}-{}/{}'.format(chunk_start,
                                                                   chunk_end,
                                                                   file_size)
                status_codes = (requests.codes.ok,
                                requests.codes.created,
                                requests.codes.accepted,
                                requests.codes.conflict)
                response = self.http_request(url=data["uploadUrl"],
                                             request_type=RequestType.PUT,
                                             headers=headers,
                                             status_codes=status_codes,
                                             data=chunk_data,
                                             use_access_token=True,
                                             action_string="Upload Chunk")
                # TODO: Check for proper response based on
                # location in file uploading.

                if response.status_code in (requests.codes.conflict,):
                    raise RuntimeError("File Already Exists")

                logger.info("{} of {} bytes sent, {}% complete"
                            .format(str(chunk_end+1),
                                    str(file_size),
                                    str(float(chunk_end+1)
                                        / float(file_size)*100)))
                chunk_start += CHUNK_SIZE
                chunk_end += CHUNK_SIZE
                if chunk_end+1 >= file_size:
                    chunk_end = file_size - 1

        if response is not None:
            logger.info(response.status_code)
            logger.info(response.text)
        print("Upload of file {} complete".format(os.path.basename(file_name)))

    def download_helper(self, url, local_path):
        logger = logging.getLogger("multidrive")
        f = open(local_path, "wb")

        logger.info("URL to save file is: "+url)

        status_codes = (requests.codes.ok,)
        severe_status_codes = (requests.codes.bandwidth_limit_exceeded,
                               requests.codes.service_unavailable)
        response = self.http_request(url=url,
                                     request_type=RequestType.GET,
                                     status_codes=status_codes,
                                     stream=True,
                                     severe_status_codes=severe_status_codes,
                                     use_access_token=True,
                                     action_string="Download file",
                                     max_tries=8)

        size = 0
        for chunk in response.iter_content(chunk_size=4*1024*1024):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
                f.flush()
                size = size + 1
                if size % 200 == 0:
                    logger.info(str(size)*4 + "MB written")
        os.fsync(f.fileno())
        f.close()

    def download_item(self, cur_file, destination=None, overwrite=False,
                      create_folder=False):
        local_path = cur_file['name']
        if destination is not None:
            local_path = os.path.join(destination, local_path)

        if 'folder' in cur_file:
            if not os.path.exists(local_path):
                # Add proper error message here?
                os.mkdir(local_path)
            return (local_path, cur_file['lastModifiedDateTime'])

        if os.path.isdir(local_path):
            raise RuntimeError("Local destination is a folder")
        if overwrite is False and os.path.isfile(local_path):
            raise RuntimeError("Local file {} exists.  Enable overwrite "
                               "option to continue.".format(local_path))
        url = self.onedrive_url_root+"/drive/items/"+cur_file['id']+"/content"

        self.download_helper(url, local_path)

        lastModifiedDateTimeString = cur_file['lastModifiedDateTime']
        modifiedDate = parse(lastModifiedDateTimeString)

        os.utime(local_path, (time.mktime(modifiedDate.timetuple()),
                              time.mktime(modifiedDate.timetuple())))

        print(local_path + " has been saved to disk")
        # TODO: deal with return values.
        return (local_path, lastModifiedDateTimeString)

    def download(self, file_path, destination=None, overwrite=False):
        print("Download {} OneDrive Storage Service".format(file_path))

        local_path = file_path.split('/')[-1]

        if destination is not None:
            local_path = os.path.join(destination, local_path)

        if os.path.isdir(local_path):
            raise RuntimeError("Local destination is a folder")
        if overwrite is False and os.path.isfile(local_path):
            raise RuntimeError("Local file {} exists.  Enable overwrite "
                               "option to continue.".format(local_path))

        url = (self.onedrive_url_root+"/drive/root:/" +
               urllib.parse.quote(file_path)+":/content")

        self.download_helper(url, local_path)

        lastModifiedDateTimeString = self.get_modified_time(file_path)
        modifiedDate = parse(lastModifiedDateTimeString)

        os.utime(local_path, (time.mktime(modifiedDate.timetuple()),
                              time.mktime(modifiedDate.timetuple())))

        print(local_path + " has been saved to disk")
        # TODO: deal with return values.
        return (local_path, lastModifiedDateTimeString)

    # Due to a issue with OneDrive API, Modified time doesn't match time in
    # Web or Desktop OneDrive Clients
    def get_modified_time(self, file_path):
        if file_path.endswith('/'):
            file_path = file_path[:-1]

        url = (self.onedrive_url_root+"/drive/root:/" +
               urllib.parse.quote(file_path))

        status_codes = (requests.codes.ok,)
        response = self.http_request(url=url,
                                     request_type=RequestType.GET,
                                     status_codes=status_codes,
                                     use_access_token=True,
                                     action_string="Get Modified Time",
                                     max_tries=8)

        data = json.loads(response.text)

        if "lastModifiedDateTime" not in data:
            raise RuntimeError("Last Modified date/time does not exist")
        return data["lastModifiedDateTime"]

    def is_folder(self, folder_path):
        result = self.get_item(folder_path)
        if result is None:
            return False
        return "folder" in result

    def get_item(self, item_path):
        logger = logging.getLogger("multidrive")

        if item_path.endswith('/'):
            item_path = item_path[:-1]

        url = (self.onedrive_url_root+"/drive/root:/" +
               urllib.parse.quote(item_path))

        status_codes = (requests.codes.ok,
                        requests.codes.not_found)

        response = self.http_request(url=url,
                                     request_type=RequestType.GET,
                                     status_codes=status_codes,
                                     use_access_token=True,
                                     action_string="Get Item",
                                     max_tries=8)

        if response.status_code == requests.codes.not_found:
            logger.info("Item not found: " + item_path)
            return None

        return json.loads(response.text)

    def create_folder(self, folder_path):
        logger = logging.getLogger("multidrive")

        if folder_path.endswith('/'):
            folder_path = folder_path[:-1]

        split_path = folder_path.split('/')
        cur_path = ""
        while len(split_path) > 0:

            prev_path = cur_path
            cur_item = split_path.pop(0)
            if len(cur_path) is 0:
                cur_path += cur_item
            else:
                cur_path += "/"+cur_item
            if self.is_folder(cur_path):
                continue

            logger.info("prev_path: " + prev_path)
            logger.info("cur_item: " + cur_item)
            logger.info("cur_path: " + cur_path)
            headers = {'Content-Type': "application/json"}

            payload = {}
            payload["name"] = cur_item
            payload["folder"] = {}

            url = ""
            if prev_path == "":
                url = self.onedrive_url_root+"/drive/root/children"
            else:
                url = (self.onedrive_url_root+"/drive/root:/" +
                       urllib.parse.quote(prev_path)+":/children")
            logger.info("url: " + url)

            response = self.http_request(url=url,
                                         request_type=RequestType.POST,
                                         status_codes=(requests.codes.ok,
                                                       requests.codes.created,
                                                       requests.codes.accepted,
                                                       requests.codes.
                                                       not_found),
                                         headers=headers,
                                         data=json.dumps(payload),
                                         use_access_token=True,
                                         action_string="Create Folder",
                                         max_tries=6)

            if response.status_code == requests.codes.not_found:
                logger.info("Item not found: " + prev_path)
                return False
        return True

    def list_folder(self, folder_path):
        base_folder = None
        if folder_path is None:
            folder_path = ""
        base_folder = self.get_item(folder_path)

        if "folder" not in base_folder:
            raise RuntimeError("Invalid folder: "+folder_path)

        folder_list = self.get_folder_listing(base_folder, [], folder_path)
        return folder_list

    def get_folder_listing(self, cur_folder, path_list, current_path):
        logger = logging.getLogger("multidrive")

        print("Getting listing for {}".format(current_path))
        result_list = []
        if current_path.endswith('/'):
            current_path = current_path[:-1]
        url = (self.onedrive_url_root+"/drive/root:/" +
               urllib.parse.quote(current_path)+":/children")

        status_codes = (requests.codes.ok,
                        requests.codes.not_found)

        response = self.http_request(url=url,
                                     request_type=RequestType.GET,
                                     status_codes=status_codes,
                                     use_access_token=True,
                                     action_string="Get Folder Listing",
                                     max_tries=8)

        if response.status_code == requests.codes.not_found:
            logger.info("Item not found: " + current_path)
            raise RuntimeError("Item not found. Possible bad path: " +
                               current_path)

        data = json.loads(response.text)
        for current_item in data['value']:
            result_list.append((current_item, path_list))
            if "folder" in current_item:
                new_list = list(path_list)
                new_list.append(current_item['name'])
                result_list.extend(
                    self.get_folder_listing(current_item, new_list,
                                            current_path+'/' +
                                            current_item['name']))
        return result_list

    def get_file_name(self, file):
        return file['name']

    def is_folder_from_file_type(self, file):
        return "folder" in file
