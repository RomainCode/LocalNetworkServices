import os
import random
import socket
import time
import traceback
from threading import Thread

from dependencies import LiveTransmitter
from dependencies import fileService as fService
from dependencies import messageService as msgService
from dependencies import socketConnect as sockConnService

client_and_nickname_by_address_dict = dict()
client_by_id_dict = dict()
file_process_queue = dict()
client_dest_file = []
W_transmission = None
broadcaster_dic = dict()

server_feed = None


def Check_video_feed(Class_video, client_by_id_dict):
    while True:
        if Class_video.server_is_running == False:
            clients = []
            for cl in client_by_id_dict:
                clients.append(client_by_id_dict[cl])
            request = str({'service': 'video_feed', 'type': 'stoped'}).encode()
            msgService.Broadcast(request, clients)
            break


def ReceptionRoom():
    while True:
        global server_socket, client_and_nickname_by_address_dict, client_by_id_dict, broadcaster_dic
        try:
            client_socket, address_tupple = server_socket.accept()

            # save client informations
            id_c = len(client_by_id_dict)
            client_by_id_dict[id_c] = client_socket
            client_and_nickname_by_address_dict[address_tupple] = ("Unknown", client_socket)
            broadcaster_dic[address_tupple] = (False, (None, None))

            # start exchange with the client
            print("\033[92m[ReceptionRoom] New client : {}:{} ! \033[0m".format(address_tupple[0], address_tupple[1]))
            Thread(target=ClientHandler, args=(id_c, address_tupple, client_socket)).start()

        except Exception as e:
            print("\033[32m[ReceptionRoom] Error {}\033[0m".format(e))
            break


