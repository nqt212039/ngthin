import json
import time
import random
import os
from module.utils import (
    parse_cookie_string,
    generate_offline_threading_id,
    generate_session_id,
    generate_client_id,
    json_minimal,
    gen_threading_id,
    get_headers,
    formAll,
    mainRequests,
    dataGetHome,
    fbTools,
    get_from,
    dataSplit,
    clearHTML
)
import paho.mqtt.client as mqtt
from urllib.parse import urlparse
import ssl
import requests

# Global dictionary to store active MQTT senders
active_senders = {}

class MessageSender:
    """MQTT Message Sender for Facebook"""
    
    def __init__(self, fb_tools_instance, dataFB, fb_instance):
        self.fb_tools = fb_tools_instance
        self.dataFB = dataFB
        self.fb = fb_instance
        self.mqtt = None
        self.ws_req_number = 0
        self.ws_task_number = 0
        self.last_seq_id = None
        self.sync_token = None
        self.connected = False
        self.user_id = dataFB.get("FacebookID")
        self.session_id = generate_session_id()
        self.client_id = generate_client_id()
        
    def get_last_seq_id(self):
        """Get the last sequence ID for MQTT synchronization"""
        try:
            # Use fbTools to get thread list and extract sequence ID
            if self.fb_tools.getAllThreadList():
                self.last_seq_id = self.fb_tools.last_seq_id
                print(f"Got sequence ID: {self.last_seq_id}")
                return True
            else:
                print("Failed to get thread list")
                return False
        except Exception as e:
            print(f"Error getting sequence ID: {e}")
            return False
    
    def get_guid(self):
        """Generate GUID"""
        return self.client_id
    
    def connect_mqtt(self):
        """Connect to Facebook MQTT service"""
        try:
            print("Connecting to MQTT...")
            
            chat_on = True
            foreground = False
            
            user = {
                "a": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
                "u": self.user_id,
                "s": self.session_id,
                "chat_on": chat_on,
                "fg": foreground,
                "d": self.get_guid(),
                "ct": "websocket",
                "aid": "219994525426954",  # Facebook app ID
                "mqtt_sid": "",
                "cp": 3,
                "ecp": 10,
                "st": [],
                "pm": [],
                "dc": "",
                "no_auto_fg": True,
                "gas": None,
                "pack": [],
            }
            
            host = f"wss://edge-chat.facebook.com/chat?sid={self.session_id}&cid={self.get_guid()}"
            
            # Parse cookies
            cookie_dict = parse_cookie_string(self.dataFB["cookieFacebook"])
            cookie_str = "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])
            
            # MQTT options
            options = {
                "client_id": "mqttwsclient",
                "username": json_minimal(user),
                "clean": True,
                "ws_options": {
                    "headers": {
                        "Cookie": cookie_str,
                        "Origin": "https://www.facebook.com",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
                        "Referer": "https://www.facebook.com/",
                        "Host": "edge-chat.facebook.com",
                    },
                },
                "keepalive": 10,
            }
            
            # Create MQTT client
            self.mqtt = mqtt.Client(
                client_id=options["client_id"],
                clean_session=options["clean"],
                protocol=mqtt.MQTTv31,
                transport="websockets",
            )
            
            # SSL setup
            self.mqtt.tls_set(certfile=None, keyfile=None, cert_reqs=ssl.CERT_NONE, tls_version=ssl.PROTOCOL_TLSv1_2)
            self.mqtt.tls_insecure_set(True)
            
            # Set callbacks
            self.mqtt.on_connect = self._on_connect
            self.mqtt.on_message = self._on_message
            self.mqtt.on_disconnect = self._on_disconnect
            
            # Set username
            self.mqtt.username_pw_set(username=options["username"])
            
            # Parse host for websocket options
            parsed_host = urlparse(host)
            self.mqtt.ws_set_options(
                path=f"{parsed_host.path}?{parsed_host.query}",
                headers=options["ws_options"]["headers"],
            )
            
            # Connect
            self.mqtt.connect(
                host=options["ws_options"]["headers"]["Host"],
                port=443,
                keepalive=options["keepalive"],
            )
            
            # Start loop in background
            self.mqtt.loop_start()
            
            # Wait for connection
            timeout = 30
            while not self.connected and timeout > 0:
                time.sleep(0.5)
                timeout -= 0.5
            
            if self.connected:
                print("MQTT connected successfully")
                return True
            else:
                print("MQTT connection timeout")
                return False
                
        except Exception as e:
            print(f"Error connecting to MQTT: {e}")
            return False
    
    def _on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        print(f"MQTT connected with result code {rc}")
        
        if rc == 0:
            self.connected = True
            
            # Subscribe to necessary topics
            topics = [
                "/ls_resp",
                "/t_ms",
                "/mercury",
                "/messaging_events",
            ]
            
            for topic in topics:
                client.subscribe(topic, qos=1)
            
            # Send app settings
            client.publish(
                topic="/ls_app_settings",
                payload=json_minimal({
                    "ls_fdid": "", 
                    "ls_sv": "6928813347213944"
                }),
                qos=1,
                retain=False,
            )
            
            # Create sync queue
            queue = {
                "sync_api_version": 10,
                "max_deltas_able_to_process": 1000,
                "delta_batch_size": 500,
                "encoding": "JSON",
                "entity_fbid": self.user_id,
            }
            
            if self.sync_token:
                topic = "/messenger_sync_get_diffs"
                queue["last_seq_id"] = self.last_seq_id
                queue["sync_token"] = self.sync_token
            else:
                topic = "/messenger_sync_create_queue"
                queue["initial_titan_sequence_id"] = self.last_seq_id
                queue["device_params"] = None
            
            client.publish(
                topic=topic,
                payload=json_minimal(queue),
                qos=1,
                retain=False,
            )
        else:
            print(f"MQTT connection failed with code {rc}")
            self.connected = False
    
    def _on_message(self, client, userdata, msg):
        """MQTT message callback"""
        try:
            payload_str = msg.payload.decode("utf-8")
            
            if payload_str.startswith("{"):
                parsed = json.loads(payload_str)
            else:
                parsed = {"t": payload_str}
            
            if msg.topic == "/t_ms":
                if "firstDeltaSeqId" in parsed and "syncToken" in parsed:
                    self.last_seq_id = parsed["firstDeltaSeqId"]
                    self.sync_token = parsed["syncToken"]
                
                if "lastIssuedSeqId" in parsed:
                    self.last_seq_id = parsed["lastIssuedSeqId"]
            
            elif msg.topic == "/ls_resp":
                # Handle response from poll creation
                if "payload" in parsed:
                    payload = json.loads(parsed["payload"])
                    if "actions" in payload:
                        for action in payload["actions"]:
                            if "message_id" in action:
                                print(f"Poll created with message ID: {action['message_id']}")
                    elif "error" in payload:
                        print(f"Poll creation error: {payload['error']}")
                        
        except Exception as e:
            print(f"Error processing MQTT message: {e}")
    
    def _on_disconnect(self, client, userdata, rc):
        """MQTT disconnect callback"""
        print(f"MQTT disconnected with result code {rc}")
        self.connected = False
    
    def send_poll(self, thread_id, question, options):
        """Send poll using MQTT"""
        if not self.connected:
            print("MQTT not connected")
            return False
        
        try:
            self.ws_req_number += 1
            self.ws_task_number += 1
            
            # Create poll payload
            task_payload = {
                "question_text": question,
                "thread_key": int(thread_id),
                "options": options,
                "sync_group": 1,
            }
            
            task = {
                "failure_count": None,
                "label": "163",
                "payload": json.dumps(task_payload, separators=(",", ":")),
                "queue_name": "poll_creation",
                "task_id": self.ws_task_number,
            }
            
            content = {
                "app_id": "2220391788200892",
                "payload": {
                    "data_trace_id": None,
                    "epoch_id": int(generate_offline_threading_id()),
                    "tasks": [task],
                    "version_id": "7158486590867448",
                },
                "request_id": self.ws_req_number,
                "type": 3,
            }
            
            content["payload"] = json.dumps(content["payload"], separators=(",", ":"))
            
            # Publish poll
            self.mqtt.publish(
                topic="/ls_req",
                payload=json.dumps(content, separators=(",", ":")),
                qos=1,
                retain=False,
            )
            return True
            
        except Exception as e:
            print(f"Error sending poll: {e}")
            return False
    
    def stop(self):
        """Stop MQTT connection"""
        if self.mqtt:
            self.mqtt.loop_stop()
            self.mqtt.disconnect()
            self.connected = False


