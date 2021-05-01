import threading # manage multiple clients at the same time
import socket # network server
import time # usefull during the client 
import os # get file size and open downloaded files
import traceback # debug lib
import ast # convert str(type) to type itself
from tkinter import Tk # simple GUI for get the IPv4 and the port
from tkinter.simpledialog import askstring, askinteger # idem


""" add a function for the file downloading """

########## SOCKET ##########
server_socket = None # socket of the server
clients = [] # [(is, socket, address)]
client_data_recognition = dict() # {address: ('nickname', client_socket)}

# temp variables
client_name = ""
filename = ""
dest_file = None

# look at the bug wen a client exit (it doesn't really left from the user list refresh and file)

def Connect(host_IPv4, host_port): # connect the server
    global server_socket
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((host_IPv4, host_port))
        server_socket.listen(5)
        print("[SERVER] Server is connected !")

    except Exception as e:
        raise Exception("\033[31m[SERVER] Connection Error... {}\033[0m".format(e))
    return server_socket


def Reception(): # accept new clients and assign them a thread
    while True:
        global clients, server_socket, client_data_recognition
        try:
            (client_socket, address) = server_socket.accept()
            id_client = len(clients)
            clients.append((id_client, client_socket, address))
            client_data_recognition[clients[id_client][2]] = ("Unknown", client_socket)
            print("\033[32m[Reception] Thread created for client from {}\033[0m".format(address))
            threading.Thread(target=ClientHandler, args=(server_socket, clients[id_client])).start() # create a thread which will run the ClientHandler()


        except Exception as e:
            print("\033[31m")
            traceback.print_exc()
            print("[Reception] Errorr : {}\033[0m".format(e))
            break


def ClientHandler(s, client_info):
    print("[ClientHandler] Start receiver from {}".format(client_info[2]))
    while True:
        global clients, client_data_recognition, client_name, filename, dest_file
        try: # check if an user's here
            # process the request
            req_raw = client_info[1].recv(1024).decode()
            req_d = ExtractInfosFromRequest(req_raw)
            print(req_d)

            # message handler
            if req_d["type"] == "message": # distribute the message to all the clients
                response = HeaderCreator("::", ";;", {'type':'message', 'from_client':req_d["from_client"], 'content':req_d["content"]})
                Broadcast(response.encode(), client_info)
                


            # file handler
            elif req_d["type"] == "file_transfer":
                if req_d["command"] == "receive":
                    FileReceiver(client_info[1], "server/download/"+req_d["file_name"].replace(" ", "_"), req_d["buffer"])
                    dests = get_destinations(req_d["dest_file_list"])
                    client_name = req_d["from_client_name"]
                    ipport = client_info[2]
                    if dests != {}: # make sure it's okay
                        # Send the agree message to all people
                        response = HeaderCreator("::", ";;", {'type': 'file_transfer',
                                                              'from_client': client_name, 'ip_dest':ipport,
                                                              'command': 'get_agree_to_transfer', 'file_name': req_d["file_name"]})
                        for dest_ in dests: # send the agree consent
                            dest_[1].send(response.encode())
                        filename = req_d["file_name"]
                elif req_d["command"] == "agree":
                    if req_d["agree"] == "Yes":
                        response = HeaderCreator("::", ";;", {'type': 'file_transfer',
                                                              'from_client': client_name,
                                                              'command': 'receive', 'file_name': filename,
                                                              'buffer': '200000'})
                        client_info[1].send(response.encode())
                        FileSender(client_info[1], "server/download/"+filename.replace(" ", "_"), 200000)
                        print("[ClientHandler] File service entirely complete")
                    else:
                        print("no agreement !")


            # nicknames handler
            elif req_d["type"] == "nicknames":
                if  req_d["command"] == "post":
                    print("saving of nickanames...")
                    client_data_recognition[client_info[2]] = req_d["content"], client_data_recognition[client_info[2]][1]
                elif req_d["command"] == "get":
                    only_nicknames = dict()
                    for dat in client_data_recognition:
                        only_nicknames[dat] = client_data_recognition[dat][0]
                    header = header = HeaderCreator("::", ";;", {'type':'nicknames', 'command':'receive', 'content':HeaderCreator("££", "§§", only_nicknames)})
                    client_info[1].send(header.encode())
                    


        # errors handler
        except Exception as e:
            # if is an error in this thread, it will be kick
            print("\033[31m")
            traceback.print_exc()
            print("[ClientHandler] Exception : {}".format(e))
            print("disconnect : {}\033[0m".format(client_info[2]))
            client_info[1].close() # kick the client
            # del the infos from the kicked client
            del client_data_recognition[client_info[2]]
            try: del clients[client_info[0]]
            except: pass
            break # kill the thread


