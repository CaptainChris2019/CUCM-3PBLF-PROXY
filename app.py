import html
import random
import re
import socket
import threading
import time

LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 5060
PROXY_IP = "YOURSERVERIPHERE"
UPSTREAM_HOST = "YOURCUCMIPHERE"
UPSTREAM_PORT = 5060

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((LISTEN_HOST, LISTEN_PORT))

subscriptions = {}
lock = threading.Lock()

def now():
    return time.strftime("%H:%M:%S")

def print_packet(direction, addr, data):
    try:
        text = data.decode(errors="ignore")
    except:
        text = str(data)
    print(f"\n[{now()}] {direction} {addr[0]}:{addr[1]}\n{text}\n")

def decode(data):
    return data.decode(errors="ignore")

def encode(text):
    return text.encode()

def split_message(text):
    if "\r\n\r\n" in text:
        return text.split("\r\n\r\n", 1)
    return text, ""

def get_header(text, header):
    for line in text.split("\r\n"):
        if line.lower().startswith(header.lower() + ":"):
            return line.split(":", 1)[1].strip()
    return None

def set_header(text, header, value):
    lines = text.split("\r\n")
    out = []
    replaced = False
    for line in lines:
        if line.lower().startswith(header.lower() + ":"):
            out.append(f"{header}: {value}")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        out.append(f"{header}: {value}")
    return "\r\n".join(out)

def remove_to_tag(text):
    lines = text.split("\r\n")
    out = []
    for line in lines:
        if line.lower().startswith("to:"):
            line = re.sub(r";tag=[^;\s>]+", "", line, flags=re.IGNORECASE)
        out.append(line)
    return "\r\n".join(out)

def get_call_id(text):
    return get_header(text, "Call-ID")

def get_uri_from_header(value):
    if not value:
        return ""
    m = re.search(r"<sip:([^>]+)>", value, flags=re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r"sip:([^;>\s]+)", value, flags=re.IGNORECASE)
    if m:
        return m.group(1)
    return value

def rewrite_request_uri(text, host, port):
    first, rest = text.split("\r\n", 1)
    m = re.match(r"^([A-Z]+)\s+sip:([^@>\s;]+)@([^>\s;:]+)(?::(\d+))?(\S*)\s+(SIP/2\.0)$", first)
    if not m:
        return text
    method, user, old_host, old_port, suffix, version = m.groups()
    first = f"{method} sip:{user}@{host}:{port}{suffix} {version}"
    return first + "\r\n" + rest

def ensure_content_length(text):
    head, body = split_message(text)
    head = set_header(head, "Content-Length", str(len(body.encode())))
    return head + "\r\n\r\n" + body

def build_upstream_subscribe(text):
    text = remove_to_tag(text)
    text = rewrite_request_uri(text, UPSTREAM_HOST, UPSTREAM_PORT)
    text = set_header(text, "Event", "presence")
    text = set_header(text, "Contact", f"<sip:{PROXY_IP}:{LISTEN_PORT}>")
    text = ensure_content_length(text)
    return text

def parse_presence_state(text):
    lower = text.lower()
    if "on-the-phone" in lower or "busy" in lower or "closed" in lower:
        return "confirmed"
    return "terminated"

def build_dialog_notify(sub, state):
    sub["notify_seq"] += 1
    version = sub["notify_seq"]
    call_id = sub["call_id"]
    target_uri = sub["target_uri"]
    subscriber_uri = sub["subscriber_uri"]
    request_uri = sub["contact_uri"]
    if not request_uri:
        request_uri = f"{sub['client_ip']}:{sub['client_port']}"
    
    body = f'''<?xml version="1.0"?>
<dialog-info xmlns="urn:ietf:params:xml:ns:dialog-info" version="{version}" state="full" entity="sip:{html.escape(target_uri)}">
  <dialog id="1" call-id="{html.escape(call_id)}" local-tag="relay12345" direction="recipient">
    <state>{state}</state>
    <local>
      <identity>sip:{html.escape(target_uri)}</identity>
    </local>
    <remote>
      <identity>sip:{html.escape(subscriber_uri)}</identity>
    </remote>
  </dialog>
</dialog-info>
'''
    notify = (
        f"NOTIFY sip:{request_uri} SIP/2.0\r\n"
        f"Via: SIP/2.0/UDP {PROXY_IP}:{LISTEN_PORT};branch=z9hG4bK{random.randint(10000000, 99999999)}\r\n"
        f"Max-Forwards: 70\r\n"
        f"From: <sip:{target_uri}>;tag=relay12345\r\n"
        f"To: {sub['subscriber_hdr']}\r\n"
        f"Call-ID: {call_id}\r\n"
        f"CSeq: {version} NOTIFY\r\n"
        f"Event: dialog\r\n"
        f"Subscription-State: active;expires=1800\r\n"
        f"Content-Type: application/dialog-info+xml\r\n"
        f"Content-Length: {len(body.encode())}\r\n"
        f"\r\n"
        f"{body}"
    )
    return notify

