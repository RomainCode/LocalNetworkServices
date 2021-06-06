import os
import random
import time
import traceback
from threading import Thread
from tkinter import Tk
from tkinter.filedialog import askopenfilename

import eel

from dependencies import LiveTransmitter
from dependencies import fileService as fService
from dependencies import socketConnect as sockConnService

nickname_by_address_dict = dict()
sock = None
current_gui_path = None
current_gui_file_name = None
list_clients_address_gui = []
current_gui_address = None
my_own_address = None
feed_source = None
C = None


def remap_keys(mapping):
    return [{'key': k, 'value': v} for k, v in mapping.items()]


@eel.expose
def sendToPython(data):
    global sock, current_gui_path, current_gui_file_name, nickname_by_address_dict, list_clients_address_gui, current_gui_address

    # pre-process the data
    data_splited = data.split("||")
    print(data)

    if data_splited[0] == "message":

        if data_splited[1] == "global":
            response = str({'service': 'message', 'type': 'global', 'content': data_splited[2]}).encode()
            sock.send(response)

        if data_splited[1] == "private":

            if data_splited[2] == "dest":
                d = data_splited[3].replace('(', '("').replace(',', '",')
                current_gui_address = eval(d)

            if data_splited[2] == "content" and current_gui_address != None:
                response = str({'service': 'message', 'type': 'private', 'content': data_splited[3],
                                'client_dest_address': str(current_gui_address)}).encode()
                sock.send(response)

    if data_splited[0] == 'file':

        if data_splited[1] == 'choose_a_file':
            # file browser window
            root = Tk()
            root.withdraw()
            root.call('wm', 'attributes', '.', '-topmost', True)

            # get file_name and path
            current_gui_path = askopenfilename(initialdir="/", title="Select a File", filetypes=(("all files", "*.*"),))
            # current_gui_path = current_gui_path.replace(" ", "_")
            current_gui_file_name = current_gui_path.split('/')[-1]
            root.destroy()

            # return the infos to the GUI
            eel.sendToGui("file||file_infos||{}||{}".format(current_gui_path, current_gui_file_name))
            print("[SendToPython/file_path] set : {}".format(current_gui_path))

        if data_splited[1] == 'dest_clients_address':
            list_clients_address_gui = eval(data_splited[2])
            print(list_clients_address_gui)

        if data_splited[1] == 'send':
            request = str({'service': 'file', 'type': 'receive', 'client_dest_address': str(list_clients_address_gui),
                           'file_name': current_gui_file_name, 'BUFFER': 200000}).encode()
            print(str({'service': 'file', 'type': 'receive', 'client_dest_address': str(list_clients_address_gui),
                       'file_name': current_gui_file_name, 'BUFFER': 200000}))
            sock.send(request)
            fService.FileSender(sock, current_gui_path, current_gui_file_name, 200000, eel_display=True, eel=eel)
            # demander d'abord le agree du client ?

        if data_splited[1] == 'agreement':
            if data_splited[2] == 'Yes':
                request = str({'service': 'file', 'type': 'agreement', 'command': 'Yes', 'file_id': data_splited[3],
                               'file_name': data_splited[4], 'BUFFER': data_splited[5]}).encode()
                sock.send(request)
            else:
                request = str({'service': 'file', 'type': 'agreement', 'command': 'No', 'file_id': data_splited[3],
                               'file_name': data_splited[4], 'BUFFER': data_splited[5]}).encode()
                sock.send(request)

        if data_splited[1] == 'open':
            os.system(f"start client\download\{data_splited[2]}")

    if data_splited[0] == 'nicknames':

        if data_splited[1] == 'get_IPs_and_nicknames':
            request = str({'service': 'nicknames', 'type': 'get_IPs_and_nicknames'}).encode()
            sock.send(request)

        if data_splited[1] == 'get_my_own':
            request = str({'service': 'nicknames', 'type': 'get_my_own'}).encode()
            sock.send(request)

        if data_splited[1] == 'update':
            request = str({'service': 'nicknames', 'type': 'update', 'content': data_splited[2]}).encode()
            sock.send(request)

    if data_splited[0] == 'video_feed':

        if data_splited[1] == 'check_is_broadcasting':
            request = str({'service': 'video_feed', 'type': 'check_is_broadcasting'}).encode()
            sock.send(request)

        if data_splited[1] == 'start_broadcasting':
            global feed_source
            if data_splited[2] == "camera":
                feed_source = LiveTransmitter.ImageSource.Camera
            elif data_splited[2] == "screen":
                feed_source = LiveTransmitter.ImageSource.Screen
            else:
                print(data_splited[2])
            request = str({'service': 'video_feed', 'type': 'start_streaming', 'source': data_splited[2]}).encode()
            sock.send(request)
            eel.sendToGui("video_feed||info||trying to launch the stream... Please wait.||next")

        if data_splited[1] == 'stop':
            global C
            if C != None:
                C.shutDown()
                request = str({'service': 'video_feed', 'type': 'end_streaming'}).encode()
                sock.send(request)


