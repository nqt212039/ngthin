import requests
import json
import time
import random
import string
import re
from os.path import basename
from mimetypes import guess_type
import requests
import os
import json
import re
from html import unescape
from io import BytesIO


def get_uid_fbdtsg(ck):
  try:
    headers = {
      'Accept': 'text/html',
      'Cookie': ck,
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }

    response = requests.get('https://www.facebook.com/', headers=headers)
    html_content = response.text

    if "home_icon" not in html_content and '"USER_ID":"' not in html_content:
      return None, None, None, None, None, None

    user_id = re.search(r'"USER_ID":"(\d+)"', html_content)
    user_id = user_id.group(1) if user_id else None

    fb_dtsg_match = re.search(r'"f":"([^"]+)"', html_content)
    fb_dtsg = fb_dtsg_match.group(1) if fb_dtsg_match else None

    jazoest_match = re.search(r'jazoest=(\d+)', html_content)
    jazoest = jazoest_match.group(1) if jazoest_match else None

    revision_match = re.search(r'"server_revision":(\d+),"client_revision":(\d+)', html_content)
    rev = revision_match.group(1) if revision_match else ""

    a_match = re.search(r'__a=(\d+)', html_content)
    a = a_match.group(1) if a_match else "1"

    req = "1b"

    if not user_id or not fb_dtsg:
      return None, None, None, None, None, None

    return user_id, fb_dtsg, rev, req, a, jazoest

  except Exception as e:
    print(f"Lỗi Khi Check Cookie: {e}")
    return None, None, None, None, None, None


def upload_image_get_fbid(image_path_or_url: str, ck: str) -> str:
  user_id, fb_dtsg, rev, req, a, jazoest = get_uid_fbdtsg(ck)
  if not all([user_id, fb_dtsg, jazoest]):
    return "Không thể lấy thông tin từ cookie. Vui lòng kiểm tra lại."

  # Tải ảnh nếu là URL
  is_url = image_path_or_url.startswith("http://") or image_path_or_url.startswith("https://")
  try:
    if is_url:
      resp = requests.get(image_path_or_url)
      if resp.status_code != 200:
        return "Không thể tải ảnh từ URL."
      img_data = BytesIO(resp.content)
      img_data.name = "image.jpg"
    else:
      if not os.path.isfile(image_path_or_url):
        return "File không tồn tại. Hãy nhập đúng đường dẫn tới ảnh."
      img_data = open(image_path_or_url, 'rb')
  except Exception as e:
    return f"Lỗi khi đọc ảnh: {e}"

  headers = {
    'cookie': ck,
    'origin': 'https://www.facebook.com',
    'referer': 'https://www.facebook.com/',
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64)',
    'x-fb-lsd': fb_dtsg,
  }

  params = {
    'av': user_id,
    'profile_id': user_id,
    'source': '19',
    'target_id': user_id,
    '__user': user_id,
    '__a': a,
    '__req': req,
    '__rev': rev,
    'fb_dtsg': fb_dtsg,
    'jazoest': jazoest,
  }

  try:
    files = {
      'file': (img_data.name, img_data, 'image/jpeg')
    }

    response = requests.post(
      'https://www.facebook.com/ajax/ufi/upload/',
      headers=headers,
      params=params,
      files=files
    )

    if is_url:
      img_data.close()

    text = response.text.strip()
    if text.startswith("for(;;);"):
      text = text[8:]

    try:
      data = json.loads(text)
      fbid = data.get("payload", {}).get("fbid")
      if fbid:
        return fbid
      return "Không tìm thấy fbid trong JSON."

    except json.JSONDecodeError:
      match = re.search(r'"fbid"\s*:\s*"(\d+)"', text)
      if match:
        return match.group(1)
      return "Không tìm thấy fbid trong text."

  except Exception as e:
    return f"Lỗi khi upload: {e}"


def parse_cookie_string(cookie_string):
    """Parse cookie string into dictionary"""
    cookie_dict = {}
    cookies = cookie_string.split(";")
    for cookie in cookies:
        if "=" in cookie:
            key, value = cookie.split("=", 1)  # Split only on first =
            try: 
                cookie_dict[key.strip()] = value.strip()
            except: 
                pass
    return cookie_dict


def digitToChar(digit):
    """Convert digit to character for base conversion"""
    if digit < 10:
        return str(digit)
    return chr(ord('a') + digit - 10)


