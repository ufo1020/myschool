import urllib.request
import urllib.parse
from html.parser import HTMLParser
from http import cookies
from http import cookiejar
import time
import random
import os.path
from os import  remove

STATIC_SCHOOL_LIST_FILE = 'myschool.txt'

class myschool_parse(HTMLParser):

    def __init__(self):
        HTMLParser.__init__(self)

        self.m_items = []
        self.m_name = ''
        self.m_link = ''
        self.m_type = ''
        self.m_sector = ''
        self.m_charref = ''
        self.m_suburb = ''
        self.m_postcode = ''
        self.m_is_school = False

    def set_suburb_and_postcode(self, suburb, postcode):
        self.m_suburb = suburb
        self.m_postcode = str(postcode)
        # print('postcode:%s' %postcode)

    def handle_starttag(self, tag, attrs):
        self.find_school(tag, attrs)

    # def clear(self):
    #     self.m_items = []

    def handle_data(self, data):
        data = data.strip()
        # print(data)
        # print(len(data), self.m_is_school)
        if self.m_is_school and len(data):
            self.m_name += self.m_charref + data
        elif data in ['Primary',  'Secondary', 'Special']:
            self.m_type = data
        elif data in ['Government', 'Non-government']:
            self.m_sector = data
            # assume sector is the last item for a school
            self.update_school_list()

    def handle_charref(self, name):
        if name.startswith('x'):
            c = chr(int(name[1:], 16))
        else:
            c = chr(int(name))
        self.m_charref = c

    def find_school(self, tag, attrs):
        # <a href="/Home/Index/86678">Bentleigh Secondary College</a>
        if tag != 'a':
            self.m_is_school = False
            return
        self.m_is_school = True
        for attr in attrs:
            if attr[0] == 'href':
                self.m_link = attr[1]

    def update_school_list(self):
        item = {'name':self.m_name, 'link':self.m_link, 'type':self.m_type, 'sector':self.m_sector, 'suburb':self.m_suburb, 'postcode':self.m_postcode}
        # print(item)
        self.m_items.append(item)
        self.m_name = ''
        self.m_link = ''
        self.m_type = ''
        self.m_sector = ''
        self.m_charref = ''

