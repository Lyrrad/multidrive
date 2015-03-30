#!/usr/bin/env python
# -*- coding: utf-8 -*-

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


import argparse
import os

import logging
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
from clouddrivestorageservice import CloudDriveStorageService
import tempfile
import shutil

def get_storage_service(service_name):
    if service_name.lower() == 'googledrive':
        return GoogleDriveStorageService()
    elif service_name.lower() == 'onedrive':
        return OneDriveStorageService()
    elif service_name.lower() == 'clouddrive':
        return CloudDriveStorageService()
    return None


def main():
    parser = argparse.ArgumentParser(description='Multiple Cloud Storage Operation')
    # parser.add_argument('-m', '--moveFile', help="Path to File to move")
    # parser.add_argument('-s', '--moveFiles', nargs= '*', help="Path to Files to move")
    parser.add_argument('-s', '--source', nargs=1, required=True, help='set primary service for this command. Valid values are clouddrive, onedrive and googledrive')
    parser.add_argument('-a', '--action', nargs=1, required=True, help='action to perform, valid actions include download, upload, list, and copy')
    parser.add_argument('-d', '--destination', nargs=1, help='set secondary service for this command, Valid values are clouddrive, onedrive and googledrive.  Only valid with copy command')
    parser.add_argument('-l', '--local', nargs=1, help='path of local file or folder')
    parser.add_argument('-r', '--remote', nargs=1, help='path of remote file or folder')
    parser.add_argument('-c', '--createfolder', help='enable creation of necessary remote folders', action='store_true')
    parser.add_argument('-e', '--secondaryremote', nargs=1, help='path secondary remote file or folder (for copy action)')
    parser.add_argument('-o', '--overwrite', help='enable overwriting of files', action='store_true')
    # parser.add_argument('-p', '--parent', help="parent folder for Google Drive")
    # parser.add_argument('-d', '--debug', help="enable debug logging")

    args = parser.parse_args();

    storage_service = get_storage_service(args.source[0])
    if storage_service is None:
        raise ValueError("Please specify a valid source service.")

    storage_service.authorize()

    if args.action[0].lower() == "upload":
        if args.local is None:
            raise ValueError("Please specify a local file to upload.")
        destination = None
        if args.remote is not None:
            destination = args.remote[0]
        storage_service.upload(args.local[0], destination=destination, create_folder=args.createfolder, overwrite=args.overwrite)
        pass
    elif args.action[0].lower() == "download":
        if args.remote is None:
            raise ValueError("Please specify a remote file or folder to download.")
        local_path = None
        if args.local is not None:
            local_path = args.local[0]
        if storage_service.is_folder(args.remote[0]) is True:
            remote_files = storage_service.list_folder(args.remote[0])
            for (cur_file, path) in remote_files:
                destination = None
                if local_path is None:
                    if path is None or len(path) == 0:
                        destination = None
                    else:
                        ##TODO: is is portable to windows?  Should I be using a "/".join method?
                        destination = os.path.join(*path)
                else:
                    destination = os.path.join(local_path, *path)
                storage_service.download_item(cur_file, destination=destination, overwrite=args.overwrite)
        else:
            storage_service.download(args.remote[0], local_path, overwrite=args.overwrite)
    elif args.action[0].lower() == "list":
        if args.remote is None:
            raise ValueError("Please specify a remote folder to list.")
        if storage_service.is_folder(args.remote[0]) is False:
            raise ValueError("Remote path is either does not exist or is not a folder")
        for (cur_file, path) in storage_service.list_folder(args.remote[0]):
            new_path = list(path)
            new_path.append(storage_service.get_file_name(cur_file))
            print u"/".join(new_path)
            
    elif args.action[0].lower() == "copy":
        secondary_storage_service = get_storage_service(args.destination[0])
        secondary_storage_service.authorize()
        if secondary_storage_service is None:
            raise ValueError("Please specify a valid secondary source service.")
        if args.source[0].lower() == args.secondaryremote[0].lower():
            raise ValueError("Primary and secondary services must be different")
        if args.remote is None:
            raise ValueError("Please specify a remote file or folder to copy from.")
        if args.secondaryremote is None:
            raise ValueError("Please specify a secondary remote file or folder to copy to.")

        if args.createfolder is False and secondary_storage_service.is_folder(args.secondaryremote[0]) is False:
            raise ValueError("Secondary remote folder does not exist. Use the createfolder option to create it")
        tmp_path = tempfile.mkdtemp()
        try:
            if storage_service.is_folder(args.remote[0]) is True:
                remote_files = storage_service.list_folder(args.remote[0])
                for (cur_file, path) in remote_files:

                    cur_destination = args.secondaryremote[0]
                    if len(path)>0:
                        cur_destination = os.path.join(cur_destination, *path)

                    if storage_service.is_folder_from_file_type(cur_file) is True:
                        if secondary_storage_service.is_folder(cur_destination) is False:
                            secondary_storage_service.create_folder(cur_destination)
                    else:
                        (local_temp_file, last_modified) = storage_service.download_item(cur_file, destination=tmp_path, overwrite=args.overwrite)

                        secondary_storage_service.upload(local_temp_file, destination=cur_destination, modified_time=last_modified, create_folder=args.createfolder, overwrite=args.overwrite)
                        os.remove(local_temp_file)
            else:
                (local_temp_file, last_modified) = storage_service.download(args.remote[0], tmp_path, overwrite=args.overwrite)
                secondary_storage_service.upload(local_temp_file, destination=args.secondaryremote[0], modified_time=last_modified, create_folder=args.createfolder, overwrite=args.overwrite)
                os.remove(local_temp_file)
        finally:
            shutil.rmtree(tmp_path)
    else:
        raise ValueError("Please specify a valid action.")

    # storage_service.download("test")
if __name__ == "__main__":
    main()
