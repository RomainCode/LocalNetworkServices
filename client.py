import traceback
import eel  # Web GUI
import os  # file size
import random  # eel local port selection
import socket  # network client <---> server
import threading  # multi-task capacity
import time  # get transfer rate and push %
from tkinter.filedialog import askopenfilename  # file browser
from tkinter import Tk  # use for hide the blank window in tkinter while askopenfilename
from colorama import init
from termcolor import colored

""" Work of Cortale Romain @2021 """
""" Description of the project """
#####0##### EEL GUI #####2#####
file_path_gui = ""
file_name_gui = ""
booted = False
IPv4, port = None, None
nick_name = 'Unknown'
nicknames = dict()
dest_file = None  # 192.168.1.60:12345
file_history = dict()
dest_file_dict = dict()
dest_file_list = []


@eel.expose  # send the funtion to web
def sendToPython(message):  ## Listen the GUI
    global client_socket, nick_name, file_path_gui, file_name_gui, IPv4, port, booted, nicknames, dest_file, file_history, dest_file_dict, dest_file_list
    print("[SendToPython] received : {}".format(message))
    msg_splited = message.split("&&")

    # message service
    if msg_splited[0] == "message":  # send the massage to the server
        message = HeaderCreator("::", ";;", {'type': 'message', 'from_client': nick_name, 'content': msg_splited[1]})
        client_socket.send(message.encode())


    # file service
    elif msg_splited[0] == "file_transfer":
        if msg_splited[1] == "GO":
            root = Tk()
            root.withdraw()
            root.call('wm', 'attributes', '.', '-topmost', True)
            # root.withdraw()
            file_path_gui = askopenfilename(initialdir="/", title="Select a File", filetypes=(("all files", "*.*"),))
            # Change label contents
            file_name_gui = file_path_gui.split('/')[-1]
            eel.sendToGui("file&&file_name&&{}°°{}".format(file_name_gui, file_path_gui))
            root.destroy()
            print("[SendToPython/file_path] set : {}".format(file_path_gui))

    elif msg_splited[0] == "send_file":
        if file_path_gui != "":
            header = HeaderCreator("::", ";;",
                                   {'type': 'file_transfer', 'command': 'receive', 'file_name': file_name_gui,
                                    'buffer': "200000", "dest_file": "dest_file", "dest_file_list": str(dest_file_list),
                                    'from_client_name': nick_name})
            client_socket.send(header.encode())
            time.sleep(0.2)
            FileSender(client_socket, file_path_gui, 200000)
        else:
            print("[SendToPython/send_file] No path_file.")

    elif msg_splited[0] == "boot_socket":
        if booted == False:
            global IPv4, port
            if IPv4 != None:
                print("[SendToPython/boot_socket] Try to connect...")
                ClientConnect(IPv4, port)
                if client_socket != "error":
                    threading.Thread(target=ListenServer, args=(client_socket,)).start()
                    booted = True

    elif msg_splited[0] == "turn_off":
        eel.sendToGui("power&&off&&m")

    elif msg_splited[0] == "identification":
        IPv4 = msg_splited[1].split(":")[0]
        port = int(msg_splited[1].split(":")[1])
        eel.sendToGui("power&&identification_saved&&Address saved for {}:{}. Please connect.".format(IPv4, port))

    elif msg_splited[0] == "refresh":
        if msg_splited[1] == "is_connected":
            eel.sendToGui("refresh&&is_connected&&{}".format(booted))

    elif msg_splited[0] == "file_dest":
        dat = msg_splited[1].replace("(", "").replace(")", "")
        dest_file = dat

    elif msg_splited[0] == "file_des_dict":
        dest_file_list = msg_splited[1].split("°°")


    elif msg_splited[0] == "link_file":
        for file in file_history:
            if file_history[file] == msg_splited[1]:
                os.system("start " + file)

    elif msg_splited[0] == "agree":
        if msg_splited[1] == "Yes":
            header = HeaderCreator("::", ";;", {'type': 'file_transfer', 'command': 'agree', 'agree': 'Yes'})
            client_socket.send(header.encode())
        if msg_splited[1] == "No":
            header = HeaderCreator("::", ";;", {'type': 'file_transfer', 'command': 'agree', 'agree': 'No'})
            client_socket.send(header.encode())





    # settings service
    elif msg_splited[0] == "nick_name":
        nick_name = msg_splited[1]
        header = HeaderCreator("::", ";;", {'type': 'nicknames', 'command': 'post', 'content': nick_name})
        client_socket.send(header.encode())

    # buttons pushed
    elif msg_splited[0] == "button":
        if msg_splited[1] == "refresh_user_list":
            header = HeaderCreator("::", ";;", {'type': 'nicknames', 'command': 'get'})
            client_socket.send(header.encode())


    else:
        print("[SendToPython] Command non detected")