def str_base(number, base):
    """Convert number to specified base"""
    if number < 0:
        return "-" + str_base(-number, base)
    (d, m) = divmod(number, base)
    if d > 0:
        return str_base(d, base) + digitToChar(m)
    return digitToChar(m)


def base36encode(number: int, alphabet="0123456789abcdefghijklmnopqrstuvwxyz"):
    """Encode number to base36"""
    if not isinstance(number, int):
        raise TypeError("number must be an integer")

    base36 = ""
    sign = ""

    if number < 0:
        sign = "-"
        number = -number

    if 0 <= number < len(alphabet):
        return sign + alphabet[number]

    while number != 0:
        number, i = divmod(number, len(alphabet))
        base36 = alphabet[i] + base36

    return sign + base36


def dataSplit(string1, string2, numberSplit1=None, numberSplit2=None, HTML=None, amount=None, string3=None, numberSplit3=None, defaultValue=None):
    """Split HTML/text data"""
    if defaultValue: 
        numberSplit1, numberSplit2 = 1, 0
    if amount is None:
        return HTML.split(string1)[numberSplit1].split(string2)[numberSplit2]
    elif amount == 3:
        return HTML.split(string1)[numberSplit1].split(string2)[numberSplit2].split(string3)[numberSplit3]


def get_from(input_str, start_token, end_token):
    """Extract text between start and end tokens"""
    start = input_str.find(start_token) + len(start_token)
    if start < len(start_token):
        return ""

    last_half = input_str[start:]
    end = last_half.find(end_token)
    if end == -1:
        raise ValueError(f"Could not find endTime `{end_token}` in the given string.")

    return last_half[:end]


def generate_offline_threading_id() -> str:
    """Generate offline threading ID"""
    ret = int(time.time() * 1000)
    value = random.randint(0, 4294967295)
    binary_str = format(value, "022b")[-22:]
    msgs = bin(ret)[2:] + binary_str
    return str(int(msgs, 2))


def generate_session_id():
    """Generate a random session ID between 1 and 9007199254740991"""
    return random.randint(1, 2 ** 53)


def generate_client_id():
    """Generate client ID"""
    def gen(length):
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))
    return gen(8) + '-' + gen(4) + '-' + gen(4) + '-' + gen(4) + '-' + gen(12)


def json_minimal(data):
    """Get JSON data in minimal form"""
    return json.dumps(data, separators=(",", ":"))


def gen_threading_id():
    """Generate threading ID"""
    return str(
        int(format(int(time.time() * 1000), "b") + 
        ("0000000000000000000000" + 
        format(int(random.random() * 4294967295), "b"))
        [-22:], 2)
    )


def require_list(list_):
    """Convert to set if list, otherwise create set with single item"""
    if isinstance(list_, list):
        return set(list_)
    else:
        return set([list_])


def get_files_from_paths(filenames):
    """Get files from file paths"""
    files = [filenames, open(filenames, "rb"), guess_type(filenames)[0]]
    yield files


def clearHTML(text):
    """Remove HTML tags from text"""
    regex = re.compile(r'<[^>]+>')
    return regex.sub('', text)


# ============================================================================
# HEADER AND REQUEST FUNCTIONS
# ============================================================================

def get_headers(url: str, options: dict = {}, ctx: dict = {}, customHeader: dict = {}):
    """Get headers for requests"""
    headers = {
        "Accept-Encoding": "gzip, deflate",
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "https://www.facebook.com/",
        "Host": url.replace("https://", "").split("/")[0],
        "Origin": "https://www.facebook.com",
        "User-Agent": "Mozilla/5.0 (Linux; Android 9; SM-G973U Build/PPR1.180610.011) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Mobile Safari/537.36",
        "Connection": "keep-alive",
    }

    if "user_agent" in options:
        headers["User-Agent"] = options["user_agent"]

    for key in customHeader:
        headers[key] = customHeader[key]

    if "region" in ctx:
        headers["X-MSGR-Region"] = ctx["region"]

    return headers


def Headers(setCookies, dataForm=None, Host=None):
    """Generate headers for Facebook requests"""
    if Host is None: 
        Host = "www.facebook.com"
    headers = {}
    headers["Host"] = Host
    headers["Connection"] = "keep-alive"
    if dataForm is not None:
        headers["Content-Length"] = str(len(dataForm))
    headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36"
    headers["Accept"] = "*/*"
    headers["Origin"] = "https://" + Host
    headers["Sec-Fetch-Site"] = "same-origin"
    headers["Sec-Fetch-Mode"] = "cors"
    headers["Sec-Fetch-Dest"] = "empty"
    headers["Referer"] = "https://" + Host
    headers["Accept-Language"] = "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"
    
    return headers