class school_profile_parse(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        # defines key-value we interested
        self.m_valid = False
        self.m_last_data = ''
        self.m_school_distribut_count = 0 # count data from scholl distribution
        self.m_data_not_reported = 'Data not reported'
        self.m_profile = {'Year range': '',
                  'Teaching staff': '',
                  'Per student net recurrent income': '',
                  'School ICSEA value': '',
                  'School Distribution': '',
                  'Girls': '',
                  'Boys': '',
                  'Language background other than English': '',
                  'Students at university': ''}

    def get_school_profile(self):
        return self.m_profile

    def is_valid(self):
        return self.m_valid

    # def clear(self):
    #     self.m_valid = False
    #     self.m_profile = {'Year range': '',
    #           'Teaching staff': '',
    #           'Per student net recurrent income': '',
    #           'School ICSEA value': '',
    #           'School Distribution': '',
    #           'Girls': '',
    #           'Boys': '',
    #           'Language background other than English': '',
    #           'Students at university': ''}

    def handle_data(self, data):
        data = data.strip()
        # expections:
        # - no data
        # - data not reported
        if not len(data):
            return

        if data in self.m_data_not_reported:
            self.m_last_data =data
            return

        # print("Data:%s" %(data))
        # school distribution has 4 data
        # data: School Distribution
        # data: 3%
        # data: 11%
        # data: 31%
        # data: 55%
        if self.m_school_distribut_count > 0 and self.m_school_distribut_count < 4:
            data_fraction = self.m_profile['School Distribution']
            self.m_profile['School Distribution'] = data_fraction + '; ' + data
            self.m_school_distribut_count += 1

        if self.m_last_data in self.m_profile.keys():
            self.m_valid = True
            if not len(self.m_profile[self.m_last_data]):
                self.m_profile[self.m_last_data] = data

            # start counting next 3 data from school distribution
            if self.m_last_data in 'School Distribution':
                self.m_school_distribut_count = 1

            # print("profiling: %s" %(self.m_profile))

        self.m_last_data = data

def find_suburb_name(suburbs):
    # suburbs = '[{"SchoolDetails":"Bentleigh East,VIC,3165","SMCLID":"86678","Id":0,"SectorCode"'
    # suburbs += '{"SchoolDetails":"East Bentleigh,VIC,3165","SMCLID":"86224","Id":2,"SectorCode":'
    # return format:
    # [{"SchoolDetails":"Bentleigh East,VIC,3165","SMCLID":"86678","Id":0,"SectorCode":null,"SectorCodeDesc":null,"SchoolTypeCodeDesc":null,"SchoolUrl":null}
    key = 'SchoolDetails'
    # while len(suburbs) > 0:
    # if returns more than 1 results from one postcode, just pick the first one
    suburb_list = []
    while len(suburbs):
        index = suburbs.find(key)
        # if nothing found
        if index==-1:
            # print("No school found in this area %s", suburbs)
            break

        suburbs = suburbs[index + len(key) + 3:]
        # finding end of school name
        end = suburbs.find('",')
        value = suburbs[:end]
        suburb_list.append(value)
    return suburb_list

def get_suburb_from_postcode(postcode):
    # suburbs = get_suburb_from_postcode(postcode)
    params = urllib.parse.urlencode({'term':postcode, 'count':20})
    url = "http://www.myschool.edu.au/SchoolSearch/SearchBySuburbTownPostCode?%s" %params
    f = urllib.request.urlopen(url)
    return f.read()

def get_school_list(suburb_string, postcode):
    suburb = suburb_string[:suburb_string.find(',')]

    query = {'Length':4,'.x':40,'.y':15,'SuburbTownPostcodeSearch':suburb_string}
    query['Suburb'] = suburb
    query['PostCode'] = postcode
    query['SectorGovernment'] = 'true'
    query['SectorNonGovernment'] = 'true'
    query['X-Requested-With'] = 'XMLHttpRequest'
    # 13 digits, 1430129329913
    query['_'] = 1430000000000 + random.randint(0, 9000000000)

    params = urllib.parse.urlencode(query)
    url = "http://www.myschool.edu.au/Home/SearchSuburbTownPostcodeSector?%s" %params
    f = urllib.request.urlopen(url)
    response = f.read()

    html_parser = myschool_parse()
    html_parser.set_suburb_and_postcode(suburb, postcode)
    # html_parser.clear()
    html_parser.feed(response.decode('UTF-8'))

    return html_parser.m_items

def search_postcode(postcode):
    suburbs = get_suburb_from_postcode(postcode)
    # empty result returns '[]'
    if len(suburbs) < 3:
        return
    # print(suburbs, len(suburbs))
    suburb_list = find_suburb_name(suburbs.decode('UTF-8'))

    if len(suburb_list) == 0:
        return

    for suburb in suburb_list:
        print(suburb)
        school_list = get_school_list(suburb, postcode)
        serach_school_detail(school_list)

def save_to_file(school, profile):
    # db = sqlite3.connect('myschool.db')
    # cursor = db.cursor()
    if not len(school):
        return

    f = open(STATIC_SCHOOL_LIST_FILE, 'ab')

    #   item = {'name':self.m_name, 'link':self.m_link, 'type':self.m_type, 'sector':self.m_sector}
    # profile = {'Year range': '',
    #           'Teaching staff': '',
    #           'Total net recurrent income': '',
    #           'School ICSEA value': '',
    #           'School Distribution': '',
    #           'Girls': '',
    #           'Boys': '',
    #           'Language background other than English': '',
    #           'Students at university': ''}
    separater = ';'

    line = school['name']
    line += separater + school['type']
    if len(school['type']) == 0:
        line += ' '

    line += separater + school['sector']
    line += separater + school['suburb']
    for key in sorted(profile):
        # add space for empty items
        if len(profile[key]) == 0:
            if key == 'School Distribution':
                for i in range(0, 4):
                    line += separater + ' '
            else:
                line += separater + ' '
        else:
            line += separater + profile[key]

    line += separater + school['postcode']
    line += '\n'
    # print(line)
    # f.write(''.join('%s, ' %(value) for value in item.values))
    f.write(bytes(line, 'UTF-8'))
    # print(line)

    f.close()
    # print('done')

def load_cookies():
    cookies = {'.ASPXAUTH': '', 'ARRAffinity':'','.ESAPI_SESSIONID':'','__utmt':'','__utma':'','__utmb':'','__utmc':'','__utmz':''}
    f = open('cookies.txt')
    raw_data = f.read()
    for key in cookies:
        # __utmt=1
        start = raw_data.find(key)
        if start == -1:
            continue
        start += len(key) + 1
        end = raw_data.find(';', start)

        if end == -1:
            cookies[key] = raw_data[start:]
        else:
            cookies[key] = raw_data[start:end]

    return cookies
    # print(cookies)
    # login_data = {'.ASPXAUTH':'5F6DBF7B4057AFC82A3EA82D3DAD76405D53A5A8DFA24CBDF49673E2A41062D2BB330F102539CF812FFE13816DAA687766DDEFDB86A3757BF0E11DE6832210501BFDB5CD'}
    # login_data['ARRAffinity'] = 'f66487746c30c9d858ccc28cc6d039d1a3cf71acfa4a87c6c1b54d51b8bae1e0'
    # login_data['.ESAPI_SESSIONID'] = 'vgwnejayahtofyhmrmf5opma'
    # login_data['__utmt'] = 1
    # login_data['__utma'] = '93103489.290018555.1431172708.1431172708.1431175474.2'
    # login_data['__utmb'] = '93103489.4.10.1431175474'
    #
    # login_data['__utmc'] = '93103489'
    # login_data['__utmz'] = '93103489.1431172708.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none)'


def serach_school_detail(school_list):
    cj = cookiejar.CookieJar()
    opener = urllib.request.build_opener()
    login_data = urllib.parse.urlencode({})

    login_data = load_cookies()

    opener.addheaders.append(('Cookie', "; ".join('%s=%s' % (k,v) for k,v in login_data.items())))

    invalid_data_threshold = 3
    invalid_data_count = 0
    for school in school_list:
        # print(school)
        link = school['link']
        target = 'http://myschool.edu.au' + link
        # print(target)
        f = opener.open(target)
        resp = f.read()

        # print(resp)
        html_parser = school_profile_parse()
        # html_parser.clear()
        # print("Before parse: %s" %(html_parser.get_school_profile()))
        html_parser.feed(resp.decode('UTF-8'))
        # print("profile:")
        profile = html_parser.get_school_profile()

        if not html_parser.is_valid():
            invalid_data_count += 1
        else:
            invalid_data_count = 0
        save_to_file(school, profile)

        if invalid_data_count >= invalid_data_threshold:
            print("data invalid anymore")
            raise

def main():
    start = 3100
    end = 3250
    if os.path.isfile(STATIC_SCHOOL_LIST_FILE):
        #retrieve last postcode first
        f = open(STATIC_SCHOOL_LIST_FILE)
        content = f.read()
        f.close()

        # find last postcode
        if len(content) > 4:
            postcode = content[len(content) - 5:]
            postcode= postcode.strip()

            if postcode.isdigit():
                # print(postcode)

                f = open(STATIC_SCHOOL_LIST_FILE)
                lines = f.readlines()
                f.close()

                # remove invalid postcode records
                f = open(STATIC_SCHOOL_LIST_FILE, 'w')
                for line in lines:
                    # if the line does not contains invalid postcode
                    if line.find(postcode) == -1:
                        # print("adding line:%s"%line)
                        f.write(line)
                    # else:
                        # print("removing line:%s" %line)

                f.close()
                start = int(postcode)

    for postcode in range(start, end):
        search_postcode(postcode)
        time.sleep(1)

class test:
    def __int__(self):
        self.r = 0
        self.n = 0


def test_test():
    m_profile = {'Year range': '',
          'Teaching staff': '',
          'Per student net recurrent income': '',
          'School ICSEA value': '',
          'School Distribution': '',
          'Girls': '',
          'Boys': '',
          'Language background other than English': '',
          'Students at university': ''}

    # keys = m_profile.keys()
    # keys.sort()
    # print(keys)
    for key in sorted(m_profile):
        print(key)

if __name__ == "__main__":
    main()
    # test_test()