class facebook:
    """Facebook API wrapper"""
    
    def __init__(self, cookie):
        self.cookie = cookie
        self.dataFB = dataGetHome(cookie)
        self.user_id = self.dataFB.get("FacebookID")
        self.fb_dtsg = self.dataFB.get("fb_dtsg")
        self.rev = self.dataFB.get("clientRevision")
        self.jazoest = self.dataFB.get("jazoest")


def start_nhay_poll_func(cookie, idbox, delay_str, folder_name):
    """Start the nhây poll function with MQTT connection"""
    delay = float(delay_str)
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            # Initialize Facebook API
            fb = facebook(cookie)
            if fb.user_id and fb.fb_dtsg:
                # Create fbTools instance
                fb_tools_data = {
                    "FacebookID": fb.user_id,
                    "fb_dtsg": fb.fb_dtsg,
                    "clientRevision": fb.rev,
                    "jazoest": fb.jazoest,
                    "cookieFacebook": cookie
                }
                
                fb_tools_instance = fbTools(fb_tools_data)
                
                # Create message sender with MQTT
                sender = MessageSender(fb_tools_instance, fb.dataFB, fb)
                
                # Store active sender
                active_senders[folder_name] = sender
                
                # Get sequence ID
                if not sender.get_last_seq_id():
                    print("Failed to get sequence ID")
                    retry_count += 1
                    time.sleep(10)
                    continue
                
                # Connect MQTT
                if not sender.connect_mqtt():
                    print("Failed to connect MQTT")
                    retry_count += 1
                    time.sleep(10)
                    continue
                
                # Create or read nhay.txt file
                current_dir = os.path.dirname(os.path.abspath(__file__))
                nhay_path = os.path.join(current_dir, "ngon.txt")
                if not os.path.exists(nhay_path):
                    with open(nhay_path, "w", encoding="utf-8") as f:
                        f.write("cay ak\ncn choa\nsua em\nsua de\nmanh em\ncay ak\ncn nqu")
                
                running = True
                while running:
                    try:
                        # Check if folder still exists
                        folder_path = os.path.join("data", folder_name)
                        if not os.path.exists(folder_path):
                            print(f"Folder {folder_name} no longer exists, stopping...")
                            running = False
                            break
                        
                        # Read poll options from file
                        with open(nhay_path, "r", encoding="utf-8") as f:
                            lines = [line.strip() for line in f.readlines() if line.strip()]
                        
                        if len(lines) < 3:
                            print("Not enough poll options, waiting...")
                            time.sleep(delay)
                            continue
                        
                        # Create polls for each line as question
                        for line in lines:
                            # Check folder existence again
                            folder_path = os.path.join("data", folder_name)
                            if not os.path.exists(folder_path):
                                running = False
                                break
                            
                            title = line.strip()
                            if title:
                                # Get available options (excluding the current title)
                                available_options = [opt for opt in lines if opt != title]
                                
                                if len(available_options) >= 2:
                                    options = random.sample(available_options, 2)
                                else:
                                    # If not enough unique options, add random choices
                                    options = available_options + random.choices(lines, k=2-len(available_options))
                                
                                # Send poll via MQTT
                                success = sender.send_poll(idbox, title, options)
                                
                                if success:
                                             pass
                                else:
                                    print(f"Failed to send poll: '{title}'")
                                
                                # Wait for specified delay
                                time.sleep(delay)
                            
                            # Break if folder is deleted during the loop
                            if not running:
                                break
                    
                    except Exception as e:
                        print(f"Error during nhây poll loop: {e}")
                        if "connection" in str(e).lower() or "mqtt" in str(e).lower():
                            print("Connection error detected, breaking loop...")
                            break
                        time.sleep(10)
                
                # Clean up
                if folder_name in active_senders:
                    active_senders[folder_name].stop()
                    del active_senders[folder_name]
                
                print(f"Nhây poll stopped for thread {idbox}")
                break
                
        except Exception as e:
            print(f"Error initializing Facebook API: {e}")
            retry_count += 1
            time.sleep(10)
    
    if retry_count >= max_retries:
        print(f"Failed to start nhây poll after {max_retries} retries")


