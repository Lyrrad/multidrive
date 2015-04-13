#!/usr/bin/env python3
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
from googledrivestorageservice import GoogleDriveStorageService
from onedrivestorageservice import OneDriveStorageService
from clouddrivestorageservice import CloudDriveStorageService
import tempfile
import shutil
from _version import __version__


def get_storage_service(service_name):
    if service_name.lower() == 'googledrive':
        return GoogleDriveStorageService()
    elif service_name.lower() == 'onedrive':
        return OneDriveStorageService()
    elif service_name.lower() == 'clouddrive':
        return CloudDriveStorageService()
    return None


def main():
    parser = argparse.ArgumentParser(description='MultiDrive version ' +
                                                 str(__version__) +
                                                 '\nMultiple Cloud Storage '
                                                 'Operations')
    parser.add_argument('-s', '--source', nargs=1, required=True,
                        help='set primary service for this command. Valid '
                        'values are clouddrive, onedrive and googledrive')
    parser.add_argument('-a', '--action', nargs=1, required=True,
                        help='action to perform, valid actions include '
                        'download, upload, list, copy, and quota')
    parser.add_argument('-d', '--destination', nargs=1,
                        help='set secondary service for this command, Valid '
                        'values are clouddrive, onedrive and googledrive.  '
                        'Only valid with copy command')
    parser.add_argument('-l', '--local', nargs=1,
                        help='path of local file or folder')
    parser.add_argument('-r', '--remote', nargs=1,
                        help='path of remote file or folder')
    parser.add_argument('-c', '--createfolder',
                        help='enable creation of necessary remote folders',
                        action='store_true')
    parser.add_argument('-e', '--secondaryremote', nargs=1,
                        help='path secondary remote file or folder (for copy '
                        'action)')
    parser.add_argument('-o', '--overwrite',
                        help='enable overwriting of files',
                        action='store_true')
    parser.add_argument('-b', '--debug', help="enable debug logging",
                        action='store_true')

    args = parser.parse_args()

    service = get_storage_service(args.source[0])
    if service is None:
        raise ValueError("Please specify a valid source service.")

    service.authorize()
    if args.debug is True:
        logging.getLogger("multidrive").setLevel(logging.DEBUG)
        logging.getLogger("multidrive").debug("Logging enabled.")
    if args.action[0].lower() == "upload":
        if args.local is None:
            raise ValueError("Please specify a local file to upload.")
        destination = None
        if args.remote is not None:
            destination = args.remote[0]
        service.upload(args.local[0], destination=destination,
                       create_folder=args.createfolder,
                       overwrite=args.overwrite)
        pass
    elif args.action[0].lower() == "download":
        if args.remote is None:
            raise ValueError("Please specify a remote file or folder to "
                             "download.")
        local_path = None
        if args.local is not None:
            local_path = args.local[0]
        if service.is_folder(args.remote[0]) is True:
            # TODO: Give an error earlier if the
            # destination folder doesn't exist
            remote_files = service.list_folder(args.remote[0])
            for (cur_file, path) in remote_files:
                destination = None
                if local_path is None:
                    if path is None or len(path) == 0:
                        destination = None
                    else:
                        # TODO: is is portable to windows?  Should I be using a
                        # "/".join method?
                        destination = os.path.join(*path)
                else:
                    destination = os.path.join(local_path, *path)
                service.download_item(cur_file,
                                      destination=destination,
                                      overwrite=args.overwrite,
                                      create_folder=True)
        else:
            service.download(args.remote[0],
                             local_path,
                             overwrite=args.overwrite)
    elif args.action[0].lower() == "list":
        if args.remote is None:
            raise ValueError("Please specify a remote folder to list.")
        if service.is_folder(args.remote[0]) is False:
            raise ValueError("Remote path is either does not exist or is not "
                             "a folder")
        for (cur_file, path) in service.list_folder(args.remote[0]):
            new_path = list(path)
            new_path.append(service.get_file_name(cur_file))
            print("/".join(new_path))
    elif args.action[0].lower() == "copy":
        if args.destination is None:
            raise ValueError("Please specify a destination for copy "
                             "operation.")
        service2 = get_storage_service(args.destination[0])
        service2.authorize()
        if service2 is None:
            raise ValueError("Please specify a valid secondary source "
                             "service.")
        if args.source[0].lower() == args.secondaryremote[0].lower():
            raise ValueError("Primary and secondary services must be "
                             "different")
        if args.remote is None:
            raise ValueError("Please specify a remote file or folder to copy "
                             "from.")
        if args.secondaryremote is None:
            raise ValueError("Please specify a secondary remote file or "
                             "folder to copy to.")

        if args.createfolder is False and \
           service2.is_folder(args.secondaryremote[0]) \
           is False:
            raise ValueError("Secondary remote folder does not exist. Use the "
                             "createfolder option to create it")
        tmp_path = tempfile.mkdtemp()
        try:
            if service.is_folder(args.remote[0]) is True:
                remote_files = service.list_folder(args.remote[0])
                for (cur_file, path) in remote_files:

                    cur_dest = args.secondaryremote[0]
                    if len(path) > 0:
                        cur_dest = os.path.join(cur_dest, *path)

                    if service.is_folder_from_file_type(cur_file):
                        if not service2.is_folder(cur_dest):
                            service2.create_folder(cur_dest)
                    else:
                        (local_temp,
                         last_mod) = (service.download_item(
                                      cur_file,
                                      destination=tmp_path,
                                      overwrite=args.overwrite))

                        service2.upload(local_temp, destination=cur_dest,
                                        modified_time=last_mod,
                                        create_folder=args.createfolder,
                                        overwrite=args.overwrite)
                        os.remove(local_temp)
            else:
                (local_temp, last_mod) = (service.download(
                                          args.remote[0], tmp_path,
                                          overwrite=args.overwrite))
                service2.upload(local_temp,
                                destination=args.secondaryremote[0],
                                modified_time=last_mod,
                                create_folder=args.createfolder,
                                overwrite=args.overwrite)
                os.remove(local_temp)
        finally:
            shutil.rmtree(tmp_path)
    elif args.action[0].lower() == "quota":
        print(service.get_quota())
    else:
        raise ValueError("Please specify a valid action.")


if __name__ == "__main__":
    main()