# ============================================================================
# COUNTER CLASS
# ============================================================================

class Counter:
    """Simple counter class"""
    def __init__(self, initial_value=0):
        self.value = initial_value
        
    def increment(self):
        self.value += 1
        return self.value
        
    @property
    def counter(self):
        return self.value


# ============================================================================
# FORM AND REQUEST BUILDERS
# ============================================================================

# Global counter for requests
_req_counter = Counter(0)


def formAll(dataFB, FBApiReqFriendlyName=None, docID=None, requireGraphql=None):
    """Build form data for Facebook API requests"""
    global _req_counter
    
    __reg = _req_counter.increment()
    dataForm = {}
    
    if requireGraphql is None:
        dataForm["fb_dtsg"] = dataFB["fb_dtsg"]
        dataForm["jazoest"] = dataFB["jazoest"]
        dataForm["__a"] = 1
        dataForm["__user"] = str(dataFB["FacebookID"])
        dataForm["__req"] = str_base(__reg, 36) 
        dataForm["__rev"] = dataFB["clientRevision"]
        dataForm["av"] = dataFB["FacebookID"]
        dataForm["fb_api_caller_class"] = "RelayModern"
        dataForm["fb_api_req_friendly_name"] = FBApiReqFriendlyName
        dataForm["server_timestamps"] = "true"
        dataForm["doc_id"] = str(docID)
    else:
        dataForm["fb_dtsg"] = dataFB["fb_dtsg"]
        dataForm["jazoest"] = dataFB["jazoest"]
        dataForm["__a"] = 1
        dataForm["__user"] = str(dataFB["FacebookID"])
        dataForm["__req"] = str_base(__reg, 36) 
        dataForm["__rev"] = dataFB["clientRevision"]
        dataForm["av"] = dataFB["FacebookID"]

    return dataForm


def mainRequests(url, data, cookies):
    """Build request parameters for Facebook API"""
    if isinstance(url, str) and isinstance(data, dict):
        # New format (from b.py)
        return {
            "url": url,
            "data": data,
            "headers": {
                "authority": "www.facebook.com",
                "accept": "*/*",
                "accept-language": "en-US,en;q=0.9,vi;q=0.8",
                "content-type": "application/x-www-form-urlencoded",
                "origin": "https://www.facebook.com",
                "referer": "https://www.facebook.com/",
                "sec-ch-ua": "\"Not?A_Brand\";v=\"8\", \"Chromium\";v=\"108\"",
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": "\"Windows\"",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "user-agent": "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
                "x-fb-friendly-name": "FriendingCometFriendRequestsRootQueryRelayPreloader",
                "x-fb-lsd": "YCb7tYCGWDI6JLU5Aexa1-"
            },
            "cookies": parse_cookie_string(cookies),
            "verify": True
        }
    else:
        # Old format (from utils.py)
        return {
            "headers": Headers(cookies, data),
            "timeout": 5,
            "url": url,
            "data": data,
            "cookies": parse_cookie_string(cookies),
            "verify": True
        }


# ============================================================================
# DATA EXTRACTION FUNCTIONS
# ============================================================================

