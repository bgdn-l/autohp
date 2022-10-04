To install:
1. Create a new venv and activate it. Ideally use python version = 3.10 but should work with anything past 3.6.
2. pip install -r requirements.txt
current venv pip freeze is provided as 'pip freeze.txt'

To run:
1. Add the scientific name of the chemicals you want to lookup in the chemicals.txt file. Each chemical should be on a new line.
2. Run autohp_v2.py with the newly created venv.
3. The formatted output text can be found in output.txt

4(optional). The phrases.txt file contains the translation of the hazard and precautionary codes in human-readable phrases.
Some precautionary statements (P400+) have been intentionally omitted. If needed, add them to the end of the file, each on a new line,
in the format 'code statement' (as the other codes are formatted).