# eel.sendToGui("message&&m&&{}°°{}".format(from_client, content)) 

#####0##### EEL GUI #####4#####


#####2##### SOCKET #####0#####
client_socket = None


def ClientConnect(host, port):
    try:
        global client_socket
        client_socket = socket.socket()
        client_socket.connect((host, port))
        eel.sendToGui("power&&on&&m")
    except Exception as e:
        print(colored("[ClientConnect] Error : {}".format(e), 'white', 'on_red'))
        eel.sendToGui("power&&error&&{}".format(e))
        client_socket = "error"


def ListenServer(sock):  ## Listen the Server
    while True:
        try:
            while True:
                global client_socket, booted, nickames, file_history
                # get type
                req_raw = sock.recv(1024).decode()
                req_d = ExtractInfosFromRequest(req_raw)
                print("[ListenServer] Request receved {}".format(req_d))

                # file_transfer
                if req_d["type"] == "file_transfer":
                    if req_d["command"] == "receive":
                        # only receive data
                        eel.sendToGui(
                            "file&&received&&{}°°{}".format(req_d["from_client"], req_d["file_name"].replace(" ", "_")))
                        FileReceiver(sock, "client/download/" + req_d["file_name"].replace(" ", "_"), req_d["buffer"])
                        file_history[
                            os.getcwd().replace("\\", "/") + "/client/download/" + req_d["file_name"].replace(" ",
                                                                                                              "_")] = \
                            req_d["file_name"].replace(" ", "_")
                        print("[FILE] ENDED SUCCESFULLY!!!")
                    elif req_d["command"] == "send":
                        # tell the server to listen, send the file
                        message = HeaderCreator("::", ";;", {'type': 'file_transfer', 'command': 'receive',
                                                             'file_name': req_d["filename"].replace(" ", "_"),
                                                             'destination': req_d["file_dest"]})
                        sock.send(message.encode())  # order to the server to receive the file
                        FileSender(sock, req_d["file_name".replace(" ", "_")])  # the client send the file
                        # then the server will send the file to the dest. client

                    elif req_d["command"] == "get_agree_to_transfer":
                        eel.sendToGui("file&&agree_to_send&&{}°°{}°°{}".format(req_d["from_client"], req_d["ip_dest"],
                                                                               req_d["file_name"]))


                # settings
                elif req_d["type"] == "nicknames":
                    if req_d["command"] == "receive":
                        nicknames = ExtractInfosFromRequest(req_d["content"], define_marker="££", pause_marker="§§")
                        eel.sendToGui("users&&post&&{}".format(DictToStr(nicknames)))

                # message
                elif req_d["type"] == "message":
                    eel.sendToGui("message&&m&&{}°°{}".format(req_d["from_client"], req_d["content"]))

                else:
                    print("[ListenServer] ErrorRequest : {}".format(req_d["command"]))



        except Exception as e:
            traceback.print_exc()
            # print("[ListenServer] Error : {}".format(e))
            print(colored("[ListenServer] Error : {}".format(e), 'white', 'on_red'))
            if str(type(e).__name__) == "ConnectionResetError" and str(
                    e.args[0]) == "10054":  # = to connection lost with the server
                try:
                    # eel.sendToGui("power&&off&&m")
                    eel.sendToGui("power&&reconnect&&m")
                    # client_socket.close()
                    client_socket = None
                    booted = False
                except:
                    pass
                break

            if str(type(e).__name__) == "ConnectionResetError" and str(
                    e.args[0]) == "10053":  # = to connection lost with the server
                try:
                    # eel.sendToGui("power&&off&&m")
                    eel.sendToGui("power&&reconnect&&m")
                    # client_socket.close()
                    client_socket = None
                    booted = False
                except:
                    pass
                break

                # exit()


