import re
import time
import json
from typing import List, Optional, Tuple
import concurrent.futures
from multiprocessing import cpu_count
import requests
from bs4 import BeautifulSoup
from googlesearch import search

def hp_statements_dictionary(file_path: str) -> dict:
    '''
    Function that takes a formatted .txt file in the project folder as input and generates a
    dictionary in the format key = H/P code, value = H/P statement.
    This dictionary can later be used to lookup H and P codes and translate them to human
    readable statements.
    '''
    with open(file_path, 'r', encoding='UTF-8') as file:
        hp_dict = {}
        for line in file:
            (code, phrase) = line.split(' ', 1)
            hp_dict[code] = phrase.replace('\n', "")
    return hp_dict

def exact_google_search_by_website(search_terms: str, site: str='') -> List[str]:
    '''
    Function that uses the standard google search library but adds a site condition if specified.
    Returns the first 5 matching links as a list for an exact term search.
    '''
    if site != '':
        query = f'site:{site} "{search_terms}"'
    else:
        query = f'"{search_terms}"'
    found_links = []
    for item in search(query, tld='com', lang='en', num=10, start=0, stop=5, pause=0.5):
        found_links.append(item)
    return found_links

def get_response_text(link: str, attempts: int=3) -> Optional[str]:
    '''
    Function that emulates the use of a web browser by passing headers to the website such that a
    HTML response 200 is obtained. The function returns the source code of the webpage as a string
    that can later be processed using BeautifulSoup4.

    The function attempts to get a valid response a number of (by default) 3 times, which can be
    changed by passing the 'attempts' argument.
    '''
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like \
            Gecko) Chrome/106.0.0.0 Safari/537.36',
        'country_code': 'GB',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }
    params = dict(lang='en-US,en;q=0.5')

    for i in range(attempts):
        try:
            response = session.get(link, headers=headers, params=params, timeout=5, \
                allow_redirects=True)
        except requests.exceptions.Timeout:
            time.sleep(3 * (i + 1))
            return ''
        else:
            if response.ok:
                return response.text
    print(f'get_response_text failed on link {link} after {attempts} attempts')
    return ""

def parse_script_tag_from_html(response_text: str) -> Optional[dict]:
    '''
    Function that parses a HTML text string and strips the first found JSON data set. This is passed
    to the standard json library to be converted from string to an addressable dictionary where data
    lookup can be performed.
    The function returns a json.loads dict object.
    '''
    soup = BeautifulSoup(response_text, "html.parser")
    box = soup.findAll('script', attrs={'type': 'application/json'})
    json_string = box[0].text.strip()

    if json_string != "":
        return json.loads(json_string)

    print("JSON data not found")
    return None

def initiate_chem_dict_from_text(file_path: str) -> list[str]:
    '''
    Function that reads a .txt file line by line and makes a dictionary with key = name and
    value = Chemical(name). The dictionary initiates a Chemical data storage class for each key.
    Returns a dictionary prepared for data assignment.
    '''
    dict1={}
    with open(file_path, 'r', encoding='UTF-8') as file:
        for line in file:
            dict1[line.replace('\n', "")] = Chemical(line.replace('\n', ""))
    return dict1

def hp_string_to_list(input_string: str) -> List[str]:
    '''
    Function that takes a string, splits it by [,+ -] and returns a list of the words.
    '''
    out = []
    for item in re.split('[,+ -]', input_string):
        if item != '':
            # strip code of any subclasses. eg H361f -> H361
            item[:] = item[:4]
            out.append(item)
    return out

def find_hp_sigma_compliance(list1: list) -> Tuple[int, int]:
    '''
    Function that takes the compliance section of a Sigma-Aldrich product JSON file as input and
    searches for the index of the h and p codes dictionaries. Returns both indexes.
    '''
    h_c_idx, p_c_idx = None, None
    for (index, data) in enumerate(list1):
        if data['key'] == 'hcodes':
            h_c_idx = index
        elif data['key'] == 'pcodes':
            p_c_idx = index
    return h_c_idx, p_c_idx

