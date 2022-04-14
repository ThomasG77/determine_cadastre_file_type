import argparse
import logging
import json
import tarfile
import io
import os
import re
import shutil
import urllib.request
from pathlib import Path
from zipfile import ZipFile
import glob

import py7zr
from osgeo import gdal, ogr, osr


class MakeSpatialQuery:
    def __init__(self, file):
        self.source_ds = gdal.OpenEx(file, gdal.OF_VECTOR)
        self.sql_lyr = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()

    def sql(self, query, dialect="SQLITE"):
        self.sql_lyr = self.source_ds.ExecuteSQL(statement=query, dialect=dialect)
        return self.sql_lyr

    def close(self):
        if self.sql_lyr is not None:
            self.source_ds.ReleaseResultSet(self.sql_lyr)
        self.source_ds = None


script_path = os.path.dirname(os.path.realpath(__file__))

departements_path = "DEPARTEMENT.shp"
abs_departements_path = Path(script_path) / Path(departements_path)

URL = "ftp://Admin_Express_ext:Dahnoh0eigheeFok@ftp3.ign.fr/ADMIN-EXPRESS-COG_3-0__SHP__FRA_L93_2021-05-19.7z"
compressed_file_name = URL.split("/")[-1]
abs_compressed_file_name = Path(script_path) / Path(compressed_file_name)


def uncompress_departements_layer():
    urllib.request.urlretrieve(URL, abs_compressed_file_name)
    with py7zr.SevenZipFile(abs_compressed_file_name, "r") as archive:
        allfiles = archive.getnames()
        selective_files = [f for f in allfiles if "DEPARTEMENT." in f and "LAMB93" in f]
        archive.extract(targets=selective_files)
        for f in selective_files:
            shutil.move(f, Path(script_path) / Path(f).name)
    shutil.rmtree(selective_files[0].split("/")[0])
    Path(abs_compressed_file_name).unlink()


def get_directory_name_from_projection_within_file(abs_zip_path):
    capture_dept = re.search("dep[0-9A-Za-z]+", Path(abs_zip_path).name)
    if capture_dept is not None:
        dep = capture_dept.group().replace("dep", "")
    capture_id_type_data = (
        Path(abs_zip_path).name.replace("Commande ", "").split("_")[0]
    )
    logging.debug(f"File input: {abs_zip_path}")
    logging.debug(f"Departement: {dep}")
    logging.debug(f"ID for type of data: {capture_id_type_data}")
    with ZipFile(abs_zip_path, "r") as zipObj:
        # Get list of ZipInfo objects
        listOfFiles = zipObj.infolist()
        listOfFilesTarBz2 = [f for f in listOfFiles if f.filename.endswith(".tar.bz2")]
        # Get element name, a tar.bz2
        elem = listOfFilesTarBz2[0]
        # Read in memory the zip file
        extracted = zipObj.read(elem.filename)
        # Get in memory the tar.bz2
        content = tarfile.open(fileobj=io.BytesIO(extracted))
        members_names = [m.name for m in content.getmembers()]
        isDxf = len([m for m in members_names if "dxf" in m.lower()]) > 0
        isL93 = False
        if isDxf:
            tar_bz2_element = content.getmembers()[0]
            # Get the file and it 40 first lines
            tar_content = content.extractfile(tar_bz2_element)
            head = [next(tar_content) for x in range(40)]
            extmin_index = [
                index
                for index, line in enumerate(head)
                if "EXTMIN" in line.decode("utf8")
            ][0]
            [x, y] = [
                float(coord.decode("utf8").strip("\r\n"))
                for coord in [head[extmin_index + 2], head[extmin_index + 4]]
            ]
            with MakeSpatialQuery(f"{abs_departements_path}") as conn:
                sql_query = f"SELECT * FROM DEPARTEMENT WHERE INSEE_DEP = '{dep}' AND ST_Contains(geometry, MakePoint({x}, {y}))"
                layer = conn.sql(sql_query)
                if layer.GetFeatureCount() > 0:
                    isL93 = True
                    feature = layer.GetNextFeature()
                    myjson = feature.ExportToJson()
                    logging.debug(json.dumps(json.loads(myjson).get("properties")))
        else:
            first_edigeo_geo_file_index = [
                i for i, m in enumerate(members_names) if ".geo" in m.lower()
            ][0]
            tar_bz2_element_geo = content.getmembers()[first_edigeo_geo_file_index]
            tar_content = content.extractfile(tar_bz2_element_geo)
            content = [
                line.decode("utf8").strip("\r\n").split(":")[-1]
                for line in tar_content
                if "RELSA" in line.decode("utf8")
            ][0]
            logging.debug(f"Projection in Edigeo: {content}")
            if "LAMB93" in content:
                isL93 = True
        target_dir = ""
        if isDxf:
            target_dir = "dxf"
        else:
            target_dir = "edigeo"
        if not isL93:
            target_dir += "-cc"
        logging.debug(f"id: {capture_id_type_data}, target: {target_dir}")
        return [capture_id_type_data, target_dir]


def main():
    parser = argparse.ArgumentParser(
        description="Move files to default structure according to their projection"
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    requiredNamed = parser.add_argument_group("required named arguments")
    requiredNamed.add_argument(
        "-d", "--directory", help="Input zip file name", required=True
    )
    parser.add_argument("-t", "--targetdir", help="Output directory destination")
    parser.add_argument(
        "-c",
        "--copyfiles",
        help="Copy files after detecting couples id type cadastre and directory",
        action="store_true",
    )
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    if not abs_departements_path.exists():
        logging.debug("Caching DEPARTEMENT.shp")
        uncompress_departements_layer()
    dir_source = Path(args.directory)
    target_dir = dir_source if args.targetdir is None else args.targetdir
    dir_dest = Path(target_dir)
    if not dir_source.exists() and not dir_source.is_dir():
        logging.debug(f"Source directory {dir_source} does not exists")
    elif not dir_dest.exists() and not dir_dest.is_dir():
        logging.debug(f"Target directory {sub_dir_dest} does not exists")
    else:
        files = [f"{f}" for f in Path(dir_source).glob("*_dep*")]
        list_files = "\n".join(files)
        logging.debug(f"FILES: {list_files}")
        couples_idtypecadastre_directory = [
            get_directory_name_from_projection_within_file(f) for f in files
        ]
        couples_idtypecadastre_directory = {
            i[0]: i[1] for i in couples_idtypecadastre_directory
        }
        logging.debug(
            f"couples_idtypecadastre_directory: {couples_idtypecadastre_directory}"
        )
        with open("couples_idtypecadastre_directory.json", "w") as f:
            json.dump(couples_idtypecadastre_directory, f)
        if args.copyfiles:
            for key, value in couples_idtypecadastre_directory.items():
                sub_dir_dest = dir_dest / value
                logging.debug(f"sub_dir_dest: {sub_dir_dest}")
                sub_dir_dest.mkdir(parents=False, exist_ok=True)
                for f in dir_source.glob(f"Commande*{key}*"):
                    shutil.copy2(f, sub_dir_dest / f.name)


if __name__ == "__main__":
    # execute only if run as a script
    main()