def Broadcast(data, client_info): # send a message to all the clients
    try:
        global clients
        message = data
        if len(clients) != 0:
            for client in clients:
                print(client[2])
                try:
                    client[1].send(message)
                except:
                    print("\033[31m[Broadcast] Error : {}\033[0m".format(e))
        else:
            print("[Broadcast] Nobody is connected.")
    except Exception as e:
        print("\033[31m")
        traceback.print_exc()
        print("[Broadcast] Error : {}\033[0m".format(e))

########## SOCKET ##########

########## REQUEST PROCESS ##########
def ExtractInfosFromRequest(request): # tranform the client request into a dict like {type : 'x', command: 'x', path_file : 'x'...}
    header = None
    try:
        headers = request.split(';;')
        temp_dict = dict()
        for header in headers:
            temp_dict[header.split('::')[0]] = header.split('::')[1]
        header = temp_dict
        return header
    except Exception as e:
        print("\033[31m[ExtractInfosFromRequest] Error : {}\033[0m".format(e))
        return dict

def HeaderCreator(define_marker, pause_marker, dict_header, start_marker='', end_marker=''): # transform a dict into a request for the client (it's the opposite of ExtractInfosFromRequest(request))
    head = start_marker
    i = 0
    for dict_name in dict_header:
        i += 1
        if i == len(dict_header):
            head += str(dict_name) + define_marker + str(dict_header[dict_name])
        else:
            head += str(dict_name) + define_marker + str(dict_header[dict_name]) + pause_marker
    head += end_marker
    return head

# these 2 functions are the came in the cliend programm (it does like a transmission protocol)



########## FILE TRANSFER ##########

def FileReceiver(socket, file_name, BUFFER): # receive a file from a client util it receives the end tranfert message
    print("[FileReceiver] lunched")
    try:
        with open(file_name, 'wb') as f:
            while True:
                data = socket.recv(int(BUFFER))
                if "end_file_transfer".encode() in data:
                    data = data.replace("end_file_transfer".encode(), "".encode())
                    f.write(data)
                    break
                f.write(data)
            f.close()
    except Exception as e:
        print("\033[31m")
        traceback.print_exc()
        print("[FileReceiver] Error : {}\033[0m".format(e))
    print("[FileReceiver] ended successfully")

def FileSender(socket, file_name, BUFFER): # the opposite
    try:
        f = open(file_name, 'rb')
        l = f.read(int(BUFFER))
        file_size = os.path.getsize(file_name)
        file_transfer = int(BUFFER)
        t = time.time()
        while (l):
            socket.send(l)
            l = f.read(BUFFER)
            file_transfer += int(BUFFER)
            if time.time() > t + 1:
                print(file_transfer / file_size)
                t = time.time()
        f.close()
        socket.send("end_file_transfer".encode())
        print("[FileSender] File sent !")
    except Exception as e:
        print("\033[31m")
        traceback.print_exc()
        print("[FileSender] Error : {}\033[0m".format(e))

def get_destinations(dest_file_list): # create a list of diffusion for the file
    global client_data_recognition
    traceback.print_exc()
    dests = []
    dest_file_list = ast.literal_eval(dest_file_list)
    for ct in dest_file_list:
        try:
            dests.append((client_data_recognition[ast.literal_eval(ct)][0], client_data_recognition[ast.literal_eval(ct)][1], ct, ast.literal_eval(ct)))
        except:
            pass
    print("dests : {}".format(dests))
    return dests # [('pseudo', <socket>, str(ipport), tupple(ipport)),...]


########## FILE TRANSFER ##########



while True: # get the infos for connect the server socket
    root = Tk()
    root.withdraw()
    root.call('wm', 'attributes', '.', '-topmost', True)
    IPv4 = askstring("Configuration - IP", "Please set the IP")
    Port = askstring("Configuration - port", "Please set the port (integger like 1234)")
    root.destroy()
    try:
        Connect(IPv4, int(Port))
        break
    except Exception as e:
        print("\033[31m[Main] Error : {}\033[0m".format(e))

threading.Thread(target=Reception).start()

while True: # infinite loop
    pass
