# == SET-UP LOGGER ============================================================
# Import the logging library.
from enum import Enum
import re
import os
import sys
import difflib
from io import TextIOWrapper
import edacurry
import logging
import ansi
import requests  # Per scaricare il file
import tarfile
import zipfile   # Per decomprimere i file
import tempfile  # Per creare una directory temporanea
import requests

# URL file ZIP
ZIP_URL = "https://sagroups.ieee.org/2427/wp-content/uploads/sites/302/2019/03/analog_benchmark2017_v2.2.tar_.gz"
ZIP_URL2 = "https://github.com/AMS-Net/ams-net.github.io/raw/main/amsnet_1.0-20240412T024532Z-001.zip"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

response = requests.get(ZIP_URL, headers=headers)

# Download and unzip the ZIP file
def download_and_extract(zip_url, extract_to):
    
    print("Scaricando il file da:", zip_url)
    response = requests.get(zip_url, stream=True)
    if response.status_code == 200:
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(response.content)
            temp_file_path = temp_file.name

        if zip_url.endswith(".zip"):
            print("Decomprimendo il file ZIP nella cartella:", extract_to)
            with zipfile.ZipFile(temp_file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)

        elif zip_url.endswith(".tar_.gz"):
            print("Decomprimendo il file TAR.gz nella cartella:", extract_to)
            with tarfile.open(temp_file_path, 'r:gz') as tar_ref:
                tar_ref.extractall(extract_to)
        else:
            print("Formato di file non supportato:", zip_url)
            sys.exit(1)

        os.remove(temp_file_path)
    else:
        print("Errore durante il download del file", response.status_code)
        sys.exit(1)



if not os.path.exists("eldo"):
    os.mkdir("eldo")
if not os.path.exists("eldo/analog_benchmark2017_v2.2/"):
    download_and_extract(ZIP_URL, "eldo") 
if not os.path.exists("eldo/amsnet_1.0/"):
    download_and_extract(ZIP_URL2, "eldo")



# Get the C++ declared logger.
logger = logging.getLogger("edacurry_logger")
# Set the level.
logger.setLevel(logging.DEBUG)
# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# create formatter
formatter = logging.Formatter("[%(asctime)s - %(levelname)s]%(message)s")
# add formatter to ch
ch.setFormatter(formatter)
# add ch to logger
logger.addHandler(ch)
# =============================================================================
# Import the EDACurry library.

class Changes(Enum):
    NONE = 0
    EXTRA = 1
    MISSING = 2
    ANNOTATION = 3


def must_skip_line(line: str) -> bool:
    return line.startswith("#") or line.startswith("//") or line.startswith("*")


def parse_lines(file: TextIOWrapper) -> str:
    lines = []
    for line in file:
        if not must_skip_line(line):
            if re.match(r"^ +\+", line):
                previous_line: str = lines.pop()
                previous_line = previous_line.replace("\n", " ").replace("  ", " ")
                line = previous_line + re.sub(r"^ +\+", "", line)
            lines.append(re.sub(r" +", " ", line.rstrip().lower()))
    return lines


def handle_print(
    line: str, line_number: int, line_type: Changes, previous_type: Changes
) -> Changes:
    # If this line is only in b, print the line number and the text on the line
    if line_type == Changes.EXTRA:
        print(ansi.fg.yellow, "%3d" % line_number, line, ansi.util.reset)
        previous_type = line_type
    elif line_type == Changes.MISSING:
        print(ansi.fg.red, "%3d" % line_number, line, ansi.util.reset)
        previous_type = line_type
    else:
        if line_type == Changes.ANNOTATION:
            if previous_type == Changes.EXTRA:
                print(ansi.fg.yellow, "%3d" % line_number, line, ansi.util.reset)
            elif previous_type == Changes.MISSING:
                print(ansi.fg.red, "%3d" % line_number, line, ansi.util.reset)
        else:
            print(ansi.fg.green, "%3d" % line_number, line, ansi.util.reset)
        previous_type = Changes.NONE
    return previous_type


