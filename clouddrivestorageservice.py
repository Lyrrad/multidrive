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
import urllib.parse
import os

import logging
from mimetypes import guess_type

from requests_toolbelt import MultipartEncoder
import time

from storageservice import StorageService
from enum import Enum
import hashlib


class ItemDoesNotExistError(RuntimeError):
    pass


class WrongTypeError(RuntimeError):
    pass


class RemoteConnectionError(RuntimeError):
    pass


class RequestType(Enum):
    GET = 0
    PUT = 1
    POST = 2


class HashFile(object):
    def set_file(self, cur_file):
        self.file = cur_file
        self.cur_file_hash = hashlib.md5()

    def __len__(self):
        pos = self.file.tell()
        self.file.seek(0, os.SEEK_END)
        length = self.file.tell()-pos
        self.file.seek(pos, os.SEEK_SET)
        return length

    def read(self, *args):
        chunk = self.file.read(*args)
        if len(chunk) > 0:
            self.cur_file_hash.update(chunk)
        return chunk

    def get_md5(self):
        return self.cur_file_hash.hexdigest()


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
        logger = logging.getLogger("multidrive")
        logger.debug("Authorize Cloud Drive Storage Service")

        with open('cloud_drive_client_secrets.json', 'r') as f:
            config = json.load(f)
            self.__client_id__ = config['client_id']
            self.__client_secret__ = config['client_secret']
            self.__return_uri__ = config['return_uri']
        # If there's an error loading file, tell the user, as ask for client_id
        # and secret

        self.load_tokens()
        self.load_end_points()
        self.load_root_folder()

    def http_request(self, url, request_type, status_codes=(), headers={},
                     stream=False, data="", params=None,
                     severe_status_codes=(),
                     use_access_token=False, action_string="OneDrive HTTP",
                     max_tries=6,
                     use_multipart_encoder=False,
                     multipart_encoder_fields=None,
                     multipart_encoder_content=None,
                     multipart_hash_file=None):
        logger = logging.getLogger("multidrive")

        if use_access_token is True:
            headers['Authorization'] = "Bearer " + self.get_access_token()

        if use_multipart_encoder is True:
            cur_multipart_file = open(multipart_encoder_content[1], 'rb')
            multipart_hash_file.set_file(cur_multipart_file)
            cur_multipart_content = ('content', (multipart_encoder_content[0],
                                                 multipart_hash_file,
                                                 multipart_encoder_content[2]))
            multipart_encoder_fields.append(cur_multipart_content)
            data = MultipartEncoder(fields=multipart_encoder_fields)
            headers["Content-Type"] = data.content_type

        try:
            if request_type == RequestType.GET:
                response = requests.get(url, headers=headers, params=params,
                                        stream=stream)
            elif request_type == RequestType.PUT:
                response = requests.put(url, headers=headers, data=data,
                                        params=params)
            elif request_type == RequestType.POST:
                response = requests.post(url, headers=headers, data=data)
            if use_multipart_encoder is True:
                logger.info("Current hash: "+multipart_hash_file.get_md5())
        except UnicodeDecodeError as err:
            logger.warning("UnicodeDecodeError: {}".format(err))
            response = None
        except requests.exceptions.ConnectionError as err:
            logger.warning("ConnectionError: {}".format(err))
            response = None
        finally:
            if use_multipart_encoder is True:
                cur_multipart_file.close()

        tries = 0
        while response is None or (response.status_code not in status_codes
                                   and tries < max_tries):
            tries += 1
            logger.warning("Retry " + str(tries))
            sleep_length = float(1 << tries) / 2

            if response is not None:
                logger.warning("{}: Connection failed Code: {}"
                               .format(action_string,
                                       str(response.status_code)))
                logger.warning("Error: {}".format(response.text))
                logger.warning("Headers: {}".format(str(response.headers)))

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

            if use_multipart_encoder is True:
                cur_multipart_file = open(multipart_encoder_content[1])
                multipart_hash_file.set_file(cur_multipart_file)
                cur_multipart_content = ('content',
                                         (multipart_encoder_content[0],
                                          multipart_hash_file,
                                          multipart_encoder_content[2]))
                multipart_encoder_fields.append(cur_multipart_content)
                data = MultipartEncoder(fields=multipart_encoder_fields)

            try:
                if request_type == RequestType.GET:
                    response = requests.get(url, headers=headers,
                                            params=params, stream=stream)
                elif request_type == RequestType.PUT:
                    response = requests.put(url, headers=headers, data=data,
                                            params=params)
                elif request_type == RequestType.POST:
                    response = requests.post(url, headers=headers, data=data)
            except UnicodeDecodeError as err:
                logger.warning("UnicodeDecodeError: {}".format(err))
                response = None
            except requests.exceptions.ConnectionError as err:
                logger.warning("ConnectionError: {}".format(err))
                response = None
            finally:
                if use_multipart_encoder is True:
                    cur_multipart_file.close()

        if response is None:
            raise RemoteConnectionError("{}: Unable to complete request."
                                        .format(action_string))
        if response.status_code not in status_codes:
            logger.warning("{}: Connection failed Code: {}"
                           .format(action_string, str(response.status_code)))
            logger.warning("Error: {}".format(response.text))
            logger.warning("Headers: {}".format(str(response.headers)))
            logger.warning("Retry " + str(tries))
            raise RemoteConnectionError("{}: Unable to complete request."
                                        .format(action_string))

        return response

    def get_tokens_from_code(self, code):
        data = {'client_id': self.__client_id__,
                'redirect_uri': self.__return_uri__,
                'client_secret': self.__client_secret__,
                'code': code,
                'grant_type': 'authorization_code'}
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        url = 'https://api.amazon.com/auth/o2/token'
        response = self.http_request(url=url,
                                     request_type=RequestType.POST,
                                     status_codes=(requests.codes.ok,),
                                     headers=headers,
                                     data=data, use_access_token=False,
                                     action_string="Cloud Drive Get Tokens "
                                     "From Code")
        data = json.loads(response.text)
        return (data['refresh_token'],
                data['access_token'],
                int(data['expires_in']))

    def load_tokens(self):
        refresh_token = None
        try:
            with open('cloud_drive_settings.json', 'r') as f:
                config = json.load(f)
                refresh_token = config['refresh_token']
        except IOError:
            pass

        if refresh_token is not None:
            self.__refresh_token__ = refresh_token
            self.refresh_access_token()
            return

        parameters = {'client_id': self.__client_id__,
                      'scope': 'clouddrive:read clouddrive:write',
                      'response_type': 'code',
                      'redirect_uri': self.__return_uri__}
        print(("Go to this URL to authorize.  Input the redirected URL: "
               "https://www.amazon.com/ap/oa?")
              + urllib.parse.urlencode(parameters))

        response = input("Enter the URL you were redirected to: ")
        code = urllib.parse.parse_qs(
            urllib.parse.urlparse(response).query)['code'][0]

        (refresh_token, access_token, expiry) = self.get_tokens_from_code(code)

        if (refresh_token is None):
            raise RuntimeError("Unable to get refresh token")

        config = {'refresh_token': refresh_token}
        with open('cloud_drive_settings.json', 'w') as f:
            json.dump(config, f)

        self.__refresh_token__ = refresh_token
        self.set_access_token(access_token, expiry)
        return

    def get_access_token(self):
        now = datetime.datetime.utcnow()
        if (now > self.__token__expiry__):
            self.refresh_access_token()
        return self.__access_token__

    def set_access_token(self, access_token, expiry):
        self.__access_token__ = access_token
        self.__token__expiry__ = (datetime.datetime.utcnow() +
                                  datetime.timedelta(seconds=(expiry-60)))

    def refresh_access_token(self):
        data = {'client_id': self.__client_id__,
                'redirect_uri': self.__return_uri__,
                'client_secret': self.__client_secret__,
                'refresh_token': self.__refresh_token__,
                'grant_type': 'refresh_token'}
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        url = 'https://api.amazon.com/auth/o2/token'
        response = self.http_request(url=url,
                                     request_type=RequestType.POST,
                                     status_codes=(requests.codes.ok,),
                                     headers=headers,
                                     data=data,
                                     use_access_token=False,
                                     action_string="Cloud Drive Refresh Access"
                                     " Token")

        data = json.loads(response.text)
        self.set_access_token(data['access_token'], int(data['expires_in']))
        return

    def load_end_points(self):
        url = self.cloud_drive_url_root + '/drive/v1/account/endpoint'
        response = self.http_request(url=url,
                                     request_type=RequestType.GET,
                                     status_codes=(requests.codes.ok,),
                                     use_access_token=True,
                                     action_string="Cloud Drive End Points")
        data = json.loads(response.text)
        if data['customerExists'] is not True:
            raise RuntimeError("Error with account")
        self.content_url = data['contentUrl']
        self.metadata_url = data['metadataUrl']

    def load_root_folder(self):
        url = self.metadata_url + '/nodes?filters=isRoot:true'
        response = self.http_request(url=url,
                                     request_type=RequestType.GET,
                                     status_codes=(requests.codes.ok,),
                                     use_access_token=True,
                                     action_string="Cloud Drive Root Folder")

        data = json.loads(response.text)
        if 'data' not in data:
            raise RuntimeError("Error getting root folder")
        self.root_folder = data['data'][0]['id']

    def upload(self, file_path, destination=None,
               modified_time=None, create_folder=False, overwrite=False):
        logger = logging.getLogger("multidrive")
        logger.debug("Upload {} Cloud Drive Storage Service".format(file_path))

        destination_id = self.root_folder
        if destination is not None and destination != "":
            destination_id = self.get_folder(self.root_folder,
                                             destination,
                                             create_folder)

        file_name = os.path.basename(file_path)
        cur_file = self.get_file(destination_id, file_name)
        cur_hash_file = HashFile()

        NUM_ATTEMPTS = 5
        cur_attempt = 1
        while cur_attempt <= NUM_ATTEMPTS:

            if cur_file is None:
                url = self.content_url + "/nodes?suppress=deduplication"

                metadata = {}
                metadata['name'] = file_name
                metadata['kind'] = "FILE"
                metadata['parents'] = [destination_id]

                mime_type = guess_type(file_path)[0]
                if not mime_type:
                    mime_type = 'application/octet-stream'

                fields = [('metadata', ("", json.dumps(metadata)))]
                content = (file_name, file_path, mime_type)

                response = self.http_request(url=url,
                                             request_type=RequestType.POST,
                                             status_codes=(requests.codes.
                                                           created,),
                                             use_access_token=True,
                                             action_string="Upload File",
                                             max_tries=10,
                                             use_multipart_encoder=True,
                                             multipart_encoder_fields=fields,
                                             multipart_encoder_content=content,
                                             multipart_hash_file=cur_hash_file)
            else:
                if overwrite is False:
                    raise RuntimeError("File: {} exists, but "
                                       "overwrite is not set"
                                       .format(file_name))
                url = self.content_url + "/nodes/"+cur_file['id']+"/content"

                mime_type = guess_type(file_path)[0]
                if not mime_type:
                    mime_type = 'application/octet-stream'

                content = (file_name, file_path, mime_type)
                cur_hash_file = HashFile()
                response = self.http_request(url=url,
                                             request_type=RequestType.PUT,
                                             status_codes=(requests.codes.ok,),
                                             use_access_token=True,
                                             action_string="Upload File "
                                                           "Overwrite",
                                             max_tries=10,
                                             use_multipart_encoder=True,
                                             multipart_encoder_fields=[],
                                             multipart_encoder_content=content,
                                             multipart_hash_file=cur_hash_file)

            server_hash = json.loads(response.text)['contentProperties']['md5']

            cur_attempt += 1
            if (cur_hash_file.get_md5() == server_hash.lower()):
                break
            logger.warning("Hash of uploaded file does "
                           "not match server.  Attempting again")

        if (cur_hash_file.get_md5() != server_hash.lower()):
            raise RuntimeError("Hash of uploaded file does "
                               "not match server.")

        print("{} successfully uploaded".format(file_name))

    def get_folder(self, cur_folder, folder_path, create=False):
        if folder_path.endswith('/'):
            folder_path = folder_path[:-1]

        split_path = folder_path.split('/')
        # cur_path = cur_folder
        # print "Path: "+ str(split_path)
        create_rest = False
        while len(split_path) > 0:
            cur_item = split_path.pop(0)
            data = None
            if create_rest is False:
                params = urllib.parse.urlencode({'filters': 'name:'
                                                + cur_item.replace(" ", "\ ")})
                url = self.metadata_url + '/nodes/' + cur_folder + '/children'
                response = self.http_request(url=url,
                                             request_type=RequestType.GET,
                                             status_codes=(requests.codes.ok,
                                                           requests.codes.
                                                           bad_request),
                                             use_access_token=True,
                                             params=params,
                                             action_string='Get Folder')
                if response.status_code == requests.codes.bad_request:
                    raise ItemDoesNotExistError("Error: Folder {} does not "
                                                "exist.".format(cur_item))

                data = json.loads(response.text)
                if 'data' not in data:
                    raise RuntimeError("Error getting folder " + cur_item)

            if create_rest is True or len(data['data']) == 0:
                if create is False:
                    raise ItemDoesNotExistError("Error: Folder {} does not "
                                                "exist and createfolder is "
                                                "not set.".format(cur_item))
                create_rest = True
                url = self.metadata_url + "/nodes"

                metadata = {}
                metadata['name'] = cur_item
                metadata['kind'] = "FOLDER"
                metadata['parents'] = [cur_folder]

                data = json.dumps(metadata)

                response = self.http_request(url=url,
                                             request_type=RequestType.POST,
                                             status_codes=(requests.codes.
                                                           created,),
                                             use_access_token=True,
                                             data=data,
                                             action_string='Create Folder')

                data = json.loads(response.text)
                cur_folder = data['id']
            elif len(data['data']) > 1:
                raise RuntimeError("Error: Multiple items with name: " +
                                   cur_item)
            else:
                if data['data'][0]['kind'] != "FOLDER":
                    raise WrongTypeError("Error: {} is not a folder."
                                         .format(cur_item))
                cur_folder = data['data'][0]['id']

        return cur_folder

    def get_file(self, folder_id, file_name):
        params = urllib.parse.urlencode({'filters': 'name:' +
                                        file_name.replace(" ", "\ ")})

        url = self.metadata_url + '/nodes/' + folder_id + '/children'
        response = self.http_request(url=url,
                                     request_type=RequestType.GET,
                                     status_codes=(requests.codes.ok,),
                                     use_access_token=True,
                                     params=params,
                                     action_string='Get File')

        data = json.loads(response.text)
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

        return data['data'][0]

    def download(self, file_path, destination=None, overwrite=False):
        print("Download {} Cloud Drive Storage Service".format(file_path))
        (folder, file_name) = os.path.split(file_path)

        if folder is None or folder == "":
            folder = self.root_folder
        else:
            folder = self.get_folder(self.root_folder, folder, create=False)

        cur_file = self.get_file(folder, file_name)

        if cur_file is None:
            raise RuntimeError("File {} does not exist".format(file_path))
        return self.download_item(cur_file, destination, overwrite=overwrite,
                                  create_folder=False)

    def download_item(self, cur_file, destination=None, overwrite=False,
                      create_folder=False):
        logger = logging.getLogger("multidrive")
        local_path = cur_file['name']

        if destination is not None:
            local_path = os.path.join(destination, local_path)

        if cur_file['kind'] == 'FOLDER':
            if create_folder is False:
                raise RuntimeError("Error: Folder chosen to be downloaded.")
            if not os.path.exists(local_path):
                # Add proper error message here?
                os.mkdir(local_path)
            return (local_path, cur_file['modifiedDate'])
        if os.path.isdir(local_path):
            raise RuntimeError("Local destination is a folder")
        if overwrite is False and os.path.isfile(local_path):
            raise RuntimeError("Local file {} exists.  Enable overwrite "
                               "option to continue.".format(local_path))

        remote_hash = cur_file['contentProperties']['md5'].lower()
        NUM_ATTEMPTS = 5
        cur_attempt = 1
        while cur_attempt <= NUM_ATTEMPTS:
            f = open(local_path, "wb")

            url = self.content_url+"/nodes/"+cur_file['id']+"/content"
            logger.info("URL to save file is: "+url)

            response = self.http_request(url=url,
                                         request_type=RequestType.GET,
                                         status_codes=(requests.codes.ok,),
                                         use_access_token=True,
                                         stream=True,
                                         action_string='Download Item')

            size = 0
            cur_file_hash = hashlib.md5()
            for chunk in response.iter_content(chunk_size=4*1024*1024):
                if chunk:  # filter out keep-alive new chunks
                    cur_file_hash.update(chunk)
                    f.write(chunk)
                    f.flush()
                    size += 1
                    if size % 100 == 0:
                        logger.info(str(size*4) + "MB written")
            os.fsync(f.fileno())
            f.close()

            cur_attempt += 1
            if (remote_hash == (cur_file_hash.hexdigest())):
                break
            logger.warning("Hash of downloaded file does "
                           "not match server.  Attempting again")

        if (remote_hash != (cur_file_hash.hexdigest())):
            raise RuntimeError("Hash of downloaded file does "
                               "not match server.")

        lastModifiedDateTimeString = cur_file['modifiedDate']
        modifiedDate = parse(lastModifiedDateTimeString)

        os.utime(local_path, (time.mktime(modifiedDate.timetuple()),
                              time.mktime(modifiedDate.timetuple())))

        print(local_path + " has been saved to disk")

        # TODO: deal with return values.
        return (local_path, lastModifiedDateTimeString)

    def create_folder(self, folder_path):
        self.get_folder(self.root_folder, folder_path, create=True)

    def is_folder(self, folder_path):
        if folder_path is None or len(folder_path) == 0 or folder_path == "/":
            return True
        try:
            result = self.get_folder(self.root_folder,
                                     folder_path,
                                     create=False)
            if result is None:
                return False
            return True
        except (ItemDoesNotExistError, WrongTypeError):
            return False

    def list_folder(self, folder_path):
        base_folder = self.root_folder
        if (folder_path is not None and (len(folder_path) > 0 and
                                         folder_path != "/")):
            base_folder = self.get_folder(base_folder,
                                          folder_path,
                                          create=False)
        print("Getting listing for {}".format(folder_path))
        folder_list = self.get_folder_listing(base_folder, [])
        return folder_list

    def get_folder_listing(self, cur_folder, path_list):
        logger = logging.getLogger("multidrive")
        result_list = []

        url = self.metadata_url + '/nodes/' + cur_folder + '/children'
        params = {}
        data = []
        num_files = 0
        while True:
            response = self.http_request(url=url,
                                         request_type=RequestType.GET,
                                         status_codes=(requests.codes.ok,
                                                       requests.codes.
                                                       not_found),
                                         use_access_token=True,
                                         params=params,
                                         action_string='Get Folder Listing')

            if response.status_code == requests.codes.not_found:
                logger.warning("Item not found: " + cur_folder)
                raise RuntimeError("Item not found. Possible bad path: "
                                   + cur_folder)

            cur_response = json.loads(response.text)
            if 'data' not in cur_response:
                raise RuntimeError("Error getting folder " + cur_folder)
            data.extend(cur_response['data'])
            num_files += len(cur_response['data'])
            if num_files >= cur_response['count']:
                break
            params['startToken'] = cur_response['nextToken']

        data.sort(key=lambda cur_file: cur_file['name'])

        for current_item in data:
            result_list.append((current_item, path_list))
            if current_item['kind'] == "FOLDER":
                new_list = list(path_list)
                new_list.append(current_item['name'])
                result_list.extend(self.get_folder_listing(
                    current_item['id'], new_list))

        return result_list

    def get_file_name(self, file):
        return file['name']

    def is_folder_from_file_type(self, file):
        return file['kind'] == "FOLDER"