def send_to_client(call_id, data):
    with lock:
        sub = subscriptions.get(call_id)
    if not sub:
        return
    dest = (sub["client_ip"], sub["client_port"])
    sock.sendto(data, dest)
    print_packet("OUT -> CLIENT", dest, data)

def send_initial_notify(call_id):
    with lock:
        sub = subscriptions.get(call_id)
    if not sub:
        return
    notify = build_dialog_notify(sub, "terminated")
    send_to_client(call_id, notify.encode())

def handle_client_subscribe(text, addr):
    call_id = get_call_id(text)
    if not call_id:
        return
    target_uri = get_uri_from_header(get_header(text, "To"))
    subscriber_hdr = get_header(text, "From") or ""
    subscriber_uri = get_uri_from_header(subscriber_hdr)
    contact_uri = get_uri_from_header(get_header(text, "Contact"))
    with lock:
        subscriptions[call_id] = {
            "call_id": call_id,
            "client_ip": addr[0],
            "client_port": addr[1],
            "contact_uri": contact_uri,
            "subscriber_hdr": subscriber_hdr,
            "subscriber_uri": subscriber_uri,
            "target_uri": target_uri,
            "notify_seq": 0
        }
    upstream = build_upstream_subscribe(text)
    sock.sendto(upstream.encode(), (UPSTREAM_HOST, UPSTREAM_PORT))
    print_packet("OUT -> UPSTREAM", (UPSTREAM_HOST, UPSTREAM_PORT), upstream.encode())

def handle_upstream_response(text, data):
    call_id = get_call_id(text)
    if not call_id:
        return
    send_to_client(call_id, data)
    if text.startswith("SIP/2.0 200"):
        send_initial_notify(call_id)

def handle_upstream_notify(text, data):
    call_id = get_call_id(text)
    via = get_header(text, "Via")
    from_hdr = get_header(text, "From")
    to_hdr = get_header(text, "To")
    cseq = get_header(text, "CSeq")
    ok = (
        f"SIP/2.0 200 OK\r\n"
        f"Via: {via}\r\n"
        f"From: {from_hdr}\r\n"
        f"To: {to_hdr}\r\n"
        f"Call-ID: {call_id}\r\n"
        f"CSeq: {cseq}\r\n"
        f"Content-Length: 0\r\n"
        f"\r\n"
    )
    sock.sendto(ok.encode(), (UPSTREAM_HOST, UPSTREAM_PORT))
    print_packet("OUT -> UPSTREAM (200 OK)", (UPSTREAM_HOST, UPSTREAM_PORT), ok.encode())
    with lock:
        sub = subscriptions.get(call_id)
    if not sub:
        return
    state = parse_presence_state(text)
    notify = build_dialog_notify(sub, state)
    send_to_client(call_id, notify.encode())

def handle_request(data, addr):
    text = decode(data)
    if text.startswith("SUBSCRIBE"):
        handle_client_subscribe(text, addr)
        return
    sock.sendto(data, (UPSTREAM_HOST, UPSTREAM_PORT))
    print_packet("OUT -> UPSTREAM", (UPSTREAM_HOST, UPSTREAM_PORT), data)

def handle_response(data, addr):
    text = decode(data)
    if addr[0] == UPSTREAM_HOST and addr[1] == UPSTREAM_PORT:
        if text.startswith("SIP/2.0"):
            handle_upstream_response(text, data)

def handle_notify(data, addr):
    text = decode(data)
    if addr[0] == UPSTREAM_HOST and addr[1] == UPSTREAM_PORT:
        handle_upstream_notify(text, data)
    else:
        sock.sendto(data, (UPSTREAM_HOST, UPSTREAM_PORT))
        print_packet("OUT -> UPSTREAM", (UPSTREAM_HOST, UPSTREAM_PORT), data)

def handle():
    while True:
        data, addr = sock.recvfrom(65535)
        print_packet("IN", addr, data)
        text = decode(data)
        if text.startswith("SIP/2.0"):
            handle_response(data, addr)
        elif text.startswith("NOTIFY"):
            handle_notify(data, addr)
        else:
            handle_request(data, addr)

threading.Thread(target=handle, daemon=True).start()

while True:
    time.sleep(1)
