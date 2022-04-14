import argparse
import logging
import json
import re
import os
from pathlib import Path
from zipfile import ZipFile
import csv
import glob
import contextlib

script_path = os.path.dirname(os.path.realpath(__file__))


@contextlib.contextmanager
def working_directory(path):
    """Changes working directory and returns to previous on exit."""
    prev_cwd = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)


# DONE: Issue 71 (empty tar.gz2)
# DONE: count 101 departements for each code
# DONE: check if at least all with an edigeo name. Seen on DOM where all delivery with only DXF content


def errors_analysis(subdir):
    with working_directory(subdir) as work_dir:
        files = [f"{f}" for f in Path(".").glob("*_dep*")]
        my_files_with_size_issues = []
        all_tar_bz2 = []
        my_depts = {}
        for file in files:
            with ZipFile(file, "r") as zipObj:
                # Get list of ZipInfo objects
                listOfFiles = zipObj.infolist()
                listOfFilesTarBz2Info = [
                    {
                        "original_zip": file,
                        "file_size": f.file_size,
                        "filename": f.filename,
                        "compress_size": f.compress_size,
                    }
                    for f in listOfFiles
                    if f.filename.endswith(".tar.bz2")
                ]
                all_tar_bz2.append(listOfFilesTarBz2Info)
                dep = re.search("dep[0-9A-Za-z]+", file).group()
                if dep not in my_depts:
                    my_depts[dep] = {"dxf": 0, "edigeo": 0}
                firstFileName = listOfFilesTarBz2Info[0].get("filename")
                if "edigeo" in firstFileName.lower():
                    my_depts[dep]["edigeo"] += 1
                if "dxf" in firstFileName.lower():
                    my_depts[dep]["dxf"] += 1
                listOfFilesTarBz2InfoWithIssues = [
                    f for f in listOfFilesTarBz2Info if f.get("file_size") == 46
                ]
            if len(listOfFilesTarBz2InfoWithIssues) > 0:
                my_files_with_size_issues += listOfFilesTarBz2InfoWithIssues

    anomalies_content = {
        k: v for k, v in my_depts.items() if v.get("dxf") != 2 or v.get("edigeo") != 2
    }

    if len(anomalies_content.keys()) > 0:
        logging.debug("Content with wrong type of files within zip")
        logging.debug(anomalies_content)

    if len(my_files_with_size_issues) > 0:
        logging.debug(
            "Files with empty tar.gz. See content of `my_files_with_size_issues.csv`"
        )
        with open("my_files_with_size_issues.json", "w") as outfile:
            json.dump(my_files_with_size_issues, outfile)

        headers = list(my_files_with_size_issues[0].keys())
        with open("my_files_with_size_issues.csv", "w") as f:
            cw = csv.DictWriter(f, headers, delimiter=",")
            cw.writeheader()
            cw.writerows(my_files_with_size_issues)

    if len(files) != (4 * 101):
        logging.debug("wrong number of files in delivery")

    with open("all_tar_bz2.json", "w") as f:
        json.dump(all_tar_bz2, f)


# abs_departements_path = Path(script_path) / Path(departements_path)
# abs_compressed_file_name = Path(script_path) / Path(compressed_file_name)


def main():
    parser = argparse.ArgumentParser(
        description="Check delivery compliant, with no issues"
    )
    requiredNamed = parser.add_argument_group("required named arguments")
    requiredNamed.add_argument(
        "-d", "--directory", help="Input zip file name", required=True
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG)
    errors_analysis(args.directory)


if __name__ == "__main__":
    # execute only if run as a script
    main()
