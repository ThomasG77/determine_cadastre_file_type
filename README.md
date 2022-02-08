# Script to manage some part of cadastre delivery from DGFIP

## Install deps

    conda create --name python_cmd python=3.7 -y
    conda activate python_cmd
    conda config --add channels conda-forge
    conda config --set channel_priority strict
    conda install py7zr -y
    conda install gdal -y



## Use

Activate environment
    
    conda activate python_cmd

Determine type of cadastre delivery from zip file and move files

    python determine_cadastre_file_type.py -d 'path/to/source/dir'
    # If you want verbose version
    python determine_cadastre_file_type.py -v -d 'path/to/source/dir'
    # If you want a target directory different from the source
    python determine_cadastre_file_type.py -d 'path/to/source/dir' -t 'path/to/target/dir'

Analysis to determine issues in the delivery before going further

    python analysis_issues_cadastre.py -d cadastre-2022-01-01

where `cadastre-2022-01-01` directory contains a list of files like below

```
'Commande 403657_101_dep01.zip'
'Commande 403657_101_dep02.zip'
'Commande 403657_101_dep03.zip'
'Commande 403657_101_dep04.zip'
...
```