class Chemical:
    '''
    This class stores data about the chemical, such as websites and compliance details.
    '''
    def __init__(self, name: str):
        self.name = name
        self.links = []
        self.hcodes = None
        self.pcodes = None
        self.found_on_first_attempt = True

    def add_links(self, links: List[str]):
        '''
        Adds the contents of the input links list to the instance links list.
        '''
        self.links += links

    def set_codes(self, typ: str, codes: List[str]):
        '''
        Function that sets the s or p codes strings.
        '''
        if typ == 'h':
            self.hcodes = codes
        elif typ == 'p':
            self.pcodes = codes

    def set_found_first(self, value: bool):
        '''
        This function sets the status of the self.found_on_first_attempt flag.
        '''
        self.found_on_first_attempt = value

if __name__ == "__main__":
    # set default website path to products page of the sigmaaldrich.com website
    PATH_TO_SIGMA_PRODUCT = 'sigmaaldrich.com/US/en/product'
    # initiate dictionary to later match H/P codes with human readable phrases.
    h_p_dict = hp_statements_dictionary('phrases.txt')
    # read chemicals list from input file and prepare a dictionary where
    # data per chemical can be stored.
    chemicals_storage = initiate_chem_dict_from_text('chemicals.txt')

    # SLOW SECTION NEEDS MULTITHREADING/MULTIPROCESSING. Most time wasted.
   
    # for (chemical, _) in chemicals_storage.items():
    #     # perform google search of current chemical with the specified
    #     # website path.
    #     chemicals_storage[chemical].add_links\
    #         (exact_google_search_by_website(chemical, PATH_TO_SIGMA_PRODUCT))

    def myfunction(chem):
        '''
        Google search function. Only created for multithreading purposes.
        '''
        chemicals_storage[chem].add_links(
            exact_google_search_by_website(chem, PATH_TO_SIGMA_PRODUCT)
            )

    # Create a thread pool with the maximum available number of threads and perform the google
    # search function concurrently. Reduces wait time from ~3 seconds per chemical to
    # ~3 seconds per cpu_count() chemicals.
    executor = concurrent.futures.ThreadPoolExecutor(cpu_count())
    futures = [executor.submit(myfunction, chemical) for (chemical, _) in chemicals_storage.items()]
    concurrent.futures.wait(futures)

    for (chemical, _) in chemicals_storage.items():
        for (idx, website_link) in enumerate(chemicals_storage[chemical].links):
            # get JSON data from website and parse it.
            json_dict = \
                parse_script_tag_from_html(get_response_text(website_link))

            compliance_details = \
                json_dict['props']['pageProps']['data']['getProductDetail']['compliance'] \
                if json_dict is not None else None

            # Check if the chemical has any stated hazard or precautionary codes,
            # and if it does, store them.
            h_codes_index, p_codes_index = find_hp_sigma_compliance(compliance_details)

            if h_codes_index is not None:
                chemicals_storage[chemical].set_codes('h', \
                    hp_string_to_list(compliance_details[h_codes_index]['value']))

            if p_codes_index is not None:
                chemicals_storage[chemical].set_codes('p', \
                    hp_string_to_list(compliance_details[p_codes_index]['value']))

            # break the loop after the first website that has any H or P codes
            # stated for the chemical.
            if h_codes_index is not None or p_codes_index is not None:
                if idx > 0:
                    chemicals_storage[chemical].set_found_first(False)
                break

    # all necessary data has been collected. Write data in an output file and format it such that
    # it can be copied and used directly in a document.
    with open(r'output.txt', 'w', encoding='UTF-8') as out_file:
        for (chemical, _) in chemicals_storage.items():
            out_file.write(f'{chemical} ')
            # write !!! next to the chemical name if the H and P codes were not found using the
            # first search result. Chemical should be checked manually if so.
            if not chemicals_storage[chemical].found_on_first_attempt:
                out_file.write('!!! \n')
            else:
                out_file.write('\n')
            # check if the chemical has any H codes and if it does, translate them to human-readable
            # statements using the h_p_dict dictionary.
            if chemicals_storage[chemical].hcodes is not None:
                out_file.write('H statements: \n')
                for hcode in chemicals_storage[chemical].hcodes:
                    # if the code is not defined in the dictionary, skip it (done on purpose as some
                    # of the codes are not relevant).
                    out_file.write(f'{h_p_dict.get(hcode, "")} ')
                out_file.write('\n')

            # do the same for P codes.
            if chemicals_storage[chemical].pcodes is not None:
                out_file.write('P statements: \n')
                for pcode in chemicals_storage[chemical].pcodes:
                    out_file.write(f'{h_p_dict.get(pcode, "")} ')
                out_file.write('\n')

            out_file.write('\n')
