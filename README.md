# Script to determine type of cadastre delivery from zip file

## Install deps

    conda create --name python_cmd python=3.7 -y
    conda activate python_cmd
    conda config --add channels conda-forge
    conda config --set channel_priority strict
    conda install py7zr -y
    conda install gdal -y



## Use
    
    conda activate python_cmd
    python determine_cadastre_file_type.py -d 'path/to/source/dir'
    # If you want verbose version
    python determine_cadastre_file_type.py -v -d 'path/to/source/dir'
    # If you want a target directory different from the source
    python determine_cadastre_file_type.py -d 'path/to/source/dir' -t 'path/to/target/dir'