#####0##### SOCKET #####5#####


########## REQUEST PROCESS ##########
def ExtractInfosFromRequest(request, define_marker="::", pause_marker=";;"):
    header = None
    try:
        headers = request.split(pause_marker)
        temp_dict = dict()
        for header in headers:
            temp_dict[header.split(define_marker)[0]] = header.split(define_marker)[1]
        header = temp_dict
        return header
    except Exception as e:
        print(colored("[ExtractInfosFromRequest] Error : {}".format(e), 'white', 'on_red'))
        return dict


def HeaderCreator(define_marker, pause_marker, dict_header, start_marker='', end_marker=''):
    head = start_marker
    i = 0
    for dict_name in dict_header:
        i += 1
        if i == len(dict_header):
            head += dict_name + define_marker + dict_header[dict_name]
        else:
            head += dict_name + define_marker + dict_header[dict_name] + pause_marker
    head += end_marker
    return head


########## REQUEST PROCESS ##########


########## FILE TRANSFER ##########
def FileReceiver(socket, file_name, BUFFER):
    try:
        with open(file_name, 'wb') as f:
            while True:
                # print('receiving data...')
                data = socket.recv(int(BUFFER))
                # print(len(data))
                if "end_file_transfer".encode() in data:
                    data = data.replace("end_file_transfer".encode(), "".encode())
                    f.write(data)
                    # print(data)
                    break
                # print('data={}'.format(data))
                # write data to a file
                f.write(data)
            f.close()
        print("[FileReceiver] File received successfully !")
    except Exception as e:
        print(colored("[FileReceiver] Error : {}".format(e), 'white', 'on_red'))


def FileSender(socket, file_name, BUFFER):
    try:
        # filename='video.mp4' #In the same folder or path is this file running must the file you want to tranfser to be
        f = open(file_name, 'rb')
        l = f.read(BUFFER)
        file_size = os.path.getsize(file_name)
        file_transfer = int(BUFFER)
        t = time.time()
        while (l):
            # print('Sent '+repr(l))
            socket.send(l)
            l = f.read(BUFFER)
            last_tr = file_transfer
            file_transfer += int(BUFFER)
            if time.time() > t + 1:
                print(file_transfer / file_size)
                print("Transfer rate : " + str((file_transfer - last_tr) / 1000000) + "Mb/s")
                eel.sendToGui("file&&progress&&{}".format(file_transfer / file_size))
                t = time.time()
                last_tr = file_transfer
        f.close()
        eel.sendToGui("file&&progress&&{}".format(1))
        socket.send("end_file_transfer".encode())
        socket.send("end_file_transfer".encode())
        print("[FileSender] File sended successfully !")
    except Exception as e:
        traceback.print_exc()
        print(colored("[FileSender] Error : {}".format(e), 'white', 'on_red'))


########## FILE TRANSFER ##########


### OTHER ###
def DictToStr(dic):
    i = 0
    output = "{"
    for di in dic:
        if i == len(dic):
            output += di + "::" + dic[di]
        else:
            output += di + "::" + dic[di] + ",,"
    output += "}"
    return output


### OTHER ###


########## EEL - MAIN ##########
eel_port = random.randint(1000, 9999)
eel.init("client")
try:
    eel.start("index.html", port=eel_port, block=False)
except:
    print("error eel")
    i = 0
    while i == 0:
        try:
            eel.start("index.html", port=random.randint(1000, 9999), block=False)
            print("[Main] Port eel found")
            i = 1
        except:
            pass

while True:
    try:
        eel.sleep(0.01)
    except:
        from tkinter import messagebox

        root = Tk()
        root.withdraw()
        root.call('wm', 'attributes', '.', '-topmost', True)
        messagebox.showerror("Critical error",
                             "We can't provide the 'LAN Services' on this session.\nPlease, relaunch the software.")
        root.destroy()
        break
########## EEL - MAIN ##########
# add a freeze to the window during the download