def stop_nhay_poll(folder_name):
    """Stop nhây poll for a specific folder"""
    if folder_name in active_senders:
        active_senders[folder_name].stop()
        del active_senders[folder_name]
        print(f"Stopped nhây poll for folder: {folder_name}")
        return True
    else:
        print(f"No active nhây poll found for folder: {folder_name}")
        return False


def get_active_polls():
    """Get list of active poll senders"""
    return list(active_senders.keys())


def is_poll_active(folder_name):
    """Check if poll is active for a folder"""
    return folder_name in active_senders and active_senders[folder_name].connected


# Example usage
if __name__ == "__main__":
    # Example cookie and parameters
    cookie = "datr=956QaLaUtc4IZQCa-8kAP710;sb=956QaCdQYAlY1NegIRy-qhrl;dpr=1.9782406091690063;wd=991x1927;c_user=61566421582707;xs=21%3A9HusoWBAW9cUig%3A2%3A1754308356%3A-1%3A-1;fr=0QxNy25NfxKF6iSp2.AWdGBLpmubxYy3mWiqybTJhcezir1uDUfTeGy_sK40psLQp0o2Y.BokJ73..AAA.0.0.BokJ8I.AWd5SynOk04N8yX7fuQQJCC0XCg;presence=C%7B%22lm3%22%3A%22g.24065311806495886%22%2C%22t3%22%3A%5B%5D%2C%22utc3%22%3A1754308379541%2C%22v%22%3A1%7D;"
    thread_id = "24065311806495886"  # Thread ID to send polls to
    delay = "30"  # Delay between polls in seconds
    folder_name = "test_folder"
    
    # Create test folder
    os.makedirs(os.path.join("data", folder_name), exist_ok=True)
    
    # Start nhây poll
    start_nhay_poll_func(cookie, thread_id, delay, folder_name)