def ServerHandler(sock):
    while type(sock) != str:
        try:

            # receive and pre-process the data
            req_raw = sock.recv(1024).decode()
            req_d = eval(req_raw)
            print(req_d)

            # Message Service
            if req_d['service'] == 'message':

                if req_d['type'] == 'global':
                    print("[GlobalMessage] {}".format(req_d['content']))
                    eel.sendToGui("message||global||" + req_d['from_client'] + "||" + req_d['content'])

                if req_d['type'] == 'private':
                    eel.sendToGui("message||private||{}||{}".format(req_d['from_client'], req_d['content']))
                    print("[PrivateMessage] {}".format(req_d['content']))

            # File Service
            if req_d['service'] == 'file':

                if req_d['type'] == 'receive':
                    req_d["file_name"] = req_d["file_name"].replace(" ", "_")
                    print("RECEIVEING FILE ")
                    fService.FileReceiver(sock, req_d['file_name'], req_d['BUFFER'], file_size=req_d['file_size'],
                                          eel=eel, save_pre_ext="client/download/")
                    eel.sendToGui("file||file_received_successfully||" + req_d['file_name'])

                if req_d['type'] == 'getAgree':
                    eel.sendToGui(
                        "file||getAgree||{}||{}||{}||{}".format(req_d['file_name'], req_d['from_client_address'],
                                                                req_d['file_id'], req_d['BUFFER']))

            # Nicknames Service
            if req_d['service'] == 'nicknames':

                if req_d['type'] == 'receive_nicknames':
                    global nickname_by_address_dict
                    nickname_by_address_dict = dict()
                    nickname_by_address_dict = req_d['content']
                    eel.sendToGui(
                        "nicknames||get_IPs_and_nicknames||" + str(remap_keys(nickname_by_address_dict)).replace("(",
                                                                                                                 "[").replace(
                            ")", "]").replace("'", '"'))

                if req_d['type'] == 'get_my_own':
                    global my_own_address
                    my_own_address = req_d['content']
                    eel.sendToGui("nicknames||get_my_own||" + str(my_own_address))

                if req_d['type'] == 'order_to_refresh':
                    request = str({'service': 'nicknames', 'type': 'get_IPs_and_nicknames'}).encode()
                    sock.send(request)

            # Video_feed Service
            if req_d['service'] == 'video_feed':

                if req_d['type'] == 'check_is_broadcasting':
                    eel.sendToGui("video_feed||check_is_broadcasting||"+str(req_d['content'])+"||"+str([req_d['web_address'][0], req_d['web_address'][1]]))

                if req_d['type'] == 'streaming_port':
                    time.sleep(2)
                    # client
                    print(req_d['image_bytes_socket_address'])
                    global feed_source, C
                    C = LiveTransmitter.Web_Server(feed_source, scale=1)
                    print("connect")
                    C.connect(req_d['image_bytes_socket_address'], type_of_conn=LiveTransmitter.Web_Server.Slave,
                              mode=LiveTransmitter.Web_Server.sender)
                    C.start()
                    print("started")
                    eel.sendToGui(
                        "video_feed||info||<p style='background-color: green; color: white'>You are streaming now !<p/>||erase")

                    eel.sendToGui("video_feed||started")
                    time.sleep(1)

                if req_d['type'] == 'live_link':
                    eel.sendToGui(
                        f"video_feed||video_link||{req_d['content'][0]}||{req_d['content'][1]}||{[req_d['from_address'][0], req_d['from_address'][1]]}")

                if req_d['type'] == 'stoped':
                    eel.sendToGui("video_feed||stoped")  # create the web feed video stop part in Sublime Text*
                    eel.sendToGui(
                        "video_feed||info||<p style='background-color: red; color: white'>Stream closed !<p/>||erase")





        except Exception as e:
            print(type(e).__name__)
            if type(e).__name__ == "ConnectionResetError":
                print("Connection with the server lost !")
                eel.sendToGui("global||exit")
                sockConnService.winMessage("error", title="Fatal error", msg="Connection lost with the server...\nPlease close this message box to completely terminate the program.")
                exit()
            print("[ServerHandler] Error : {}".format(e))
            traceback.print_exc()

    time.sleep(1)
    print("exit")
    eel.sendToGui("global||exit")
    exit()


#sock = sockConnService.ClientConnect("192.168.56.1", 8081)
while True:
    address = sockConnService.getConnectionInfoBox()
    try:
        sock = sockConnService.ClientConnect(address[0], address[1])
        break
    except:
        pass
Thread(target=ServerHandler, args=(sock,), daemon=True).start()

########## EEL - MAIN ##########
eel_port = random.randint(1000, 9999)
eel.init("client")
try:
    eel.start("index.html", port=eel_port, block=False)
except:
    while True:
        try:
            eel.start("index.html", port=random.randint(1000, 9999), block=False)
            print("[Main] Port eel found")
            break
        except:
            pass

while True:
    try:
        eel.sleep(0.01)
    except:
        time.sleep(1.5)
        print("Global error")


""" 
- Ajouter la fenêtre de connexion pour sock au dessus de eel - main
"""