def ClientHandler(id_c, address, client_socket):
    while True:
        global client_and_nickname_by_address_dict, client_by_id_dict, client_dest_file

        try:

            # get the request and transform it to a dict
            raw_q = client_socket.recv(1024)
            try:
                req_d = eval(raw_q)
                print(req_d)
            except Exception as e:
                print("\033[31m [ClientHandler.raw_q] Error : {}\033[0m".format(e))
                req_d = {'service': 'None caused by an error'}

            # Message Service
            if req_d['service'] == 'message':

                if req_d['type'] == 'global':  # private message
                    clients = []
                    for cl in client_by_id_dict:
                        clients.append(client_by_id_dict[cl])
                    request = str({'service': 'message', 'type': 'global', 'content': req_d['content'],
                                   'from_client': client_and_nickname_by_address_dict[address][0]}).encode()
                    msgService.Broadcast(request, clients)

                if req_d['type'] == 'private':  # global message
                    client_dest = client_and_nickname_by_address_dict[eval(req_d['client_dest_address'])][1]
                    request = str({'service': 'message', 'type': 'private', 'content': req_d['content'],
                                   'from_client': client_and_nickname_by_address_dict[address][0]}).encode()
                    client_dest.send(request)

            # File Service
            # ajouter un token unique par téléchargement (un aléatoire par destination de client)
            if req_d['service'] == 'file':

                if req_d['type'] == 'receive':  # receive and distribute the message

                    fService.FileReceiver(client_socket, req_d['file_name'], req_d['BUFFER'], save_pre_ext="server/download/")

                    d = eval(req_d['client_dest_address'])
                    if type(d) == tuple:
                        d = [d]

                    print(d)

                    client_dest_file = []
                    for i in range(len(d)):
                        client_dest_file.append(client_and_nickname_by_address_dict[d[i]][1])

                    request = []
                    global file_process_queue
                    for i in range(len(d)):
                        file_id = random.randint(0, 10000)
                        request.append(str({'service': 'file', 'type': 'getAgree', 'file_name': req_d['file_name'],
                                            'from_client_address': address, 'file_id': file_id,
                                            'BUFFER': req_d['BUFFER']}).encode())
                        file_process_queue[file_id] = (req_d['file_name'], address)
                        print(file_process_queue)

                    # send the agree
                    msgService.Broadcast(request, client_dest_file, unique=True)

                if req_d['type'] == 'agreement':

                    if req_d['command'] == 'Yes':
                        global file_process_queue_dict
                        try:
                            print(file_process_queue[int(req_d['file_id'])][0])
                            print(req_d['file_name'])
                            print(file_process_queue[int(req_d['file_id'])][0] == req_d['file_name'])
                            if file_process_queue[int(req_d['file_id'])][0] == req_d['file_name']:
                                request = str({'service': 'file', 'type': 'receive', 'file_name': req_d['file_name'],
                                               'from_client_address': file_process_queue[int(req_d['file_id'])][1],
                                               'BUFFER': int(req_d['BUFFER']),
                                               'file_size': os.path.getsize("server/download/" + req_d['file_name'])}).encode()
                                print(request)
                                client_socket.send(request)
                                fService.FileSender(client_socket, "server/download/" + req_d['file_name'], req_d['file_name'],
                                                    req_d['BUFFER'])
                                del file_process_queue[int(req_d['file_id'])]
                                print(file_process_queue)

                            else:
                                print("[ClientHandler.fileService] file_process_queue_dict error")
                                print("Original queue : {}".fomat(file_process_queue))
                                print("File id and file_name received {} | {}".format(req_d['file_id'],
                                                                                      req_d['file_name']))
                        except Exception as e:
                            print(e)
                    else:
                        try:
                            del file_process_queue[int(req_d['file_id'])]
                        except:
                            print("file process queue del error")

            # Nicknames Service
            if req_d['service'] == 'nicknames':

                if req_d['type'] == 'update':
                    client_and_nickname_by_address_dict[address] = (req_d['content'], client_socket)

                if req_d['type'] == 'get_IPs_and_nicknames':

                    nickname_by_address_dict = dict()
                    for client_address in client_and_nickname_by_address_dict:
                        nickname_by_address_dict[client_address] = client_and_nickname_by_address_dict[client_address][
                            0]

                    request = str({'service': 'nicknames', 'type': 'receive_nicknames',
                                   'content': nickname_by_address_dict}).encode()
                    client_socket.send(request)

                if req_d['type'] == 'get_my_own':
                    request = str({'service': 'nicknames', 'type': 'get_my_own', 'content': str(address)}).encode()
                    client_socket.send(request)

            # Video_feed Service
            if req_d['service'] == 'video_feed':

                if req_d['type'] == 'start_streaming':
                    global server_feed, ip, W_transmission, broadcaster_dic

                    # send a request for refresh nicknames
                    clients = []
                    for cl in client_by_id_dict:
                        clients.append(client_by_id_dict[cl])
                    request = str({'service': 'nicknames', 'type': 'order_to_refresh', }).encode()
                    msgService.Broadcast(request, clients)

                    image_bytes_socket_port = sockConnService.found_free_port()  # search a free port for stream the video
                    image_bytes_socket_address = (ip, image_bytes_socket_port)
                    print(image_bytes_socket_address)

                    web_handler_socket_port = sockConnService.found_free_port(
                        different_of=image_bytes_socket_port)  # search a free port for stream the video
                    web_handler_socket_address = (ip, web_handler_socket_port)
                    print(web_handler_socket_address)

                    # server
                    W_transmission = LiveTransmitter.Web_Server(LiveTransmitter.ImageSource.Screen, scale=1)
                    W_transmission.connect([image_bytes_socket_address, web_handler_socket_address],
                                           type_of_conn=LiveTransmitter.Web_Server.Master,
                                           mode=LiveTransmitter.Web_Server.distributor)

                    request = str({'service': 'video_feed', 'type': 'streaming_port',
                                   'image_bytes_socket_address': image_bytes_socket_address,
                                   'web_handler_socket_address': web_handler_socket_address}).encode()
                    client_socket.send(request)
                    print("W.start()")
                    W_transmission.start()

                    # check if the Video feed is running and order to the GUIs to close it when it's off
                    Thread(target=Check_video_feed, args=(W_transmission, client_by_id_dict)).start()

                    # put the user in the broadcaster dict
                    global broadcaster_dic
                    broadcaster_dic[address] = (True, web_handler_socket_address)

                    time.sleep(1)

                    # send the video feed link
                    clients = []
                    for cl in client_by_id_dict:
                        clients.append(client_by_id_dict[cl])
                    request = str({'service': 'video_feed', 'type': 'live_link',
                                   'content': [web_handler_socket_address[0], web_handler_socket_address[1]],
                                   'from_client': client_and_nickname_by_address_dict[address][0],
                                   'from_address': address}).encode()
                    msgService.Broadcast(request, clients)

                if req_d['type'] == 'end_streaming':
                    if broadcaster_dic[address][0] == True:
                        W_transmission.shutDown()
                        broadcaster_dic[address] = (False, (None, None))
                    else:
                        print("broadcast_dict doesn't match with the address")

                if req_d['type'] == 'check_is_broadcasting':
                    request = str({'service': 'video_feed', 'type': 'check_is_broadcasting', 'content':broadcaster_dic[address][0], 'web_address':broadcaster_dic[address][1]}).encode()
                    client_socket.send(request)

                    # send the port



        # del the client
        except Exception as e:
            traceback.print_exc()
            print("\033[31m [ClientHandler] Error : {}".format(e))
            client_socket.close()
            del client_and_nickname_by_address_dict[address]
            del client_by_id_dict[id_c]
            broadcaster_dic[address] = (False, (None, None))
            print("[ClientHandler] Client {} succesfully disconnected ! \033[0m")
            break

# clean the download server path:
for f in os.listdir("server\\download\\"):
    os.remove(os.path.join("server\\download\\", f))


# connect the server
print("launch start")
while True:
    port = random.randint(1000, 9999)
    port = 8081
    ip = socket.gethostbyname(socket.gethostname())
    server_socket = sockConnService.ServerConnect(ip, port)

    if server_socket != "error":
        Thread(target=sockConnService.winMessage, args=("infoConn", ip, port)).start()
        break

# launch the server
Thread(target=ReceptionRoom).start()