def dataGetHome(setCookies):
    """Extract Facebook data from home page"""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
    ]
    
    dictValueSaved = {}
    
    try:
        c_user = re.search(r"c_user=(\d+)", setCookies)
        if c_user:
            dictValueSaved["FacebookID"] = c_user.group(1)
        else:
            dictValueSaved["FacebookID"] = "Unable to retrieve data for FacebookID. Cookie không hợp lệ."
    except:
        dictValueSaved["FacebookID"] = "Unable to retrieve data for FacebookID. It's possible that they have been deleted or modified."
    
    headers = {
        'Cookie': setCookies,
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,/;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1'
    }
    
    sites_to_try = ['https://www.facebook.com', 'https://mbasic.facebook.com', 'https://m.facebook.com']
    fb_dtsg_found = False
    jazoest_found = False
    
    params_to_extract = {
        "fb_dtsg": None,
        "fb_dtsg_ag": None,
        "jazoest": None,
        "hash": None,
        "sessionID": None,
        "clientRevision": None
    }
    
    for site in sites_to_try:
        if fb_dtsg_found and jazoest_found:
            break
            
        try:
            response = requests.get(site, headers=headers)
            
            if not fb_dtsg_found:
                fb_dtsg_match = re.search(r'"token":"(.*?)"', response.text)
                if not fb_dtsg_match:
                    fb_dtsg_match = re.search(r'name="fb_dtsg" value="(.*?)"', response.text)
                
                if fb_dtsg_match:
                    params_to_extract["fb_dtsg"] = fb_dtsg_match.group(1)
                    fb_dtsg_found = True
            
            if not jazoest_found:
                jazoest_match = re.search(r'jazoest=(\d+)', response.text)
                if jazoest_match:
                    params_to_extract["jazoest"] = jazoest_match.group(1)
                    jazoest_found = True
            
            fb_dtsg_ag_match = re.search(r'async_get_token":"(.*?)"', response.text)
            if fb_dtsg_ag_match:
                params_to_extract["fb_dtsg_ag"] = fb_dtsg_ag_match.group(1)
            
            hash_match = re.search(r'hash":"(.*?)"', response.text)
            if hash_match:
                params_to_extract["hash"] = hash_match.group(1)
            
            session_match = re.search(r'sessionId":"(.*?)"', response.text)
            if session_match:
                params_to_extract["sessionID"] = session_match.group(1)
            
            revision_match = re.search(r'client_revision":(\d+)', response.text)
            if revision_match:
                params_to_extract["clientRevision"] = revision_match.group(1)
                
        except Exception as e:
            continue
    
    for param, value in params_to_extract.items():
        if value:
            dictValueSaved[param] = value
        else:
            dictValueSaved[param] = f"Unable to retrieve data for {param}. It's possible that they have been deleted or modified."
    
    dictValueSaved["__rev"] = "1015919737"
    dictValueSaved["__req"] = "1b"
    dictValueSaved["__a"] = "1"
    dictValueSaved["cookieFacebook"] = setCookies
    
    return dictValueSaved


# ============================================================================
# FACEBOOK TOOLS CLASS
# ============================================================================

