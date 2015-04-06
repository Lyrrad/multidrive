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
import dateutil.parser
import datetime
import os
import json
import logging
from mimetypes import guess_type
import hashlib

import apiclient
# from apiclient.http import MediaFileUpload
from apiclient.http import MediaIoBaseUpload

from oauth2client import client
from oauth2client.file import Storage
from apiclient.discovery import build
import httplib2

import time

from storageservice import StorageService


class HashMismatch(RuntimeError):
    pass


class HashFile(object):
    def set_file(self, cur_file):
        self.file = cur_file
        self.cur_file_hash = hashlib.md5()
        self.begin = False
        self.last_hash_pos = 0
        if self.file.tell() == 0:
            self.begin = True

        pos = self.file.tell()
        self.file.seek(0, os.SEEK_END)
        self.length = self.file.tell()-pos
        self.file.seek(pos, os.SEEK_SET)

    def __len__(self):
        return self.length

    def seek(self, offset, whence=os.SEEK_SET):
        self.file.seek(offset, whence)
        if self.begin is False and self.file.tell() == 0:
            self.begin = True

    def tell(self):
        return self.file.tell()

    def read(self, *args):
        chunk = self.file.read(*args)
        if len(chunk) > 0 and self.begin is True:
            if self.file.tell()-len(chunk) == self.last_hash_pos:
                self.cur_file_hash.update(chunk)
                self.last_hash_pos += len(chunk)
        return chunk

    def get_md5(self):
        if self.last_hash_pos == self.length:
            return self.cur_file_hash.hexdigest()
        raise RuntimeError("Did not complete hash of file.")


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
        logger = logging.getLogger("multidrive")
        logger.info("Authorize Google Drive Storage Service")

        flow = client.flow_from_clientsecrets(
            'google_drive_client_secrets.json',
            scope='https://www.googleapis.com/auth/drive',
            redirect_uri='urn:ietf:wg:oauth:2.0:oob')

        storage = Storage('google_drive_settings.dat')
        credentials = storage.get()
        if credentials is None or credentials.invalid:
            url = flow.step1_get_authorize_url()
            print("Go to this URL to authorize: {}".format(url))
            response = input("Enter the Token you received: ")
            credentials = flow.step2_exchange(response)
            storage.put(credentials)
        http_auth = credentials.authorize(httplib2.Http())
        self.__credentials__ = credentials
        credentials.set_store(storage)
        self.__service__ = build('drive', 'v2', http=http_auth)

    def upload(self, file_path, destination=None, modified_time=None,
               create_folder=False, overwrite=False):
        print("Uploading {} to Google Drive".format(file_path))
        self.upload_file(file_path, folder=destination,
                         modified_time=modified_time,
                         create_folder=create_folder, overwrite=overwrite)
        print("Upload complete")

    def download(self, file_path, destination=None, overwrite=False):
        print("Downloading {} from Google Drive".format(file_path))
        return self.download_file(file_path, destination=destination,
                                  overwrite=overwrite)
        print("Download Complete")

    def is_folder(self, folder_path):
        if folder_path is None or folder_path == "":
            # Interpret as root
            return True
        try:
            self.get_folder(folder_path)
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

        result_list = []
        query = "'{}' in parents and trashed=false ".format(cur_folder)

        file_list = []
        page_token = None
        while True:
            files = None
            if page_token:
                files = (self.__service__.files().
                         list(q=query, pageToken=page_token).execute())
            else:
                files = self.__service__.files().list(q=query).execute()

            file_list.extend(files['items'])
            page_token = files.get('nextPageToken')
            if not page_token:
                break

        file_list.sort(key=lambda cur_file: cur_file['title'])
        for cur_file in file_list:
            result_list.append((cur_file, path_list))
            if cur_file['mimeType'] == 'application/vnd.google-apps.folder':
                new_list = list(path_list)
                new_list.append(cur_file['title'])
                result_list.extend(self.get_folder_listing(cur_file['id'],
                                   new_list))

        return result_list

    def download_file(self, file_path, destination=None, overwrite=False):
        cur_file = self.get_file(file_path)
        return self.download_item(cur_file, destination=destination,
                                  overwrite=overwrite, create_folder=False)

    def download_item(self, cur_file, destination=None, overwrite=False,
                      create_folder=False):
        logger = logging.getLogger("multidrive")
        local_path = cur_file['title']
        if destination is not None:
            local_path = os.path.join(destination, local_path)

        if cur_file['mimeType'] == "application/vnd.google-apps.folder":
            if create_folder is False:
                raise RuntimeError("Path is a folder")
            if not os.path.exists(local_path):
                os.mkdir(local_path)
            return (local_path, cur_file['modifiedDate'])

        if os.path.isdir(local_path):
            raise RuntimeError("Local destination is a folder")
        if overwrite is False and os.path.isfile(local_path):
            raise RuntimeError(
                "Local file {} exists.  Enable overwrite option to continue."
                .format(local_path))

        NUM_ATTEMPTS = 5
        cur_attempt = 1
        while cur_attempt <= NUM_ATTEMPTS:
            fd = open(local_path, 'wb')
            try:
                self.download_helper(cur_file['id'], fd, cur_file['title'],
                                     cur_file['md5Checksum'])
            except HashMismatch:
                logger.warning("Hash of downloaded file does "
                               "not match server.  Attempting again")
                cur_attempt += 1
                continue
            finally:
                fd.close()
            break
        if cur_attempt > NUM_ATTEMPTS:
            raise RuntimeError("Hash of downloaded file does "
                               "not match server.")

        modified_date = dateutil.parser.parse(cur_file['modifiedDate'])
        os.utime(local_path, (time.mktime(modified_date.timetuple()),
                 time.mktime(modified_date.timetuple())))
        return (local_path, cur_file['modifiedDate'])

    def download_helper(self, file_id, local_fd, file_name, remote_hash):
        now = datetime.datetime.utcnow() + datetime.timedelta(minutes=1)
        expiry = self.__credentials__.token_expiry
        if now > expiry:
            self.__credentials__.refresh(httplib2.Http())

        headers = {}
        self.__credentials__.apply(headers)
        url = "https://www.googleapis.com/drive/v2/files/"+file_id
        parameters = {'alt': 'media'}

        response = requests.get(url, headers=headers, stream=True,
                                params=parameters)

        tries = 0
        while response.status_code != requests.codes.ok and tries < 6:
            if (response.status_code == requests.codes.forbidden):
                message = json.loads(response.text)
                if 'error' in message and 'errors' in message['error']:
                    is_malware = False
                    for cur_error in message['error']['errors']:
                        if cur_error['reason'] == 'abuse':
                            is_malware = True
                            break
                    if is_malware is True:
                        print("Error downloading file with name: {}"
                              .format(file_name))
                        answer = input("The file you have selected to "
                                       "download has been flaged as abusive "
                                       "or malware by Google. Do you still "
                                       "want to download?  Only do so if you "
                                       "understand the risks.  Enter 'y' or "
                                       "'yes' if you wish to do so. ")
                        if (answer.lower() == 'y' or answer.lower() == 'yes'):
                            parameters['acknowledgeAbuse'] = 'true'
                            response = requests.get(url, headers=headers,
                                                    stream=True,
                                                    params=parameters)
                            continue
                        raise RuntimeError("Abusive or malware file detected "
                                           "and not downloaded. Aborting.")

                    # If it's not malware, perhaps we need to refresh the "
                    # "token, so we'll do that on the next iteration
                    self.__credentials__.refresh(httplib2.Http())
                    self.__credentials__.apply(headers)

            tries += 1
            print("Save File: Google Drive connection failed Error: " +
                  response.text)
            print("Retry " + str(tries))
            sleep_length = float(1 << tries) / 2
            time.sleep(sleep_length)
            response = requests.get(url, headers=headers, stream=True,
                                    params=parameters)

        if response.status_code != requests.codes.ok:
            raise RuntimeError("Unable to access Google Drive file")

        size = 0
        cur_file_hash = hashlib.md5()
        for chunk in response.iter_content(chunk_size=1024*1024):
            if chunk:  # filter out keep-alive new chunks
                cur_file_hash.update(chunk)
                local_fd.write(chunk)
                local_fd.flush()
                size = size + 1
                if size % 200 == 0:
                    logging.info(str(size) + "MB written")
        os.fsync(local_fd.fileno())

        if remote_hash.lower() != cur_file_hash.hexdigest():
            raise RuntimeError("Hash of downloaded file does "
                               "not match server.")

    def upload_file(self, file_path, folder=None, modified_time=None,
                    create_folder=False, overwrite=False):
        logger = logging.getLogger("multidrive")

        logger.debug("Uploading " + file_path)
        file_name = os.path.basename(file_path)
        mime_type = guess_type(file_path)[0]
        mime_type = mime_type if mime_type else 'application/octet-stream'

        file_size = os.path.getsize(file_path)

        parents = []
        cur_folder = 'root'
        if folder is not None:
            cur_folder = self.get_folder(folder, create=create_folder)
            parents.append({"id": cur_folder})

        if modified_time is None:
            modified_time = datetime.datetime.fromtimestamp(
                os.path.getmtime(file_path),
                UTC()).isoformat()[:-6]
            if '.' not in modified_time:
                modified_time += ".000000Z"
            else:
                modified_time += "Z"

        # OneDrive returns times that happen to lie on the second without
        # the microseconds at the end.
        if '.' not in modified_time:
                modified_time = modified_time.replace("Z", ".000000Z")
        logging.debug("Modified time: "+modified_time)

        NUM_ATTEMPTS = 5
        cur_attempt = 1
        while cur_attempt <= NUM_ATTEMPTS:
            with open(file_path, 'rb') as cur_open_file:

                cur_hash_file = HashFile()
                cur_hash_file.set_file(cur_open_file)

                media_body = MediaIoBaseUpload(cur_hash_file,
                                               mimetype=mime_type,
                                               chunksize=1024*1024,
                                               resumable=True)
                if file_size == 0:
                    media_body = None

                existing_file = self.get_file_if_exists(file_name, cur_folder)

                try:
                    if existing_file is not None:
                        if overwrite is False:
                            raise RuntimeError("File already exists")
                        old_file = self.__service__.files().get(
                            fileId=existing_file['id']).execute()
                        old_file['modifiedDate'] = modified_time
                        old_file['title'] = file_name
                        old_file['mimeType'] = mime_type
                        old_file['parents'] = parents
                        new_file = self.__service__.files().update(
                            fileId=existing_file['id'],
                            body=old_file,
                            media_body=media_body).execute()
                    else:
                        body = {
                            'title': file_name,
                            'mimeType': mime_type,
                            'parents': parents,
                            'modifiedDate': modified_time,
                        }
                        new_file = self.__service__.files().insert(
                            body=body,
                            media_body=media_body).execute()

                except apiclient.errors.HttpError as error:
                    print('An error occured uploading file: %s' % error)
                    return None
                logger.info('Calculated MD5 of uploaded file:' +
                            cur_hash_file.get_md5())
                logger.info('Google Drive Checksum: ' +
                            new_file['md5Checksum'])
                if (cur_hash_file.get_md5() == new_file['md5Checksum']):
                    break
                logger.warning("Hash of downloaded file does "
                               "not match server.  Attempting again")
                cur_attempt += 1

        if (cur_hash_file.get_md5() != new_file['md5Checksum']):
            raise HashMismatch("Hash of uploaded file does "
                               "not match server.")

    def get_file_if_exists(self, file_name, folder_id):
        escaped_file_name = file_name.replace("'", "\\'")
        query = ("'{}' in parents and trashed=false and "
                 "title='{}'".format(folder_id, escaped_file_name))
        file_list = self.__service__.files().list(q=query).execute()['items']
        if len(file_list) > 1:
            raise RuntimeError('Multiple files with name "{}" exist'
                               .format(file_name))
        elif len(file_list) is 0:
            logging.debug("File {} does not exist".format(file_name))
            return None
        else:
            logging.debug("File {} exists".format(file_name))
            return file_list[0]

    def get_folder(self, folder_path, create=False):
        return self.get_file(folder_path, is_folder=True, create=create)

    def get_file(self, file_path, is_folder=False, create=False):

        if is_folder is True and file_path.endswith('/'):
            file_path = file_path[:-1]

        folders = file_path.split('/')

        file_name = None
        if is_folder is False:
            file_name = folders.pop()

        parent = 'root'

        for cur_folder in folders:
            escaped_folder = cur_folder.replace("'", "\\'")
            query = ("'{}' in parents and trashed=false and "
                     "mimeType='application/vnd.google-apps.folder' and "
                     "title='{}'".format(parent, escaped_folder))
            file_list = (self.__service__.files()
                         .list(q=query).execute()['items'])
            if len(file_list) > 1:
                raise RuntimeError('Multiple folders with name "{}" exist'
                                   .format(cur_folder))
            elif len(file_list) is 0:
                if create is False:
                    raise ItemDoesNotExistError('Folder "{}" does not exist'
                                                .format(cur_folder))
                parent = self.create_folder_helper(cur_folder, parent)['id']
                if parent is None:
                    raise RuntimeError('Unable to create folder "{}"'
                                       .format(cur_folder))
            else:
                parent = file_list[0]['id']

        if is_folder is True:
            return parent

        escaped_file_name = file_name.replace("'", "\\'")
        query = ("'{}' in parents and trashed=false and title='{}'"
                 .format(parent, escaped_file_name))
        file_list = self.__service__.files().list(q=query).execute()['items']
        if len(file_list) > 1:
            raise RuntimeError('Multiple files with name "{}" exist'
                               .format(file_name))
        elif len(file_list) is 0:
            raise ItemDoesNotExistError('File "{}" does not exist'
                                        .format(file_name))

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
            'parents': parents,
        }
        if modified_time is not None:
            body['modifiedDate'] = modified_time

        try:
            file = (self.__service__.files().insert(body=body)
                    .execute())
            print("Folder creation complete")
            return file
        except apiclient.errors.HttpError as error:
            print('An error occured creating folder: %s' % error)
            return None

    def get_file_name(self, file):
        return file['title']

    def is_folder_from_file_type(self, file):
        return file['mimeType'] == 'application/vnd.google-apps.folder'

    # Formatting code from http://stackoverflow.com/questions/1094841/
    def format_bytes(self, num, suffix='B'):
        for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
            if abs(num) < 1024.0:
                return "%3.2f%s%s" % (num, unit, suffix)
            num /= 1024.0
        return "%.2f%s%s" % (num, 'Yi', suffix)

    def get_quota(self):
        about = self.__service__.about().get().execute()

        quota_type = about['quotaType']
        if quota_type == 'UNLIMITED':

            result = "Total quota: Unlimited\n"
            result += "Used quota: {}\n"
            result += "Data in Trash: {}"
            used_quota = int(about['quotaBytesUsedAggregate'])
            trashed_quota = int(about['quotaBytesUsedInTrash'])
            result = (result.
                      format(self.format_bytes(used_quota),
                             self.format_bytes(trashed_quota)))
        else:
            total_quota = int(about['quotaBytesTotal'])
            used_quota = int(about['quotaBytesUsedAggregate'])
            remaining_quota = total_quota-used_quota
            trashed_quota = int(about['quotaBytesUsedInTrash'])
            percentage = float(used_quota)/total_quota*100
            result = (("Total quota: {}\n"
                       "Used quota: {}\n"
                       "Remaining Quota: {}\n"
                       "Data in Trash: {}\n"
                       "Percentage Used {}%")
                      .format(self.format_bytes(total_quota),
                              self.format_bytes(used_quota),
                              self.format_bytes(remaining_quota),
                              self.format_bytes(trashed_quota),
                              float("{0:.2f}".format(percentage))))
        return result