def compare(filepath1: str, filepath2: str):
    # Compare the two files.
    print("Comparing {} and {}...".format(filepath1, filepath2))
    with open(filepath1) as f1, open(filepath2) as f2:
        # Get the content.
        content_f1 = parse_lines(f1)
        content_f2 = parse_lines(f2)
        # Compute the differences.
        differences = difflib.ndiff(
            content_f1, content_f2, charjunk=difflib.IS_CHARACTER_JUNK
        )
        # Store the line number.
        line_number = 0
        # Store the type of the previous entry.
        previous_type: Changes = 0
        # Print the differences.
        for line in differences:
            # Strip the end of the line.
            line = line.rstrip()
            # Split off the tag.
            tag = line[:2]
            remaining = line[2:]
            # Skip empty lines.
            if not tag or not remaining:
                continue
            # Set the tag.
            if tag == "? ":
                line_type = Changes.ANNOTATION
            elif tag == "+ ":
                line_type = Changes.EXTRA
            elif tag == "- ":
                line_type = Changes.MISSING
            else:
                line_type = Changes.NONE
            # If the line is in both files or just b, increment the line number.
            if line_type in (Changes.NONE, Changes.MISSING):
                line_number += 1
            # Print the line.
            previous_type = handle_print(line, line_number, line_type, previous_type)



def find_first_file(path):
    if os.path.isfile(path):
        test(path)
    elif os.path.isdir(path):
        for entry in os.listdir(path):
            find_first_file(os.path.join(path, entry))



def convert_to_utf8(filepath):
    try:
        # Prova a leggere il file come UTF-8
        with open(filepath, 'r', encoding='utf-8') as f:
            f.read()
    except UnicodeDecodeError:
        print(f"[INFO] Conversione necessaria per: {filepath}")
        # Prova con altre encoding comuni (puoi estendere questa lista)
        encodings_to_try = ['latin1', 'iso-8859-1', 'windows-1252']
        for enc in encodings_to_try:
            try:
                with open(filepath, 'r', encoding=enc) as f:
                    content = f.read()
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"[CONVERTITO] Da {enc} a UTF-8: {filepath}")
                return
            except UnicodeDecodeError:
                continue
        print(f"[ERRORE] Non riesco a determinare l'encoding di: {filepath}")



def test(argument):
    # Get the basename.
    basename = os.path.basename(argument)
    # Get just the name.
    name, _ = os.path.splitext(basename)
    if _ == ".circuit" or _==".cir" or _==".cir":
        convert_to_utf8(argument)
        print(f"\nTesting '{basename}' from '{os.path.dirname(argument)}':")
        # Generate output names.
        out_xml = os.path.join("eldo_result/", "{}.xml".format(name))
        out_json = os.path.join("eldo_result/", "{}.json".format(name))
        out_eldo = os.path.join("eldo_result/", "{}.cir".format(name))

        # Get the content.
        print("Parsing `{}`".format(argument))
        root = edacurry.parse_eldo(argument)
        # Write to XML.
        xml_content = edacurry.write_xml(root)
        # If required generate the output file.
        print("Writing `{}`".format(out_xml))
        with open(out_xml, "w") as outf:
            outf.write(xml_content)
        # Write to JSON.
        json_content = edacurry.write_json(root)
        # If required generate the output file.
        print("Writing `{}`".format(out_json))
        with open(out_json, "w") as outf:
            outf.write(json_content)
        # Write to ELDO.
        eldo_content = edacurry.write_eldo(root)
        # If required generate the output file.
        print("Writing `{}`".format(out_eldo))
        with open(out_eldo, "w") as outf:
            outf.write(eldo_content)
        # Compare the two files.
        compare(argument, out_eldo)

if not os.path.exists("eldo_result"):
    os.mkdir("eldo_result")

if len(sys.argv) == 1:
    # Test all files in the working directory
    find_first_file("eldo")
else:
    print("Argomenti forniti non supportati!")