class fbTools:
    """Facebook tools for thread management and data extraction"""
    
    def __init__(self, dataFB, threadID="0"):
        self.threadID = threadID
        self.dataGet = None
        self.dataFB = dataFB
        self.ProcessingTime = None
        self.last_seq_id = None
    
    def getAllThreadList(self):
        """Get all thread list from Facebook"""
        randomNumber = str(int(format(int(time.time() * 1000), "b") + ("0000000000000000000000" + format(int(random.random() * 4294967295), "b"))[-22:], 2))
        dataForm = formAll(self.dataFB, requireGraphql=0)

        dataForm["queries"] = json.dumps({
            "o0": {
                "doc_id": "3336396659757871",
                "query_params": {
                    "limit": 20,
                    "before": None,
                    "tags": ["INBOX"],
                    "includeDeliveryReceipts": False,
                    "includeSeqID": True,
                }
            }
        })
        
        sendRequests = requests.post(**mainRequests("https://www.facebook.com/api/graphqlbatch/", dataForm, self.dataFB["cookieFacebook"]))
        response_text = sendRequests.text
        self.ProcessingTime = sendRequests.elapsed.total_seconds()
        
        if response_text.startswith("for(;;);"):
            response_text = response_text[9:]
        
        if not response_text.strip():
            print("Error: Empty response from Facebook API")
            return False
            
        try:
            response_parts = response_text.split("\n")
            first_part = response_parts[0]
            
            if first_part.strip():
                response_data = json.loads(first_part)
                self.dataGet = first_part
                
                if "o0" in response_data and "data" in response_data["o0"] and "viewer" in response_data["o0"]["data"] and "message_threads" in response_data["o0"]["data"]["viewer"]:
                    self.last_seq_id = response_data["o0"]["data"]["viewer"]["message_threads"]["sync_sequence_id"]
                    return True
                else:
                    print("Error: Expected fields not found in response")
                    return False
            else:
                print("Error: Empty first part of response")
                return False
                
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e}")
            print(f"Response first part: {response_parts[0][:100]}")
            return False
        except KeyError as e:
            print(f"Key Error: {e}")
            print("The expected data structure wasn't found in the response")
            return False
    
    def typeCommand(self, commandUsed):
        """Execute various commands on thread data"""
        listData = []
        
        try:
            if self.dataGet is None:
                return "No data available. Make sure to call getAllThreadList first."
                
            data_to_parse = self.dataGet
            if data_to_parse.startswith("for(;;);"):
                data_to_parse = data_to_parse[9:]
                
            getData = json.loads(data_to_parse)["o0"]["data"]["viewer"]["message_threads"]["nodes"]
        except json.JSONDecodeError as e:
            return f"Failed to decode JSON response: {e}"
        except KeyError as e:
            try:
                error_data = json.loads(data_to_parse)["o0"]
                if "errors" in error_data:
                    return error_data["errors"][0]["summary"]
                else:
                    return f"Unexpected response structure. Missing key: {e}"
            except:
                return f"Unexpected response structure. Missing key: {e}"
        
        dataThread = None
        for getNeedIDThread in getData:
            thread_key = getNeedIDThread.get("thread_key", {})
            thread_fbid = thread_key.get("thread_fbid")
            if thread_fbid and str(thread_fbid) == str(self.threadID):
                dataThread = getNeedIDThread
                break
        
        if dataThread is not None:
            if commandUsed == "getAdmin":
                for dataID in dataThread.get("thread_admins", []):
                    listData.append(str(dataID["id"]))
                exportData = {
                    "adminThreadList": listData
                }
            elif commandUsed == "threadInfomation":
                threadInfoList = dataThread.get("customization_info", {})
                exportData = {
                    "nameThread": dataThread.get("name"), 
                    "IDThread": self.threadID, 
                    "emojiThread": threadInfoList.get("emoji"),
                    "messageCount": dataThread.get("messages_count"),
                    "adminThreadCount": len(dataThread.get("thread_admins", [])),
                    "memberCount": len(dataThread.get("all_participants", {}).get("edges", [])),
                    "approvalMode": "Bật" if (dataThread.get("approval_mode", 0) != 0) else "Tắt",
                    "joinableMode": "Bật" if (dataThread.get("joinable_mode", {}).get("mode") != "0") else "Tắt",
                    "urlJoinableThread": dataThread.get("joinable_mode", {}).get("link", "")
                }
            elif commandUsed == "exportMemberListToJson":
                getMemberList = dataThread.get("all_participants", {}).get("edges", [])
                for exportMemberList in getMemberList:
                    node = exportMemberList.get("node", {})
                    dataUserThread = node.get("messaging_actor", {})
                    if dataUserThread:
                        exportData = json.dumps({
                            dataUserThread.get("id", ""): {
                                "nameFB": str(dataUserThread.get("name", "")),
                                "idFacebook": str(dataUserThread.get("id", "")),
                                "profileUrl": str(dataUserThread.get("url", "")),
                                "avatarUrl": str(dataUserThread.get("big_image_src", {}).get("uri", "")),
                                "gender": str(dataUserThread.get("gender", "")),
                                "usernameFB": str(dataUserThread.get("username", ""))
                            }
                        }, skipkeys=True, allow_nan=True, ensure_ascii=False, indent=5)
                        listData.append(exportData)
                exportData = listData
            else:
                exportData = {
                    "err": "no data"
                }
                
            return exportData
            
        else:
            return "Không lấy được dữ liệu ThreadList, đã xảy ra lỗi T___T"
    
    def getListThreadID(self):
        """Get list of thread IDs and names"""
        try:
            if self.dataGet is None:
                return {
                    "ERR": "No data available. Make sure to call getAllThreadList first."
                }
                
            data_to_parse = self.dataGet
            if data_to_parse.startswith("for(;;);"):
                data_to_parse = data_to_parse[9:]
                
            threadIDList = []
            threadNameList = []
            try:
                getData = json.loads(data_to_parse)["o0"]["data"]["viewer"]["message_threads"]["nodes"]
                
                for getThreadID in getData:
                    thread_key = getThreadID.get("thread_key", {})
                    thread_fbid = thread_key.get("thread_fbid")
                    
                    if thread_fbid is not None:
                        threadIDList.append(thread_fbid)
                        threadNameList.append(getThreadID.get("name", "No Name"))
                        
                return {
                    "threadIDList": threadIDList,
                    "threadNameList": threadNameList,
                    "countThread": len(threadIDList)
                }
                
            except (KeyError, json.JSONDecodeError) as e:
                return {
                    "ERR": f"Error processing thread data: {str(e)}"
                }
                
        except Exception as errLog:
            return {
                "ERR": f"Unexpected error: {str(errLog)}"
            }

